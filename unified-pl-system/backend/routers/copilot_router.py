from datetime import datetime
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from core.security import get_current_user
from models.user import User
from models.chat_history import ChatHistory
from models.ai_log import AILog
from services.copilot_agent import ask_copilot

router = APIRouter()

class CopilotChatRequest(BaseModel):
    prompt: Optional[str] = None
    question: Optional[str] = None
    session_id: Optional[str] = None

class CopilotChatResponse(BaseModel):
    answer: str

@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat_endpoint(
    req: CopilotChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Resolve prompt/question
    query_text = req.prompt or req.question
    if not query_text:
        raise HTTPException(status_code=400, detail="Either 'prompt' or 'question' field is required.")

    session_id = req.session_id or "default_session"

    # Log user prompt to ChatHistory
    user_chat = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        content=query_text,
        created_at=datetime.utcnow()
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
        response_text = f"An unexpected error occurred: {str(e)}"
        db.rollback()
    
    execution_time_ms = int((time.time() - start_time) * 1000)

    # Log assistant response to ChatHistory
    assistant_chat = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        role="assistant",
        content=response_text,
        created_at=datetime.utcnow()
    )
    db.add(assistant_chat)

    # Log to AILog
    ai_log = AILog(
        agent_name="Copilot",
        action="chat",
        request_payload={"prompt": query_text, "session_id": session_id},
        response_payload={"answer": response_text},
        execution_time_ms=execution_time_ms,
        status=status,
        created_at=datetime.utcnow()
    )
    db.add(ai_log)
    db.commit()

    return {"answer": response_text}
