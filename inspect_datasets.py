import os
import re
import pandas as pd
import sqlite3

def clean_amount(val):
    if pd.isnull(val):
        return 0.0
    s = str(val).strip()
    s = re.sub(r"[^\d,\.\-\+]", "", s)
    if not s:
        return 0.0
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) != 3:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except:
        return 0.0

# FX Rates commonly used: USD to INR ~83, EUR to INR ~90, GBP to INR ~105, or raw numbers
RATES = {
    'USD': 83.0,
    'EUR': 90.5,
    'GBP': 105.0,
    'INR': 1.0,
}

print("=== 1. Checking unified_pnl_demo_dataset.csv ===")
csv_path1 = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\unified_pnl_demo_dataset.csv"
if os.path.exists(csv_path1):
    df = pd.read_csv(csv_path1)
    df['clean_amt'] = df['amount'].apply(clean_amount)
    df['inr_amt'] = df.apply(lambda r: r['clean_amt'] * RATES.get(str(r.get('currency', 'USD')).strip().upper(), 83.0), axis=1)
    
    print("Row count:", len(df))
    print("Columns:", df.columns.tolist())
    print("Currencies:", df['currency'].value_counts().to_dict())
    print("Transaction types:", df['transaction_type'].value_counts().to_dict() if 'transaction_type' in df else 'None')
    print("Departments:", df['department'].unique().tolist() if 'department' in df else 'None')
    
    rev_raw = df[df['transaction_type'].str.lower() == 'revenue']['clean_amt'].sum() if 'transaction_type' in df else 0
    exp_raw = df[df['transaction_type'].str.lower() == 'expense']['clean_amt'].sum() if 'transaction_type' in df else 0
    print(f"Raw sums: Rev = {rev_raw:,.2f}, Exp = {exp_raw:,.2f}, Diff = {rev_raw - exp_raw:,.2f}")
    
    rev_inr = df[df['transaction_type'].str.lower() == 'revenue']['inr_amt'].sum() if 'transaction_type' in df else 0
    exp_inr = df[df['transaction_type'].str.lower() == 'expense']['inr_amt'].sum() if 'transaction_type' in df else 0
    print(f"INR (converted) sums: Rev = {rev_inr:,.2f} ({rev_inr/1e7:.2f} Cr), Exp = {exp_inr:,.2f} ({exp_inr/1e7:.2f} Cr), Net Profit = {(rev_inr - exp_inr)/1e7:.2f} Cr")
    print(f"Exp - Rev in INR = {(exp_inr - rev_inr)/1e7:.2f} Cr")

print("\n=== 2. Checking backend/demo_dataset.csv ===")
csv_path2 = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\backend\demo_dataset.csv"
if os.path.exists(csv_path2):
    df2 = pd.read_csv(csv_path2)
    df2['clean_amt'] = df2['amount'].apply(clean_amount) if 'amount' in df2 else 0
    df2['inr_amt'] = df2.apply(lambda r: r['clean_amt'] * RATES.get(str(r.get('currency', 'USD')).strip().upper(), 83.0), axis=1) if 'currency' in df2 else df2['clean_amt']
    print("Row count:", len(df2))
    print("Columns:", df2.columns.tolist())
    rev_inr2 = df2[df2['transaction_type'].str.lower() == 'revenue']['inr_amt'].sum() if 'transaction_type' in df2 else 0
    exp_inr2 = df2[df2['transaction_type'].str.lower() == 'expense']['inr_amt'].sum() if 'transaction_type' in df2 else 0
    print(f"INR sums: Rev = {rev_inr2/1e7:.2f} Cr, Exp = {exp_inr2/1e7:.2f} Cr, Net = {(rev_inr2 - exp_inr2)/1e7:.2f} Cr")

print("\n=== 3. Checking 76MB enterprise_pl.db backups ===")
db_paths = [
    r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system_broken_backup\backend\enterprise_pl.db",
    r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\enterprise_pl.db",
]
for db_p in db_paths:
    if os.path.exists(db_p):
        print(f"\nDB: {db_p} ({os.path.getsize(db_p):,} bytes)")
        con = sqlite3.connect(db_p)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print("Tables:", tables)
        for t in tables:
            try:
                cnt = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                print(f"  Table {t}: {cnt} rows")
            except:
                pass
        
        # Check pl_records if present
        if 'pl_records' in tables:
            rows = con.execute("SELECT upload_id, count(*), sum(amount) FROM pl_records GROUP BY upload_id").fetchall()
            print("  pl_records by upload_id:", rows)
            
            # check by line_item or type
            types = con.execute("SELECT line_item, count(*), sum(amount) FROM pl_records GROUP BY line_item").fetchall()
            print("  pl_records by line_item:", types)
            
            # sample currencies
            currs = con.execute("SELECT currency, count(*), sum(amount) FROM pl_records GROUP BY currency").fetchall()
            print("  pl_records by currency:", currs)
        con.close()
