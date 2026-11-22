// Synthetic auth/transport, real Chromium IndexedDB. No live API or private data.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const clientSource = fs.readFileSync(new URL('../src/fe-express/driverClient.js', import.meta.url), 'utf8');
const storeSource = fs.readFileSync(new URL('../src/utils/feExpressOfflineStore.js', import.meta.url), 'utf8');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const results = [];
try {
  const page = await browser.newPage();
  await page.route('**/*', route => route.fulfill({ contentType: route.request().url().endsWith('.js') ? 'text/javascript' : 'text/html', body: route.request().url().endsWith('driverClient.js') ? clientSource : route.request().url().endsWith('feExpressOfflineStore.js') ? storeSource : '<html>Synthetic driver fixture</html>' }));
  await page.goto('https://driver-fixture.invalid');
  await page.evaluate(async () => {
    window.create = (await import('/fe-express/driverClient.js')).createDriverClient;
    window.check = (value, text) => { if (!value) throw new Error(text); };
    window.rejects = async action => { let failed = false; try { await action(); } catch { failed = true; } check(failed, 'expected rejection'); };
    window.make = (uid, extra = {}) => {
      const env = { connected: true, requests: [], tokens: [], status: 200, identityOwner: `firebase:ai-bs-dashboard:${uid}` };
      env.auth = { currentUser: { uid, getIdToken: async fresh => { env.tokens.push(fresh); return `synthetic-${uid}`; } }, authStateReady: async () => {} };
      env.client = create({ auth: env.auth, subscribeAuth: cb => { env.notify = cb; return () => {}; }, online: () => env.connected, fetchImpl: async (url, options) => {
        env.requests.push({ url, options });
        if (env.pause && options.method === 'POST') await env.pause;
        const identity = url.endsWith('/identity');
        return { status: identity ? 200 : env.status, json: async () => identity ? { owner: env.identityOwner, scope: 'driver_work' } : { load_id: JSON.parse(options.body).load_id, revision: 1 } };
      }, ...extra });
      return env;
    };
  });
  const test = async (name, fn) => { await page.evaluate(fn); results.push({ name, status: 'PASS' }); };
  await test('restrict credential destinations', () => {
    for (const baseUrl of ['https://evil.invalid', 'http://localhost:3001', 'https://api.brettstehouwer.live/path', 'https://name:pass@api.brettstehouwer.live']) {
      let failed = false; try { create({ baseUrl }); } catch { failed = true; } check(failed, baseUrl);
    }
  });
  await test('online Firebase identity enrolls without body owner', async () => {
    window.a = make('driver-a'); await a.client.open();
    check(a.client.getSnapshot().owner.endsWith(':driver-a'), 'owner');
    check(a.requests[0].options.redirect === 'error' && a.requests[0].options.credentials === 'omit' && !a.requests[0].options.body, 'transport policy');
    check(a.tokens.every(Boolean), 'fresh tokens');
  });
  await test('save work and Blob while offline', async () => {
    a.connected = false;
    await a.client.save({ notes: 'synthetic evidence' }, { loadId: 'proof', attachments: [new Blob(['proof'], { type: 'image/png' })] });
    const records = await a.client.list(); check(records.outbox.length === 2 && await records.attachments[0].blob.text() === 'proof', 'durability');
  });
  await test('offline SDK restored same UID reopens durable outbox', async () => {
    await a.client.close(); window.reopen = make('driver-a'); reopen.connected = false; await reopen.client.open();
    const records = await reopen.client.list(); check(records.outbox.length === 2 && records.loads.length === 1, 'reopen');
  });
  await test('unenrolled account cannot open offline', async () => { const other = make('unenrolled'); other.connected = false; await rejects(() => other.client.open()); });
  await test('local admin and wrong Firebase principal rejected', async () => { for (const owner of ['local_admin', 'firebase:ai-bs-dashboard:someone-else']) { const e = make('bad'); e.identityOwner = owner; await rejects(() => e.client.open()); } });
  await test('offline sync retains original outbox', async () => { await rejects(() => reopen.client.sync()); check((await reopen.client.list()).outbox.length === 2, 'outbox lost'); });
  await test('reconnect revalidates owner before posting', async () => {
    reopen.connected = true; reopen.identityOwner = 'firebase:ai-bs-dashboard:other'; await rejects(() => reopen.client.sync());
    check(!reopen.requests.some(r => r.options.method === 'POST'), 'unauthorized post');
  });
  await test('conflicts remain observable and retain evidence', async () => {
    reopen.identityOwner = 'firebase:ai-bs-dashboard:driver-a'; reopen.status = 409; await reopen.client.sync();
    check(reopen.client.getSnapshot().conflicts === 1 && reopen.client.getSnapshot().status === 'conflict', 'missing conflict');
    check((await reopen.client.list()).attachments.length === 1 && reopen.tokens.every(Boolean), 'evidence/fresh token');
    const post = reopen.requests.find(r => r.options.method === 'POST'); check(!Object.hasOwn(JSON.parse(post.options.body), 'owner'), 'body owner');
  });
  await test('account switch revokes pending acknowledgement and preserves operation', async () => {
    window.late = make('late'); await late.client.open(); await late.client.save({ notes: 'late' }, { loadId: 'late' });
    let resume; late.pause = new Promise(resolve => { resume = resolve; });
    const pending = late.client.sync().catch(() => {}); await new Promise(resolve => setTimeout(resolve, 30));
    check(late.requests.some(r => r.options.method === 'POST'), 'POST never reached late acknowledgement fixture');
    late.auth.currentUser = null; late.notify(null); resume(); await pending;
    check(late.client.getSnapshot().status === 'locked', 'not locked');
    const same = make('late'); same.connected = false; await same.client.open(); check((await same.client.list()).outbox.length === 1, 'late ack removed work'); await same.client.close();
  });
  await test('redirect response rejected and observable errors emitted', async () => {
    const e = make('redirect', { fetchImpl: async () => ({ status: 200, redirected: true, json: async () => ({}) }) });
    const states = []; e.client.subscribe(s => states.push(s)); await rejects(() => e.client.open());
    check(states.some(s => s.error?.includes('redirect')), 'error absent'); await e.client.close(); await reopen.client.close();
  });
  await test('reachable-browser network outage reopens enrolled cache; authorization and schema failures never fallback', async () => {
    const seed = make('weak-signal'); await seed.client.open(); await seed.client.save({ notes: 'retained in outage' }, { loadId: 'weak' }); await seed.client.close();
    const outage = make('weak-signal', { fetchImpl: async () => { throw new TypeError('Failed to fetch'); } });
    await outage.client.open(); check(outage.client.getSnapshot().status === 'offline' && (await outage.client.list()).outbox.length === 1, 'network outage locked enrolled work');
    await rejects(() => outage.client.sync()); check((await outage.client.list()).outbox.length === 1, 'outage acknowledged operation'); await outage.client.close();
    const firebaseOutage = make('weak-signal'); firebaseOutage.auth.currentUser.getIdToken = async () => { throw Object.assign(new Error('network'), { code: 'auth/network-request-failed' }); };
    await firebaseOutage.client.open(); check(firebaseOutage.client.getSnapshot().status === 'offline', 'Firebase network outage locked cache'); await firebaseOutage.client.close();
    for (const response of [
      { status: 403, json: async () => ({ detail: 'Forbidden' }) },
      { status: 401, json: async () => ({ detail: 'Unauthorized' }) },
      { status: 200, json: async () => ({ owner: 'local_admin', scope: 'driver_work' }) },
      { status: 200, json: async () => { throw new SyntaxError('Invalid JSON'); } },
    ]) { const denied = make('weak-signal', { fetchImpl: async () => response }); await rejects(() => denied.client.open()); check(!denied.client.getSnapshot().owner, 'denied identity fell back'); await denied.client.close(); }
  });
  assert.equal(results.length, 12);
  console.log(JSON.stringify({ status: 'PASS', checks: results.length, results }, null, 2));
} finally { await browser.close(); }
