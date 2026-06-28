import logging
import uuid
from typing import Any, Dict

import requests
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(self, engine_url: str = "http://localhost:8080/engine-rest"):
        self.engine_url = engine_url

    def start_upload_workflow(
        self, db: Session, user_id: int, upload_id: str, records_count: int
    ) -> str:
        """
        Starts the Camunda Upload Workflow.
        """
        variables = {
            "uploadId": {"value": upload_id, "type": "String"},
            "userId": {"value": user_id, "type": "Integer"},
            "recordsCount": {"value": records_count, "type": "Integer"},
        }

        try:
            response = requests.post(
                f"{self.engine_url}/process-definition/key/Process_UploadData/start",
                json={"variables": variables},
                timeout=5,
            )
            response.raise_for_status()
            process_instance_id = response.json().get("id")
            logger.info(
                f"Started Camunda workflow Process_UploadData with Instance ID: {process_instance_id}"
            )
            return process_instance_id
        except Exception as e:
            logger.warning(
                f"Camunda engine unreachable or failed. Falling back to mock ID. Error: {e}"
            )
            # Fallback for when Camunda is down
            process_instance_id = str(uuid.uuid4())
            return process_instance_id

    def complete_task(self, task_id: str, variables: Dict[str, Any] = None):
        """
        Completes a Camunda External Task or User Task
        """
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
