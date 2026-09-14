import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from repositories.anomaly_repository import (
    get_anomalies,
    get_anomaly,
    update_anomaly_status,
)
from schemas.anomaly_schemas import (
    AnomalyDetail,
    AnomalyResponse,
    AnomalyUpdateStatus,
    DetectionResult,
)
from models.anomaly import Anomaly

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


@router.post("/detect", response_model=DetectionResult, status_code=201)
@limiter.limit("20/minute")
def detect_anomalies_endpoint(request: Request, upload_id: str, db: Session = Depends(get_db)):
    safe_upload_id = re.sub(r"[^a-zA-Z0-9_\-]", "", str(upload_id).strip())
    if not safe_upload_id:
        raise HTTPException(status_code=400, detail="Invalid upload_id parameter")

    from services.cache_service import invalidate_global_cache
    from services.anomaly_service import run_anomaly_detection

    invalidate_global_cache()

    anomalies = run_anomaly_detection(db, safe_upload_id)
    high = sum(1 for a in anomalies if a.severity == "High")
    med = sum(1 for a in anomalies if a.severity == "Medium")
    low = sum(1 for a in anomalies if a.severity == "Low")
    return {
        "upload_id": safe_upload_id,
        "anomalies_detected": len(anomalies),
        "high_severity_count": high,
        "medium_severity_count": med,
        "low_severity_count": low,
    }


DEPT_GROUPS = {
    "commercial": ["sales", "marketing", "marketing & sales", "sales & marketing", "commercial"],
    "technology": ["it", "r&d", "engineering", "tech", "technology", "information technology"],
    "operations": ["operations", "logistics", "procurement", "supply chain"],
    "corporate": ["finance", "legal", "human resources", "hr", "administration", "admin"],
}


def get_matching_domains(dept: str, db: Session, active_id: str | None = None) -> list[str]:
    from models.pl_record import PLRecord

    if not dept or str(dept).strip().lower() in ["all", "all departments", "overall", "total", "none"]:
        return []

    dept_lower = str(dept).strip().lower()

    query = db.query(PLRecord.domain).distinct()
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    all_domains = [d[0] for d in query.all() if d[0]]

    # 1. Exact match
    exact = [d for d in all_domains if d.lower() == dept_lower]
    if exact:
        return exact

    # 2. Group match
    group_candidates = DEPT_GROUPS.get(dept_lower, [])
    if group_candidates:
        matched = [d for d in all_domains if d.lower() in group_candidates or any(cand in d.lower() for cand in group_candidates)]
        if matched:
            return matched

    # 3. Substring match
    matched = [d for d in all_domains if dept_lower in d.lower() or d.lower() in dept_lower]
    return matched or [dept]


@router.get("/summary")
def get_anomaly_summary(dept: str = "all", db: Session = Depends(get_db)):
    from models.pl_record import PLRecord
    from routers.datasets_router import get_active_dataset_id
    from collections import defaultdict
    import re

    active_id = get_active_dataset_id(db)
    query = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)

    matching_depts = get_matching_domains(dept, db, active_id)
    if matching_depts:
        query = query.filter(PLRecord.domain.in_(matching_depts))

    anomalies = query.all()

    total = len(anomalies)
    critical = sum(1 for a in anomalies if (a.severity or "").lower() == "critical")
    high = sum(1 for a in anomalies if (a.severity or "").lower() == "high")
    medium = sum(1 for a in anomalies if (a.severity or "").lower() == "medium")
    low = sum(1 for a in anomalies if (a.severity or "").lower() == "low")

    # Group by period to calculate previous period diff
    period_counts = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0})
    for a in anomalies:
        p = (a.pl_record.period if a.pl_record else "") or ""
        # normalize to YYYY-MM
        match = re.search(r"(\d{4})[-/](\d{1,2})", p)
        if match:
            norm_p = f"{match.group(1)}-{int(match.group(2)):02d}"
        else:
            norm_p = p[:7] if len(p) >= 7 else p
        if not norm_p:
            norm_p = "Current"
        period_counts[norm_p]["total"] += 1
        s = (a.severity or "medium").lower()
        if s in period_counts[norm_p]:
            period_counts[norm_p][s] += 1

    sorted_periods = sorted(period_counts.keys())
    diffs = {}
    if len(sorted_periods) >= 2:
        curr = period_counts[sorted_periods[-1]]
        prev = period_counts[sorted_periods[-2]]
        for key in ["total", "critical", "high", "medium", "low"]:
            c_val = curr[key]
            p_val = prev[key]
            if p_val == 0 and c_val == 0:
                diffs[key] = {"pct": 0, "text": "0%", "is_pos": None}
            elif p_val == 0:
                diffs[key] = {"pct": 100, "text": "↑ 100%", "is_pos": True}
            else:
                pct = round(((c_val - p_val) / p_val) * 100)
                diffs[key] = {
                    "pct": pct,
                    "text": f"{'↑' if pct > 0 else '↓'} {abs(pct)}%",
                    "is_pos": pct > 0
                }
    else:
        for key in ["total", "critical", "high", "medium", "low"]:
            diffs[key] = {"pct": 0, "text": "0%", "is_pos": None}

    return {
        "total": total,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "diffs": diffs,
    }


@router.get("/trend")
def get_anomaly_trend(dept: str = "all", range: str = "12m", db: Session = Depends(get_db)):
    from models.pl_record import PLRecord
    from routers.datasets_router import get_active_dataset_id
    from collections import defaultdict
    import re
    
    active_id = get_active_dataset_id(db)
    query = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)

    matching_depts = get_matching_domains(dept, db, active_id)
    if matching_depts:
        query = query.filter(PLRecord.domain.in_(matching_depts))

    anomalies = query.all()

    # Aggregate by financial period (e.g. YYYY-MM)
    period_map = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0})
    for a in anomalies:
        p = (a.pl_record.period if a.pl_record else "") or ""
        match = re.search(r"(\d{4})[-/](\d{1,2})", p)
        if match:
            norm_p = f"{match.group(1)}-{int(match.group(2)):02d}"
        else:
            norm_p = p[:7] if len(p) >= 7 else (p or "2026-01")
        
        period_map[norm_p]["total"] += 1
        s = (a.severity or "medium").lower()
        if s in period_map[norm_p]:
            period_map[norm_p][s] += 1

    sorted_periods = sorted(period_map.keys())

    # Filter by range
    r_lower = (range or "12m").lower()
    if r_lower == "3m":
        selected_periods = sorted_periods[-3:]
    elif r_lower == "6m":
        selected_periods = sorted_periods[-6:]
    elif r_lower == "12m":
        selected_periods = sorted_periods[-12:]
    elif r_lower == "24m":
        selected_periods = sorted_periods[-24:]
    else:
        selected_periods = sorted_periods

    trend = [
        {
            "period": p,
            "date": p,
            "count": period_map[p]["total"],
            "total": period_map[p]["total"],
            "critical": period_map[p]["critical"],
            "high": period_map[p]["high"],
            "medium": period_map[p]["medium"],
            "low": period_map[p]["low"],
        }
        for p in selected_periods
    ]

    return {"trend": trend}


@router.get("/heatmap")
def get_anomaly_heatmap(dept: str = "all", metric: str = "count", db: Session = Depends(get_db)):
    from models.pl_record import PLRecord
    from routers.datasets_router import get_active_dataset_id

    active_id = get_active_dataset_id(db)

    # Fetch all active departments dynamically
    dept_query = db.query(PLRecord.domain).distinct()
    if active_id:
        dept_query = dept_query.filter(PLRecord.upload_id == active_id)
    all_depts = sorted([d[0] for d in dept_query.all() if d[0] and d[0] not in ["All Departments", "Unknown", "All"]])

    matching_depts = get_matching_domains(dept, db, active_id)
    if matching_depts:
        display_depts = [d for d in all_depts if d in matching_depts] or matching_depts
    else:
        display_depts = all_depts

    query = db.query(Anomaly).join(PLRecord, PLRecord.id == Anomaly.pl_record_id)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    if matching_depts:
        query = query.filter(PLRecord.domain.in_(matching_depts))

    anomalies = query.all()

    # Matrix: severity -> department -> { count, amount }
    severities = ["Critical", "High", "Medium", "Low"]
    matrix = {s: {d: {"count": 0, "amount": 0.0} for d in display_depts} for s in severities}

    max_val = 1
    for a in anomalies:
        s_raw = (a.severity or "Medium").capitalize()
        s = s_raw if s_raw in severities else "Medium"
        d = a.pl_record.domain if a.pl_record else "General"
        amt = abs(a.pl_record.amount if a.pl_record else 0.0)

        if d in matrix[s]:
            matrix[s][d]["count"] += 1
            matrix[s][d]["amount"] += amt
            val = matrix[s][d]["amount"] if metric == "amount" else matrix[s][d]["count"]
            if val > max_val:
                max_val = val

    return {
        "departments": display_depts,
        "severities": severities,
        "matrix": matrix,
        "metric": metric,
        "max_value": max_val
    }


@router.get("/", response_model=List[AnomalyResponse])
async def get_anomalies_list(skip: int = 0, limit: int = 5000, agg: str = None, db: Session = Depends(get_db)):
    import asyncio
    from services.pl_service import ensure_demo_data
    from services.cache_service import get_cached_item, set_cached_item

    def _fetch():
        try:
            ensure_demo_data(db)

            from routers.datasets_router import get_active_dataset_id
            active_id = get_active_dataset_id(db) or "default"
            cache_key = f"anomalies_{active_id}_{skip}_{limit}_{agg}"
            cached = get_cached_item(cache_key)
            if cached is not None:
                return cached

            res = get_anomalies(db, skip, limit, agg)
            for anomaly in res:
                if anomaly.pl_record:
                    anomaly.line_item = anomaly.pl_record.line_item
                    anomaly.department = anomaly.pl_record.domain
                    anomaly.impact_amount = anomaly.pl_record.amount
                    anomaly.period = anomaly.pl_record.period
                    anomaly.date = anomaly.pl_record.period
                    anomaly.description = (
                        f"{anomaly.pl_record.line_item} is {anomaly.severity.lower()} severity "
                        f"({anomaly.percentile_rank * 100:.1f}th percentile) due to unexpected "
                        f"{anomaly.pl_record.amount} amount in {anomaly.pl_record.domain} domain."
                    )
            set_cached_item(cache_key, res)
            return res
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to fetch anomalies: {e}")
            return []

    return await asyncio.to_thread(_fetch)


@router.get("/{id}", response_model=AnomalyDetail)
def get_anomaly_detail(id: int, db: Session = Depends(get_db)):
    anomaly = get_anomaly(db, id)
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return anomaly


@router.patch("/{id}/status", response_model=AnomalyResponse)
def update_status(
    id: int, status_update: AnomalyUpdateStatus, db: Session = Depends(get_db)
):
    from services.cache_service import invalidate_global_cache

    invalidate_global_cache()

    updated = update_anomaly_status(db, id, status_update.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return updated
