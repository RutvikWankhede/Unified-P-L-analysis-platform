"""
memory_agent.py - Lightweight Persistent Agent Memory Service
==============================================================
Maintains historical context of analyst decisions, feedback on recommendations,
and organizational directives across sessions and datasets.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from models.recommendation import Setting, Recommendation
from models.audit_log import AuditLog
from routers.datasets_router import get_active_dataset_id

logger = logging.getLogger(__name__)


class AgentMemory:
    """Manages cross-session and cross-run agent context and feedback memory."""

    def record_decision(
        self,
        db: Session,
        recommendation_id: int,
        decision: str,  # 'APPROVED', 'REJECTED', 'MODIFIED'
        notes: str,
        user_id: int = 1,
    ) -> Dict[str, Any]:
        """Records a human manager decision on an AI recommendation."""
        active_id = get_active_dataset_id(db)
        rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
        dept = getattr(rec, "domain", "Enterprise") if rec else "Enterprise"
        action_type = getattr(rec, "action_type", "General Action") if rec else "General Action"

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "recommendation_id": recommendation_id,
            "dataset_id": active_id,
            "department": dept,
            "action_type": action_type,
            "decision": decision.upper(),
            "notes": notes,
            "user_id": user_id,
        }

        key = f"agent_memory_rec_{recommendation_id}_{int(datetime.utcnow().timestamp())}"
        setting = Setting(key=key, value=json.dumps(entry))
        db.merge(setting)
        db.commit()

        logger.info(f"[AgentMemory] Recorded decision for Rec #{recommendation_id}: {decision} ({notes})")
        return entry

    def record_directive(
        self,
        db: Session,
        directive_text: str,
        category: str = "general",
        user_id: int = 1,
    ) -> Dict[str, Any]:
        """Stores a strategic analyst constraint or directive."""
        active_id = get_active_dataset_id(db)
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "dataset_id": active_id,
            "category": category,
            "directive": directive_text,
            "user_id": user_id,
        }
        key = f"agent_directive_{int(datetime.utcnow().timestamp())}"
        setting = Setting(key=key, value=json.dumps(entry))
        db.merge(setting)
        db.commit()
        return entry

    def get_context_summary(self, db: Session, limit: int = 10) -> Dict[str, Any]:
        """Retrieves aggregated memory context for current active dataset."""
        active_id = get_active_dataset_id(db)
        settings = db.query(Setting).filter(Setting.key.like("agent_%")).order_by(Setting.key.desc()).limit(limit * 2).all()

        decisions = []
        directives = []

        for s in settings:
            try:
                data = json.loads(s.value)
                if data.get("dataset_id") == active_id or not data.get("dataset_id"):
                    if "decision" in data:
                        decisions.append(data)
                    elif "directive" in data:
                        directives.append(data)
            except Exception:
                pass

        return {
            "dataset_id": active_id,
            "recent_decisions": decisions[:limit],
            "approved_count": sum(1 for d in decisions if d.get("decision") == "APPROVED"),
            "rejected_count": sum(1 for d in decisions if d.get("decision") == "REJECTED"),
            "active_directives": directives[:limit],
        }


memory_agent = AgentMemory()
