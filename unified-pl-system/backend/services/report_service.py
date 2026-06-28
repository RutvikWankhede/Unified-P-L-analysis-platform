import csv
import io
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReportService:
    """
    Generates PDF, CSV, Excel, and Interactive HTML reports.
    """

    def generate_csv_report(self, data: List[Dict[str, Any]]) -> io.StringIO:
        logger.info("Generating CSV Report")
        output = io.StringIO()
        if not data:
            return output

        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        output.seek(0)
        return output

    def generate_html_report(self, data: List[Dict[str, Any]], ai_summary: str) -> str:
        logger.info("Generating Interactive HTML Report")

        # In a real enterprise app, we'd use Jinja2 to render a beautiful HTML template
        # with Chart.js or Recharts embedded.
        html = """
        <html>
        <head>
            <title>Executive P&L Report</title>
            <style>
                body { font-family: sans-serif; padding: 40px; background: #f9fafb; }
                h1 { color: #111827; }
                .summary { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <h1>Executive P&L Intelligence Report</h1>
            <div class="summary">
                <h3>AI Summary</h3>
                <p>{ai_summary}</p>
            </div>
            <!-- Data table would go here -->
        </body>
        </html>
        """.replace("{ai_summary}", ai_summary)
        return html

    def generate_pdf_report(
        self, data: List[Dict[str, Any]], ai_summary: str
    ) -> io.BytesIO:
        logger.info("Generating PDF Report")
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(
            0,
            10,
            "Executive P&L Intelligence Report",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )

        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 10, f"AI Summary:\n{ai_summary}")

        if data:
            pdf.set_font("Helvetica", "B", 10)
            headers = list(data[0].keys())
            for header in headers:
                pdf.cell(40, 10, str(header), border=1)
            pdf.ln()

            pdf.set_font("Helvetica", "", 10)
            for row in data:
                for header in headers:
                    pdf.cell(40, 10, str(row[header])[:20], border=1)
                pdf.ln()

        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        return output


report_service = ReportService()
