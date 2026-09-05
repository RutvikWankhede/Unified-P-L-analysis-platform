import sqlite3
import pandas as pd
import json
import os

# Connect to the primary backend database
db_path = os.path.abspath("unified-pl-system/backend/enterprise_pl.db")
conn = sqlite3.connect(db_path)

# Query pl_records
df_pl = pd.read_sql_query("SELECT * FROM pl_records", conn)
df_anom = pd.read_sql_query("SELECT * FROM anomalies", conn)
df_rec = pd.read_sql_query("SELECT * FROM recommendations", conn)
df_files = pd.read_sql_query("SELECT * FROM uploaded_files", conn)

print(f"Total PL Records: {len(df_pl)}")
print("Periods:", df_pl['period'].min(), "to", df_pl['period'].max())
print("Unique periods count:", df_pl['period'].nunique())
print("Unique departments (cost_center):", df_pl['cost_center'].unique().tolist())
print("Line items:", df_pl['line_item'].unique().tolist())
print("Currencies:", df_pl['currency'].unique().tolist())

# Check dynamic_data parsing if present
rev = 0
exp = 0
if 'amount' in df_pl.columns:
    # Let's see summary by line_item / category
    print("\nSummary by line_item:")
    print(df_pl.groupby('line_item')['amount'].sum())

# Also inspect demo csv/xlsx
csv_path = os.path.abspath("unified_pnl_enterprise_demo.csv")
if os.path.exists(csv_path):
    df_csv = pd.read_csv(csv_path)
    print(f"\nCSV Dataset ({csv_path}): {len(df_csv)} rows, columns: {list(df_csv.columns)}")
    print("CSV summary:")
    for col in ['Revenue', 'revenue', 'Expense', 'expense', 'Expenses', 'expenses', 'Profit', 'profit', 'Net Profit', 'net_profit']:
        if col in df_csv.columns:
            print(f"  - {col}: sum = {df_csv[col].sum()}")

conn.close()
