from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.anomaly_schemas import ExplanationResponse, CopilotRequest, CopilotResponse
from services.explanation_agent import generate_explanation
from services.copilot_agent import ask_copilot

router = APIRouter()


@router.post(
    "/generate/{anomaly_id}", response_model=ExplanationResponse, status_code=201
)
def get_or_generate_explanation(anomaly_id: int, db: Session = Depends(get_db)):
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
def copilot_chat(req: CopilotRequest, db: Session = Depends(get_db)):
    ans = ask_copilot(db, req.question, session_id=req.session_id or "default")
    return {"answer": ans}
