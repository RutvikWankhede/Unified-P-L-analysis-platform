import sys
import os
import io
import json

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import sqlite3

backup_db = r"unified-pl-system_broken_backup\backend\enterprise_pl.db"
target_dbs = [
    r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\enterprise_pl.db",
    r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\backend\enterprise_pl.db",
]

print("=== Extracting Original Dataset ===")
con_src = sqlite3.connect(backup_db)
cur_src = con_src.cursor()

# 1. Extract raw transactions from dynamic_data of upload 899540e5-fa49-49e8-b87a-6965b44fd71f
rows = cur_src.execute("""
    SELECT DISTINCT dynamic_data 
    FROM pl_records 
    WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f' AND dynamic_data IS NOT NULL
""").fetchall()

transactions = []
for r in rows:
    if r[0]:
        try:
            d = json.loads(r[0])
            transactions.append(d)
        except Exception as e:
            pass

df_trans = pd.DataFrame(transactions)
print(f"Extracted {len(df_trans)} unique transactions.")
print("Columns:", df_trans.columns.tolist())

# Sort chronologically by Date
if "Date" in df_trans.columns:
    df_trans["Date"] = pd.to_datetime(df_trans["Date"], format="mixed", errors="coerce").dt.strftime("%Y-%m-%d")
    df_trans.sort_values("Date", inplace=True)

# Save exact CSV and Excel files
csv_out1 = r"unified-pl-system\unified_pnl_enterprise_demo.csv"
csv_out2 = r"data\default\unified_pnl_enterprise_demo.csv"
xlsx_out = r"unified-pl-system\unified_pnl_enterprise_demo.xlsx"

os.makedirs(r"data\default", exist_ok=True)
df_trans.to_csv(csv_out1, index=False)
df_trans.to_csv(csv_out2, index=False)
df_trans.to_excel(xlsx_out, index=False)
print(f"Saved original dataset to:\n  {csv_out1}\n  {csv_out2}\n  {xlsx_out}")

# Verify exact sums
rev_sum = df_trans["Revenue"].sum()
exp_sum = df_trans["Expense"].sum()
prof_sum = df_trans["Profit"].sum()
print(f"\nCalculated Sums from Extracted CSV:")
print(f"Total Revenue: ₹{rev_sum:,.2f}  -->  ₹{rev_sum/1e7:.2f} Cr (₹27.80 Cr)")
print(f"Total Expense: ₹{exp_sum:,.2f}  -->  ₹{exp_sum/1e7:.2f} Cr (₹19.81 Cr)")
print(f"Net Profit:    ₹{prof_sum:,.2f}  -->  ₹{prof_sum/1e7:.2f} Cr (₹7.99 Cr)")

# 2. Re-populate active databases with this exact dataset
upload_id = "899540e5-fa49-49e8-b87a-6965b44fd71f"
records_src = cur_src.execute("""
    SELECT id, domain, period, line_item, amount, currency, cost_center, dynamic_data
    FROM pl_records
    WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f'
""").fetchall()

record_id_map = {} # old_id -> new_id

for target_db in target_dbs:
    print(f"\nPopulating active database: {target_db}")
    con_tgt = sqlite3.connect(target_db)
    cur_tgt = con_tgt.cursor()
    
    # Delete old records
    cur_tgt.execute("DELETE FROM pl_records")
    cur_tgt.execute("DELETE FROM uploaded_files")
    cur_tgt.execute("DELETE FROM anomalies")
    
    # Insert pl_records
    for r in records_src:
        old_id, domain, period, line_item, amount, currency, cost_center, dyn_data = r
        cur_tgt.execute("""
            INSERT INTO pl_records (upload_id, uploaded_by, domain, period, line_item, amount, currency, cost_center, dynamic_data, created_at)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (upload_id, domain, period, line_item, amount, currency, cost_center, dyn_data))
        new_id = cur_tgt.lastrowid
        record_id_map[old_id] = new_id
        
    # Insert uploaded_files
    cur_tgt.execute("""
        INSERT INTO uploaded_files (upload_id, filename, file_size_bytes, user_id, status, created_at)
        VALUES (?, 'unified_pnl_enterprise_demo.xlsx', 126378, 1, 'COMPLETED', datetime('now'))
    """, (upload_id,))
    
    # Check if anomalies exist for old ids
    if record_id_map:
        old_ids_tuple = tuple(record_id_map.keys())
        if len(old_ids_tuple) == 1:
            q = f"SELECT pl_record_id, anomaly_score, severity, is_anomaly, percentile_rank, status FROM anomalies WHERE pl_record_id = {old_ids_tuple[0]}"
        else:
            q = f"SELECT pl_record_id, anomaly_score, severity, is_anomaly, percentile_rank, status FROM anomalies WHERE pl_record_id IN {old_ids_tuple}"
        
        try:
            anom_rows = cur_src.execute(q).fetchall()
            print(f"Found {len(anom_rows)} anomalies associated with this dataset.")
            for ar in anom_rows:
                old_pid, a_score, sev, is_anom, p_rank, st = ar
                new_pid = record_id_map.get(old_pid)
                if new_pid:
                    cur_tgt.execute("""
                        INSERT INTO anomalies (pl_record_id, anomaly_score, severity, is_anomaly, percentile_rank, status, detected_at)
                        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (new_pid, a_score, sev, is_anom, p_rank, st))
        except Exception as ae:
            print("Anomaly copy note:", ae)
            
    # Update active dataset setting
    cur_tgt.execute("DELETE FROM settings WHERE key IN ('active_dataset_id', 'active_dataset_filename')")
    cur_tgt.execute("INSERT INTO settings (key, value) VALUES ('active_dataset_id', ?)", (upload_id,))
    cur_tgt.execute("INSERT INTO settings (key, value) VALUES ('active_dataset_filename', 'unified_pnl_enterprise_demo.xlsx')")
    
    con_tgt.commit()
    con_tgt.close()

con_src.close()
print("\n=== Restoration Completed Successfully ===")
