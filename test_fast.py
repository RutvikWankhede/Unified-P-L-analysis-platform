import sys
import os
import json

os.environ["PYTEST_CURRENT_TEST"] = "1"

backend_dir = os.path.abspath(r"unified-pl-system\backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

out_file = open(r"..\..\test_endpoints_out.txt", "w", encoding="utf-8")
def log(msg):
    out_file.write(str(msg) + "\n")
    out_file.flush()

log("=== 1. VERIFYING DATABASE RECORDS ===")
from database import SessionLocal
from models.pl_record import PLRecord
from models.anomaly import Anomaly
from models.user import User
from routers.auth_router import create_access_token

db = SessionLocal()
record_count = db.query(PLRecord).count()
anomaly_count = db.query(Anomaly).count()
high_anomalies = db.query(Anomaly).filter(Anomaly.severity == "High").count()
log(f"Total PL Records: {record_count} (Expected: 1800)")
log(f"Total Anomalies: {anomaly_count} (Expected: 95)")
log(f"High Severity Anomalies: {high_anomalies} (Expected: 5)")

log("\n=== 2. GENERATING AUTH TOKEN ===")
admin = db.query(User).filter(User.username == "admin").first()
token = create_access_token(data={"sub": admin.username, "role": admin.role, "user_id": admin.id})
headers = {"Authorization": f"Bearer {token}"}
log("Auth token created.")

log("\n=== 3. TESTING /api/v1/pl/kpis ===")
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

res_kpis = client.get("/api/v1/pl/kpis", headers=headers)
log(f"Status: {res_kpis.status_code}")
kpis = res_kpis.json()
log("KPI Response: " + json.dumps(kpis, indent=2))

tot_rev = kpis.get("total_revenue", 0)
tot_exp = kpis.get("total_expenses", 0)
net_prof = kpis.get("net_profit", 0)

log(f"\nCalculated KPI Values:")
log(f"Total Revenue: ₹{tot_rev:,.2f}  -->  ₹{tot_rev/1e7:.2f} Cr (Target: ₹27.80 Cr / ₹277,988,276.87)")
log(f"Total Expense: ₹{tot_exp:,.2f}  -->  ₹{tot_exp/1e7:.2f} Cr (Target: ₹19.81 Cr / ₹198,066,136.85)")
log(f"Net Profit:    ₹{net_prof:,.2f}  -->  ₹{net_prof/1e7:.2f} Cr (Target: ₹7.99 Cr / ₹79,922,140.02)")

log("\n=== 4. TESTING /api/v1/pl/departments ===")
res_depts = client.get("/api/v1/pl/departments", headers=headers)
log(f"Status: {res_depts.status_code}")
depts = res_depts.json()
log(f"Departments Count: {len(depts)} (Expected: 12)")
dept_names = [d.get("department", d.get("domain", d.get("name"))) for d in depts] if isinstance(depts, list) else depts
log(f"Department names: {dept_names}")

log("\n=== 5. TESTING /api/v1/anomalies ===")
res_anom = client.get("/api/v1/anomalies", headers=headers)
log(f"Status: {res_anom.status_code}")
anoms = res_anom.json()
if isinstance(anoms, list):
    log(f"Anomalies returned: {len(anoms)}")
elif isinstance(anoms, dict):
    items = anoms.get('items', anoms.get('anomalies', []))
    log(f"Anomalies returned: {len(items)}")

log("\n=== 6. TESTING /api/v1/datasets/active ===")
res_active = client.get("/api/v1/datasets/active", headers=headers)
log(f"Status: {res_active.status_code}")
log("Active Dataset: " + json.dumps(res_active.json(), indent=2))

db.close()
out_file.close()
log("Done!")
