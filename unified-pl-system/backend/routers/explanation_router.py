import re
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from schemas.anomaly_schemas import ExplanationResponse, CopilotRequest, CopilotResponse
from services.explanation_agent import generate_explanation
from services.copilot_agent import ask_copilot

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


@router.post(
    "/generate/{anomaly_id}", response_model=ExplanationResponse, status_code=201
)
@limiter.limit("30/minute")
def get_or_generate_explanation(request: Request, anomaly_id: int, db: Session = Depends(get_db)):
    exp = generate_explanation(db, anomaly_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return exp


@router.get("/{anomaly_id}", response_model=ExplanationResponse)
def get_explanation(anomaly_id: int, db: Session = Depends(get_db)):
    from models.recommendation import Explanation

    exp = db.query(Explanation).filter(Explanation.anomaly_id == anomaly_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Explanation not found")
    return exp


@router.post("/copilot", response_model=CopilotResponse)
@limiter.limit("20/minute")
def copilot_chat(request: Request, req: CopilotRequest, db: Session = Depends(get_db)):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if len(question) > 4000:
        raise HTTPException(status_code=400, detail="Question exceeds maximum allowed length of 4000 characters")

    safe_session_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(req.session_id or "default").strip()) or "default"
    try:
        ans = ask_copilot(db, question, session_id=safe_session_id)
        return {"answer": ans}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Copilot error: {e}")
        return {"answer": "I encountered an error processing your query. Please rephrase or try again later."}

