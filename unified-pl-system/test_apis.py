import requests

try:
    login_res = requests.post("http://127.0.0.1:8001/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
        "email": "admin@unifiedpl.com"
    })
    print("Login:", login_res.status_code)
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    summary_res = requests.get("http://127.0.0.1:8001/api/v1/pl/summary", headers=headers)
    print("Summary:", summary_res.status_code)
    
    charts_res = requests.get("http://127.0.0.1:8001/api/v1/pl/charts", headers=headers)
    print("Charts:", charts_res.status_code)
    print(charts_res.text[:200])

except Exception as e:
    print("Error:", e)
