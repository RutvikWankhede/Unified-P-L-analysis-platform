from sqlalchemy import func, or_, case
from sqlalchemy.orm import Session
from models.pl_record import PLRecord
import pandas as pd
import numpy as np

class MetricEngine:
    def __init__(self, db: Session, active_dataset_id: str = None):
        self.db = db
        self.active_dataset_id = active_dataset_id

    def get_active_profile(self):
        query = self._base_query()
        row_count = query.count()
        first_record = query.first()
        
        date_col = "date"
        revenue_col = "revenue"
        expense_col = "expense"
        profit_col = "profit"
        dept_col = "department"
        budget_col = None
        cash_inflow_col = None
        cash_outflow_col = None
        
        if first_record and first_record.dynamic_data:
            dd = first_record.dynamic_data
            keys = list(dd.keys())
            
            def find_match(synonyms):
                for k in keys:
                    k_clean = str(k).strip().lower().replace("_", " ").replace("-", " ")
                    if any(syn == k_clean or syn in k_clean for syn in synonyms):
                        return k
                return None

            date_col = find_match(["posting date", "invoice date", "transaction date", "date", "period", "day", "month", "year"]) or "date"
            revenue_col = find_match(["revenue", "sales", "income", "turnover"]) or "revenue"
            expense_col = find_match(["expense", "cost", "opex", "spend", "expenditure"]) or "expense"
            profit_col = find_match(["net profit", "operating profit", "profit", "net income", "ebit", "p&l", "pnl"]) or "profit"
            dept_col = find_match([
                "department", "dept", "division", "business unit", "cost center", 
                "segment", "category", "region", "branch", "team", "bu"
            ]) or "department"
            budget_col = find_match(["budget amount", "approved budget", "planned budget", "budget", "planned expense", "budgeted amount"])
            cash_inflow_col = find_match(["cash inflow", "cash_inflow", "inflow", "cash_received", "operating_cash_inflow"])
            cash_outflow_col = find_match(["cash outflow", "cash_outflow", "outflow", "cash_paid", "operating_cash_outflow"])
            net_cash_flow_col = find_match(["net cash flow", "net_cash_flow", "cash flow", "cash_flow"])
            
        else:
            net_cash_flow_col = None
        date_stats = query.with_entities(
            func.min(PLRecord.period).label("min_date"),
            func.max(PLRecord.period).label("max_date")
        ).first()
        
        date_min = date_stats.min_date if date_stats else None
        date_max = date_stats.max_date if date_stats else None
        
        # Auto-detect the most appropriate aggregation frequency
        date_frequency = "monthly"
        if date_min and date_max:
            try:
                from datetime import datetime as _dt
                d1 = _dt.strptime(date_min[:10], "%Y-%m-%d")
                d2 = _dt.strptime(date_max[:10], "%Y-%m-%d")
                span_days = (d2 - d1).days
                if span_days <= 30:
                    date_frequency = "daily"
                elif span_days <= 90:
                    date_frequency = "weekly"
                elif span_days <= 730:
                    date_frequency = "monthly"
                elif span_days <= 1825:
                    date_frequency = "quarterly"
                else:
                    date_frequency = "yearly"
            except Exception:
                date_frequency = "monthly"
        
        domains_query = query.with_entities(PLRecord.domain).distinct().all()
        dimension_values = sorted([d[0] for d in domains_query if d[0] and d[0] not in ["All Departments", "Unknown", "All"]])
        
        caps = self.get_capabilities()
        caps["budget"]["available"] = budget_col is not None or caps["budget"]["available"]
        
        # Cash Flow strict rules
        cash_flow_mode = "unavailable"
        actual_cash = False
        if net_cash_flow_col is not None or (cash_inflow_col is not None and cash_outflow_col is not None):
            cash_flow_mode = "actual"
            actual_cash = True
        elif caps["revenue"]["available"] and caps["expense"]["available"]:
            cash_flow_mode = "estimated"
            actual_cash = False
            
        caps["cashFlow"]["available"] = (cash_flow_mode != "unavailable")
        caps["cashFlow"]["mode"] = cash_flow_mode
        
        profile = {
            "dataset_id": self.active_dataset_id or "DEMO-DATASET",
            "row_count": row_count,
            "date_column": date_col,
            "date_frequency": date_frequency,
            "revenue_column": revenue_col,
            "expense_column": expense_col,
            "profit_column": profit_col,
            "department_column": dept_col,
            "budget_column": budget_col,
            "cash_inflow_column": cash_inflow_col,
            "cash_outflow_column": cash_outflow_col,
            "net_cash_flow_column": net_cash_flow_col,
            "dimensions": [dept_col] if dept_col else ["department"],
            "dimension_values": dimension_values,
            "date_min": date_min,
            "date_max": date_max,
            "capabilities": {
                "revenue": caps["revenue"]["available"],
                "expense": caps["expense"]["available"],
                "profit": caps["profit"]["available"],
                "margin": caps["margin"]["available"],
                "department": caps["has_departments"],
                "budget": caps["budget"]["available"],
                "cash_flow": caps["cashFlow"]["available"],
                "cash_flow_mode": cash_flow_mode,
                "forecast": caps["profit"]["available"] and row_count >= 3,
                "anomaly": caps["profit"]["available"] and row_count >= 3
            }
        }
        return profile

    def aggregate_data(self, aggregation="monthly", dept=None):
        query = self._base_query()
        if dept and dept.lower() not in ["all", "all departments", "overall"]:
            query = query.filter(PLRecord.domain == dept)
            
        records = query.all()
        if not records:
            return pd.DataFrame()
            
        rows = []
        for r in records:
            row = {
                "period": r.period,
                "domain": r.domain,
                "line_item": r.line_item,
                "amount": r.amount,
            }
            if r.dynamic_data:
                row.update(r.dynamic_data)
            rows.append(row)
            
        df = pd.DataFrame(rows)
        df["date_parsed"] = pd.to_datetime(df["period"])
        
        profile = self.get_active_profile()
        cash_inflow_col = profile["cash_inflow_column"]
        cash_outflow_col = profile["cash_outflow_column"]
        net_cash_flow_col = profile["net_cash_flow_column"]
        budget_col = profile["budget_column"]
        cash_flow_mode = profile["capabilities"].get("cash_flow_mode", "unavailable")
        
        if "transaction_id" in df.columns:
            raw_df = df.drop_duplicates(subset=["transaction_id"])
        else:
            raw_df = df.drop_duplicates(subset=["period", "domain", "amount", "line_item"])
            
        agg_lower = str(aggregation).lower().replace("_", "-").replace(" ", "-")
        if agg_lower in ["overall", "total", "all"]:
            df["group_period"] = "Overall"
            raw_df["group_period"] = "Overall"
        elif agg_lower in ["daily", "day"]:
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-%m-%d")
            raw_df["group_period"] = raw_df["date_parsed"].dt.strftime("%Y-%m-%d")
        elif agg_lower in ["weekly", "week"]:
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-W%U")
            raw_df["group_period"] = raw_df["date_parsed"].dt.strftime("%Y-W%U")
        elif agg_lower in ["quarterly", "quarter"]:
            df["group_period"] = df["date_parsed"].dt.year.astype(str) + "-Q" + df["date_parsed"].dt.quarter.astype(str)
            raw_df["group_period"] = raw_df["date_parsed"].dt.year.astype(str) + "-Q" + raw_df["date_parsed"].dt.quarter.astype(str)
        elif agg_lower in ["half-yearly", "half_yearly", "half-year", "half yearly", "h1-h2"]:
            half = np.where(df["date_parsed"].dt.month <= 6, "1", "2")
            df["group_period"] = df["date_parsed"].dt.year.astype(str) + "-H" + half
            raw_half = np.where(raw_df["date_parsed"].dt.month <= 6, "1", "2")
            raw_df["group_period"] = raw_df["date_parsed"].dt.year.astype(str) + "-H" + raw_half
        elif agg_lower in ["yearly", "year", "annual"]:
            df["group_period"] = df["date_parsed"].dt.strftime("%Y")
            raw_df["group_period"] = raw_df["date_parsed"].dt.strftime("%Y")
        else:
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-%m")
            raw_df["group_period"] = raw_df["date_parsed"].dt.strftime("%Y-%m")
            
        rev_cond = df["line_item"].str.lower().str.contains("revenue|sales|income", na=False)
        exp_cond = df["line_item"].str.lower().str.contains("expense|cost|opex|salary|salaries", na=False)
        
        rev_group = df[rev_cond].groupby("group_period")["amount"].sum()
        exp_group = df[exp_cond].groupby("group_period")["amount"].sum()
        
        budget_group = pd.Series(dtype=float)
        if budget_col and budget_col in raw_df.columns:
            raw_df[budget_col] = pd.to_numeric(raw_df[budget_col].replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(0.0)
            budget_group = raw_df.groupby("group_period")[budget_col].sum()
            
        cash_in_group = pd.Series(dtype=float)
        if cash_inflow_col and cash_inflow_col in raw_df.columns:
            raw_df[cash_inflow_col] = pd.to_numeric(raw_df[cash_inflow_col].replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(0.0)
            cash_in_group = raw_df.groupby("group_period")[cash_inflow_col].sum()
            
        cash_out_group = pd.Series(dtype=float)
        if cash_outflow_col and cash_outflow_col in raw_df.columns:
            raw_df[cash_outflow_col] = pd.to_numeric(raw_df[cash_outflow_col].replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(0.0)
            cash_out_group = raw_df.groupby("group_period")[cash_outflow_col].sum()
            
        net_cash_group = pd.Series(dtype=float)
        if net_cash_flow_col and net_cash_flow_col in raw_df.columns:
            raw_df[net_cash_flow_col] = pd.to_numeric(raw_df[net_cash_flow_col].replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(0.0)
            net_cash_group = raw_df.groupby("group_period")[net_cash_flow_col].sum()
            
        all_periods = sorted(list(set(df["group_period"])))
        result_rows = []
        for p in all_periods:
            rev = float(rev_group.get(p, 0.0))
            exp = float(exp_group.get(p, 0.0))
            prof = rev - exp
            margin = (prof / rev * 100) if rev > 0 else 0.0
            
            budget = float(budget_group.get(p, 0.0)) if not budget_group.empty else None
            
            # Cash flow rules logic
            net_cash = None
            if cash_flow_mode == "actual":
                if not net_cash_group.empty:
                    net_cash = float(net_cash_group.get(p, 0.0))
                else:
                    cash_in = float(cash_in_group.get(p, 0.0)) if not cash_in_group.empty else 0.0
                    cash_out = float(cash_out_group.get(p, 0.0)) if not cash_out_group.empty else 0.0
                    net_cash = cash_in - cash_out
            elif cash_flow_mode == "estimated":
                net_cash = rev - exp
            
            result_rows.append({
                "period": p,
                "revenue": round(rev, 2),
                "expense": round(exp, 2),
                "profit": round(prof, 2),
                "margin": round(margin, 2),
                "budget": round(budget, 2) if budget is not None else None,
                "net_cash_flow": round(net_cash, 2) if net_cash is not None else None,
                "cash_flow_mode": cash_flow_mode
            })
            
        return pd.DataFrame(result_rows)


    def _base_query(self):
        query = self.db.query(PLRecord)
        if self.active_dataset_id:
            query = query.filter(PLRecord.upload_id == self.active_dataset_id)
        return query

    def get_capabilities(self):
        query = self._base_query()
        first_record = query.first()

        has_revenue = False
        has_expense = False
        has_cogs = False
        has_budget = False
        has_cash_flow = False

        items = query.with_entities(PLRecord.line_item).distinct().all()
        line_items = {item[0] for item in items if item[0]}

        has_revenue = any(any(x in it.lower() for x in ["revenue", "sales", "income"]) for it in line_items)
        has_expense = any(any(x in it.lower() for x in ["expense", "cost", "opex", "spend", "salary", "salaries"]) for it in line_items)
        has_cogs = any("cogs" in it.lower() or "cost of goods" in it.lower() for it in line_items)
        has_budget = any("budget" in it.lower() for it in line_items)
        has_cash_flow = any("cash" in it.lower() or "inflow" in it.lower() or "outflow" in it.lower() for it in line_items)

        if first_record and first_record.dynamic_data:
            dd = first_record.dynamic_data
            keys = [str(k).lower() for k in dd.keys()]

            if not has_revenue:
                has_revenue = any(any(x in k for x in ["revenue", "sales", "income"]) for k in keys)
            if not has_expense:
                has_expense = any(any(x in k for x in ["expense", "cost", "opex", "spend", "salary", "salaries"]) for k in keys)
            if not has_budget:
                has_budget = any("budget" in k for k in keys)
            if not has_cash_flow:
                has_cash_flow = any("cash" in k or "inflow" in k or "outflow" in k for k in keys)
            if not has_cogs:
                has_cogs = any("cogs" in k or "cost of goods" in k for k in keys)

        domains_query = query.with_entities(PLRecord.domain).distinct().all()
        domains = {d[0] for d in domains_query if d[0] and d[0] not in ["All Departments", "Unknown", "All"]}

        return {
            "revenue": {
                "available": has_revenue,
                "source": "Revenue" if has_revenue else None,
                "derived": False
            },
            "expense": {
                "available": has_expense,
                "source": "Expense" if has_expense else None,
                "derived": False
            },
            "profit": {
                "available": has_revenue and has_expense,
                "source": "Revenue - Expense" if (has_revenue and has_expense) else None,
                "derived": True
            },
            "margin": {
                "available": has_revenue and has_expense,
                "source": "Profit / Revenue" if (has_revenue and has_expense) else None,
                "derived": True
            },
            "cashFlow": {
                "available": has_cash_flow,
                "source": "Cash Inflow/Outflow" if has_cash_flow else None
            },
            "budget": {
                "available": has_budget,
                "source": "Budget" if has_budget else None
            },
            "has_departments": len(domains) > 0,
            "has_cash_flow_categories": has_cash_flow,
            "has_budget_data": has_budget,
            "has_cogs_tax_breakdown": has_cogs,
            "available_dimensions": ["department"] if len(domains) > 0 else ["region"]
        }

    def get_kpis(self, filters=None):
        query = self._base_query()
        
        dept_filter = None
        if filters:
            for k, v in filters.items():
                if k == "domain" and v and v.lower() not in ["all", "all departments", "overall"]:
                    dept_filter = v
                    query = query.filter(PLRecord.domain == v)
                elif k == "period" and v:
                    query = query.filter(PLRecord.period == v)

        caps = self.get_capabilities()

        rev_cond = or_(
            PLRecord.line_item.ilike("%revenue%"),
            PLRecord.line_item.ilike("%income%"),
            PLRecord.line_item.ilike("%sales%")
        )
        exp_cond = or_(
            PLRecord.line_item.ilike("%expense%"),
            PLRecord.line_item.ilike("%cost%"),
            PLRecord.line_item.ilike("%opex%"),
            PLRecord.line_item.ilike("%salary%"),
            PLRecord.line_item.ilike("%salaries%")
        )

        total_stats = query.with_entities(
            func.sum(case((rev_cond, PLRecord.amount), else_=0)).label("total_rev"),
            func.sum(case((exp_cond, PLRecord.amount), else_=0)).label("total_exp")
        ).first()

        total_rev = float(total_stats.total_rev or 0) if caps["revenue"]["available"] else None
        total_exp = float(total_stats.total_exp or 0) if caps["expense"]["available"] else None

        profit = None
        profit_margin = None
        if total_rev is not None and total_exp is not None:
            profit = total_rev - total_exp
            profit_margin = (profit / total_rev * 100) if total_rev > 0 else 0
        elif total_rev is not None:
            profit_margin = 100.0

        # Health score
        if profit_margin is not None:
            health_score = 95 if profit_margin > 15 else (75 if profit_margin > 0 else 40)
        else:
            health_score = 80

        profile = self.get_active_profile()
        all_records = query.all()
        seen_txns = set()
        unique_rows = []
        for r in all_records:
            txn_key = None
            if r.dynamic_data:
                txn_key = r.dynamic_data.get("transaction_id")
                if not txn_key:
                    txn_key = (r.period, r.domain, r.amount, r.line_item)
            if txn_key not in seen_txns:
                seen_txns.add(txn_key)
                unique_rows.append(r)

        total_budget = None
        if profile["budget_column"]:
            total_budget = sum(float(r.dynamic_data.get(profile["budget_column"]) or 0.0) for r in unique_rows if r.dynamic_data and r.dynamic_data.get(profile["budget_column"]) is not None)
        else:
            from models.pl_record import DepartmentBudget
            db_budgets = self.db.query(DepartmentBudget).all()
            if db_budgets:
                if dept_filter:
                    total_budget = sum(b.budget_amount for b in db_budgets if b.department.lower() == dept_filter.lower())
                else:
                    total_budget = sum(b.budget_amount for b in db_budgets)

        cash_flow_mode = profile["capabilities"].get("cash_flow_mode", "unavailable")
        net_cash_flow = None
        if cash_flow_mode == "actual":
            if profile.get("net_cash_flow_column"):
                net_cash_flow = sum(float(r.dynamic_data.get(profile["net_cash_flow_column"]) or 0.0) for r in unique_rows if r.dynamic_data and r.dynamic_data.get(profile["net_cash_flow_column"]) is not None)
            else:
                total_cash_in = sum(float(r.dynamic_data.get(profile["cash_inflow_column"]) or 0.0) for r in unique_rows if r.dynamic_data and r.dynamic_data.get(profile["cash_inflow_column"]) is not None)
                total_cash_out = sum(float(r.dynamic_data.get(profile["cash_outflow_column"]) or 0.0) for r in unique_rows if r.dynamic_data and r.dynamic_data.get(profile["cash_outflow_column"]) is not None)
                net_cash_flow = total_cash_in - total_cash_out
        elif cash_flow_mode == "estimated":
            if total_rev is not None and total_exp is not None:
                net_cash_flow = total_rev - total_exp

        # Calculate Trends (PoP Growth %)
        # Get all monthly periods in sorted order
        base_period_query = self._base_query()
        if dept_filter:
            base_period_query = base_period_query.filter(PLRecord.domain == dept_filter)
        distinct_periods = sorted([
            row[0] for row in base_period_query.with_entities(func.substr(PLRecord.period, 1, 7)).distinct().all() if row[0]
        ])

        rev_trend_val = 0.0
        exp_trend_val = 0.0
        profit_trend_val = 0.0
        margin_trend_val = 0.0

        if len(distinct_periods) >= 2:
            curr_p = distinct_periods[-1]
            prev_p = distinct_periods[-2]

            # Query stats for current period
            curr_stats = base_period_query.filter(PLRecord.period.like(f"{curr_p}%")).with_entities(
                func.sum(case((rev_cond, PLRecord.amount), else_=0)).label("rev"),
                func.sum(case((exp_cond, PLRecord.amount), else_=0)).label("exp")
            ).first()

            # Query stats for previous period
            prev_stats = base_period_query.filter(PLRecord.period.like(f"{prev_p}%")).with_entities(
                func.sum(case((rev_cond, PLRecord.amount), else_=0)).label("rev"),
                func.sum(case((exp_cond, PLRecord.amount), else_=0)).label("exp")
            ).first()

            curr_rev = float(curr_stats.rev or 0)
            curr_exp = float(curr_stats.exp or 0)
            curr_prof = curr_rev - curr_exp

            prev_rev = float(prev_stats.rev or 0)
            prev_exp = float(prev_stats.exp or 0)
            prev_prof = prev_rev - prev_exp

            if prev_rev > 0:
                rev_trend_val = round(((curr_rev - prev_rev) / prev_rev) * 100, 2)
            if prev_exp > 0:
                exp_trend_val = round(((curr_exp - prev_exp) / prev_exp) * 100, 2)
            if abs(prev_prof) > 0:
                profit_trend_val = round(((curr_prof - prev_prof) / abs(prev_prof)) * 100, 2)

            curr_margin = (curr_prof / curr_rev * 100) if curr_rev > 0 else 0
            prev_margin = (prev_prof / prev_rev * 100) if prev_rev > 0 else 0
            margin_trend_val = round(curr_margin - prev_margin, 2)

        has_data = ((total_rev or 0) > 0 or (total_exp or 0) > 0 or query.first() is not None)

        return {
            "revenue": round(total_rev, 2) if total_rev is not None else None,
            "expense": round(total_exp, 2) if total_exp is not None else None,
            "profit": round(profit, 2) if profit is not None else None,
            "profit_margin": round(profit_margin, 2) if profit_margin is not None else None,
            "health_score": health_score,
            "risk_score": 100 - health_score,
            "has_data": has_data,
            "budget": round(total_budget, 2) if total_budget is not None else None,
            "cash_flow": round(net_cash_flow, 2) if net_cash_flow is not None else None,
            "cash_flow_mode": cash_flow_mode,
            "trends": {
                "revenue": rev_trend_val,
                "expense": exp_trend_val,
                "profit": profit_trend_val,
                "profit_margin": margin_trend_val
            }
        }

    def get_department_aggregates(self):
        query = self._base_query()
        caps = self.get_capabilities()
        
        rev_cond = or_(
            PLRecord.line_item.ilike("%revenue%"), 
            PLRecord.line_item.ilike("%sales%"),
            PLRecord.line_item.ilike("%income%")
        )
        exp_cond = or_(
            PLRecord.line_item.ilike("%expense%"), 
            PLRecord.line_item.ilike("%cost%"),
            PLRecord.line_item.ilike("%opex%"),
            PLRecord.line_item.ilike("%salary%"),
            PLRecord.line_item.ilike("%salaries%")
        )

        results = query.with_entities(
            PLRecord.domain,
            func.sum(case((rev_cond, PLRecord.amount), else_=0)).label("rev"),
            func.sum(case((exp_cond, PLRecord.amount), else_=0)).label("exp")
        ).group_by(PLRecord.domain).all()

        summary_map = {}
        for domain, rev, exp in results:
            if domain and domain != "Unknown" and domain != "All Departments":
                rev_val = float(rev or 0) if caps["revenue"]["available"] else None
                exp_val = float(exp or 0) if caps["expense"]["available"] else None
                profit_val = None
                margin_val = None
                
                if rev_val is not None and exp_val is not None:
                    profit_val = rev_val - exp_val
                    margin_val = (profit_val / rev_val * 100) if rev_val > 0 else 0
                
                summary_map[domain] = {
                    "department": domain,
                    "revenue": round(rev_val, 2) if rev_val is not None else None,
                    "expense": round(exp_val, 2) if exp_val is not None else None,
                    "profit": round(profit_val, 2) if profit_val is not None else None,
                    "margin": round(margin_val, 2) if margin_val is not None else None
                }
        
        return list(summary_map.values())

    def get_time_series(self, dept=None):
        query = self._base_query()
        if dept and dept.lower() not in ["all", "all departments", "overall"]:
            query = query.filter(PLRecord.domain == dept)

        caps = self.get_capabilities()
        rev_cond = or_(PLRecord.line_item.ilike("%revenue%"), PLRecord.line_item.ilike("%sales%"), PLRecord.line_item.ilike("%income%"))
        exp_cond = or_(PLRecord.line_item.ilike("%expense%"), PLRecord.line_item.ilike("%cost%"), PLRecord.line_item.ilike("%opex%"), PLRecord.line_item.ilike("%salary%"), PLRecord.line_item.ilike("%salaries%"))

        results = query.with_entities(
            func.substr(PLRecord.period, 1, 7).label("month"),
            func.sum(case((rev_cond, PLRecord.amount), else_=0)).label("rev"),
            func.sum(case((exp_cond, PLRecord.amount), else_=0)).label("exp")
        ).group_by(func.substr(PLRecord.period, 1, 7)).order_by(func.substr(PLRecord.period, 1, 7)).all()

        time_series = []
        for month, rev, exp in results:
            if month:
                rev_val = float(rev or 0) if caps["revenue"]["available"] else None
                exp_val = float(exp or 0) if caps["expense"]["available"] else None
                profit_val = None
                if rev_val is not None and exp_val is not None:
                    profit_val = rev_val - exp_val
                time_series.append({
                    "period": month,
                    "revenue": round(rev_val, 2) if rev_val is not None else None,
                    "expense": round(exp_val, 2) if exp_val is not None else None,
                    "profit": round(profit_val, 2) if profit_val is not None else None
                })
        return time_series

    def aggregate_by_dimension(self, aggregation="monthly"):
        query = self._base_query()
        records = query.all()
        if not records:
            return pd.DataFrame()
            
        rows = []
        for r in records:
            rows.append({
                "period": r.period,
                "domain": r.domain,
                "line_item": r.line_item,
                "amount": r.amount
            })
        df = pd.DataFrame(rows)
        df["date_parsed"] = pd.to_datetime(df["period"])
        
        if aggregation == "daily":
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-%m-%d")
        elif aggregation == "weekly":
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-W%U")
        elif aggregation == "quarterly":
            df["group_period"] = df["date_parsed"].dt.year.astype(str) + "-Q" + df["date_parsed"].dt.quarter.astype(str)
        elif aggregation == "half-yearly":
            half = np.where(df["date_parsed"].dt.month <= 6, "1", "2")
            df["group_period"] = df["date_parsed"].dt.year.astype(str) + "-H" + half
        elif aggregation == "yearly":
            df["group_period"] = df["date_parsed"].dt.strftime("%Y")
        else:
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-%m")
            
        rev_cond = df["line_item"].str.lower().str.contains("revenue|sales|income", na=False)
        exp_cond = df["line_item"].str.lower().str.contains("expense|cost|opex|salary|salaries", na=False)
        
        rev_group = df[rev_cond].groupby(["group_period", "domain"])["amount"].sum().reset_index()
        exp_group = df[exp_cond].groupby(["group_period", "domain"])["amount"].sum().reset_index()
        
        merged = pd.merge(rev_group, exp_group, on=["group_period", "domain"], how="outer", suffixes=('_rev', '_exp')).fillna(0.0)
        merged["profit"] = merged["amount_rev"] - merged["amount_exp"]
        return merged

    def get_anomaly_summary(self, period="overall", dept="all"):
        from models.anomaly import Anomaly
        query = self.db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id)
        if self.active_dataset_id:
            query = query.filter(PLRecord.upload_id == self.active_dataset_id)
            
        if dept and dept.lower() not in ["all", "all departments", "overall"]:
            query = query.filter(PLRecord.domain.ilike(dept))
            
        date_stats = self.db.query(
            func.min(PLRecord.period).label("min_date"),
            func.max(PLRecord.period).label("max_date")
        )
        if self.active_dataset_id:
            date_stats = date_stats.filter(PLRecord.upload_id == self.active_dataset_id)
        min_date, max_date = date_stats.first()
        
        p_lower = str(period).lower().replace("_", "-").replace(" ", "-")
        if max_date and p_lower not in ["overall", "all", "total"]:
            if p_lower in ["daily", "day"]:
                query = query.filter(PLRecord.period == max_date[:10])
            elif p_lower in ["weekly", "week"]:
                try:
                    from datetime import datetime, timedelta
                    dt_max = datetime.strptime(max_date[:10], "%Y-%m-%d")
                    dt_start = (dt_max - timedelta(days=7)).strftime("%Y-%m-%d")
                    query = query.filter(PLRecord.period >= dt_start)
                except Exception:
                    query = query.filter(PLRecord.period.like(f"{max_date[:7]}%"))
            elif p_lower in ["monthly", "month"]:
                query = query.filter(PLRecord.period.like(f"{max_date[:7]}%"))
            elif p_lower in ["half-yearly", "half-year", "half yearly", "h1-h2"]:
                yr = max_date[:4]
                month_num = int(max_date[5:7]) if len(max_date) >= 7 else 12
                start_m = "07-01" if month_num > 6 else "01-01"
                query = query.filter(PLRecord.period >= f"{yr}-{start_m}")
            elif p_lower in ["yearly", "year", "annual"]:
                query = query.filter(PLRecord.period.like(f"{max_date[:4]}%"))

        anomalies = query.all()
        total_count = len(anomalies)

        critical_count = sum(1 for a in anomalies if (a.severity or "").lower() == "critical")
        high_count = sum(1 for a in anomalies if (a.severity or "").lower() == "high")
        medium_count = sum(1 for a in anomalies if (a.severity or "").lower() == "medium")
        low_count = sum(1 for a in anomalies if (a.severity or "").lower() == "low")

        unclassified = total_count - (critical_count + high_count + medium_count + low_count)
        if unclassified > 0:
            medium_count += unclassified

        severities = [
            {"name": "Critical", "count": critical_count, "color": "#EF4444", "percentage": round((critical_count/total_count*100), 1) if total_count > 0 else 0},
            {"name": "High", "count": high_count, "color": "#F97316", "percentage": round((high_count/total_count*100), 1) if total_count > 0 else 0},
            {"name": "Medium", "count": medium_count, "color": "#FBBF24", "percentage": round((medium_count/total_count*100), 1) if total_count > 0 else 0},
            {"name": "Low", "count": low_count, "color": "#38BDF8", "percentage": round((low_count/total_count*100), 1) if total_count > 0 else 0},
        ]

        return {
            "period": period,
            "department": dept,
            "total_anomalies": total_count,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "severities": severities,
            "has_data": total_count > 0
        }

    def get_financial_distribution(self, metric="expense", dept="all"):
        dept_colors = {
            "Sales": "#3B82F6",
            "Operations": "#10B981",
            "Finance": "#F59E0B",
            "Human Resources": "#EC4899",
            "HR": "#EC4899",
            "Engineering": "#8B5CF6",
            "IT": "#8B5CF6",
            "Technology": "#8B5CF6",
            "Information Technology": "#8B5CF6",
            "Marketing": "#06B6D4",
            "R&D": "#6366F1",
            "Research & Development": "#6366F1",
            "Legal": "#64748B",
            "Logistics": "#14B8A6",
            "Supply Chain": "#14B8A6",
            "Support": "#F97316",
            "Customer Support": "#F97316",
            "Commercial": "#0284C7",
            "Procurement": "#84CC16",
            "Executive": "#4F46E5",
            "Administration": "#475569",
        }
        palette = [
            "#3B82F6", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6",
            "#06B6D4", "#6366F1", "#F97316", "#14B8A6", "#0284C7",
            "#84CC16", "#A855F7", "#E11D48", "#64748B", "#D97706"
        ]

        def get_color(name, idx):
            if name in dept_colors:
                return dept_colors[name]
            for k, v in dept_colors.items():
                if k.lower() == name.lower():
                    return v
            return palette[idx % len(palette)]

        m_key = str(metric).lower().replace("_", " ").replace("-", " ")
        is_revenue = any(w in m_key for w in ["revenue", "sales", "income", "turnover"])
        is_profit = any(w in m_key for w in ["profit", "net profit", "ebit", "gain", "earnings"]) and not ("margin" in m_key or "%" in m_key or "pct" in m_key)
        is_margin = any(w in m_key for w in ["margin", "%", "pct", "net margin"])
        is_expense = not (is_revenue or is_profit or is_margin)

        is_all_depts = not dept or dept.lower() in ["all", "all departments", "overall", "total"]

        query = self._base_query()
        if not is_all_depts:
            query = query.filter(PLRecord.domain == dept)

        if is_all_depts:
            dept_aggs = self.get_department_aggregates()
            if not dept_aggs:
                return {"has_data": False, "metric": metric, "department": dept, "total_amount": 0.0, "categories": []}

            cat_map = {}
            for d in dept_aggs:
                d_name = d["department"]
                if is_revenue:
                    val = float(d.get("revenue") or 0.0)
                elif is_profit:
                    val = float(d.get("profit") or 0.0)
                    if val < 0:
                        val = 0.0
                elif is_margin:
                    val = float(d.get("margin") or 0.0)
                    if val < 0:
                        val = 0.0
                else:  # expense
                    val = float(d.get("expense") or 0.0)

                if val > 0:
                    cat_map[d_name] = val

            total_val = sum(cat_map.values())
            if total_val <= 0:
                return {"has_data": False, "metric": metric, "department": dept, "total_amount": 0.0, "categories": []}

            sorted_cats = sorted(cat_map.items(), key=lambda x: x[1], reverse=True)
            categories = []
            if len(sorted_cats) > 8:
                top_cats = sorted_cats[:7]
                other_sum = sum(v for _, v in sorted_cats[7:])
                for idx, (name, amt) in enumerate(top_cats):
                    pct = round((amt / total_val) * 100, 1)
                    categories.append({
                        "name": name,
                        "amount": round(amt, 2),
                        "percentage": pct,
                        "color": get_color(name, idx),
                        "is_margin": is_margin
                    })
                if other_sum > 0:
                    categories.append({
                        "name": "Others",
                        "amount": round(other_sum, 2),
                        "percentage": round((other_sum / total_val) * 100, 1),
                        "color": "#1E293B",
                        "is_margin": is_margin
                    })
            else:
                for idx, (name, amt) in enumerate(sorted_cats):
                    pct = round((amt / total_val) * 100, 1)
                    categories.append({
                        "name": name,
                        "amount": round(amt, 2),
                        "percentage": pct,
                        "color": get_color(name, idx),
                        "is_margin": is_margin
                    })

            return {
                "has_data": True,
                "metric": metric,
                "department": dept,
                "total_amount": round(total_val, 2),
                "is_percentage": is_margin,
                "categories": categories
            }
        else:
            records = query.all()
            if not records:
                return {"has_data": False, "metric": metric, "department": dept, "total_amount": 0.0, "categories": []}

            rev_cond = lambda li: any(w in (li or "").lower() for w in ["revenue", "sales", "income"])
            exp_cond = lambda li: any(w in (li or "").lower() for w in ["expense", "cost", "opex", "salary", "salaries"])

            cat_map = {}
            for r in records:
                li = str(r.line_item or "General").strip()
                amt = float(r.amount or 0.0)

                channel = r.dynamic_data.get("Channel") if r.dynamic_data else None
                cat_label = channel if (channel and channel != "None") else li

                if is_revenue:
                    if rev_cond(r.line_item) or (r.dynamic_data and "Revenue" in r.dynamic_data and not exp_cond(r.line_item)):
                        cat_map[cat_label] = cat_map.get(cat_label, 0.0) + amt
                elif is_profit:
                    if rev_cond(r.line_item):
                        cat_map[cat_label] = cat_map.get(cat_label, 0.0) + amt
                    elif exp_cond(r.line_item):
                        cat_map[cat_label] = cat_map.get(cat_label, 0.0) - amt
                elif is_margin:
                    cat_map[cat_label] = cat_map.get(cat_label, 0.0) + amt
                else:  # expense
                    if exp_cond(r.line_item) or (r.dynamic_data and "Expense" in r.dynamic_data and not rev_cond(r.line_item)):
                        cat_map[cat_label] = cat_map.get(cat_label, 0.0) + amt

            valid_cats = {k: v for k, v in cat_map.items() if v > 0}
            if not valid_cats:
                total_dept_amt = sum(abs(float(r.amount or 0.0)) for r in records)
                valid_cats = {f"{dept} {metric.capitalize()}": total_dept_amt}

            total_val = sum(valid_cats.values())
            sorted_cats = sorted(valid_cats.items(), key=lambda x: x[1], reverse=True)

            categories = []
            if len(sorted_cats) > 8:
                top_cats = sorted_cats[:7]
                other_sum = sum(v for _, v in sorted_cats[7:])
                for idx, (name, amt) in enumerate(top_cats):
                    categories.append({
                        "name": name,
                        "amount": round(amt, 2),
                        "percentage": round((amt / total_val) * 100, 1) if total_val > 0 else 0,
                        "color": palette[idx % len(palette)],
                        "is_margin": is_margin
                    })
                if other_sum > 0:
                    categories.append({
                        "name": "Others",
                        "amount": round(other_sum, 2),
                        "percentage": round((other_sum / total_val) * 100, 1) if total_val > 0 else 0,
                        "color": "#1E293B",
                        "is_margin": is_margin
                    })
            else:
                for idx, (name, amt) in enumerate(sorted_cats):
                    categories.append({
                        "name": name,
                        "amount": round(amt, 2),
                        "percentage": round((amt / total_val) * 100, 1) if total_val > 0 else 0,
                        "color": palette[idx % len(palette)],
                        "is_margin": is_margin
                    })

            return {
                "has_data": True,
                "metric": metric,
                "department": dept,
                "total_amount": round(total_val, 2),
                "is_percentage": is_margin,
                "categories": categories
            }

    def get_expense_distribution(self, dept="all", metric="expense"):
        return self.get_financial_distribution(metric=metric, dept=dept)

    def get_department_performance(self, metric="profit", limit="top5"):
        dept_aggs = self.get_department_aggregates()
        items = []
        for d in dept_aggs:
            dept_name = d["department"]
            rev = d.get("revenue") or 0.0
            exp = d.get("expense") or 0.0
            prof = d.get("profit") if d.get("profit") is not None else (rev - exp)
            margin = d.get("margin") if d.get("margin") is not None else ((prof / rev * 100) if rev > 0 else 0.0)

            m_key = metric.lower().replace("_", " ").replace("-", " ")
            if "expense" in m_key or "cost" in m_key:
                val = exp
            elif "revenue" in m_key or "sales" in m_key or "income" in m_key:
                val = rev
            elif "margin" in m_key or "%" in m_key or "pct" in m_key:
                val = margin
            else:
                val = prof

            items.append({
                "department": dept_name,
                "value": round(val, 2),
                "revenue": round(rev, 2),
                "expense": round(exp, 2),
                "profit": round(prof, 2),
                "margin_pct": round(margin, 2),
            })

        items.sort(key=lambda x: x["value"], reverse=True)

        limit_lower = str(limit).lower()
        if limit_lower in ["top5", "5", "top 5"]:
            items = items[:5]
        elif limit_lower in ["top10", "10", "top 10"]:
            items = items[:10]

        return {
            "metric": metric,
            "limit": limit,
            "departments": [it["department"] for it in items],
            "values": [it["value"] for it in items],
            "items": items
        }

    def get_budget_vs_actual(self, dept="all"):
        from models.pl_record import DepartmentBudget, PLRecord

        profile = self.get_active_profile()
        budget_col = profile.get("budget_column")
        budgets_db = {}
        try:
            budgets_db = {b.department.lower(): b.budget_amount for b in self.db.query(DepartmentBudget).all() if b.budget_amount and b.budget_amount > 0}
        except Exception:
            budgets_db = {}

        base_query = self.db.query(PLRecord)
        if self.active_dataset_id:
            base_query = base_query.filter(PLRecord.upload_id == self.active_dataset_id)
        records = base_query.all()

        seen_txns = set()
        dept_map = {}
        has_budget_col_data = False

        for r in records:
            txn_key = r.dynamic_data.get("Transaction_ID") if r.dynamic_data else None
            if not txn_key:
                txn_key = (r.period, r.domain, r.amount, r.line_item)
            if txn_key not in seen_txns:
                seen_txns.add(txn_key)
                d_name = r.domain or "General"
                if d_name not in dept_map:
                    dept_map[d_name] = {"actual": 0.0, "budget": 0.0}

                # Extract Expense
                exp_val = 0.0
                if r.dynamic_data and "Expense" in r.dynamic_data and r.dynamic_data["Expense"] is not None:
                    try:
                        exp_val = float(r.dynamic_data["Expense"])
                    except (ValueError, TypeError):
                        exp_val = 0.0
                elif "exp" in (r.line_item or "").lower() or "cost" in (r.line_item or "").lower():
                    exp_val = float(r.amount or 0.0)

                dept_map[d_name]["actual"] += exp_val

                # Extract Budget
                if budget_col and r.dynamic_data and budget_col in r.dynamic_data and r.dynamic_data[budget_col] is not None:
                    try:
                        bgt_val = float(r.dynamic_data[budget_col])
                        dept_map[d_name]["budget"] += bgt_val
                        has_budget_col_data = True
                    except (ValueError, TypeError):
                        pass

        has_any_budget = has_budget_col_data or bool(budgets_db)
        results = []
        for d_name, vals in dept_map.items():
            if dept and dept.lower() not in ["all", "all departments", "overall"] and d_name.lower() != dept.lower():
                continue

            actual_exp = round(vals["actual"], 2)
            if has_budget_col_data:
                allocated_budget = round(vals["budget"], 2)
            elif d_name.lower() in budgets_db:
                allocated_budget = round(budgets_db[d_name.lower()], 2)
            else:
                allocated_budget = 0.0

            variance = round(actual_exp - allocated_budget, 2)
            variance_pct = round((variance / allocated_budget * 100), 1) if allocated_budget > 0 else 0.0
            status = "Over Budget" if variance > 0 else ("Under Budget" if variance < 0 else "On Track")

            results.append({
                "department": d_name,
                "actual": actual_exp,
                "budget": allocated_budget,
                "variance": variance,
                "variance_pct": variance_pct,
                "status": status
            })

        results.sort(key=lambda x: x["actual"], reverse=True)
        total_actual = sum(it["actual"] for it in results)
        total_budget = sum(it["budget"] for it in results)
        total_var = round(total_actual - total_budget, 2)
        total_var_pct = round((total_var / total_budget * 100), 1) if total_budget > 0 else 0.0

        return {
            "department": dept,
            "has_data": has_any_budget and len(results) > 0,
            "total_actual": total_actual,
            "total_budget": total_budget,
            "total_variance": total_var,
            "total_variance_pct": total_var_pct,
            "items": results
        }


