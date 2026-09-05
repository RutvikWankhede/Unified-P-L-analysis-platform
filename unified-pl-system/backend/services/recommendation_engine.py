import json
import logging
from sqlalchemy.orm import Session
from config import settings

from models.anomaly import Anomaly
from models.pl_record import PLRecord
from models.recommendation import Recommendation

def _get_genai_model():
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception as e:
        logger.warning(f"AI model initialization failed or not installed: {e}")
        return None

def generate_recommendations(db: Session, anomaly_id: int):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        return []

    pl_record = db.query(PLRecord).filter(PLRecord.id == anomaly.pl_record_id).first()

    # Fetch some historical context for the same department and line item
    historical_records = db.query(PLRecord).filter(
        PLRecord.domain == pl_record.domain,
        PLRecord.line_item == pl_record.line_item,
        PLRecord.id != pl_record.id
    ).limit(5).all()
    
    history_context = ""
    if historical_records:
        history_context = "\nHistorical Data for Context:\n"
        for hr in historical_records:
            history_context += f"- Period {hr.period}: {hr.amount}\n"

    is_sod_violation = False
    if anomaly.assigned_to and anomaly.assigned_to == pl_record.uploaded_by:
        is_sod_violation = True

    prompt = f"""
    You are an expert Financial Analysis AI.
    An anomaly has been detected in a company's P&L records.
    
    Anomaly Details:
    - Department: {pl_record.domain}
    - Line Item: {pl_record.line_item}
    - Period: {pl_record.period}
    - Amount: {pl_record.amount}
    - Deviation Amount: {anomaly.deviation_amount}
    - Severity: {anomaly.severity}
    - SOD Violation: {'Yes (Uploader is the assigned reviewer)' if is_sod_violation else 'No'}
    {history_context}
    
    Based on this, generate 1 to 3 actionable recommendations to address this anomaly.
    Return ONLY a valid JSON array of objects. Each object must have:
    - "priority": integer (1=Highest, 5=Lowest)
    - "action_type": string (short title)
    - "description": string (detailed description)
    - "action_owner": string (e.g. "Finance Controller", "Department Head")
    - "sod_flag": boolean (true if addressing SOD violation, else false)
    - "reason": string (why this action is recommended)
    - "financial_impact": string (e.g. "High", "Low", or specific estimated value)
    - "confidence": integer (0 to 100)
    - "suggested_action": string (one sentence summary)
    - "expected_benefit": string
    """

    recommendations_data = []
    
    try:
        model = _get_genai_model()
        if model:
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Clean up markdown if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            recommendations_data = json.loads(text.strip())
            
            if not isinstance(recommendations_data, list):
                recommendations_data = [recommendations_data]
            
    except Exception as e:
        logger.error(f"Error generating AI recommendations: {e}")
        # Fallback
        recommendations_data = [
            {
                "priority": 1,
                "action_type": "Manual Review Required",
                "description": "AI generation failed. Please review this anomaly manually.",
                "action_owner": "Finance Manager",
                "sod_flag": is_sod_violation,
                "reason": f"System error generating insights for anomaly {anomaly.id}.",
                "financial_impact": "Unknown",
                "confidence": 100,
                "suggested_action": "Manually audit this record.",
                "expected_benefit": "Prevent unverified ledger anomalies."
            }
        ]

    db_recs = []
    # Clear existing
    db.query(Recommendation).filter(Recommendation.anomaly_id == anomaly.id).delete()

    for rec in recommendations_data:
        db_rec = Recommendation(anomaly_id=anomaly.id, **rec)
        db.add(db_rec)
        db_recs.append(db_rec)

    db.commit()
    for rec in db_recs:
        db.refresh(rec)

    return db_recs
