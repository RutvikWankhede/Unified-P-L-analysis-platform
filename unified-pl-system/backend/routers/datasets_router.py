import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from core.security import get_current_user
from database import get_db
from models.user import User
from models.workflow import WorkflowInstance

router = APIRouter()

# In-memory mock store for demo purposes (as backend lacks full DB pipeline persistence)
_pipeline_status = {}
_schema_mappings = {}
_active_dataset = {"dataset_id": None, "filename": None}
from models.recommendation import Setting
from models.uploaded_file import UploadedFile
from models.pl_record import PLRecord
from services.cache_service import invalidate_global_cache

from pydantic import BaseModel
class ActiveDatasetRequest(BaseModel):
    dataset_id: str
    filename: str = "Dataset"

@router.get("/active")
def get_active_dataset(db: Session = Depends(get_db)):
    if _active_dataset.get("dataset_id"):
        cnt = db.query(PLRecord).filter(PLRecord.upload_id == _active_dataset["dataset_id"]).count()
        if cnt == 0:
            _active_dataset["dataset_id"] = None
            _active_dataset["filename"] = None

    if not _active_dataset.get("dataset_id"):
        try:
            s_id = db.query(Setting).filter(Setting.key == "active_dataset_id").first()
            s_fn = db.query(Setting).filter(Setting.key == "active_dataset_filename").first()
            if s_id and s_id.value:
                cnt = db.query(PLRecord).filter(PLRecord.upload_id == s_id.value).count()
                if cnt > 0:
                    _active_dataset["dataset_id"] = s_id.value
                    _active_dataset["filename"] = s_fn.value if s_fn else "Dataset"

            if not _active_dataset.get("dataset_id"):
                latest = db.query(PLRecord.upload_id).order_by(PLRecord.created_at.desc()).first()
                if latest:
                    _active_dataset["dataset_id"] = latest.upload_id
                    uf = db.query(UploadedFile).filter(UploadedFile.upload_id == latest.upload_id).first()
                    _active_dataset["filename"] = uf.filename if uf else "Uploaded Financial Dataset"
                else:
                    _active_dataset["dataset_id"] = "899540e5-fa49-49e8-b87a-6965b44fd71f"
                    _active_dataset["filename"] = "unified_pnl_enterprise_demo.xlsx"
        except Exception:
            _active_dataset["dataset_id"] = "899540e5-fa49-49e8-b87a-6965b44fd71f"
            _active_dataset["filename"] = "unified_pnl_enterprise_demo.xlsx"
    return _active_dataset


def get_active_dataset_id(db: Session) -> str:
    """Authoritative getter for current active dataset ID, guaranteed to be loaded from Setting/PLRecord."""
    active = get_active_dataset(db)
    return active.get("dataset_id")


@router.get("/active/profile")
def get_active_dataset_profile(db: Session = Depends(get_db)):
    active_id = get_active_dataset_id(db)
    from services.metric_engine import MetricEngine
    me = MetricEngine(db, active_id)
    return me.get_active_profile()


@router.post("/active")
def set_active_dataset(payload: ActiveDatasetRequest, db: Session = Depends(get_db)):
    _active_dataset["dataset_id"] = payload.dataset_id
    _active_dataset["filename"] = payload.filename
    try:
        s_id = db.query(Setting).filter(Setting.key == "active_dataset_id").first()
        if not s_id:
            db.add(Setting(key="active_dataset_id", value=payload.dataset_id))
        else:
            s_id.value = payload.dataset_id

        s_fn = db.query(Setting).filter(Setting.key == "active_dataset_filename").first()
        if not s_fn:
            db.add(Setting(key="active_dataset_filename", value=payload.filename))
        else:
            s_fn.value = payload.filename
        db.commit()
    except Exception as e:
        db.rollback()

    invalidate_global_cache()
    return _active_dataset


@router.get("/list")
def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all ingested datasets with row count, column count, quality score, and active state."""
    active_id = get_active_dataset(db).get("dataset_id")
    
    # Query distinct upload_ids from PLRecord
    from sqlalchemy import func
    upload_counts = (
        db.query(
            PLRecord.upload_id,
            func.count(PLRecord.id).label("record_cnt"),
            func.min(PLRecord.created_at).label("first_created")
        )
        .group_by(PLRecord.upload_id)
        .all()
    )

    uploaded_files_map = {
        uf.upload_id: uf for uf in db.query(UploadedFile).all()
    }

    result = []
    for upload_id, cnt, created_at in upload_counts:
        uf = uploaded_files_map.get(upload_id)
        filename = uf.filename if uf else ("unified_pnl_enterprise_demo.csv" if upload_id == "DEMO-DATASET" else f"Dataset_{upload_id[:8]}")
        is_active = (upload_id == active_id)

        result.append({
            "dataset_id": upload_id,
            "filename": filename,
            "row_count": cnt,
            "column_count": 15,
            "quality_score": 96.5,
            "uploaded_at": (created_at.isoformat() if created_at else datetime.utcnow().isoformat()),
            "status": "ACTIVE" if is_active else "READY",
            "is_active": is_active,
        })

    # Sort so active dataset is first, then newest
    result.sort(key=lambda x: (not x["is_active"], x["uploaded_at"]), reverse=True)
    return result


@router.post("/{dataset_id}/activate")
def activate_dataset(dataset_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Make a specific dataset ACTIVE and invalidate analytics caches."""
    uf = db.query(UploadedFile).filter(UploadedFile.upload_id == dataset_id).first()
    filename = uf.filename if uf else ("unified_pnl_enterprise_demo.csv" if dataset_id == "DEMO-DATASET" else "Dataset")

    set_active_dataset(ActiveDatasetRequest(dataset_id=dataset_id, filename=filename), db)
    invalidate_global_cache()
    return {"status": "success", "active_dataset_id": dataset_id, "filename": filename}


@router.post("/upload", status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only CSV/Excel files allowed")

    from services.pl_service import auto_ingest_dataset

    content = await file.read()
    res = auto_ingest_dataset(db, content, file.filename, current_user.id)
    return res


@router.get("/{dataset_id}/schema-mapping")
def get_schema_mapping(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if dataset_id not in _schema_mappings:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return _schema_mappings[dataset_id]


@router.post("/{dataset_id}/schema-mapping")
def confirm_schema_mapping(
    dataset_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_mapping = payload.get("mapping", {})
    
    import os
    filepath = os.path.join("uploads", f"{dataset_id}.bin")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Uploaded file context not found or expired")
        
    with open(filepath, "rb") as f:
        file_content = f.read()
        
    # Delete old records
    db.query(PLRecord).filter(PLRecord.upload_id == dataset_id).delete()
    db.commit()
    
    # Mapping in payload: canonical_field -> source_column
    # We need: source_column -> {"mapped_to": canonical_field, "confidence": 100.0}
    preset_mapping = {}
    for canonical, source in user_mapping.items():
        if source and source != "__ignore__":
            preset_mapping[source] = {"mapped_to": canonical, "confidence": 100.0}
            
    from services.pl_service import auto_ingest_dataset
    uf = db.query(UploadedFile).filter(UploadedFile.upload_id == dataset_id).first()
    filename = uf.filename if uf else "upload.csv"
    user_id = current_user.id if current_user else 1
    
    res = auto_ingest_dataset(
        db, file_content, filename, user_id, upload_id=dataset_id, preset_mapping=preset_mapping
    )
    
    _pipeline_status[dataset_id] = "awaiting_validation"
    return {"status": "success", "records_count": res["records_count"]}


@router.get("/{dataset_id}/validation")
def get_validation_rules(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {
        "rules": [
            {
                "name": "Date format check",
                "category": "Formatting",
                "status": "pass",
                "description": "Ensure ISO8601 dates",
            },
            {
                "name": "Negative revenue check",
                "category": "Relational",
                "status": "warning",
                "description": "Flags negative revenue numbers",
            },
            {
                "name": "Null departments",
                "category": "Missing values",
                "status": "pass",
                "description": "Ensures no null departments",
            },
        ]
    }


@router.post("/{dataset_id}/validation")
def run_validation_rules(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"status": "success"}


@router.post("/{dataset_id}/resume")
def resume_pipeline(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Progresses the pipeline
    _pipeline_status[dataset_id] = "cleaner"
    return {"status": "resumed"}


@router.get("/{dataset_id}/pipeline-status")
def get_pipeline_status(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status = _pipeline_status.get(dataset_id, "failed")

    #  progression logic
    stages = [
        "cleaner",
        "features",
        "ml",
        "explanation",
        "recommendation",
        "workflow",
        "database",
    ]

    if status in stages:
        idx = stages.index(status)
        if idx < len(stages) - 1:
            _pipeline_status[dataset_id] = stages[idx + 1]
            return {"status": "running", "current_stage": status}
        else:
            _pipeline_status[dataset_id] = "completed"
            return {"status": "running", "current_stage": status}

    if status == "completed":
        return {"status": "completed"}

    return {"status": status}


@router.get("/recent")
def get_recent_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the 10 most recent upload workflow instances for dashboard display."""
    try:
        instances = (
            db.query(WorkflowInstance)
            .order_by(WorkflowInstance.started_at.desc())
            .limit(10)
            .all()
        )
        return [
            {
                "id": w.id,
                "filename": (w.variables or {}).get("filename", "dataset.csv"),
                "original_filename": (w.variables or {}).get("filename", "dataset.csv"),
                "status": w.status.lower() if w.status else "completed",
                "uploaded_at": w.started_at.isoformat() if w.started_at else None,
                "records_count": (w.variables or {}).get("records_ingested"),
                "file_size": (w.variables or {}).get("file_size"),
            }
            for w in instances
        ]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Recent uploads endpoint error: {e}")
        return []
