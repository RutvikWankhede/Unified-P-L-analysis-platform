"""
tools.py - Controlled Financial Tool Registry for Agentic Execution
====================================================================
Wraps existing deterministic analytical and ML engines into clean,
parameter-validated, active-dataset-scoped tools for AI Agents.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from services.metric_engine import MetricEngine
from services.analytics_engine import AnalyticsEngine
from services.insight_engine import InsightEngine
from services.recommendation_engine import generate_enterprise_recommendations
from services.forecast_agent import generate_forecast
from ml.isolation_forest import detect_anomalies
from models.pl_record import PLRecord
from models.anomaly import Anomaly
from routers.datasets_router import get_active_dataset_id, get_active_dataset
from core.dataset_context import runtime_dataset_context

logger = logging.getLogger(__name__)


class AgentToolsRegistry:
    """Registry of controlled financial analytics tools for autonomous agents."""

    @staticmethod
    def get_active_dataset_info(db: Session) -> Dict[str, Any]:
        """Tool: Get metadata of the currently active runtime dataset."""
        active_id = get_active_dataset_id(db)
        info = get_active_dataset(db)
        return {
            "dataset_id": active_id,
            "filename": info.get("filename", "Active Dataset"),
            "is_seed": info.get("is_seed", False),
            "record_count": info.get("record_count", 0),
            "date_range": info.get("date_range", {}),
            "departments_count": info.get("departments_count", 0),
        }

    @staticmethod
    def get_kpis(db: Session, dept: Optional[str] = None) -> Dict[str, Any]:
        """
        Tool: Get authoritative enterprise or departmental KPIs (Revenue, Expense, Profit, Margin).
        Grounded strictly in the active dataset via MetricEngine.
        """
        active_id = get_active_dataset_id(db)
        me = MetricEngine(db, active_id)
        kpis = me.get_kpis()
        caps = me.get_capabilities()

        if dept and dept.lower() not in ["all", "overall", "all departments", ""]:
            dept_aggs = me.get_department_aggregates()
            target = next((d for d in dept_aggs if d["department"].lower() == dept.lower()), None)
            if target:
                return {
                    "scope": f"Department: {target['department']}",
                    "revenue": target["revenue"],
                    "expense": target["expense"],
                    "profit": target["profit"],
                    "margin": target["margin"],
                    "record_count": target.get("record_count", 0),
                    "dataset_id": active_id,
                    "evidence": f"Calculated over active records for {target['department']}",
                }

        return {
            "scope": "Enterprise Total",
            "revenue": float(kpis.get("revenue") or 0.0),
            "expense": float(kpis.get("expense") or 0.0),
            "profit": float(kpis.get("profit") or 0.0),
            "margin": float(kpis.get("profit_margin") or 0.0),
            "health_score": int(kpis.get("health_score") or 85),
            "trends": kpis.get("trends", {}),
            "dataset_id": active_id,
            "capabilities": caps,
            "evidence": f"Grounded in active dataset {active_id}",
        }

    @staticmethod
    def get_department_analysis(
        db: Session,
        metric: str = "profit",
        limit: int = 10,
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Tool: Get departmental breakdown, ranked by revenue, expense, profit, or margin,
        enriched with canonical 1-indexed ascending and descending ranks.
        """
        active_id = get_active_dataset_id(db)
        me = MetricEngine(db, active_id)
        depts = me.get_department_aggregates()

        norm_metric = metric.lower().strip()
        if norm_metric not in ["revenue", "expense", "profit", "margin"]:
            norm_metric = "profit"

        # Compute canonical rankings across all dimensions
        by_prof_desc = sorted(depts, key=lambda x: x.get("profit", 0.0), reverse=True)
        by_rev_desc = sorted(depts, key=lambda x: x.get("revenue", 0.0), reverse=True)
        by_exp_desc = sorted(depts, key=lambda x: x.get("expense", 0.0), reverse=True)
        by_mrg_desc = sorted(depts, key=lambda x: (x.get("margin") is not None, x.get("margin") or 0.0), reverse=True)

        n_total = len(depts)
        enriched_depts = []
        for d in depts:
            d_name = d["department"]
            prof_rank_desc = next((i + 1 for i, item in enumerate(by_prof_desc) if item["department"] == d_name), n_total)
            prof_rank_asc = n_total - prof_rank_desc + 1

            rev_rank_desc = next((i + 1 for i, item in enumerate(by_rev_desc) if item["department"] == d_name), n_total)
            rev_rank_asc = n_total - rev_rank_desc + 1

            exp_rank_desc = next((i + 1 for i, item in enumerate(by_exp_desc) if item["department"] == d_name), n_total)
            exp_rank_asc = n_total - exp_rank_desc + 1

            mrg_rank_desc = next((i + 1 for i, item in enumerate(by_mrg_desc) if item["department"] == d_name), n_total)
            mrg_rank_asc = n_total - mrg_rank_desc + 1

            enriched = dict(d)
            enriched.update({
                "profit_rank_descending": prof_rank_desc,  # 1 = most profitable
                "profit_rank_ascending": prof_rank_asc,    # 1 = least profitable
                "revenue_rank_descending": rev_rank_desc,  # 1 = highest revenue
                "revenue_rank_ascending": rev_rank_asc,    # 1 = lowest revenue
                "expense_rank_descending": exp_rank_desc,  # 1 = highest expense
                "expense_rank_ascending": exp_rank_asc,    # 1 = lowest expense
                "margin_rank_descending": mrg_rank_desc,   # 1 = highest margin
                "margin_rank_ascending": mrg_rank_asc,     # 1 = lowest margin
            })
            enriched_depts.append(enriched)

        reverse = (sort_order.lower() == "desc")
        sorted_depts = sorted(enriched_depts, key=lambda x: x.get(norm_metric, 0.0) if norm_metric != "margin" else (x.get("margin") is not None, x.get("margin") or 0.0), reverse=reverse)
        sliced = sorted_depts[:limit]

        return {
            "ranked_metric": norm_metric,
            "sort_order": sort_order,
            "total_departments": len(depts),
            "departments": sliced,
            "all_ranked_departments": enriched_depts,
            "rankings": sliced,
            "dataset_id": active_id,
            "top_performer": sorted_depts[0] if sorted_depts else None,
            "lowest_performer": sorted_depts[-1] if sorted_depts else None,
        }

    @staticmethod
    def compare_periods(
        db: Session,
        dept: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tool: Compare monthly/quarterly financial periods to isolate trend shifts and growth rates.
        """
        active_id = get_active_dataset_id(db)
        me = MetricEngine(db, active_id)
        trend_df = me.aggregate_data(aggregation="monthly", dept=dept)

        if trend_df.empty or len(trend_df) < 2:
            return {"error": "Insufficient period records for comparison", "periods": []}

        periods = []
        for _, row in trend_df.iterrows():
            rev = float(row.get("revenue", 0.0) or 0.0)
            exp = float(row.get("expense", 0.0) or 0.0)
            prof = float(row.get("profit", rev - exp) or 0.0)
            mrg = (prof / rev * 100) if rev > 0 else 0.0
            periods.append({
                "period": str(row["period"]),
                "revenue": rev,
                "expense": exp,
                "profit": prof,
                "margin": mrg,
            })

        p_curr = periods[-1]
        p_prev = periods[-2]
        rev_change = ((p_curr["revenue"] - p_prev["revenue"]) / p_prev["revenue"] * 100) if p_prev["revenue"] > 0 else 0.0
        exp_change = ((p_curr["expense"] - p_prev["expense"]) / p_prev["expense"] * 100) if p_prev["expense"] > 0 else 0.0
        prof_change = ((p_curr["profit"] - p_prev["profit"]) / abs(p_prev["profit"]) * 100) if p_prev["profit"] != 0 else 0.0
        margin_delta = p_curr["margin"] - p_prev["margin"]

        return {
            "current_period": p_curr,
            "previous_period": p_prev,
            "revenue_change_abs": round(p_curr["revenue"] - p_prev["revenue"], 2),
            "expense_change_abs": round(p_curr["expense"] - p_prev["expense"], 2),
            "profit_change_abs": round(p_curr["profit"] - p_prev["profit"], 2),
            "revenue_change_pct": round(rev_change, 2),
            "expense_change_pct": round(exp_change, 2),
            "profit_change_pct": round(prof_change, 2),
            "margin_delta_pp": round(margin_delta, 2),
            "all_periods": periods,
            "dataset_id": active_id,
        }

    @staticmethod
    def run_forecast(
        db: Session,
        dept: Optional[str] = None,
        metric: str = "profit",
        horizon: int = 3
    ) -> Dict[str, Any]:
        """
        Tool: Run predictive linear/polynomial regression forecast for upcoming periods.
        """
        active_id = get_active_dataset_id(db)
        target_domain = dept if dept and dept.lower() not in ["all", "overall", ""] else "All"
        fcst = generate_forecast(db, domain=target_domain, periods=horizon)
        return {
            "domain": target_domain,
            "horizon_periods": horizon,
            "forecast_result": fcst,
            "dataset_id": active_id,
        }

    @staticmethod
    def detect_anomalies_tool(
        db: Session,
        dept: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tool: Run Isolation Forest outlier detection across current dataset records.
        """
        active_id = get_active_dataset_id(db)
        query = db.query(PLRecord)
        if active_id:
            query = query.filter(PLRecord.upload_id == active_id)
        if dept and dept.lower() not in ["all", "overall", ""]:
            query = query.filter(PLRecord.domain.ilike(f"%{dept}%"))

        records = query.all()
        if not records:
            return {"total_anomalies": 0, "anomalies": [], "dataset_id": active_id}

        eval_records = records[:5000] if len(records) > 5000 else records
        anoms = detect_anomalies(eval_records, db=db)
        crit_count = sum(1 for a in anoms if a.get("severity") == "Critical")
        high_count = sum(1 for a in anoms if a.get("severity") == "High")

        return {
            "total_records_analyzed": len(records),
            "total_anomalies": len(anoms),
            "total_anomalies_detected": len(anoms),
            "critical_anomalies": crit_count,
            "high_anomalies": high_count,
            "anomalies": anoms,
            "top_anomalies": anoms[:10],
            "dataset_id": active_id,
        }

    @staticmethod
    def generate_insights_tool(db: Session) -> Dict[str, Any]:
        """
        Tool: Generate 3–8 prioritized, data-grounded strategic management insights.
        """
        active_id = get_active_dataset_id(db)
        ie = InsightEngine(db, active_id)
        insights = ie.generate_insights()
        return {
            "insights_count": len(insights),
            "insights": insights,
            "dataset_id": active_id,
        }

    @staticmethod
    def generate_recommendations_tool(db: Session) -> Dict[str, Any]:
        """
        Tool: Generate 8–12 actionable enterprise recommendations with expected financial impact.
        """
        active_id = get_active_dataset_id(db)
        recs = generate_enterprise_recommendations(db, active_id)
        return {
            "recommendations_count": len(recs),
            "recommendations": recs,
            "dataset_id": active_id,
        }

    @staticmethod
    def run_what_if_tool(
        db: Session,
        rev_growth_pct: float = 0.0,
        exp_growth_pct: float = 0.0,
        dept: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tool: Stress-test financial performance under revenue and expense shifts.
        """
        active_id = get_active_dataset_id(db)
        me = MetricEngine(db, active_id)
        kpis = me.get_kpis()

        base_rev = float(kpis.get("revenue") or 0.0)
        base_exp = float(kpis.get("expense") or 0.0)
        base_prof = base_rev - base_exp
        base_mrg = (base_prof / base_rev * 100) if base_rev > 0 else 0.0

        scen_rev = base_rev * (1.0 + (rev_growth_pct / 100.0))
        scen_exp = base_exp * (1.0 + (exp_growth_pct / 100.0))
        scen_prof = scen_rev - scen_exp
        scen_mrg = (scen_prof / scen_rev * 100) if scen_rev > 0 else 0.0

        profit_delta = scen_prof - base_prof
        margin_delta = scen_mrg - base_mrg

        scen_dict = {
            "rev_growth_pct": rev_growth_pct,
            "exp_growth_pct": exp_growth_pct,
            "revenue": scen_rev,
            "expense": scen_exp,
            "profit": scen_prof,
            "margin": scen_mrg,
        }

        return {
            "baseline": {
                "revenue": base_rev,
                "expense": base_exp,
                "profit": base_prof,
                "margin": base_mrg,
            },
            "scenario": scen_dict,
            "simulated": scen_dict,
            "impact": {
                "profit_delta": profit_delta,
                "margin_delta_pct": margin_delta,
                "is_profitable": scen_prof > 0,
            },
            "dataset_id": active_id,
        }


agent_tools = AgentToolsRegistry()
