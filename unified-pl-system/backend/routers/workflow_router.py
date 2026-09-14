from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from services.workflow_service import workflow_service

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class StartWorkflowRequest(BaseModel):
    dataset_id: Optional[int] = Field(1, ge=1)
    department: Optional[str] = Field("Overall", max_length=100)
    fiscal_year: Optional[str] = Field("2024", max_length=10)
    trigger_approval: Optional[bool] = True


class ApprovalDecisionRequest(BaseModel):
    notes: Optional[str] = Field("Approved by Executive Manager", max_length=1000)


@router.get("")
@router.get("/")
def list_workflow_instances_root(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """Returns list of recent workflow execution instances."""
    return workflow_service.list_instances(db, limit=limit)


@router.get("/kpis")
def get_workflow_kpis(db: Session = Depends(get_db)):
    """Returns workflow KPIs: active, completed, pending approval, and failed counts."""
    return workflow_service.get_kpis(db)


@router.get("/instances")
def list_workflow_instances(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """Returns list of recent workflow execution instances."""
    return workflow_service.list_instances(db, limit=limit)


@router.get("/instances/{instance_id}")
@router.get("/{instance_id}")
@router.get("/{instance_id}/status")
@router.get("/{instance_id}/history")
def get_workflow_instance(instance_id: str, db: Session = Depends(get_db)):
    """Fetches full execution state, timeline, step outputs, and variables for a specific instance."""
    safe_instance_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(instance_id).strip())
    if not safe_instance_id:
        raise HTTPException(status_code=400, detail="Invalid instance_id parameter")

    inst = workflow_service.get_instance(db, safe_instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Workflow instance '{safe_instance_id}' not found")
    return inst


@router.post("/start")
@limiter.limit("20/minute")
def start_workflow(request: Request, req: StartWorkflowRequest, db: Session = Depends(get_db)):
    """Triggers and executes a new P&L financial workflow."""
    inst = workflow_service.start_workflow(
        db=db,
        user_id=1,
        dataset_id=req.dataset_id,
        department=req.department or "Overall",
        fiscal_year=req.fiscal_year or "2024",
        trigger_approval=req.trigger_approval if req.trigger_approval is not None else True,
    )
    return inst


@router.post("/{instance_id}/approve")
@limiter.limit("30/minute")
def approve_workflow(request: Request, instance_id: str, req: Optional[ApprovalDecisionRequest] = None, db: Session = Depends(get_db)):
    """Resolves a pending approval task as APPROVED and resumes workflow execution."""
    safe_instance_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(instance_id).strip())
    notes = req.notes if req and req.notes else "Approved by Executive Manager"
    inst = workflow_service.approve_task(db, safe_instance_id, notes=notes)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Workflow instance '{safe_instance_id}' not found")
    return inst


@router.post("/{instance_id}/reject")
@limiter.limit("30/minute")
def reject_workflow(request: Request, instance_id: str, req: Optional[ApprovalDecisionRequest] = None, db: Session = Depends(get_db)):
    """Resolves a pending approval task as REJECTED."""
    safe_instance_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(instance_id).strip())
    notes = req.notes if req and req.notes else "Rejected by Executive Manager"
    inst = workflow_service.reject_task(db, safe_instance_id, notes=notes)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Workflow instance '{safe_instance_id}' not found")
    return inst


@router.post("/{instance_id}/retry")
@limiter.limit("20/minute")
def retry_workflow(request: Request, instance_id: str, db: Session = Depends(get_db)):
    """Retries a failed workflow execution."""
    safe_instance_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(instance_id).strip())
    inst = workflow_service.retry_workflow(db, safe_instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Workflow instance '{safe_instance_id}' not found")
    return inst


@router.post("/{instance_id}/cancel")
@limiter.limit("20/minute")
def cancel_workflow(request: Request, instance_id: str, db: Session = Depends(get_db)):
    """Cancels a running workflow instance."""
    safe_instance_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(instance_id).strip())
    inst = workflow_service.cancel_workflow(db, safe_instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Workflow instance '{safe_instance_id}' not found")
    return inst


@router.get("/bpmn")
def get_bpmn_xml():
    """Returns the official BPMN 2.0 XML definition for the P&L workflow."""
    bpmn_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "camunda", "pl_financial_workflow.bpmn")
    if os.path.exists(bpmn_path):
        with open(bpmn_path, "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="application/xml")
    return Response(content="<bpmn:definitions/>", media_type="application/xml")


@router.get("/camunda-status")
def get_camunda_status():
    """Checks whether external Camunda REST engine is reachable."""
    url = workflow_service.engine_url
    is_connected = False
    try:
        import requests
        r = requests.get(f"{url}/version", timeout=1.0)
        is_connected = r.status_code == 200
    except Exception:
        is_connected = False

    return {
        "engine_url": url,
        "is_connected": is_connected,
        "engine_type": "Camunda BPMN 7.x" if is_connected else "Integrated Enterprise BPMN State Machine",
    }
