"""
learning_agent.py - Adaptive Learning and Model Feedback Agent
==============================================================
Incorporates analyst feedback on anomalies and recommendations,
dynamically updating Isolation Forest contamination rates and
persisting decision history in AgentMemory.
"""

import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from models.ai_log import AILog
from agents.memory_agent import memory_agent

logger = logging.getLogger(__name__)


class LearningAgent:
    """
    Analyzes historical anomaly resolutions and recommendation approvals/rejections,
    adapting model contamination rates and recording strategic directives.
    """

    def __init__(self):
        self.agent_name = "LearningAgent"

    def process_anomaly_feedback(self, anomaly_id: int, was_correct: bool, user_id: int = 1):
        """Updates Isolation Forest contamination threshold based on anomaly feedback."""
        logger.info(f"[{self.agent_name}] Processing feedback for anomaly {anomaly_id}: was_correct={was_correct}")
        db = SessionLocal()
        action = "unknown"
        try:
            from models.anomaly import Anomaly
            from models.pl_record import PLRecord
            from models.domain_settings import DomainSettings

            anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
            if anomaly:
                pl_record = db.query(PLRecord).filter(PLRecord.id == anomaly.pl_record_id).first()
                if pl_record:
                    domain = pl_record.domain or "All"
                    domain_setting = db.query(DomainSettings).filter(DomainSettings.domain == domain).first()

                    if not domain_setting:
                        from ml.isolation_forest import get_contamination
                        domain_setting = DomainSettings(domain=domain, contamination_rate=get_contamination(domain, db))
                        db.add(domain_setting)

                    # If it was a false positive, lower contamination (make it stricter)
                    if not was_correct:
                        domain_setting.contamination_rate = max(0.01, domain_setting.contamination_rate * 0.9)
                        action = "update_model_weights (reduced contamination)"
                    else:
                        domain_setting.contamination_rate = min(0.15, domain_setting.contamination_rate * 1.05)
                        action = "reinforce_model (increased contamination)"

                    db.commit()
        except Exception as e:
            logger.error(f"Error processing anomaly feedback: {e}")
            action = "error"
        finally:
            db.close()

        result = {"action_taken": action, "status": "Feedback incorporated into ML thresholds"}
        self._log_action("process_anomaly_feedback", {"anomaly_id": anomaly_id, "was_correct": was_correct}, result)
        return result

    def process_recommendation_feedback(
        self,
        db: Session,
        recommendation_id: int,
        decision: str,  # APPROVED, REJECTED, MODIFIED
        notes: str,
        user_id: int = 1
    ) -> dict:
        """Stores human manager decision in AgentMemory for future reasoning."""
        logger.info(f"[{self.agent_name}] Processing decision for recommendation #{recommendation_id}: {decision}")
        entry = memory_agent.record_decision(
            db=db,
            recommendation_id=recommendation_id,
            decision=decision,
            notes=notes,
            user_id=user_id
        )
        result = {"decision_recorded": decision, "notes": notes, "status": "Memory updated"}
        self._log_action("process_recommendation_feedback", {"recommendation_id": recommendation_id, "decision": decision}, result)
        return result

    def _log_action(self, action: str, request_payload: dict, response_payload: dict):
        db = SessionLocal()
        try:
            log = AILog(
                agent_name=self.agent_name,
                action=action,
                request_payload=request_payload,
                response_payload=response_payload,
                execution_time_ms=50,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI action: {e}")
        finally:
            db.close()


learning_agent = LearningAgent()
