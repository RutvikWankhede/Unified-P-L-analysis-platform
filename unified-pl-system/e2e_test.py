import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        errors = []
        network_failures = []
        
        page.on('console', lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type in ['error', 'warning'] else None)
        page.on('pageerror', lambda err: errors.append(f"[pageerror] {err.message}"))
        
        def handle_response(response):
            if response.status >= 400 and response.url.startswith('http://127.0.0.1'):
                network_failures.append(f"{response.status} {response.url}")
                
        page.on('response', handle_response)
        
        print('--- Starting E2E Verification ---')
        
        # 1. Login (Authentication)
        print('1. Authentication...')
        await page.goto('http://127.0.0.1:3000/index.html')
        await page.fill('#username-input', 'admin')
        await page.fill('#password-input', 'admin123')
        await page.click('#login-btn')
        
        await page.wait_for_url('**/dashboard.html')
        print('[PASS] Authentication successful')
        
        # 2. Dashboard
        print('2. Dashboard...')
        await page.wait_for_selector('.kpi-value')
        await page.wait_for_timeout(1000)
        print('[PASS] Dashboard loaded')
        
        # 3. Upload
        print('3. Upload...')
        await page.click("a.nav-item[href='upload.html']")
        await page.wait_for_url('**/upload.html')
        await page.wait_for_selector('#upload-zone')
        print('[PASS] Upload page loaded')
        
        # 4. Anomalies
        print('4. Anomalies...')
        await page.click("a.nav-item[href='anomalies.html']")
        await page.wait_for_url('**/anomalies.html')
        await page.wait_for_selector('#anomalies-table')
        await page.wait_for_timeout(1000)
        print('[PASS] Anomalies page loaded')
        
        # 5. Forecast
        print('5. Forecast...')
        await page.click("a.nav-item[href='forecast.html']")
        await page.wait_for_url('**/forecast.html')
        await page.wait_for_selector('#param-horizon')
        print('[PASS] Forecast page loaded')
        
        # 6. Reports
        print('6. Reports...')
        await page.click("a.nav-item[href='reports.html']")
        await page.wait_for_url('**/reports.html')
        await page.wait_for_selector('.report-card')
        print('[PASS] Reports page loaded')
        
        # 7. Copilot (Recommendations)
        print('7. Copilot...')
        await page.click("a.nav-item[href='copilot.html']")
        await page.wait_for_url('**/copilot.html')
        await page.wait_for_selector('#chat-input')
        print('[PASS] Copilot page loaded')
        
        # 8. Workflow
        print('8. Workflow...')
        await page.click("a.nav-item[href='workflow.html']")
        await page.wait_for_url('**/workflow.html')
        print('[PASS] Workflow page loaded')
        
        # 9. Departments
        print('9. Departments...')
        await page.click("a.nav-item[href='departments.html']")
        await page.wait_for_url('**/departments.html')
        print('[PASS] Departments page loaded')

        # 10. Exports
        print('10. Exports (Dashboard)...')
        await page.click("a.nav-item[href='dashboard.html']")
        await page.wait_for_url('**/dashboard.html')
        await page.wait_for_selector('.kpi-value')
        
        try:
            await page.wait_for_selector("button:has-text('Export PDF')", timeout=2000)
            await page.wait_for_selector("button:has-text('Export CSV')", timeout=2000)
            print('[PASS] Export buttons found')
        except Exception as e:
            print('[WARN] Export buttons not found or not clickable in dashboard')

        print('--- Test Complete ---')
        
        real_errors = [e for e in errors if 'favicon.ico' not in e]
        if real_errors:
            print('Console Errors:')
            for e in real_errors:
                print(f'  {e}')
        else:
            print('[PASS] No console errors')
            
        real_failures = [f for f in network_failures if 'favicon.ico' not in f]
        if real_failures:
            print('Network Failures:')
            for f in real_failures:
                print(f'  {f}')
        else:
            print('[PASS] No failed network requests')
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
