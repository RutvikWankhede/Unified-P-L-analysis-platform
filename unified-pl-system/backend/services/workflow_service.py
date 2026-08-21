import logging
import uuid
import time
import threading
import random
from datetime import datetime
from typing import Any, Dict
import requests
from sqlalchemy.orm import Session
from database import SessionLocal

logger = logging.getLogger(__name__)

STAGES = [
    ("upload", "Upload"),
    ("schema_detection", "Schema Detection"),
    ("ai_mapping", "AI Schema Mapping"),
    ("data_cleaning", "Data Cleaning"),
    ("data_validation", "Data Validation"),
    ("quality_check", "Quality Check"),
    ("anomaly_detection", "Anomaly Detection"),
    ("forecast", "Forecast"),
    ("recommendations", "Recommendations"),
    ("generate_report", "Generate Report"),
    ("notify_user", "Notify User"),
    ("completed", "Completed"),
]


# Simulator removed for Phase 5. Genuine Camunda integration only.


class WorkflowService:
    def __init__(self, engine_url: str = "http://localhost:8080/engine-rest"):
        self.engine_url = engine_url

    def start_upload_workflow(
        self, db: Session, user_id: int, upload_id: str, records_count: int
    ) -> str:
        """Starts the Camunda Ingestion Workflow and triggers simulated pipeline states."""
        variables = {
            "uploadId": {"value": upload_id, "type": "String"},
            "userId": {"value": user_id, "type": "Integer"},
            "recordsCount": {"value": records_count, "type": "Integer"},
        }

        status = "ACTIVE"
        try:
            response = requests.post(
                f"{self.engine_url}/process-definition/key/Process_UploadData/start",
                json={"variables": variables},
                timeout=1.0,
            )
            response.raise_for_status()
            process_instance_id = response.json().get("id")
            logger.info(
                f"Started Camunda workflow Process_UploadData with Instance ID: {process_instance_id}"
            )
        except Exception as e:
            logger.warning(
                f"Camunda engine unreachable or failed. Falling back to explicit failure alert. Error: {e}"
            )
            process_instance_id = str(uuid.uuid4())
            status = "FAILED"

        from models.workflow import WorkflowInstance

        try:
            # Initialize steps variables
            steps_init = {}
            for skey, sname in STAGES:
                steps_init[skey] = {
                    "name": sname,
                    "status": "FAILED" if status == "FAILED" else "PENDING",
                    "execution_time_ms": 0,
                    "retries": 0,
                    "logs": ["CAMUNDA ENGINE UNAVAILABLE - PLEASE DEPLOY ENGINE AND RETRY."] if status == "FAILED" else [],
                }

            workflow_inst = WorkflowInstance(
                process_instance_id=process_instance_id,
                workflow_name="Process_UploadData",
                status=status,
                started_by=user_id,
                variables={
                    "upload_id": upload_id,
                    "records_count": records_count,
                    "active_activity": "upload",
                    "steps": steps_init,
                    "error": "Camunda engine unavailable" if status == "FAILED" else None
                },
            )
            db.add(workflow_inst)
            db.commit()
            db.refresh(workflow_inst)
            logger.info(f"Saved WorkflowInstance {process_instance_id} to DB.")

        except Exception as db_err:
            logger.error(f"Failed to save WorkflowInstance to DB: {db_err}")
            db.rollback()

        return process_instance_id

    def complete_task(self, task_id: str, variables: Dict[str, Any] = None):
        """Completes a Camunda External Task or User Task."""
        try:
            response = requests.post(
                f"{self.engine_url}/external-task/{task_id}/complete",
                json={"workerId": "unified-pl-backend", "variables": variables or {}},
                timeout=5,
            )
            response.raise_for_status()
            logger.info(f"Completed task {task_id} with variables {variables}")
            return True
        except Exception as e:
            logger.warning(f"Failed to complete task {task_id} in Camunda: {e}")
            return False


workflow_service = WorkflowService()
