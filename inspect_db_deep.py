import sqlite3
import os
import json

db_paths = [
    os.path.abspath("enterprise_pl.db"),
    os.path.abspath("unified-pl-system/backend/enterprise_pl.db"),
    os.path.abspath("unified-pl-system/enterprise_pl.db")
]

results = {}

for p in db_paths:
    if os.path.exists(p):
        size = os.path.getsize(p)
        conn = sqlite3.connect(p)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in c.fetchall()]
        table_info = {}
        for t in tables:
            try:
                c.execute(f"SELECT COUNT(*) FROM {t}")
                cnt = c.fetchone()[0]
                
                c.execute(f"PRAGMA table_info({t})")
                cols = [col[1] for col in c.fetchall()]
                
                table_info[t] = {"count": cnt, "columns": cols}
            except Exception as e:
                table_info[t] = {"error": str(e)}
        
        # Financial metrics summary
        summary = {}
        if "financial_records" in tables:
            c.execute("SELECT COUNT(*), MIN(date), MAX(date), SUM(revenue), SUM(expenses), SUM(net_profit) FROM financial_records")
            row = c.fetchone()
            summary["financial_records"] = {
                "count": row[0],
                "min_date": row[1],
                "max_date": row[2],
                "total_revenue": row[3],
                "total_expenses": row[4],
                "total_net_profit": row[5]
            }
            c.execute("SELECT DISTINCT department FROM financial_records")
            summary["departments"] = [r[0] for r in c.fetchall()]
        
        results[p] = {
            "size_bytes": size,
            "tables": table_info,
            "summary": summary
        }
        conn.close()

with open("scratch_db_inspect.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("DB Inspection complete. Written to scratch_db_inspect.json")
