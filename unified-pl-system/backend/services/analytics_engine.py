from services.metric_engine import MetricEngine
import numpy as np

class AnalyticsEngine:
    def __init__(self, metric_engine: MetricEngine):
        self.me = metric_engine

    def get_forecast(self, dept=None, metric="profit", n_forecast=12):
        import pandas as pd
        import numpy as np

        profile = self.me.get_active_profile()
        freq = profile["date_frequency"] or "monthly"
        df_agg = self.me.aggregate_data(freq, dept)
        
        # Check capabilities
        caps = self.me.get_capabilities()
        metric_avail = False
        if metric == "revenue" and caps["revenue"]["available"]:
            metric_avail = True
        elif metric == "profit" and caps["profit"]["available"]:
            metric_avail = True
            
        if not metric_avail or df_agg.empty:
            return {
                "has_enough_data": False,
                "expected_case": 0,
                "best_case": 0,
                "worst_case": 0,
                "forecast": [],
                "historical": [],
                "model_used": "None",
                "confidence_score": 0.0,
                "observations": 0
            }
            
        historical = []
        for _, r in df_agg.iterrows():
            historical.append({
                "period": r["period"],
                "revenue": r["revenue"],
                "expense": r["expense"],
                "profit": r["profit"]
            })
            
        values = df_agg[metric].astype(float).tolist()
        n_obs = len(values)
        
        if n_obs < 4:
            return {
                "has_enough_data": False,
                "expected_case": 0,
                "best_case": 0,
                "worst_case": 0,
                "forecast": [],
                "historical": historical,
                "model_used": "None",
                "confidence_score": 0.0,
                "observations": n_obs
            }

        months = np.arange(n_obs)
        coeffs = np.polyfit(months, values, 1)
        slope, intercept = coeffs[0], coeffs[1]
        
        # Validation split: 80% train, 20% test (minimum 3 points for train)
        split_idx = max(3, int(n_obs * 0.8))
        train_vals = values[:split_idx]
        test_vals = values[split_idx:]
        
        train_months = np.arange(split_idx)
        train_coeffs = np.polyfit(train_months, train_vals, 1)
        tr_slope, tr_intercept = train_coeffs[0], train_coeffs[1]
        
        test_months = np.arange(split_idx, n_obs)
        pred_test = tr_slope * test_months + tr_intercept
        
        y_true = np.array(test_vals)
        y_pred = np.array(pred_test)
        
        mape_denom = np.where(y_true == 0, 1e-5, y_true)
        mape = float(np.mean(np.abs((y_true - y_pred) / mape_denom)) * 100)
        
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0
        
        if r2 < 0.0 or np.isnan(r2):
            r2 = 0.0
        if r2 > 1.0:
            r2 = 1.0

        last_period = df_agg["period"].iloc[-1]
        forecast_dates = []
        
        if freq == "daily":
            last_date = pd.to_datetime(last_period)
            forecast_dates = [(last_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, n_forecast + 1)]
        elif freq == "weekly":
            try:
                year_str, week_str = last_period.split("-W")
                year = int(year_str)
                week = int(week_str)
            except Exception:
                year, week = 2026, 1
            for i in range(1, n_forecast + 1):
                week += 1
                if week > 52:
                    week = 1
                    year += 1
                forecast_dates.append(f"{year}-W{week:02d}")
        elif freq == "yearly":
            try:
                year = int(last_period)
            except Exception:
                year = 2026
            forecast_dates = [str(year + i) for i in range(1, n_forecast + 1)]
        else: # monthly
            try:
                year, month = map(int, last_period.split("-"))
            except Exception:
                year, month = 2026, 6
            for i in range(1, n_forecast + 1):
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                forecast_dates.append(f"{year}-{month:02d}")


        forecast_out = []
        base_vals = []
        opt_vals = []
        cons_vals = []
        
        for i in range(1, n_forecast + 1):
            x_val = n_obs + i - 1
            pred_base = (slope * x_val) + intercept
            
            pred_opt = pred_base * 1.15
            pred_cons = pred_base * 0.85
            
            if metric == "revenue":
                pred_base = max(0.0, pred_base)
                pred_opt = max(0.0, pred_opt)
                pred_cons = max(0.0, pred_cons)
                
            # Use n_forecast-safe date lookup
            if i - 1 < len(forecast_dates):
                fdate = forecast_dates[i - 1]
            else:
                fdate = f"Period+{i}"
                
            forecast_out.append({
                "period": fdate,
                "predicted_value": round(pred_base, 2),
                "lower": round(pred_cons, 2),
                "upper": round(pred_opt, 2)
            })
            base_vals.append(pred_base)
            opt_vals.append(pred_opt)
            cons_vals.append(pred_cons)

        return {
            "has_enough_data": True,
            "expected_case": round(sum(base_vals), 2),
            "best_case": round(sum(opt_vals), 2),
            "worst_case": round(sum(cons_vals), 2),
            "forecast": forecast_out,
            "historical": historical,
            "model_used": "Linear Regression (OLS)",
            "confidence_score": round(r2, 2),
            "r2_score": round(r2, 2),
            "mape": round(mape, 2),
            "observations": n_obs
        }

    def get_anomalies(self, dept=None):
        profile = self.me.get_active_profile()
        freq = profile["date_frequency"] or "monthly"
        df_agg = self.me.aggregate_data(freq, dept)
        caps = self.me.get_capabilities()
        
        if len(df_agg) < 3 or not caps["profit"]["available"]:
            return []

        profits = df_agg["profit"].dropna().tolist()
        if not profits:
            return []
            
        mean_profit = np.mean(profits)
        std_profit = np.std(profits)

        anomalies = []
        for _, row in df_agg.iterrows():
            profit = row["profit"]
            if pd.isna(profit):
                continue
            if std_profit > 0 and abs(profit - mean_profit) > (1.5 * std_profit):
                severity = "HIGH" if abs(profit - mean_profit) > (2.5 * std_profit) else "MEDIUM"
                anomalies.append({
                    "id": f"anm-{row['period']}",
                    "metric": "Profit",
                    "value": profit,
                    "expected_range": f"{round(mean_profit - std_profit)} to {round(mean_profit + std_profit)}",
                    "period": row["period"],
                    "severity": severity,
                    "description": f"Profit of {profit} is outside expected bounds.",
                    "status": "OPEN",
                    "department": dept or "All Departments"
                })

        return anomalies
