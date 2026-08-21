import enum
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, Enum
from sqlalchemy.sql import func

from database import Base


class AuditActionType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VIEW = "VIEW"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action_type = Column(Enum(AuditActionType), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(200), nullable=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    metadata_json = Column(JSON, nullable=True)
