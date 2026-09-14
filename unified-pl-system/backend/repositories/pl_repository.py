from typing import List

from sqlalchemy.orm import Session

from models.pl_record import PLRecord


def _sanitize_record(rec: dict, upload_id: str, user_id: int) -> dict:
    import math
    import numpy as np
    import pandas as pd
    
    # Sanitize dynamic_data for JSON
    raw_dyn = rec.get("dynamic_data") or {}
    clean_dyn = {}
    if isinstance(raw_dyn, dict):
        for k, v in raw_dyn.items():
            k_str = str(k)
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) or pd.isnull(v):
                clean_dyn[k_str] = None
            elif isinstance(v, (np.integer, int)):
                clean_dyn[k_str] = int(v)
            elif isinstance(v, (np.floating, float)):
                clean_dyn[k_str] = round(float(v), 4)
            elif isinstance(v, (pd.Timestamp, pd.Period)):
                clean_dyn[k_str] = str(v)
            else:
                clean_dyn[k_str] = str(v)

    # Sanitize amount
    raw_amt = rec.get("amount", 0.0)
    try:
        if raw_amt is None or pd.isnull(raw_amt) or (isinstance(raw_amt, float) and (math.isnan(raw_amt) or math.isinf(raw_amt))):
            amt = 0.0
        else:
            amt = float(raw_amt)
    except (ValueError, TypeError):
        amt = 0.0

    return {
        "upload_id": upload_id,
        "uploaded_by": user_id,
        "domain": str(rec.get("domain") or "All Departments").strip()[:50] or "All Departments",
        "period": str(rec.get("period") or "2026-01-01").strip()[:20] or "2026-01-01",
        "line_item": str(rec.get("line_item") or "Financial Line Item").strip()[:100] or "Financial Line Item",
        "amount": amt,
        "currency": str(rec.get("currency") or "USD").strip()[:10] or "USD",
        "cost_center": str(rec.get("cost_center") or "").strip()[:50] if rec.get("cost_center") else None,
        "dynamic_data": clean_dyn,
    }


def create_pl_records(db: Session, mappings: List[dict], upload_id: str, user_id: int, batch_size: int = 1000):
    if not mappings:
        return []

    inserted_objs = []
    total = len(mappings)

    for i in range(0, total, batch_size):
        chunk = mappings[i : i + batch_size]
        sanitized_chunk = [_sanitize_record(m, upload_id, user_id) for m in chunk]
        try:
            objs = [PLRecord(**rec) for rec in sanitized_chunk]
            db.add_all(objs)
            db.commit()
            inserted_objs.extend(objs)
        except Exception as e:
            db.rollback()
            for rec in sanitized_chunk:
                try:
                    obj = PLRecord(**rec)
                    db.add(obj)
                    db.commit()
                    inserted_objs.append(obj)
                except Exception:
                    db.rollback()

    return inserted_objs


def get_pl_records(db: Session, skip: int = 0, limit: int = 100):
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)
    query = db.query(PLRecord)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    return query.offset(skip).limit(limit).all()

def get_pl_record(db: Session, record_id: int):
    return db.query(PLRecord).filter(PLRecord.id == record_id).first()

def get_pl_records_by_upload_id(db: Session, upload_id: str):
    return db.query(PLRecord).filter(PLRecord.upload_id == upload_id).all()
