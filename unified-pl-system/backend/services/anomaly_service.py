from sqlalchemy.orm import Session

from ml.isolation_forest import detect_anomalies
from repositories import anomaly_repository, pl_repository


def run_anomaly_detection(db: Session, upload_id: str):
    # Fetch records
    records = pl_repository.get_pl_records_by_upload_id(db, upload_id)
    if not records:
        return []

    # Run ML
    anomalies_data = detect_anomalies(records, db=db)

    # Save anomalies
    if anomalies_data:
        saved_anomalies = anomaly_repository.create_anomalies(db, anomalies_data)
        return saved_anomalies
    return []
