/**
 * verify_links.js -- Sidebar link health checker
 * Usage: node verify_links.js <sidebar_html_file> [base_url]
 */

const fs   = require('fs');
const http = require('http');

if (process.argv.length < 3) {
  process.stderr.write('Usage: node verify_links.js <sidebar_html_file> [base_url]\n');
  process.exit(1);
}

const sidebarPath = process.argv[2];
const BASE_URL    = (process.argv[3] || 'http://127.0.0.1:3000').replace(/\/$/, '');

const html  = fs.readFileSync(sidebarPath, 'utf8');
const hrefs = [...html.matchAll(/href="([^"#][^"]*)"/g)]
  .map(m => m[1])
  .filter(h => !h.startsWith('http') && !h.startsWith('//'));

function fetchStatus(url) {
  return new Promise(resolve => {
    const req = http.get(url, res => {
      res.resume();
      resolve({ status: res.statusCode, ok: res.statusCode === 200 });
    });
    req.on('error', err => resolve({ status: null, error: err.message, ok: false }));
    req.setTimeout(5000, () => { req.destroy(); resolve({ status: 'TIMEOUT', ok: false }); });
  });
}

(async () => {
  const results = [];
  let allOk = true;

  for (const href of hrefs) {
    const url    = BASE_URL + '/' + href.replace(/^\//, '');
    const result = await fetchStatus(url);
    results.push({ href, url, status: result.status, ok: result.ok, error: result.error || null });
    if (!result.ok) allOk = false;
    const icon = result.ok ? '[OK]' : '[FAIL]';
    process.stderr.write('  ' + icon + ' ' + href.padEnd(30) + ' -> ' + (result.status || result.error) + '\n');
  }

  process.stdout.write(JSON.stringify(results, null, 2) + '\n');
  process.exit(allOk ? 0 : 1);
})();