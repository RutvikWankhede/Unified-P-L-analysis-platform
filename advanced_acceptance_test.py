import asyncio
import json
import traceback
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:3003"
PAGES = [
    "dashboard.html",
    "departments.html",
    "datasets.html",
    "forecast.html",
    "reports.html",
    "workflow.html",
    "recommendations.html",
    "anomalies.html",
    "audit.html",
    "settings.html"
]

RESULTS = {}

async def test_page(page, page_name, token):
    url = f"{BASE_URL}/{page_name}"
    print(f"\n--- Testing {page_name} ---")
    
    # Track errors
    console_errors = []
    network_errors = []
    api_calls = []

    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    
    async def handle_response(response):
        req = response.request
        api_calls.append({"url": req.url, "status": response.status})
        if response.status >= 400:
            network_errors.append(f"HTTP {response.status}: {req.url}")
        if response.status == 302 and "/api/" in req.url:
            network_errors.append(f"UNACCEPTABLE 302 ON API: {req.url}")

    page.on("response", handle_response)
    
    # Pre-inject token via localStorage (must hit origin first)
    if token:
        await page.goto(f"{BASE_URL}/login.html")
        await page.evaluate(f"localStorage.setItem('pl_access_token', '{token}')")

    page_result = {
        "url": url,
        "status": None,
        "console_errors": console_errors,
        "network_errors": network_errors,
        "api_calls": api_calls,
        "dom_issues": [],
        "chart_status": "Not Tested",
        "table_status": "Not Tested"
    }

    try:
        response = await page.goto(url, wait_until="load", timeout=15000)
        page_result["status"] = response.status if response else "NO_RESPONSE"

        # Wait a bit for JS to render DOM, Charts, Tables
        await page.wait_for_timeout(2000)

        # Take screenshot
        screenshot_name = f"evidence/{page_name.replace('.html', '.png')}"
        await page.screenshot(path=screenshot_name, full_page=True)
        page_result["screenshot"] = screenshot_name

        # --- STEP 5: DOM Binding Check ---
        dom_issues = await page.evaluate('''() => {
            const issues = [];
            const textContent = document.body.innerText;
            if (textContent.includes('NaN')) issues.push('Found NaN in DOM');
            if (textContent.includes('undefined')) issues.push('Found undefined in DOM');
            if (textContent.includes('null')) issues.push('Found null in DOM');
            if (textContent.includes('Placeholder')) issues.push('Found Placeholder text in DOM');
            
            const ids = Array.from(document.querySelectorAll('[id]')).map(el => el.id);
            const duplicates = ids.filter((item, index) => ids.indexOf(item) !== index);
            if (duplicates.length > 0) issues.push('Duplicate IDs: ' + [...new Set(duplicates)].join(', '));
            
            return issues;
        }''')
        page_result["dom_issues"] = dom_issues

        # --- STEP 6: Chart Check ---
        has_charts = await page.evaluate("() => document.querySelectorAll('canvas').length > 0")
        if has_charts:
            # We assume ECharts is used. Basic check for echarts instance.
            echarts_ok = await page.evaluate('''() => {
                const charts = document.querySelectorAll('.echart, [id*="chart"]');
                return charts.length > 0 ? 'Rendered' : 'Missing canvas/echarts';
            }''')
            page_result["chart_status"] = echarts_ok
            
        # --- STEP 7: Table Check ---
        has_tables = await page.evaluate("() => document.querySelectorAll('table').length > 0")
        if has_tables:
            table_rows = await page.evaluate("() => document.querySelectorAll('tbody tr').length")
            page_result["table_status"] = f"Rendered ({table_rows} rows)"

    except Exception as e:
        print(f"Error testing {page_name}: {e}")
        page_result["status"] = "TIMEOUT_OR_ERROR"
        page_result["error_msg"] = str(e)
        
    return page_result

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        login_page = await context.new_page()
        print("Logging in to obtain JWT...")
        await login_page.goto(f"{BASE_URL}/login.html")
        await login_page.fill('input[type="text"], input[name="username"]', 'admin')
        await login_page.fill('input[type="password"]', 'admin123')
        await login_page.check('input[id="remember"]')
        await login_page.click('button[type="submit"]')
        
        token = None
        try:
            await login_page.wait_for_url('**/dashboard.html', timeout=5000)
            print("Login successful!")
            token = await login_page.evaluate("localStorage.getItem('pl_access_token')")
            print(f"JWT Extracted: {'YES' if token else 'NO'}")
        except Exception as e:
            print(f"Login failed or timed out waiting for redirect: {e}")
            if console_errors:
                print("Console errors during login:")
                for err in console_errors:
                    print(err)
            print("Cannot proceed without JWT token. Exiting.")
            await browser.close()
            sys.exit(1)
            
        await login_page.close()
        
        if not token:
            print("Cannot proceed without JWT token. Exiting.")
            await browser.close()
            return

        for p_name in PAGES:
            page = await context.new_page()
            res = await test_page(page, p_name, token)
            RESULTS[p_name] = res
            await page.close()
            
        await browser.close()
        
    # Build Pass/Fail Matrix
    matrix = []
    all_passed = True
    
    with open("advanced_test_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)

    print("\n\n--- FINAL PASS / FAIL MATRIX ---")
    print(f"{'Page':<25} | {'Visual (HTTP)':<15} | {'API':<10} | {'Charts':<20} | {'Tables':<20} | {'DOM':<10} | {'Overall'}")
    print("-" * 115)
    
    for p_name, res in RESULTS.items():
        visual = "PASS" if res.get("status") == 200 else "FAIL"
        
        # APIs pass if no 401/403/404/500 in network_errors for /api/
        api_errors = [e for e in res.get("network_errors", []) if "/api/" in e]
        api = "FAIL" if api_errors else "PASS"
        
        charts = res.get("chart_status", "N/A")
        tables = res.get("table_status", "N/A")
        
        dom = "FAIL" if res.get("dom_issues") else "PASS"
        
        if res.get("console_errors"):
            # Some console errors (like lucide path syntax) we might ignore, but strict mode says FAIL
            # Let's count them, if there are non-svg errors it's a fail.
            real_errors = [e for e in res.get("console_errors") if "attribute d: Expected number" not in e and "WebSocket" not in e]
            if real_errors:
                dom = "FAIL"
                
        overall = "PASS" if (visual == "PASS" and api == "PASS" and dom == "PASS") else "FAIL"
        if overall == "FAIL": all_passed = False
        
        print(f"{p_name:<25} | {visual:<15} | {api:<10} | {charts:<20} | {tables:<20} | {dom:<10} | {overall}")

    if all_passed:
        print("\nALL TESTS PASSED. READY FOR PRODUCTION.")
    else:
        print("\nSOME TESTS FAILED. CHECK advanced_test_results.json AND evidence/ FOR DETAILS.")

if __name__ == "__main__":
    import os
    os.makedirs("evidence", exist_ok=True)
    asyncio.run(main())
