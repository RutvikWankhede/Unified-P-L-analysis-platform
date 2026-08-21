from scipy import stats

from config import settings
from ml.feature_engineering import engineer_features

def get_contamination(domain: str, db=None) -> float:
    if db:
        try:
            from models.domain_settings import DomainSettings
            domain_setting = db.query(DomainSettings).filter(DomainSettings.domain == domain).first()
            if domain_setting:
                return domain_setting.contamination_rate
        except Exception:
            pass

    domain_lower = domain.lower()
    if "retail" in domain_lower:
        return settings.CONTAM_RETAIL
    elif "corporate" in domain_lower:
        return settings.CONTAM_CORPORATE
    elif "investment" in domain_lower:
        return settings.CONTAM_INVESTMENT
    elif "sme" in domain_lower:
        return settings.CONTAM_SME
    return 0.05  # Default


def assign_severity(anomaly_score: float, batch_scores: list) -> str:
    percentile = stats.percentileofscore(batch_scores, anomaly_score)
    if percentile >= 95:
        return "High"
    elif percentile >= 75:
        return "Medium"
    else:
        return "Low"


def detect_anomalies(records: list) -> list:
    if not records:
        return []

    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest

    df = pd.DataFrame([{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records])
    if "id" not in df.columns:
        df["id"] = [r.id for r in records]

    df_features = engineer_features(df)

    features = [
        "amount_scaled",
        "log_amount",
        "domain_encoded",
        "line_item_encoded",
        "year_num",
        "period_num",
        "amount_zscore",
        "period_rolling_mean",
    ]

    X = df_features[features].fillna(0)

    results = []

    # We need a DB session to read adaptive thresholds
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        # Process per domain due to different contamination rates
        for domain, group in df_features.groupby("domain"):
            contam = get_contamination(domain, db)
            # IsolationForest expects contamination in (0, 0.5]
            contam = max(0.001, min(contam, 0.5))

            clf = IsolationForest(contamination=contam, random_state=42)

            group_X = X.loc[group.index]
            if len(group_X) > 1:
                clf.fit(group_X)
                # anomaly score in scikit-learn is opposite, lower is more anomalous.
                # We invert it so higher is more anomalous.
                scores = -clf.decision_function(group_X)
                preds = clf.predict(group_X)
                is_anomaly = preds == -1
            else:
                scores = np.zeros(len(group_X))
                is_anomaly = np.zeros(len(group_X), dtype=bool)

            group["anomaly_score"] = scores
            group["is_anomaly"] = is_anomaly
            results.append(group)

        if not results:
            return []

        final_df = pd.concat(results)

        # Calculate percentiles and assign severity for the batch
        anomalous_df = final_df[final_df["is_anomaly"]]  # Keep as is for pandas comparison
        if not anomalous_df.empty:
            batch_scores = anomalous_df["anomaly_score"].tolist()
            final_df["percentile_rank"] = final_df.apply(
                lambda row: (
                    stats.percentileofscore(batch_scores, row["anomaly_score"])
                    if row["is_anomaly"]
                    else 0.0
                ),
                axis=1,
            )
            final_df["severity"] = final_df.apply(
                lambda row: (
                    assign_severity(row["anomaly_score"], batch_scores)
                    if row["is_anomaly"]
                    else "Low"
                ),
                axis=1,
            )
        else:
            final_df["percentile_rank"] = 0.0
            final_df["severity"] = "Low"

        # Filter only anomalies to return
        anomalies = final_df[final_df["is_anomaly"]]

        out = []
        for _, row in anomalies.iterrows():
            out.append(
                {
                    "pl_record_id": int(row["id"]),
                    "anomaly_score": float(row["anomaly_score"]),
                    "severity": str(row["severity"]),
                    "is_anomaly": bool(row["is_anomaly"]),
                    "percentile_rank": float(row["percentile_rank"]),
                    "status": "open",
                }
            )
    finally:
        db.close()

    return out
