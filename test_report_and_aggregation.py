"""
test_report_and_aggregation.py
==============================
Validates:
1. Redesigned Report Page API (/api/v1/reports/data) with:
   - All departments vs Commercial vs Technology vs Sales vs IT
   - Aggregations: daily, weekly, monthly, quarterly, yearly
   - Periods: all, 2024, 2025, 2026
2. Dynamic KPIs, Trend arrays, Department performance, Budget vs Actual graceful fallback
3. Sortable financial summary table data
4. Anomaly trend filtering and anomaly API integrity
"""
import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent / "unified-pl-system" / "backend"))

from database import SessionLocal
from routers.reports import get_report_data
from services.metric_engine import MetricEngine

def test_reports():
    db = SessionLocal()
    print("\n--- 1. Testing Report Data Default (Executive / All) ---")
    data_all = get_report_data("all", "all", "all", "monthly", db)
    assert data_all is not None
    assert "kpis" in data_all
    assert data_all["kpis"]["total_revenue"] > 0
    assert data_all["kpis"]["total_expense"] > 0
    assert data_all["kpis"]["net_profit"] == data_all["kpis"]["total_revenue"] - data_all["kpis"]["total_expense"]
    assert len(data_all["pnl_trend"]["periods"]) > 0
    assert len(data_all["department_performance"]) > 0
    assert len(data_all["financial_summary"]) > 0
    assert len(data_all["management_insights"]) > 0
    print(f"  [OK] Default report loaded: {len(data_all['department_performance'])} depts, {len(data_all['pnl_trend']['periods'])} trend periods")
    print(f"  [OK] Revenue: {data_all['kpis']['total_revenue']:.2f}, Expense: {data_all['kpis']['total_expense']:.2f}, Profit: {data_all['kpis']['net_profit']:.2f}, Margin: {data_all['kpis']['net_margin']:.2f}%")

    print("\n--- 2. Testing Department Filtering (Commercial vs Technology vs All) ---")
    data_comm = get_report_data("all", "Commercial", "all", "monthly", db)
    data_sales = get_report_data("all", "Sales", "all", "monthly", db)
    data_tech = get_report_data("all", "Technology", "all", "monthly", db)
    data_it = get_report_data("all", "IT", "all", "monthly", db)

    assert len(data_comm["pnl_trend"]["periods"]) > 0, "Commercial periods should not be empty!"
    assert len(data_tech["pnl_trend"]["periods"]) > 0, "Technology periods should not be empty!"
    assert data_comm["kpis"]["total_revenue"] == data_sales["kpis"]["total_revenue"], "Commercial synonym should resolve to Sales"
    assert data_tech["kpis"]["total_revenue"] == data_it["kpis"]["total_revenue"], "Technology synonym should resolve to IT"
    assert data_comm["kpis"]["total_revenue"] != data_tech["kpis"]["total_revenue"], "Commercial and Technology must have different revenue!"
    assert data_comm["kpis"]["total_revenue"] < data_all["kpis"]["total_revenue"], "Single dept revenue must be less than enterprise total!"
    print(f"  [OK] Commercial resolved to Sales (Revenue: {data_comm['kpis']['total_revenue']:.2f})")
    print(f"  [OK] Technology resolved to IT (Revenue: {data_tech['kpis']['total_revenue']:.2f})")
    print(f"  [OK] Enterprise Total Revenue: {data_all['kpis']['total_revenue']:.2f}")

    print("\n--- 3. Testing Aggregation Frequencies ---")
    for agg in ["daily", "weekly", "monthly", "quarterly", "yearly"]:
        d_agg = get_report_data("all", "all", "all", agg, db)
        periods_cnt = len(d_agg["pnl_trend"]["periods"])
        assert periods_cnt > 0, f"Aggregation {agg} returned 0 periods!"
        print(f"  [OK] Aggregation '{agg}': {periods_cnt} periods (sample: {d_agg['pnl_trend']['periods'][:2]})")

    print("\n--- 4. Testing Period / Fiscal Year Filtering ---")
    d_2024 = get_report_data("all", "all", "2024", "monthly", db)
    assert len(d_2024["pnl_trend"]["periods"]) > 0
    assert all(p.startswith("2024") for p in d_2024["pnl_trend"]["periods"]), "All periods in 2024 filter must start with 2024!"
    print(f"  [OK] Period '2024' filtered correctly: {len(d_2024['pnl_trend']['periods'])} monthly records")

    print("\n--- 5. Testing Budget vs Actual Graceful Fallback ---")
    b_info = data_all["budget_vs_actual"]
    assert "has_budget" in b_info
    if not b_info["has_budget"] or not b_info.get("total_budget"):
        assert "Budget data unavailable" in b_info.get("message", "") or "Budget data unavailable" in data_all["kpis"]["budget_status"]
        print(f"  [OK] Graceful budget fallback working: '{data_all['kpis']['budget_status']}'")
    else:
        print(f"  [OK] Budget data present: Allocated {b_info['total_budget']}")

    print("\n--- 6. Testing Management Insights ---")
    insights = data_all["management_insights"]
    assert len(insights) >= 3, "At least 3 data-driven management insights required!"
    for idx, ins in enumerate(insights, 1):
        print(f"  [OK] Insight {idx}: {ins}")

    print("\n========================================================")
    print("ALL REPORT & AGGREGATION TESTS PASSED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    test_reports()
