import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import sqlite3

print("=== 1. Checking backend/demo_dataset.csv ===")
df = pd.read_csv(r"unified-pl-system\backend\demo_dataset.csv")
print("Rows:", len(df))
print("Columns:", df.columns.tolist())
rev = df["Revenue"].sum()
exp = df["Expense"].sum()
prof = df["Profit"].sum()
bud = df["Budget"].sum()

print(f"Revenue: ₹{rev:,.2f}  -->  ₹{rev/1e7:.2f} Cr")
print(f"Expense: ₹{exp:,.2f}  -->  ₹{exp/1e7:.2f} Cr")
print(f"Profit:  ₹{prof:,.2f}  -->  ₹{prof/1e7:.2f} Cr")
print(f"Budget:  ₹{bud:,.2f}  -->  ₹{bud/1e7:.2f} Cr")
print(f"Departments ({df['Department'].nunique()}): {df['Department'].unique().tolist()}")
print(f"Currencies: {df['Currency'].unique().tolist()}")
print(f"Date Range: {df['Date'].min()} to {df['Date'].max()}")

print("\n=== 2. Checking SQLite Backups ===")
db_path = r"unified-pl-system_broken_backup\backend\enterprise_pl.db"
if os.path.exists(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Check all uploaded_files
    try:
        files = cur.execute("SELECT upload_id, filename, file_size_bytes FROM uploaded_files").fetchall()
        print("Uploaded files in backup DB:", files)
    except Exception as e:
        print("uploaded_files err:", e)
        
    # Check distinct uploads and their sums in pl_records
    try:
        sums = cur.execute("""
            SELECT upload_id, line_item, count(*), sum(amount)
            FROM pl_records
            GROUP BY upload_id, line_item
        """).fetchall()
        print("PL Records sums by upload_id and line_item:")
        for s in sums:
            print(" ", s)
    except Exception as e:
        print("pl_records err:", e)
    con.close()
