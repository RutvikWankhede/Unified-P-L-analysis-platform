from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.pl_record import PLRecord
from services.report_service import report_service

router = APIRouter()


@router.get("/csv")
def get_csv_report(db: Session = Depends(get_db)):
    records = db.query(PLRecord).limit(100).all()
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
    ai_summary = "AI analysis indicates stable operating expenses with potential anomalies in Q2."
    records = db.query(PLRecord).limit(50).all()
    data = [
        {"domain": r.domain, "period": r.period, "amount": r.amount} for r in records
    ]

    html_content = report_service.generate_html_report(data, ai_summary)
    return HTMLResponse(content=html_content)


@router.get("/pdf")
def get_pdf_report(db: Session = Depends(get_db)):
    ai_summary = "AI analysis indicates stable operating expenses with potential anomalies in Q2."
    records = db.query(PLRecord).limit(50).all()
    data = [
        {"domain": r.domain, "period": r.period, "amount": r.amount} for r in records
    ]

    pdf_bytes = report_service.generate_pdf_report(data, ai_summary)
    response = Response(content=pdf_bytes.getvalue(), media_type="application/pdf")
    response.headers["Content-Disposition"] = (
        "attachment; filename=executive_report.pdf"
    )
    return response
