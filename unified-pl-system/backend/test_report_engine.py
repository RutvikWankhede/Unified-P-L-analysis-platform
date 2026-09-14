import os
import sys
from database import SessionLocal
from routers.reports import build_canonical_report_dataset
from services.report_service import report_service

def test_report_generation():
    db = SessionLocal()
    report_types = ["overall", "department", "anomaly", "forecast", "budget", "whatif", "executive"]
    
    output_dir = "test_reports_output"
    os.makedirs(output_dir, exist_ok=True)
    
    print("==================================================", flush=True)
    print("TESTING CANONICAL REPORT DATASET & RECONCILIATION", flush=True)
    print("==================================================", flush=True)
    
    for r_type in report_types:
        print(f"\n--- Testing Report Type: {r_type} ---", flush=True)
        data = build_canonical_report_dataset(db, report_type=r_type, dept="all", period="all", agg="monthly")
        
        kpis = data.get("kpis", {})
        total_rev = kpis.get("total_revenue", 0.0)
        total_exp = kpis.get("total_expense", 0.0)
        net_prof = kpis.get("net_profit", 0.0)
        dept_rows = data.get("department_performance", [])
        
        sum_dept_rev = sum(d["revenue"] for d in dept_rows)
        sum_dept_exp = sum(d["expense"] for d in dept_rows)
        sum_dept_prof = sum(d["profit"] for d in dept_rows)
        
        print(f"Enterprise Revenue: {total_rev:,.2f} | Sum Dept Rev: {sum_dept_rev:,.2f} | Diff: {abs(total_rev - sum_dept_rev):.2f}", flush=True)
        print(f"Enterprise Expense: {total_exp:,.2f} | Sum Dept Exp: {sum_dept_exp:,.2f} | Diff: {abs(total_exp - sum_dept_exp):.2f}", flush=True)
        print(f"Enterprise Profit:  {net_prof:,.2f} | Sum Dept Prof: {sum_dept_prof:,.2f} | Diff: {abs(net_prof - sum_dept_prof):.2f}", flush=True)
        
        assert abs(total_rev - sum_dept_rev) < 1.0, "Revenue reconciliation failed!"
        assert abs(total_exp - sum_dept_exp) < 1.0, "Expense reconciliation failed!"
        assert abs(net_prof - (total_rev - total_exp)) < 1.0, "Profit reconciliation failed!"
        
        # Test PDF Generation
        print("Generating PDF...", flush=True)
        pdf_io = report_service.generate_pdf_report(data)
        pdf_bytes = pdf_io.getvalue()
        pdf_path = os.path.join(output_dir, f"report_{r_type}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"PDF Generated successfully: {pdf_path} ({len(pdf_bytes):,} bytes)", flush=True)
        assert len(pdf_bytes) > 20000, "PDF size too small!"
        
        # Test Excel Generation
        excel_io = report_service.generate_excel_report(data)
        excel_bytes = excel_io.getvalue()
        excel_path = os.path.join(output_dir, f"report_{r_type}.xlsx")
        with open(excel_path, "wb") as f:
            f.write(excel_bytes)
        print(f"Excel Generated successfully: {excel_path} ({len(excel_bytes):,} bytes)", flush=True)

    print("\n==================================================", flush=True)
    print("ALL 7 REPORT TYPES GENERATED & VALIDATED 100% OK!", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    test_report_generation()
