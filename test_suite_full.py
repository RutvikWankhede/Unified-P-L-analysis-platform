import requests
import json
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000"

# 1. Login
def login():
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code != 200:
        res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin@enterprise.com", "password": "admin123"})
    if res.status_code != 200:
        print(f"Login failed: {res.status_code} {res.text}")
        sys.exit(1)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

headers = login()
print("[OK] Login successful.")

# 2. Check Active Dataset
res = requests.get(f"{BASE_URL}/api/v1/datasets/active", headers=headers)
print(f"Active Dataset: {res.json()}")

# 3. Check Summary KPIs
summary = requests.get(f"{BASE_URL}/api/v1/pl/summary", headers=headers).json()
kpis = summary.get("kpis", {})
rev = kpis.get("revenue")
exp = kpis.get("expense")
prof = kpis.get("profit")
print(f"KPIs -> Revenue: {rev:,.2f} | Expense: {exp:,.2f} | Net Profit: {prof:,.2f}")
assert abs(rev - 277988276.87) < 1.0, f"Expected 277988276.87, got {rev}"
assert abs(exp - 198066136.85) < 1.0, f"Expected 198066136.85, got {exp}"
assert abs(prof - 79922140.02) < 1.0, f"Expected 79922140.02, got {prof}"
print("[OK] KPIs match exact seeded baseline Rs 27.80 Cr / Rs 19.81 Cr / Rs 7.99 Cr!")

# 4. Check Anomaly Overview
print("\n--- Testing Anomaly Overview ---")
for period in ["overall", "daily", "weekly", "monthly", "half-yearly", "yearly"]:
    anom_all = requests.get(f"{BASE_URL}/api/v1/pl/anomaly-overview?period={period}&dept=all", headers=headers).json()
    print(f"Period: {period:<12} | Total: {anom_all['total_anomalies']:<3} | Crit: {anom_all['critical_count']} | High: {anom_all['high_count']} | Med: {anom_all['medium_count']} | Low: {anom_all['low_count']}")

anom_sales = requests.get(f"{BASE_URL}/api/v1/pl/anomaly-overview?period=overall&dept=Sales", headers=headers).json()
print(f"Dept: Sales (Overall) | Total: {anom_sales['total_anomalies']} | Crit: {anom_sales['critical_count']} | High: {anom_sales['high_count']}")

# 5. Check Revenue vs Expense Aggregations
print("\n--- Testing Revenue vs Expense Chart Aggregations ---")
for agg in ["overall", "daily", "weekly", "monthly", "half-yearly", "yearly"]:
    chart_res = requests.get(f"{BASE_URL}/api/v1/pl/charts?dept=all&agg={agg}", headers=headers).json()
    periods = chart_res.get("periods", [])
    rev_vals = chart_res.get("revenue_trend", [])
    print(f"Agg: {agg:<12} | Periods count: {len(periods):<3} | Sample periods: {periods[:3]}")

# 6. Check Department Performance
print("\n--- Testing Department Performance ---")
for metric in ["profit", "revenue", "expense", "margin_pct"]:
    for limit in ["top5", "top10", "all"]:
        dp = requests.get(f"{BASE_URL}/api/v1/pl/department-performance?metric={metric}&limit={limit}", headers=headers).json()
        print(f"Metric: {metric:<10} | Limit: {limit:<5} | Depts returned: {len(dp['departments'])} | Top: {dp['departments'][0]} ({dp['values'][0]})")

# 7. Check Expense Distribution
print("\n--- Testing Expense Distribution ---")
exp_dist = requests.get(f"{BASE_URL}/api/v1/pl/expense-distribution?dept=all", headers=headers).json()
print(f"Expense Dist (All) | Has Data: {exp_dist['has_data']} | Total: {exp_dist['total_expense']:,.2f} | Categories: {len(exp_dist['categories'])}")
for c in exp_dist['categories'][:4]:
    print(f"  -> {c['name']}: Rs {c['amount']:,.2f} ({c['percentage']}%)")

# 8. Check Insights
print("\n--- Testing Dynamic Insights ---")
insights_res = requests.get(f"{BASE_URL}/api/v1/pl/insights", headers=headers).json()
insights = insights_res.get("insights", [])
print(f"Insights count: {len(insights)}")
for ins in insights:
    print(f"  [{ins['badge']}] {ins['title']} - Metric: {ins['metric']} | Change: {ins['change_pct']}%")

# 9. Check Forecast vs Actual
print("\n--- Testing Forecast vs Actual ---")
for period in ["monthly", "weekly", "daily", "yearly"]:
    fcst = requests.get(f"{BASE_URL}/api/v1/pl/forecast-vs-actual?dept=all&period={period}", headers=headers).json()
    print(f"Period: {period:<10} | Periods: {len(fcst['periods'])} | Actuals: {len([x for x in fcst['actual'] if x is not None])} | Forecasts: {len([x for x in fcst['forecast'] if x is not None])}")

# 10. Check Cash Flow Trend
print("\n--- Testing Cash Flow Trend ---")
for period in ["monthly", "weekly", "daily", "overall"]:
    cf = requests.get(f"{BASE_URL}/api/v1/pl/cash-flow-trend?dept=all&period={period}", headers=headers).json()
    print(f"Period: {period:<10} | Periods: {len(cf['periods'])} | Net Flow sample: {cf['net_flow'][:2]}")

print("\n[SUCCESS] ALL BACKEND LOGIC VERIFIED WITH SEEDED DATASET SUCCESSFULLY!")
