from datetime import datetime, timezone
import time
import re
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from core.security import get_current_user
from models.user import User
from models.chat_history import ChatHistory
from models.ai_log import AILog
from services.copilot_agent import ask_copilot, get_financial_context_and_calc

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class CopilotChatRequest(BaseModel):
    prompt: Optional[str] = Field(None, max_length=4000)
    question: Optional[str] = Field(None, max_length=4000)
    session_id: Optional[str] = Field(None, max_length=128)

class CopilotChatResponse(BaseModel):
    answer: str

class CopilotContextResponse(BaseModel):
    active_dataset_name: str
    active_dataset_id: Optional[str] = None
    record_count: int
    date_range: str
    departments: List[str]
    suggested_questions: List[str]

@router.get("/context", response_model=CopilotContextResponse)
def copilot_context_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ctx = get_financial_context_and_calc(db)
    depts = sorted(list(ctx["departments"].keys()))
    
    suggested = [
        "Why did profit change?",
        "Which department is most profitable?",
        "Which department needs attention?",
        "Where are we overspending?",
        "Compare Sales and Marketing",
        "What is driving revenue?",
        "What happens if expenses fall 5%?",
        "What is missing from my dataset?",
        "Show budget risks",
        "How many anomalies were flagged?"
    ]
    
    return {
        "active_dataset_name": ctx["dataset_name"],
        "active_dataset_id": ctx["dataset_id"],
        "record_count": ctx["record_count"],
        "date_range": ctx["date_range"],
        "departments": depts,
        "suggested_questions": suggested,
    }

@router.post("/chat", response_model=CopilotChatResponse)
@limiter.limit("20/minute")
def copilot_chat_endpoint(
    request: Request,
    req: CopilotChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query_text = (req.prompt or req.question or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Either 'prompt' or 'question' field is required.")

    if len(query_text) > 4000:
        raise HTTPException(status_code=400, detail="Prompt exceeds maximum length of 4,000 characters.")

    raw_session = req.session_id or f"user_{current_user.id}_session"
    session_id = re.sub(r"[^a-zA-Z0-9_\-]", "", raw_session)[:64] or "default_session"

    # Log user prompt to ChatHistory
    user_chat = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        content=query_text,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user_chat)
    db.commit()

    start_time = time.time()
    status = "SUCCESS"
    response_text = ""
    try:
        response_text = ask_copilot(db, query_text, session_id=session_id)
    except Exception as e:
        status = "FAILED"
        logger.error(f"Copilot query failed: {e}", exc_info=True)
        response_text = "I encountered an issue processing your financial query. Please refine your question or try again."
        db.rollback()
    
    execution_time_ms = int((time.time() - start_time) * 1000)

    # Log assistant response to ChatHistory
    assistant_chat = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        role="assistant",
        content=response_text,
        created_at=datetime.now(timezone.utc)
    )
    db.add(assistant_chat)

    # Log to AILog
    ai_log = AILog(
        agent_name="Copilot",
        action="chat",
        request_payload={"prompt_len": len(query_text), "session_id": session_id},
        response_payload={"answer_len": len(response_text)},
        execution_time_ms=execution_time_ms,
        status=status,
        created_at=datetime.now(timezone.utc)
    )
    db.add(ai_log)
    db.commit()

    return {"answer": response_text}

