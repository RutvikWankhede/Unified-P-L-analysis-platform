import urllib.request
import urllib.parse
import json

base_url = "http://127.0.0.1:8000"

# 1. Login
try:
    req = urllib.request.Request(
        f"{base_url}/api/v1/auth/login",
        data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read().decode())["access_token"]
except Exception as e:
    print("Backend login failed:", e)
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

def get(path):
    r = urllib.request.Request(f"{base_url}{path}", headers=headers)
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read().decode())

print("=== 1. TEST DEPARTMENT TREND WITH MULTI-SELECTION ===")
t_4 = get("/api/v1/pl/departments/trend?agg=monthly&metric=profit&dept=Sales%2COperations%2CFinance%2CIT")
assert set(t_4.get('series', {}).keys()) == {"Sales", "Operations", "Finance", "IT"}, "Series must contain EXACTLY 4 depts"
print(">>> PASS: 4 Depts returned:", list(t_4.get('series', {}).keys()))

t_2 = get("/api/v1/pl/departments/trend?agg=monthly&metric=profit&dept=Sales%2COperations")
assert set(t_2.get('series', {}).keys()) == {"Sales", "Operations"}, "Series must contain EXACTLY 2 depts"
print(">>> PASS: 2 Depts returned:", list(t_2.get('series', {}).keys()))

print("=== 2. TEST METRICS FOR TREND ===")
for m in ['profit', 'revenue', 'expense', 'margin_pct']:
    res = get(f"/api/v1/pl/departments/trend?agg=monthly&metric={m}&dept=Sales%2CIT")
    assert len(res.get('series', {})) == 2
    print(f">>> PASS: Metric {m} OK, periods={len(res.get('periods', []))}")

print("=== 3. TEST FORECAST ALL AGGREGATIONS ===")
for agg in ['daily', 'weekly', 'monthly', 'half-yearly', 'yearly']:
    f = get(f"/api/v1/pl/forecast?dept=Overall&metric=profit&periods=6&agg={agg}")
    assert f.get('has_enough_data') is True, f"Forecast for {agg} should have enough data"
    assert len(f.get('historical', [])) > 0, f"Forecast for {agg} should have historical data"
    assert len(f.get('forecast', [])) > 0, f"Forecast for {agg} should have forecast data"
    print(f">>> PASS: Forecast {agg} OK, hist={len(f.get('historical', []))}, fcast={len(f.get('forecast', []))}")

print("=== 4. TEST BUDGET VS ACTUAL ===")
bva = get("/api/v1/pl/budget-vs-actual?dept=all&range=all")
assert bva.get('has_data') is True
assert len(bva.get('items', [])) == 12
print(f">>> PASS: Budget vs Actual returned {len(bva.get('items'))} depts")

print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
