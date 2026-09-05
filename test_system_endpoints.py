import sys
import os
import json

# Add backend directory to sys.path
backend_dir = os.path.abspath(r"unified-pl-system\backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models.pl_record import PLRecord
from models.anomaly import Anomaly
from models.user import User
from routers.auth_router import create_access_token

client = TestClient(app)

print("=== 1. VERIFYING DATABASE RECORDS ===")
db = SessionLocal()
record_count = db.query(PLRecord).count()
anomaly_count = db.query(Anomaly).count()
high_anomalies = db.query(Anomaly).filter(Anomaly.severity == "High").count()
print(f"Total PL Records: {record_count} (Expected: 1800)")
print(f"Total Anomalies: {anomaly_count} (Expected: 95)")
print(f"High Severity Anomalies: {high_anomalies} (Expected: 5)")

print("\n=== 2. GENERATING AUTH TOKEN ===")
admin = db.query(User).filter(User.username == "admin").first()
token = create_access_token(data={"sub": admin.username, "role": admin.role, "user_id": admin.id})
headers = {"Authorization": f"Bearer {token}"}
print("Auth token created.")

print("\n=== 3. TESTING /api/v1/pl/kpis ===")
res_kpis = client.get("/api/v1/pl/kpis", headers=headers)
print(f"Status: {res_kpis.status_code}")
kpis = res_kpis.json()
print("KPI Response:", json.dumps(kpis, indent=2))

tot_rev = kpis.get("total_revenue", 0)
tot_exp = kpis.get("total_expenses", 0)
net_prof = kpis.get("net_profit", 0)

print(f"\nCalculated KPI Values:")
print(f"Total Revenue: ₹{tot_rev:,.2f}  -->  ₹{tot_rev/1e7:.2f} Cr (Target: ₹27.80 Cr / ₹277,988,276.87)")
print(f"Total Expense: ₹{tot_exp:,.2f}  -->  ₹{tot_exp/1e7:.2f} Cr (Target: ₹19.81 Cr / ₹198,066,136.85)")
print(f"Net Profit:    ₹{net_prof:,.2f}  -->  ₹{net_prof/1e7:.2f} Cr (Target: ₹7.99 Cr / ₹79,922,140.02)")

print("\n=== 4. TESTING /api/v1/pl/summary ===")
res_summary = client.get("/api/v1/pl/summary", headers=headers)
print(f"Status: {res_summary.status_code}")
summary = res_summary.json()
print("Summary Response:", json.dumps(summary, indent=2))

print("\n=== 5. TESTING /api/v1/pl/departments ===")
res_depts = client.get("/api/v1/pl/departments", headers=headers)
print(f"Status: {res_depts.status_code}")
depts = res_depts.json()
print(f"Departments Count: {len(depts)} (Expected: 12)")
print("Department names:", [d.get("department", d.get("domain", d.get("name"))) for d in depts] if isinstance(depts, list) else depts)

print("\n=== 6. TESTING /api/v1/anomalies ===")
res_anom = client.get("/api/v1/anomalies", headers=headers)
print(f"Status: {res_anom.status_code}")
anoms = res_anom.json()
if isinstance(anoms, list):
    print(f"Anomalies returned: {len(anoms)}")
elif isinstance(anoms, dict):
    print(f"Anomalies returned: {len(anoms.get('items', anoms.get('anomalies', [])))}")

print("\n=== 7. TESTING /api/v1/datasets/active ===")
res_active = client.get("/api/v1/datasets/active", headers=headers)
print(f"Status: {res_active.status_code}")
print("Active Dataset:", res_active.json())

db.close()
