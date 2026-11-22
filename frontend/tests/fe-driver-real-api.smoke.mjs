// Real driver FastAPI + browser UI/IndexedDB; synthetic Firebase SDK identity only.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { build } = require('../node_modules/esbuild');
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = path.resolve('.'), phase = path.join(root, 'backups/fe_api_composition_20261114_v01');
const attempt = process.env.FE_API_COMPOSITION_ATTEMPT || '';
if (attempt && !/^attempt[2-9]$/.test(attempt)) throw new Error('Unsupported owned attempt name');
const output = attempt ? path.join(phase, attempt) : phase;
fs.mkdirSync(output, { recursive: true });
if (fs.existsSync(path.join(output, 'receipt.json')) || fs.existsSync(path.join(output, 'server-ready.json'))) throw new Error('Preserve prior composition attempt');
const results = [], requests = [], errors = [], cleanup = {};
const prefix = '/api/v1/fe-express/driver-records';
let browser, server, currentPage, disconnected = false, serverPort;
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const sourcePaths = ['frontend/src/fe-express/DriverPortal.jsx', 'frontend/src/fe-express/driverClient.js', 'frontend/src/utils/feExpressOfflineStore.js', 'backend/AI_BS_Backend.py', 'backend/fe_express_owned_records.py', 'backend/security/firebase_auth.py', 'backend/routers/fe_driver_registration.py', 'backend/tests/fixtures/fe_driver_api_server.py'];
const pinSources = () => Object.fromEntries(sourcePaths.map(name => [name, digest(fs.readFileSync(path.join(root, name)))]));
const sourceAtStart = pinSources(), actualBundleInputs = {};
let sourceAtBuild, sourceAtEnd;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(action, message = 'Condition not reached') {
  const end = Date.now() + 12000;
  while (Date.now() < end) { if (await action()) return; await pause(80); }
  throw new Error(message);
}
const fixtureAuth = `
const listeners=new Set();
const user=uid=>uid?{uid,email:uid+'@example.test',emailVerified:true,getIdToken:async()=> 'synthetic:'+uid}:null;
export const auth={currentUser:user(localStorage.getItem('fixture-uid')),authStateReady:async()=>{}};
window.fixture={signin(uid){auth.currentUser=user(uid);if(uid)localStorage.setItem('fixture-uid',uid);else localStorage.removeItem('fixture-uid');for(const f of [...listeners])f(auth.currentUser);}};
export function onAuthStateChanged(_auth,f){listeners.add(f);queueMicrotask(()=>listeners.has(f)&&f(auth.currentUser));return()=>listeners.delete(f);}
export async function signOut(){window.fixture.signin(null);}
`;
const test = async (name, action) => {
  try { await action(); results.push({ name, status: 'PASS' }); }
  catch (error) { results.push({ name, status: 'QUARANTINED', error: error.message }); throw error; }
};
const headers = uid => ({ Authorization: `Bearer synthetic:${uid}` });
async function api(context, route, { uid = 'owner-a', method = 'GET', data, extra = {} } = {}) {
  return context.request.fetch(`http://127.0.0.1:${serverPort}${prefix}${route}`, {
    method, headers: { ...headers(uid), ...extra }, ...(data === undefined ? {} : { data }),
  });
}
async function records(page) {
  return page.evaluate(async source => {
    const { FEExpressOfflineStore } = await import('data:text/javascript,' + encodeURIComponent(source));
    const store = new FEExpressOfflineStore({ owner: 'firebase:ai-bs-dashboard:' + localStorage.getItem('fixture-uid'), scope: 'driver_work', verified: true });
    try {
      const stored = await store.listLoads();
      if (stored.some(x => x._driverMetadata || x.id.startsWith('review:'))) throw new Error('Legacy capture store contains non-load review metadata');
      let journal = [];
      const reviewName = 'aibs-fe-driver-reviews-v1:' + encodeURIComponent(store.owner);
      if ((await indexedDB.databases()).some(x => x.name === reviewName)) {
        const reviewDb = await new Promise((resolve, reject) => { const r = indexedDB.open(reviewName); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
        try { journal = await new Promise((resolve, reject) => { const r = reviewDb.transaction('journal', 'readonly').objectStore('journal').getAll(); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); }); }
        finally { reviewDb.close(); }
      }
      return { loads: stored, journal, outbox: await store.listOutbox(), attachments: (await store.listAttachments()).map(x => ({ id: x.id, load_id: x.load_id, state: x.state, size: x.blob.size, type: x.blob.type })) };
    } finally { await store.close(); }
  }, fs.readFileSync(path.join(root, 'frontend/src/utils/feExpressOfflineStore.js'), 'utf8'));
}
const click = (page, name) => page.getByRole('button', { name, exact: true }).click();
const notes = page => page.locator('label').filter({ hasText: /^Notes/ }).locator('textarea');
async function save(page) { await click(page, 'Save locally now'); await page.getByText('Saved locally', { exact: true }).waitFor(); }
async function remote(context) { const r = await api(context, '/loads'); assert.equal(r.status(), 200); return (await r.json()).loads; }
async function sync(page) { await click(page, 'Sync now'); await until(async () => !(await records(page)).outbox.length, 'Outbox not drained'); }
try {
  const stdout = fs.openSync(path.join(output, 'server.stdout.log'), 'wx');
  const stderr = fs.openSync(path.join(output, 'server.stderr.log'), 'wx');
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => /^(SYSTEMROOT|WINDIR|COMSPEC|PATH|PATHEXT|TEMP|TMP|USERPROFILE|USERNAME|USERDOMAIN|LOCALAPPDATA|APPDATA|PROGRAMDATA|HOMEDRIVE|HOMEPATH)$/i.test(key)));
  server = spawn(path.join(root, 'runtime/recovery-20261110/Scripts/python.exe'), [path.join(root, 'backend/tests/fixtures/fe_driver_api_server.py'), output], { cwd: root, env, windowsHide: true, stdio: ['pipe', stdout, stderr] });
  fs.closeSync(stdout); fs.closeSync(stderr);
  await until(() => fs.existsSync(path.join(output, 'server-ready.json')), 'Fixture server did not publish readiness');
  const ready = JSON.parse(fs.readFileSync(path.join(output, 'server-ready.json'))); serverPort = ready.port;
  const probe = require('node:http');
  await until(() => new Promise(resolve => { const q = probe.get(`http://127.0.0.1:${serverPort}/openapi.json`, r => { r.resume(); resolve(r.statusCode === 200); }); q.on('error', () => resolve(false)); }), 'Fixture API not ready');
  sourceAtBuild = pinSources(); assert.deepEqual(sourceAtBuild, sourceAtStart, 'Composition sources changed before build');
  const bundle = await build({ stdin: { contents: `import React from 'react';import{createRoot}from'react-dom/client';import DriverPortal from './src/fe-express/DriverPortal.jsx';createRoot(document.getElementById('root')).render(<DriverPortal/>);`, resolveDir: path.join(root, 'frontend'), loader: 'jsx' }, bundle: true, write: false, format: 'iife', plugins: [{ name: 'fixture-firebase-only', setup(b) {
    b.onLoad({ filter: /\.[cm]?jsx?$/, namespace: 'file' }, args => {
      const contents = fs.readFileSync(args.path); actualBundleInputs[args.path] = digest(contents);
      return { contents, loader: args.path.endsWith('.jsx') ? 'jsx' : 'js' };
    });
    b.onResolve({ filter: /^firebase\/auth$|(^|\/)firebase\.js$/ }, () => ({ path: 'auth', namespace: 'fixture' }));
    b.onResolve({ filter: /LoginModal\.jsx$/ }, () => ({ path: 'login', namespace: 'fixture' }));
    b.onResolve({ filter: /accessControl\.js$/ }, () => ({ path: 'allow', namespace: 'fixture' }));
    b.onLoad({ filter: /.*/, namespace: 'fixture' }, ({ path: name }) => ({ loader: 'jsx', resolveDir: path.join(root, 'frontend'), contents: name === 'auth' ? fixtureAuth : name === 'allow' ? `export const ADMIN_EMAILS=['owner-a@example.test','owner-b@example.test'];export const ADMIN_UIDS=[];` : `import React from 'react';export default function LoginModal(){return <p>Fixture existing account sign in</p>;}` }));
  } }] });
  fs.writeFileSync(path.join(output, 'browser-fixture.bundle.js'), bundle.outputFiles[0].contents);
  fs.writeFileSync(path.join(output, 'source-provenance.json'), JSON.stringify({ start: sourceAtStart, build: sourceAtBuild, actualEsbuildInputs: actualBundleInputs, bundleSha256: digest(bundle.outputFiles[0].contents), syntheticAuthSha256: digest(fixtureAuth) }, null, 2));
  browser = await chromium.launch({ channel: 'chrome', headless: true });
  async function contextFor(uid = null) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
    if (uid) await context.addInitScript(value => localStorage.setItem('fixture-uid', value), uid);
    await context.route('**/*', async route => {
      const req = route.request(), url = new URL(req.url());
      if (url.hostname === 'ai-bs-dashboard.web.app') return route.fulfill({ contentType: 'text/html', body: `<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script>${bundle.outputFiles[0].text}</script></body></html>` });
      if (!url.pathname.startsWith(prefix)) throw new Error(`Unexpected external fixture request: ${url.hostname}${url.pathname}`);
      if (disconnected) return route.abort('internetdisconnected');
      const requestHeaders = req.headers(), body = req.postDataBuffer();
      const forwardHeaders = Object.fromEntries(Object.entries(requestHeaders).filter(([k]) => ['authorization', 'content-type', 'x-operation-id', 'origin', 'access-control-request-method', 'access-control-request-headers'].includes(k)));
      const response = await context.request.fetch(`http://127.0.0.1:${serverPort}${url.pathname}${url.search}`, { method: req.method(), headers: forwardHeaders, ...(body === null ? {} : { data: body }) });
      requests.push({ method: req.method(), path: url.pathname, status: response.status(), ...(url.pathname.endsWith('/sync') ? { body: req.postDataJSON() } : {}) });
      return route.fulfill({ response });
    });
    const page = await context.newPage(); page.setDefaultTimeout(10000);
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('https://ai-bs-dashboard.web.app');
    return { context, page };
  }
  const first = await contextFor(); const { context, page } = first; currentPage = page;
  await test('real identity admission and signed-out UI gate', async () => {
    const preflight = await context.request.fetch(`http://127.0.0.1:${serverPort}${prefix}/loads/fixture/attachments`, { method: 'OPTIONS', headers: { Origin: 'https://ai-bs-dashboard.web.app', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Authorization, Content-Type, X-Operation-Id' } });
    assert.equal(preflight.status(), 200); assert.equal(preflight.headers()['access-control-allow-origin'], 'https://ai-bs-dashboard.web.app'); assert.match(preflight.headers()['access-control-allow-headers'], /x-operation-id/i);
    const untrusted = await context.request.fetch(`http://127.0.0.1:${serverPort}${prefix}/loads/fixture/attachments`, { method: 'OPTIONS', headers: { Origin: 'https://untrusted.example.invalid', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Authorization, Content-Type, X-Operation-Id' } });
    assert.equal(untrusted.status(), 400); assert.equal(untrusted.headers()['access-control-allow-origin'], undefined);
    await page.getByText('Fixture existing account sign in').waitFor(); assert.equal(await page.getByRole('button', { name: 'New load', exact: true }).count(), 0);
    const denied = await context.request.get(`http://127.0.0.1:${serverPort}${prefix}/identity`); assert.equal(denied.status(), 403);
    await page.evaluate(() => fixture.signin('owner-a')); await page.getByText('ready', { exact: true }).waitFor();
    assert.equal((await (await api(context, '/identity')).json()).owner, 'firebase:ai-bs-dashboard:owner-a');
  });
  await test('five UI loads keep durable IDs without server writes before sync', async () => {
    for (let n = 0; n < 5; n++) { await click(page, 'New load'); await page.getByLabel('Load reference', { exact: true }).fill(`Actual API fixture ${n}`); await save(page); }
    const local = await records(page); assert.equal(local.loads.length, 5); assert.equal(new Set(local.loads.map(x => x.id)).size, 5); assert.equal((await remote(context)).length, 0);
  });
  let selected;
  await test('arrival timestamps and original text survive local capture', async () => {
    await notes(page).fill('Original\n  fixture notes'); await save(page);
    await click(page, 'Pickup arrived'); await page.getByText('Saved locally', { exact: true }).waitFor();
    selected = (await records(page)).loads.find(x => x.payload.load_ref === 'Actual API fixture 4').id;
    const load = (await records(page)).loads.find(x => x.id === selected); assert.equal(load.payload.notes, 'Original\n  fixture notes'); assert.match(load.payload.pickup_arrival, /^\d{4}-\d{2}-\d{2}T.*Z$/);
  });
  const pdf = Buffer.from('%PDF-1.4\nSynthetic composition evidence\n%%EOF');
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=', 'base64');
  await test('evidence persists in IndexedDB across browser reload', async () => {
    await page.getByLabel('Add photos or PDF evidence').setInputFiles([{ name: 'fixture.pdf', mimeType: 'application/pdf', buffer: pdf }, { name: 'fixture.png', mimeType: 'image/png', buffer: png }]);
    await until(async () => (await records(page)).attachments.length === 2); await page.reload(); await page.getByText('ready', { exact: true }).waitFor(); await page.locator('select').selectOption(selected); assert.equal((await records(page)).attachments.length, 2);
  });
  await test('offline reopening retains edits and evidence without API acknowledgement', async () => {
    disconnected = true; await page.reload(); await page.getByText('offline', { exact: true }).waitFor(); await page.locator('select').selectOption(selected);
    await notes(page).fill('Offline actual API text'); await save(page); assert.equal((await records(page)).loads.find(x => x.id === selected).payload.notes, 'Offline actual API text'); assert.ok((await records(page)).outbox.length); assert.equal((await remote(context)).length, 0);
  });
  await test('resumed UI sync commits actual server loads and evidence', async () => {
    disconnected = false; await sync(page); const loads = await remote(context); assert.equal(loads.length, 5); const load = loads.find(x => x.load_id === selected); assert.equal(load.payload.notes, 'Offline actual API text'); assert.equal(load.attachments.length, 2); assert.match(load.payload.pickup_arrival, /Z$/);
  });
  await test('actual operation replay is idempotent and repeated UI sync is empty', async () => {
    const original = requests.find(x => x.method === 'POST' && x.path.endsWith('/sync') && x.status === 200).body; const firstAck = await api(context, '/sync', { method: 'POST', data: original }); const secondAck = await api(context, '/sync', { method: 'POST', data: original }); assert.equal(firstAck.status(), 200); assert.deepEqual(await firstAck.json(), await secondAck.json());
    const before = await remote(context); await sync(page); assert.deepEqual(await remote(context), before);
  });
  await test('real owner filtering blocks foreign load and evidence access', async () => {
    const denied = await api(context, '/identity', { uid: 'invalid' }); assert.equal(denied.status(), 403);
    const other = await api(context, '/loads', { uid: 'owner-b' }); assert.deepEqual(await other.json(), { loads: [] });
    const load = (await remote(context)).find(x => x.load_id === selected), evidence = load.attachments[0]; assert.equal((await api(context, `/loads/${selected}/attachments/${evidence.attachment_id}`, { uid: 'owner-b' })).status(), 404);
  });
  let fresh;
  await test('fresh browser pulls actual remote records without prior local cache', async () => {
    fresh = await contextFor('owner-a'); currentPage = fresh.page; await fresh.page.getByText('ready', { exact: true }).waitFor();
    await until(async () => (await records(fresh.page)).loads.length === 5, 'Remote hydration did not import five loads'); assert.equal(await fresh.page.locator('select option').count(), 6); await fresh.page.locator('select').selectOption(selected); assert.equal(await notes(fresh.page).inputValue(), 'Offline actual API text');
  });
  await test('UI remote evidence download verifies actual server body SHA', async () => {
    const load = (await remote(context)).find(x => x.load_id === selected), meta = load.attachments.find(x => x.media_type === 'application/pdf');
    const response = await api(context, `/loads/${selected}/attachments/${meta.attachment_id}`); assert.equal(response.status(), 200); assert.equal(digest(await response.body()), digest(pdf)); assert.equal(meta.sha256, digest(pdf));
    await fresh.page.getByRole('button', { name: `Download verified evidence ${meta.attachment_id}`, exact: true }).click(); await until(async () => (await records(fresh.page)).attachments.some(x => x.id === meta.attachment_id || x.size === pdf.length));
    const downloadEvent = fresh.page.waitForEvent('download'); await fresh.page.getByRole('link', { name: 'Download original evidence', exact: true }).first().click(); const download = await downloadEvent; const target = path.join(output, 'downloaded-fixture.pdf'); await download.saveAs(target); assert.equal(digest(fs.readFileSync(target)), digest(pdf));
  });
  await test('server change creates preserved local conflict and explicit keep-local resolution', async () => {
    const p = fresh.page; await notes(p).fill('Local concurrent original'); await save(p);
    const old = (await remote(context)).find(x => x.load_id === selected); const changed = await api(context, '/sync', { method: 'POST', data: { op_id: 'fixture-server-change', load_id: selected, base_revision: old.revision, payload: { ...old.payload, notes: 'Server concurrent original' } } }); assert.equal(changed.status(), 200);
    await click(p, 'Sync now'); await p.getByRole('heading', { name: 'Conflicts need review', exact: true }).waitFor();
    assert.ok((await records(p)).outbox.some(x => x.state === 'conflict')); assert.equal(await notes(p).inputValue(), 'Local concurrent original');
    await click(p, 'Pull records for review'); await until(async () => (await p.getByLabel('Server raw fields').textContent()).includes('Server concurrent original'));
    await click(p, 'Keep local fields'); await sync(p); assert.equal((await remote(context)).find(x => x.load_id === selected).payload.notes, 'Local concurrent original'); assert.ok((await records(p)).journal.some(x => x.loadId === selected));
  });
  await test('account switch clears former owner UI and isolates actual server records', async () => {
    await fresh.page.evaluate(() => fixture.signin('owner-b')); await fresh.page.getByText('ready', { exact: true }).waitFor(); assert.equal((await records(fresh.page)).loads.length, 0); assert.equal(await fresh.page.getByRole('link', { name: 'Download original evidence', exact: true }).count(), 0); assert.equal(await fresh.page.getByLabel('Local raw fields').count(), 0); assert.equal((await remote(context)).length, 5); assert.equal(errors.length, 0);
  });
} catch (error) {
  errors.push(error.stack || String(error));
  if (currentPage) await currentPage.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
  process.exitCode = 1;
} finally {
  sourceAtEnd = pinSources();
  const sourcesStable = JSON.stringify(sourceAtStart) === JSON.stringify(sourceAtEnd) && Object.entries(actualBundleInputs).every(([name, pin]) => digest(fs.readFileSync(name)) === pin);
  if (browser) await browser.close();
  if (server) {
    server.stdin.end('STOP\n');
    await Promise.race([new Promise(resolve => server.once('exit', resolve)), pause(10000)]);
    cleanup.wrapperExitCode = server.exitCode;
    cleanup.gracefulStop = server.exitCode === 0;
    if (server.exitCode === null) { server.kill(); cleanup.ownedWrapperKillFallback = true; process.exitCode = 1; }
  }
  const report = { status: results.length === 12 && results.every(x => x.status === 'PASS') && cleanup.gracefulStop && sourcesStable ? 'PASS' : 'FAILED', checks: results, checkCount: results.length, errors, requests, cleanup, sourceAtStart, sourceAtBuild, sourceAtEnd, actualBundleInputs, sourcesStable, fixturePort: serverPort, scope: 'Actual registered FastAPI, principal admission, SQLite, browser UI and IndexedDB; Firebase SDK and sign-in UI fixtures only', realCredentials: false, realPrivateDatabase: false, productionRegistrationOrRoutingChanged: false };
  fs.writeFileSync(path.join(output, 'receipt.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ status: report.status, checks: results.length, output, cleanup }));
}
