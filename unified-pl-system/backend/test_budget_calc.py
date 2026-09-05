from database import SessionLocal
from models.pl_record import PLRecord
from services.metric_engine import MetricEngine

db = SessionLocal()
me = MetricEngine(db)
prof = me.get_active_profile()
print("Budget col:", prof["budget_column"])
records = db.query(PLRecord).all()
seen = set()
dept_data = {}
for r in records:
    k = r.dynamic_data.get("Transaction_ID") if r.dynamic_data else (r.period, r.domain, r.amount, r.line_item)
    if k not in seen:
        seen.add(k)
        d = r.domain or "General"
        if d not in dept_data:
            dept_data[d] = {"actual": 0.0, "budget": 0.0}
        exp = float(r.dynamic_data.get("Expense", 0) if r.dynamic_data else 0)
        bgt = float(r.dynamic_data.get(prof["budget_column"], 0) if r.dynamic_data and prof["budget_column"] else 0)
        dept_data[d]["actual"] += exp
        dept_data[d]["budget"] += bgt

for d, v in sorted(dept_data.items(), key=lambda x: x[1]["actual"], reverse=True):
    var = v["actual"] - v["budget"]
    vp = (var / v["budget"] * 100) if v["budget"] > 0 else 0
    print(f"{d}: Actual={v['actual']:,.2f}, Budget={v['budget']:,.2f}, Var={var:,.2f} ({vp:+.1f}%)")
