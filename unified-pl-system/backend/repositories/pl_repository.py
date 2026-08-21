from typing import List

from sqlalchemy.orm import Session

from models.pl_record import PLRecord


def create_pl_records(db: Session, mappings: List[dict], upload_id: str, user_id: int):
    if not mappings:
        return []

    # Add upload_id and user_id to each mapping
    for mapping in mappings:
        mapping["upload_id"] = upload_id
        mapping["uploaded_by"] = user_id

    try:
        db.bulk_insert_mappings(PLRecord, mappings)
        db.commit()
    except Exception:
        db.rollback()
        raise
    # Return lightweight count proxy (avoids re-querying all rows)
    return mappings


def get_pl_records(db: Session, skip: int = 0, limit: int = 100):
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)
    query = db.query(PLRecord)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    return query.offset(skip).limit(limit).all()

def get_pl_record(db: Session, record_id: int):
    return db.query(PLRecord).filter(PLRecord.id == record_id).first()

def get_pl_records_by_upload_id(db: Session, upload_id: str):
    return db.query(PLRecord).filter(PLRecord.upload_id == upload_id).all()
