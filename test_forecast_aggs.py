import urllib.request
import urllib.parse
import json

base_url = "http://127.0.0.1:8000"

req = urllib.request.Request(
    f"{base_url}/api/v1/auth/login",
    data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read().decode())["access_token"]

headers = {"Authorization": f"Bearer {token}"}

for agg in ["monthly", "half-yearly", "yearly", "weekly", "daily"]:
    for metric in ["profit", "revenue", "expense"]:
        url = f"{base_url}/api/v1/pl/forecast?dept=Overall&metric={metric}&periods=12&agg={agg}"
        r = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(r) as resp:
            data = json.loads(resp.read().decode())
            hist = data.get("historical", [])
            fc = data.get("forecast", [])
            print(f"[{agg} - {metric}] has_enough_data: {data.get('has_enough_data')}, hist len: {len(hist)}, fc len: {len(fc)}")
            if hist:
                print(f"   hist[0]: {hist[0]}")
            if fc:
                print(f"   fc[0]: {fc[0]}")
