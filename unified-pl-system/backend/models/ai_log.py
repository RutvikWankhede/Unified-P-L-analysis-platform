from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from database import Base


class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, index=True)  # e.g. 'Copilot', 'Forecast', 'DataQuality'
    action = Column(String)
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    status = Column(String, default="SUCCESS")
    created_at = Column(DateTime, default=datetime.utcnow)
