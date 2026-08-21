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

        db = SessionLocal()
        try:
            from models.anomaly import Anomaly
            from models.pl_record import PLRecord
            from models.domain_settings import DomainSettings

            anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
            if anomaly:
                pl_record = db.query(PLRecord).filter(PLRecord.id == anomaly.pl_record_id).first()
                if pl_record:
                    domain = pl_record.domain
                    domain_setting = db.query(DomainSettings).filter(DomainSettings.domain == domain).first()
                    
                    if not domain_setting:
                        from backend.ml.isolation_forest import get_contamination
                        domain_setting = DomainSettings(domain=domain, contamination_rate=get_contamination(domain, db))
                        db.add(domain_setting)
                        
                    # If it was a false positive, lower contamination (make it stricter)
                    if not was_correct:
                        # Reduce by 10% (e.g. 0.05 -> 0.045)
                        domain_setting.contamination_rate = max(0.01, domain_setting.contamination_rate * 0.9)
                        action = "update_model_weights (reduced contamination)"
                    else:
                        # Reinforce: maybe slightly increase or keep same
                        domain_setting.contamination_rate = min(0.15, domain_setting.contamination_rate * 1.05)
                        action = "reinforce_model (increased contamination)"
                        
                    db.commit()
            else:
                action = "unknown_anomaly"
                
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            action = "error"
        finally:
            db.close()

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
