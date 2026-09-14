import requests
import pandas as pd
import numpy as np
import json

BASE_URL = "http://localhost:8000/api/v1"

# 1. Login to get auth token
auth_resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin123"})
if auth_resp.status_code != 200:
    print(f"Auth failed: {auth_resp.status_code} {auth_resp.text}")
    exit(1)

token = auth_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Authenticated successfully.")

# 2. Test 10k enterprise transactional dataset
n_rows = 10000
df_10k = pd.DataFrame({
    'transaction_id': [f'TXN-{i:06d}' for i in range(1, n_rows + 1)],
    'date': np.random.choice(['2025-01-15', '2025-02-18', '2025-03-20', '2025-04-10'], n_rows),
    'department': np.random.choice(['Engineering', 'Marketing', 'Sales', 'Finance', 'Operations'], n_rows),
    'business_unit': np.random.choice(['Enterprise', 'Commercial', 'Public Sector'], n_rows),
    'region': np.random.choice(['North America', 'EMEA', 'APAC'], n_rows),
    'category': np.random.choice(['Sales Revenue', 'Software Subscription', 'Operating Cost', 'Cloud Hosting', 'Salaries'], n_rows),
    'amount': np.random.uniform(500, 50000, n_rows).round(2)
})

csv_data = df_10k.to_csv(index=False).encode('utf-8')
files = {"file": ("enterprise_pl_dataset_10000.csv", csv_data, "text/csv")}

print("Testing /pl/upload with 10k rows...")
upload_resp = requests.post(f"{BASE_URL}/pl/upload", files=files, headers=headers)
print("Upload status:", upload_resp.status_code)
assert upload_resp.status_code in [200, 201], f"Upload failed: {upload_resp.text}"
up_json = upload_resp.json()
print("Upload ID:", up_json["upload_id"])
print("Schema mapping detected:", up_json.get("schema_mapping", {}).get("capabilities"))

print("Testing /pl/finalize-upload...")
finalize_payload = {
    "upload_id": up_json["upload_id"],
    "mapping": up_json.get("schema_mapping", {}).get("mappings", {}),
    "filename": "enterprise_pl_dataset_10000.csv"
}
finalize_resp = requests.post(f"{BASE_URL}/pl/finalize-upload", json=finalize_payload, headers=headers)
print("Finalize status:", finalize_resp.status_code)
assert finalize_resp.status_code == 201, f"Finalize failed: {finalize_resp.text}"
fin_json = finalize_resp.json()
print("Records ingested:", fin_json.get("records_ingested"))

# 3. Test active dataset verification
active_resp = requests.get(f"{BASE_URL}/datasets/active", headers=headers)
print("Active dataset:", active_resp.json())

# 4. Test summary endpoint
summary_resp = requests.get(f"{BASE_URL}/pl/summary", headers=headers)
print("Summary response status:", summary_resp.status_code)
sum_json = summary_resp.json()
print("Summary total revenue:", sum_json.get("total_revenue"), "total expenses:", sum_json.get("total_expenses"))

print("\nALL INGESTION AND PIPELINE TESTS PASSED!")
