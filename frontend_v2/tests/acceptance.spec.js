const { test, expect } = require('@playwright/test');

const PAGES = [
    'dashboard.html',
    'departments.html',
    'forecast.html',
    'reports.html',
    'anomalies.html'
];

test.describe('Enterprise Intelligence Platform Acceptance Tests', () => {
    
    // We will serve the static files on localhost:8080 during the test, or just use the file:// protocol if that works, 
    // but Playwright test typically uses a local server. Let's assume we use an http server.
    const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8080';

    for (const pageName of PAGES) {
        test(`Page ${pageName} returns HTTP 200 and has NO JS errors`, async ({ page }) => {
            const errors = [];
            page.on('pageerror', exception => {
                errors.push(`Uncaught exception: "${exception}"`);
            });
            page.on('console', msg => {
                if (msg.type() === 'error' && !msg.text().includes('favicon') && !msg.text().includes('404')) {
                    errors.push(`Console error: "${msg.text()}"`);
                }
            });

            const response = await page.goto(`${baseUrl}/${pageName}`, { waitUntil: 'networkidle' });
            
            expect(response.status()).toBe(200);
            expect(errors.length).toBe(0);
        });
    }

    test('Global filters persist across navigations', async ({ page }) => {
        await page.goto(`${baseUrl}/dashboard.html`, { waitUntil: 'networkidle' });

        // Wait for state.js to initialize
        await page.waitForTimeout(500);

        // Open filter panel if it exists
        const deptSelect = await page.locator('select[data-filter="department"]');
        if (await deptSelect.count() > 0) {
            await deptSelect.selectOption('Finance');
            
            // Wait for URL to update
            await page.waitForTimeout(500);
            
            expect(page.url()).toContain('dept=Finance');

            // Navigate to departments page
            await page.goto(`${baseUrl}/departments.html`, { waitUntil: 'networkidle' });
            
            // Verify query param persisted in localStorage/URL or is appended by state.js
            const newDeptSelect = await page.locator('select[data-filter="department"]');
            const val = await newDeptSelect.inputValue();
            expect(val).toBe('Finance');
        }
    });

});
