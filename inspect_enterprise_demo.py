import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import sqlite3

print("=== 1. Checking data/default/unified_pnl_enterprise_demo.csv ===")
p = r"data\default\unified_pnl_enterprise_demo.csv"
if os.path.exists(p):
    df = pd.read_csv(p)
    print("Rows:", len(df))
    print("Columns:", df.columns.tolist())
    print("Sample rows:\n", df.head(3))
    rev = df["Revenue"].sum() if "Revenue" in df.columns else 0
    exp = df["Expense"].sum() if "Expense" in df.columns else 0
    prof = df["Profit"].sum() if "Profit" in df.columns else 0
    print(f"Revenue sum: {rev:,.2f}  -->  ₹{rev/1e7:.2f} Cr")
    print(f"Expense sum: {exp:,.2f}  -->  ₹{exp/1e7:.2f} Cr")
    print(f"Profit sum:  {prof:,.2f}  -->  ₹{prof/1e7:.2f} Cr")

print("\n=== 2. Checking pl_records for upload 899540e5-fa49-49e8-b87a-6965b44fd71f in backup DB ===")
db_path = r"unified-pl-system_broken_backup\backend\enterprise_pl.db"
con = sqlite3.connect(db_path)
cur = con.cursor()

# Export all columns and rows from pl_records for this upload
query = """
SELECT id, upload_id, domain, period, line_item, amount, currency, cost_center, dynamic_data
FROM pl_records
WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f'
"""
db_df = pd.read_sql_query(query, con)
print("DB Records count:", len(db_df))
print(db_df.groupby('line_item')['amount'].agg(['count', 'sum', lambda s: f"₹{s.sum()/1e7:.2f} Cr"]))

rev_total = db_df[db_df['line_item'] == 'Revenue']['amount'].sum()
exp_total = db_df[db_df['line_item'] == 'Expense']['amount'].sum()
net_profit = rev_total - exp_total

print(f"\nEXACT VALUES FROM ORIGINAL DATASET:")
print(f"Total Revenue: ₹{rev_total:,.2f}  -->  ₹{rev_total/1e7:.2f} Cr (₹27.80 Cr)")
print(f"Total Expense: ₹{exp_total:,.2f}  -->  ₹{exp_total/1e7:.2f} Cr (₹19.81 Cr)")
print(f"Net Profit:    ₹{net_profit:,.2f}  -->  ₹{net_profit/1e7:.2f} Cr (₹7.99 Cr)")
print(f"Departments ({db_df['domain'].nunique()}): {db_df['domain'].unique().tolist()}")
print(f"Date Range: {db_df['period'].min()} to {db_df['period'].max()}")
print(f"Currencies: {db_df['currency'].unique().tolist()}")

# Also check dynamic_data
import json
first_dyn = json.loads(db_df['dynamic_data'].iloc[0]) if db_df['dynamic_data'].iloc[0] else {}
print("Sample dynamic_data keys:", list(first_dyn.keys()))
print("Sample dynamic_data:", first_dyn)

con.close()
