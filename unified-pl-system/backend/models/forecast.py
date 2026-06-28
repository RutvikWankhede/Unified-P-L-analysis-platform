from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True)
    target_period = Column(String, index=True)
    predicted_amount = Column(Float)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    model_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
