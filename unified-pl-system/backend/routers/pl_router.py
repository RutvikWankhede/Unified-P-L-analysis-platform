from typing import Dict, List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from core.security import get_current_user

from database import get_db
from models.user import User
from schemas.pl_schemas import UploadResponse, PLRecordResponse
from services.pl_service import process_csv_upload
from repositories import pl_repository

router = APIRouter()


@router.get("/records", response_model=Dict[str, List[PLRecordResponse]])
def list_pl_records(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = pl_repository.get_pl_records(db, skip, limit)
    return {"items": records}


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_pl_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    try:
        content = await file.read()
        upload_id, count = process_csv_upload(db, content, current_user.id)

        # Trigger Camunda Workflow
        from services.workflow_service import workflow_service

        process_id = workflow_service.start_upload_workflow(
            db, current_user.id, upload_id, count
        )

        return {
            "upload_id": upload_id,
            "records_ingested": count,
            "message": "Upload successful. Workflow started.",
            "workflow_process_id": process_id,
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
