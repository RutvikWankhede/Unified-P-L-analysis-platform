const puppeteer = require('puppeteer');

(async () => {
    console.log('Launching browser...');
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    // Set viewport to 1280x720 (standard 100% zoom)
    await page.setViewport({ width: 1280, height: 720 });
    
    // Inject token to bypass guardRoute
    console.log('Navigating to login to set origin...');
    await page.goto('http://localhost:3000/login.html');
    await page.evaluate(() => {
        localStorage.setItem('pl_access_token', 'fake_token_for_screenshots');
    });

    console.log('Navigating to pl_dashboard.html...');
    await page.goto('http://localhost:3000/pl_dashboard.html');
    await page.waitForTimeout(2000); // Wait for charts/scripts to run
    await page.screenshot({ path: 'real_dashboard.png', fullPage: true });

    console.log('Navigating to departments.html...');
    await page.goto('http://localhost:3000/departments.html');
    await page.waitForTimeout(3000); // Wait for charts
    await page.screenshot({ path: 'real_departments.png', fullPage: true });

    await browser.close();
    console.log('Screenshots saved as real_dashboard.png and real_departments.png');
})();
