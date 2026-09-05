import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import re

def clean_amount(val):
    if pd.isnull(val): return 0.0
    s = str(val).strip()
    s = re.sub(r"[^\d,\.\-\+]", "", s)
    if not s: return 0.0
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."): s = s.replace(".", "").replace(",", ".")
        else: s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) != 3: s = s.replace(",", ".")
        else: s = s.replace(",", "")
    try: return float(s)
    except: return 0.0

files = [
    r"unified-pl-system\unified_pnl_demo_dataset.csv",
    r"unified-pl-system\backend\demo_dataset.csv"
]

fx_options = [
    {"name": "Standard (USD=83, EUR=90, GBP=105)", "rates": {"USD": 83.0, "EUR": 90.0, "GBP": 105.0, "INR": 1.0}},
    {"name": "Realistic (USD=83.3, EUR=90.8, GBP=106.2)", "rates": {"USD": 83.3, "EUR": 90.8, "GBP": 106.2, "INR": 1.0}},
    {"name": "Fixed 1:83", "rates": {"USD": 83.0, "EUR": 83.0, "GBP": 83.0, "INR": 1.0}},
    {"name": "Direct USD in Cr", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "INR": 1/83.0}},
]

for f in files:
    if not os.path.exists(f):
        continue
    print(f"\n==========================================")
    print(f"FILE: {f}")
    print(f"==========================================")
    df = pd.read_csv(f)
    df["amt"] = df["amount"].apply(clean_amount) if "amount" in df.columns else 0.0
    
    print(f"Transactions: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    if "currency" in df.columns:
        print(f"Currencies: {df['currency'].value_counts().to_dict()}")
    if "department" in df.columns:
        print(f"Departments ({df['department'].nunique()}): {df['department'].unique().tolist()}")
    if "category" in df.columns:
        print(f"Categories ({df['category'].nunique()}): {df['category'].unique().tolist()}")
    if "date" in df.columns:
        print(f"Date min/max: {df['date'].min()} to {df['date'].max()}")
    if "transaction_type" in df.columns:
        print(f"Types: {df['transaction_type'].value_counts().to_dict()}")
        exp = df[df["transaction_type"].str.lower() == "expense"]
        rev = df[df["transaction_type"].str.lower() == "revenue"]
        print(f"Raw Sums -> Revenue: {rev['amt'].sum():,.2f} | Expense: {exp['amt'].sum():,.2f}")
        
        for fx in fx_options:
            r = fx["rates"]
            df["inr"] = df.apply(lambda row: row["amt"] * r.get(str(row.get("currency", "USD")).strip().upper(), 83.0), axis=1)
            e_inr = df[df["transaction_type"].str.lower() == "expense"]["inr"].sum()
            r_inr = df[df["transaction_type"].str.lower() == "revenue"]["inr"].sum()
            print(f"--- FX: {fx['name']} ---")
            print(f"  Expense:   {e_inr:,.2f}  -->  Rs. {e_inr/1e7:.2f} Cr")
            print(f"  Revenue:   {r_inr:,.2f}  -->  Rs. {r_inr/1e7:.2f} Cr")
            print(f"  Rev - Exp: Rs. {(r_inr - e_inr)/1e7:.2f} Cr")
            print(f"  Exp - Rev: Rs. {(e_inr - r_inr)/1e7:.2f} Cr")
