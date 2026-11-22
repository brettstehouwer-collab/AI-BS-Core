import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import vm from 'node:vm';
import { createHash, webcrypto } from 'node:crypto';
import { createRequire } from 'node:module';
import config, { driverShellPlugin } from '../vite.driver.config.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const hash = value => createHash('sha256').update(value).digest('hex');
const source = fs.readFileSync(new URL('../public/driver/sw.js', import.meta.url), 'utf8');
const results = [];
async function check(name, action) { await action(); results.push({ name, status: 'PASS' }); }
const html = '<!doctype html><title>Driver synthetic</title><link rel="stylesheet" href="/css/driver.123.css"><div id="proof">Public shell</div><script type="module" src="/js/driver.123.js"></script>';
const bundle = {
  'driver/index.html': { type: 'asset', source: html },
  'js/driver.123.js': { type: 'chunk', code: 'window.shellReady=true;', imports: ['js/shared.123.js'], dynamicImports: ['js/lazy.123.js'], viteMetadata: { importedCss: new Set(['css/driver.123.css']), importedAssets: new Set(['assets/evidence.svg']) } },
  'js/shared.123.js': { type: 'chunk', code: 'export const shared=1;', imports: [], dynamicImports: [] },
  'js/lazy.123.js': { type: 'chunk', code: 'export const lazy=1;', imports: [], dynamicImports: [] },
  'css/driver.123.css': { type: 'asset', source: 'body{color:black}' },
  'assets/evidence.svg': { type: 'asset', source: '<svg></svg>' },
  'assets/unrelated-studio.js': { type: 'chunk', code: 'PRIVATE_UNRELATED', imports: [], dynamicImports: [] },
};
const emitted = {};
driverShellPlugin().generateBundle.call({ emitFile: item => { emitted[item.fileName] = item.source; } }, {}, bundle);
const pinned = JSON.parse(emitted['driver/asset-manifest.json']);
await check('retain existing multi-page entries', () => {
  for (const entry of ['main', 'writer', 'chat', 'driver']) assert.ok(config.build.rollupOptions.input[entry]);
});
await check('dependency closure includes dynamic CSS assets and excludes unrelated Studio', () => {
  for (const path of ['driver/index.html', 'js/driver.123.js', 'js/shared.123.js', 'js/lazy.123.js', 'css/driver.123.css', 'assets/evidence.svg']) assert.ok(pinned.assets.some(a => a.url === '/'+path));
  assert.ok(!pinned.assets.some(a => a.url.includes('unrelated')));
  assert.ok(emitted['driver/sw.js'].includes(pinned.version));
});
await check('PWA scope and public favicon are driver-specific', () => {
  const manifest = JSON.parse(fs.readFileSync(new URL('../public/driver/manifest.webmanifest', import.meta.url)));
  assert.equal(manifest.scope, '/driver/'); assert.equal(manifest.start_url, '/driver/');
  assert.equal(manifest.display, 'standalone'); assert.equal(manifest.name, 'FE Express Driver');
});

function worker({ corrupt = false, failure = false, documentStatus = 200 } = {}) {
  const events = {}, stored = new Map(), calls = [];
  let skipped = 0;
  const manifest = { version: 'a'.repeat(64), entry: '/driver/index.html', assets: [
    { url: '/driver/index.html', sha256: hash(html) }, { url: '/js/driver.123.js', sha256: hash('shell') },
    { url: '/css/driver.123.css', sha256: hash('shell') }] };
  const cache = { put: async (url, response) => stored.set(url, response.clone()), match: async url => stored.get(url)?.clone() };
  const fetcher = async (url, options) => {
    calls.push({ url: typeof url === 'string' ? url : url.url, options });
    if (failure && typeof url !== 'string') throw Error('offline');
    if (typeof url !== 'string') return new Response('network document', { status: documentStatus });
    if (url === '/driver/asset-manifest.json') return Response.json(manifest);
    return new Response(url === '/driver/index.html' ? html : corrupt ? 'tampered' : 'shell');
  };
  const context = vm.createContext({ URL, Response, Uint8Array, crypto: webcrypto, fetch: fetcher,
    caches: { open: async () => cache, delete: async () => stored.clear() },
    self: { location: { origin: 'https://fixture.test' }, addEventListener: (name, cb) => { events[name] = cb; }, skipWaiting: () => { skipped++; } } });
  vm.runInContext(source.replace('__DRIVER_BUILD__', manifest.version), context);
  return { events, stored, calls, get skipped() { return skipped; },
    install: async () => { let promise; events.install({ waitUntil: value => { promise = value; } }); await promise; },
    request: async (path, extra = {}) => { let promise; events.fetch({ request: { url: 'https://fixture.test'+path, method: 'GET', mode: 'cors', headers: new Headers(), ...extra }, respondWith: value => { promise = value; } }); return promise; } };
}
await check('install verifies complete pinned shell before committing marker', async () => {
  const w = worker(); await w.install(); assert.equal(w.stored.size, 4);
  assert.ok(w.calls.every(c => c.options.credentials === 'omit' && c.options.redirect === 'error'));
});
await check('corrupt asset rejects installation without offline marker', async () => {
  const w = worker({ corrupt: true }); await assert.rejects(w.install()); assert.equal(w.stored.size, 0);
});
await check('API auth provider mutations and credential requests bypass cache', async () => {
  const w = worker(); await w.install();
  for (const path of ['/api/v1/fe-express/driver-records/loads', '/auth/token', '/provider/result']) assert.equal(await w.request(path), undefined);
  assert.equal(await w.request('/js/driver.123.js', { headers: new Headers({ Authorization: 'Bearer synthetic' }) }), undefined);
  assert.equal(await w.request('/driver/', { method: 'POST', mode: 'navigate' }), undefined);
  assert.equal(w.stored.size, 4);
});
await check('pinned immutable asset serves installed bytes', async () => {
  const w = worker(); await w.install(); const before = w.calls.length;
  assert.equal(await (await w.request('/js/driver.123.js')).text(), 'shell');
  assert.equal(await (await w.request('/css/driver.123.css')).text(), 'shell');
  assert.equal(w.calls.length, before);
});
await check('document HTTP errors never become cached success', async () => {
  for (const documentStatus of [401, 500]) {
    const w = worker({ documentStatus }); await w.install();
    const response = await w.request('/driver/', { mode: 'navigate' });
    assert.equal(response.status, documentStatus);
    assert.equal(await response.text(), 'network document');
    assert.equal(await w.request('/driver/private-record', { mode: 'navigate' }), undefined);
  }
});
await check('activation requires explicit update message and never claims clients', async () => {
  const w = worker(); await w.install(); assert.equal(w.skipped, 0);
  w.events.message({ data: { type: 'unrelated' } }); assert.equal(w.skipped, 0);
  w.events.message({ data: { type: 'ACTIVATE_DRIVER_UPDATE' } }); assert.equal(w.skipped, 1);
  assert.ok(!source.includes('clients.claim'));
});
await check('offline document fallback returns only installed public entry', async () => {
  const w = worker({ failure: true }); await w.install();
  assert.equal(await (await w.request('/driver/', { mode: 'navigate' })).text(), html);
  assert.equal(w.stored.size, 4);
});

const served = new Map(Object.entries(emitted).map(([name, body]) => ['/'+name, body]));
for (const [name, item] of Object.entries(bundle)) served.set('/'+name, item.type === 'chunk' ? item.code : item.source);
for (const name of ['driver/manifest.webmanifest', 'favicon.ico']) served.set('/'+name, fs.readFileSync(new URL('../public/'+name, import.meta.url)));
let status = 200;
const server = http.createServer((request, response) => {
  const path = request.url.split('?')[0];
  if (path === '/driver/' && status !== 200) { response.writeHead(status); response.end('network failure status'); return; }
  const body = served.get(path === '/driver/' ? '/driver/index.html' : path);
  if (body === undefined) { response.writeHead(404); response.end(); return; }
  response.setHeader('Content-Type', path.endsWith('.js') ? 'application/javascript' : path.endsWith('.json') ? 'application/json' : path.endsWith('.css') ? 'text/css' : path.endsWith('.webmanifest') ? 'application/manifest+json' : 'text/html');
  response.end(body);
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(origin+'/driver/');
  await page.evaluate(async () => { await navigator.serviceWorker.register('/driver/sw.js', { scope: '/driver/' }); await navigator.serviceWorker.ready; });
  await page.reload();
  await check('real Chromium offline shell reload succeeds without auth/private data', async () => {
    await context.setOffline(true); await page.reload();
    assert.equal(await page.locator('#proof').textContent(), 'Public shell');
    assert.equal(await page.evaluate(() => window.shellReady), true);
    const urls = await page.evaluate(async () => { const names = await caches.keys(); return (await Promise.all(names.map(async name => (await (await caches.open(name)).keys()).map(r => r.url)))).flat(); });
    assert.ok(urls.every(url => !url.includes('/api/') && !url.includes('/auth/')));
    await context.setOffline(false);
  });
  await check('real Chromium preserves server 401 and 500 for driver documents', async () => {
    for (const code of [401, 500]) {
      status = code; const response = await page.goto(origin+'/driver/');
      assert.equal(response.status(), code); assert.equal(await page.locator('body').textContent(), 'network failure status');
    }
  });
  await context.close();
} finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
console.log(JSON.stringify({ status: 'PASS', checks: results.length, results }, null, 2));
