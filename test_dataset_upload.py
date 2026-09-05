import requests
import io
import time
import pandas as pd
import datetime

BASE = "http://127.0.0.1:8000"

# Wait for server readiness
print("Connecting to backend on port 8000...")
token = None
for _ in range(15):
    try:
        resp = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "admin123"}, timeout=5)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            print("Login success! Token acquired.")
            break
    except Exception as e:
        time.sleep(1)

if not token:
    raise RuntimeError("Could not connect to backend after 15 seconds")

headers = {"Authorization": f"Bearer {token}"}

# 2. Create alternate dataset with non-standard column names
dates = pd.date_range("2025-01-01", periods=12, freq="ME").strftime("%Y-%m-%d").tolist()
data = []
depts = ["Sales Unit", "Tech Dept", "Ops Division", "HR Branch"]

for d in dates:
    for dept in depts:
        data.append({
            "Transaction Date": d,
            "Dept": dept,
            "Sales": round(5000000 + (len(data) * 150000), 2),
            "Cost": round(3200000 + (len(data) * 80000), 2),
            "Gain": round(1800000 + (len(data) * 70000), 2),
            "Collections": round(4800000 + (len(data) * 120000), 2),
            "Payments": round(3100000 + (len(data) * 75000), 2),
            "Target": round(3500000 + (len(data) * 85000), 2),
        })

df = pd.DataFrame(data)
csv_buf = io.StringIO()
df.to_csv(csv_buf, index=False)
csv_bytes = csv_buf.getvalue().encode("utf-8")

print(f"Uploading alternate dataset with {len(df)} records and custom column synonyms...")
files = {"file": ("q3_custom_financials.csv", csv_bytes, "text/csv")}
upload_resp = requests.post(f"{BASE}/api/v1/datasets/upload", headers=headers, files=files)
print("Upload status:", upload_resp.status_code)
upload_json = upload_resp.json()
print("Upload response summary:", upload_json.get("message") or upload_json)

# Check active dataset
active_resp = requests.get(f"{BASE}/api/v1/datasets/active", headers=headers).json()
print("Active dataset:", active_resp)

# Check Summary with new dataset
new_summary = requests.get(f"{BASE}/api/v1/pl/summary", headers=headers).json()
print("New Summary KPIs:", new_summary.get("kpis"))

# Check Dept Performance with new dataset
new_perf = requests.get(f"{BASE}/api/v1/pl/department-performance?metric=profit&limit=all", headers=headers).json()
print("New Depts detected:", new_perf.get("departments"))
print("New Dept Values (Profit):", new_perf.get("values"))

# Check Cash Flow with new dataset
new_cf = requests.get(f"{BASE}/api/v1/pl/cash-flow-trend", headers=headers).json()
print("New Cash Flow periods:", len(new_cf.get("periods", [])))
print("First Cash Flow item:", new_cf.get("inflow", [])[0] if new_cf.get("inflow") else None)

print("\n--- ALL DATASET TESTS PASSED ---")
