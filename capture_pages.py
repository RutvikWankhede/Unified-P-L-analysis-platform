import asyncio
import os
import json
import urllib.request
from playwright.async_api import async_playwright

os.makedirs('screenshots', exist_ok=True)

async def main():
    # 1. Get access token via API
    login_data = json.dumps({"username": "admin", "password": "wrong_password"}).encode('utf-8')
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.test"
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", 
                                     data=json.dumps({"username": "admin", "password": "admin123"}).encode('utf-8'),
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req)
        res_json = json.loads(resp.read().decode('utf-8'))
        token = res_json.get("access_token") or token
        print("Obtained real auth token from API")
    except Exception as e:
        print("Using standard JWT fallback token:", e)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = await context.new_page()

        # Set localStorage / sessionStorage auth
        await page.goto('http://127.0.0.1:3000/login.html')
        await page.evaluate(f"""() => {{
            localStorage.setItem('pl_access_token', '{token}');
            sessionStorage.setItem('pl_access_token', '{token}');
        }}""")

        # 1. Executive Dashboard
        print("Capturing Executive Dashboard...")
        await page.goto('http://127.0.0.1:3000/dashboard.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots/dashboard_live.png', full_page=True)

        # 2. Department Analysis
        print("Capturing Department Analysis...")
        await page.goto('http://127.0.0.1:3000/departments.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots/departments_live.png', full_page=True)

        # 3. Anomaly Detection
        print("Capturing Anomaly Detection...")
        await page.goto('http://127.0.0.1:3000/anomalies.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots/anomalies_live.png', full_page=True)

        await browser.close()
        print("All 3 screenshots saved to screenshots/")

asyncio.run(main())
