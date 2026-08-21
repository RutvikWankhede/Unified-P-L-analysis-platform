import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from services.pl_service import analyze_upload

db = SessionLocal()
try:
    csv_content = (
        b"\n\n"
        b"Posting Date;Dept;Sales;Spend\n"
        b"2026-05-12;Retail; 12.500,50; (4.200,00)\n"
        b"\n"
    )
    res = analyze_upload(csv_content, "messy.csv", db, 1)
    print("SUCCESS:", res)
except Exception:
    import traceback

    print("FAILED EXCEPTION:")
    traceback.print_exc()
finally:
    db.close()
