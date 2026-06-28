import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session

from models.pl_record import PLRecord


def generate_forecast(db: Session, domain: str, periods: int = 3):
    records = (
        db.query(PLRecord)
        .filter(PLRecord.domain == domain)
        .order_by(PLRecord.period)
        .all()
    )
    if not records:
        return {"error": "No data found for domain"}

    df = pd.DataFrame(
        [
            {"period": r.period, "amount": r.amount, "line_item": r.line_item}
            for r in records
        ]
    )

    # Simple linear regression forecasting
    forecasts = {}

    # Filter for revenue
    revenue_mask = (
        df["line_item"].str.lower().str.contains("revenue|income|sales", na=False)
    )
    rev_df = df[revenue_mask].groupby("period")["amount"].sum().reset_index()

    if len(rev_df) > 1:
        X = np.arange(len(rev_df)).reshape(-1, 1)
        y = rev_df["amount"].values
        model = LinearRegression().fit(X, y)

        future_X = np.arange(len(rev_df), len(rev_df) + periods).reshape(-1, 1)
        preds = model.predict(future_X)
        forecasts["revenue"] = [float(p) for p in preds]
    else:
        forecasts["revenue"] = []

    # Same for expense
    expense_mask = (
        df["line_item"].str.lower().str.contains("expense|cost|cogs|opex", na=False)
    )
    exp_df = df[expense_mask].groupby("period")["amount"].sum().reset_index()

    if len(exp_df) > 1:
        X = np.arange(len(exp_df)).reshape(-1, 1)
        y = exp_df["amount"].values
        model = LinearRegression().fit(X, y)

        future_X = np.arange(len(exp_df), len(exp_df) + periods).reshape(-1, 1)
        preds = model.predict(future_X)
        forecasts["expense"] = [float(p) for p in preds]
    else:
        forecasts["expense"] = []

    return forecasts
