"""
reports.py - Financial Reporting Suite Router
============================================
Data-driven reporting endpoints providing:
- Structured report data for frontend interactive preview
- Multi-format generation & export (CSV, HTML, PDF, Excel)
- 5 Canonical Report Types:
  1. Executive P&L Report
  2. Department Performance Report
  3. Budget vs Actual Variance Report
  4. Anomaly & Risk Report
  5. Forecast & Predictive Trajectory Report
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.pl_record import PLRecord, DepartmentBudget
from models.anomaly import Anomaly
from services.report_service import report_service
from services.copilot_agent import get_financial_context_and_calc, format_inr

router = APIRouter()

@router.get("/data")
def get_report_data(
    report_type: str = Query("executive", description="executive | department | variance | anomaly | forecast | all"),
    dept: str = Query("all", description="Department filter or 'all'"),
    period: str = Query("all", description="Fiscal year, period filter, or 'all'"),
    agg: str = Query("monthly", description="daily | weekly | monthly | quarterly | yearly"),
    db: Session = Depends(get_db)
):
    """
    Produce live, canonical dataset metrics and structured tables for interactive report previews.
    Supports dynamic department filtering, aggregation frequency, and time-range filtering.
    """
    from services.metric_engine import MetricEngine
    from routers.datasets_router import get_active_dataset_id
    from services.pl_service import ensure_demo_data

    ensure_demo_data(db)
    ctx = get_financial_context_and_calc(db)
    ent = ctx["enterprise"]
    depts: Dict[str, Dict[str, Any]] = ctx["departments"]
    dataset_name = ctx["dataset_name"]
    fc = ctx["forecast"]
    active_id = ctx.get("dataset_id") or get_active_dataset_id(db)

    now_str = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")

    me = MetricEngine(db, active_id)
    profile = me.get_active_profile()

    # Determine resolved department
    resolved_dept = me._resolve_dept_name(dept)
    agg_dept = resolved_dept if resolved_dept else None

    # Filter departments list
    departments_list = sorted(list(depts.keys())) if depts else []
    if resolved_dept and resolved_dept in depts:
        filtered_depts = {resolved_dept: depts[resolved_dept]}
    elif resolved_dept:
        # Match case-insensitively
        match_k = next((k for k in depts if k.lower() == resolved_dept.lower()), None)
        filtered_depts = {match_k: depts[match_k]} if match_k else depts
    else:
        filtered_depts = depts

    # ── Trend Series from MetricEngine ────────────────────────────
    df = me.aggregate_data(agg, dept=agg_dept)
    
    # Filter by period if specific year provided (e.g., '2024')
    if period and period.lower() not in ["all", "overall", "all periods"] and not df.empty and "period" in df.columns:
        df = df[df["period"].astype(str).str.startswith(period)]

    trend_periods: List[str] = []
    rev_series: List[float] = []
    exp_series: List[float] = []
    prof_series: List[float] = []

    if not df.empty and "period" in df.columns:
        for _, row in df.iterrows():
            p_val = str(row.get("period", ""))
            r_val = float(row.get("revenue", 0.0))
            e_val = float(row.get("expense", 0.0))
            trend_periods.append(p_val)
            rev_series.append(r_val)
            exp_series.append(e_val)
            prof_series.append(r_val - e_val)

    # ── Calculate Aggregated KPIs ─────────────────────────────────
    if resolved_dept and resolved_dept in depts:
        d_info = depts[resolved_dept]
        total_rev = d_info["revenue"]
        total_exp = d_info["expense"]
        net_prof = d_info["profit"]
        net_margin = d_info["margin"]
        total_anom = d_info["anomalies_count"]
    elif not df.empty:
        total_rev = sum(rev_series)
        total_exp = sum(exp_series)
        net_prof = total_rev - total_exp
        net_margin = (net_prof / total_rev * 100) if total_rev > 0 else 0.0
        total_anom = ent.get("total_anomalies", 0)
    else:
        total_rev = ent["revenue"]
        total_exp = ent["expense"]
        net_prof = ent["profit"]
        net_margin = ent["margin"]
        total_anom = ent.get("total_anomalies", 0)

    # ── Budget Analysis (Dataset-grounded) ─────────────────────────
    db_budgets = db.query(DepartmentBudget).all()
    has_budget = bool(profile.get("capabilities", {}).get("budget", False)) or (len(db_budgets) > 0)

    total_budget = None
    budget_variance = None
    budget_variance_pct = 0.0
    budget_status = "Budget data unavailable for this dataset"

    if has_budget:
        if resolved_dept:
            b_val = sum(b.budget_amount for b in db_budgets if b.department.lower() == resolved_dept.lower())
            total_budget = b_val if b_val > 0 else None
        else:
            b_val = sum(b.budget_amount for b in db_budgets)
            total_budget = b_val if b_val > 0 else None

        if total_budget and total_budget > 0:
            budget_variance = total_exp - total_budget
            budget_variance_pct = (budget_variance / total_budget * 100)
            budget_status = "On Budget" if budget_variance <= 0 else "Over Budget"

    # ── Department Performance Rows ───────────────────────────────
    dept_rows = []
    for d_name, d_val in sorted(filtered_depts.items(), key=lambda x: x[1]["profit"], reverse=True):
        d_budget = d_val.get("budget", 0.0)
        d_has_budget = has_budget and d_budget > 0
        d_var = (d_val["expense"] - d_budget) if d_has_budget else None
        d_var_pct = ((d_var / d_budget) * 100) if d_has_budget and d_budget > 0 else None
        d_status = "On Budget" if (d_has_budget and d_var <= 0) else ("Over Budget" if d_has_budget else "—")
        
        dept_rows.append({
            "department": d_name,
            "revenue": d_val["revenue"],
            "expense": d_val["expense"],
            "profit": d_val["profit"],
            "margin": d_val["margin"],
            "has_budget": d_has_budget,
            "budget": d_budget if d_has_budget else None,
            "variance": d_var,
            "variance_pct": d_var_pct,
            "status": d_status,
            "anomalies_count": d_val.get("anomalies_count", 0),
            "critical_anomalies": d_val.get("critical_anomalies", 0),
        })

    # Available Periods for dropdown
    all_period_query = me._base_query().with_entities(PLRecord.period).distinct().all()
    years_set = sorted(list({str(p[0])[:4] for p in all_period_query if p[0] and len(str(p[0])) >= 4}))
    periods_list = ["All Periods"] + years_set

    # ── Management Insights ───────────────────────────────────────
    top_profit_dept = dept_rows[0] if dept_rows else {}
    top_rev_dept = max(dept_rows, key=lambda x: x["revenue"]) if dept_rows else {}
    low_margin_dept = min(dept_rows, key=lambda x: x["margin"]) if dept_rows else {}
    
    insights = []
    insights.append(
        f"Total enterprise revenue reached {format_inr(total_rev)} with an aggregate operating margin of {net_margin:.1f}%."
    )
    if top_profit_dept:
        insights.append(
            f"{top_profit_dept.get('department')} is the primary profit anchor, generating {format_inr(top_profit_dept.get('profit', 0))} in net profitability ({top_profit_dept.get('margin', 0):.1f}% margin)."
        )
    if top_rev_dept and top_rev_dept.get("department") != top_profit_dept.get("department"):
        insights.append(
            f"{top_rev_dept.get('department')} drove the highest gross revenue volume at {format_inr(top_rev_dept.get('revenue', 0))}."
        )
    if low_margin_dept and low_margin_dept.get("margin", 100) < net_margin:
        insights.append(
            f"{low_margin_dept.get('department')} operates at the narrowest margin ({low_margin_dept.get('margin', 0):.1f}%), presenting an opportunity for cost rationalization."
        )
    if has_budget and total_budget:
        insights.append(
            f"Budget variance across tracked units stands at {format_inr(abs(budget_variance))} ({abs(budget_variance_pct):.1f}% {'over' if budget_variance > 0 else 'under'} budget)."
        )
    else:
        insights.append(
            "Budget baseline data is not defined for the active dataset; calculations reflect actual historical revenue and spend."
        )
    if ent.get("critical_anomalies", 0) > 0:
        insights.append(
            f"Machine learning surveillance flagged {ent.get('critical_anomalies')} critical ledger outliers requiring audit verification."
        )

    narrative = (
        f"Executive Financial Report for {dataset_name}. The enterprise generated {format_inr(total_rev)} in revenue "
        f"and {format_inr(total_exp)} in expenditures, delivering {format_inr(net_prof)} Net Profit ({net_margin:.2f}% operating margin). "
        f"{top_profit_dept.get('department', 'Top Unit')} leads departmental profitability."
    )

    return {
        "report_type": report_type,
        "title": "Executive Financial Performance & Variance Report",
        "description": "Executive financial performance, profitability and variance analysis across operating units.",
        "dataset_name": dataset_name,
        "generated_at": now_str,
        "active_filters": {
            "dept": dept,
            "period": period,
            "agg": agg,
        },
        "departments_list": departments_list,
        "periods_list": periods_list,
        "kpis": {
            "total_revenue": total_rev,
            "total_expense": total_exp,
            "net_profit": net_prof,
            "net_margin": net_margin,
            "has_budget": has_budget,
            "total_budget": total_budget,
            "budget_variance": budget_variance,
            "budget_variance_pct": budget_variance_pct,
            "budget_status": budget_status,
            "total_anomalies": total_anom,
            "tracked_departments": len(filtered_depts),
        },
        "pnl_trend": {
            "periods": trend_periods,
            "revenue": rev_series,
            "expenses": exp_series,
            "profit": prof_series,
        },
        # Backwards compatible key for trend
        "trend": {
            "periods": trend_periods,
            "revenue": rev_series,
            "expenses": exp_series,
            "profit": prof_series,
        },
        "department_performance": dept_rows,
        "departments": dept_rows,
        "budget_vs_actual": {
            "has_budget": has_budget,
            "message": "Budget data unavailable for this dataset" if not has_budget else "",
            "total_actual": total_exp,
            "total_budget": total_budget,
            "total_variance": budget_variance,
            "total_variance_pct": budget_variance_pct,
            "status": budget_status,
            "departments": dept_rows,
        },
        "financial_summary": dept_rows,
        "management_insights": insights,
        "drivers": insights,
        "narrative_summary": narrative,
    }

@router.get("/csv")
def get_csv_report(
    scope: str = Query("All Departments"),
    db: Session = Depends(get_db)
):
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)
    query = db.query(PLRecord)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    if scope != "All Departments":
        query = query.filter(PLRecord.domain == scope)
    records = query.order_by(PLRecord.period.desc()).limit(1000).all()
    data = [
        {
            "domain": r.domain,
            "period": r.period,
            "line_item": r.line_item,
            "amount": r.amount,
            "currency": r.currency,
        }
        for r in records
    ]

    csv_file = report_service.generate_csv_report(data)
    response = StreamingResponse(iter([csv_file.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=financial_report.csv"
    return response

@router.get("/executive", response_class=HTMLResponse)
def get_executive_report(db: Session = Depends(get_db)):
    from services.copilot_agent import get_rag_context
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)

    ai_summary = get_rag_context(db, "Provide a concise executive summary of our financial performance.")
    
    query = db.query(PLRecord)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    records = query.limit(300).all()
    data = [
        {"domain": r.domain, "period": r.period, "amount": r.amount} for r in records
    ]

    html_content = report_service.generate_html_report(data, ai_summary)
    return HTMLResponse(content=html_content)

@router.get("/pdf")
def get_pdf_report(db: Session = Depends(get_db)):
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)

    query = db.query(PLRecord).order_by(PLRecord.period.desc())
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    records = query.limit(500).all()
    data = [
        {
            "domain": r.domain,
            "period": r.period,
            "line_item": r.line_item,
            "amount": r.amount,
        }
        for r in records
    ]

    from services.copilot_agent import get_rag_context
    ai_summary = get_rag_context(db, "Provide an executive summary of financial performance.")
    recommendations = "1. Optimize OPEX in high spend divisions.\n2. Scale investment in top margin units.\n3. Resolve high severity anomalies."

    pdf_bytes = report_service.generate_pdf_report(data, ai_summary, recommendations)
    response = Response(content=pdf_bytes.getvalue(), media_type="application/pdf")
    response.headers["Content-Disposition"] = "attachment; filename=executive_report.pdf"
    return response

class ReportGenRequest(BaseModel):
    format: str
    type: str = "Executive P&L Report"
    scope: str = "All Departments"
    start_date: str = ""
    end_date: str = ""
    branding: bool = False
    watermark: bool = False
    ai_summary: bool = True
    schedule: bool = False
    email: bool = False

@router.post("/generate")
def generate_report(req: ReportGenRequest, db: Session = Depends(get_db)):
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)

    query = db.query(PLRecord).order_by(PLRecord.period.desc())
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    if req.scope != "All Departments":
        query = query.filter(PLRecord.domain == req.scope)

    records = query.limit(200).all()
    data = [
        {
            "domain": r.domain,
            "period": r.period,
            "line_item": r.line_item,
            "amount": r.amount,
        }
        for r in records
    ]
    
    from services.copilot_agent import get_rag_context
    ai_summary = get_rag_context(db, f"Write a professional summary for {req.type}.") if req.ai_summary else ""
    
    fmt = req.format.lower()
    if fmt == "pdf":
        pdf_bytes = report_service.generate_pdf_report(data, ai_summary)
        response = Response(content=pdf_bytes.getvalue(), media_type="application/pdf")
        response.headers["Content-Disposition"] = "attachment; filename=report.pdf"
        return response
    elif fmt in ["excel", "xlsx"]:
        excel_bytes = report_service.generate_excel_report(data)
        response = Response(content=excel_bytes.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = "attachment; filename=report.xlsx"
        return response
    elif fmt in ["ppt", "pptx"]:
        ppt_bytes = report_service.generate_ppt_report(data, ai_summary)
        response = Response(content=ppt_bytes.getvalue(), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        response.headers["Content-Disposition"] = "attachment; filename=report.pptx"
        return response
    else:
        csv_bytes = report_service.generate_csv_report(data)
        response = StreamingResponse(iter([csv_bytes.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=report.csv"
        return response
