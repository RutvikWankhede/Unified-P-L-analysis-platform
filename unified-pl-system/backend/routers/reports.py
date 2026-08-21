from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.pl_record import PLRecord
from services.report_service import report_service

router = APIRouter()


@router.get("/csv")
def get_csv_report(db: Session = Depends(get_db)):
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)
    query = db.query(PLRecord)
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

    csv_file = report_service.generate_csv_report(data)
    response = StreamingResponse(iter([csv_file.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=pl_report.csv"
    return response


@router.get("/executive", response_class=HTMLResponse)
def get_executive_report(db: Session = Depends(get_db)):
    from services.copilot_agent import get_rag_context
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)

    ai_summary = get_rag_context(db, "Write a 2-3 sentence executive summary of our financial performance. Do not include recommendations.")
    
    query = db.query(PLRecord)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    records = query.limit(200).all()
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

    total_rev = sum(r["amount"] for r in data if r["amount"] > 0)
    total_exp = sum(abs(r["amount"]) for r in data if r["amount"] < 0)
    net_profit = total_rev - total_exp
    margin = (net_profit / total_rev * 100) if total_rev > 0 else 0

    from services.copilot_agent import get_rag_context
    
    ai_summary = get_rag_context(db, "Write a professional 3-sentence executive summary of the overall financial performance, highlighting total revenue, expenses, and margins.")
    recommendations = get_rag_context(db, "Based on the financial performance, generate 3 specific numbered actionable recommendations. Just output the numbered list.")

    pdf_bytes = report_service.generate_pdf_report(data, ai_summary, recommendations)
    response = Response(content=pdf_bytes.getvalue(), media_type="application/pdf")
    response.headers["Content-Disposition"] = (
        "attachment; filename=executive_report.pdf"
    )
    return response

from pydantic import BaseModel
class ReportGenRequest(BaseModel):
    format: str
    type: str = "Full/Combined Report"
    scope: str = "All Departments"
    start_date: str = ""
    end_date: str = ""
    branding: bool = False
    watermark: bool = False
    ai_summary: bool = False
    schedule: bool = False
    email: bool = False

@router.post("/generate")
def generate_report(req: ReportGenRequest, db: Session = Depends(get_db)):
    from routers.datasets_router import get_active_dataset_id
    active_id = get_active_dataset_id(db)

    query = db.query(PLRecord).order_by(PLRecord.period.desc())
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)
    records = query.limit(100).all()
    data = [
        {
            "domain": r.domain,
            "period": r.period,
            "line_item": r.line_item,
            "amount": r.amount,
        }
        for r in records
    ]
    
    if req.ai_summary:
        from services.copilot_agent import get_rag_context
        ai_summary = get_rag_context(db, "Write a 2-3 sentence executive summary of our financial performance. Do not include recommendations.")
    else:
        ai_summary = ""
    
    if req.format == "pdf":
        pdf_bytes = report_service.generate_pdf_report(data, ai_summary)
        response = Response(content=pdf_bytes.getvalue(), media_type="application/pdf")
        response.headers["Content-Disposition"] = "attachment; filename=report.pdf"
        return response
    elif req.format == "excel":
        excel_bytes = report_service.generate_excel_report(data)
        response = Response(content=excel_bytes.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = "attachment; filename=report.xlsx"
        return response
    elif req.format == "ppt":
        ppt_bytes = report_service.generate_ppt_report(data, ai_summary)
        response = Response(content=ppt_bytes.getvalue(), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        response.headers["Content-Disposition"] = "attachment; filename=report.pptx"
        return response
    elif req.format == "csv":
        csv_bytes = report_service.generate_csv_report(data)
        response = StreamingResponse(iter([csv_bytes.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=report.csv"
        return response
    else:
        return {"error": "Unsupported format"}
