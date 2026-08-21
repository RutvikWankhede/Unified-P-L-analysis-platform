from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from database import Base


class SchemaMappingHistory(Base):
    __tablename__ = "schema_mapping_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    original_column = Column(String(100), nullable=False)
    mapped_column = Column(String(100), nullable=False)
    confidence = Column(Integer, default=100)
    sample_values = Column(String(500), nullable=True)  # new column
    currency_context = Column(String(10), nullable=True) # new column
    created_at = Column(DateTime, default=func.now())
