from typing import List

from sqlalchemy.orm import Session, joinedload

from models.anomaly import Anomaly


def create_anomalies(db: Session, anomalies_data: List[dict]):
    db_anomalies = [Anomaly(**data) for data in anomalies_data]
    db.add_all(db_anomalies)
    db.commit()
    return db_anomalies


def get_anomalies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Anomaly).options(joinedload(Anomaly.pl_record)).offset(skip).limit(limit).all()


def get_anomaly(db: Session, anomaly_id: int):
    return db.query(Anomaly).options(joinedload(Anomaly.pl_record)).filter(Anomaly.id == anomaly_id).first()


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
