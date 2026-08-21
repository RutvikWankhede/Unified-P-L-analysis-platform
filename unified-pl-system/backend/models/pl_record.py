from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from database import Base


class PLRecord(Base):
    __tablename__ = "pl_records"

    id = Column(Integer, primary_key=True)
    upload_id = Column(String(36), nullable=False, index=True)
    domain = Column(String(50), nullable=False, index=True)
    period = Column(String(20), nullable=False, index=True)
    line_item = Column(String(100), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    cost_center = Column(String(50), nullable=True)
    dynamic_data = Column(JSON, default=dict)  # Dynamic schema support
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

class DepartmentBudget(Base):
    __tablename__ = "department_budgets"

    id = Column(Integer, primary_key=True)
    department = Column(String(50), nullable=False, unique=True, index=True)
    budget_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
