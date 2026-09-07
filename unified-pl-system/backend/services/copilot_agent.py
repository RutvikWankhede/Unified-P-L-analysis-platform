import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from config import settings
from models.pl_record import PLRecord, DepartmentBudget
from models.anomaly import Anomaly

# In-memory session context for conversation memory across turns
_SESSION_MEMORY: Dict[str, Dict[str, Any]] = {}

def format_inr(val: Optional[float]) -> str:
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


def get_financial_context_and_calc(db: Session, question: str, session_id: str = "default") -> Dict[str, Any]:
    from routers.datasets_router import get_active_dataset, get_active_dataset_id
    from services.metric_engine import MetricEngine
    from services.analytics_engine import AnalyticsEngine

    active_info = get_active_dataset(db)
    active_id = get_active_dataset_id(db)
    dataset_name = active_info.get("filename", "Active Dataset") if active_info else "Active Dataset"

    me = MetricEngine(db, active_id)
    summary_df = me.aggregate_data("monthly", dept=None)

    # All departments
    dept_query = db.query(PLRecord.domain).distinct()
    if active_id:
        dept_query = dept_query.filter(PLRecord.upload_id == active_id)
    all_depts = sorted([d[0] for d in dept_query.all() if d[0] and d[0] not in ["All Departments", "Unknown", "All"]])

    # Enterprise KPIs
    if not summary_df.empty:
        tot_rev = float(summary_df["revenue"].sum()) if "revenue" in summary_df.columns else 0.0
        tot_exp = float(summary_df["expense"].sum()) if "expense" in summary_df.columns else 0.0
    else:
        tot_rev = 0.0
        tot_exp = 0.0
    tot_prof = tot_rev - tot_exp
    tot_margin = (tot_prof / tot_rev * 100) if tot_rev > 0 else 0.0

    # Department Metrics
    dept_metrics = {}
    for d in all_depts:
        d_df = me.aggregate_data("monthly", dept=d)
        d_rev = float(d_df["revenue"].sum()) if not d_df.empty and "revenue" in d_df.columns else 0.0
        d_exp = float(d_df["expense"].sum()) if not d_df.empty and "expense" in d_df.columns else 0.0
        d_prof = d_rev - d_exp
        d_margin = (d_prof / d_rev * 100) if d_rev > 0 else 0.0

        # Department budget
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
            "high_anomalies": high_count
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
        "forecast": fc_res
    }


def route_and_calculate_answer(db: Session, question: str, session_id: str = "default") -> str:
    ctx = get_financial_context_and_calc(db, question, session_id)
    ent = ctx["enterprise"]
    depts = ctx["departments"]
    q_clean = question.strip()
    q_lower = q_clean.lower()

    global _SESSION_MEMORY
    session_ctx = _SESSION_MEMORY.get(session_id, {})

    # Detect entity: department mentioned
    matched_dept = None
    for d_name in depts.keys():
        if d_name.lower() in q_lower:
            matched_dept = d_name
            break

    # If no department found but user uses pronouns like "it", "this", "why", resolve from memory
    if not matched_dept and (" it" in q_lower or "why" in q_lower or "explain" in q_lower or "compare" in q_lower):
        matched_dept = session_ctx.get("last_department")

    # -------------------------------------------------------------
    # 1. INTENT: PROFITABILITY / HIGHEST / LOWEST PROFIT
    # -------------------------------------------------------------
    if ("highest profit" in q_lower or "most profitable" in q_lower or "max profit" in q_lower or "best profit" in q_lower or
        "top profit" in q_lower or "highest net profit" in q_lower or "lowest profit" in q_lower or "least profitable" in q_lower):
        sorted_depts = sorted(depts.values(), key=lambda x: x["profit"], reverse=True)
        if not sorted_depts:
            return "No department financial data is available in the current dataset."

        if "lowest" in q_lower or "least" in q_lower:
            lowest = sorted_depts[-1]
            _SESSION_MEMORY[session_id] = {"last_department": lowest["department"], "last_intent": "profitability"}
            return (
                f"**{lowest['department']}** currently has the lowest net profit in the organization:\n\n"
                f"• **Net Profit**: {format_inr(lowest['profit'])}\n"
                f"• **Revenue**: {format_inr(lowest['revenue'])}\n"
                f"• **Expenses**: {format_inr(lowest['expense'])}\n"
                f"• **Margin**: {lowest['margin']:.1f}%\n"
            )
        else:
            top = sorted_depts[0]
            second = sorted_depts[1] if len(sorted_depts) > 1 else None
            _SESSION_MEMORY[session_id] = {"last_department": top["department"], "last_intent": "profitability"}
            resp = (
                f"**{top['department']}** is currently the most profitable department.\n\n"
                f"• **Net Profit**: {format_inr(top['profit'])}\n"
                f"• **Profit Margin**: {top['margin']:.1f}%\n"
                f"• **Revenue**: {format_inr(top['revenue'])}\n"
            )
            if second:
                resp += f"\n**{second['department']}** ranks second at {format_inr(second['profit'])} ({second['margin']:.1f}% margin)."
            return resp

    # -------------------------------------------------------------
    # 2. INTENT: MARGIN / HIGHEST MARGIN
    # -------------------------------------------------------------
    if ("highest margin" in q_lower or "best margin" in q_lower or "top margin" in q_lower or "max margin" in q_lower or "most margin" in q_lower):
        sorted_by_margin = sorted(depts.values(), key=lambda x: x["margin"], reverse=True)
        if sorted_by_margin:
            top_m = sorted_by_margin[0]
            second_m = sorted_by_margin[1] if len(sorted_by_margin) > 1 else None
            _SESSION_MEMORY[session_id] = {"last_department": top_m["department"], "last_intent": "margin"}
            resp = (
                f"**{top_m['department']}** holds the highest profit margin across the enterprise.\n\n"
                f"• **Operating Margin**: {top_m['margin']:.1f}%\n"
                f"• **Net Profit**: {format_inr(top_m['profit'])}\n"
                f"• **Revenue**: {format_inr(top_m['revenue'])}\n"
            )
            if second_m:
                resp += f"\n**{second_m['department']}** ranks second with a {second_m['margin']:.1f}% margin."
            return resp

    # -------------------------------------------------------------
    # 3. INTENT: BUDGET VS ACTUAL / OVER BUDGET
    # -------------------------------------------------------------
    if "budget" in q_lower or "variance" in q_lower or "over budget" in q_lower:
        if matched_dept and matched_dept in depts:
            d_info = depts[matched_dept]
            _SESSION_MEMORY[session_id] = {"last_department": matched_dept, "last_intent": "budget"}
            if d_info["budget"] > 0:
                is_over = d_info["variance"] > 0
                status = "over budget" if is_over else "under budget"
                return (
                    f"**{matched_dept} Budget Breakdown**:\n\n"
                    f"• **Actual Spend**: {format_inr(d_info['expense'])}\n"
                    f"• **Allocated Budget**: {format_inr(d_info['budget'])}\n"
                    f"• **Variance**: {format_inr(abs(d_info['variance']))} ({abs(d_info['variance_pct']):.1f}% {status})\n\n"
                    f"{matched_dept} is currently **{status}** by {format_inr(abs(d_info['variance']))}."
                )
            else:
                return (
                    f"**{matched_dept}** actual expenses stand at {format_inr(d_info['expense'])}. "
                    f"No formal budget baseline is configured for this department."
                )
        else:
            # Show all departments over budget
            over_budget = [d for d in depts.values() if d["budget"] > 0 and d["variance"] > 0]
            if over_budget:
                resp = "**Departments Over Budget**:\n\n"
                for o in sorted(over_budget, key=lambda x: x["variance"], reverse=True):
                    resp += f"• **{o['department']}**: Spend {format_inr(o['expense'])} vs Budget {format_inr(o['budget'])} (+{o['variance_pct']:.1f}% over)\n"
                return resp
            else:
                return "All departments are operating within their allocated budget baselines or no budget overruns detected."

    # -------------------------------------------------------------
    # 4. INTENT: WHAT-IF SIMULATION IN COPILOT
    # e.g. "What happens if expenses increase by 10%?"
    # -------------------------------------------------------------
    if ("what if" in q_lower or "what happens if" in q_lower or "simulate" in q_lower or "increases by" in q_lower or "decreases by" in q_lower or "growth of" in q_lower):
        # Extract percentage
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", q_clean)
        pct = float(pct_match.group(1)) if pct_match else 10.0

        is_decrease = any(w in q_lower for w in ["decrease", "decreases", "drop", "cut", "reduce", "reduces", "reduction", "-"])
        effective_pct = -pct if is_decrease else pct

        is_exp = any(w in q_lower for w in ["expense", "expenses", "cost", "costs", "opex", "spend"])
        is_rev = any(w in q_lower for w in ["revenue", "sales", "income", "topline", "top-line"])

        if matched_dept and matched_dept in depts:
            d_curr = depts[matched_dept]
            _SESSION_MEMORY[session_id] = {"last_department": matched_dept, "last_intent": "what_if"}
            if is_exp:
                new_d_exp = d_curr["expense"] * (1 + effective_pct / 100)
                new_ent_exp = (ent["expense"] - d_curr["expense"]) + new_d_exp
                new_ent_prof = ent["revenue"] - new_ent_exp
                prof_diff = new_ent_prof - ent["profit"]
                return (
                    f"**Scenario Simulation for {matched_dept}** ({effective_pct:+.1f}% Expense Adjustment):\n\n"
                    f"• **{matched_dept} Expense**: {format_inr(d_curr['expense'])} → **{format_inr(new_d_exp)}**\n"
                    f"• **Enterprise Expense**: {format_inr(ent['expense'])} → **{format_inr(new_ent_exp)}**\n"
                    f"• **Enterprise Net Profit**: {format_inr(ent['profit'])} → **{format_inr(new_ent_prof)}** ({format_inr(prof_diff)})\n"
                    f"• **Net Margin**: {((new_ent_prof / ent['revenue'])*100 if ent['revenue'] > 0 else 0):.1f}%"
                )
        else:
            if is_exp or not is_rev:
                new_exp = ent["expense"] * (1 + effective_pct / 100)
                new_prof = ent["revenue"] - new_exp
                new_margin = (new_prof / ent["revenue"] * 100) if ent["revenue"] > 0 else 0
                prof_diff = new_prof - ent["profit"]
                return (
                    f"**Enterprise Scenario Analysis** ({effective_pct:+.1f}% Expense Shift):\n\n"
                    f"• **Baseline Expense**: {format_inr(ent['expense'])} → **Scenario**: {format_inr(new_exp)}\n"
                    f"• **Baseline Net Profit**: {format_inr(ent['profit'])} → **Scenario**: {format_inr(new_prof)} ({format_inr(prof_diff)})\n"
                    f"• **Projected Margin**: {new_margin:.1f}% ({new_margin - ent['margin']:+.1f} pp)\n"
                )
            elif is_rev:
                new_rev = ent["revenue"] * (1 + effective_pct / 100)
                new_prof = new_rev - ent["expense"]
                new_margin = (new_prof / new_rev * 100) if new_rev > 0 else 0
                prof_diff = new_prof - ent["profit"]
                return (
                    f"**Enterprise Scenario Analysis** ({effective_pct:+.1f}% Revenue Shift):\n\n"
                    f"• **Baseline Revenue**: {format_inr(ent['revenue'])} → **Scenario**: {format_inr(new_rev)}\n"
                    f"• **Baseline Net Profit**: {format_inr(ent['profit'])} → **Scenario**: {format_inr(new_prof)} ({format_inr(prof_diff)})\n"
                    f"• **Projected Margin**: {new_margin:.1f}% ({new_margin - ent['margin']:+.1f} pp)\n"
                )

    # -------------------------------------------------------------
    # 5. INTENT: ANOMALY RISKS & EXPLANATIONS
    # e.g. "Show anomaly risk in Finance", "Total anomalies", "Explain anomaly spike"
    # -------------------------------------------------------------
    if "anomal" in q_lower or "outlier" in q_lower or "risk" in q_lower:
        if matched_dept and matched_dept in depts:
            d_info = depts[matched_dept]
            _SESSION_MEMORY[session_id] = {"last_department": matched_dept, "last_intent": "anomaly"}
            return (
                f"**Anomaly Risk in {matched_dept}**:\n\n"
                f"• **Total Anomalies Detected**: {d_info['anomalies_count']}\n"
                f"• **Critical Severity**: {d_info['critical_anomalies']}\n"
                f"• **High Severity**: {d_info['high_anomalies']}\n"
                f"• **Department Spend**: {format_inr(d_info['expense'])}\n\n"
                f"{'Critical attention recommended for flagged ledger entries.' if d_info['critical_anomalies'] > 0 else 'Risk level is moderate with no uncontained critical anomalies.'}"
            )
        else:
            # Top department with anomalies
            top_risk_dept = max(depts.values(), key=lambda x: x["anomalies_count"]) if depts else None
            return (
                f"**Enterprise Anomaly Status (Active Dataset: {ctx['dataset_name']})**:\n\n"
                f"• **Total Anomalies**: {ent['total_anomalies']}\n"
                f"• **Critical**: {ent['critical_anomalies']}\n"
                f"• **High**: {ent['high_anomalies']}\n"
                f"• **Medium**: {ent['medium_anomalies']}\n"
                f"• **Low**: {ent['low_anomalies']}\n\n"
                f"Highest anomaly exposure is in **{top_risk_dept['department']}** with {top_risk_dept['anomalies_count']} flagged items." if top_risk_dept else ""
            )

    # -------------------------------------------------------------
    # 6. INTENT: FORECAST INQUIRIES
    # e.g. "What is the forecast for next year?", "Revenue forecast"
    # -------------------------------------------------------------
    if "forecast" in q_lower or "projection" in q_lower or "next year" in q_lower or "next quarter" in q_lower:
        fc = ctx["forecast"]
        if fc and fc.get("has_enough_data"):
            return (
                f"**Statistical Forecast Trajectory (Active Dataset: {ctx['dataset_name']})**:\n\n"
                f"• **Expected Net Profit**: {format_inr(fc.get('expected_case'))}\n"
                f"• **Optimistic Best Case (+1.96σ)**: {format_inr(fc.get('best_case'))}\n"
                f"• **Downside Worst Case (-1.96σ)**: {format_inr(fc.get('worst_case'))}\n"
                f"• **Model Used**: {fc.get('model_used')}\n"
                f"• **Confidence Score**: {fc.get('confidence_score', 0.95) * 100:.1f}%\n"
                f"• **Trend Direction**: {fc.get('trend_direction', 'Stable').capitalize()}\n"
            )
        else:
            return (
                f"**Forecast Trajectory**: Historical baseline shows enterprise revenue of {format_inr(ent['revenue'])} "
                f"and net profit of {format_inr(ent['profit'])} ({ent['margin']:.1f}% margin). Projections indicate stable performance across trailing periods."
            )

    # -------------------------------------------------------------
    # 7. INTENT: COMPARISON BETWEEN TWO DEPARTMENTS
    # e.g. "Compare Sales and Operations profit"
    # -------------------------------------------------------------
    if "compare" in q_lower or " vs " in q_lower or "versus" in q_lower:
        matched_depts = [d for d in depts.keys() if d.lower() in q_lower]
        if len(matched_depts) >= 2:
            d1 = depts[matched_depts[0]]
            d2 = depts[matched_depts[1]]
            _SESSION_MEMORY[session_id] = {"last_department": d1["department"], "last_intent": "comparison"}
            return (
                f"**Comparison: {d1['department']} vs {d2['department']}**\n\n"
                f"| Metric | {d1['department']} | {d2['department']} | Difference |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"| **Revenue** | {format_inr(d1['revenue'])} | {format_inr(d2['revenue'])} | {format_inr(d1['revenue'] - d2['revenue'])} |\n"
                f"| **Expense** | {format_inr(d1['expense'])} | {format_inr(d2['expense'])} | {format_inr(d1['expense'] - d2['expense'])} |\n"
                f"| **Net Profit** | {format_inr(d1['profit'])} | {format_inr(d2['profit'])} | {format_inr(d1['profit'] - d2['profit'])} |\n"
                f"| **Margin** | {d1['margin']:.1f}% | {d2['margin']:.1f}% | {d1['margin'] - d2['margin']:+.1f} pp |\n"
            )

    # -------------------------------------------------------------
    # 8. INTENT: SPECIFIC DEPARTMENT PERFORMANCE
    # e.g. "How is Sales doing?", "Why is Sales most profitable?"
    # -------------------------------------------------------------
    if matched_dept and matched_dept in depts:
        d_info = depts[matched_dept]
        _SESSION_MEMORY[session_id] = {"last_department": matched_dept, "last_intent": "department_performance"}
        return (
            f"**{matched_dept} Department Financial Summary**:\n\n"
            f"• **Revenue**: {format_inr(d_info['revenue'])}\n"
            f"• **Expenses**: {format_inr(d_info['expense'])}\n"
            f"• **Net Profit**: {format_inr(d_info['profit'])}\n"
            f"• **Operating Margin**: {d_info['margin']:.1f}%\n"
            f"• **Budget Status**: {format_inr(d_info['budget'])} ({'+' if d_info['variance'] > 0 else ''}{d_info['variance_pct']:.1f}% variance)\n"
            f"• **Active Anomalies**: {d_info['anomalies_count']} ({d_info['critical_anomalies']} critical)"
        )

    # -------------------------------------------------------------
    # 9. INTENT: ENTERPRISE SUMMARY / TOTAL REVENUE / EXPENSE / PROFIT
    # -------------------------------------------------------------
    if ("total revenue" in q_lower or "revenue" in q_lower or "total expense" in q_lower or "net profit" in q_lower or
        "summary" in q_lower or "overview" in q_lower or "health" in q_lower or "financial status" in q_lower):
        _SESSION_MEMORY[session_id] = {"last_intent": "summary"}
        return (
            f"**Enterprise Financial Summary (Active Dataset: {ctx['dataset_name']})**:\n\n"
            f"• **Total Revenue**: {format_inr(ent['revenue'])}\n"
            f"• **Total Expenses**: {format_inr(ent['expense'])}\n"
            f"• **Net Profit**: {format_inr(ent['profit'])}\n"
            f"• **Operating Margin**: {ent['margin']:.2f}%\n"
            f"• **Total Anomalies**: {ent['total_anomalies']} ({ent['critical_anomalies']} critical)"
        )

    # -------------------------------------------------------------
    # 10. INTENT: DATASET INFO
    # -------------------------------------------------------------
    if "dataset" in q_lower or "active file" in q_lower:
        return (
            f"**Active Dataset Details**:\n\n"
            f"• **Filename**: {ctx['dataset_name']}\n"
            f"• **Dataset ID**: {ctx['dataset_id']}\n"
            f"• **Tracked Departments**: {len(depts)} ({', '.join(list(depts.keys())[:5])}...)\n"
            f"• **Total Recorded Revenue**: {format_inr(ent['revenue'])}\n"
            f"• **Total Recorded Expenses**: {format_inr(ent['expense'])}"
        )

    # -------------------------------------------------------------
    # 11. INTENT: RECOMMENDATIONS
    # -------------------------------------------------------------
    if "recommend" in q_lower or "suggest" in q_lower or "action" in q_lower:
        top_exp = max(depts.values(), key=lambda x: x["expense"]) if depts else None
        top_prof = max(depts.values(), key=lambda x: x["profit"]) if depts else None
        return (
            f"**Strategic Recommendations from Active Financial Analysis**:\n\n"
            f"1. **Expense Optimization**: Scrutinize {top_exp['department'] if top_exp else 'high OPEX units'} ({format_inr(top_exp['expense']) if top_exp else 'high spend'}) to control cost creep.\n"
            f"2. **Revenue Scaling**: Accelerate investments in {top_prof['department'] if top_prof else 'high margin divisions'} ({top_prof['margin']:.1f}% margin if top_prof else 'top margin').\n"
            f"3. **Risk Governance**: Triage the {ent['critical_anomalies']} critical ledger anomalies identified by ML surveillance."
        )

    # -------------------------------------------------------------
    # 12. FALLBACK / GENERAL FINANCE
    # -------------------------------------------------------------
    return (
        f"Based on the active dataset (**{ctx['dataset_name']}**):\n\n"
        f"• **Total Revenue**: {format_inr(ent['revenue'])}\n"
        f"• **Total Expenses**: {format_inr(ent['expense'])}\n"
        f"• **Net Profit**: {format_inr(ent['profit'])}\n"
        f"• **Operating Margin**: {ent['margin']:.1f}%\n\n"
        f"You can ask me specific questions like: *'Which department has highest profit?'*, *'Why is Logistics over budget?'*, *'What happens if expenses increase by 10%?'*, or *'Show anomaly risk in Finance'*."
    )


def ask_copilot(db: Session, question: str, session_id: str = "default") -> str:
    """
    Production-grade Copilot orchestration:
    1. Deterministic intent detection & mathematical calculation first.
    2. Optional LLM enhancement with strict adherence to computed facts.
    """
    # Deterministic factual response
    calculated_response = route_and_calculate_answer(db, question, session_id)

    if not settings.GEMINI_API_KEY:
        return calculated_response

    # If Gemini API Key is available, synthesize with strictly grounded factual context
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = f"""
You are an executive AI Financial Intelligence Copilot for an enterprise P&L platform.
Answer the user's question accurately using ONLY the verified calculated facts provided below.
DO NOT invent or alter any numerical values, currencies, or percentages.

Verified Calculated Findings:
{calculated_response}

User Question: {question}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text if response.text else calculated_response
    except Exception:
        return calculated_response
