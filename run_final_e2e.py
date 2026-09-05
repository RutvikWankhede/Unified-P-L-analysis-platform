import os
import sys
import json
import sqlite3
import pandas as pd

os.environ["PYTEST_CURRENT_TEST"] = "1"

backend_dir = os.path.abspath(r"unified-pl-system\backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

report_file = open(r"..\..\FINAL_DATASET_RESTORATION_REPORT.json", "w", encoding="utf-8")

# 1. Inspect CSV & Excel files
csv_path = os.path.abspath(r"..\unified_pnl_enterprise_demo.csv")
df_csv = pd.read_csv(csv_path)

rev_csv = float(df_csv["Revenue"].sum())
exp_csv = float(df_csv["Expense"].sum())
prof_csv = float(df_csv["Profit"].sum())
calc_prof_csv = rev_csv - exp_csv

depts_csv = sorted(df_csv["Department"].unique().tolist())
date_min_csv = str(df_csv["Date"].min())
date_max_csv = str(df_csv["Date"].max())

# 2. Database checks
from database import SessionLocal
from models.pl_record import PLRecord
from models.anomaly import Anomaly
from models.uploaded_file import UploadedFile
from models.user import User
from routers.auth_router import create_access_token
from fastapi.testclient import TestClient
from main import app

db = SessionLocal()
record_count = db.query(PLRecord).count()
distinct_uploads = [u[0] for u in db.query(PLRecord.upload_id).distinct().all()]
anomaly_count = db.query(Anomaly).count()
high_anomalies = db.query(Anomaly).filter(Anomaly.severity.in_(["High", "Critical"])).count()
medium_anomalies = db.query(Anomaly).filter(Anomaly.severity == "Medium").count()
low_anomalies = db.query(Anomaly).filter(Anomaly.severity == "Low").count()

admin = db.query(User).filter(User.username == "admin").first()
token = create_access_token(data={"sub": admin.username, "role": admin.role, "user_id": admin.id})
headers = {"Authorization": f"Bearer {token}"}

client = TestClient(app)

# API Summary
res_summary = client.get("/api/v1/pl/summary", headers=headers).json()
kpis = res_summary.get("kpis", {})

# API Departments
res_depts = client.get("/api/v1/pl/departments/summary", headers=headers).json().get("departments", [])

# API Anomalies
res_anom = client.get("/api/v1/anomalies", headers=headers).json()
anom_total = len(res_anom) if isinstance(res_anom, list) else len(res_anom.get("items", []))

# API Active Dataset
res_active = client.get("/api/v1/datasets/active", headers=headers).json()

db.close()

result = {
    "canonical_dataset_file": csv_path,
    "dataset_file_rows": len(df_csv),
    "dataset_file_columns": list(df_csv.columns),
    "date_range": {
        "min": date_min_csv,
        "max": date_max_csv
    },
    "departments": {
        "count": len(depts_csv),
        "list": depts_csv
    },
    "database": {
        "active_upload_id": distinct_uploads[0] if distinct_uploads else None,
        "total_pl_records": record_count,
        "total_anomalies": anomaly_count,
        "anomaly_severity_breakdown": {
            "High": high_anomalies,
            "Medium": medium_anomalies,
            "Low": low_anomalies
        }
    },
    "kpi_baseline": {
        "total_revenue": {
            "exact": kpis.get("revenue"),
            "formatted": f"₹{kpis.get('revenue', 0)/1e7:.2f} Cr",
            "target": "₹27.80 Cr (₹277,988,276.87)"
        },
        "total_expense": {
            "exact": kpis.get("expense"),
            "formatted": f"₹{kpis.get('expense', 0)/1e7:.2f} Cr",
            "target": "₹19.81 Cr (₹198,066,136.85)"
        },
        "net_profit": {
            "exact": kpis.get("profit"),
            "formatted": f"₹{kpis.get('profit', 0)/1e7:.2f} Cr",
            "target": "₹7.99 Cr (₹79,922,140.02)",
            "formula_check": f"{kpis.get('revenue')} - {kpis.get('expense')} = {round(kpis.get('revenue', 0) - kpis.get('expense', 0), 2)}"
        },
        "profit_margin_pct": kpis.get("profit_margin"),
        "health_score": kpis.get("health_score"),
        "risk_score": kpis.get("risk_score")
    },
    "api_active_dataset": res_active,
    "departments_summary_sample": res_depts[:3]
}

json.dump(result, report_file, indent=2)
report_file.close()

print(json.dumps(result, indent=2))
