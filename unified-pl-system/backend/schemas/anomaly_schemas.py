from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from schemas.pl_schemas import PLRecordResponse

class AnomalyBase(BaseModel):
    anomaly_score: float
    severity: str
    is_anomaly: bool
    percentile_rank: float
    status: str

class AnomalyResponse(AnomalyBase):
    id: int
    pl_record_id: int
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[int] = None

    class Config:
        from_attributes = True

class AnomalyDetail(AnomalyResponse):
    pl_record: PLRecordResponse

class DetectionResult(BaseModel):
    upload_id: str
    anomalies_detected: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int

class AnomalyStats(BaseModel):
    total_anomalies: int
    open_anomalies: int
    high_severity: int
    medium_severity: int
    low_severity: int

class AnomalyUpdateStatus(BaseModel):
    status: str

class AnomalyAssign(BaseModel):
    user_id: int

class ExplanationResponse(BaseModel):
    explanation_text: str
    root_cause: Optional[str] = None
    business_impact: Optional[str] = None
    model_version: str
    tokens_used: Optional[int] = None

class RecommendationResponse(BaseModel):
    id: int
    priority: int
    action_type: str
    description: str
    action_owner: str
    sod_flag: bool
    estimated_impact: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
