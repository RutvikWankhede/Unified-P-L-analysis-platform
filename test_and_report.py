import subprocess
import time
import urllib.request
import json

def main():
    print("Starting run.py...")
    proc = subprocess.Popen(["python", "run.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Wait for ready
    ready = False
    for i in range(60):
        try:
            r = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/system/ready", timeout=2)
            if r.status == 200:
                ready = True
                break
        except Exception:
            time.sleep(1)
            
    if not ready:
        print("Backend not ready after 60s")
        proc.kill()
        return

    print("Backend ready. Checking port 3000...")
    # 1. Port 3000
    try:
        netstat = subprocess.check_output("netstat -ano | findstr :3000", shell=True, text=True)
        print("netstat output:")
        print(netstat.strip())
    except Exception as e:
        print(f"netstat failed: {e}")

    # Wait a bit for frontend
    time.sleep(5)

    # 2. Frontend serves new dashboard
    try:
        frontend_html = urllib.request.urlopen('http://127.0.0.1:3000/dashboard.html').read().decode('utf-8')[:200]
        print("Frontend dashboard (200 chars):")
        print(frontend_html)
    except Exception as e:
        print(f"Frontend failed: {e}")

    # 3. Check endpoints
    print("Getting auth token...")
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:8000/api/v1/auth/login', 
            data=json.dumps({'username': 'admin', 'password': 'admin123'}).encode(), 
            headers={'Content-Type': 'application/json'}, 
            method='POST'
        )
        token = json.loads(urllib.request.urlopen(req).read())['access_token']
        
        headers = {'Authorization': 'Bearer ' + token}
        endpoints = ['/api/v1/pl/summary', '/api/v1/pl/charts', '/api/v1/recommendations/']
        for ep in endpoints:
            print(f"Testing {ep} ...")
            t0 = time.time()
            try:
                r = urllib.request.Request(f"http://127.0.0.1:8000{ep}", headers=headers)
                resp = urllib.request.urlopen(r, timeout=15)
                status = resp.status
                resp.read()
            except urllib.error.HTTPError as e:
                status = e.code
            except Exception as e:
                status = str(e)
            t1 = time.time()
            print(f"Endpoint {ep}: Status {status}, Time: {t1-t0:.4f}s")
            
    except Exception as e:
        print(f"Token/Endpoints failed: {e}")

    print("Killing run.py...")
    proc.terminate()
    time.sleep(2)
    proc.kill()
    print("Done.")

if __name__ == "__main__":
    main()
