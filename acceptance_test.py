import asyncio
import os
import json
from playwright.async_api import async_playwright

PAGES = [
    "dashboard.html",
    "departments.html",
    "datasets.html",
    "forecast.html",
    "reports.html",
    "workflow.html",
    "anomalies.html",
    "copilot.html",
    "audit.html",
    "settings.html"
]

BASE_URL = "http://127.0.0.1:3003"
API_BASE = "http://127.0.0.1:8000"
RESULTS = {}

async def test_page(page, page_name, token):
    url = f"{BASE_URL}/{page_name}"
    print(f"Testing {page_name}...")
    
    # Pre-inject token
    if token:
        await page.goto(f"{BASE_URL}/")  # Go to origin to set localStorage
        await page.evaluate(f"localStorage.setItem('pl_access_token', '{token}')")
    
    page_result = {
        "url": url,
        "status": 0,
        "console_errors": [],
        "network_errors": [],
        "api_calls": []
    }
    
    # Setup listeners
    page.on("console", lambda msg: page_result["console_errors"].append(msg.text) if msg.type == "error" else None)
    page.on("requestfailed", lambda request: page_result["network_errors"].append(request.url))
    
    def handle_response(response):
        page_result["api_calls"].append({
            "url": response.url,
            "status": response.status
        })
        if "/api/" in response.url:
            if response.status >= 400:
                page_result["network_errors"].append(f"API Error {response.status}: {response.url}")
    
    page.on("response", handle_response)
    
    # Navigate
    try:
        response = await page.goto(url, wait_until="networkidle", timeout=10000)
        page_result["status"] = response.status if response else 500
        
        # Wait a bit for JS to populate
        await asyncio.sleep(2)
        
        # Take screenshot
        os.makedirs("evidence", exist_ok=True)
        screenshot_path = f"evidence/{url_path.replace('.html', '')}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        page_result["screenshot"] = screenshot_path
        
    except Exception as e:
        page_result["status"] = "TIMEOUT_OR_ERROR"
        page_result["error_msg"] = str(e)
        
    return page_result

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # 1. Login
        login_page = await context.new_page()
        await login_page.goto(f"{BASE_URL}/login.html")
        
        # Fill login form (assuming id or name attributes exist)
        # We can just fill by input type for simplicity if they are unique
        await login_page.fill('input[type="text"], input[name="username"]', 'admin')
        await login_page.fill('input[type="password"]', 'admin123')
        await login_page.check('input[id="remember"]')
        await login_page.click('button[type="submit"]')
        
        # Wait for redirect to dashboard
        token = None
        try:
            await login_page.wait_for_url('**/dashboard.html', timeout=5000)
            print("Login successful!")
            token = await login_page.evaluate("localStorage.getItem('pl_access_token')")
        except Exception as e:
            print("Login failed or timed out waiting for redirect:", e)
            await login_page.screenshot(path="evidence/login_failed.png")
            
        await login_page.close()
        
        # 2. Test Pages using the authenticated context
        for p_name in PAGES:
            page = await context.new_page()
            res = await test_page(page, p_name, token)
            RESULTS[p_name] = res
            await page.close()
            
        await browser.close()
        
    with open("test_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    print("Testing complete. Results written to test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
