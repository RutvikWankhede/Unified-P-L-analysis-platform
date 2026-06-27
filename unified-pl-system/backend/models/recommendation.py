from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    anomaly_id = Column(Integer, ForeignKey("anomalies.id"))
    priority = Column(Integer, nullable=False) # 1-5
    action_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    action_owner = Column(String(100), nullable=False)
    sod_flag = Column(Boolean, default=False)
    estimated_impact = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=func.now())

class Explanation(Base):
    __tablename__ = "explanations"

    id = Column(Integer, primary_key=True)
    anomaly_id = Column(Integer, ForeignKey("anomalies.id"), unique=True)
    state_hash = Column(String(64), nullable=False)
    explanation_text = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True)
    business_impact = Column(Text, nullable=True)
    model_version = Column(String(20), default="gpt-4")
    generated_at = Column(DateTime, default=func.now())
    tokens_used = Column(Integer, nullable=True)
