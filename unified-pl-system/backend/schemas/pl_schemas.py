from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class PLRecordBase(BaseModel):
    domain: str
    period: str
    line_item: str
    amount: float
    currency: Optional[str] = "USD"
    cost_center: Optional[str] = None
    dynamic_data: Optional[Dict[str, Any]] = None


class PLRecordCreate(PLRecordBase):
    pass


class PLRecordResponse(PLRecordBase):
    id: int
    upload_id: str
    uploaded_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    upload_id: str
    records_ingested: int
    message: str
    workflow_process_id: Optional[str] = None


class DomainSummary(BaseModel):
    domain: str
    total_amount: float
    record_count: int


class SummaryResponse(BaseModel):
    total_records: int
    domains: List[DomainSummary]
