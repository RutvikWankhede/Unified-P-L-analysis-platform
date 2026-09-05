import os
import sys
import io
import json
import sqlite3
import pandas as pd
import shutil

backup_db = r"unified-pl-system_broken_backup\backend\enterprise_pl.db"
con_src = sqlite3.connect(backup_db)
cur_src = con_src.cursor()

upload_id = "899540e5-fa49-49e8-b87a-6965b44fd71f"

# 1. Extract raw transactions
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
        except Exception:
            pass

df_trans = pd.DataFrame(transactions)
if "Date" in df_trans.columns:
    df_trans["Date"] = pd.to_datetime(df_trans["Date"], format="mixed", errors="coerce").dt.strftime("%Y-%m-%d")
    df_trans.sort_values("Date", inplace=True)

# Save exact CSV and Excel files to all canonical and fallback paths
csv_paths = [
    r"unified_pnl_enterprise_demo.csv",
    r"unified-pl-system\unified_pnl_enterprise_demo.csv",
    r"data\default\unified_pnl_enterprise_demo.csv",
    r"unified-pl-system\data\default\unified_pnl_enterprise_demo.csv",
    r"unified-pl-system\backend\demo_dataset.csv", # Keep demo_dataset.csv synchronized with enterprise demo dataset to prevent accidental fallback drift
]

for p in csv_paths:
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    df_trans.to_csv(p, index=False)
    print(f"Saved CSV: {p} ({len(df_trans)} rows)")

xlsx_paths = [
    r"unified_pnl_enterprise_demo.xlsx",
    r"unified-pl-system\unified_pnl_enterprise_demo.xlsx",
]
for p in xlsx_paths:
    df_trans.to_excel(p, index=False)
    print(f"Saved XLSX: {p}")

# 2. Get canonical records and anomalies from backup
records_src = cur_src.execute("""
    SELECT id, domain, period, line_item, amount, currency, cost_center, dynamic_data
    FROM pl_records
    WHERE upload_id='899540e5-fa49-49e8-b87a-6965b44fd71f'
    ORDER BY id ASC
""").fetchall()

print(f"Found {len(records_src)} source records in backup.")

# Get original anomalies
old_ids = [r[0] for r in records_src]
old_ids_tuple = tuple(old_ids)
anom_rows = cur_src.execute(f"""
    SELECT DISTINCT pl_record_id, anomaly_score, severity, is_anomaly, percentile_rank, status
    FROM anomalies 
    WHERE pl_record_id IN {old_ids_tuple}
""").fetchall()
print(f"Found {len(anom_rows)} distinct anomalies in source backup.")

# Count severity breakdown
sev_counts = {}
for ar in anom_rows:
    sev = ar[2]
    sev_counts[sev] = sev_counts.get(sev, 0) + 1
print(f"Anomaly severity breakdown: {sev_counts}")

target_dbs = [
    r"enterprise_pl.db",
    r"unified-pl-system\enterprise_pl.db",
    r"unified-pl-system\backend\enterprise_pl.db",
]

for target_db in target_dbs:
    con_tgt = sqlite3.connect(target_db)
    cur_tgt = con_tgt.cursor()
    
    # Ensure tables exist
    cur_tgt.execute("""
        CREATE TABLE IF NOT EXISTS pl_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id VARCHAR,
            uploaded_by INTEGER,
            domain VARCHAR,
            period VARCHAR,
            line_item VARCHAR,
            amount FLOAT,
            currency VARCHAR,
            cost_center VARCHAR,
            dynamic_data JSON,
            created_at DATETIME
        )
    """)
    cur_tgt.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id VARCHAR UNIQUE,
            filename VARCHAR,
            file_size_bytes INTEGER,
            user_id INTEGER,
            status VARCHAR,
            created_at DATETIME
        )
    """)
    cur_tgt.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pl_record_id INTEGER,
            anomaly_score FLOAT,
            severity VARCHAR,
            is_anomaly BOOLEAN,
            percentile_rank FLOAT,
            status VARCHAR,
            detected_at DATETIME
        )
    """)
    cur_tgt.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key VARCHAR UNIQUE,
            value VARCHAR
        )
    """)
    
    # Clear current data
    cur_tgt.execute("DELETE FROM pl_records")
    cur_tgt.execute("DELETE FROM uploaded_files")
    cur_tgt.execute("DELETE FROM anomalies")
    
    record_id_map = {}
    for r in records_src:
        old_id, domain, period, line_item, amount, currency, cost_center, dyn_data = r
        cur_tgt.execute("""
            INSERT INTO pl_records (upload_id, uploaded_by, domain, period, line_item, amount, currency, cost_center, dynamic_data, created_at)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (upload_id, domain, period, line_item, amount, currency, cost_center, dyn_data))
        new_id = cur_tgt.lastrowid
        record_id_map[old_id] = new_id
        
    cur_tgt.execute("""
        INSERT INTO uploaded_files (upload_id, filename, file_size_bytes, user_id, status, created_at)
        VALUES (?, 'unified_pnl_enterprise_demo.xlsx', 126378, 1, 'COMPLETED', datetime('now'))
    """, (upload_id,))
    
    # Insert anomalies mapping to new pl_record_id
    inserted_anom = 0
    for ar in anom_rows:
        old_pid, a_score, sev, is_anom, p_rank, st = ar
        new_pid = record_id_map.get(old_pid)
        if new_pid:
            cur_tgt.execute("""
                INSERT INTO anomalies (pl_record_id, anomaly_score, severity, is_anomaly, percentile_rank, status, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (new_pid, a_score, sev, is_anom, p_rank, st))
            inserted_anom += 1
            
    print(f"Target {target_db}: inserted {len(records_src)} records and {inserted_anom} anomalies.")
    
    # Default settings
    settings_dict = {
        "enable_copilot": "true",
        "enable_forecast_engine": "true",
        "enable_recommendations": "true",
        "enable_notifications": "true",
        "active_dataset_id": upload_id,
        "active_dataset_filename": "unified_pnl_enterprise_demo.xlsx",
    }
    for k, v in settings_dict.items():
        cur_tgt.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    con_tgt.commit()
    con_tgt.close()

con_src.close()
print("Restoration complete.")
