import requests

BASE_URL = "http://127.0.0.1:8000"

# First login to get the token
login_url = f"{BASE_URL}/api/v1/auth/login"
login_payload = {"username": "admin", "password": "admin123"}
r = requests.post(login_url, json=login_payload)
print("Login status:", r.status_code)
if r.status_code != 200:
    print("Login body:", r.text)
    exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

endpoints = [
    "/api/v1/pl/departments",
    "/api/v1/recommendations",
    "/api/v1/anomalies",
    "/api/v1/auth/audit-logs",
    "/api/v1/system/health",
]

for ep in endpoints:
    url = f"{BASE_URL}{ep}"
    print(f"\nTesting {url}...")
    try:
        res = requests.get(url, headers=headers)
        print("Status code:", res.status_code)
        print("Response body:", res.text[:500])
    except Exception as e:
        print("Error connecting:", e)
