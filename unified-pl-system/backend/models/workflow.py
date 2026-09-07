from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base
import models.user  # Ensures User model is registered with SQLAlchemy mapper


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(Integer, primary_key=True, index=True)
    process_instance_id = Column(String, unique=True, index=True, nullable=False)
    workflow_name = Column(String, nullable=False)
    status = Column(String, index=True, default="ACTIVE")  # ACTIVE, RUNNING, PENDING_APPROVAL, COMPLETED, FAILED
    started_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    variables = Column(JSON, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")
