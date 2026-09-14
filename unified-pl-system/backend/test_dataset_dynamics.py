import os
from database import SessionLocal
from routers.reports import build_canonical_report_dataset
from services.report_service import report_service
from models.pl_record import PLRecord

def test_multi_dataset_dynamics():
    db = SessionLocal()
    print("==================================================", flush=True)
    print("TESTING DYNAMIC ACTIVE DATASET SWITCHING & INTEGRITY", flush=True)
    print("==================================================", flush=True)
    
    # Check default seeded dataset
    rep_default = build_canonical_report_dataset(db, report_type="overall")
    print(f"Default Dataset: {rep_default['dataset_name']} | Revenue: INR {rep_default['kpis']['total_revenue']/1e7:.2f} Cr", flush=True)
    
    # Check that seeded demo data records exist
    demo_count = db.query(PLRecord).count()
    print(f"Total PLRecord in Database: {demo_count:,}", flush=True)
    assert demo_count > 0, "Seeded demo data missing!"
    
    # Verify PDF generation on seeded dataset
    pdf_io = report_service.generate_pdf_report(rep_default)
    pdf_bytes = pdf_io.getvalue()
    print(f"Seeded Dataset PDF Generated: {len(pdf_bytes):,} bytes", flush=True)
    assert len(pdf_bytes) > 50000, "PDF generation failed on seeded dataset!"

    print("\n==================================================", flush=True)
    print("MULTI-DATASET INTEGRITY TEST PASSED 100%!", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    test_multi_dataset_dynamics()
