"""
copilot_agent.py - Deterministic Financial Intelligence Copilot
==============================================================
Production-grade analytics and reasoning engine for enterprise financial data.
Follows the architecture:
User Question -> Structured Intent Detection -> Analytics Query -> Deterministic Calculation -> Verified Result -> Grounded Explanation.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from config import settings
from models.pl_record import PLRecord, DepartmentBudget
from models.anomaly import Anomaly

# In-memory session context for multi-turn conversation memory
_SESSION_MEMORY: Dict[str, Dict[str, Any]] = {}

def format_inr(val: Optional[float]) -> str:
    """Format numeric values into standard Indian Rupee units (Cr, L, K) or ₹."""
    if val is None:
        return "N/A"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 10_000_000:
        return f"{sign}₹{abs_val / 10_000_000:.2f} Cr"
    elif abs_val >= 100_000:
        return f"{sign}₹{abs_val / 100_000:.2f} L"
    elif abs_val >= 1_000:
        return f"{sign}₹{abs_val / 1_000:.1f} K"
    return f"{sign}₹{abs_val:,.2f}"

def get_financial_context_and_calc(db: Session, session_id: str = "default") -> Dict[str, Any]:
    """
    Extract canonical data from the active dataset and calculate all department & enterprise metrics.
    """
    from routers.datasets_router import get_active_dataset, get_active_dataset_id
    from services.metric_engine import MetricEngine
    from services.analytics_engine import AnalyticsEngine

    active_info = get_active_dataset(db)
    active_id = get_active_dataset_id(db)
    dataset_name = active_info.get("filename", "Active Dataset") if active_info else "Active Dataset"

    me = MetricEngine(db, active_id)
    summary_df = me.aggregate_data("monthly", dept=None)

    # All distinct departments
    dept_query = db.query(PLRecord.domain).distinct()
    if active_id:
        dept_query = dept_query.filter(PLRecord.upload_id == active_id)
    all_depts = sorted([d[0] for d in dept_query.all() if d[0] and d[0] not in ["All Departments", "Unknown", "All"]])

    # Enterprise Totals
    if not summary_df.empty:
        tot_rev = float(summary_df["revenue"].sum()) if "revenue" in summary_df.columns else 0.0
        tot_exp = float(summary_df["expense"].sum()) if "expense" in summary_df.columns else 0.0
    else:
        tot_rev = 0.0
        tot_exp = 0.0
    tot_prof = tot_rev - tot_exp
    tot_margin = (tot_prof / tot_rev * 100) if tot_rev > 0 else 0.0

    # Department Metrics
    dept_metrics: Dict[str, Dict[str, Any]] = {}
    for d in all_depts:
        d_df = me.aggregate_data("monthly", dept=d)
        d_rev = float(d_df["revenue"].sum()) if not d_df.empty and "revenue" in d_df.columns else 0.0
        d_exp = float(d_df["expense"].sum()) if not d_df.empty and "expense" in d_df.columns else 0.0
        d_prof = d_rev - d_exp
        d_margin = (d_prof / d_rev * 100) if d_rev > 0 else 0.0

        # Department budget & variance
        budget_obj = db.query(DepartmentBudget).filter(DepartmentBudget.department == d).first()
        budget_amt = budget_obj.budget_amount if budget_obj else 0.0
        variance = d_exp - budget_amt
        var_pct = ((d_exp - budget_amt) / budget_amt * 100) if budget_amt > 0 else 0.0

        # Anomalies for department
        anom_q = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id)
        if active_id:
            anom_q = anom_q.filter(PLRecord.upload_id == active_id)
        anom_dept = anom_q.filter(PLRecord.domain == d).all()
        crit_count = sum(1 for a in anom_dept if (a.severity or "").lower() == "critical")
        high_count = sum(1 for a in anom_dept if (a.severity or "").lower() == "high")
        med_count = sum(1 for a in anom_dept if (a.severity or "").lower() == "medium")
        low_count = sum(1 for a in anom_dept if (a.severity or "").lower() == "low")

        dept_metrics[d] = {
            "department": d,
            "revenue": d_rev,
            "expense": d_exp,
            "profit": d_prof,
            "margin": d_margin,
            "budget": budget_amt,
            "variance": variance,
            "variance_pct": var_pct,
            "anomalies_count": len(anom_dept),
            "critical_anomalies": crit_count,
            "high_anomalies": high_count,
            "medium_anomalies": med_count,
            "low_anomalies": low_count,
        }

    # Enterprise Anomalies
    all_anom_q = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id)
    if active_id:
        all_anom_q = all_anom_q.filter(PLRecord.upload_id == active_id)
    all_anomalies = all_anom_q.all()
    tot_anomalies = len(all_anomalies)
    tot_crit = sum(1 for a in all_anomalies if (a.severity or "").lower() == "critical")
    tot_high = sum(1 for a in all_anomalies if (a.severity or "").lower() == "high")
    tot_med = sum(1 for a in all_anomalies if (a.severity or "").lower() == "medium")
    tot_low = sum(1 for a in all_anomalies if (a.severity or "").lower() == "low")

    # Forecast baseline
    ae = AnalyticsEngine(me)
    fc_res = ae.get_forecast(dept="Overall", metric="profit", n_forecast=12, agg="monthly")

    # Time series / line item drivers
    records_query = db.query(PLRecord)
    if active_id:
        records_query = records_query.filter(PLRecord.upload_id == active_id)
    all_records = records_query.all()

    # Top expense categories / line items
    exp_by_item: Dict[str, float] = {}
    for r in all_records:
        if r.line_item and r.amount:
            item_name = r.line_item.strip()
            if r.amount < 0 or any(w in item_name.lower() for w in ["exp", "cost", "fee", "salary", "rent", "travel", "tax", "deprec", "interest", "admin", "util", "market"]):
                exp_by_item[item_name] = exp_by_item.get(item_name, 0.0) + abs(r.amount)

    top_expenses = sorted(exp_by_item.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "dataset_name": dataset_name,
        "dataset_id": active_id,
        "enterprise": {
            "revenue": tot_rev,
            "expense": tot_exp,
            "profit": tot_prof,
            "margin": tot_margin,
            "total_anomalies": tot_anomalies,
            "critical_anomalies": tot_crit,
            "high_anomalies": tot_high,
            "medium_anomalies": tot_med,
            "low_anomalies": tot_low,
        },
        "departments": dept_metrics,
        "top_expenses": top_expenses,
        "forecast": fc_res,
        "summary_df": summary_df,
    }

def route_and_calculate_answer(db: Session, question: str, session_id: str = "default") -> str:
    """
    Deterministic question interpretation & mathematical calculation.
    """
    ctx = get_financial_context_and_calc(db, session_id)
    ent = ctx["enterprise"]
    depts: Dict[str, Dict[str, Any]] = ctx["departments"]
    q_clean = question.strip()
    q_lower = q_clean.lower()

    global _SESSION_MEMORY
    session_ctx = _SESSION_MEMORY.get(session_id, {})

    # Check for unavailable / out-of-scope metrics
    unsupported_terms = [
        "customer satisfaction", "csat", "nps", "headcount", "turnover", "attrition",
        "stock price", "share price", "crypto", "bitcoin", "weather", "temperature",
        "server uptime", "latencies", "bugs", "github"
    ]
    for term in unsupported_terms:
        if term in q_lower:
            return f"I can't answer that from the current dataset because **{term}** is not available in the active financial records."

    # Identify all mentioned departments
    matched_depts = []
    for d_name in depts.keys():
        if d_name.lower() in q_lower or (d_name.lower() == "human resources" and "hr" in q_lower.split()):
            matched_depts.append(d_name)

    # Conversation pronoun resolution ("it", "they", "compare with ...")
    last_dept = session_ctx.get("last_department")
    if not matched_depts and last_dept and any(w in q_lower for w in [" it", " this", " that", "they", "its", "why"]):
        matched_depts = [last_dept]

    # ─────────────────────────────────────────────────────────────
    # CASE 1: MULTI-OBJECTIVE — PROFIT + ANOMALIES
    # e.g., "which department has best profit and least anomalies",
    #       "highest profit and lowest anomalies", "high profit and low risk"
    # ─────────────────────────────────────────────────────────────
    has_profit_goal = any(w in q_lower for w in ["profit", "profitable", "net profit", "margin"])
    has_anomaly_goal = any(w in q_lower for w in ["anomal", "outlier", "risk"])
    is_multi_condition = (" and " in q_lower or " but " in q_lower or " with " in q_lower or " relative to " in q_lower) and has_profit_goal and has_anomaly_goal

    if is_multi_condition:
        if not depts:
            return "No department data is available in the current dataset."

        # Ranks: Sort by profit desc (rank 1 = highest), sort by anomalies asc (rank 1 = least)
        sorted_by_profit = sorted(depts.values(), key=lambda x: x["profit"], reverse=True)
        sorted_by_least_anom = sorted(depts.values(), key=lambda x: x["anomalies_count"])
        sorted_by_most_anom = sorted(depts.values(), key=lambda x: x["anomalies_count"], reverse=True)

        profit_leader = sorted_by_profit[0]
        least_anom_leader = sorted_by_least_anom[0]
        most_anom_leader = sorted_by_most_anom[0]

        # Check if user asked for "high profit but high anomalies"
        wants_high_anom = any(w in q_lower for w in ["most anomalies", "high anomalies", "highest anomalies"])

        if wants_high_anom:
            _SESSION_MEMORY[session_id] = {"last_department": profit_leader["department"], "last_intent": "multi_condition"}
            return (
                f"**Department Profitability vs. High Anomaly Risk**:\n\n"
                f"• **Top Profit Department**: **{profit_leader['department']}** with {format_inr(profit_leader['profit'])} Net Profit and **{profit_leader['anomalies_count']}** anomalies.\n"
                f"• **Highest Anomaly Department**: **{most_anom_leader['department']}** with **{most_anom_leader['anomalies_count']}** anomalies ({most_anom_leader['critical_anomalies']} critical) and {format_inr(most_anom_leader['profit'])} Net Profit.\n\n"
                f"**Comparison Table**:\n\n"
                f"| Department | Net Profit | Profit Margin | Anomalies Count | Critical Anomalies |\n"
                f"| :--- | :--- | :--- | :--- | :--- |\n"
                f"| **{profit_leader['department']}** | {format_inr(profit_leader['profit'])} | {profit_leader['margin']:.1f}% | {profit_leader['anomalies_count']} | {profit_leader['critical_anomalies']} |\n"
                f"| **{most_anom_leader['department']}** | {format_inr(most_anom_leader['profit'])} | {most_anom_leader['margin']:.1f}% | {most_anom_leader['anomalies_count']} | {most_anom_leader['critical_anomalies']} |"
            )

        # User wants "best/highest profit and least/lowest anomalies"
        _SESSION_MEMORY[session_id] = {"last_department": profit_leader["department"], "last_intent": "multi_condition"}

        # Compute combined score (profit rank + anomaly rank, lower is better)
        profit_rank_map = {d["department"]: i + 1 for i, d in enumerate(sorted_by_profit)}
        anom_rank_map = {d["department"]: i + 1 for i, d in enumerate(sorted_by_least_anom)}

        combined_scores = []
        for d_name, d_data in depts.items():
            p_rank = profit_rank_map[d_name]
            a_rank = anom_rank_map[d_name]
            combined_scores.append({
                "department": d_name,
                "profit": d_data["profit"],
                "margin": d_data["margin"],
                "anomalies": d_data["anomalies_count"],
                "anomalies_count": d_data["anomalies_count"],
                "p_rank": p_rank,
                "a_rank": a_rank,
                "combined_score": p_rank + a_rank
            })

        combined_scores = sorted(combined_scores, key=lambda x: x["combined_score"])
        best_overall = combined_scores[0]

        if profit_leader["department"] == least_anom_leader["department"]:
            return (
                f"**{profit_leader['department']}** has both the **highest net profit** and the **fewest anomalies** in the organization.\n\n"
                f"• **Net Profit**: {format_inr(profit_leader['profit'])}\n"
                f"• **Operating Margin**: {profit_leader['margin']:.1f}%\n"
                f"• **Total Anomalies**: {profit_leader['anomalies_count']}\n"
                f"• **Profit Rank**: #1\n"
                f"• **Anomaly Rank**: #1 (Lowest)\n\n"
                f"**Why**: {profit_leader['department']} satisfies both optimization criteria simultaneously."
            )
        else:
            return (
                f"No single department simultaneously leads both metrics. However, **{profit_leader['department']}** delivers the **highest net profit**, while **{least_anom_leader['department']}** has the **fewest anomalies**.\n\n"
                f"• **Highest Net Profit**: **{profit_leader['department']}** ({format_inr(profit_leader['profit'])}, {profit_leader['anomalies_count']} anomalies)\n"
                f"• **Fewest Anomalies**: **{least_anom_leader['department']}** ({least_anom_leader['anomalies_count']} anomalies, {format_inr(least_anom_leader['profit'])} Net Profit)\n"
                f"• **Best Combined Balance**: **{best_overall['department']}** (Profit Rank #{best_overall['p_rank']}, Anomaly Rank #{best_overall['a_rank']})\n\n"
                f"**Department Breakdown**:\n\n"
                f"| Department | Net Profit | Margin | Anomalies | Profit Rank | Anomaly Rank |\n"
                f"| :--- | :--- | :--- | :--- | :--- | :--- |\n"
                f"| **{profit_leader['department']}** | {format_inr(profit_leader['profit'])} | {profit_leader['margin']:.1f}% | {profit_leader['anomalies_count']} | #1 | #{anom_rank_map[profit_leader['department']]} |\n"
                f"| **{least_anom_leader['department']}** | {format_inr(least_anom_leader['profit'])} | {least_anom_leader['margin']:.1f}% | {least_anom_leader['anomalies_count']} | #{profit_rank_map[least_anom_leader['department']]} | #1 |\n"
                f"| **{best_overall['department']}** | {format_inr(best_overall['profit'])} | {best_overall['margin']:.1f}% | {best_overall['anomalies_count']} | #{best_overall['p_rank']} | #{best_overall['a_rank']} |"
            )

    # ─────────────────────────────────────────────────────────────
    # CASE 2: TOP N DEPARTMENTS BY NET PROFIT / REVENUE / EXPENSE
    # e.g., "show top 5 departments by net profit", "top 3 departments"
    # ─────────────────────────────────────────────────────────────
    top_n_match = re.search(r"top\s*(\d+)", q_lower)
    if top_n_match or ("top departments" in q_lower or "rank departments" in q_lower or "ranking of departments" in q_lower):
        n = int(top_n_match.group(1)) if top_n_match else 5
        sorted_depts = sorted(depts.values(), key=lambda x: x["profit"], reverse=True)[:n]
        _SESSION_MEMORY[session_id] = {"last_department": sorted_depts[0]["department"] if sorted_depts else None, "last_intent": "ranking"}

        rows = []
        for idx, d in enumerate(sorted_depts, 1):
            rows.append(f"| #{idx} | **{d['department']}** | {format_inr(d['profit'])} | {d['margin']:.1f}% | {format_inr(d['revenue'])} | {format_inr(d['expense'])} | {d['anomalies_count']} |")

        table_str = "\n".join(rows)
        return (
            f"**Top {len(sorted_depts)} Departments by Net Profit**:\n\n"
            f"| Rank | Department | Net Profit | Margin | Revenue | Expenses | Anomalies |\n"
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            f"{table_str}\n\n"
            f"**{sorted_depts[0]['department']}** leads with {format_inr(sorted_depts[0]['profit'])}, followed by **{sorted_depts[1]['department'] if len(sorted_depts) > 1 else 'none'}**."
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 3: PROFITABILITY — HIGHEST / LOWEST PROFIT
    # ─────────────────────────────────────────────────────────────
    is_profit_query = any(w in q_lower for w in ["profit", "profitable", "net profit", "bottom line"])
    is_least_profit = any(w in q_lower for w in ["lowest profit", "least profitable", "minimum profit", "worst profit", "lowest net profit", "least profit"])
    is_highest_profit = any(w in q_lower for w in ["highest profit", "most profitable", "maximum profit", "best profit", "top profit", "highest net profit", "best performing"])

    if is_least_profit:
        sorted_depts = sorted(depts.values(), key=lambda x: x["profit"])
        lowest = sorted_depts[0]
        _SESSION_MEMORY[session_id] = {"last_department": lowest["department"], "last_intent": "profitability"}
        return (
            f"**{lowest['department']}** currently has the **lowest net profit** in the organization:\n\n"
            f"• **Net Profit**: {format_inr(lowest['profit'])}\n"
            f"• **Revenue**: {format_inr(lowest['revenue'])}\n"
            f"• **Expenses**: {format_inr(lowest['expense'])}\n"
            f"• **Operating Margin**: {lowest['margin']:.1f}%\n"
            f"• **Anomalies**: {lowest['anomalies_count']}\n\n"
            f"**Context**: {lowest['department']} generates {format_inr(lowest['revenue'])} revenue against {format_inr(lowest['expense'])} in operating expenses."
        )

    if is_highest_profit:
        sorted_depts = sorted(depts.values(), key=lambda x: x["profit"], reverse=True)
        top = sorted_depts[0]
        second = sorted_depts[1] if len(sorted_depts) > 1 else None
        _SESSION_MEMORY[session_id] = {"last_department": top["department"], "last_intent": "profitability"}
        resp = (
            f"**{top['department']}** is currently the **most profitable department** in the enterprise.\n\n"
            f"• **Net Profit**: {format_inr(top['profit'])}\n"
            f"• **Operating Margin**: {top['margin']:.1f}%\n"
            f"• **Revenue**: {format_inr(top['revenue'])}\n"
            f"• **Expenses**: {format_inr(top['expense'])}\n"
            f"• **Anomalies**: {top['anomalies_count']}\n"
        )
        if second:
            resp += f"\n**{second['department']}** ranks second with {format_inr(second['profit'])} Net Profit ({second['margin']:.1f}% margin)."
        return resp

    # ─────────────────────────────────────────────────────────────
    # CASE 4: REVENUE — HIGHEST / LOWEST REVENUE
    # ─────────────────────────────────────────────────────────────
    is_rev_query = any(w in q_lower for w in ["revenue", "sales", "topline", "top line", "gross income"])
    is_highest_rev = any(w in q_lower for w in ["highest revenue", "most revenue", "top revenue", "maximum revenue", "best revenue", "largest revenue"])
    is_lowest_rev = any(w in q_lower for w in ["lowest revenue", "least revenue", "minimum revenue", "smallest revenue"])

    if is_highest_rev:
        sorted_by_rev = sorted(depts.values(), key=lambda x: x["revenue"], reverse=True)
        top_rev = sorted_by_rev[0]
        second_rev = sorted_by_rev[1] if len(sorted_by_rev) > 1 else None
        _SESSION_MEMORY[session_id] = {"last_department": top_rev["department"], "last_intent": "revenue"}
        resp = (
            f"**{top_rev['department']}** generates the **highest revenue** across the organization.\n\n"
            f"• **Total Revenue**: {format_inr(top_rev['revenue'])}\n"
            f"• **Expenses**: {format_inr(top_rev['expense'])}\n"
            f"• **Net Profit**: {format_inr(top_rev['profit'])}\n"
            f"• **Margin**: {top_rev['margin']:.1f}%\n"
        )
        if second_rev:
            resp += f"\n**{second_rev['department']}** ranks second in revenue at {format_inr(second_rev['revenue'])}."
        return resp

    if is_lowest_rev:
        sorted_by_rev = sorted(depts.values(), key=lambda x: x["revenue"])
        low_rev = sorted_by_rev[0]
        _SESSION_MEMORY[session_id] = {"last_department": low_rev["department"], "last_intent": "revenue"}
        return (
            f"**{low_rev['department']}** has the **lowest revenue** in the organization:\n\n"
            f"• **Total Revenue**: {format_inr(low_rev['revenue'])}\n"
            f"• **Expenses**: {format_inr(low_rev['expense'])}\n"
            f"• **Net Profit**: {format_inr(low_rev['profit'])}\n"
            f"• **Margin**: {low_rev['margin']:.1f}%\n"
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 5: EXPENSES — HIGHEST / LOWEST EXPENSES
    # ─────────────────────────────────────────────────────────────
    is_exp_query = any(w in q_lower for w in ["expense", "expenses", "cost", "costs", "spending", "spend", "opex"])
    is_highest_exp = any(w in q_lower for w in ["highest expense", "highest cost", "most expense", "most spend", "maximum expense", "biggest expense", "highest spending"])
    is_lowest_exp = any(w in q_lower for w in ["lowest expense", "lowest cost", "least expense", "least spend", "minimum expense", "smallest expense", "lowest spending"])

    if is_lowest_exp:
        sorted_by_exp = sorted(depts.values(), key=lambda x: x["expense"])
        low_exp = sorted_by_exp[0]
        _SESSION_MEMORY[session_id] = {"last_department": low_exp["department"], "last_intent": "expense"}
        return (
            f"**{low_exp['department']}** has the **lowest expenses** in the organization:\n\n"
            f"• **Total Expenses**: {format_inr(low_exp['expense'])}\n"
            f"• **Revenue**: {format_inr(low_exp['revenue'])}\n"
            f"• **Net Profit**: {format_inr(low_exp['profit'])}\n"
            f"• **Margin**: {low_exp['margin']:.1f}%\n"
        )

    if is_highest_exp:
        sorted_by_exp = sorted(depts.values(), key=lambda x: x["expense"], reverse=True)
        top_exp = sorted_by_exp[0]
        _SESSION_MEMORY[session_id] = {"last_department": top_exp["department"], "last_intent": "expense"}
        return (
            f"**{top_exp['department']}** has the **highest expenses** across the enterprise:\n\n"
            f"• **Total Expenses**: {format_inr(top_exp['expense'])}\n"
            f"• **Revenue**: {format_inr(top_exp['revenue'])}\n"
            f"• **Net Profit**: {format_inr(top_exp['profit'])}\n"
            f"• **Operating Margin**: {top_exp['margin']:.1f}%\n"
            f"• **Budget Variance**: {'+' if top_exp['variance'] > 0 else ''}{format_inr(top_exp['variance'])}\n"
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 6: ANOMALIES — HIGHEST / LEAST ANOMALIES
    # ─────────────────────────────────────────────────────────────
    is_anom_query = any(w in q_lower for w in ["anomal", "outlier", "risk", "fraud", "irregular"])
    is_least_anom = any(w in q_lower for w in ["least anomalies", "lowest anomalies", "fewest anomalies", "least anomaly", "lowest anomaly risk", "minimum anomalies"])
    is_most_anom = any(w in q_lower for w in ["most anomalies", "highest anomalies", "maximum anomalies", "highest anomaly", "greatest anomalies", "most anomaly"])

    if is_least_anom:
        sorted_by_anom = sorted(depts.values(), key=lambda x: x["anomalies_count"])
        least_anom = sorted_by_anom[0]
        _SESSION_MEMORY[session_id] = {"last_department": least_anom["department"], "last_intent": "anomalies"}
        return (
            f"**{least_anom['department']}** has the **fewest anomalies** ({least_anom['anomalies_count']} detected) in the active dataset.\n\n"
            f"• **Total Anomalies**: {least_anom['anomalies_count']}\n"
            f"• **Critical**: {least_anom['critical_anomalies']}\n"
            f"• **High**: {least_anom['high_anomalies']}\n"
            f"• **Net Profit**: {format_inr(least_anom['profit'])}\n"
            f"• **Department Spend**: {format_inr(least_anom['expense'])}\n"
        )

    if is_most_anom:
        sorted_by_anom = sorted(depts.values(), key=lambda x: x["anomalies_count"], reverse=True)
        top_anom = sorted_by_anom[0]
        _SESSION_MEMORY[session_id] = {"last_department": top_anom["department"], "last_intent": "anomalies"}
        return (
            f"**{top_anom['department']}** has the **most anomalies** ({top_anom['anomalies_count']} flagged items) in the active dataset.\n\n"
            f"• **Total Anomalies**: {top_anom['anomalies_count']}\n"
            f"• **Critical Severity**: {top_anom['critical_anomalies']}\n"
            f"• **High Severity**: {top_anom['high_anomalies']}\n"
            f"• **Medium Severity**: {top_anom['medium_anomalies']}\n"
            f"• **Low Severity**: {top_anom['low_anomalies']}\n"
            f"• **Department Spend**: {format_inr(top_anom['expense'])}\n\n"
            f"**Recommendation**: Prioritize review of critical transactions in **{top_anom['department']}**."
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 7: MARGIN — BEST / WORST MARGIN
    # ─────────────────────────────────────────────────────────────
    if "margin" in q_lower and any(w in q_lower for w in ["highest", "best", "top", "max"]):
        sorted_by_margin = sorted(depts.values(), key=lambda x: x["margin"], reverse=True)
        top_m = sorted_by_margin[0]
        _SESSION_MEMORY[session_id] = {"last_department": top_m["department"], "last_intent": "margin"}
        return (
            f"**{top_m['department']}** holds the **highest operating profit margin** ({top_m['margin']:.1f}%).\n\n"
            f"• **Margin**: {top_m['margin']:.1f}%\n"
            f"• **Net Profit**: {format_inr(top_m['profit'])}\n"
            f"• **Revenue**: {format_inr(top_m['revenue'])}\n"
            f"• **Expenses**: {format_inr(top_m['expense'])}\n"
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 8: COMPARISON BETWEEN TWO DEPARTMENTS (OR CONTEXTUAL)
    # e.g., "compare Finance and HR", "compare top profit with highest anomaly department"
    # ─────────────────────────────────────────────────────────────
    if "compare" in q_lower or " vs " in q_lower or "versus" in q_lower or "difference between" in q_lower:
        if len(matched_depts) >= 2:
            d1_name, d2_name = matched_depts[0], matched_depts[1]
        elif len(matched_depts) == 1 and last_dept and last_dept != matched_depts[0]:
            d1_name, d2_name = matched_depts[0], last_dept
        elif "top profit" in q_lower and "anomaly" in q_lower:
            sorted_by_profit = sorted(depts.values(), key=lambda x: x["profit"], reverse=True)
            sorted_by_anom = sorted(depts.values(), key=lambda x: x["anomalies_count"], reverse=True)
            d1_name = sorted_by_profit[0]["department"]
            d2_name = sorted_by_anom[0]["department"]
        else:
            sorted_depts = sorted(depts.values(), key=lambda x: x["profit"], reverse=True)
            d1_name = sorted_depts[0]["department"]
            d2_name = sorted_depts[1]["department"] if len(sorted_depts) > 1 else sorted_depts[0]["department"]

        d1 = depts.get(d1_name, {})
        d2 = depts.get(d2_name, {})
        _SESSION_MEMORY[session_id] = {"last_department": d1_name, "last_intent": "comparison"}

        return (
            f"**Comparison: {d1_name} vs {d2_name}**\n\n"
            f"| Metric | {d1_name} | {d2_name} | Difference |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"| **Revenue** | {format_inr(d1.get('revenue'))} | {format_inr(d2.get('revenue'))} | {format_inr(d1.get('revenue', 0) - d2.get('revenue', 0))} |\n"
            f"| **Expenses** | {format_inr(d1.get('expense'))} | {format_inr(d2.get('expense'))} | {format_inr(d1.get('expense', 0) - d2.get('expense', 0))} |\n"
            f"| **Net Profit** | {format_inr(d1.get('profit'))} | {format_inr(d2.get('profit'))} | {format_inr(d1.get('profit', 0) - d2.get('profit', 0))} |\n"
            f"| **Operating Margin** | {d1.get('margin', 0):.1f}% | {d2.get('margin', 0):.1f}% | {d1.get('margin', 0) - d2.get('margin', 0):+.1f} pp |\n"
            f"| **Anomalies** | {d1.get('anomalies_count', 0)} ({d1.get('critical_anomalies', 0)} crit) | {d2.get('anomalies_count', 0)} ({d2.get('critical_anomalies', 0)} crit) | {d1.get('anomalies_count', 0) - d2.get('anomalies_count', 0):+d} |\n"
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 9: DRIVERS & WHY QUESTIONS
    # e.g., "why did profit fall", "what is driving expenses", "why is profit down"
    # ─────────────────────────────────────────────────────────────
    if "driving expense" in q_lower or "what is driving expenses" in q_lower or "expense driver" in q_lower or "biggest expense" in q_lower:
        top_exp_list = ctx["top_expenses"]
        lines = []
        for item, amt in top_exp_list:
            lines.append(f"• **{item}**: {format_inr(amt)}")
        return (
            f"**Primary Expense Drivers (Active Dataset: {ctx['dataset_name']})**:\n\n"
            + "\n".join(lines) + "\n\n"
            f"Total enterprise expenses stand at **{format_inr(ent['expense'])}** across all operating divisions."
        )

    if ("why did profit" in q_lower or "why is profit" in q_lower or "profit change" in q_lower or "profit fell" in q_lower or "profit dropped" in q_lower):
        top_exp_dept = max(depts.values(), key=lambda x: x["expense"]) if depts else None
        return (
            f"**Profit Variance Analysis (Active Dataset: {ctx['dataset_name']})**:\n\n"
            f"• **Enterprise Revenue**: {format_inr(ent['revenue'])}\n"
            f"• **Enterprise Expenses**: {format_inr(ent['expense'])}\n"
            f"• **Net Profit**: {format_inr(ent['profit'])} (Margin: {ent['margin']:.1f}%)\n\n"
            f"**Key Drivers**:\n"
            f"1. **Cost Concentration**: **{top_exp_dept['department']}** is the highest cost center ({format_inr(top_exp_dept['expense'])}).\n"
            f"2. **Anomalies & Variance**: {ent['critical_anomalies']} critical anomalies are currently impacting expense predictability.\n"
            f"3. **Operating Margin Spread**: Margins range from {min(d['margin'] for d in depts.values()):.1f}% to {max(d['margin'] for d in depts.values()):.1f}% across departments."
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 10: BUDGET & OVER BUDGET
    # e.g., "which departments are over budget", "budget status"
    # ─────────────────────────────────────────────────────────────
    if "budget" in q_lower or "over budget" in q_lower or "variance" in q_lower:
        if matched_depts:
            target_d = matched_depts[0]
            d_info = depts[target_d]
            _SESSION_MEMORY[session_id] = {"last_department": target_d, "last_intent": "budget"}
            if d_info["budget"] > 0:
                is_over = d_info["variance"] > 0
                status = "over budget" if is_over else "under budget"
                return (
                    f"**{target_d} Budget Breakdown**:\n\n"
                    f"• **Actual Spend**: {format_inr(d_info['expense'])}\n"
                    f"• **Allocated Budget**: {format_inr(d_info['budget'])}\n"
                    f"• **Variance**: {format_inr(abs(d_info['variance']))} ({abs(d_info['variance_pct']):.1f}% {status})\n\n"
                    f"Status: **{status.upper()}** by {format_inr(abs(d_info['variance']))}."
                )
            else:
                return f"**{target_d}** actual expenses stand at **{format_inr(d_info['expense'])}**. No budget target is configured for this department in the dataset."
        else:
            over_budget = [d for d in depts.values() if d["budget"] > 0 and d["variance"] > 0]
            if over_budget:
                resp = "**Departments Operating Over Budget**:\n\n"
                for o in sorted(over_budget, key=lambda x: x["variance"], reverse=True):
                    resp += f"• **{o['department']}**: Spend {format_inr(o['expense'])} vs Budget {format_inr(o['budget'])} (+{o['variance_pct']:.1f}% over)\n"
                return resp
            else:
                return "All departments with configured budgets are operating within their allocated targets."

    # ─────────────────────────────────────────────────────────────
    # CASE 11: FORECAST INQUIRIES
    # e.g., "what is the forecast", "how does forecast compare with historical actuals"
    # ─────────────────────────────────────────────────────────────
    if "forecast" in q_lower or "projection" in q_lower or "next year" in q_lower or "future" in q_lower:
        fc = ctx["forecast"]
        if fc and fc.get("has_enough_data"):
            return (
                f"**Statistical Forecast Trajectory (Active Dataset: {ctx['dataset_name']})**:\n\n"
                f"• **Expected Net Profit**: {format_inr(fc.get('expected_case'))}\n"
                f"• **Optimistic Best Case (+15% / +1.96σ)**: {format_inr(fc.get('best_case'))}\n"
                f"• **Downside Worst Case (-15% / -1.96σ)**: {format_inr(fc.get('worst_case'))}\n"
                f"• **Model Used**: {fc.get('model_used')}\n"
                f"• **Confidence Score (R²)**: {fc.get('confidence_score', 0.95) * 100:.1f}%\n"
                f"• **Trend Direction**: {fc.get('trend_direction', 'Stable').capitalize()}\n\n"
                f"**Historical Comparison**: Current historical actual profit is {format_inr(ent['profit'])}, projecting a {fc.get('trend_direction', 'stable')} trend forward."
            )
        else:
            return (
                f"**Forecast Trajectory**: Historical baseline shows enterprise revenue of {format_inr(ent['revenue'])} "
                f"and net profit of {format_inr(ent['profit'])} ({ent['margin']:.1f}% margin). Projected performance remains stable across the forecast horizon."
            )

    # ─────────────────────────────────────────────────────────────
    # CASE 12: WHAT-IF SIMULATIONS
    # ─────────────────────────────────────────────────────────────
    if ("what if" in q_lower or "simulate" in q_lower or "increases by" in q_lower or "decreases by" in q_lower or "grows by" in q_lower):
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", q_clean)
        pct = float(pct_match.group(1)) if pct_match else 10.0
        is_decrease = any(w in q_lower for w in ["decrease", "drop", "cut", "reduce", "reduction", "-"])
        effective_pct = -pct if is_decrease else pct

        is_exp = any(w in q_lower for w in ["expense", "cost", "spend", "opex"])
        is_rev = any(w in q_lower for w in ["revenue", "sales", "income", "topline"])

        if matched_depts:
            target_d = matched_depts[0]
            d_curr = depts[target_d]
            _SESSION_MEMORY[session_id] = {"last_department": target_d, "last_intent": "what_if"}
            if is_exp or not is_rev:
                new_d_exp = d_curr["expense"] * (1 + effective_pct / 100)
                new_ent_exp = (ent["expense"] - d_curr["expense"]) + new_d_exp
                new_ent_prof = ent["revenue"] - new_ent_exp
                prof_diff = new_ent_prof - ent["profit"]
                return (
                    f"**Scenario Simulation for {target_d}** ({effective_pct:+.1f}% Expense Adjustment):\n\n"
                    f"• **{target_d} Expenses**: {format_inr(d_curr['expense'])} → **{format_inr(new_d_exp)}**\n"
                    f"• **Enterprise Total Expenses**: {format_inr(ent['expense'])} → **{format_inr(new_ent_exp)}**\n"
                    f"• **Enterprise Net Profit Impact**: {format_inr(ent['profit'])} → **{format_inr(new_ent_prof)}** ({format_inr(prof_diff)})\n"
                    f"• **Projected Margin**: {((new_ent_prof / ent['revenue']) * 100 if ent['revenue'] > 0 else 0):.1f}%"
                )
        else:
            new_exp = ent["expense"] * (1 + effective_pct / 100)
            new_prof = ent["revenue"] - new_exp
            new_margin = (new_prof / ent["revenue"] * 100) if ent["revenue"] > 0 else 0
            prof_diff = new_prof - ent["profit"]
            return (
                f"**Enterprise Scenario Simulation** ({effective_pct:+.1f}% Expense Shift):\n\n"
                f"• **Baseline Expenses**: {format_inr(ent['expense'])} → **Scenario**: {format_inr(new_exp)}\n"
                f"• **Baseline Net Profit**: {format_inr(ent['profit'])} → **Scenario**: {format_inr(new_prof)} ({format_inr(prof_diff)})\n"
                f"• **Projected Margin**: {new_margin:.1f}% ({new_margin - ent['margin']:+.1f} pp)"
            )

    # ─────────────────────────────────────────────────────────────
    # CASE 13: SPECIFIC DEPARTMENT OVERVIEW
    # ─────────────────────────────────────────────────────────────
    if matched_depts:
        target_d = matched_depts[0]
        d_info = depts[target_d]
        _SESSION_MEMORY[session_id] = {"last_department": target_d, "last_intent": "department_performance"}
        return (
            f"**{target_d} Department Financial Performance**:\n\n"
            f"• **Revenue**: {format_inr(d_info['revenue'])}\n"
            f"• **Expenses**: {format_inr(d_info['expense'])}\n"
            f"• **Net Profit**: {format_inr(d_info['profit'])}\n"
            f"• **Operating Margin**: {d_info['margin']:.1f}%\n"
            f"• **Anomalies**: {d_info['anomalies_count']} ({d_info['critical_anomalies']} critical)\n"
            f"• **Budget Variance**: {'+' if d_info['variance'] > 0 else ''}{format_inr(d_info['variance'])}"
        )

    # ─────────────────────────────────────────────────────────────
    # CASE 14: ENTERPRISE OVERVIEW / GENERAL
    # ─────────────────────────────────────────────────────────────
    _SESSION_MEMORY[session_id] = {"last_intent": "summary"}
    return (
        f"**Enterprise Financial Summary (Active Dataset: {ctx['dataset_name']})**:\n\n"
        f"• **Total Revenue**: {format_inr(ent['revenue'])}\n"
        f"• **Total Expenses**: {format_inr(ent['expense'])}\n"
        f"• **Net Profit**: {format_inr(ent['profit'])}\n"
        f"• **Operating Margin**: {ent['margin']:.2f}%\n"
        f"• **Total Anomalies**: {ent['total_anomalies']} ({ent['critical_anomalies']} critical)\n\n"
        f"You can ask analytical questions such as:\n"
        f"• *'Which department has best profit and least anomalies?'*\n"
        f"• *'Which department has highest revenue?'*\n"
        f"• *'Which department has lowest expenses?'*\n"
        f"• *'Show top 5 departments by net profit'*.\n"
    )

def get_rag_context(db: Session, query: str) -> str:
    """Helper for Reports and other services requiring concise synthesized narrative."""
    return route_and_calculate_answer(db, query)

def ask_copilot(db: Session, question: str, session_id: str = "default") -> str:
    """
    Main Copilot entrypoint:
    1. Runs deterministic analytics & calculation.
    2. Uses Gemini LLM strictly to refine presentation without altering any numbers.
    """
    calculated_response = route_and_calculate_answer(db, question, session_id)

    if not settings.GEMINI_API_KEY:
        return calculated_response

    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = f"""
You are an executive AI Financial Intelligence Copilot for an enterprise P&L platform.
Answer the user's question accurately using ONLY the verified calculated findings provided below.
DO NOT alter, guess, or invent any numbers, currency amounts, percentages, or department rankings.
Keep the answer concise, structured, and professional.

Verified Calculated Findings:
{calculated_response}

User Question: {question}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text and len(response.text.strip()) > 10:
            return response.text.strip()
        return calculated_response
    except Exception:
        return calculated_response
