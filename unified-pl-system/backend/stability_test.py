import requests
import time
import threading

base = 'http://127.0.0.1:8000'
session = requests.Session()

r = session.post(base + '/api/v1/auth/login', json={'username': 'admin', 'password': 'admin123'})
token = r.json()['access_token']
session.headers['Authorization'] = 'Bearer ' + token

print('=== STABILITY TEST: Simulating concurrent browser-like load ===')
print('Running 3 rounds of concurrent heavy requests + health checks...')
print()

page_requests = [
    '/api/v1/pl/summary',
    '/api/v1/pl/charts',
    '/api/v1/pl/forecast',
    '/api/v1/pl/departments/summary',
    '/api/v1/pl/departments/trend',
    '/api/v1/anomalies/',
    '/api/v1/anomalies/trend',
    '/api/v1/recommendations',
]

all_ok = True
for round_num in range(1, 4):
    print('--- Round ' + str(round_num) + '/3 ---')
    results = {}
    errors = {}

    def fetch(path):
        try:
            t0 = time.time()
            resp = session.get(base + path, timeout=60)
            results[path] = (resp.status_code, round(time.time() - t0, 2))
        except Exception as e:
            errors[path] = str(e)

    threads = [threading.Thread(target=fetch, args=(p,)) for p in page_requests]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for path in page_requests:
        if path in errors:
            print('  ERROR  ' + path + ': ' + errors[path])
            all_ok = False
        else:
            code, elapsed = results[path]
            ok = 'OK' if code < 400 else 'FAIL'
            if ok == 'FAIL':
                all_ok = False
            print('  ' + ok + ' ' + str(code) + ' ' + path + ' (' + str(elapsed) + 's)')

    # Health check IMMEDIATELY after concurrent load
    t0 = time.time()
    health = session.get(base + '/api/v1/system/health', timeout=5)
    health_time = round(time.time() - t0, 3)
    health_ok = health.status_code == 200 and health_time < 2.0
    label = 'PASS (fast)' if health_ok else 'FAIL (too slow or error)'
    print('  HEALTH CHECK: ' + str(health.status_code) + ' in ' + str(health_time) + 's -> ' + label)
    if not health_ok:
        all_ok = False
    print()
    time.sleep(2)

print('=== RESULT: ' + ('ALL STABLE - NO CRASH' if all_ok else 'FAILURES DETECTED') + ' ===')
