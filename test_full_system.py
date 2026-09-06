import urllib.request
import json
import sys

def test_full_system():
    base = 'http://127.0.0.1:8000'
    
    # 1. Login
    login_data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
    req = urllib.request.Request(f'{base}/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
    resp = json.loads(urllib.request.urlopen(req).read().decode())
    token = resp['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print('[PASS] Authenticated successfully with JWT')

    # 2. Test Forecast with all aggregations and metrics
    metrics = ['profit', 'revenue', 'expense', 'gross_profit', 'margin_pct']
    aggs = ['daily', 'weekly', 'monthly', 'quarterly', 'half-yearly', 'yearly']
    for m in metrics:
        for a in aggs:
            url = f'{base}/api/v1/pl/forecast?dept=Overall&metric={m}&periods=12&agg={a}'
            req = urllib.request.Request(url, headers=headers)
            res = json.loads(urllib.request.urlopen(req).read().decode())
            assert 'forecast' in res, f'Missing forecast for {m} {a}'
            assert 'has_enough_data' in res, f'Missing has_enough_data for {m} {a}'
            fc_pts = len(res.get('forecast', []))
            hist_pts = len(res.get('historical', []))
            enough = res.get('has_enough_data')
            print(f'[PASS] Forecast metric={m:<12} agg={a:<12} -> has_enough_data={enough}, fc_points={fc_pts}, hist_points={hist_pts}')

    # 3. Test Anomalies Endpoint
    req = urllib.request.Request(f'{base}/api/v1/anomalies/?limit=50', headers=headers)
    anoms = json.loads(urllib.request.urlopen(req).read().decode())
    print(f'[PASS] Anomalies fetched: {len(anoms)} records')

    # 4. Test Summary & Departments for What-If
    req = urllib.request.Request(f'{base}/api/v1/pl/summary', headers=headers)
    summary = json.loads(urllib.request.urlopen(req).read().decode())
    print(f'[PASS] Summary: Revenue={summary.get("total_revenue")}, Profit={summary.get("net_profit")}')

    req = urllib.request.Request(f'{base}/api/v1/pl/departments', headers=headers)
    depts = json.loads(urllib.request.urlopen(req).read().decode())
    dept_list = depts.get('departments', [])
    print(f'[PASS] Active departments ({len(dept_list)}): {dept_list[:4]}...')

    # 5. Test Frontend Pages accessibility
    f_base = 'http://127.0.0.1:3000'
    for page in ['forecast.html', 'anomalies.html', 'what-if.html', 'dashboard.html', 'departments.html']:
        req = urllib.request.urlopen(f'{f_base}/{page}')
        assert req.status == 200, f'Page {page} returned {req.status}'
        print(f'[PASS] Frontend {page} served (HTTP 200)')

    print('\n=============================================')
    print('ALL SYSTEM VALIDATION CHECKS PASSED PERFECTLY!')
    print('=============================================')

if __name__ == '__main__':
    test_full_system()
