import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    os.makedirs('screenshots-stitch', exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1582, "height": 900})
        
        print('Taking Dashboard screenshot...')
        await page.goto('http://127.0.0.1:3103/dashboard.html')
        await page.wait_for_timeout(3000) # wait for charts to render
        await page.screenshot(path='screenshots-stitch/dashboard.png', full_page=True)
        
        print('Taking Departments screenshot...')
        await page.goto('http://127.0.0.1:3103/departments.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots-stitch/departments.png', full_page=True)
        
        print('Taking Anomaly Detection screenshot...')
        await page.goto('http://127.0.0.1:3103/anomalies.html')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots-stitch/anomalies.png', full_page=True)
        
        await browser.close()
        print('Done!')

asyncio.run(main())
