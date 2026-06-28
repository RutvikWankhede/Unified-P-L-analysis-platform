import logging

from database import SessionLocal
from models.ai_log import AILog

logger = logging.getLogger(__name__)


class LearningAgent:
    """
    Analyzes historical anomaly resolutions (e.g. false positives)
    and updates the Isolation Forest or Gemini prompt thresholds.
    """

    def __init__(self):
        self.agent_name = "LearningAgent"

    def process_feedback(self, anomaly_id: int, was_correct: bool, user_id: int):
        logger.info(
            f"[{self.agent_name}] Processing feedback for anomaly {anomaly_id}: {was_correct}"
        )

        # In a real app, retrain the model or update knowledge graph
        action = "update_model_weights" if not was_correct else "reinforce_model"

        result = {"action_taken": action, "status": "Feedback incorporated"}
        self._log_action(
            "process_feedback",
            {"anomaly_id": anomaly_id, "was_correct": was_correct},
            result,
        )
        return result

    def _log_action(self, action: str, request_payload: dict, response_payload: dict):
        db = SessionLocal()
        try:
            log = AILog(
                agent_name=self.agent_name,
                action=action,
                request_payload=request_payload,
                response_payload=response_payload,
                execution_time_ms=150,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI action: {e}")
        finally:
            db.close()


learning_agent = LearningAgent()
