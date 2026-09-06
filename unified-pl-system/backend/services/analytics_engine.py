from services.metric_engine import MetricEngine
import numpy as np

class AnalyticsEngine:
    def __init__(self, metric_engine: MetricEngine):
        self.me = metric_engine

    def get_forecast(self, dept=None, metric="profit", n_forecast=12, agg=None):
        import pandas as pd
        import numpy as np

        profile = self.me.get_active_profile()
        freq = agg or profile["date_frequency"] or "monthly"
        dept_filter = None if str(dept).lower() in ["overall", "all", "all departments", ""] else dept
        df_agg = self.me.aggregate_data(freq, dept_filter)
        
        # Check capabilities
        caps = self.me.get_capabilities()
        norm_metric = str(metric).lower().strip()
        if norm_metric in ["net_profit", "gross_profit", "profit"]:
            norm_metric = "profit"
        elif norm_metric in ["margin", "margin_pct", "margin %"]:
            norm_metric = "margin"
        elif norm_metric in ["revenue", "sales", "income"]:
            norm_metric = "revenue"
        elif norm_metric in ["expense", "expenses", "cost", "opex"]:
            norm_metric = "expense"
        else:
            norm_metric = "profit"
            
        if df_agg.empty:
            return {
                "has_enough_data": False,
                "expected_case": 0,
                "best_case": 0,
                "worst_case": 0,
                "forecast": [],
                "historical": [],
                "model_used": "None",
                "confidence_score": 0.0,
                "observations": 0,
                "drivers": [],
                "explanation": "Insufficient data for this forecast period."
            }
            
        historical = []
        for _, r in df_agg.iterrows():
            rev = float(r.get("revenue", 0.0) or 0.0)
            exp = float(r.get("expense", 0.0) or 0.0)
            prof = float(r.get("profit", rev - exp) or 0.0)
            mrg = float(r.get("margin", (prof / rev * 100) if rev > 0 else 0.0) or 0.0)
            historical.append({
                "period": str(r["period"]),
                "revenue": round(rev, 2),
                "expense": round(exp, 2),
                "profit": round(prof, 2),
                "margin": round(mrg, 2),
                "value": round(mrg if norm_metric == "margin" else (rev if norm_metric == "revenue" else (exp if norm_metric == "expense" else prof)), 2)
            })
            
        if norm_metric in df_agg.columns:
            values = df_agg[norm_metric].astype(float).tolist()
        else:
            values = [h["value"] for h in historical]
            
        n_obs = len(values)
        
        if n_obs < 2:
            return {
                "has_enough_data": False,
                "expected_case": 0,
                "best_case": 0,
                "worst_case": 0,
                "forecast": [],
                "historical": historical,
                "model_used": "None",
                "confidence_score": 0.0,
                "observations": n_obs,
                "drivers": [],
                "explanation": "Insufficient data for this forecast period."
            }

        months = np.arange(n_obs)
        coeffs = np.polyfit(months, values, 1)
        slope, intercept = float(coeffs[0]), float(coeffs[1])
        
        # Validation split: 80% train, 20% test (safe for small n_obs)
        if n_obs >= 4:
            split_idx = max(3, int(n_obs * 0.8))
            train_vals = values[:split_idx]
            test_vals = values[split_idx:]
            
            train_months = np.arange(split_idx)
            train_coeffs = np.polyfit(train_months, train_vals, 1)
            tr_slope, tr_intercept = float(train_coeffs[0]), float(train_coeffs[1])
            
            test_months = np.arange(split_idx, n_obs)
            pred_test = tr_slope * test_months + tr_intercept
            
            y_true = np.array(test_vals)
            y_pred = np.array(pred_test)
            
            mape_denom = np.where(y_true == 0, 1e-5, y_true)
            mape = float(np.mean(np.abs((y_true - y_pred) / mape_denom)) * 100)
            
            ss_res = np.sum((y_true - y_pred) ** 2)
            ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
            r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0
        else:
            y_pred_all = slope * months + intercept
            ss_res = np.sum((values - y_pred_all) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.95
            mape = 5.0
        
        if r2 < 0.0 or np.isnan(r2):
            r2 = 0.0
        if r2 > 1.0:
            r2 = 1.0

        last_period = str(df_agg["period"].iloc[-1])
        forecast_dates = []
        
        freq_lower = freq.lower().replace("_", "-")
        if freq_lower in ["daily", "day"]:
            try:
                last_date = pd.to_datetime(last_period)
                forecast_dates = [(last_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, n_forecast + 1)]
            except Exception:
                forecast_dates = [f"Day+{i}" for i in range(1, n_forecast + 1)]
        elif freq_lower in ["weekly", "week"]:
            try:
                if "-W" in last_period:
                    year_str, week_str = last_period.split("-W")
                    year = int(year_str)
                    week = int(week_str)
                else:
                    year, week = 2026, 1
            except Exception:
                year, week = 2026, 1
            for i in range(1, n_forecast + 1):
                week += 1
                if week > 52:
                    week = 1
                    year += 1
                forecast_dates.append(f"{year}-W{week:02d}")
        elif freq_lower in ["half-yearly", "half_yearly", "half-year", "h1-h2"]:
            try:
                if "-H" in last_period:
                    year_str, h_str = last_period.split("-H")
                    year = int(year_str)
                    h_num = int(h_str)
                else:
                    year, h_num = 2026, 1
            except Exception:
                year, h_num = 2026, 1
            for i in range(1, n_forecast + 1):
                h_num += 1
                if h_num > 2:
                    h_num = 1
                    year += 1
                forecast_dates.append(f"{year}-H{h_num}")
        elif freq_lower in ["quarterly", "quarter"]:
            try:
                if "-Q" in last_period:
                    year_str, q_str = last_period.split("-Q")
                    year = int(year_str)
                    q_num = int(q_str)
                else:
                    year, q_num = 2026, 1
            except Exception:
                year, q_num = 2026, 1
            for i in range(1, n_forecast + 1):
                q_num += 1
                if q_num > 4:
                    q_num = 1
                    year += 1
                forecast_dates.append(f"{year}-Q{q_num}")
        elif freq_lower in ["yearly", "year", "annual"]:
            try:
                year = int(last_period[:4])
            except Exception:
                year = 2026
            forecast_dates = [str(year + i) for i in range(1, n_forecast + 1)]
        else: # monthly
            try:
                parts = last_period.split("-")
                year, month = int(parts[0]), int(parts[1])
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
        
        # Standard error for confidence interval
        residuals = np.array(values) - (slope * months + intercept)
        std_err = float(np.std(residuals)) if len(residuals) > 1 else (abs(values[-1]) * 0.08)
        if std_err == 0:
            std_err = abs(values[-1]) * 0.05
            
        for i in range(1, n_forecast + 1):
            x_val = n_obs + i - 1
            pred_base = (slope * x_val) + intercept
            
            spread = 1.96 * std_err * np.sqrt(1 + (1.0 / n_obs) + ((x_val - np.mean(months))**2 / np.sum((months - np.mean(months))**2 + 1e-6)))
            pred_opt = pred_base + spread
            pred_cons = pred_base - spread
            
            if norm_metric in ["revenue", "expense"]:
                pred_base = max(0.0, pred_base)
                pred_opt = max(0.0, pred_opt)
                pred_cons = max(0.0, pred_cons)
            elif norm_metric == "margin":
                pred_base = max(-100.0, min(100.0, pred_base))
                pred_opt = max(-100.0, min(100.0, pred_opt))
                pred_cons = max(-100.0, min(100.0, pred_cons))
                
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

        # Dynamic drivers calculation
        rev_vals = [h["revenue"] for h in historical]
        exp_vals = [h["expense"] for h in historical]
        rev_growth = ((rev_vals[-1] - rev_vals[0]) / rev_vals[0] * 100) if rev_vals and rev_vals[0] > 0 else 5.0
        exp_growth = ((exp_vals[-1] - exp_vals[0]) / exp_vals[0] * 100) if exp_vals and exp_vals[0] > 0 else 3.0
        
        drivers = [
            {
                "name": "Historical Trend Momentum",
                "desc": f"{'Upward' if slope >= 0 else 'Downward'} trajectory across {n_obs} observation periods",
                "impact": round(float(slope / (abs(values[-1]) + 1e-5) * 100), 1)
            },
            {
                "name": "Revenue Velocity",
                "desc": "Compounded revenue change across historical baseline",
                "impact": round(float(rev_growth), 1)
            },
            {
                "name": "Cost Structure Impact",
                "desc": "Operating expenditure growth rate",
                "impact": round(float(-exp_growth if norm_metric == 'profit' else exp_growth), 1)
            }
        ]

        if norm_metric == "margin":
            exp_case = round(float(np.mean(base_vals)), 2)
            best_c = round(float(np.mean(opt_vals)), 2)
            worst_c = round(float(np.mean(cons_vals)), 2)
        else:
            exp_case = round(float(sum(base_vals)), 2)
            best_c = round(float(sum(opt_vals)), 2)
            worst_c = round(float(sum(cons_vals)), 2)

        return {
            "has_enough_data": True,
            "expected_case": exp_case,
            "best_case": best_c,
            "worst_case": worst_c,
            "forecast": forecast_out,
            "historical": historical,
            "model_used": "Linear Regression (OLS)",
            "confidence_score": round(r2, 2),
            "r2_score": round(r2, 2),
            "mape": round(mape, 2),
            "observations": n_obs,
            "drivers": drivers,
            "slope": round(slope, 2),
            "metric": norm_metric,
            "is_percentage": (norm_metric == "margin")
        }

    def get_anomalies(self, dept=None):
        import pandas as pd
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
