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
    report_type: str = Query("executive", description="executive | department | variance | anomaly | forecast"),
    dept: str = Query("all", description="Department filter or 'all'"),
    period: str = Query("monthly", description="monthly | weekly | quarterly | yearly"),
    db: Session = Depends(get_db)
):
    """
    Produce live, canonical dataset metrics and structured tables for interactive report previews.
    """
    ctx = get_financial_context_and_calc(db)
    ent = ctx["enterprise"]
    depts: Dict[str, Dict[str, Any]] = ctx["departments"]
    dataset_name = ctx["dataset_name"]
    fc = ctx["forecast"]
    summary_df = ctx.get("summary_df")

    now_str = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")

    # Filter departments if specified
    filtered_depts = depts
    if dept and dept != "all" and dept in depts:
        filtered_depts = {dept: depts[dept]}

    # Build trend periods from summary_df or active records
    from services.metric_engine import MetricEngine
    active_id = ctx.get("dataset_id")
    me = MetricEngine(db, active_id)
    agg_dept = None if dept == "all" else dept
    df = me.aggregate_data(period, dept=agg_dept)

    periods: List[str] = []
    rev_series: List[float] = []
    exp_series: List[float] = []
    prof_series: List[float] = []

    if not df.empty and "period" in df.columns:
        for _, row in df.iterrows():
            p_val = str(row.get("period", ""))
            r_val = float(row.get("revenue", 0.0))
            e_val = float(row.get("expense", 0.0))
            periods.append(p_val)
            rev_series.append(r_val)
            exp_series.append(e_val)
            prof_series.append(r_val - e_val)

    # ─────────────────────────────────────────────────────────────
    # 1. EXECUTIVE P&L REPORT
    # ─────────────────────────────────────────────────────────────
    if report_type == "executive":
        dept_rows = sorted(filtered_depts.values(), key=lambda x: x["profit"], reverse=True)
        top_d = dept_rows[0] if dept_rows else {}
        low_d = dept_rows[-1] if dept_rows else {}

        narrative = (
            f"The enterprise generated {format_inr(ent['revenue'])} in total revenue against {format_inr(ent['expense'])} "
            f"in operating expenditures, yielding a Net Profit of {format_inr(ent['profit'])} ({ent['margin']:.2f}% operating margin). "
            f"{top_d.get('department', 'Top unit')} is the leading profitability contributor with {format_inr(top_d.get('profit'))}."
        )

        return {
            "report_type": "executive",
            "title": "Executive P&L Performance Report",
            "description": "Comprehensive top-line, cost structure, and net margin analysis across operating divisions.",
            "dataset_name": dataset_name,
            "generated_at": now_str,
            "kpis": {
                "primary_metric": "Total Revenue",
                "primary_value": ent["revenue"],
                "secondary_metric": "Total Expenses",
                "secondary_value": ent["expense"],
                "net_profit": ent["profit"],
                "operating_margin": ent["margin"],
                "total_anomalies": ent["total_anomalies"],
            },
            "trend": {
                "periods": periods,
                "revenue": rev_series,
                "expenses": exp_series,
                "profit": prof_series,
            },
            "departments": dept_rows,
            "drivers": [
                f"Operating margin across the enterprise averages {ent['margin']:.1f}%.",
                f"Leading profit contributor is {top_d.get('department')} ({format_inr(top_d.get('profit'))}).",
                f"{ent['critical_anomalies']} critical ledger anomalies identified in ML surveillance.",
            ],
            "narrative_summary": narrative,
        }

    # ─────────────────────────────────────────────────────────────
    # 2. DEPARTMENT PERFORMANCE REPORT
    # ─────────────────────────────────────────────────────────────
    elif report_type == "department":
        dept_rows = sorted(filtered_depts.values(), key=lambda x: x["profit"], reverse=True)
        top_prof = dept_rows[0] if dept_rows else {}
        top_rev = max(filtered_depts.values(), key=lambda x: x["revenue"]) if filtered_depts else {}

        narrative = (
            f"Department performance review across {len(filtered_depts)} operating units. "
            f"{top_prof.get('department')} leads all departments with {format_inr(top_prof.get('profit'))} Net Profit ({top_prof.get('margin', 0):.1f}% margin), "
            f"while {top_rev.get('department')} generated the highest gross revenue at {format_inr(top_rev.get('revenue'))}."
        )

        return {
            "report_type": "department",
            "title": "Department Financial Performance & Contribution",
            "description": "Detailed departmental breakdown of revenue, OPEX allocation, net margin, and profitability ranks.",
            "dataset_name": dataset_name,
            "generated_at": now_str,
            "kpis": {
                "tracked_departments": len(filtered_depts),
                "top_performing_dept": top_prof.get("department", "N/A"),
                "top_dept_profit": top_prof.get("profit", 0.0),
                "top_revenue_dept": top_rev.get("department", "N/A"),
                "top_dept_revenue": top_rev.get("revenue", 0.0),
            },
            "trend": {
                "periods": periods,
                "revenue": rev_series,
                "expenses": exp_series,
                "profit": prof_series,
            },
            "departments": dept_rows,
            "drivers": [
                f"{top_prof.get('department')} delivers the highest profit margin in the enterprise.",
                f"Revenue distribution is diversified across {len(filtered_depts)} operating units.",
                f"Margin spread ranges from {min((d['margin'] for d in dept_rows), default=0):.1f}% to {max((d['margin'] for d in dept_rows), default=0):.1f}%.",
            ],
            "narrative_summary": narrative,
        }

    # ─────────────────────────────────────────────────────────────
    # 3. VARIANCE REPORT (BUDGET VS ACTUAL)
    # ─────────────────────────────────────────────────────────────
    elif report_type == "variance":
        dept_rows = sorted(filtered_depts.values(), key=lambda x: x["variance"], reverse=True)
        over_budget = [d for d in dept_rows if d["budget"] > 0 and d["variance"] > 0]
        tot_budget = sum(d["budget"] for d in dept_rows)
        tot_spend = sum(d["expense"] for d in dept_rows)
        net_variance = tot_spend - tot_budget
        net_var_pct = (net_variance / tot_budget * 100) if tot_budget > 0 else 0.0

        narrative = (
            f"Budget variance audit reflects {len(over_budget)} departments currently operating over budget. "
            f"Total actual expenditure of {format_inr(tot_spend)} compares against an allocated budget baseline of {format_inr(tot_budget)} "
            f"({abs(net_var_pct):.1f}% {'over' if net_variance > 0 else 'under'} budget)."
        )

        return {
            "report_type": "variance",
            "title": "Budget vs. Actual Variance Audit Report",
            "description": "Comparative analysis of departmental spend against allocated budget targets with variance percentages.",
            "dataset_name": dataset_name,
            "generated_at": now_str,
            "kpis": {
                "total_budget": tot_budget,
                "total_actual_spend": tot_spend,
                "net_variance": net_variance,
                "variance_percentage": net_var_pct,
                "over_budget_count": len(over_budget),
            },
            "trend": {
                "periods": periods,
                "expenses": exp_series,
            },
            "departments": dept_rows,
            "drivers": [
                f"{len(over_budget)} departments require budgetary remediation or target realignment." if over_budget else "All departments operating within allocated targets.",
                f"Highest cost department is {dept_rows[0].get('department') if dept_rows else 'N/A'}.",
            ],
            "narrative_summary": narrative,
        }

    # ─────────────────────────────────────────────────────────────
    # 4. ANOMALY & RISK REPORT
    # ─────────────────────────────────────────────────────────────
    elif report_type == "anomaly":
        dept_rows = sorted(filtered_depts.values(), key=lambda x: x["anomalies_count"], reverse=True)
        top_risk = dept_rows[0] if dept_rows else {}

        narrative = (
            f"Automated risk surveillance detected {ent['total_anomalies']} ledger anomalies across active records, "
            f"including {ent['critical_anomalies']} critical and {ent['high_anomalies']} high-severity outliers. "
            f"{top_risk.get('department')} exhibits the highest concentration with {top_risk.get('anomalies_count')} flagged items."
        )

        return {
            "report_type": "anomaly",
            "title": "Machine Learning Anomaly & Audit Risk Report",
            "description": "Risk distribution, severity breakdown, and department vulnerability assessment from ML surveillance.",
            "dataset_name": dataset_name,
            "generated_at": now_str,
            "kpis": {
                "total_anomalies": ent["total_anomalies"],
                "critical_count": ent["critical_anomalies"],
                "high_count": ent["high_anomalies"],
                "medium_count": ent["medium_anomalies"],
                "low_count": ent["low_anomalies"],
            },
            "trend": {
                "periods": periods,
            },
            "departments": dept_rows,
            "drivers": [
                f"{top_risk.get('department')} has the highest anomaly exposure ({top_risk.get('anomalies_count')} outliers).",
                f"{ent['critical_anomalies']} critical severity entries require immediate financial controller verification.",
            ],
            "narrative_summary": narrative,
        }

    # ─────────────────────────────────────────────────────────────
    # 5. FORECAST & PREDICTIVE TRAJECTORY REPORT
    # ─────────────────────────────────────────────────────────────
    else:
        dept_rows = sorted(filtered_depts.values(), key=lambda x: x["profit"], reverse=True)
        exp_case = fc.get("expected_case", ent["profit"]) if fc else ent["profit"]
        best_case = fc.get("best_case", exp_case * 1.15) if fc else exp_case * 1.15
        worst_case = fc.get("worst_case", exp_case * 0.85) if fc else exp_case * 0.85
        conf_score = (fc.get("confidence_score", 0.95) * 100) if fc else 95.0
        trend_dir = fc.get("trend_direction", "stable") if fc else "stable"

        narrative = (
            f"Predictive modeling projects an expected net profit trajectory of {format_inr(exp_case)} over the forward 12-period horizon "
            f"(Confidence: {conf_score:.1f}%, Trend: {trend_dir.capitalize()}). Multi-scenario projections range between {format_inr(worst_case)} (downside) "
            f"and {format_inr(best_case)} (optimistic upside)."
        )

        return {
            "report_type": "forecast",
            "title": "Predictive Forecast & Horizon Trajectory Report",
            "description": "Statistical time-series forecasting, confidence intervals, and sensitivity scenarios.",
            "dataset_name": dataset_name,
            "generated_at": now_str,
            "kpis": {
                "expected_profit": exp_case,
                "best_case_profit": best_case,
                "worst_case_profit": worst_case,
                "confidence_score": conf_score,
                "trend_direction": trend_dir,
            },
            "trend": {
                "periods": periods,
                "actual": prof_series,
                "forecast": [exp_case / len(periods) if periods else 0] * len(periods),
            },
            "departments": dept_rows,
            "drivers": [
                f"Prediction model: {fc.get('model_used', 'Linear Regression (OLS)') if fc else 'Linear Regression'}.",
                f"Historical baseline indicates {format_inr(ent['profit'])} Net Profit with {ent['margin']:.1f}% margin.",
            ],
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
