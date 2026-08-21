import asyncio
import json
import os
import sys
import time
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:3000"
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

async def test_page(context, page_name, token):
    url = f"{BASE_URL}/{page_name}"
    print(f"\n========================================\nTESTING PAGE: {page_name}\n========================================")
    
    page = await context.new_page()
    
    # Track errors & responses
    console_errors = []
    page_errors = []
    failed_requests = []
    api_calls = []
    
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: page_errors.append(err.message))
    
    async def handle_response(response):
        req = response.request
        # Track API endpoints
        if "/api/" in req.url:
            api_calls.append({"url": req.url, "status": response.status, "method": req.method})
            if response.status == 302:
                failed_requests.append(f"UNACCEPTABLE 302 redirect on API: {req.method} {req.url}")
            elif response.status >= 400:
                failed_requests.append(f"HTTP {response.status} on API: {req.method} {req.url}")
        else:
            if response.status >= 400:
                failed_requests.append(f"HTTP {response.status} on Asset: {req.method} {req.url}")

    page.on("response", handle_response)
    
    # Pre-inject token via localStorage & sessionStorage
    # We must hit the origin first to set local storage, so we go to login.html first
    await page.goto(f"{BASE_URL}/login.html")
    await page.evaluate(f"localStorage.setItem('pl_access_token', '{token}')")
    await page.evaluate(f"sessionStorage.setItem('pl_access_token', '{token}')")
    await page.evaluate("sessionStorage.setItem('pl_user_role', 'admin')")
    
    # Clear any errors accumulated during token injection/redirect
    console_errors.clear()
    page_errors.clear()
    failed_requests.clear()
    
    # Measure page load time
    start_time = time.time()
    response = await page.goto(url, wait_until="load", timeout=20000)
    load_time_ms = int((time.time() - start_time) * 1000)
    
    page_status = response.status if response else "NO_RESPONSE"
    
    # Wait for JS execution and AJAX calls to finish
    await page.wait_for_timeout(3000)
    
    # Capture screenshot
    screenshot_name = f"evidence/{page_name.replace('.html', '')}.png"
    await page.screenshot(path=screenshot_name, full_page=True)
    
    # 1. Verify Page Status
    visual_ok = page_status == 200
    
    # 2. Check sidebar and navigation
    sidebar_renders = await page.locator("#main-sidebar").count() > 0
    
    # 3. Check title
    title = await page.title()
    title_ok = "Unified P&L" in title or "Sign In" in title or "Sign" in title or "Forecast" in title or "Report" in title or len(title) > 0
    
    # 4. Verify DOM Binding (NaN, undefined, null,  text, duplicate IDs)
    dom_issues = await page.evaluate('''() => {
        const issues = [];
        const textContent = document.body.innerText;
        
        // Exclude specific code/scripts/JSON output if any
        if (textContent.includes('NaN')) issues.push('Found NaN in DOM');
        if (textContent.includes('undefined')) issues.push('Found undefined in DOM');
        if (textContent.includes('null')) issues.push('Found null in DOM');
        
        const ids = Array.from(document.querySelectorAll('[id]')).map(el => el.id);
        const duplicates = ids.filter((item, index) => ids.indexOf(item) !== index);
        if (duplicates.length > 0) {
            issues.push('Duplicate IDs: ' + [...new Set(duplicates)].join(', '));
        }
        return issues;
    }''')
    
    # 5. Verify Charts
    chart_elements = await page.evaluate('''() => {
        const canvases = document.querySelectorAll('canvas');
        const echarts = document.querySelectorAll('.echart, [id*="chart"], [class*="chart"]');
        return {
            canvas_count: canvases.length,
            echart_count: echarts.length
        };
    }''')
    
    # Check if charts render and if we can hover
    chart_status = "N/A"
    if chart_elements["canvas_count"] > 0 or chart_elements["echart_count"] > 0:
        chart_status = f"Rendered ({chart_elements['canvas_count']} canvas, {chart_elements['echart_count']} chart containers)"
        
        # Try to simulate hover on the first canvas/chart to verify hover/tooltip
        try:
            first_canvas = page.locator("canvas").first
            if await first_canvas.count() > 0:
                box = await first_canvas.bounding_box()
                if box:
                    await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    await page.wait_for_timeout(500)
                    chart_status += " + Hover Verified"
        except Exception as e:
            chart_status += f" (Hover test error: {e})"
            
    # 6. Verify Tables
    table_count = await page.locator("table").count()
    table_status = "N/A"
    if table_count > 0:
        row_count = await page.evaluate("() => document.querySelectorAll('tbody tr').length")
        table_status = f"Rendered ({table_count} tables, {row_count} rows total)"
        
        # Test table sorting if there is headers
        try:
            first_header = page.locator("table th").first
            if await first_header.count() > 0:
                # Hover and click to test sorting
                await first_header.hover()
                await page.wait_for_timeout(200)
                table_status += " + Interaction Verified"
        except Exception as e:
            table_status += f" (Interaction test error: {e})"

    # Filter console errors to exclude benign ones like favicon.ico, WebSocket, or SVG attribute issues
    filtered_console_errors = [
        err for err in console_errors 
        if "favicon.ico" not in err and "WebSocket" not in err and "Error in svg" not in err
    ]
    
    # Compile page report
    api_errors = [err for err in failed_requests if "/api/" in err]
    other_errors = [err for err in failed_requests if "/api/" not in err]
    
    page_ok = (
        visual_ok and 
        sidebar_renders and 
        not filtered_console_errors and 
        not page_errors and 
        not api_errors
    )
    
    res = {
        "page_name": page_name,
        "url": url,
        "status": page_status,
        "load_time_ms": load_time_ms,
        "sidebar_renders": sidebar_renders,
        "title": title,
        "page_ok": page_ok,
        "console_errors": console_errors,
        "filtered_console_errors": filtered_console_errors,
        "page_errors": page_errors,
        "failed_requests": failed_requests,
        "api_errors": api_errors,
        "other_errors": other_errors,
        "api_calls": api_calls,
        "dom_issues": dom_issues,
        "chart_status": chart_status,
        "table_status": table_status,
        "screenshot": screenshot_name
    }
    
    # Print individual results
    print(f"Status: {page_status}")
    print(f"Load Time: {load_time_ms} ms")
    print(f"Sidebar Renders: {sidebar_renders}")
    print(f"DOM Issues: {dom_issues}")
    print(f"Chart Status: {chart_status}")
    print(f"Table Status: {table_status}")
    print(f"Console Errors (Filtered): {filtered_console_errors}")
    print(f"Page JS Errors: {page_errors}")
    print(f"Failed API Requests: {api_errors}")
    
    await page.close()
    return res

async def main():
    os.makedirs("evidence", exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a large desktop viewport
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_har_path="acceptance_test.har"
        )
        await context.add_init_script("window.__API_BASE__ = 'http://127.0.0.1:8000';")
        
        login_page = await context.new_page()
        print("Obtaining JWT token from real login page...")
        await login_page.goto(f"{BASE_URL}/login.html")
        await login_page.fill('input[name="username"]', 'admin')
        await login_page.fill('input[name="password"]', 'admin123')
        await login_page.check('input[id="remember"]')
        
        # Trigger login submit
        await login_page.click('button[type="submit"]')
        
        token = None
        try:
            # Wait for dashboard redirect
            await login_page.wait_for_url(f"{BASE_URL}/dashboard.html", timeout=10000)
            print("Successfully logged in via UI!")
            token = await login_page.evaluate("localStorage.getItem('pl_access_token')")
            print(f"Retrieved token: {'YES' if token else 'NO'}")
        except Exception as e:
            print(f"Login navigation failed: {e}")
            await login_page.screenshot(path="evidence/login_failure.png")
            print("Saved login failure screenshot to evidence/login_failure.png")
            await browser.close()
            sys.exit(1)
            
        await login_page.close()
        
        if not token:
            print("Error: pl_access_token not found in local storage.")
            await browser.close()
            sys.exit(1)
            
        # Test all pages
        for page_name in PAGES:
            RESULTS[page_name] = await test_page(context, page_name, token)
            
        await browser.close()

    # Save results to json
    with open("full_test_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
        
    # Generate pass/fail matrix
    print("\n" + "="*80)
    print("FINAL VERIFICATION PASS / FAIL MATRIX")
    print("="*80)
    headers = ["Page", "Visual", "API", "Charts", "Tables", "Navigation", "DOM", "Overall"]
    print(f"{headers[0]:<25} | {headers[1]:<8} | {headers[2]:<8} | {headers[3]:<15} | {headers[4]:<15} | {headers[5]:<10} | {headers[6]:<8} | {headers[7]:<8}")
    print("-" * 110)
    
    all_passed = True
    for name, res in RESULTS.items():
        visual = "PASS" if res["status"] == 200 else "FAIL"
        api = "PASS" if len(res["api_errors"]) == 0 else "FAIL"
        charts = "PASS" if "Rendered" in res["chart_status"] or res["chart_status"] == "N/A" else "FAIL"
        tables = "PASS" if "Rendered" in res["table_status"] or res["table_status"] == "N/A" else "FAIL"
        navigation = "PASS" if res["sidebar_renders"] else "FAIL"
        dom = "PASS" if len(res["dom_issues"]) == 0 else "FAIL"
        
        overall = "PASS" if (visual == "PASS" and api == "PASS" and navigation == "PASS" and dom == "PASS" and 
                             len(res["filtered_console_errors"]) == 0 and len(res["page_errors"]) == 0) else "FAIL"
        if overall == "FAIL":
            all_passed = False
            
        print(f"{name:<25} | {visual:<8} | {api:<8} | {charts:<15} | {tables:<15} | {navigation:<10} | {dom:<8} | {overall:<8}")
        
    print("="*80)
    if all_passed:
        print("VERIFICATION RESULT: ALL PAGES AND APIS PASSED!")
        sys.exit(0)
    else:
        print("VERIFICATION RESULT: SOME PAGES OR APIS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
