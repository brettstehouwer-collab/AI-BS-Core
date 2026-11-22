// Trusted static-fixture DOM test only. Never opens an existing browser profile.
const fs = require('node:fs'), path = require('node:path');
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const checkpoint = process.argv[2], phase = process.argv[3], url = new URL(process.argv[4]);
if (!/^C:\\AI-BS\\backups\\coding_actor_scope_\d{8}T\d{6,}Z$/.test(checkpoint) || !/^(red|green|strict_green|regression_review|regression_history)$/.test(phase) || url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port || url.port === '5173' || url.pathname !== '/' || url.search || url.hash || url.username || url.password) throw Error('Only the isolated loopback fixture is allowed');
const profile = path.join(checkpoint, 'browser-profile-' + phase), reportPath = path.join(checkpoint, phase + '.browser.json');
if (fs.existsSync(profile) || fs.existsSync(reportPath)) throw Error('Fresh retained fixture profile/report required');
(async () => {
  let context;
  const errors = [], blocked = [];
  try {
    context = await chromium.launchPersistentContext(profile, { executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, chromiumSandbox: true,
      args: ['--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run'], viewport: { width: 1200, height: 900 } });
    await context.route('**/*', route => { const target = new URL(route.request().url()); if (target.origin === url.origin) return route.continue(); blocked.push(target.origin); return route.abort(); });
    const page = context.pages()[0] || await context.newPage(); page.on('pageerror', error => errors.push(error.message.slice(0, 2000)));
    await page.goto(url.href, { waitUntil: 'load', timeout: 20000 });
    await page.waitForFunction(() => document.getElementById('test-report')?.textContent.length > 0, null, { timeout: 30000 });
    const report = await page.evaluate(() => JSON.parse(document.getElementById('test-report').textContent));
    if (report.realBackendRequests !== 0 || report.modelRequests !== 0 || report.vmOperations !== 0 || !Array.isArray(report.results)) throw Error('Unexpected controlled report');
    const record = { url: page.url(), browserVersion: context.browser()?.version() || 'persistent system Chromium', phase, total: report.results.length, passed: report.results.filter(row => row.passed).length, failures: report.results.filter(row => !row.passed), pageErrors: errors, blockedExternalOrigins: blocked, profile, realAccountsUsed: false, realBackendRequests: 0, modelRequests: 0, vmOperations: 0 };
    fs.writeFileSync(reportPath, JSON.stringify(record, null, 2), { flag: 'wx' });
    console.log(JSON.stringify(record, null, 2));
    if (errors.length || blocked.length || (phase === 'red' ? record.failures.length === 0 : record.failures.length !== 0)) process.exitCode = 1;
  } finally { if (context) await context.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
