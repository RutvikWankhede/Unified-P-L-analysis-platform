import hashlib
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from config import settings
from models.recommendation import Explanation
from models.anomaly import Anomaly
from models.pl_record import PLRecord

client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

def _compute_hash(anomaly: Anomaly, pl_record: PLRecord) -> str:
    state_str = f"{anomaly.id}_{anomaly.severity}_{anomaly.status}_{pl_record.amount}_{pl_record.domain}_{pl_record.period}"
    return hashlib.sha256(state_str.encode()).hexdigest()

def generate_explanation(db: Session, anomaly_id: int) -> Explanation:
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        return None
        
    pl_record = db.query(PLRecord).filter(PLRecord.id == anomaly.pl_record_id).first()
    
    state_hash = _compute_hash(anomaly, pl_record)
    
    # Check cache
    cached = db.query(Explanation).filter(Explanation.state_hash == state_hash).first()
    if cached:
        return cached
        
    # Call OpenAI if available
    explanation_text = "Detailed explanation not available. (OpenAI API Key missing)"
    root_cause = "Unknown"
    business_impact = "Needs review"
    tokens_used = 0
    
    if client:
        sys_prompt = "You are a senior financial analyst. Analyze this P&L anomaly. Output JSON with keys: explanation, root_cause, business_impact, recommended_urgency."
        user_prompt = f"Domain: {pl_record.domain}, Period: {pl_record.period}, Line Item: {pl_record.line_item}, Amount: {pl_record.amount}, Score: {anomaly.anomaly_score}, Severity: {anomaly.severity}"
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            explanation_text = result.get("explanation", "")
            root_cause = result.get("root_cause", "")
            business_impact = result.get("business_impact", "")
            tokens_used = response.usage.total_tokens
        except Exception as e:
            explanation_text = f"Error generating explanation: {e}"
            
    # Invalidate old cache for this anomaly if exists
    db.query(Explanation).filter(Explanation.anomaly_id == anomaly.id).delete()
    
    new_exp = Explanation(
        anomaly_id=anomaly.id,
        state_hash=state_hash,
        explanation_text=explanation_text,
        root_cause=root_cause,
        business_impact=business_impact,
        tokens_used=tokens_used
    )
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)
    return new_exp
