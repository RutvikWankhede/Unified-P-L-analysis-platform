import requests

BASE = "http://127.0.0.1:8000"

print("1. Health:", requests.get(f"{BASE}/api/v1/health/health").status_code if requests.get(f"{BASE}/api/v1/datasets/active").status_code else "ok")

# Login as admin with JSON
resp = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
print("2. Login status:", resp.status_code)
tokens = resp.json()
token = tokens.get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Active dataset
active = requests.get(f"{BASE}/api/v1/datasets/active", headers=headers).json()
print("3. Active dataset:", active)

# Summary
summary = requests.get(f"{BASE}/api/v1/pl/summary", headers=headers).json()
print("4. Summary KPIs:", summary.get("kpis"))

# Charts
charts = requests.get(f"{BASE}/api/v1/pl/charts", headers=headers).json()
print("5. Charts periods:", len(charts.get("periods", [])))
print("   Revenue trend count:", len(charts.get("revenue_trend", [])))

# Anomalies
anomalies = requests.get(f"{BASE}/api/v1/anomalies", headers=headers).json()
print("6. Anomalies count:", len(anomalies) if isinstance(anomalies, list) else anomalies)

# Recommendations
recs = requests.get(f"{BASE}/api/v1/recommendations", headers=headers).json()
print("7. Recommendations count:", len(recs) if isinstance(recs, list) else recs)
