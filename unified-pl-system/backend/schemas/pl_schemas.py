from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class PLRecordBase(BaseModel):
    domain: str
    period: str
    line_item: str
    amount: float
    currency: Optional[str] = "USD"
    cost_center: Optional[str] = None

class PLRecordCreate(PLRecordBase):
    pass

class PLRecordResponse(PLRecordBase):
    id: int
    upload_id: str
    uploaded_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    upload_id: str
    records_ingested: int
    message: str

class DomainSummary(BaseModel):
    domain: str
    total_amount: float
    record_count: int

class SummaryResponse(BaseModel):
    total_records: int
    domains: List[DomainSummary]
