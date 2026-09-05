import requests

BASE = "http://127.0.0.1:8000"

resp = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
token = resp.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

print("1. Anomaly Overview:", requests.get(f"{BASE}/api/v1/pl/anomaly-overview?period=month&dept=all", headers=headers).json())
print("2. Dept Performance (Profit Top 5):", requests.get(f"{BASE}/api/v1/pl/department-performance?metric=profit&limit=top5", headers=headers).json())
print("3. Dept Performance (Revenue All):", requests.get(f"{BASE}/api/v1/pl/department-performance?metric=revenue&limit=all", headers=headers).json())
print("4. Forecast vs Actual (Monthly):", requests.get(f"{BASE}/api/v1/pl/forecast-vs-actual?period=monthly&dept=all", headers=headers).json()["periods"][:5])
print("5. Cash Flow Trend (Monthly):", requests.get(f"{BASE}/api/v1/pl/cash-flow-trend?period=monthly&dept=all", headers=headers).json()["periods"][:5])
print("6. Budget vs Actual:", len(requests.get(f"{BASE}/api/v1/pl/budget-vs-actual?dept=all", headers=headers).json()["items"]))
print("7. Dynamic Insights:", len(requests.get(f"{BASE}/api/v1/pl/insights", headers=headers).json()["insights"]))
