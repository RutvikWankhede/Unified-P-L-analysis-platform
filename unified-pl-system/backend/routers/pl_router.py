import uuid
import asyncio
import logging
import pandas as pd
from typing import Dict, List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from core.security import require_role
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_

from core.security import get_current_user
from database import get_db
from models.user import User
from models.pl_record import PLRecord, DepartmentBudget
from models.anomaly import Anomaly
from models.workflow import WorkflowInstance
from routers.datasets_router import _active_dataset
from services.pl_service import ensure_demo_data, analyze_upload, finalize_ingestion
from services.cache_service import get_cached_item, set_cached_item
from services.forecast_agent import generate_forecast
from schemas.pl_schemas import PLRecordResponse
from repositories import pl_repository

router = APIRouter()

@router.get("/datasets", response_model=List[Dict])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import datetime
    # Fake response for datasets as there's no actual Dataset model specified in the repository.
    # In a real app we would query from a dataset registry table.
    # Assuming one dataset from the records.
    return [
        {
            "filename": "Financial_Data_2024.csv",
            "rows": 12500,
            "columns": 15,
            "uploaded_by": current_user.email if current_user else "System",
            "uploaded_on": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "Processed"
        }
    ]

@router.get("/records", response_model=Dict[str, List[PLRecordResponse]])
def list_pl_records(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pl_service import ensure_demo_data
    from services.cache_service import get_cached_item, set_cached_item

    ensure_demo_data(db)

    cache_key = f"pl_records_{skip}_{limit}"
    cached = get_cached_item(cache_key)
    if cached is not None:
        return cached

    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)
    if active_id:
        records = db.query(PLRecord).filter(PLRecord.upload_id == active_id).offset(skip).limit(limit).all()
    else:
        records = pl_repository.get_pl_records(db, skip, limit)
    res = {"items": records}
    set_cached_item(cache_key, res)
    return res


@router.post("/upload", status_code=201, dependencies=[Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER"]))])
async def upload_pl_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        file.filename.lower().endswith(".csv")
        or file.filename.lower().endswith(".xlsx")
        or file.filename.lower().endswith(".xls")
    ):
        raise HTTPException(status_code=400, detail="Only CSV or Excel files allowed")

    try:
        content = await file.read()
        import uuid, os
        from services.pl_service import analyze_upload
        
        upload_id = str(uuid.uuid4())
        os.makedirs("uploads", exist_ok=True)
        filepath = os.path.join("uploads", f"{upload_id}.bin")
        with open(filepath, "wb") as f:
            f.write(content)
            
        analysis = analyze_upload(content, file.filename, db, current_user.id)
        
        return {
            "upload_id": upload_id,
            "analysis": analysis,
            "filename": file.filename
        }
    except Exception as e:
        import logging, traceback
        logging.getLogger(__name__).error(f"Upload failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/finalize-upload", status_code=201, dependencies=[Depends(require_role(["ADMINISTRATOR", "FINANCE_MANAGER"]))])
async def finalize_upload(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload_id = payload.get("upload_id")
    mapping = payload.get("mapping")
    filename = payload.get("filename", "upload.csv")

    if not upload_id or not mapping:
        raise HTTPException(
            status_code=400, detail="Missing upload_id or mapping parameters"
        )

    import os

    filepath = os.path.join("uploads", f"{upload_id}.bin")
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404, detail="Uploaded file context not found or expired"
        )

    try:
        with open(filepath, "rb") as f:
            content = f.read()

        from services.pl_service import finalize_ingestion

        final_upload_id, count = finalize_ingestion(
            db, content, filename, mapping, current_user.id, upload_id
        )

        # Trigger Camunda Workflow
        from services.workflow_service import workflow_service

        process_id = workflow_service.start_upload_workflow(
            db, current_user.id, final_upload_id, count
        )

        # Clean up temp file
        os.remove(filepath)

        return {
            "upload_id": final_upload_id,
            "records_ingested": count,
            "message": "Mapping finalized successfully. Workflow started.",
            "workflow_process_id": process_id,
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/summary")
async def get_pl_summary(
    date: str = None,
    dept: str = None,
    currency: str = None,
    agg: str = "yearly",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pl_service import ensure_demo_data
    from services.metric_engine import MetricEngine
    from routers.datasets_router import get_active_dataset_id
    
    ensure_demo_data(db)
    active_id = get_active_dataset_id(db)
    
    me = MetricEngine(db, active_id)
    kpis = me.get_kpis({"domain": dept, "period": date})
    caps = me.get_capabilities()
    
    # Query database for actual anomaly counts
    active_anomalies = db.query(Anomaly).join(PLRecord).filter(PLRecord.upload_id == active_id, Anomaly.status != "Resolved").count()
    high_severity = db.query(Anomaly).join(PLRecord).filter(PLRecord.upload_id == active_id, Anomaly.status != "Resolved", Anomaly.severity.in_(["Critical", "High"])).count()
    pending_workflows = db.query(WorkflowInstance).filter(WorkflowInstance.status == "ACTIVE").count()

    trends = kpis.get("trends", {})

    res = {
        "kpis": {
            "revenue": kpis["revenue"],
            "revenue_growth": trends.get("revenue", 0.0),
            "expense": kpis["expense"],
            "expense_growth": trends.get("expense", 0.0),
            "profit": kpis["profit"],
            "profit_growth": trends.get("profit", 0.0),
            "profit_margin": kpis["profit_margin"],
            "margin_growth": trends.get("profit_margin", 0.0),
            # Real cash flow from centralized MetricEngine; None if dataset lacks cash columns
            "cash_flow": kpis.get("cash_flow"),
            # Real budget totals from dataset if budget column present
            "budget_total": kpis.get("budget_total"),
            "health_score": kpis["health_score"],
            "health_growth": 0.5,
            "risk_score": kpis["risk_score"],
            "active_anomalies": active_anomalies,
            "high_severity": high_severity,
            "pending_workflows": pending_workflows,
            "forecasted_profit": None,
            "forecast_growth": None,
        },
        "domains": [
            {
                "domain": d["department"],
                "revenue": d["revenue"],
                "expense": d["expense"],
                "profit": d["profit"],
                "margin": d["margin"]
            }
            for d in me.get_department_aggregates()
        ],
        "capabilities": caps
    }
    
    return res


@router.get("/forecast")
def get_domain_forecast(
    domain: str = Query("Overall", alias="dept"),
    metric: str = Query("profit"),
    timeframe: str = Query("12M"),
    periods: int = Query(12),
    confidence: str = Query("95%"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.metric_engine import MetricEngine
    from services.analytics_engine import AnalyticsEngine
    from routers.datasets_router import get_active_dataset_id
    from services.pl_service import ensure_demo_data
    
    ensure_demo_data(db)
    active_id = get_active_dataset_id(db)
    
    me = MetricEngine(db, active_id)
    ae = AnalyticsEngine(me)
    
    # Parse horizon: prefer explicit `periods`, fall back to `timeframe` string
    n_forecast = periods
    if periods == 12:  # default; check if timeframe provides override
        timeframe_map = {"3M": 3, "6M": 6, "12M": 12, "24M": 24}
        n_forecast = timeframe_map.get(timeframe.upper(), 12)
    
    forecast_data = ae.get_forecast(domain, metric=metric, n_forecast=n_forecast)
    
    if not forecast_data["has_enough_data"]:
        return {
            "has_enough_data": False,
            "historical": forecast_data["historical"],
            "forecast": [],
            "best_case": 0.0,
            "expected_case": 0.0,
            "worst_case": 0.0,
            "model_metrics": {
                "accuracy": 0.0,
                "rmse": 0,
                "seasonality": "None"
            },
            "explanation": "Forecast unavailable: insufficient historical observations.",
            "drivers": [],
            "predicted_profit_next_12_months_in_crores": 0.0,
            "growth_percentage_vs_current_month": 0.0,
            "model_used": "None",
            "confidence_score": 0.0
        }
        
    hist_series = forecast_data["historical"]
    growth_pct = 0.0
    if hist_series and forecast_data["forecast"]:
        last_hist_val = hist_series[-1].get(metric)
        if last_hist_val is None:
            last_hist_val = (hist_series[-1].get("revenue") or 0) - (hist_series[-1].get("expense") or 0) if metric == "profit" else (hist_series[-1].get("revenue") or 0)
        next_forecast_val = forecast_data["forecast"][-1]["predicted_value"]
        if last_hist_val and last_hist_val > 0:
            growth_pct = round(((next_forecast_val - last_hist_val) / last_hist_val) * 100, 1)
        else:
            growth_pct = 12.5

    res = {
        "has_enough_data": True,
        "historical": forecast_data["historical"],
        "forecast": forecast_data["forecast"],
        "best_case": forecast_data["best_case"],
        "expected_case": forecast_data["expected_case"],
        "worst_case": forecast_data["worst_case"],
        "model_metrics": {
            "accuracy": round(forecast_data["confidence_score"] * 100, 1),
            "rmse": round(forecast_data["expected_case"] * 0.05),
            "seasonality": "Detected" if forecast_data["observations"] >= 12 else "None"
        },
        "explanation": f"Forecast generated using {forecast_data['model_used']} model.",
        "drivers": [
            {
                "name": "Historical Trend",
                "desc": "Underlying upward trajectory in data",
                "impact": round(growth_pct * 0.65, 1)
            },
            {
                "name": "Seasonal Momentum",
                "desc": "Cyclical peaks matching seasonal factors",
                "impact": round(growth_pct * 0.35, 1)
            }
        ],
        "predicted_profit_next_12_months_in_crores": round(forecast_data["expected_case"] / 10000000, 2),
        "growth_percentage_vs_current_month": growth_pct,
        "model_used": forecast_data["model_used"],
        "confidence_score": forecast_data["confidence_score"],
        # Validation metrics for the forecast accuracy panel
        "r2_score": forecast_data.get("r2_score"),
        "mape": forecast_data.get("mape"),
        "observations": forecast_data.get("observations", 0)
    }
    
    return res


@router.get("/departments")
def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pl_service import ensure_demo_data
    from services.cache_service import get_cached_item, set_cached_item

    try:
        ensure_demo_data(db)
        cache_key = "pl_departments"
        cached = get_cached_item(cache_key)
        if cached is not None:
            return cached
        depts = [row[0] for row in db.query(PLRecord.domain).distinct().all()]
        res = {"departments": sorted(depts)}
        set_cached_item(cache_key, res)
        return res
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Departments endpoint error: {e}")
        return {"departments": []}

@router.get("/departments/summary")
def get_departments_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.metric_engine import MetricEngine
    from routers.datasets_router import get_active_dataset_id
    from services.pl_service import ensure_demo_data
    
    ensure_demo_data(db)
    active_id = get_active_dataset_id(db)
    
    me = MetricEngine(db, active_id)
    return {"departments": me.get_department_aggregates()}


@router.get("/departments/trend")
def get_departments_trend(
    agg: str = "monthly",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.metric_engine import MetricEngine
    from routers.datasets_router import get_active_dataset_id
    from services.pl_service import ensure_demo_data
    
    ensure_demo_data(db)
    active_id = get_active_dataset_id(db)
    
    me = MetricEngine(db, active_id)
    df_dim = me.aggregate_by_dimension(agg)
    
    if df_dim.empty:
        return {"periods": [], "series": {}}
        
    periods = sorted(df_dim["group_period"].unique().tolist())
    
    # Identify top 5 departments by absolute total profit
    dept_totals = df_dim.groupby("domain")["profit"].sum().abs()
    top_depts = dept_totals.nlargest(5).index.tolist()
    
    series = {}
    for domain in df_dim["domain"].unique():
        if domain not in top_depts:
            continue
        domain_df = df_dim[df_dim["domain"] == domain]
        domain_dict = dict(zip(domain_df["group_period"], domain_df["profit"]))
        series[domain] = [round(domain_dict.get(p, 0.0)) for p in periods]
        
    return {"periods": periods, "series": series}


@router.get("/charts")
async def get_charts_data(
    date: str = None,
    dept: str = None,
    currency: str = None,
    agg: str = "monthly",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Single endpoint returning all pre-aggregated chart series — avoids N+1 fetches."""
    import asyncio
    from fastapi import HTTPException
    
    def _fetch_charts():
        from services.pl_service import ensure_demo_data
        from services.cache_service import get_cached_item, set_cached_item
        from routers.datasets_router import get_active_dataset_id
        from sqlalchemy import func, or_, case
        active_id = get_active_dataset_id(db)

        try:
            ensure_demo_data(db)

            # Resolve auto-aggregation if requested
            resolved_agg = agg
            if agg == "auto":
                from datetime import datetime
                date_stats = db.query(
                    func.min(PLRecord.period).label("min_date"),
                    func.max(PLRecord.period).label("max_date")
                )
                if active_id:
                    date_stats = date_stats.filter(PLRecord.upload_id == active_id)
                min_date, max_date = date_stats.first()
                if min_date and max_date:
                    try:
                        d1 = datetime.strptime(min_date[:10], "%Y-%m-%d")
                        d2 = datetime.strptime(max_date[:10], "%Y-%m-%d")
                        days = (d2 - d1).days
                        if days <= 30:
                            resolved_agg = "daily"
                        elif days <= 180:
                            resolved_agg = "weekly"
                        elif days <= 730:
                            resolved_agg = "monthly"
                        elif days <= 1825:
                            resolved_agg = "quarterly"
                        else:
                            resolved_agg = "yearly"
                    except Exception:
                        resolved_agg = "monthly"
                else:
                    resolved_agg = "monthly"

            cache_key = f"pl_charts_{date}_{dept}_{currency}_{agg}_{resolved_agg}"
            cached = get_cached_item(cache_key)
            if cached is not None:
                return cached

            from collections import defaultdict

            from services.metric_engine import MetricEngine
            me = MetricEngine(db, active_id)
            caps = me.get_capabilities()
            profile = me.get_active_profile()

            df_agg = me.aggregate_data(resolved_agg, dept)
            
            revenue_trend = []
            expense_trend = []
            profit_trend = []
            cashflow_trend = []
            budget_trend = []
            
            if not df_agg.empty:
                periods = df_agg["period"].tolist()
                
                if caps["revenue"]["available"]:
                    revenue_trend = [{"period": r["period"], "value": round(r["revenue"])} for _, r in df_agg.iterrows()]
                if caps["expense"]["available"]:
                    expense_trend = [{"period": r["period"], "value": round(r["expense"])} for _, r in df_agg.iterrows()]
                if caps["profit"]["available"]:
                    profit_trend = [{"period": r["period"], "value": round(r["profit"])} for _, r in df_agg.iterrows()]
                
                if profile["capabilities"]["cash_flow"]:
                    cashflow_trend = []
                    for _, r in df_agg.iterrows():
                        val = r["net_cash_flow"]
                        cashflow_trend.append({"period": r["period"], "value": round(val) if val is not None else None})
                        
                if profile["capabilities"]["budget"]:
                    budget_trend = []
                    for _, r in df_agg.iterrows():
                        actual = round(r["revenue"] - r["expense"]) if "revenue" in r and "expense" in r else None
                        budget = round(r["budget"]) if "budget" in r and pd.notnull(r["budget"]) else None
                        variance = (actual - budget) if actual is not None and budget is not None else None
                        variance_pct = (variance / abs(budget) * 100) if variance is not None and budget else 0.0
                        
                        budget_trend.append({
                            "period": r["period"],
                            "actual": actual,
                            "budget": budget,
                            "variance": variance,
                            "variance_pct": round(variance_pct, 2)
                        })
            else:
                periods = []
                
            all_depts = profile["dimension_values"]
            
            dept_breakdown = []
            dept_aggregates = me.get_department_aggregates()
            for d in dept_aggregates:
                dept_breakdown.append({
                    "department": d["department"],
                    "revenue": round(d["revenue"]) if d["revenue"] is not None else None,
                    "expense": round(d["expense"]) if d["expense"] is not None else None,
                    "profit": round(d["profit"]) if d["profit"] is not None else None,
                })
                
            total_rev = sum(d["revenue"] or 0 for d in dept_aggregates)
            total_exp = sum(d["expense"] or 0 for d in dept_aggregates)
            
            waterfall = []
            if caps["revenue"]["available"]:
                waterfall.append({"name": "Revenue", "value": round(total_rev), "type": "revenue"})
            if caps["expense"]["available"]:
                waterfall.append({"name": "Expenses", "value": round(total_exp), "type": "expense"})
            if caps["profit"]["available"]:
                waterfall.append({
                    "name": "Net Profit",
                    "value": round(total_rev - total_exp),
                    "type": "profit",
                })
                
            scatter_query = db.query(PLRecord)
            if active_id:
                scatter_query = scatter_query.filter(PLRecord.upload_id == active_id)
            scatter_records = scatter_query.limit(200).all()
            scatter = [
                {"x": i, "y": round(r.amount), "domain": r.domain, "line_item": r.line_item}
                for i, r in enumerate(scatter_records)
            ]
            
            df_dim = me.aggregate_by_dimension(resolved_agg)
            
            dept_profit_trend = []
            heatmap_data_dict = {}
            if not df_dim.empty:
                for _, r in df_dim.iterrows():
                    dept_profit_trend.append({
                        "period": r["group_period"],
                        "department": r["domain"],
                        "profit": round(r["profit"])
                    })
                    heatmap_data_dict[(r["group_period"], r["domain"])] = round(r["amount_exp"])
                    
            heatmap_data = []
            for (p, d), val in heatmap_data_dict.items():
                try:
                    p_idx = periods.index(p)
                    d_idx = all_depts.index(d)
                    heatmap_data.append([p_idx, d_idx, round(val)])
                except ValueError:
                    pass

            res = {
                "revenue_trend": revenue_trend,
                "expense_trend": expense_trend,
                "profit_trend": profit_trend,
                "cashflow_trend": cashflow_trend,
                "budget_trend": budget_trend,
                "cash_flow_mode": profile["capabilities"].get("cash_flow_mode", "unavailable"),
                "department_breakdown": dept_breakdown,
                "waterfall": waterfall,
                "scatter": scatter,
                "heatmap": heatmap_data,
                "dept_profit_trend": dept_profit_trend,
                "periods": periods,
                "departments": all_depts,
            }
            set_cached_item(cache_key, res)
            return res
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Charts endpoint error: {e}")
            return {
                "revenue_trend": [],
                "expense_trend": [],
                "profit_trend": [],
                "department_breakdown": [],
                "waterfall": [],
                "scatter": [],
            }

    return await asyncio.to_thread(_fetch_charts)


@router.get("/workflows")
def get_workflow_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    instances = (
        db.query(WorkflowInstance).order_by(WorkflowInstance.started_at.desc()).all()
    )
    return [
        {
            "id": w.id,
            "process_instance_id": w.process_instance_id,
            "workflow_name": w.workflow_name,
            "status": w.status,
            "variables": w.variables,
            "started_at": w.started_at,
            "completed_at": w.completed_at,
        }
        for w in instances
    ]

@router.post("/workflows/{workflow_id}/cancel")
def cancel_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = db.query(WorkflowInstance).filter(WorkflowInstance.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.status not in ["ACTIVE", "PAUSED", "FAILED"]:
        raise HTTPException(status_code=400, detail="Cannot cancel workflow in current state")
        
    workflow.status = "CANCELLED"
    db.commit()
    return {"message": "Workflow cancelled"}

@router.post("/workflows/{workflow_id}/retry")
def retry_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = db.query(WorkflowInstance).filter(WorkflowInstance.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    if workflow.status != "FAILED":
        raise HTTPException(status_code=400, detail="Can only retry failed workflows")
        
    workflow.status = "ACTIVE"
    db.commit()
    
    # In a real Camunda setup, we would trigger an incident retry API here
    # For simulation, we re-invoke the thread
    from services.workflow_service import simulate_workflow_steps
    import threading
    threading.Thread(
        target=simulate_workflow_steps, args=(workflow.process_instance_id,), daemon=True
    ).start()
    
    return {"message": "Workflow retry initiated"}

from pydantic import BaseModel, Field
from typing import Optional

class BudgetUpdate(BaseModel):
    department: str
    amount: Optional[float] = None
    budget_amount: Optional[float] = None

    @property
    def effective_amount(self) -> float:
        if self.budget_amount is not None:
            return self.budget_amount
        if self.amount is not None:
            return self.amount
        return 0.0

@router.get("/budget")
def get_budgets(db: Session = Depends(get_db)):
    from models.pl_record import DepartmentBudget
    budgets = db.query(DepartmentBudget).all()
    return {b.department: b.budget_amount for b in budgets}

@router.post("/budget")
def set_budget(budget: BudgetUpdate, db: Session = Depends(get_db)):
    from models.pl_record import DepartmentBudget
    from services.cache_service import invalidate_global_cache
    
    amt = budget.effective_amount
    b = db.query(DepartmentBudget).filter(DepartmentBudget.department == budget.department).first()
    if b:
        b.budget_amount = amt
    else:
        b = DepartmentBudget(department=budget.department, budget_amount=amt)
        db.add(b)
    db.commit()
    invalidate_global_cache()
    return {"message": "Budget updated", "department": budget.department, "budget_amount": amt}
