"""
client.py - Camunda 7 BPMN REST Client
=======================================
Communicates with Camunda 7 REST Engine (/engine-rest) to auto-deploy BPMN models,
start process instances, query execution state, and resolve user tasks.
"""

from __future__ import annotations
import os
import logging
import requests
from typing import Dict, Any, List, Optional
from config import settings

logger = logging.getLogger(__name__)


class CamundaClient:
    """Client for Camunda 7 REST Engine."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or getattr(settings, "CAMUNDA_URL", "http://localhost:8080/engine-rest")).rstrip("/")

    def is_reachable(self, timeout: float = 1.0) -> bool:
        """Checks if Camunda 7 REST engine is online."""
        try:
            r = requests.get(f"{self.base_url}/version", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def is_live(self, timeout: float = 1.0) -> bool:
        """Alias for is_reachable."""
        return self.is_reachable(timeout=timeout)

    def get_engine_status(self) -> Dict[str, Any]:
        """Returns connection and metadata status for Camunda REST engine."""
        reachable = self.is_reachable()
        return {
            "engine_url": self.base_url,
            "is_live": reachable,
            "engine_type": "Camunda BPMN 7.x (REST)" if reachable else "Integrated Fallback Engine"
        }

    def deploy_bpmn(self, bpmn_path: str, deployment_name: str = "PL_Financial_Workflow") -> Optional[Dict[str, Any]]:
        """Deploys a BPMN 2.0 XML file to Camunda 7 REST engine."""
        if not os.path.exists(bpmn_path):
            logger.warning(f"[CamundaClient] BPMN file not found: {bpmn_path}")
            return None

        if not self.is_reachable():
            logger.debug(f"[CamundaClient] Camunda engine unreachable at {self.base_url}, skipping deployment.")
            return None

        try:
            with open(bpmn_path, "rb") as f:
                files = {
                    "deployment-name": (None, deployment_name),
                    "enable-duplicate-filtering": (None, "true"),
                    "deploy-changed-only": (None, "true"),
                    os.path.basename(bpmn_path): (os.path.basename(bpmn_path), f, "application/xml"),
                }
                resp = requests.post(f"{self.base_url}/deployment/create", files=files, timeout=5.0)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    logger.info(f"[CamundaClient] Successfully deployed BPMN '{deployment_name}' (ID: {data.get('id')})")
                    return data
                else:
                    logger.warning(f"[CamundaClient] Deployment returned status {resp.status_code}: {resp.text}")
                    return None
        except Exception as e:
            logger.warning(f"[CamundaClient] Deployment failed: {e}")
            return None

    def start_process(
        self,
        process_definition_key: str,
        variables: Optional[Dict[str, Any]] = None,
        business_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Starts a new process instance for the given process definition key."""
        if not self.is_reachable():
            return None

        camunda_vars = {}
        if variables:
            for k, v in variables.items():
                if isinstance(v, bool):
                    camunda_vars[k] = {"value": v, "type": "Boolean"}
                elif isinstance(v, int):
                    camunda_vars[k] = {"value": v, "type": "Integer"}
                elif isinstance(v, float):
                    camunda_vars[k] = {"value": v, "type": "Double"}
                else:
                    camunda_vars[k] = {"value": str(v), "type": "String"}

        payload = {"variables": camunda_vars}
        if business_key:
            payload["businessKey"] = business_key

        try:
            resp = requests.post(
                f"{self.base_url}/process-definition/key/{process_definition_key}/start",
                json=payload,
                timeout=3.0
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                logger.info(f"[CamundaClient] Started process instance {data.get('id')} (Key: {process_definition_key})")
                return data
            else:
                logger.warning(f"[CamundaClient] Start process returned {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.warning(f"[CamundaClient] Failed to start process: {e}")
            return None

    def get_user_tasks(self, process_instance_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves active User Tasks waiting for human approval."""
        if not self.is_reachable():
            return []

        params = {}
        if process_instance_id:
            params["processInstanceId"] = process_instance_id

        try:
            resp = requests.get(f"{self.base_url}/task", params=params, timeout=2.0)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.debug(f"[CamundaClient] Failed to get user tasks: {e}")
            return []

    def complete_user_task(self, task_id: str, variables: Optional[Dict[str, Any]] = None) -> bool:
        """Completes a user task (resolving human approval/rejection)."""
        if not self.is_reachable():
            return False

        camunda_vars = {}
        if variables:
            for k, v in variables.items():
                if isinstance(v, bool):
                    camunda_vars[k] = {"value": v, "type": "Boolean"}
                else:
                    camunda_vars[k] = {"value": str(v), "type": "String"}

        try:
            resp = requests.post(
                f"{self.base_url}/task/{task_id}/complete",
                json={"variables": camunda_vars},
                timeout=3.0
            )
            return resp.status_code in [200, 204]
        except Exception as e:
            logger.warning(f"[CamundaClient] Failed to complete user task {task_id}: {e}")
            return False


camunda_client = CamundaClient()
