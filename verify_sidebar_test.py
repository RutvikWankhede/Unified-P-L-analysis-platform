import os
import sys
import time
import json
import asyncio
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
from playwright.async_api import async_playwright

FRONTEND_DIR = os.path.abspath('frontend_v2')
PORT = 3000
BASE_URL = f"http://127.0.0.1:{PORT}"

EXPECTED_MENU_ORDER = [
    ("Dashboard", "dashboard.html"),
    ("Departments", "departments.html"),
    ("Upload / Datasets", "datasets.html"),
    ("Forecast", "forecast.html"),
    ("Anomaly Detection", "anomalies.html"),
    ("AI Copilot", "copilot.html"),
    ("Workflow", "workflow.html"),
    ("Reports", "reports.html"),
    ("Audit Trail", "audit.html"),
    ("Settings", "settings.html"),
]

PAGE_TARGETS = [
    ("dashboard.html", "Dashboard"),
    ("departments.html", "Departments"),
    ("datasets.html", "Upload / Datasets"),
    ("forecast.html", "Forecast"),
    ("anomalies.html", "Anomaly Detection"),
    ("copilot.html", "AI Copilot"),
    ("workflow.html", "Workflow"),
    ("reports.html", "Reports"),
    ("audit.html", "Audit Trail"),
    ("settings.html", "Settings"),
]

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, format, *args):
        pass

def start_server():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.mock_signature"

async def run_tests():
    server = start_server()
    time.sleep(1)

    os.makedirs('evidence', exist_ok=True)
    results = {}
    all_passed = True

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})

        # Inject token before ANY page scripts load
        await context.add_init_script(f"""
            localStorage.setItem('pl_access_token', '{MOCK_TOKEN}');
            sessionStorage.setItem('pl_access_token', '{MOCK_TOKEN}');
        """)

        page = await context.new_page()

        print("=" * 60, flush=True)
        print("VERIFYING GLOBAL UNIFIED P&L SIDEBAR ACROSS ALL 10 PAGES", flush=True)
        print("=" * 60, flush=True)

        for filename, expected_active_label in PAGE_TARGETS:
            url = f"{BASE_URL}/{filename}"
            print(f"\nTesting {filename} (Expected Active: '{expected_active_label}')...", flush=True)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_selector("#main-sidebar", timeout=5000)
                await page.wait_for_selector("#main-sidebar .sidebar-item", timeout=5000)

                # 1. Check Menu Order
                items = await page.eval_on_selector_all("#main-sidebar .sidebar-item", """
                    elements => elements.map(el => ({
                        text: el.querySelector('.sidebar-item-text')?.innerText?.trim(),
                        href: el.getAttribute('href'),
                        isActive: el.classList.contains('active'),
                        hasDot: !!el.querySelector('.sidebar-active-dot')
                    }))
                """)

                count_ok = len(items) == 10
                order_ok = [item['text'] for item in items] == [label for label, _ in EXPECTED_MENU_ORDER]
                active_items = [item for item in items if item['isActive']]
                active_ok = len(active_items) == 1 and active_items[0]['text'] == expected_active_label and active_items[0]['hasDot']

                # Take screenshots for required pages
                if filename in ['dashboard.html', 'departments.html', 'anomalies.html', 'forecast.html']:
                    screenshot_path = f"evidence/{filename.replace('.html', '')}_sidebar.png"
                    sidebar_el = await page.query_selector("#main-sidebar")
                    if sidebar_el:
                        await sidebar_el.screenshot(path=screenshot_path)
                    
                    full_screenshot_path = f"evidence/{filename.replace('.html', '')}_full.png"
                    await page.screenshot(path=full_screenshot_path, full_page=False)
                    print(f"  Captured screenshots: {screenshot_path} and {full_screenshot_path}", flush=True)

                status = count_ok and order_ok and active_ok
                if not status:
                    all_passed = False

                results[filename] = {
                    "passed": status,
                    "item_count": len(items),
                    "order_correct": order_ok,
                    "active_item": active_items[0]['text'] if active_items else None,
                    "active_correct": active_ok,
                }

                print(f"  [OK] Item Count: {len(items)}/10", flush=True)
                print(f"  [OK] Menu Order: {'MATCH' if order_ok else 'MISMATCH'}", flush=True)
                print(f"  [OK] Active State: {active_items[0]['text'] if active_items else 'None'} ({'MATCH' if active_ok else 'FAILED'})", flush=True)

            except Exception as e:
                all_passed = False
                results[filename] = {"passed": False, "error": str(e)}
                print(f"  [ERR] Error testing {filename}: {e}", flush=True)

        await browser.close()

    server.shutdown()

    print("\n" + "=" * 60, flush=True)
    print(f"SUMMARY: {'ALL 10 PAGES PASSED' if all_passed else 'SOME TESTS FAILED'}", flush=True)
    print("=" * 60, flush=True)
    with open('evidence/sidebar_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    return all_passed

if __name__ == '__main__':
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
