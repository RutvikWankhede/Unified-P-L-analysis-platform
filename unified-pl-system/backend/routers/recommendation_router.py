from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.recommendation import Recommendation
from models.audit_log import AuditLog, AuditActionType
from schemas.anomaly_schemas import RecommendationResponse
from services.recommendation_engine import generate_recommendations
from core.security import require_role, get_current_user
from models.user import User

router = APIRouter()

class ReasonPayload(BaseModel):
    reason: str
    
class ModifyPayload(BaseModel):
    reason: str
    modifications: dict


@router.post(
    "/generate/{anomaly_id}",
    response_model=List[RecommendationResponse],
    status_code=201,
    dependencies=[Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER", "DEPARTMENT_HEAD"]))]
)
def create_recommendations(anomaly_id: int, db: Session = Depends(get_db)):
    from services.cache_service import invalidate_global_cache

    invalidate_global_cache()

    recs = generate_recommendations(db, anomaly_id)
    return recs


@router.get("/{anomaly_id}", response_model=List[RecommendationResponse], dependencies=[Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "Viewer"]))])
def get_recommendations(anomaly_id: int, db: Session = Depends(get_db)):
    from services.pl_service import ensure_demo_data
    from services.cache_service import get_cached_item, set_cached_item

    ensure_demo_data(db)

    cache_key = f"recommendations_{anomaly_id}"
    cached = get_cached_item(cache_key)
    if cached is not None:
        return cached

    recs = (
        db.query(Recommendation).filter(Recommendation.anomaly_id == anomaly_id).all()
    )
    set_cached_item(cache_key, recs)
    return recs

@router.get("", response_model=list, dependencies=[Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "Viewer"]))])
async def get_all_recommendations(db: Session = Depends(get_db)):
    import asyncio
    from fastapi import HTTPException
    
    def _fetch_recommendations():
        from services.pl_service import ensure_demo_data
        from services.cache_service import get_cached_item, set_cached_item
        from services.metric_engine import MetricEngine
        from sqlalchemy import func
        from models.pl_record import PLRecord
        from models.anomaly import Anomaly

        ensure_demo_data(db)
        
        from routers.datasets_router import get_active_dataset_id
        ds_id = get_active_dataset_id(db)
        me = MetricEngine(db, ds_id)
        
        kpis = me.get_kpis()
        dept_aggs = me.get_department_aggregates()
        trends = kpis.get("trends", {})
        
        tot_rev = kpis.get("revenue") or 0.0
        tot_exp = kpis.get("expense") or 0.0
        tot_prof = kpis.get("profit") or (tot_rev - tot_exp)
        margin = kpis.get("profit_margin") or ((tot_prof / tot_rev * 100) if tot_rev > 0 else 0.0)

        anom_query = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id).filter(Anomaly.status != "Resolved")
        if ds_id:
            anom_query = anom_query.filter(PLRecord.upload_id == ds_id)
        active_anom_count = anom_query.count()
        crit_anom_count = anom_query.filter(Anomaly.severity.in_(["Critical", "High"])).count()
        
        recommendations = []
        
        # 1. OPEX Optimization in Top Spending Department
        if dept_aggs:
            top_exp_dept = max(dept_aggs, key=lambda x: x.get("expense") or 0)
            exp_amt = top_exp_dept.get("expense") or 0
            exp_share = round((exp_amt / tot_exp * 100), 1) if tot_exp > 0 else 0
            savings_est = round(exp_amt * 0.08)
            recommendations.append({
                "category": "cost_reduction",
                "priority": "High" if exp_share > 30 else "Medium",
                "title": f"Optimize OPEX in {top_exp_dept.get('department')}",
                "reason": f"{top_exp_dept.get('department')} accounts for {exp_share}% of enterprise OPEX (₹{exp_amt/1e7:.2f} Cr). Vendor contract consolidation can yield immediate savings.",
                "financial_impact": savings_est,
                "confidence": 92,
                "suggested_action": f"Renegotiate top vendor contracts and streamline {top_exp_dept.get('department')} procurement.",
                "expected_benefit": f"Estimated savings of ₹{savings_est/1e7:.2f} Cr (8-10% cost reduction)",
                "action_button": "Audit Department Spend",
                "department": top_exp_dept.get("department")
            })

        # 2. Commercial Funnel & Pricing Optimization
        if dept_aggs:
            top_rev_dept = max(dept_aggs, key=lambda x: x.get("revenue") or 0)
            rev_amt = top_rev_dept.get("revenue") or 0
            rev_share = round((rev_amt / tot_rev * 100), 1) if tot_rev > 0 else 0
            lift_est = round(rev_amt * 0.05)
            recommendations.append({
                "category": "revenue_growth",
                "priority": "High",
                "title": f"Expand Commercial Momentum in {top_rev_dept.get('department')}",
                "reason": f"{top_rev_dept.get('department')} drives {rev_share}% of enterprise gross income (₹{rev_amt/1e7:.2f} Cr). Up-selling and revised contract pricing could accelerate growth.",
                "financial_impact": lift_est,
                "confidence": 88,
                "suggested_action": "Reallocate top commercial resources and optimize pricing tiers.",
                "expected_benefit": f"Projected ₹{lift_est/1e7:.2f} Cr incremental revenue (+5% ARR lift)",
                "action_button": "Review Sales Pipeline",
                "department": top_rev_dept.get("department")
            })

        # 3. High-Margin Playbook Replication
        if len(dept_aggs) > 1:
            best_margin_dept = max(dept_aggs, key=lambda x: x.get("margin") or 0)
            bm_margin = best_margin_dept.get("margin") or 0
            recommendations.append({
                "category": "margin_expansion",
                "priority": "Medium",
                "title": f"Replicate Efficiency Model from {best_margin_dept.get('department')}",
                "reason": f"{best_margin_dept.get('department')} achieved an outstanding {bm_margin:.1f}% operating margin, outperforming the {margin:.1f}% enterprise average.",
                "financial_impact": round(tot_prof * 0.06),
                "confidence": 90,
                "suggested_action": "Implement standardized unit-cost controls across other operational departments.",
                "expected_benefit": "Potential +1.5% to +2.5% increase in blended operating margin",
                "action_button": "Benchmark Cost Metrics",
                "department": best_margin_dept.get("department")
            })

        # 4. Statistical Anomaly & Risk Mitigation
        if active_anom_count > 0:
            risk_impact = crit_anom_count * 150000 + (active_anom_count - crit_anom_count) * 40000
            recommendations.append({
                "category": "risk_mitigation",
                "priority": "High" if crit_anom_count > 0 else "Medium",
                "title": f"Triage {active_anom_count} Unresolved Ledger Anomalies",
                "reason": f"{active_anom_count} anomalous ledger transactions flagged by ML detection (including {crit_anom_count} high-severity outliers).",
                "financial_impact": risk_impact,
                "confidence": 96,
                "suggested_action": "Trigger Camunda approval workflow for outlier transaction verification.",
                "expected_benefit": "Prevent unverified ledger postings and audit non-compliance fines",
                "action_button": "Triage Anomalies",
                "department": "Finance & Audit"
            })
        else:
            recommendations.append({
                "category": "compliance",
                "priority": "Low",
                "title": "Continuous Ledger Quality Monitoring",
                "reason": "All transaction entries currently comply with expected variance thresholds. Maintain automated audits.",
                "financial_impact": 0,
                "confidence": 99,
                "suggested_action": "Schedule monthly automated SOD and ledger audit reviews.",
                "expected_benefit": "Maintain zero-defect compliance posture",
                "action_button": "View Audit Schedule",
                "department": "Compliance"
            })

        # 5. Working Capital & Cash Conversion Optimization
        net_cf = kpis.get("cash_flow") or tot_prof
        cf_impact = round(net_cf * 0.04) if net_cf > 0 else 500000
        recommendations.append({
            "category": "cash_flow",
            "priority": "Medium",
            "title": "Streamline Working Capital & Collection Cycle",
            "reason": f"Current net cash flow is ₹{net_cf/1e7:.2f} Cr. Optimizing DSO (Days Sales Outstanding) can unlock additional liquid headroom.",
            "financial_impact": cf_impact,
            "confidence": 85,
            "suggested_action": "Automate client invoice follow-ups and enforce stricter 30-day payment terms.",
            "expected_benefit": "Shorten cash conversion cycle by 7-10 business days",
            "action_button": "Optimize Invoicing",
            "department": "Treasury"
        })

        # 6. Budget Variance Oversight
        recommendations.append({
            "category": "budget_governance",
            "priority": "Medium",
            "title": "Enforce Real-Time Budgetary Controls",
            "reason": "Ensure department expenditures stay strictly within allocated quarterly thresholds to safeguard EBITDA.",
            "financial_impact": round(tot_exp * 0.03),
            "confidence": 91,
            "suggested_action": "Institute pre-spend budget checks for expenditures exceeding ₹5,00,000.",
            "expected_benefit": "Eliminate unbudgeted departmental expense overruns",
            "action_button": "Review Budget Limits",
            "department": "Operations"
        })

        return recommendations

    return await asyncio.to_thread(_fetch_recommendations)

@router.post("/{recommendation_id}/approve")
def approve_recommendation(
    recommendation_id: int, 
    payload: ReasonPayload, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER"]))
):
    # Logic to approve
    # Record audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action_type=AuditActionType.APPROVE,
        resource_type="Recommendation",
        resource_id=recommendation_id,
        description=f"Approved recommendation {recommendation_id}: {payload.reason}"
    ))
    db.commit()
    return {"status": "approved", "recommendation_id": recommendation_id}

@router.post("/{recommendation_id}/reject")
def reject_recommendation(
    recommendation_id: int, 
    payload: ReasonPayload, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER"]))
):
    # Record audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action_type=AuditActionType.REJECT,
        resource_type="Recommendation",
        resource_id=recommendation_id,
        description=f"Rejected recommendation {recommendation_id}: {payload.reason}"
    ))
    db.commit()
    return {"status": "rejected", "recommendation_id": recommendation_id}

@router.post("/{recommendation_id}/modify")
def modify_recommendation(
    recommendation_id: int, 
    payload: ModifyPayload, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER"]))
):
    # Record audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action_type=AuditActionType.UPDATE,
        resource_type="Recommendation",
        resource_id=recommendation_id,
        description=f"Modified recommendation {recommendation_id}: {payload.reason}",
        metadata_json=payload.modifications
    ))
    db.commit()
    return {"status": "modified", "recommendation_id": recommendation_id}
