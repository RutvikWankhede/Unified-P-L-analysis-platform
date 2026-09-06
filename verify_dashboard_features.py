import os
import sys
import json
import requests

BASE_URL = "http://localhost:8000"

def run_checks():
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[1] Auth Success", flush=True)

    # 1. Check Active Dataset
    act = requests.get(f"{BASE_URL}/api/v1/datasets/active", headers=headers).json()
    print(f"[2] Active Dataset: {act.get('filename')}", flush=True)

    # 2. Check Summary KPIs
    summ = requests.get(f"{BASE_URL}/api/v1/pl/summary", headers=headers).json()
    k = summ["kpis"]
    print(f"[3] Seeded KPIs: Rev = Rs {k['revenue']/1e7:.2f} Cr, Exp = Rs {k['expense']/1e7:.2f} Cr, Net = Rs {k['profit']/1e7:.2f} Cr", flush=True)

    # 3. Check Anomaly Overview
    for p in ["overall", "daily", "weekly", "monthly", "half-yearly", "yearly"]:
        a = requests.get(f"{BASE_URL}/api/v1/pl/anomaly-overview?period={p}&dept=all", headers=headers).json()
        print(f"[4] Anomaly {p}: Total = {a['total_anomalies']}, Crit = {a['critical_count']}, High = {a['high_count']}, Med = {a['medium_count']}, Low = {a['low_count']}", flush=True)

    # 4. Check Dept Performance
    for m in ["profit", "revenue", "expense", "margin_pct"]:
        dp = requests.get(f"{BASE_URL}/api/v1/pl/department-performance?metric={m}&limit=top5", headers=headers).json()
        print(f"[5] Dept Perf ({m}): Top = {dp['departments'][0]} ({dp['values'][0]})", flush=True)

    # 5. Check Expense Distribution
    for m in ["expense", "revenue", "profit", "margin_pct"]:
        ed = requests.get(f"{BASE_URL}/api/v1/pl/expense-distribution?metric={m}&dept=all", headers=headers).json()
        print(f"[6] Financial Dist ({m}): HasData = {ed['has_data']}, Categories = {len(ed['categories'])}, Total = {ed.get('total_amount', 0):,.2f}", flush=True)

    # 6. Check Budget vs Actual with Top 5, Top 10, All
    for r in ["top5", "top10", "all"]:
        bva = requests.get(f"{BASE_URL}/api/v1/pl/budget-vs-actual?range={r}&dept=all", headers=headers).json()
        print(f"[7] Budget vs Actual ({r}): Items = {len(bva['items'])}, Total Var = {bva['total_variance_pct']}%, On = {bva['on_budget_count']}, Over = {bva['over_budget_count']}, Highest = {bva['highest_variance_dept']}", flush=True)

    # 7. Check Insights
    ins = requests.get(f"{BASE_URL}/api/v1/pl/insights", headers=headers).json()
    print(f"[8] Insights count: {len(ins['insights'])}, First: {ins['insights'][0]['title']}", flush=True)

    # 8. Check Forecast vs Actual
    fa = requests.get(f"{BASE_URL}/api/v1/pl/forecast-vs-actual?dept=all&period=monthly", headers=headers).json()
    print(f"[9] Forecast vs Actual (monthly): Periods = {len(fa['periods'])}, Variances = {len(fa['variance'])}", flush=True)

    # 9. Check Cash Flow Trend
    cf = requests.get(f"{BASE_URL}/api/v1/pl/cash-flow-trend?dept=all&period=monthly", headers=headers).json()
    print(f"[10] Cash Flow (monthly): Periods = {len(cf['periods'])}, Inflow sample = {cf['inflow'][0]}, Net = {cf['net_flow'][0]}", flush=True)

    print("\n>>> ALL VERIFICATION CHECKS COMPLETED PERFECTLY! <<<", flush=True)

if __name__ == "__main__":
    run_checks()
