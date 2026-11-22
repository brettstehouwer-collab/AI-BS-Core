// Trusted headless fixture only. Uses a fresh profile; never opens user state.
const fs = require('node:fs'), path = require('node:path');
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const checkpoint = process.argv[2], phase = process.argv[3], url = new URL(process.argv[4]);
if (!/^C:\\AI-BS\\backups\\notos_demo_seed_\d{8}T\d{6,}Z$/.test(checkpoint) || !/^(red|red_validated|red_final|green|green_final)$/.test(phase) || url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port || ['5173', '8080', '8000', '11434'].includes(url.port) || url.pathname !== '/' || url.search || url.hash || url.username || url.password) throw Error('Only isolated loopback fixture allowed');
const profile = path.join(checkpoint, phase + '.browser-profile'), reportPath = path.join(checkpoint, phase + '.json');
if (fs.existsSync(profile) || fs.existsSync(reportPath)) throw Error('Fresh retained evidence required');
(async () => {
  let context;
  const errors = [], blocked = [];
  try {
    context = await chromium.launchPersistentContext(profile, { executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, chromiumSandbox: true, args: ['--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run'], viewport: { width: 1200, height: 900 } });
    await context.route('**/*', route => { const target = new URL(route.request().url()); if (target.origin === url.origin) return route.continue(); blocked.push(true); return route.abort(); });
    const page = context.pages()[0] || await context.newPage();
    page.on('pageerror', () => errors.push(true));
    await page.goto(url.href, { waitUntil: 'load', timeout: 20000 });
    await page.waitForFunction(() => Boolean(window.__notosFixtureReport), null, { timeout: 30000 });
    const report = await page.evaluate(() => window.__notosFixtureReport);
    if (!Array.isArray(report.results) || report.realBackendRequests !== 0 || report.modelRequests !== 0 || report.vmOperations !== 0) throw Error('Unexpected fixture report');
    const receipt = { ...report, phase, origin: url.origin, browserVersion: context.browser()?.version() || 'persistent system Chromium', pageErrorCount: errors.length, blockedExternalRequestCount: blocked.length, total: report.results.length, passed: report.results.filter(row => row.passed).length, failed: report.results.filter(row => !row.passed).length };
    fs.writeFileSync(reportPath, JSON.stringify(receipt, null, 2), { flag: 'wx' });
    console.log(JSON.stringify({ total: receipt.total, passed: receipt.passed, failed: receipt.failed, fixtureFailure: Boolean(receipt.fixtureFailure), pageErrorCount: errors.length, blockedExternalRequestCount: blocked.length }));
    if (receipt.fixtureFailure || errors.length || blocked.length || (phase.startsWith('red') ? receipt.failed === 0 : receipt.failed !== 0)) process.exitCode = 1;
  } finally { if (context) await context.close(); }
})().catch(() => { console.error(JSON.stringify({ fixtureRunnerFailed: true })); process.exitCode = 1; });
