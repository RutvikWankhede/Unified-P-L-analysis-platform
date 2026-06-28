from sqlalchemy.orm import Session

from models.anomaly import Anomaly
from models.pl_record import PLRecord
from models.recommendation import Recommendation


def generate_recommendations(db: Session, anomaly_id: int):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        return []

    pl_record = db.query(PLRecord).filter(PLRecord.id == anomaly.pl_record_id).first()

    recommendations = []

    # Rules
    if "revenue" in pl_record.line_item.lower() and anomaly.severity == "High":
        recommendations.append(
            {
                "priority": 1,
                "action_type": "Revenue Audit",
                "description": "Conduct full audit on revenue figures for this period.",
                "action_owner": "Finance Controller",
                "sod_flag": False,
            }
        )

    if anomaly.severity == "High" and not anomaly.assigned_to:
        recommendations.append(
            {
                "priority": 3,
                "action_type": "Immediate Assignment",
                "description": "Assign this high-severity anomaly to an analyst immediately.",
                "action_owner": "Team Lead",
                "sod_flag": False,
            }
        )

    # SOD Check (Separation of Duties)
    # Check if there is an assigned analyst and verify they are not the uploader
    is_sod_violation = False
    if anomaly.assigned_to and anomaly.assigned_to == pl_record.uploaded_by:
        is_sod_violation = True

    if anomaly.severity in ["High", "Medium"] or is_sod_violation:
        recommendations.append(
            {
                "priority": 1 if is_sod_violation else 2,
                "action_type": "SOD Check",
                "description": (
                    "SOD Violation detected: Assigner is the uploader."
                    if is_sod_violation
                    else "Ensure reviewing analyst is not the uploader."
                ),
                "action_owner": "Compliance Officer",
                "sod_flag": True,
            }
        )

    if anomaly.severity == "Low":
        recommendations.append(
            {
                "priority": 5,
                "action_type": "Monitor & Log",
                "description": "Monitor this pattern in future periods.",
                "action_owner": "Junior Analyst",
                "sod_flag": False,
            }
        )

    db_recs = []
    # Clear existing
    db.query(Recommendation).filter(Recommendation.anomaly_id == anomaly.id).delete()

    for rec in recommendations:
        db_rec = Recommendation(anomaly_id=anomaly.id, **rec)
        db.add(db_rec)
        db_recs.append(db_rec)

    db.commit()
    for rec in db_recs:
        db.refresh(rec)

    return db_recs
