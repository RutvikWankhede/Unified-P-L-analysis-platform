from typing import List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from models.recommendation import Recommendation
from models.audit_log import AuditLog, AuditActionType
from schemas.anomaly_schemas import RecommendationResponse
from services.recommendation_engine import generate_recommendations
from core.security import require_role, get_current_user
from models.user import User

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class ReasonPayload(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)
    
class ModifyPayload(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)
    modifications: dict = Field(default_factory=dict)


@router.post(
    "/generate/{anomaly_id}",
    response_model=List[RecommendationResponse],
    status_code=201,
    dependencies=[Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER", "DEPARTMENT_HEAD"]))]
)
@limiter.limit("30/minute")
def create_recommendations(request: Request, anomaly_id: int, db: Session = Depends(get_db)):
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
    
    def _fetch_recommendations():
        from services.pl_service import ensure_demo_data
        from services.cache_service import get_cached_item, set_cached_item
        from services.recommendation_engine import generate_enterprise_recommendations
        from routers.datasets_router import get_active_dataset_id

        ensure_demo_data(db)
        ds_id = get_active_dataset_id(db) or "default"
        
        cache_key = f"all_recommendations_{ds_id}"
        cached = get_cached_item(cache_key)
        if cached is not None:
            return cached

        recs = generate_enterprise_recommendations(db, active_dataset_id=ds_id)
        set_cached_item(cache_key, recs)
        return recs

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
