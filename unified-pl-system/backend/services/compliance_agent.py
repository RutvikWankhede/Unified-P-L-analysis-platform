import logging

from database import SessionLocal
from models.ai_log import AILog

logger = logging.getLogger(__name__)


class ComplianceAgent:
    """
    Verifies that P&L records and recommendations meet enterprise compliance rules.
    Flags records violating financial regulations.
    """

    def __init__(self):
        self.agent_name = "ComplianceAgent"

    def check_compliance(self, record_id: int):
        logger.info(f"[{self.agent_name}] Checking compliance for record {record_id}")
        db = SessionLocal()
        is_compliant = True
        reason = "Passes standard compliance checks"

        try:
            from models.pl_record import PLRecord

            record = db.query(PLRecord).filter(PLRecord.id == record_id).first()
            if not record:
                return {"is_compliant": False, "reason": "Record not found"}

            if record.amount > 1000000 and record.domain == "Retail":
                is_compliant = False
                reason = "Retail transactions over 1M require manual audit"

            # Additional enterprise rule checks
            if record.currency != "USD" and record.amount > 500000:
                is_compliant = False
                reason = (
                    "Foreign currency transactions over 500k require Hedging review"
                )
        finally:
            db.close()

        result = {"is_compliant": is_compliant, "reason": reason}
        self._log_action("check_compliance", {"record_id": record_id}, result)
        return result

    def _log_action(self, action: str, request_payload: dict, response_payload: dict):
        db = SessionLocal()
        try:
            log = AILog(
                agent_name=self.agent_name,
                action=action,
                request_payload=request_payload,
                response_payload=response_payload,
                execution_time_ms=80,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI action: {e}")
        finally:
            db.close()


compliance_agent = ComplianceAgent()
