import asyncio
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.async_api import async_playwright

BASE_URL = 'http://127.0.0.1:3000'
MOCK_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.mock_signature'

async def test_clicks():
    server = ThreadingHTTPServer(('127.0.0.1', 3000), lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=os.path.abspath('frontend_v2'), **kwargs))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_init_script(f"""
            localStorage.setItem("pl_access_token", "{MOCK_TOKEN}");
            sessionStorage.setItem("pl_access_token", "{MOCK_TOKEN}");
        """)
        page = await context.new_page()
        await page.goto(f'{BASE_URL}/dashboard.html')
        await page.wait_for_selector('#main-sidebar')

        # Click Departments
        print("Clicking Departments...", flush=True)
        await page.click('#nav-departments')
        await page.wait_for_url('**/departments.html')
        active_dept = await page.evaluate('() => document.querySelector("#main-sidebar .sidebar-item.active .sidebar-item-text").innerText.trim()')
        print(f"Active on departments.html: {active_dept}", flush=True)
        assert active_dept == 'Departments'

        # Click Anomaly Detection
        print("Clicking Anomaly Detection...", flush=True)
        await page.click('#nav-anomalies')
        await page.wait_for_url('**/anomalies.html')
        active_anom = await page.evaluate('() => document.querySelector("#main-sidebar .sidebar-item.active .sidebar-item-text").innerText.trim()')
        print(f"Active on anomalies.html: {active_anom}", flush=True)
        assert active_anom == 'Anomaly Detection'

        # Click Settings
        print("Clicking Settings...", flush=True)
        await page.click('#nav-settings')
        await page.wait_for_url('**/settings.html')
        active_set = await page.evaluate('() => document.querySelector("#main-sidebar .sidebar-item.active .sidebar-item-text").innerText.trim()')
        print(f"Active on settings.html: {active_set}", flush=True)
        assert active_set == 'Settings'

        # Click Dashboard
        print("Clicking Dashboard...", flush=True)
        await page.click('#nav-dashboard')
        await page.wait_for_url('**/dashboard.html')
        active_dash = await page.evaluate('() => document.querySelector("#main-sidebar .sidebar-item.active .sidebar-item-text").innerText.trim()')
        print(f"Active on dashboard.html: {active_dash}", flush=True)
        assert active_dash == 'Dashboard'

        print("ALL NAVIGATION CLICKS TESTED AND WORKING PERFECTLY!", flush=True)
        await browser.close()
    server.shutdown()

if __name__ == '__main__':
    asyncio.run(test_clicks())
