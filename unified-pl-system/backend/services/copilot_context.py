from typing import Dict, Any, List

# Structured in-memory session context store
_SESSION_CONTEXT: Dict[str, Dict[str, Any]] = {}

def get_context(session_id: str = "default") -> Dict[str, Any]:
    """Return a copy of the stored structured context for *session_id*."""
    ctx = _SESSION_CONTEXT.get(session_id, {})
    return ctx.copy()

def update_context(session_id: str = "default", **kwargs: Any) -> None:
    """Merge *kwargs* into the stored context for *session_id*.
    Existing keys are overwritten; new keys are added.
    """
    ctx = _SESSION_CONTEXT.setdefault(session_id, {
        "history": [],
        "last_department": None,
        "last_comparison": [],
        "last_intent": None,
        "last_metric": None,
        "last_dataset_id": None,
    })
    for k, v in kwargs.items():
        if v is not None:
            ctx[k] = v

def add_history_turn(session_id: str, question: str, answer: str, intent: str, entities: Dict[str, Any] = None) -> None:
    """Record a conversational turn in session history."""
    ctx = _SESSION_CONTEXT.setdefault(session_id, {
        "history": [],
        "last_department": None,
        "last_comparison": [],
        "last_intent": None,
        "last_metric": None,
        "last_dataset_id": None,
    })
    hist: List[Dict[str, Any]] = ctx.setdefault("history", [])
    hist.append({
        "question": question,
        "answer": answer,
        "intent": intent,
        "entities": entities or {}
    })
    # Keep last 20 turns
    if len(hist) > 20:
        ctx["history"] = hist[-20:]

def reset_context(session_id: str = "default") -> None:
    """Reset session context."""
    if session_id in _SESSION_CONTEXT:
        _SESSION_CONTEXT[session_id] = {
            "history": [],
            "last_department": None,
            "last_comparison": [],
            "last_intent": None,
            "last_metric": None,
            "last_dataset_id": None,
        }

