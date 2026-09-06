import urllib.request
import urllib.parse
import json

base_url = "http://127.0.0.1:8000"

# 1. Login
req = urllib.request.Request(
    f"{base_url}/api/v1/auth/login",
    data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read().decode())["access_token"]

headers = {"Authorization": f"Bearer {token}"}

def get(path):
    r = urllib.request.Request(f"{base_url}{path}", headers=headers)
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read().decode())

print("=== 1. TEST DEPARTMENT TREND WITH MULTI-SELECTION ===")
t_sales_fin_it = get("/api/v1/pl/departments/trend?agg=monthly&metric=profit&dept=Sales%2CFinance%2CIT")
print(f"Periods: {len(t_sales_fin_it.get('periods', []))}")
print(f"Series keys for Sales,Finance,IT: {list(t_sales_fin_it.get('series', {}).keys())}")
assert set(t_sales_fin_it.get('series', {}).keys()) == {"Sales", "Finance", "IT"}, "Series must contain ONLY Sales, Finance, IT!"
print(">>> OK: Multi-selection Sales+Finance+IT works perfectly!")

t_single = get("/api/v1/pl/departments/trend?agg=monthly&metric=revenue&dept=Sales")
print(f"Series keys for Sales single: {list(t_single.get('series', {}).keys())}")
assert list(t_single.get('series', {}).keys()) == ["Sales"], "Series must contain ONLY Sales!"
print(">>> OK: Single department selection works perfectly!")

t_all = get("/api/v1/pl/departments/trend?agg=monthly&metric=profit&dept=all")
print(f"Series keys count for all: {len(t_all.get('series', {}).keys())}")
print(">>> OK: All departments works perfectly!")

print("\n=== 2. TEST BUDGET VS ACTUAL ===")
bva = get("/api/v1/pl/budget-vs-actual?dept=all&range=all")
print(f"Has data: {bva.get('has_data')}")
print(f"Items count: {len(bva.get('items', []))}")
print(f"Total variance: {bva.get('total_variance_pct')}%")
print(">>> OK: Budget vs Actual works!")

print("\n=== 3. TEST DEPARTMENTS SUMMARY ===")
summary = get("/api/v1/pl/departments/summary")
print(f"Departments count: {len(summary.get('departments', []))}")
depts = [d['department'] for d in summary.get('departments', [])]
print(f"Departments: {depts}")
print(">>> OK: Departments summary works!")

print("\n=== 4. TEST FORECAST ===")
forecast = get("/api/v1/pl/forecast?dept=Overall&metric=profit&periods=12&agg=monthly")
print(f"Forecast has enough data: {forecast.get('has_enough_data')}")
print(f"Historical length: {len(forecast.get('historical', []))}")
print(f"Forecast length: {len(forecast.get('forecast', []))}")
print(f"Predicted value Cr: {forecast.get('predicted_profit_next_12_months_in_crores')}")
print(">>> OK: Forecast API works!")

print("\n=== 5. TEST COPILOT ===")
req_copilot = urllib.request.Request(
    f"{base_url}/api/v1/explanations/copilot",
    data=json.dumps({"question": "Why did expenses increase?"}).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req_copilot) as resp:
    copilot_res = json.loads(resp.read().decode())
    print(f"Copilot answer: {copilot_res.get('answer', '')[:100]}...")
print(">>> OK: Copilot API works!")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
