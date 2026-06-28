from typing import List

from sqlalchemy.orm import Session

from models.pl_record import PLRecord
from schemas.pl_schemas import PLRecordCreate


def create_pl_records(
    db: Session, records: List[PLRecordCreate], upload_id: str, user_id: int
):
    db_records = [
        PLRecord(**record.model_dump(), upload_id=upload_id, uploaded_by=user_id)
        for record in records
    ]
    db.add_all(db_records)
    db.commit()
    return db_records


def get_pl_records_by_upload_id(db: Session, upload_id: str):
    return db.query(PLRecord).filter(PLRecord.upload_id == upload_id).all()


def get_pl_records(db: Session, skip: int = 0, limit: int = 100):
    return db.query(PLRecord).offset(skip).limit(limit).all()


def get_pl_record(db: Session, record_id: int):
    return db.query(PLRecord).filter(PLRecord.id == record_id).first()
