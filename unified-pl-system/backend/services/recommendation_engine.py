from sqlalchemy.orm import Session
from models.anomaly import Anomaly
from models.recommendation import Recommendation
from models.pl_record import PLRecord
from models.user import User

def generate_recommendations(db: Session, anomaly_id: int):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        return []
        
    pl_record = db.query(PLRecord).filter(PLRecord.id == anomaly.pl_record_id).first()
    uploader = db.query(User).filter(User.id == pl_record.uploaded_by).first()
    
    recommendations = []
    
    # Rules
    if 'revenue' in pl_record.line_item.lower() and anomaly.severity == 'High':
        recommendations.append({
            "priority": 1,
            "action_type": "Revenue Audit",
            "description": "Conduct full audit on revenue figures for this period.",
            "action_owner": "Finance Controller",
            "sod_flag": False
        })
        
    if anomaly.severity == 'High' and not anomaly.assigned_to:
        recommendations.append({
            "priority": 3,
            "action_type": "Immediate Assignment",
            "description": "Assign this high-severity anomaly to an analyst immediately.",
            "action_owner": "Team Lead",
            "sod_flag": False
        })
        
    # SOD Check (mocking that reviewer shouldn't be uploader, but we only have uploader context here)
    # So we'll just flag it for compliance check
    if anomaly.severity in ['High', 'Medium']:
        recommendations.append({
            "priority": 1,
            "action_type": "SOD Check",
            "description": "Ensure reviewing analyst is not the uploader.",
            "action_owner": "Compliance Officer",
            "sod_flag": True
        })
        
    if anomaly.severity == 'Low':
        recommendations.append({
            "priority": 5,
            "action_type": "Monitor & Log",
            "description": "Monitor this pattern in future periods.",
            "action_owner": "Junior Analyst",
            "sod_flag": False
        })
        
    db_recs = []
    # Clear existing
    db.query(Recommendation).filter(Recommendation.anomaly_id == anomaly.id).delete()
    
    for rec in recommendations:
        db_rec = Recommendation(
            anomaly_id=anomaly.id,
            **rec
        )
        db.add(db_rec)
        db_recs.append(db_rec)
        
    db.commit()
    for rec in db_recs:
        db.refresh(rec)
        
    return db_recs
