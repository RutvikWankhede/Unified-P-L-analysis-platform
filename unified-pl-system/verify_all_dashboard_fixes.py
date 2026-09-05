import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db, SessionLocal
from services.metric_engine import MetricEngine

def main():
    db = SessionLocal()
    try:
        engine = MetricEngine(db)
        print(f"Active Dataset ID: {engine.active_dataset_id}")
        
        # Test 1: Expense Distribution for all metrics and departments
        metrics = ["expense", "revenue", "profit", "margin_pct"]
        depts = ["all", "Operations", "Finance", "Sales"]
        
        print("\n--- 1. DISTRIBUTION METRIC TESTS ---")
        for m in metrics:
            for d in depts:
                res = engine.get_financial_distribution(metric=m, dept=d)
                cats = res.get("categories", [])
                top_cats = ", ".join([f"{c['name']}: {c['amount']}" for c in cats[:3]])
                print(f"[OK] Metric: {m:10s} | Dept: {d:10s} | Total: {res.get('total_amount', 0):>12,.2f} | Items: {len(cats)} | Top: {top_cats}")
                assert res["has_data"] == True, f"Failed for {m}, {d}"
                assert len(cats) > 0, f"No categories for {m}, {d}"
        
        print("\n--- 2. DEPARTMENT PERFORMANCE METRIC & LIMIT TESTS ---")
        for m in ["profit", "expense", "revenue", "margin_pct"]:
            for lim in ["top5", "top10", "all"]:
                res = engine.get_department_performance(metric=m, limit=lim)
                depts_list = res.get("departments", [])
                vals_list = res.get("values", [])
                print(f"[OK] Metric: {m:10s} | Limit: {lim:6s} | Count: {len(depts_list)} | Top Dept: {depts_list[0] if depts_list else 'None'} ({vals_list[0] if vals_list else 0})")
                assert len(depts_list) > 0
                if lim == "top5":
                    assert len(depts_list) <= 5
                elif lim == "top10":
                    assert len(depts_list) <= 10

        print("\n--- 3. TIME AGGREGATIONS FOR CHARTS ---")
        for agg in ["daily", "weekly", "monthly", "quarterly", "half-yearly", "yearly"]:
            df = engine.aggregate_by_dimension(aggregation=agg)
            print(f"[OK] Aggregation: {agg:12s} | Rows count: {len(df)}")
            assert len(df) > 0


        print("\n--- 4. ANOMALY OVERVIEW TIME AGGREGATIONS ---")
        for p in ["overall", "daily", "weekly", "monthly", "half-yearly", "yearly"]:
            res = engine.get_anomaly_summary(period=p, dept="all")
            print(f"[OK] Period: {p:12s} | Total Anomalies: {res.get('total_anomalies', 0)} | has_data: {res.get('has_data')}")
            assert "total_anomalies" in res
            assert "severities" in res


        print("\n--- 5. BUDGET VS ACTUAL WITH REAL TARGETS ---")
        res = engine.get_budget_vs_actual(dept="all")
        print(f"[OK] Budget vs Actual has_data: {res.get('has_data')} | Items: {len(res.get('items', []))}")
        for it in res.get("items", [])[:3]:
            print(f"     Dept: {it['department']:15s} | Actual: {it['actual']:>10,.2f} | Budget: {it['budget']:>10,.2f} | Var: {it['variance']:>10,.2f}")
        
        print("\n=== ALL BACKEND METRIC & AGGREGATION TESTS PASSED 100%! ===")
    finally:
        db.close()

if __name__ == "__main__":
    main()
