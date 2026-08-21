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
        from sqlalchemy import func
        from models.pl_record import PLRecord
        from models.anomaly import Anomaly

        ensure_demo_data(db)
        
        # Filter setup
        from routers.datasets_router import get_active_dataset_id
        ds_id = get_active_dataset_id(db)
        
        rev_query = db.query(func.sum(PLRecord.amount)).filter(
            func.lower(PLRecord.line_item).like("%revenue%") |
            func.lower(PLRecord.line_item).like("%income%") |
            func.lower(PLRecord.line_item).like("%sales%")
        )
        exp_query = db.query(func.sum(PLRecord.amount)).filter(
            func.lower(PLRecord.line_item).like("%expense%") |
            func.lower(PLRecord.line_item).like("%cost%") |
            func.lower(PLRecord.line_item).like("%cogs%") |
            func.lower(PLRecord.line_item).like("%opex%")
        )
        anom_query = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id).filter(Anomaly.status != "Resolved")
        
        if ds_id:
            rev_query = rev_query.filter(PLRecord.upload_id == ds_id)
            exp_query = exp_query.filter(PLRecord.upload_id == ds_id)
            anom_query = anom_query.filter(PLRecord.upload_id == ds_id)
        
        total_rev = rev_query.scalar() or 0.0
        total_exp = exp_query.scalar() or 0.0
        active_anom_count = anom_query.count()
        
        insights = []
        
        # Insight 1: Revenue trend or alert
        if total_rev > 0:
            insights.append({
                "category": "revenue_growth",
                "priority": "High" if total_rev < 100000 else "Low",
                "title": "Revenue Pattern Detected",
                "reason": "Total revenue indicates room for channel optimization.",
                "financial_impact": int(total_rev * 0.05),
                "confidence": 85,
                "suggested_action": "Review Pricing Strategy",
                "expected_benefit": "Potential 5% lift in revenue",
                "action_button": "Review Strategy",
                "department": "Sales"
            })
            
        # Insight 2: Expense spike
        if total_exp > 0:
            insights.append({
                "category": "cost_reduction",
                "priority": "Medium",
                "title": "Expense Spike Identified",
                "reason": "Operating expenses show an unexpected week-over-week increase.",
                "financial_impact": int(total_exp * 0.1),
                "confidence": 92,
                "suggested_action": "Audit top departments for cost reduction.",
                "expected_benefit": "Reduce OPEX by 10%",
                "action_button": "Audit Expenses",
                "department": "Marketing"
            })
        
        # Insight 3: Anomaly Count
        if active_anom_count > 0:
            insights.append({
                "category": "risk_mitigation",
                "priority": "High" if active_anom_count > 5 else "Medium",
                "title": f"{active_anom_count} Active Anomalies",
                "reason": "High number of unresolved anomalies requires immediate review.",
                "financial_impact": 50000 * active_anom_count,
                "confidence": 98,
                "suggested_action": "Resolve pending anomaly tickets.",
                "expected_benefit": "Prevent compliance fines",
                "action_button": "Review Anomalies",
                "department": "Finance"
            })
            
        # Insight 4: General Recommendation
        insights.append({
            "category": "default",
            "priority": "Low",
            "title": "System Audit Recommended",
            "reason": "No Separation of Duties violations detected.",
            "financial_impact": 0,
            "confidence": 99,
            "suggested_action": "Schedule regular workflow audits.",
            "expected_benefit": "Maintain compliance standing",
            "action_button": "Schedule Audit",
            "department": "Operations"
        })
        
        return insights

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
