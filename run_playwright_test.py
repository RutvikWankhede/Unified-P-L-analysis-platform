import os
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\HP\.gemini\antigravity-ide\brain\6112750e-1322-4834-9bea-41a26756a2a4\scratch"
os.makedirs(artifact_dir, exist_ok=True)

server_proc = subprocess.Popen(["python", "proxy_server.py"])
print("Starting proxy server...")
time.sleep(3)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Dashboard
        page.goto("http://127.0.0.1:3003/dashboard.html", wait_until="networkidle")
        page.screenshot(path=os.path.join(artifact_dir, "Dashboard.png"), full_page=True)
        print("Captured Dashboard.png")
        
        # Departments
        page.goto("http://127.0.0.1:3003/departments.html", wait_until="networkidle")
        page.screenshot(path=os.path.join(artifact_dir, "Departments.png"), full_page=True)
        print("Captured Departments.png")
        
        # Reports
        page.goto("http://127.0.0.1:3003/reports.html", wait_until="networkidle")
        page.screenshot(path=os.path.join(artifact_dir, "Reports.png"), full_page=True)
        print("Captured Reports.png")
        
        # Forecast
        page.goto("http://127.0.0.1:3003/forecast.html", wait_until="networkidle")
        page.screenshot(path=os.path.join(artifact_dir, "Forecast.png"), full_page=True)
        print("Captured Forecast.png")
        
        browser.close()
except Exception as e:
    print("Playwright failed:", e)
finally:
    server_proc.terminate()
    print("Proxy server terminated.")
