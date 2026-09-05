from database import SessionLocal
from models.pl_record import PLRecord
from services.metric_engine import MetricEngine

db = SessionLocal()
me = MetricEngine(db)

for m in ["expense", "revenue", "profit", "margin_pct"]:
    for d in ["all", "Sales", "Finance", "Operations"]:
        res = me.get_expense_distribution(dept=d)
        print(f"Metric={m}, Dept={d}: has_data={res.get('has_data')}, cats={len(res.get('categories', []))}")
