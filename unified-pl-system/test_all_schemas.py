import requests
import pandas as pd
import numpy as np

BASE_URL = "http://localhost:8000/api/v1"

# Auth
auth_resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin123"})
assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
token = auth_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=== Test 1: Wide P&L Schema (Date, Department, Revenue, Expense, Budget) ===")
df_wide = pd.DataFrame({
    'date': ['2025-01-01', '2025-02-01', '2025-03-01', '2025-04-01'],
    'department': ['Sales', 'Engineering', 'Marketing', 'Finance'],
    'Revenue': [100000.0, 120000.0, 95000.0, 110000.0],
    'Expense': [70000.0, 85000.0, 60000.0, 75000.0],
    'Budget': [75000.0, 90000.0, 65000.0, 80000.0]
})
files_wide = {"file": ("wide_pl_dataset.csv", df_wide.to_csv(index=False).encode('utf-8'), "text/csv")}
up_w = requests.post(f"{BASE_URL}/pl/upload", files=files_wide, headers=headers)
assert up_w.status_code in [200, 201], f"Wide upload failed: {up_w.text}"
fin_w = requests.post(f"{BASE_URL}/pl/finalize-upload", json={"upload_id": up_w.json()["upload_id"], "mapping": up_w.json().get("schema_mapping", {}).get("mappings", {}), "filename": "wide_pl_dataset.csv"}, headers=headers)
assert fin_w.status_code == 201, f"Wide finalize failed: {fin_w.text}"
print(f"Wide dataset ingested: {fin_w.json()['records_ingested']} records. OK!")

print("\n=== Test 2: Minimal Transactional (Txn Date, Dept, Amount, Type) ===")
df_txn = pd.DataFrame({
    'Txn Date': ['2025-01-10', '2025-01-12', '2025-01-15'],
    'Dept': ['HR', 'R&D', 'Sales'],
    'Amount': [4500.0, 12000.0, 35000.0],
    'Transaction Type': ['Software Cost', 'Equipment Spend', 'Sales Credit']
})
files_txn = {"file": ("minimal_txn.csv", df_txn.to_csv(index=False).encode('utf-8'), "text/csv")}
up_t = requests.post(f"{BASE_URL}/pl/upload", files=files_txn, headers=headers)
assert up_t.status_code in [200, 201], f"Txn upload failed: {up_t.text}"
fin_t = requests.post(f"{BASE_URL}/pl/finalize-upload", json={"upload_id": up_t.json()["upload_id"], "mapping": up_t.json().get("schema_mapping", {}).get("mappings", {}), "filename": "minimal_txn.csv"}, headers=headers)
assert fin_t.status_code == 201, f"Txn finalize failed: {fin_t.text}"
print(f"Transactional dataset ingested: {fin_t.json()['records_ingested']} records. OK!")

print("\n=== Test 3: Generic Non-Financial Structured Dataset ===")
df_gen = pd.DataFrame({
    'Date': ['2025-01-01', '2025-02-01'],
    'Department': ['IT', 'Admin'],
    'Ticket Count': [14, 28],
    'Location': ['Building A', 'Building B']
})
files_gen = {"file": ("tickets.csv", df_gen.to_csv(index=False).encode('utf-8'), "text/csv")}
up_g = requests.post(f"{BASE_URL}/pl/upload", files=files_gen, headers=headers)
assert up_g.status_code in [200, 201], f"Generic upload failed: {up_g.text}"
fin_g = requests.post(f"{BASE_URL}/pl/finalize-upload", json={"upload_id": up_g.json()["upload_id"], "mapping": up_g.json().get("schema_mapping", {}).get("mappings", {}), "filename": "tickets.csv"}, headers=headers)
assert fin_g.status_code == 201, f"Generic finalize failed: {fin_g.text}"
print(f"Generic dataset ingested: {fin_g.json()['records_ingested']} records. OK!")

print("\n=== ALL SCHEMA DIVERSITY INGESTION TESTS PASSED SUCCESSFULLY! ===")
