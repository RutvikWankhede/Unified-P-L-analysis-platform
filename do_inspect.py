import os
import sys
import json
import sqlite3
import pandas as pd

out_path = "inspect_out.txt"
with open(out_path, "w", encoding="utf-8") as out:
    def log(msg):
        out.write(str(msg) + "\n")
        out.flush()

    log("=== CHECKING FILES ===")
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
        log(f"File {f}: exists={exists}, size={size}")
        if exists and f.endswith(".csv"):
            try:
                df = pd.read_csv(f)
                log(f"  Rows: {len(df)}, Cols: {list(df.columns)}")
                rev = df["Revenue"].sum() if "Revenue" in df.columns else 0
                exp = df["Expense"].sum() if "Expense" in df.columns else 0
                prof = df["Profit"].sum() if "Profit" in df.columns else (rev - exp)
                log(f"  Revenue: {rev:,.2f} ({rev/1e7:.2f} Cr)")
                log(f"  Expense: {exp:,.2f} ({exp/1e7:.2f} Cr)")
                log(f"  Profit:  {prof:,.2f} ({prof/1e7:.2f} Cr)")
                log(f"  Depts ({df['Department'].nunique()}): {list(df['Department'].unique()) if 'Department' in df.columns else 'N/A'}")
                log(f"  Date Range: {df['Date'].min()} to {df['Date'].max()}" if 'Date' in df.columns else "N/A")
            except Exception as e:
                log(f"  Error reading {f}: {e}")

    log("\n=== CHECKING DATABASES ===")
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
            log(f"\nDatabase: {db}")
            try:
                cnt = cur.execute("SELECT count(*) FROM pl_records").fetchone()[0]
                log(f"  pl_records count: {cnt}")
                uploads = cur.execute("SELECT DISTINCT upload_id FROM pl_records").fetchall()
                log(f"  upload_ids: {[u[0] for u in uploads]}")
                
                anom_cnt = cur.execute("SELECT count(*) FROM anomalies").fetchone()[0]
                log(f"  anomalies count: {anom_cnt}")
                
                rev = cur.execute("SELECT SUM(amount) FROM pl_records WHERE line_item='Revenue'").fetchone()[0] or 0
                exp = cur.execute("SELECT SUM(amount) FROM pl_records WHERE line_item='Expense'").fetchone()[0] or 0
                log(f"  Total Revenue: {rev:,.2f} ({rev/1e7:.2f} Cr)")
                log(f"  Total Expense: {exp:,.2f} ({exp/1e7:.2f} Cr)")
                log(f"  Net Profit:    {(rev - exp):,.2f} ({(rev - exp)/1e7:.2f} Cr)")
                
                settings = cur.execute("SELECT key, value FROM settings").fetchall()
                log(f"  Settings: {settings}")
            except Exception as e:
                log(f"  Error querying DB: {e}")
            con.close()
