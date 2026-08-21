from sqlalchemy import Column, String, Float, Integer
from database import Base

class DomainSettings(Base):
    __tablename__ = "domain_settings"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True, unique=True, nullable=False)
    contamination_rate = Column(Float, nullable=False, default=0.05)
