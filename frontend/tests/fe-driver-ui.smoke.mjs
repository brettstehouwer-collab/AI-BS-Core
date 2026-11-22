// Composed UI acceptance with synthetic auth/API and actual Chromium IndexedDB.
// This does not establish production Firebase ownership or live server readiness.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { build } = require('../node_modules/esbuild');
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const output = path.resolve('backups/fe_ui_integration_20261114_v01');
fs.mkdirSync(output, { recursive: true });
const authFixture = `
const listeners = new Set();
const user = uid => uid ? {uid, email:'synthetic@fixture.invalid',emailVerified:true,getIdToken:async force=>{window.fixture.tokens.push(force);return 'synthetic:'+uid;}} : null;
export const auth = {currentUser:user(localStorage.getItem('fixture-uid')),authStateReady:async()=>{}};
window.fixture={tokens:[],permissions:0,stopped:0,failRecorder:false,revoked:0,signin(uid){auth.currentUser=user(uid);if(uid)localStorage.setItem('fixture-uid',uid);else localStorage.removeItem('fixture-uid');for(const cb of [...listeners])cb(auth.currentUser);}};
export function onAuthStateChanged(_auth, callback){listeners.add(callback);queueMicrotask(()=>{if(listeners.has(callback))callback(auth.currentUser);});return()=>listeners.delete(callback);}
export async function signOut(){window.fixture.signin(null);}
Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{window.fixture.permissions++;return {getTracks:()=>[{stop:()=>window.fixture.stopped++}]};}}});
window.MediaRecorder=class {constructor(){if(window.fixture.failRecorder)throw new Error('Synthetic recorder constructor failure');this.state='inactive';this.mimeType='audio/webm';}start(){this.state='recording';}stop(){if(this.state!=='recording')return;this.state='inactive';setTimeout(()=>{this.ondataavailable?.({data:new Blob(['synthetic voice'],{type:'audio/webm'})});this.onstop?.();},150);}};
const revoke=URL.revokeObjectURL.bind(URL);URL.revokeObjectURL=url=>{window.fixture.revoked++;revoke(url);};
`;
const bundle = await build({ stdin: { contents: `import React from 'react';import{createRoot}from'react-dom/client';import DriverPortal from './src/fe-express/DriverPortal.jsx';createRoot(document.getElementById('root')).render(<DriverPortal/>);`, resolveDir: path.resolve('frontend'), loader: 'jsx' }, bundle: true, write: false, format: 'iife', plugins: [{ name: 'synthetic-auth-only', setup(builder) {
  builder.onResolve({ filter: /^firebase\/auth$/ }, () => ({ path: 'auth', namespace: 'fixture' }));
  builder.onResolve({ filter: /(^|\/)firebase\.js$/ }, () => ({ path: 'auth', namespace: 'fixture' }));
  builder.onResolve({ filter: /LoginModal\.jsx$/ }, () => ({ path: 'login', namespace: 'fixture' }));
  builder.onResolve({ filter: /accessControl\.js$/ }, () => ({ path: 'allowlist', namespace: 'fixture' }));
  builder.onLoad({ filter: /.*/, namespace: 'fixture' }, ({ path: name }) => ({ loader: 'jsx', resolveDir: path.resolve('frontend'), contents: name === 'auth' ? authFixture : name === 'allowlist' ? `export const ADMIN_EMAILS=['synthetic@fixture.invalid'];export const ADMIN_UIDS=[];` : `import React from 'react';export default function LoginModal(){return <p>Existing account sign in fixture</p>;}` }));
} }] });
const source = bundle.outputFiles[0].text;
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const results = [], consoleErrors = [], expectedNetworkDiagnostics = [], requests = [];
const remote = new Map(), operations = new Map();
let disconnected = false, conflict = false, badAck = '', activePage;
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === 'https://driver-ui.invalid') return route.fulfill({ contentType: url.pathname.endsWith('.js') ? 'text/javascript' : 'text/html', body: url.pathname.endsWith('.js') ? source : '<!doctype html><html><body><div id="root"></div><script src="/fixture.js"></script></body></html>' });
    assert.equal(url.origin, 'https://api.brettstehouwer.live', 'unexpected external request');
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    requests.push({ method: request.method(), path: url.pathname, authorization: request.headers().authorization, body: request.postData() });
    if (disconnected) return route.abort('internetdisconnected');
    const uid = request.headers().authorization?.replace('Bearer synthetic:', '');
    assert.ok(uid, 'missing synthetic credential');
    let status = 200, body;
    if (url.pathname.endsWith('/identity')) body = { owner: `firebase:ai-bs-dashboard:${uid}`, scope: 'driver_work' };
    else if (url.pathname.endsWith('/sync')) {
      const operation = request.postDataJSON(), key = `${uid}:${operation.op_id}`, loadKey = `${uid}:${operation.load_id}`;
      if (operations.has(key)) body = operations.get(key);
      else if (conflict || operation.base_revision !== (remote.get(loadKey)?.revision || 0)) { status = 409; body = { detail: 'Synthetic revision conflict' }; }
      else { body = { load_id: operation.load_id, revision: operation.base_revision + 1 }; remote.set(loadKey, { ...body, payload: operation.payload }); operations.set(key, body); }
    } else if (url.pathname.endsWith('/attachments')) {
      const bytes = request.postDataBuffer(), key = `${uid}:${request.headers()['x-operation-id']}`;
      body = operations.get(key) || { attachment_id: request.headers()['x-operation-id'], sha256: crypto.createHash('sha256').update(bytes).digest('hex'), size: bytes.length, media_type: request.headers()['content-type'] };
      operations.set(key, body);
      if (badAck) body = { ...body, ...(badAck === 'id' ? { attachment_id: 'wrong-operation-id' } : { sha256: '0'.repeat(64) }) };
    } else throw new Error(`Unexpected API path ${url.pathname}`);
    await route.fulfill({ status, headers, contentType: 'application/json', body: JSON.stringify(body) });
  });
  const page = await context.newPage();
  activePage = page; page.setDefaultTimeout(8000);
  page.on('pageerror', error => consoleErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') { const text=message.text(); if (text.includes('net::ERR_INTERNET_DISCONNECTED') || (conflict && text === 'Failed to load resource: the server responded with a status of 409 (Conflict)')) expectedNetworkDiagnostics.push(text); else consoleErrors.push(text); } });
  const waitText = text => page.getByText(text, { exact: true }).waitFor();
  const click = name => page.getByRole('button', { name, exact: true }).click();
  const saved = () => waitText('Saved locally');
  const data = () => page.evaluate(async () => {
    const { FEExpressOfflineStore } = await import('data:text/javascript,' + encodeURIComponent(window.storeModule));
    const uid = localStorage.getItem('fixture-uid'), store = new FEExpressOfflineStore({ owner: 'firebase:ai-bs-dashboard:' + uid, scope: 'driver_work', verified: true });
    try { return { loads: await store.listLoads(), outbox: await store.listOutbox(), attachments: (await store.listAttachments()).map(a => ({ id:a.id, load_id:a.load_id, size:a.blob.size, type:a.blob.type, state:a.state })) }; } finally { await store.close(); }
  });
  const installInspection = () => page.evaluate(value => { window.storeModule = value; }, fs.readFileSync('frontend/src/utils/feExpressOfflineStore.js', 'utf8'));
  const test = async (name, action) => { await action(); results.push({ name, status: 'PASS' }); };
  await page.goto('https://driver-ui.invalid'); await installInspection();
  await test('signed-out UI gates all local work and capture', async () => {
    await waitText('Existing account sign in fixture'); assert.equal(await page.getByRole('button', { name: 'New load', exact: true }).count(), 0); assert.equal(await page.evaluate(() => fixture.permissions), 0); assert.equal(requests.length, 0);
    await page.evaluate(() => fixture.signin('ui-owner')); await waitText('ready');
  });
  await test('five loads retain exactly one durable entry per stable load ID', async () => {
    for (let n=0;n<5;n++) { await click('New load'); await page.getByLabel('Load reference', { exact:true }).fill(`Synthetic load ${n}`); await click('Save locally now'); await saved(); }
    const records = await data(); assert.equal(records.loads.length, 5); assert.equal(new Set(records.loads.map(l=>l.id)).size,5); assert.equal(records.outbox.length,5);
  });
  await test('coalesced autosave preserves original work text and all timestamp fields', async () => {
    await page.getByLabel('Notes', { exact:true }).fill('Original\nnotes  $100'); await page.getByLabel('Delays', {exact:true}).fill('No changes to original delays'); await page.getByLabel('Pay issues',{exact:true}).fill('Original pay concern'); await page.getByLabel('Expenses',{exact:true}).fill('12.34 original'); await page.getByLabel('Original WhatsApp / dispatch text',{exact:true}).fill('WhatsApp\n  raw dispatch text');
    await page.getByLabel('Pickup address',{exact:true}).fill('123 pickup'); await page.getByLabel('Delivery address',{exact:true}).fill('456 delivery'); await page.getByLabel('Pickup appointment',{exact:true}).fill('2026-11-14T09:30'); await page.getByLabel('Delivery appointment',{exact:true}).fill('2026-11-15T10:30'); await saved();
    const records = await data(), load=records.loads.find(l=>l.payload.load_ref==='Synthetic load 4'); assert.equal(records.outbox.length,6); assert.equal(load.payload.notes,'Original\nnotes  $100'); assert.equal(load.payload.dispatch_text,'WhatsApp\n  raw dispatch text'); assert.equal(Object.keys(load.payload).length,14); assert.match(load.payload.pickup_appointment,/Z$/);
  });
  await test('quick arrive and depart stamps save immediately as ISO instants', async () => {
    for (const [name,key] of [['Pickup arrived','pickup_arrival'],['Pickup departed','pickup_departure'],['Delivery arrived','delivery_arrival'],['Delivery departed','delivery_departure']]) { await click(name); await saved(); const load=(await data()).loads.find(l=>l.payload.load_ref==='Synthetic load 4'); assert.match(load.payload[key],/^\d{4}-\d{2}-\d{2}T.*Z$/); assert.ok(Math.abs(Date.now()-Date.parse(load.payload[key]))<10000); }
  });
  await test('selection flushes pending edit and reopens fresh payload', async () => {
    const loads=(await data()).loads, fourth=loads.find(l=>l.payload.load_ref==='Synthetic load 4'), first=loads.find(l=>l.payload.load_ref==='Synthetic load 0');
    await page.locator('label').filter({hasText:/^Notes/}).locator('textarea').fill('fresh selection regression'); await page.locator('select').selectOption(first.id);
    await page.waitForFunction(()=>document.querySelector('input[maxlength]')?.value==='Synthetic load 0');
    await page.locator('select').selectOption(fourth.id);
    await page.waitForFunction(()=>document.querySelector('input[maxlength]')?.value==='Synthetic load 4');
    assert.equal(await page.locator('label').filter({hasText:/^Notes/}).locator('textarea').inputValue(),'fresh selection regression');
  });
  await test('photo and PDF evidence persist in real IndexedDB across reload', async () => {
    await page.getByLabel('Add photos or PDF evidence').setInputFiles([{name:'synthetic.png',mimeType:'image/png',buffer:Buffer.from([137,80,78,71])},{name:'synthetic.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-synthetic')}]); await saved();
    const before=await data(), id=before.loads.find(l=>l.payload.load_ref==='Synthetic load 4').id; assert.equal(before.attachments.length,2);
    await page.reload(); await installInspection(); await waitText('ready'); await page.locator('select').selectOption(id); await page.getByRole('link',{name:'Download original evidence'}).first().waitFor(); assert.equal(await page.getByRole('link',{name:'Download original evidence'}).count(),2); const after=await data(); assert.deepEqual(after.attachments,before.attachments);
  });
  await test('voice permission is explicit and stop holds selection until evidence saves', async () => {
    assert.equal(await page.evaluate(()=>fixture.permissions),0); await click('Record voice note'); await waitText('Recording microphone… Stop to save this voice note locally.'); assert.equal(await page.evaluate(()=>fixture.permissions),1); await click('Stop recording'); assert.equal(await page.locator('select').isDisabled(),true); await page.waitForFunction(()=>!document.querySelector('select')?.disabled); await saved(); assert.equal((await data()).attachments.filter(a=>a.type.startsWith('audio/')).length,1);
  });
  await test('recorder constructor failure closes granted microphone tracks', async () => {
    const before=await page.evaluate(()=>fixture.stopped); await page.evaluate(()=>{fixture.failRecorder=true;}); await click('Record voice note'); await waitText('Synthetic recorder constructor failure'); assert.ok(await page.evaluate(()=>fixture.stopped)>before); await page.evaluate(()=>{fixture.failRecorder=false;});
  });
  await test('offline browser with failed API reopens enrolled work and captures new text', async () => {
    disconnected=true; await page.reload(); await installInspection(); await waitText('offline'); const loads=(await data()).loads; await page.locator('select').selectOption(loads.find(l=>l.payload.load_ref==='Synthetic load 4').id); await page.locator('label').filter({hasText:/^Notes/}).locator('textarea').fill('offline retained text'); await click('Save locally now'); await saved(); assert.equal((await data()).loads.find(l=>l.payload.load_ref==='Synthetic load 4').payload.notes,'offline retained text'); await click('Sync now'); await page.getByRole('alert').waitFor(); assert.ok((await data()).outbox.length>0);
  });
  await test('reconnection uploads causally with idempotent repeated sync', async () => {
    disconnected=false;
    for (const mismatch of ['id','hash']) {
      badAck=mismatch; await click('Sync now'); await waitText('Evidence acknowledgement does not match original attachment');
      const retained=await data(); assert.ok(retained.outbox.some(op=>op.kind==='attachment')); assert.equal(retained.attachments.length,3);
    }
    badAck=''; await page.evaluate(()=>window.dispatchEvent(new Event('online'))); await page.waitForFunction(()=>document.querySelector('.status')?.textContent.includes('0 unsynced operations')); assert.equal((await data()).outbox.length,0); const count=operations.size; await click('Sync now'); await waitText('ready'); assert.equal(operations.size,count); assert.ok(await page.evaluate(()=>fixture.tokens.every(Boolean)));
  });
  await test('conflict retains local text evidence and visible review state', async () => {
    conflict=true; await page.locator('label').filter({hasText:/^Notes/}).locator('textarea').fill('conflicting original'); await click('Save locally now'); await saved(); await click('Sync now'); await waitText('Conflicts need review'); const records=await data(); assert.ok(records.outbox.some(op=>op.state==='conflict')); assert.equal(records.attachments.length,3); assert.equal(records.loads.find(l=>l.payload.load_ref==='Synthetic load 4').payload.notes,'conflicting original');
  });
  await test('account switch clears drafts evidence URLs and owner-specific load list', async () => {
    const revoked=await page.evaluate(()=>fixture.revoked); await page.evaluate(()=>fixture.signin('second-owner')); await waitText('ready'); assert.equal(await page.locator('label').filter({hasText:/^Notes/}).locator('textarea').count(),0); assert.equal(await page.getByRole('link',{name:'Download original evidence'}).count(),0); assert.equal((await data()).loads.length,0); assert.ok(await page.evaluate(()=>fixture.revoked)>revoked); await click('Sign out'); await waitText('Existing account sign in fixture'); assert.equal(consoleErrors.length,0,consoleErrors.join('\n'));
  });
  assert.equal(results.length,12);
  fs.writeFileSync(path.join(output,'ui-smoke.json'),JSON.stringify({status:'PASS',checks:12,results,consoleErrors,expectedNetworkDiagnostics,scope:'Synthetic composed UI; real IndexedDB; no live Firebase/API/private data'},null,2));
  console.log(JSON.stringify({status:'PASS',checks:12,results},null,2));
} catch(error) {
  if (activePage) { await activePage.screenshot({path:path.join(output,'ui-failure.png')}); fs.writeFileSync(path.join(output,'ui-failure.html'),await activePage.content()); }
  fs.writeFileSync(path.join(output,'ui-smoke-failure.json'),JSON.stringify({status:'FAILED',results,error:error.stack,consoleErrors},null,2)); throw error;
} finally { await browser.close(); }
