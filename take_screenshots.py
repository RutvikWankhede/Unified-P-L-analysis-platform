import asyncio
import os
from playwright.async_api import async_playwright

os.makedirs('screenshots', exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        
        print('Logging in...')
        await page.goto('http://127.0.0.1:3000/login.html')
        await page.fill('#emailField', 'admin')
        await page.fill('#passwordField', 'admin123')
        await page.click('#submitBtn')
        await page.wait_for_timeout(2000)
        
        print('Taking Executive Dashboard screenshot...')
        await page.goto('http://127.0.0.1:3000/dashboard.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots/dashboard_live.png', full_page=True)
        
        print('Taking Department Analysis screenshot...')
        await page.goto('http://127.0.0.1:3000/departments.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots/departments_live.png', full_page=True)
        
        print('Taking Anomaly Detection screenshot...')
        await page.goto('http://127.0.0.1:3000/anomalies.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots/anomalies_live.png', full_page=True)
        
        await browser.close()
        print('Screenshots captured successfully!')

asyncio.run(main())
