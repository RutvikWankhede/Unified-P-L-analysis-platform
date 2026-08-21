import urllib.request
import urllib.parse
import json
import sys

def check_url(url, method='GET', data=None, headers={}):
    try:
        req = urllib.request.Request(url, method=method, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return None, str(e)

print("Testing Frontend...")
status, body = check_url('http://127.0.0.1:8001/index.html')
if status == 200:
    print("[OK] Frontend is healthy (HTTP 200)")
else:
    print(f"[FAIL] Frontend failed. Status: {status}, Error: {body}")
    sys.exit(1)

print("Testing Backend...")
status, body = check_url('http://127.0.0.1:8000/docs')
if status == 200:
    print("[OK] Backend docs are healthy (HTTP 200)")
else:
    print(f"[FAIL] Backend failed. Status: {status}, Error: {body}")
    sys.exit(1)

print("Testing Authentication...")
# The frontend uses /api/v1/auth/login with JSON
auth_data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
status, body = check_url('http://127.0.0.1:8000/api/v1/auth/login', method='POST', data=auth_data, headers=headers)
if status == 200:
    print("[OK] Authentication successful")
else:
    print(f"[FAIL] Authentication failed. Status: {status}, Error: {body}")
    sys.exit(1)

print("\nAll checks passed successfully.")
