from typing import List

from sqlalchemy.orm import Session, joinedload

from models.anomaly import Anomaly


def create_anomalies(db: Session, anomalies_data: List[dict]):
    db_anomalies = [Anomaly(**data) for data in anomalies_data]
    db.add_all(db_anomalies)
    db.commit()
    return db_anomalies


def get_anomalies(db: Session, skip: int = 0, limit: int = 100, agg: str = None):
    from models.pl_record import PLRecord
    from routers.datasets_router import get_active_dataset_id
    from sqlalchemy import func
    active_id = get_active_dataset_id(db)

    query = db.query(Anomaly).options(joinedload(Anomaly.pl_record))
    if active_id:
        query = query.join(PLRecord, PLRecord.id == Anomaly.pl_record_id).filter(PLRecord.upload_id == active_id)

    if agg and active_id:
        # Find the latest date/period in the active dataset
        max_p = db.query(func.max(PLRecord.period)).filter(PLRecord.upload_id == active_id).scalar()
        if max_p:
            year = max_p[:4]
            month = max_p[5:7] if len(max_p) >= 7 else "01"
            
            if agg == "monthly":
                query = query.filter(PLRecord.period.like(f"{year}-{month}%"))
            elif agg == "quarterly":
                try:
                    m_val = int(month)
                except ValueError:
                    m_val = 1
                if m_val <= 3:
                    months = ["01", "02", "03"]
                elif m_val <= 6:
                    months = ["04", "05", "06"]
                elif m_val <= 9:
                    months = ["07", "08", "09"]
                else:
                    months = ["10", "11", "12"]
                
                filters = [PLRecord.period.like(f"{year}-{m}%") for m in months]
                from sqlalchemy import or_
                query = query.filter(or_(*filters))
            elif agg == "yearly":
                query = query.filter(PLRecord.period.like(f"{year}%"))

    return query.offset(skip).limit(limit).all()


def get_anomaly(db: Session, anomaly_id: int):
    return (
        db.query(Anomaly)
        .options(joinedload(Anomaly.pl_record))
        .filter(Anomaly.id == anomaly_id)
        .first()
    )


def update_anomaly_status(db: Session, anomaly_id: int, status: str):
    anomaly = get_anomaly(db, anomaly_id)
    if anomaly:
        anomaly.status = status
        db.commit()
        db.refresh(anomaly)
    return anomaly


def assign_anomaly(db: Session, anomaly_id: int, user_id: int):
    anomaly = get_anomaly(db, anomaly_id)
    if anomaly:
        anomaly.assigned_to = user_id
        db.commit()
        db.refresh(anomaly)
    return anomaly
