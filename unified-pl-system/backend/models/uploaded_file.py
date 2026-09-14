from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(
        String, default="UPLOADED"
    )  # UPLOADED, PROCESSING, COMPLETED, FAILED
    is_seeded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
