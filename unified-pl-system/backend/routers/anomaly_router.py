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

router = APIRouter()


@router.post("/detect", response_model=DetectionResult, status_code=201)
def detect_anomalies_endpoint(upload_id: str, db: Session = Depends(get_db)):
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


@router.get("/", response_model=List[AnomalyResponse])
def get_anomalies_list(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_anomalies(db, skip, limit)


@router.get("/{id}", response_model=AnomalyDetail)
def get_anomaly_detail(id: int, db: Session = Depends(get_db)):
    anomaly = get_anomaly(db, id)
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    # Due to relationships, assuming pl_record is loaded or lazy loaded
    return anomaly


@router.patch("/{id}/status", response_model=AnomalyResponse)
def update_status(
    id: int, status_update: AnomalyUpdateStatus, db: Session = Depends(get_db)
):
    updated = update_anomaly_status(db, id, status_update.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return updated
