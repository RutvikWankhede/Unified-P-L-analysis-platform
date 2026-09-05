import sys
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "unified-pl-system" / "backend"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
import main
from routers.auth_router import create_access_token

client = TestClient(main.app)

from database import SessionLocal
from models.user import User

db = SessionLocal()
user = db.query(User).first()
username = user.username if user else "admin"

token = create_access_token(data={"sub": username, "role": "ADMINISTRATOR"})
headers = {"Authorization": f"Bearer {token}"}

print("=" * 60)
print("VERIFYING DASHBOARD ENDPOINTS & INTEGRATION")
print("=" * 60)

# 1. Health check
res = client.get("/api/v1/health")
print(f"1. Health Check: Status {res.status_code} -> {res.json()}")

# 2. Revenue vs Expense vs Profit (Preserved)
res = client.get("/api/v1/pl/charts?dept=all&agg=monthly", headers=headers)
print(f"2. Rev vs Exp vs Profit (Preserved): Status {res.status_code}, Periods: {len(res.json().get('periods', []))}")
assert res.status_code == 200

# 3. Anomaly Overview (Preserved)
res = client.get("/api/v1/pl/anomaly-overview?period=overall&dept=all", headers=headers)
print(f"3. Anomaly Overview (Preserved): Status {res.status_code}, Total: {res.json().get('total_anomalies')}")
assert res.status_code == 200

# 4. Department Performance (Metric: Profit, Limit: Top5)
res = client.get("/api/v1/pl/department-performance?metric=profit&limit=top5", headers=headers)
print(f"4. Dept Perf (Profit Top5): Status {res.status_code}, Depts: {res.json().get('departments')}")
assert res.status_code == 200
assert len(res.json().get("departments", [])) == 5

# 5. Department Performance (Metric: Expense, Limit: All)
res = client.get("/api/v1/pl/department-performance?metric=expense&limit=all", headers=headers)
print(f"5. Dept Perf (Expense All): Status {res.status_code}, Dept Count: {len(res.json().get('departments', []))}")
assert res.status_code == 200

# 6. Expense Distribution (Dynamic Categories)
res = client.get("/api/v1/pl/expense-distribution?dept=all", headers=headers)
print(f"6. Expense Distribution: Status {res.status_code}, Has Data: {res.json().get('has_data')}, Categories: {len(res.json().get('categories', []))}")
for cat in res.json().get("categories", []):
    print(f"   - {cat['name']}: {cat['amount']:,.2f} ({cat['percentage']}%) [Color: {cat['color']}]")
assert res.status_code == 200
assert res.json().get("has_data") is True

# 7. Insights (Dynamic & Rich)
res = client.get("/api/v1/pl/insights", headers=headers)
insights = res.json().get("insights", [])
print(f"7. Insights: Status {res.status_code}, Count: {len(insights)}")
for ins in insights:
    print(f"   * [{ins['badge']}] {ins['title']} -> {ins['metric']}: {ins['current_value']} (Change: {ins['change_pct']}%)")
    assert "why_it_matters" in ins
    assert "supporting_data" in ins
    assert "suggested_action" in ins
assert res.status_code == 200
assert len(insights) > 0

# 8. Recommendations (AI Strategic Guidance)
res = client.get("/api/v1/recommendations", headers=headers)
recs = res.json()
print(f"8. Recommendations: Status {res.status_code}, Count: {len(recs)}")
for rec in recs:
    print(f"   * [{rec.get('priority')} Priority] {rec.get('title')} ({rec.get('department')}) -> Impact: {rec.get('financial_impact')}")
    assert "reason" in rec
    assert "suggested_action" in rec
assert res.status_code == 200
assert len(recs) > 0

# 9. Budget vs Actual (Financial Comparison & Variance)
res = client.get("/api/v1/pl/budget-vs-actual?dept=all", headers=headers)
b_data = res.json()
print(f"9. Budget vs Actual: Status {res.status_code}, Has Data: {b_data.get('has_data')}, Depts: {len(b_data.get('items', []))}")
print(f"   Total Actual: {b_data.get('total_actual'):,.2f} | Total Budget: {b_data.get('total_budget'):,.2f} | Total Var: {b_data.get('total_variance'):,.2f} ({b_data.get('total_variance_pct')}%)")
for item in b_data.get("items", []):
    print(f"   - {item['department']}: Actual={item['actual']:,.2f}, Budget={item['budget']:,.2f}, Var={item['variance']:,.2f} ({item['variance_pct']:+.1f}%) -> {item['status']}")
assert res.status_code == 200
assert b_data.get("has_data") is True
assert len(b_data.get("items", [])) > 0

print("=" * 60)
print("ALL BACKEND & INTEGRATION CHECKS PASSED PERFECTLY!")
print("=" * 60)
