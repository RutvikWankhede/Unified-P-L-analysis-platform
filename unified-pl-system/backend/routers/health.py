import time

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
start_time = time.time()


class HealthResponse(BaseModel):
    status: str
    uptime: float
    version: str


@router.get("/health", response_model=HealthResponse)
def health_check():
    uptime = time.time() - start_time
    return {"status": "ok", "uptime": uptime, "version": "1.0.0"}


@router.get("/metrics")
def get_metrics():
    # In a real enterprise app, integrate Prometheus metrics here
    return {"active_users": 0, "anomalies_detected_today": 0, "workflows_running": 0}
