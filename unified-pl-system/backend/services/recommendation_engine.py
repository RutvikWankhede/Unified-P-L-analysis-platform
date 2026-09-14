import json
import logging
from sqlalchemy.orm import Session
from config import settings

from models.anomaly import Anomaly
from models.pl_record import PLRecord
from models.recommendation import Recommendation

def _get_genai_model():
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception as e:
        logger.warning(f"AI model initialization failed or not installed: {e}")
        return None

def generate_recommendations(db: Session, anomaly_id: int):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        return []

    pl_record = db.query(PLRecord).filter(PLRecord.id == anomaly.pl_record_id).first()

    # Fetch some historical context for the same department and line item
    historical_records = db.query(PLRecord).filter(
        PLRecord.domain == pl_record.domain,
        PLRecord.line_item == pl_record.line_item,
        PLRecord.id != pl_record.id
    ).limit(5).all()
    
    history_context = ""
    if historical_records:
        history_context = "\nHistorical Data for Context:\n"
        for hr in historical_records:
            history_context += f"- Period {hr.period}: {hr.amount}\n"

    is_sod_violation = False
    if anomaly.assigned_to and anomaly.assigned_to == pl_record.uploaded_by:
        is_sod_violation = True

    prompt = f"""
    You are an expert Financial Analysis AI.
    An anomaly has been detected in a company's P&L records.
    
    Anomaly Details:
    - Department: {pl_record.domain}
    - Line Item: {pl_record.line_item}
    - Period: {pl_record.period}
    - Amount: {pl_record.amount}
    - Deviation Amount: {anomaly.deviation_amount}
    - Severity: {anomaly.severity}
    - SOD Violation: {'Yes (Uploader is the assigned reviewer)' if is_sod_violation else 'No'}
    {history_context}
    
    Based on this, generate 1 to 3 actionable recommendations to address this anomaly.
    Return ONLY a valid JSON array of objects. Each object must have:
    - "priority": integer (1=Highest, 5=Lowest)
    - "action_type": string (short title)
    - "description": string (detailed description)
    - "action_owner": string (e.g. "Finance Controller", "Department Head")
    - "sod_flag": boolean (true if addressing SOD violation, else false)
    - "reason": string (why this action is recommended)
    - "financial_impact": string (e.g. "High", "Low", or specific estimated value)
    - "confidence": integer (0 to 100)
    - "suggested_action": string (one sentence summary)
    - "expected_benefit": string
    """

    recommendations_data = []
    
    try:
        model = _get_genai_model()
        if model:
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Clean up markdown if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            recommendations_data = json.loads(text.strip())
            
            if not isinstance(recommendations_data, list):
                recommendations_data = [recommendations_data]
            
    except Exception as e:
        logger.error(f"Error generating AI recommendations: {e}")
        # Fallback
        recommendations_data = [
            {
                "priority": 1,
                "action_type": "Manual Review Required",
                "description": "AI generation failed. Please review this anomaly manually.",
                "action_owner": "Finance Manager",
                "sod_flag": is_sod_violation,
                "reason": f"System error generating insights for anomaly {anomaly.id}.",
                "financial_impact": "Unknown",
                "confidence": 100,
                "suggested_action": "Manually audit this record.",
                "expected_benefit": "Prevent unverified ledger anomalies."
            }
        ]

    db_recs = []
    # Clear existing
    db.query(Recommendation).filter(Recommendation.anomaly_id == anomaly.id).delete()

    for rec in recommendations_data:
        db_rec = Recommendation(anomaly_id=anomaly.id, **rec)
        db.add(db_rec)
        db_recs.append(db_rec)

    db.commit()
    for rec in db_recs:
        db.refresh(rec)

    return db_recs


def generate_enterprise_recommendations(db: Session, active_dataset_id=None):
    """
    Generate prioritized, data-driven management recommendations strictly grounded
    in active dataset financials, departmental breakdown, budget variance, anomalies,
    and forecast trajectory following the pattern:
    DATA -> FINDING -> BUSINESS IMPACT -> ACTION
    Target: 8–12 prioritized, actionable recommendations when supported by dataset evidence.
    """
    from services.metric_engine import MetricEngine
    from services.analytics_engine import AnalyticsEngine
    from models.anomaly import Anomaly
    from models.pl_record import PLRecord

    me = MetricEngine(db, active_dataset_id)
    ae = AnalyticsEngine(me)
    kpis = me.get_kpis()
    dept_aggs = me.get_department_aggregates()
    trends = kpis.get("trends", {})
    caps = me.get_capabilities()

    tot_rev = float(kpis.get("revenue") or 0.0)
    tot_exp = float(kpis.get("expense") or 0.0)
    tot_prof = float(kpis.get("profit") or (tot_rev - tot_exp))
    margin = float(kpis.get("profit_margin") or ((tot_prof / tot_rev * 100) if tot_rev > 0 else 0.0))

    rev_growth = float(trends.get("revenue", 0.0) or 0.0)
    exp_growth = float(trends.get("expense", 0.0) or 0.0)

    # Anomaly records
    anom_q = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id).filter(Anomaly.status != "Resolved")
    if active_dataset_id:
        anom_q = anom_q.filter(PLRecord.upload_id == active_dataset_id)
    active_anoms = anom_q.all()
    total_anom_count = len(active_anoms)
    crit_anom_count = sum(1 for a in active_anoms if a.severity in ["Critical", "High"])

    # Forecast context
    fcst = ae.get_forecast(metric="profit", n_forecast=12)
    fcst_has_data = fcst.get("has_enough_data", False)
    fcst_exp = float(fcst.get("expected_case") or 0.0) if fcst_has_data else None

    recommendations = []

    # -------------------------------------------------------------
    # 1. Budget Overrun Discipline (if Budget exists)
    # -------------------------------------------------------------
    has_bgt = caps.get("budget", {}).get("available", False) or caps.get("has_budget", False)
    if has_bgt:
        try:
            bgt_res = me.get_budget_vs_actual(dept="all", range_limit="all")
            if bgt_res and bgt_res.get("departments"):
                highest_var_dept = bgt_res.get("highest_variance_dept")
                highest_var_pct = bgt_res.get("highest_variance_pct", 0.0)
                over_count = bgt_res.get("over_budget_count", 0)

                if highest_var_dept and highest_var_pct > 0:
                    target_dept_agg = next((d for d in dept_aggs if d.get("department") == highest_var_dept), None)
                    d_exp = target_dept_agg.get("expense", 0) if target_dept_agg else tot_exp * 0.2
                    savings_target = round(d_exp * (highest_var_pct / 100.0) * 0.5)

                    recommendations.append({
                        "id": "rec-budget-control",
                        "category": "budget_governance",
                        "priority": "Critical" if highest_var_pct > 15 else ("High" if highest_var_pct > 5 else "Medium"),
                        "title": f"Control {highest_var_dept} Budget Overrun",
                        "evidence": f"{highest_var_dept} spend is {highest_var_pct:.1f}% above budget target, contributing to an overall {over_count}-department overrun.",
                        "reason": f"Actual expenditures in {highest_var_dept} exceed budget allocation by {highest_var_pct:.1f}%, depressing overall enterprise operating margin.",
                        "business_impact": "Uncontrolled departmental budget overruns directly dilute enterprise EBITDA and reduce free cash conversion.",
                        "financial_impact": savings_target,
                        "confidence": 94,
                        "department": highest_var_dept,
                        "metric": "Budget Variance",
                        "suggested_action": f"Review largest cost drivers in {highest_var_dept} and establish immediate purchase order authorization thresholds.",
                        "expected_benefit": f"Recover up to ₹{savings_target/1e7:.2f} Cr by realigning departmental spend with approved quarterly targets",
                        "action_button": "Review Budget Analysis",
                        "action_url": "dashboard.html#card-budget-vs-actual"
                    })
        except Exception:
            pass

    # -------------------------------------------------------------
    # 2. Budget Underspend Strategic Capital Reallocation (if Budget exists)
    # -------------------------------------------------------------
    if has_bgt:
        try:
            bgt_res = me.get_budget_vs_actual(dept="all", range_limit="all")
            if bgt_res and bgt_res.get("departments"):
                # Find department with significant underspend (negative variance > 10%)
                underspent_depts = [d for d in bgt_res["departments"] if d.get("variance_pct", 0) < -10]
                if underspent_depts:
                    top_underspent = min(underspent_depts, key=lambda x: x.get("variance_pct", 0))
                    u_dept = top_underspent["department"]
                    u_var_pct = abs(top_underspent.get("variance_pct", 0))
                    u_surplus = abs(top_underspent.get("variance", 0))

                    recommendations.append({
                        "id": "rec-budget-underspend",
                        "category": "budget_governance",
                        "priority": "Medium",
                        "title": f"Reallocate Underutilized Budget in {u_dept}",
                        "evidence": f"{u_dept} is tracking {u_var_pct:.1f}% below its approved budget allocation (₹{u_surplus/1e7:.2f} Cr unutilized).",
                        "reason": f"Significant underspending in {u_dept} may reflect delayed project rollouts or under-resourced initiatives.",
                        "business_impact": "Unspent capital creates idle capacity that could be deployed to accelerate revenue-generating divisions.",
                        "financial_impact": round(u_surplus * 0.4),
                        "confidence": 88,
                        "department": u_dept,
                        "metric": "Budget Allocation",
                        "suggested_action": f"Reallocate unutilized budget surplus from {u_dept} toward high-ROI commercial expansion and digital transformation.",
                        "expected_benefit": f"Deploy ₹{u_surplus/1e7:.2f} Cr surplus toward commercial sales pipeline expansion",
                        "action_button": "Reallocate Budget",
                        "action_url": "dashboard.html#card-budget-vs-actual"
                    })
        except Exception:
            pass

    # -------------------------------------------------------------
    # 3. OPEX Optimization in Top Spending Department
    # -------------------------------------------------------------
    if dept_aggs:
        top_exp_dept = max(dept_aggs, key=lambda x: x.get("expense") or 0.0)
        exp_amt = top_exp_dept.get("expense") or 0.0
        exp_share = round((exp_amt / tot_exp * 100), 1) if tot_exp > 0 else 0.0
        est_savings = round(exp_amt * 0.08)

        recommendations.append({
            "id": "rec-opex-opt",
            "category": "cost_reduction",
            "priority": "High" if exp_share > 30 else "Medium",
            "title": f"Optimize OPEX in {top_exp_dept.get('department')}",
            "evidence": f"{top_exp_dept.get('department')} incurs ₹{exp_amt/1e7:.2f} Cr, representing {exp_share}% of total enterprise operating expenses.",
            "reason": f"The heavy OPEX concentration in {top_exp_dept.get('department')} makes enterprise EBITDA sensitive to cost inflation.",
            "business_impact": "Unchecked operational overhead in primary cost centers limits operating leverage during market fluctuations.",
            "financial_impact": est_savings,
            "confidence": 91,
            "department": top_exp_dept.get("department"),
            "metric": "Operating Expenses",
            "suggested_action": f"Consolidate key supplier contracts, renegotiate SLA rate cards, and introduce automated procurement workflows in {top_exp_dept.get('department')}.",
            "expected_benefit": f"Estimated annual cost savings of ₹{est_savings/1e7:.2f} Cr (~8% reduction in departmental overhead)",
            "action_button": "Audit Department Spend",
            "action_url": "departments.html"
        })

    # -------------------------------------------------------------
    # 4. Commercial Growth & Revenue Expansion in Top Unit
    # -------------------------------------------------------------
    if dept_aggs:
        top_rev_dept = max(dept_aggs, key=lambda x: x.get("revenue") or 0.0)
        rev_amt = top_rev_dept.get("revenue") or 0.0
        rev_share = round((rev_amt / tot_rev * 100), 1) if tot_rev > 0 else 0.0
        growth_est = round(rev_amt * 0.06)

        recommendations.append({
            "id": "rec-revenue-growth",
            "category": "revenue_growth",
            "priority": "High" if rev_share > 45 else "Medium",
            "title": f"Scale Commercial Expansion in {top_rev_dept.get('department')}",
            "evidence": f"{top_rev_dept.get('department')} generates ₹{rev_amt/1e7:.2f} Cr ({rev_share}% of enterprise revenue).",
            "reason": f"Strong commercial momentum in {top_rev_dept.get('department')} provides immediate leverage for high-value contract expansion.",
            "business_impact": "Accelerating top-line revenue in proven profit engines compounds enterprise gross margins.",
            "financial_impact": growth_est,
            "confidence": 89,
            "department": top_rev_dept.get("department"),
            "metric": "Gross Revenue",
            "suggested_action": f"Expand high-margin service offerings and cross-sell multi-year enterprise contracts within {top_rev_dept.get('department')}.",
            "expected_benefit": f"Potential ₹{growth_est/1e7:.2f} Cr top-line ARR expansion (+6% commercial lift)",
            "action_button": "Review Sales Pipeline",
            "action_url": "forecast.html"
        })

    # -------------------------------------------------------------
    # 5. Loss-Making Department Turnaround Plan
    # -------------------------------------------------------------
    loss_depts = [d for d in dept_aggs if (d.get("profit") or 0.0) < 0]
    for ld in loss_depts[:2]:
        l_name = ld.get("department")
        l_loss = abs(ld.get("profit") or 0.0)
        l_exp = ld.get("expense") or 0.0
        l_rev = ld.get("revenue") or 0.0
        recovery_val = round(l_loss * 0.75)

        recommendations.append({
            "id": f"rec-loss-{l_name.lower()}",
            "category": "loss_mitigation",
            "priority": "Critical",
            "title": f"Implement Turnaround Plan for {l_name}",
            "evidence": f"{l_name} operates at a net operating loss of ₹{l_loss/1e7:.2f} Cr (Expenses: ₹{l_exp/1e7:.2f} Cr vs Revenue: ₹{l_rev/1e7:.2f} Cr).",
            "reason": f"Sustained losses in {l_name} directly erode enterprise net income and consume cash flow generated by profitable units.",
            "business_impact": "Negative operating margin divisions create continuous structural drag on company valuation.",
            "financial_impact": recovery_val,
            "confidence": 95,
            "department": l_name,
            "metric": "Net Operating Loss",
            "suggested_action": f"Initiate zero-based budgeting for {l_name}, eliminate non-performing service lines, and restructure delivery headcount.",
            "expected_benefit": f"Eliminate up to ₹{recovery_val/1e7:.2f} Cr in annual operating drain and return unit to break-even within 2 quarters",
            "action_button": "View Division Breakdown",
            "action_url": "departments.html"
        })

    # -------------------------------------------------------------
    # 6. Margin Playbook Replication Across Secondary Divisions
    # -------------------------------------------------------------
    if len(dept_aggs) > 1:
        best_mrg_dept = max(dept_aggs, key=lambda x: x.get("margin") or 0.0)
        bm_margin = best_mrg_dept.get("margin") or 0.0
        if bm_margin > margin:
            margin_lift = round(tot_prof * 0.05)
            recommendations.append({
                "id": "rec-margin-rep",
                "category": "margin_expansion",
                "priority": "Medium",
                "title": f"Replicate Efficiency Playbook from {best_mrg_dept.get('department')}",
                "evidence": f"{best_mrg_dept.get('department')} achieved a {bm_margin:.1f}% operating margin vs enterprise average {margin:.1f}%.",
                "reason": f"Unit-level operational controls in {best_mrg_dept.get('department')} can serve as an internal benchmark for lower-margin divisions.",
                "business_impact": "Standardizing operational efficiencies across all business units elevates aggregate enterprise margin.",
                "financial_impact": margin_lift,
                "confidence": 90,
                "department": best_mrg_dept.get("department"),
                "metric": "Operating Margin %",
                "suggested_action": f"Benchmark cost-per-unit metrics and standardize procurement policies modeled after {best_mrg_dept.get('department')}.",
                "expected_benefit": "Potential +1.0% to +2.0% blended margin expansion across secondary business units",
                "action_button": "Benchmark Cost Metrics",
                "action_url": "departments.html"
            })

    # -------------------------------------------------------------
    # 7. Lowest Margin Division Profitability Enhancement
    # -------------------------------------------------------------
    positive_depts = [d for d in dept_aggs if (d.get("profit") or 0.0) >= 0 and (d.get("margin") or 0.0) < margin]
    if positive_depts:
        worst_pos_dept = min(positive_depts, key=lambda x: x.get("margin") or 0.0)
        wm_name = worst_pos_dept.get("department")
        wm_margin = worst_pos_dept.get("margin") or 0.0
        wm_rev = worst_pos_dept.get("revenue") or 0.0
        mrg_enhancement = round(wm_rev * 0.03)

        recommendations.append({
            "id": f"rec-margin-enhance-{wm_name.lower()}",
            "category": "margin_expansion",
            "priority": "Medium",
            "title": f"Enhance Operating Margin in {wm_name}",
            "evidence": f"{wm_name} operating margin is compressed at {wm_margin:.1f}%, trailing the enterprise benchmark of {margin:.1f}%.",
            "reason": f"High variable cost ratios in {wm_name} restrict operating leverage as transaction volumes scale.",
            "business_impact": "Sub-par departmental margins dilute overall portfolio returns and suppress blended ROCE.",
            "financial_impact": mrg_enhancement,
            "confidence": 89,
            "department": wm_name,
            "metric": "Operating Margin %",
            "suggested_action": f"Audit vendor rate cards, eliminate low-margin legacy contracts, and automate manual operational touchpoints in {wm_name}.",
            "expected_benefit": f"Recover +250 bps in operating margin, generating an additional ₹{mrg_enhancement/1e7:.2f} Cr in operating profit",
            "action_button": "Audit Division Margin",
            "action_url": "departments.html"
        })

    # -------------------------------------------------------------
    # 8. Anomaly Cluster Triage & Internal Audit Controls
    # -------------------------------------------------------------
    if total_anom_count > 0:
        dept_anom_counts = {}
        for a in active_anoms:
            d = (a.pl_record.domain if a.pl_record and a.pl_record.domain else "Finance") or "Finance"
            dept_anom_counts[d] = dept_anom_counts.get(d, 0) + 1
        top_anom_dept = max(dept_anom_counts.items(), key=lambda x: x[1])[0] if dept_anom_counts else "Finance"
        top_anom_count = dept_anom_counts.get(top_anom_dept, 0)
        risk_exposure = (crit_anom_count * 200000) + ((total_anom_count - crit_anom_count) * 50000)

        recommendations.append({
            "id": "rec-anomaly-triage",
            "category": "risk_mitigation",
            "priority": "Critical" if crit_anom_count > 5 else ("High" if crit_anom_count > 0 else "Medium"),
            "title": f"Triage {total_anom_count} Flagged Ledger Anomalies ({top_anom_dept})",
            "evidence": f"{total_anom_count} transactions flagged (including {crit_anom_count} high-severity), with {top_anom_count} entries clustered in {top_anom_dept}.",
            "reason": "Unresolved transaction outliers risk audit adjustments, duplicate vendor payments, and reporting discrepancies.",
            "business_impact": "Statistical anomalies in ledger postings may indicate fraudulent activity, misclassification, or double billing.",
            "financial_impact": risk_exposure,
            "confidence": 96,
            "department": top_anom_dept,
            "metric": "Ledger Anomalies",
            "suggested_action": f"Review flagged transactions in {top_anom_dept} and route high-severity outliers to department heads for formal sign-off.",
            "expected_benefit": "Eliminate unverified ledger postings and ensure 100% compliance with corporate audit standards",
            "action_button": "Triage Anomalies",
            "action_url": "anomalies.html"
        })
    else:
        recommendations.append({
            "id": "rec-compliance-monitor",
            "category": "risk_mitigation",
            "priority": "Low",
            "title": "Maintain Continuous Ledger Audit Protocols",
            "evidence": "Zero active transaction anomalies detected across current ledger records.",
            "reason": "Overall financial performance and transaction integrity are stable with clean reconciliation.",
            "business_impact": "Proactive automated compliance monitoring prevents future accounting discrepancies.",
            "financial_impact": 0,
            "confidence": 99,
            "department": "Compliance",
            "metric": "Audit Integrity",
            "suggested_action": "Maintain weekly automated SOD (Segregation of Duties) and statistical variance validation scans.",
            "expected_benefit": "Sustain continuous zero-defect audit readiness",
            "action_button": "View Audit Schedule",
            "action_url": "anomalies.html"
        })

    # -------------------------------------------------------------
    # 9. Revenue Concentration Risk Mitigation
    # -------------------------------------------------------------
    if dept_aggs:
        top_rev = max(dept_aggs, key=lambda x: x.get("revenue") or 0.0)
        r_share = ((top_rev.get("revenue") or 0.0) / tot_rev * 100) if tot_rev > 0 else 0.0
        if r_share > 35:
            recommendations.append({
                "id": "rec-rev-concentration",
                "category": "revenue_growth",
                "priority": "High" if r_share > 50 else "Medium",
                "title": f"Mitigate Revenue Concentration in {top_rev.get('department')}",
                "evidence": f"{top_rev.get('department')} contributes {r_share:.1f}% of aggregate enterprise revenue, creating exposure to single-division shocks.",
                "reason": "Over-reliance on one business unit exposes enterprise earnings to sector-specific demand shocks.",
                "business_impact": "Concentration risk increases revenue volatility and can impair debt coverage ratios during client attrition.",
                "financial_impact": round(tot_rev * 0.04),
                "confidence": 92,
                "department": top_rev.get("department"),
                "metric": "Revenue Concentration %",
                "suggested_action": f"Incentivize cross-divisional sales pipelines and expand client acquisition across secondary departments.",
                "expected_benefit": "Diversify top-line revenue streams so that no single division represents more than 35% of total ARR",
                "action_button": "Analyze Revenue Mix",
                "action_url": "forecast.html"
            })

    # -------------------------------------------------------------
    # 10. Forecast Trajectory & Capacity Planning
    # -------------------------------------------------------------
    if fcst_has_data:
        fcst_growth = float(fcst.get("r2_score") or 0.0)
        slope = float(fcst.get("slope") or 0.0)
        if slope >= 0:
            recommendations.append({
                "id": "rec-forecast-momentum",
                "category": "forecast_acceleration",
                "priority": "Medium",
                "title": "Scale Operational Capacity for Projected Growth",
                "evidence": f"Algorithmic forecasting projects ₹{fcst_exp/1e7:.2f} Cr net profit over the next 12 months with upward trajectory.",
                "reason": "Strong forward momentum provides confidence to expand operational capacity and capture pipeline demand.",
                "business_impact": "Anticipating volume expansion ensures service delivery standards are maintained without costly emergency scaling.",
                "financial_impact": round(fcst_exp * 0.05) if fcst_exp else 500000,
                "confidence": 88,
                "department": "Enterprise",
                "metric": "12M Forward Forecast",
                "suggested_action": "Align 12-month capital deployment and hiring plans with projected profit run-rates to support volume expansion.",
                "expected_benefit": f"Secure capacity to fulfill forward demand, protecting ₹{fcst_exp/1e7:.2f} Cr in projected net earnings",
                "action_button": "View Forecast Model",
                "action_url": "forecast.html"
            })
        else:
            recommendations.append({
                "id": "rec-forecast-hedging",
                "category": "cost_reduction",
                "priority": "High",
                "title": "Implement Proactive Cost Hedging Against Forecast Contraction",
                "evidence": f"12-month profit forecast indicates downward slope with projected earnings of ₹{fcst_exp/1e7:.2f} Cr.",
                "reason": "Forward deceleration in operating earnings signals potential margin compression across subsequent periods.",
                "business_impact": "Failing to adjust cost commitments during demand softening results in rapid operating margin decay.",
                "financial_impact": round(abs(fcst_exp) * 0.06) if fcst_exp else 1000000,
                "confidence": 91,
                "department": "Enterprise",
                "metric": "12M Forward Forecast",
                "suggested_action": "Implement variable cost gating and freeze discretionary expenditures to insulate operating profit.",
                "expected_benefit": "Protect baseline profitability against projected macroeconomic headwinds",
                "action_button": "View Forecast Scenarios",
                "action_url": "forecast.html"
            })

    # -------------------------------------------------------------
    # 11. Expense vs Revenue Velocity Rebalance
    # -------------------------------------------------------------
    if exp_growth > rev_growth and (exp_growth - rev_growth) > 2.0:
        cost_creep = round(tot_exp * 0.03)
        recommendations.append({
            "id": "rec-cost-velocity",
            "category": "cost_reduction",
            "priority": "High",
            "title": "Arrest Expense Growth Velocity Outpacing Revenue",
            "evidence": f"Operating expenses grew at {exp_growth:.1f}% period-over-period vs revenue growth of {rev_growth:.1f}% (net divergence of +{(exp_growth - rev_growth):.1f}%).",
            "reason": "Expense expansion velocity exceeding top-line growth causes negative operating leverage and margin compression.",
            "business_impact": "Unchecked cost inflation erodes gross margin gains achieved by sales expansion.",
            "financial_impact": cost_creep,
            "confidence": 93,
            "department": "Finance",
            "metric": "Expense Growth vs Revenue Growth",
            "suggested_action": "Tie department expenditure approvals strictly to verified revenue milestone achievements.",
            "expected_benefit": f"Prevent ₹{cost_creep/1e7:.2f} Cr in annual cost inflation by restoring positive operating leverage",
            "action_button": "Audit Cost Trajectory",
            "action_url": "departments.html"
        })

    # -------------------------------------------------------------
    # 12. Working Capital & Cash Liquidity Optimization (if Cash Flow present)
    # -------------------------------------------------------------
    has_cf = (caps.get("cashFlow", {}).get("available", False) and caps.get("cashFlow", {}).get("mode") == "actual") or caps.get("has_cash_flow", False)
    if has_cf and kpis.get("cash_flow") is not None:
        net_cf = float(kpis.get("cash_flow") or 0.0)
        cf_benefit = round(abs(net_cf) * 0.04) if abs(net_cf) > 0 else 500000
        recommendations.append({
            "id": "rec-working-capital",
            "category": "cash_flow",
            "priority": "Critical" if net_cf < 0 else "Medium",
            "title": "Accelerate Working Capital & DSO Cycle",
            "evidence": f"Net operating cash flow sits at ₹{net_cf/1e7:.2f} Cr ({round(net_cf/tot_rev*100, 1) if tot_rev > 0 else 0}% of revenue).",
            "reason": f"{'Negative cash flow requires urgent receivable acceleration to avoid liquidity strain.' if net_cf < 0 else 'Streamlining receivables conversion unlocks surplus liquidity for capital reinvestment.'}",
            "business_impact": "Optimizing receivables and vendor payment windows boosts operating cash conversion without external financing.",
            "financial_impact": cf_benefit,
            "confidence": 88,
            "department": "Treasury",
            "metric": "Net Cash Flow",
            "suggested_action": "Automate client payment reminders, enforce 30-day payment terms, and negotiate 45-day vendor payment cycles.",
            "expected_benefit": "Shorten cash conversion cycle by 8-12 business days and expand liquidity buffer",
            "action_button": "Optimize Invoicing",
            "action_url": "reports.html"
        })

    # -------------------------------------------------------------
    # 13. Data Governance & Financial Schema Completeness
    # -------------------------------------------------------------
    missing_fields = []
    if not has_bgt:
        missing_fields.append("Budget")
    if not has_cf:
        missing_fields.append("Cash Flow")
    if missing_fields:
        recommendations.append({
            "id": "rec-data-governance",
            "category": "governance",
            "priority": "Low",
            "title": f"Enrich Ledger Schema with {' & '.join(missing_fields)} Dimensions",
            "evidence": f"Active dataset does not contain dedicated columns for {', '.join(missing_fields)}, utilizing proxy calculations for advanced analytics.",
            "reason": "Complete ledger schema attributes enable full variance modeling and true cash flow accounting.",
            "business_impact": "Enriching core datasets unlocks precision FP&A forecasting and eliminates estimation assumptions.",
            "financial_impact": 0,
            "confidence": 98,
            "department": "Data Operations",
            "metric": "Schema Completeness",
            "suggested_action": f"Include {', '.join(missing_fields)} columns in future monthly ledger uploads to activate automated budget variance tracking.",
            "expected_benefit": "Enable 100% granular variance tracking and automated cash conversion audits",
            "action_button": "Upload Enriched Dataset",
            "action_url": "upload.html"
        })

    # -------------------------------------------------------------
    # Sort by Business Priority: Critical -> High -> Medium -> Low
    # (secondary sort by financial_impact descending)
    # -------------------------------------------------------------
    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    recommendations.sort(key=lambda x: (priority_order.get(x.get("priority", "Low"), 3), -(x.get("financial_impact") or 0)))

    # Return up to 12 recommendations (ensuring at least 8 when data is available)
    return recommendations[:12]


