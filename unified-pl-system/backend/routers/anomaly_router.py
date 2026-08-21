from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from repositories.anomaly_repository import (
    get_anomalies,
    get_anomaly,
    update_anomaly_status,
)
from schemas.anomaly_schemas import (
    AnomalyDetail,
    AnomalyResponse,
    AnomalyUpdateStatus,
    DetectionResult,
)
from services.anomaly_service import run_anomaly_detection
from models.anomaly import Anomaly

router = APIRouter()


@router.post("/detect", response_model=DetectionResult, status_code=201)
def detect_anomalies_endpoint(upload_id: str, db: Session = Depends(get_db)):
    from services.cache_service import invalidate_global_cache

    invalidate_global_cache()

    anomalies = run_anomaly_detection(db, upload_id)
    high = sum(1 for a in anomalies if a.severity == "High")
    med = sum(1 for a in anomalies if a.severity == "Medium")
    low = sum(1 for a in anomalies if a.severity == "Low")
    return {
        "upload_id": upload_id,
        "anomalies_detected": len(anomalies),
        "high_severity_count": high,
        "medium_severity_count": med,
        "low_severity_count": low,
    }


@router.get("/trend")
def get_anomaly_trend(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from models.pl_record import PLRecord
    
    # We want anomalies count per month. Let's group by detected_at month, or pl_record period.
    # Since anomalies are usually current, maybe group by date(detected_at).
    query = db.query(
        func.date(Anomaly.detected_at).label("date"),
        func.count(Anomaly.id).label("count")
    )
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)
    if active_id:
        query = query.join(PLRecord, PLRecord.id == Anomaly.pl_record_id).filter(PLRecord.upload_id == active_id)
    
    results = query.group_by(func.date(Anomaly.detected_at)).order_by("date").all()
    
    # Format as list of dicts
    trend = [{"date": str(r.date), "count": r.count} for r in results]
    
    # If no data, return mock 6 months for UI visual testing (as instructed not to fake numbers, but if DB is empty we might just return empty)
    return {"trend": trend}

@router.get("/", response_model=List[AnomalyResponse])
async def get_anomalies_list(skip: int = 0, limit: int = 100, agg: str = None, db: Session = Depends(get_db)):
    import asyncio
    from services.pl_service import ensure_demo_data
    from services.cache_service import get_cached_item, set_cached_item

    def _fetch():
        try:
            ensure_demo_data(db)

            from routers.datasets_router import get_active_dataset_id
            active_id = get_active_dataset_id(db) or "default"
            cache_key = f"anomalies_{active_id}_{skip}_{limit}_{agg}"
            cached = get_cached_item(cache_key)
            if cached is not None:
                return cached

            res = get_anomalies(db, skip, limit, agg)
            for anomaly in res:
                if anomaly.pl_record:
                    anomaly.line_item = anomaly.pl_record.line_item
                    anomaly.department = anomaly.pl_record.domain
                    anomaly.impact_amount = anomaly.pl_record.amount
                    anomaly.description = (
                        f"{anomaly.pl_record.line_item} is {anomaly.severity.lower()} severity "
                        f"({anomaly.percentile_rank * 100:.1f}th percentile) due to unexpected "
                        f"{anomaly.pl_record.amount} amount in {anomaly.pl_record.domain} domain."
                    )
            set_cached_item(cache_key, res)
            return res
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to fetch anomalies: {e}")
            return []

    return await asyncio.to_thread(_fetch)


@router.get("/{id}", response_model=AnomalyDetail)
def get_anomaly_detail(id: int, db: Session = Depends(get_db)):
    anomaly = get_anomaly(db, id)
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return anomaly


@router.patch("/{id}/status", response_model=AnomalyResponse)
def update_status(
    id: int, status_update: AnomalyUpdateStatus, db: Session = Depends(get_db)
):
    from services.cache_service import invalidate_global_cache

    invalidate_global_cache()

    updated = update_anomaly_status(db, id, status_update.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return updated
