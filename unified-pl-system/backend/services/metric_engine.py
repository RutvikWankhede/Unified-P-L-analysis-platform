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
            
        if aggregation == "daily":
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-%m-%d")
            raw_df["group_period"] = raw_df["date_parsed"].dt.strftime("%Y-%m-%d")
        elif aggregation == "weekly":
            df["group_period"] = df["date_parsed"].dt.strftime("%Y-W%U")
            raw_df["group_period"] = raw_df["date_parsed"].dt.strftime("%Y-W%U")
        elif aggregation == "quarterly":
            df["group_period"] = df["date_parsed"].dt.year.astype(str) + "-Q" + df["date_parsed"].dt.quarter.astype(str)
            raw_df["group_period"] = raw_df["date_parsed"].dt.year.astype(str) + "-Q" + raw_df["date_parsed"].dt.quarter.astype(str)
        elif aggregation == "half-yearly":
            half = np.where(df["date_parsed"].dt.month <= 6, "1", "2")
            df["group_period"] = df["date_parsed"].dt.year.astype(str) + "-H" + half
            raw_half = np.where(raw_df["date_parsed"].dt.month <= 6, "1", "2")
            raw_df["group_period"] = raw_df["date_parsed"].dt.year.astype(str) + "-H" + raw_half
        elif aggregation == "yearly":
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
