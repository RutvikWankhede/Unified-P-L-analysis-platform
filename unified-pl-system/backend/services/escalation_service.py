import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from database import SessionLocal
from models.anomaly import Anomaly
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def check_sla_escalations():
    logger.info("Running SLA Escalation Check...")
    db = SessionLocal()
    try:
        # Escalate anomalies older than 24 hours that are still 'open'
        threshold = datetime.utcnow() - timedelta(hours=24)
        anomalies = db.query(Anomaly).filter(
            Anomaly.status == 'open',
            Anomaly.detected_at < threshold
        ).all()
        
        for anomaly in anomalies:
            anomaly.severity = 'High' # Escalate severity
            # Add audit log for escalation here if needed
            logger.info(f"Escalated Anomaly {anomaly.id}")
            
        db.commit()
    except Exception as e:
        logger.error(f"Error in SLA escalation: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = AsyncIOScheduler()
    # Runs every 15 minutes
    scheduler.add_job(check_sla_escalations, 'interval', minutes=15)
    scheduler.start()
    return scheduler
