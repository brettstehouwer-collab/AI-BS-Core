// Real components, synthetic transport only. No backend listener or providers.
const assert = require('node:assert/strict');
const path = require('node:path');
const esbuild = require('../node_modules/esbuild');
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const bundle = await esbuild.build({
    stdin: { contents: `import React from 'react';import{createRoot}from'react-dom/client';import Dispatcher from './src/components/FEExpressDispatcher.jsx';createRoot(document.getElementById('root')).render(<Dispatcher BACKEND_URL="https://fe-test.invalid" request={window.fetch}/>);`, resolveDir: root, loader: 'jsx' },
    bundle: true, write: false, format: 'iife', logLevel: 'silent', jsx: 'automatic',
    alias: { react: path.dirname(require.resolve('react', { paths: [root] })), 'react-dom': path.dirname(require.resolve('react-dom/package.json', { paths: [root] })) },
    plugins: [{ name: 'application-paths', setup(build) { build.onResolve({ filter: /^\/src\// }, args => ({ path: path.join(root, args.path.slice(1)) })); } }],
  });
  const html = `<div id="root"></div><script>${bundle.outputFiles[0].text.replaceAll('</script', '<\\/script')}</script>`;
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(5000);
  const errors = [], dialogs = [], writes = [];
  const trip = { dispatch_id: 'TEST-TRIP', load_id: 'TEST-LOAD', origin: 'Test origin', destination: 'Test destination', gross_pay: 1000, fuel_cost: 40, tolls_cost: 20, net_profit: 940, broker_name: 'Test broker', status: 'DELIVERED', bol_photo_url: 'local_bol_photo.jpg' };
  const shipments = [];
  const original = Buffer.from('%PDF-1.4\nSYNTHETIC BOL original bytes\n%%EOF');
  let uploaded = null, holdUpload = null, allowUpload = null;
  page.on('pageerror', error => errors.push(error.message));
  page.on('dialog', async dialog => { dialogs.push(dialog.message()); await dialog.accept(dialog.type() === 'prompt' ? '175' : undefined); });
  async function waitUntil(predicate) {
    for (let n = 0; n < 200 && !predicate(); n++) await new Promise(resolve => setTimeout(resolve, 10));
    assert(predicate(), 'Expected asynchronous fixture result');
  }
  await page.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    assert.equal(url.origin, 'https://fe-test.invalid', 'No external connections allowed');
    const json = data => route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) });
    if (url.pathname === '/fixture') return route.fulfill({ contentType: 'text/html', body: html });
    const endpoint = url.pathname.replace('/api/v1/fe-express', '');
    if (request.method() !== 'GET') writes.push(endpoint);
    if (endpoint === '/workspace') return json({ revision: 0, values: { activeSubTab: 'active_dispatches' } });
    if (endpoint === '/loads') return json({ loads: [{ load_id: 'TEST-LOAD', origin_city_state: 'Test origin', dest_city_state: 'Test destination', equipment_type: "26' Box Truck", weight_lbs: 1000, loaded_miles: 200, total_miles: 200, deadhead_miles: 0, flat_rate_pay: 1000, rpm: 5, true_rpm: 5, score: 'Greenlight', priority_tier: 1, vehicle_match: 'BOX_TRUCK', broker_name: 'Test broker', source: 'Saved listing' }] });
    if (endpoint === '/status') return json({ status: 'CONNECTED', total_loads: 0, greenlight_loads: 0 });
    if (endpoint === '/active-dispatches') return json({ dispatches: [trip] });
    if (endpoint === '/drivers') return json({ drivers: [] });
    if (endpoint === '/settlements') return json({ settlements: [] });
    // Old server response strings must not become provider confirmation in UI.
    if (endpoint === '/factoring/submit') return json({ success: true, factoring_package: { submission_id: 'TEST-PREP', status: 'SUBMITTED', expected_payout: 950 } });
    if (endpoint === '/lumper-escrow') return json({ success: true, lumper_escrow: { escrow_id: 'TEST-LUMPER', lumper_amount: 175, status: 'URGENT_ESCROW_COMMENCED' } });
    if (endpoint === '/capacity-broadcast') return json({ success: true, broadcast_result: { broadcast_id: 'TEST-CAPACITY', status: 'BROADCAST_LIVE_ON_5_BOARDS' } });
    if (endpoint === '/blast-bid') return json({ success: true, blast_result: { status: 'PARALLEL_TRANSMISSION_COMPLETE', channels: ['SMS_DISPATCH'], execution_latency_ms: 280, pitch_snippet: 'Synthetic draft for manual review.' } });
    if (endpoint === '/driver-reports/drivers') return json({ drivers: [{ driver_id: 'OWNER-DEVIN', full_name: 'Synthetic driver' }] });
    if (endpoint === '/driver-reports/weekly') return json({ driver: { driver_id: 'OWNER-DEVIN', full_name: 'Synthetic driver' }, week_start: '2026-10-26', week_end: '2026-11-01', days: [], missing_log_dates: [], totals: {}, shipments });
    if (/^\/driver-reports\/shipments\/[^/]+$/.test(endpoint) && request.method() === 'PUT') {
      const data = request.postDataJSON();
      const saved = { ...data, revision: 1, shipment_id: endpoint.split('/').pop(), documents: [], missing_documents: ['rate_confirmation', 'bol'] };
      shipments.push(saved); return json(saved);
    }
    if (/\/documents\//.test(endpoint) && request.method() === 'PUT') {
      uploaded = request.postDataBuffer();
      assert.deepEqual(uploaded, original, 'Upload must retain selected file bytes');
      holdUpload = new Promise(resolve => { allowUpload = resolve; });
      await holdUpload;
      const document = { document_id: endpoint.split('/').pop(), kind: 'bol', filename: 'synthetic-bol.pdf', length: uploaded.length };
      shipments[0].documents.push(document);
      return json({ ...document, sha256: 'synthetic-test-receipt' });
    }
    throw Error('Unexpected synthetic endpoint: ' + endpoint);
  });
  try {
    await page.goto('https://fe-test.invalid/fixture');
    await page.getByRole('button', { name: /Factor Now|Prepare factoring draft/ }).click();
    await waitUntil(() => dialogs.some(text => /prepared locally/i.test(text)));
    assert(dialogs.some(text => /prepared locally/i.test(text)), 'Factoring must report local preparation');
    assert(!dialogs.some(text => /APPROVED FOR SAME-DAY ACH|Direct Deposit:/.test(text)), 'No invented deposit or approval');
    await page.getByRole('button', { name: /lumper/i }).first().click();
    await waitUntil(() => dialogs.some(text => /Lumper request prepared locally/i.test(text)));
    assert(!dialogs.some(text => /ALERT TRANSMITTED|Dispatched via SMS/.test(text)), 'No invented SMS delivery');
    await page.getByRole('button', { name: 'Prepare capacity posting draft', exact: true }).click();
    await page.getByRole('button', { name: 'Save local capacity draft', exact: true }).click();
    await page.getByText('Providers not connected. No load boards received this draft; posting and removal must be handled separately.', { exact: true }).waitFor();
    assert.equal(await page.getByText(/is LIVE across 5 load boards/).count(), 0);
    await page.getByRole('button', { name: 'Done', exact: true }).click();
    await page.getByRole('button', { name: /Live Load Board/ }).click();
    await page.getByRole('button', { name: 'Prepare bid draft', exact: true }).click();
    await page.getByRole('button', { name: 'Save local bid draft', exact: true }).click();
    await page.getByText('Bid draft prepared locally.', { exact: true }).waitFor();
    assert.equal(await page.getByText(/PARALLEL_TRANSMISSION_COMPLETE/).count(), 0);
    await page.getByRole('button', { name: 'Close', exact: true }).click();
    await page.getByRole('button', { name: /Active Hauls/ }).click();
    await page.getByRole('button', { name: /Upload BOL|Shipment paperwork/ }).first().click();
    await page.getByRole('heading', { name: 'Daily logs & weekly driver reports' }).waitFor();
    assert.equal(await page.locator('input[type=file]').count(), 0, 'No file selection before a stored shipment exists');
    await page.getByRole('button', { name: 'Copy selected trip into shipment' }).click();
    assert.equal(await page.getByLabel('Load / job number').inputValue(), 'TEST-LOAD');
    await page.getByRole('button', { name: 'Save shipment assignment', exact: true }).click();
    await page.getByText('Shipment assignment saved. You can now attach its paperwork.', { exact: true }).waitFor();
    await page.getByLabel('Document type').selectOption('bol');
    await page.getByLabel('Choose document').setInputFiles({ name: 'synthetic-bol.pdf', mimeType: 'application/pdf', buffer: original });
    await page.getByRole('button', { name: 'Upload to shipment file' }).click();
    await waitUntil(() => allowUpload);
    assert(allowUpload, 'Expected canonical document request');
    assert.equal(await page.getByText('synthetic-bol.pdf saved with an integrity receipt.', { exact: true }).count(), 0, 'No success before receipt');
    allowUpload();
    await page.getByText('synthetic-bol.pdf saved with an integrity receipt.', { exact: true }).waitFor();
    assert.deepEqual(uploaded, original);
    assert.deepEqual(errors, []);
    assert.equal(writes.filter(p => /documents/.test(p)).length, 1);
    console.log(JSON.stringify({ passed: true, checks: ['factoring local-only', 'SMS local-only', 'capacity local-only', 'bid local-only', 'legacy BOL routes to canonical paperwork', 'explicit reviewed trip copy', 'selected bytes uploaded intact', 'success waits for receipt'], documentBytes: uploaded.length, unexpectedBrowserErrors: errors }));
  } catch (error) {
    console.error(JSON.stringify({ browserErrors: errors, lastDialogs: dialogs, bodyExcerpt: (await page.locator('body').innerText()).slice(-1500) }));
    throw error;
  } finally { if (allowUpload) allowUpload(); await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
