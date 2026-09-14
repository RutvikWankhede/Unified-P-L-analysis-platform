"""
Deterministic, Data-Driven Insight Engine for Enterprise P&L Analytics.

Generates 3 to 8 schema-aware, prioritized management insights strictly derived
from the active dataset metrics, trends, department performance, budget variance,
anomalies, and forecast trajectory.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from services.metric_engine import MetricEngine
from services.analytics_engine import AnalyticsEngine
from models.anomaly import Anomaly
from models.pl_record import PLRecord


class InsightEngine:
    def __init__(self, db: Session, active_dataset_id: Optional[str] = None):
        self.db = db
        self.active_dataset_id = active_dataset_id
        self.me = MetricEngine(db, active_dataset_id)
        self.ae = AnalyticsEngine(self.me)

    def generate_insights(self) -> List[Dict[str, Any]]:
        """
        Generate 3-8 prioritized, evidence-based management insights
        strictly grounded in the active dataset.
        """
        kpis = self.me.get_kpis()
        dept_aggs = self.me.get_department_aggregates()
        trends = kpis.get("trends", {})
        caps = self.me.get_capabilities()

        tot_rev = float(kpis.get("revenue") or 0.0)
        tot_exp = float(kpis.get("expense") or 0.0)
        tot_prof = float(kpis.get("profit") or (tot_rev - tot_exp))
        margin = float(kpis.get("profit_margin") or ((tot_prof / tot_rev * 100) if tot_rev > 0 else 0.0))
        health = float(kpis.get("health_score") or 85.0)

        rev_growth = float(trends.get("revenue", 0.0) or 0.0)
        exp_growth = float(trends.get("expense", 0.0) or 0.0)
        prof_growth = float(trends.get("profit", 0.0) or 0.0)
        margin_growth = float(trends.get("profit_margin", 0.0) or 0.0)

        # Anomaly metrics
        anom_q = self.db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id).filter(Anomaly.status != "Resolved")
        if self.active_dataset_id:
            anom_q = anom_q.filter(PLRecord.upload_id == self.active_dataset_id)
        active_anoms = anom_q.all()
        total_anom_count = len(active_anoms)
        crit_anom_count = sum(1 for a in active_anoms if a.severity in ["Critical", "High"])

        # Candidate insights list with priority scoring (lower score = higher priority)
        candidates = []

        # -------------------------------------------------------------
        # 1. Critical Financial Risk: Loss-Making Departments (Priority: 10)
        # -------------------------------------------------------------
        if dept_aggs:
            loss_depts = [d for d in dept_aggs if (d.get("profit") or 0.0) < 0]
            if loss_depts:
                worst_dept = min(loss_depts, key=lambda x: x.get("profit") or 0.0)
                loss_amt = abs(worst_dept.get("profit") or 0.0)
                candidates.append({
                    "priority_score": 10,
                    "id": "ins-loss-making",
                    "title": f"Loss-Making Operation: {worst_dept.get('department')}",
                    "category": "Risk",
                    "severity": "CRITICAL",
                    "badge": "CRITICAL RISK",
                    "department": worst_dept.get("department", "Enterprise"),
                    "metric": "Operating Deficit",
                    "current_value": -loss_amt,
                    "previous_value": 0.0,
                    "change_pct": round(((worst_dept.get('expense', 0) - worst_dept.get('revenue', 0)) / worst_dept.get('expense', 1) * 100), 1) if worst_dept.get('expense', 0) > 0 else 0.0,
                    "evidence": f"{worst_dept.get('department')} generated ₹{worst_dept.get('revenue', 0)/1e7:.2f} Cr revenue against ₹{worst_dept.get('expense', 0)/1e7:.2f} Cr expenses, producing a ₹{loss_amt/1e7:.2f} Cr operating loss (margin: {worst_dept.get('margin', 0):.1f}%).",
                    "why_it_matters": "Operating deficits directly drain enterprise cash flow and depress blended return on invested capital.",
                    "suggested_action": f"Initiate a structural operational audit of {worst_dept.get('department')} and freeze discretionary spend."
                })

        # -------------------------------------------------------------
        # 2. Major Budget Variance (Priority: 20) — ONLY IF BUDGET FIELD EXISTS
        # -------------------------------------------------------------
        has_bgt = caps.get("budget", {}).get("available", False) or caps.get("has_budget", False)
        if has_bgt:
            try:
                bgt_res = self.me.get_budget_vs_actual(dept="all", range_limit="all")
                if bgt_res and bgt_res.get("departments"):
                    total_var = bgt_res.get("total_variance", 0.0)
                    total_var_pct = bgt_res.get("total_variance_pct", 0.0)
                    highest_var_dept = bgt_res.get("highest_variance_dept")
                    highest_var_pct = bgt_res.get("highest_variance_pct", 0.0)

                    if total_var > 0:
                        candidates.append({
                            "priority_score": 20,
                            "id": "ins-budget-overrun",
                            "title": f"Budget Overrun: {highest_var_dept} (+{highest_var_pct:.1f}%)" if highest_var_dept else "Enterprise Budget Overrun",
                            "category": "Budget",
                            "severity": "HIGH IMPACT",
                            "badge": "BUDGET OVERRUN",
                            "department": highest_var_dept or "Enterprise",
                            "metric": "Budget Variance",
                            "current_value": total_var,
                            "previous_value": 0.0,
                            "change_pct": total_var_pct,
                            "evidence": f"Total actual expenses exceed budget target by ₹{abs(total_var)/1e7:.2f} Cr (+{total_var_pct:.1f}%). {highest_var_dept} recorded the highest variance at +{highest_var_pct:.1f}%.",
                            "why_it_matters": "Unplanned budget variance erodes operating margins and indicates weak procurement spend discipline.",
                            "suggested_action": f"Implement mandatory threshold spend approvals for {highest_var_dept} and enforce department budget limits."
                        })
                    elif total_var < 0:
                        candidates.append({
                            "priority_score": 50,
                            "id": "ins-budget-discipline",
                            "title": "Favorable Budget Governance",
                            "category": "Budget",
                            "severity": "POSITIVE",
                            "badge": "ON BUDGET",
                            "department": "Enterprise",
                            "metric": "Budget Variance",
                            "current_value": total_var,
                            "previous_value": 0.0,
                            "change_pct": total_var_pct,
                            "evidence": f"Actual spend is ₹{abs(total_var)/1e7:.2f} Cr ({abs(total_var_pct):.1f}%) below allocated budget targets with {bgt_res.get('on_budget_count', 0)} departments operating within budget.",
                            "why_it_matters": "Effective budget governance maintains healthy cash liquidity and supports capital allocation.",
                            "suggested_action": "Reinvest surplus savings into strategic commercial initiatives."
                        })
            except Exception:
                pass

        # -------------------------------------------------------------
        # 3. Margin Compression / Deterioration (Priority: 25)
        # -------------------------------------------------------------
        if exp_growth > rev_growth and exp_growth > 0:
            candidates.append({
                "priority_score": 25,
                "id": "ins-margin-compression",
                "title": "Operating Margin Compression Warning",
                "category": "Margin",
                "severity": "HIGH IMPACT",
                "badge": "MARGIN PRESSURE",
                "department": "Enterprise",
                "metric": "Growth Differential",
                "current_value": margin,
                "previous_value": margin - margin_growth,
                "change_pct": margin_growth,
                "evidence": f"Operating expenses grew at {exp_growth:.1f}%, outpacing top-line revenue growth of {rev_growth:.1f}% by {(exp_growth - rev_growth):.1f} percentage points.",
                "why_it_matters": "Negative operating leverage shrinks profit margins and reduces EBITDA conversion.",
                "suggested_action": "Freeze non-essential operational expenses and review vendor contract pricing to restore margin targets."
            })
        elif margin_growth > 1.0:
            candidates.append({
                "priority_score": 45,
                "id": "ins-margin-expansion",
                "title": f"Operating Margin Expansion (+{margin_growth:.1f}%)",
                "category": "Margin",
                "severity": "POSITIVE",
                "badge": "EXPANSION",
                "department": "Enterprise",
                "metric": "Operating Margin %",
                "current_value": margin,
                "previous_value": margin - margin_growth,
                "change_pct": margin_growth,
                "evidence": f"Operating margin expanded by +{margin_growth:.1f}% to {margin:.1f}%, demonstrating positive operating leverage.",
                "why_it_matters": "Expanding margins generate excess free cash flow and increase enterprise valuation.",
                "suggested_action": "Maintain disciplined unit economics while scaling top-line commercial activity."
            })

        # -------------------------------------------------------------
        # 4. Anomaly Concentration & Outliers (Priority: 30)
        # -------------------------------------------------------------
        if total_anom_count > 0:
            dept_anom_counts = {}
            for a in active_anoms:
                d = (a.pl_record.domain if a.pl_record and a.pl_record.domain else "General") or "General"
                dept_anom_counts[d] = dept_anom_counts.get(d, 0) + 1
            top_anom_dept = max(dept_anom_counts.items(), key=lambda x: x[1])[0] if dept_anom_counts else "Enterprise"
            top_anom_dept_count = dept_anom_counts.get(top_anom_dept, 0)
            top_anom_dept_pct = round((top_anom_dept_count / total_anom_count * 100), 1) if total_anom_count > 0 else 0.0

            candidates.append({
                "priority_score": 30,
                "id": "ins-anomaly-concentration",
                "title": f"Ledger Anomaly Cluster: {top_anom_dept} ({top_anom_dept_count} flagged)",
                "category": "Risk",
                "severity": "HIGH IMPACT" if crit_anom_count > 0 else "MEDIUM IMPACT",
                "badge": "AUDIT ALERT" if crit_anom_count > 0 else "REVIEW",
                "department": top_anom_dept,
                "metric": "Active Anomalies",
                "current_value": total_anom_count,
                "previous_value": 0,
                "change_pct": 0.0,
                "evidence": f"{total_anom_count} transaction anomalies detected (including {crit_anom_count} high-severity outliers). {top_anom_dept} accounts for {top_anom_dept_pct}% ({top_anom_dept_count} entries).",
                "why_it_matters": "Clustered ledger anomalies indicate potential double-billing, invoice discrepancies, or internal control bypasses.",
                "suggested_action": f"Audit flagged transaction batches in {top_anom_dept} and route high-severity outliers through Camunda verification."
            })
        else:
            candidates.append({
                "priority_score": 80,
                "id": "ins-clean-audit",
                "title": "Zero Ledger Anomalies Detected",
                "category": "Risk",
                "severity": "POSITIVE",
                "badge": "COMPLIANT",
                "department": "Compliance",
                "metric": "Ledger Quality",
                "current_value": 100.0,
                "previous_value": 100.0,
                "change_pct": 0.0,
                "evidence": "All ledger postings conform strictly to statistical variance thresholds with zero unresolved transaction outliers.",
                "why_it_matters": "Zero anomaly state reflects robust transaction hygiene and strong internal financial controls.",
                "suggested_action": "Maintain scheduled automated statistical audit scans."
            })

        # -------------------------------------------------------------
        # 5. OPEX Concentration in Top Spending Department (Priority: 35)
        # -------------------------------------------------------------
        if dept_aggs:
            top_exp_dept = max(dept_aggs, key=lambda x: x.get("expense") or 0.0)
            exp_amt = top_exp_dept.get("expense") or 0.0
            exp_share = round((exp_amt / tot_exp * 100), 1) if tot_exp > 0 else 0.0

            candidates.append({
                "priority_score": 35,
                "id": "ins-opex-concentration",
                "title": f"OPEX Concentration: {top_exp_dept.get('department')} ({exp_share}%)",
                "category": "Expenses",
                "severity": "HIGH IMPACT" if exp_share > 35 else "MEDIUM IMPACT",
                "badge": "COST CONCENTRATION",
                "department": top_exp_dept.get("department", "Enterprise"),
                "metric": "Department OPEX Share",
                "current_value": exp_amt,
                "previous_value": 0.0,
                "change_pct": exp_share,
                "evidence": f"{top_exp_dept.get('department')} accounts for ₹{exp_amt/1e7:.2f} Cr ({exp_share}%) of total enterprise OPEX (₹{tot_exp/1e7:.2f} Cr).",
                "why_it_matters": "High expense concentration creates structural vulnerability to cost inflation in that division.",
                "suggested_action": f"Consolidate vendor contracts and introduce volume discounting across {top_exp_dept.get('department')} suppliers."
            })

        # -------------------------------------------------------------
        # 6. Revenue Concentration / Top Commercial Engine (Priority: 40)
        # -------------------------------------------------------------
        if dept_aggs:
            top_rev_dept = max(dept_aggs, key=lambda x: x.get("revenue") or 0.0)
            rev_amt = top_rev_dept.get("revenue") or 0.0
            rev_share = round((rev_amt / tot_rev * 100), 1) if tot_rev > 0 else 0.0

            candidates.append({
                "priority_score": 40,
                "id": "ins-revenue-concentration",
                "title": f"Revenue Engine: {top_rev_dept.get('department')} ({rev_share}%)",
                "category": "Revenue",
                "severity": "HIGH IMPACT" if rev_share > 50 else "POSITIVE",
                "badge": "PRIMARY ENGINE",
                "department": top_rev_dept.get("department", "Enterprise"),
                "metric": "Revenue Contribution",
                "current_value": rev_amt,
                "previous_value": 0.0,
                "change_pct": rev_share,
                "evidence": f"{top_rev_dept.get('department')} generates ₹{rev_amt/1e7:.2f} Cr, representing {rev_share}% of total enterprise revenue (₹{tot_rev/1e7:.2f} Cr).",
                "why_it_matters": f"{'Enterprise top-line is heavily dependent on a single department.' if rev_share > 50 else 'Strong commercial performance underpins enterprise cash generation.'}",
                "suggested_action": f"Scale pipeline investment in {top_rev_dept.get('department')} while diversifying revenue streams across secondary departments."
            })

        # -------------------------------------------------------------
        # 7. High-Margin Outperformer Benchmark (Priority: 42)
        # -------------------------------------------------------------
        if len(dept_aggs) > 1:
            best_mrg_dept = max(dept_aggs, key=lambda x: x.get("margin") or 0.0)
            bm_margin = best_mrg_dept.get("margin") or 0.0
            if bm_margin > margin:
                candidates.append({
                    "priority_score": 42,
                    "id": "ins-margin-benchmark",
                    "title": f"Efficiency Benchmark: {best_mrg_dept.get('department')} ({bm_margin:.1f}%)",
                    "category": "Margin",
                    "severity": "POSITIVE",
                    "badge": "BENCHMARK",
                    "department": best_mrg_dept.get("department", "Enterprise"),
                    "metric": "Operating Margin %",
                    "current_value": bm_margin,
                    "previous_value": margin,
                    "change_pct": round(bm_margin - margin, 1),
                    "evidence": f"{best_mrg_dept.get('department')} achieved a {bm_margin:.1f}% operating margin, outperforming the enterprise average of {margin:.1f}% by {(bm_margin - margin):.1f} pts.",
                    "why_it_matters": "Demonstrates proven operating efficiency model within current organizational structure.",
                    "suggested_action": f"Replicate operational workflows and cost controls from {best_mrg_dept.get('department')} into other business units."
                })

        # -------------------------------------------------------------
        # 8. Forecast Trajectory & Projected Profitability (Priority: 48)
        # -------------------------------------------------------------
        try:
            fcst = self.ae.get_forecast("Overall", metric="profit", n_forecast=12)
            if fcst.get("has_enough_data"):
                proj_val = float(fcst.get("expected_case") or 0.0)
                fcst_growth = 0.0
                hist = fcst.get("historical", [])
                if hist and fcst.get("forecast"):
                    last_hist = hist[-1].get("profit", tot_prof)
                    if last_hist and last_hist > 0:
                        fcst_growth = round(((fcst["forecast"][-1]["predicted_value"] - last_hist) / last_hist) * 100, 1)
                
                candidates.append({
                    "priority_score": 48,
                    "id": "ins-forecast-trajectory",
                    "title": f"12-Month Profit Trajectory: ₹{proj_val/1e7:.2f} Cr ({'+' if fcst_growth >= 0 else ''}{fcst_growth:.1f}%)",
                    "category": "Forecast",
                    "severity": "POSITIVE" if fcst_growth >= 0 else "WARNING",
                    "badge": "PROJECTED TREND",
                    "department": "Enterprise",
                    "metric": "Projected Profit",
                    "current_value": proj_val,
                    "previous_value": tot_prof,
                    "change_pct": fcst_growth,
                    "evidence": f"Algorithmic forecasting models project ₹{proj_val/1e7:.2f} Cr profit over the next 12 months ({'+' if fcst_growth >= 0 else ''}{fcst_growth:.1f}% vs baseline, confidence: {round(fcst.get('confidence_score', 0.9)*100)}%).",
                    "why_it_matters": "Forecasted trajectory informs forward capital expenditure, hiring capacity, and debt servicing.",
                    "suggested_action": "Align quarterly budget allocations to supported forecast momentum."
                })
        except Exception:
            pass

        # -------------------------------------------------------------
        # 9. Cash Flow & Working Capital (Priority: 55) — ONLY IF CASH FLOW DATA PRESENT
        # -------------------------------------------------------------
        has_cf = (caps.get("cashFlow", {}).get("available", False) and caps.get("cashFlow", {}).get("mode") == "actual") or caps.get("has_cash_flow", False)
        if has_cf and kpis.get("cash_flow") is not None:
            net_cf = float(kpis.get("cash_flow") or 0.0)
            candidates.append({
                "priority_score": 55,
                "id": "ins-cash-flow",
                "title": "Positive Net Operating Cash Flow" if net_cf >= 0 else "Negative Operating Cash Flow Alert",
                "category": "Cash Flow",
                "severity": "POSITIVE" if net_cf >= 0 else "HIGH IMPACT",
                "badge": "HEALTHY LIQUIDITY" if net_cf >= 0 else "LIQUIDITY ALERT",
                "department": "Treasury",
                "metric": "Net Cash Flow",
                "current_value": net_cf,
                "previous_value": 0.0,
                "change_pct": round((net_cf / tot_rev * 100), 1) if tot_rev > 0 else 0.0,
                "evidence": f"Net operating cash flow stands at ₹{net_cf/1e7:.2f} Cr ({round((net_cf/tot_rev*100), 1) if tot_rev > 0 else 0}% of gross revenue).",
                "why_it_matters": "Cash liquidity guarantees debt obligations, supplier settlements, and payroll stability.",
                "suggested_action": f"{'Deploy excess liquidity into high-yield treasury vehicles.' if net_cf >= 0 else 'Accelerate collections and extend payable terms to preserve liquidity.'}"
            })

        # Sort candidates by priority score and return top 3 to 8
        candidates.sort(key=lambda x: x["priority_score"])
        selected = candidates[:8]

        # Format output fields for both frontend dashboard cards, modals, reports, and copilot
        formatted = []
        for c in selected:
            formatted.append({
                "id": c["id"],
                "title": c["title"],
                "category": c["category"],
                "severity": c["severity"],
                "badge": c["badge"],
                "department": c["department"],
                "metric": c["metric"],
                "current_value": c["current_value"],
                "previous_value": c["previous_value"],
                "change_pct": c["change_pct"],
                "evidence": c["evidence"],
                "why_it_matters": c["why_it_matters"],
                "interpretation": c["why_it_matters"],
                "description": c["evidence"],
                "suggested_action": c["suggested_action"],
                "recommended_action": c["suggested_action"]
            })

        return formatted
