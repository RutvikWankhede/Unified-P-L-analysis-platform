import os
import sys
import io
import json
import sqlite3
import pandas as pd

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

print("=== CHECKING FILES ===")
files = [
    "unified_pnl_enterprise_demo.csv",
    "unified_pnl_enterprise_demo.xlsx",
    "unified-pl-system/unified_pnl_enterprise_demo.csv",
    "unified-pl-system/unified_pnl_enterprise_demo.xlsx",
    "data/default/unified_pnl_enterprise_demo.csv",
    "unified-pl-system/data/default/unified_pnl_enterprise_demo.csv"
]
for f in files:
    exists = os.path.exists(f)
    size = os.path.getsize(f) if exists else 0
    print(f"File {f}: exists={exists}, size={size}")
    if exists and f.endswith(".csv"):
        try:
            df = pd.read_csv(f)
            print(f"  Rows: {len(df)}, Cols: {list(df.columns)}")
            rev = df["Revenue"].sum() if "Revenue" in df.columns else 0
            exp = df["Expense"].sum() if "Expense" in df.columns else 0
            prof = df["Profit"].sum() if "Profit" in df.columns else (rev - exp)
            print(f"  Revenue: {rev:,.2f} ({rev/1e7:.2f} Cr)")
            print(f"  Expense: {exp:,.2f} ({exp/1e7:.2f} Cr)")
            print(f"  Profit:  {prof:,.2f} ({prof/1e7:.2f} Cr)")
            print(f"  Depts ({df['Department'].nunique()}): {df['Department'].unique() if 'Department' in df.columns else 'N/A'}")
            print(f"  Date Range: {df['Date'].min()} to {df['Date'].max()}" if 'Date' in df.columns else "N/A")
        except Exception as e:
            print(f"  Error reading {f}: {e}")

print("\n=== CHECKING DATABASES ===")
dbs = [
    "enterprise_pl.db",
    "unified-pl-system/enterprise_pl.db",
    "unified-pl-system/backend/enterprise_pl.db",
    "unified-pl-system_broken_backup/backend/enterprise_pl.db"
]
for db in dbs:
    if os.path.exists(db):
        con = sqlite3.connect(db)
        cur = con.cursor()
        print(f"\nDatabase: {db}")
        try:
            cnt = cur.execute("SELECT count(*) FROM pl_records").fetchone()[0]
            print(f"  pl_records count: {cnt}")
            uploads = cur.execute("SELECT DISTINCT upload_id FROM pl_records").fetchall()
            print(f"  upload_ids: {[u[0] for u in uploads]}")
            
            anom_cnt = cur.execute("SELECT count(*) FROM anomalies").fetchone()[0]
            print(f"  anomalies count: {anom_cnt}")
            
            # calculate KPI totals
            rev = cur.execute("SELECT SUM(amount) FROM pl_records WHERE line_item='Revenue'").fetchone()[0] or 0
            exp = cur.execute("SELECT SUM(amount) FROM pl_records WHERE line_item='Expense'").fetchone()[0] or 0
            print(f"  Total Revenue: {rev:,.2f} ({rev/1e7:.2f} Cr)")
            print(f"  Total Expense: {exp:,.2f} ({exp/1e7:.2f} Cr)")
            print(f"  Net Profit:    {(rev - exp):,.2f} ({(rev - exp)/1e7:.2f} Cr)")
            
            settings = cur.execute("SELECT key, value FROM settings").fetchall()
            print(f"  Settings: {settings}")
        except Exception as e:
            print(f"  Error querying DB: {e}")
        con.close()
