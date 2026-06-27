from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base

class PLRecord(Base):
    __tablename__ = "pl_records"

    id = Column(Integer, primary_key=True)
    upload_id = Column(String(36), nullable=False, index=True)
    domain = Column(String(50), nullable=False)
    period = Column(String(20), nullable=False)
    line_item = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    cost_center = Column(String(50), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
