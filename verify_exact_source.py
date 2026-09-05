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
print("Rows in demo_dataset.csv:", len(df))
print("Columns in demo_dataset.csv:", df.columns.tolist())
rev_sum = df["Revenue"].sum()
exp_sum = df["Expense"].sum()
prof_sum = df["Profit"].sum()
bud_sum = df["Budget"].sum()

print(f"Revenue sum: {rev_sum:,.2f}  -->  ₹{rev_sum/1e7:.2f} Cr")
print(f"Expense sum: {exp_sum:,.2f}  -->  ₹{exp_sum/1e7:.2f} Cr")
print(f"Profit sum:  {prof_sum:,.2f}  -->  ₹{prof_sum/1e7:.2f} Cr")
print(f"Budget sum:  {bud_sum:,.2f}  -->  ₹{bud_sum/1e7:.2f} Cr")

print("\n=== 2. Checking upload 899540e5-fa49-49e8-b87a-6965b44fd71f in backup DB ===")
db_path = r"unified-pl-system_broken_backup\backend\enterprise_pl.db"
con = sqlite3.connect(db_path)
cur = con.cursor()

# Get UploadedFile info
uf = cur.execute("SELECT * FROM uploaded_files WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f'").fetchall()
print("Uploaded file record:", uf)

# Get sample records
sample = cur.execute("SELECT domain, period, line_item, amount, currency, cost_center, dynamic_data FROM pl_records WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f' LIMIT 10").fetchall()
print("Sample pl_records:")
for s in sample:
    print(" ", s[:6])

# Distinct departments
depts = cur.execute("SELECT DISTINCT domain FROM pl_records WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f'").fetchall()
print(f"Departments ({len(depts)}):", [d[0] for d in depts])

# Date range
dates = cur.execute("SELECT min(period), max(period) FROM pl_records WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f'").fetchall()
print("Date Range:", dates)

# Currencies
currs = cur.execute("SELECT DISTINCT currency FROM pl_records WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f'").fetchall()
print("Currencies:", [c[0] for c in currs])

con.close()
