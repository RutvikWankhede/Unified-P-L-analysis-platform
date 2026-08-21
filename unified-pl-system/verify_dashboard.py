import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navigating to login page...")
        await page.goto("http://127.0.0.1:3001/")
        
        print("Entering credentials...")
        await page.fill("input[type='email']", "admin")
        await page.fill("input[type='password']", "admin123")
        
        print("Clicking login...")
        await page.click("button#login-btn")
        
        print("Waiting for dashboard redirect...")
        await page.wait_for_url("**/dashboard.html")
        
        print("Waiting for charts to render...")
        await page.wait_for_selector(".echarts-instance", timeout=10000)
        await page.wait_for_timeout(3000)
        
        print("Capturing dashboard screenshot...")
        await page.screenshot(path="dashboard_final_verify.png", full_page=True)
        
        print("Success! Dashboard loaded and charts rendered.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
