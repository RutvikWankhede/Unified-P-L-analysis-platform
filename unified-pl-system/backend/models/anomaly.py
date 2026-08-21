from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from sqlalchemy.orm import relationship
from database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True)
    pl_record_id = Column(Integer, ForeignKey("pl_records.id"), index=True)
    anomaly_score = Column(Float, nullable=False)
    severity = Column(String(10), nullable=False)
    is_anomaly = Column(Boolean, nullable=False)
    percentile_rank = Column(Float, nullable=False)
    status = Column(String(20), default="open")
    detected_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)

    pl_record = relationship("PLRecord")
