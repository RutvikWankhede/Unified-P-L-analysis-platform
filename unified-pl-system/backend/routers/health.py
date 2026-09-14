import time

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
start_time = time.time()


class HealthResponse(BaseModel):
    status: str
    service: str = "Unified P&L Intelligence Platform"
    uptime: float
    version: str


@router.get("/health", response_model=HealthResponse)
def health_check():
    uptime = time.time() - start_time
    return {
        "status": "ok",
        "service": "Unified P&L Intelligence Platform",
        "uptime": round(uptime, 2),
        "version": "1.0.0",
    }


@router.get("/metrics")
def get_metrics():
    # In a real enterprise app, integrate Prometheus metrics here
    return {"active_users": 0, "anomalies_detected_today": 0, "workflows_running": 0}


from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from fastapi import Depends, HTTPException
import traceback

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    from datetime import datetime
    import os
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "sqlite",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": os.getenv("API_VERSION", "1.0.0"),
            "uptime": time.time() - start_time
        }
    except Exception as e:
        print(f"Readiness check failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=503, detail="Database not ready")
