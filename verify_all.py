"""
Programmatic verification of all pages and API endpoints
"""
import urllib.request, json, sys, os

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:3000'
API = 'http://127.0.0.1:8000'

pages = [
    'dashboard.html', 'departments.html', 'datasets.html', 'forecast.html',
    'anomalies.html', 'copilot.html', 'workflow.html', 'reports.html',
    'audit.html', 'settings.html'
]

print("=" * 60)
print("  PAGE VERIFICATION")
print("=" * 60)
all_ok = True
for p in pages:
    try:
        r = urllib.request.urlopen(f'{BASE}/{p}', timeout=5)
        content = r.read().decode()
        checks = {
            'sidebar': 'id="sidebar-container"' in content,
            'shell':   'shell.js' in content,
            'echarts': 'echarts' in content,
            'wiring':  '_wiring.js' in content,
        }
        failed = [k for k, v in checks.items() if not v]
        status = "PASS" if not failed else f"FAIL (missing: {', '.join(failed)})"
        if failed:
            all_ok = False
        print(f"  {p:<30} {status}")
    except Exception as e:
        print(f"  {p:<30} ERROR: {e}")
        all_ok = False

print()
print("=" * 60)
print("  API ENDPOINT VERIFICATION")
print("=" * 60)

# Get a token first
try:
    login_data = json.dumps({'username': 'admin', 'password': 'Admin@123'}).encode()
    req = urllib.request.Request(f'{API}/api/v1/auth/login', data=login_data,
        headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=5)
    token_data = json.loads(resp.read())
    token = token_data.get('access_token', '')
    print(f"  Login: {'OK' if token else 'FAILED'}")
except Exception as e:
    print(f"  Login: ERROR: {e}")
    token = ''

def api_check(path, token=''):
    try:
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        req = urllib.request.Request(f'{API}{path}', headers=headers)
        r = urllib.request.urlopen(req, timeout=5)
        data = json.loads(r.read())
        has_data = bool(data)
        return f"OK ({type(data).__name__})"
    except Exception as e:
        return f"ERROR: {e}"

endpoints = [
    '/api/v1/pl/summary',
    '/api/v1/pl/departments',
    '/api/v1/pl/charts',
    '/api/v1/recommendations',
    '/api/v1/anomalies/',
    '/api/v1/anomalies/trend',
    '/api/v1/system/health',
    '/api/v1/system/ready',
]
for ep in endpoints:
    result = api_check(ep, token)
    print(f"  {ep:<40} {result}")

print()
print("=" * 60)
print(f"  OVERALL: {'ALL PASS' if all_ok else 'SOME FAILURES - see above'}")
print("=" * 60)
