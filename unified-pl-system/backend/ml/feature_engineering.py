def engineer_features(df) -> "pd.DataFrame":
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler
    
    df = df.copy()

    # 1. log_amount: log1p(|amount|) * sign(amount)
    df["log_amount"] = np.log1p(np.abs(df["amount"])) * np.sign(df["amount"])

    # 2. domain_encoded & line_item_encoded
    df["domain_encoded"] = df["domain"].astype("category").cat.codes
    df["line_item_encoded"] = df["line_item"].astype("category").cat.codes

    # 3. period_num & year_num (Assuming period is YYYY-QX or YYYY-MM)
    try:
        df["year_num"] = df["period"].str.extract(r"^(\d{4})").astype(float)
        # Extract last digit of QX or month
        df["period_num"] = df["period"].str.extract(r"(\d+)$").astype(float)
    except Exception:
        df["year_num"] = 0.0
        df["period_num"] = 0.0

    df["year_num"] = df["year_num"].fillna(0.0)
    df["period_num"] = df["period_num"].fillna(0.0)

    # 4. amount_zscore
    df["amount_zscore"] = (
        df.groupby("domain")["amount"]
        .transform(lambda x: (x - x.mean()) / x.std())
        .fillna(0)
    )

    # 5. period_rolling_mean (approximation since order matters)
    df = df.sort_values(by=["domain", "line_item", "period"])
    df["period_rolling_mean"] = df.groupby(["domain", "line_item"])["amount"].transform(
        lambda x: x.rolling(4, min_periods=1).mean()
    )

    # 6. Normalize amount
    scaler = StandardScaler()
    df["amount_scaled"] = scaler.fit_transform(df[["amount"]])

    return df
