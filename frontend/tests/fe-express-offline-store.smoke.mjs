// Real Chromium IndexedDB, synthetic work records only. No backend or providers.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const source = fs.readFileSync(new URL('../src/utils/feExpressOfflineStore.js', import.meta.url), 'utf8');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const results = [];
try {
  const context = await browser.newContext();
  await context.route('**/*', route => route.fulfill({ contentType: route.request().url().endsWith('/store.js') ? 'text/javascript' : 'text/html', body: route.request().url().endsWith('/store.js') ? source : '<html>Offline store fixture</html>' }));
  const page = await context.newPage();
  const boot = async () => {
    await page.goto('https://fe-offline.invalid/fixture');
    await page.evaluate(async () => {
      window.Store = (await import('/store.js')).FEExpressOfflineStore;
      window.binding = { owner: 'synthetic-owner-a', scope: 'driver_work', verified: true };
      window.check = (value, message) => { if (!value) throw new Error(message); };
    });
  };
  const test = async (name, run) => { await run(); results.push({ name, status: 'PASS' }); };
  await boot();
  await test('reject unverified and shared-PIN identities', () => page.evaluate(() => {
    for (const b of [{ ...binding, verified: false }, { ...binding, scope: 'website_pages' }, { ...binding, owner: '' }]) {
      let rejected = false; try { new Store(b); } catch { rejected = true; } check(rejected, 'identity accepted');
    }
  }));
  await test('atomic load and Blob durability across close and foreground reload', async () => {
    await page.evaluate(async () => {
      window.store = new Store(binding);
      for (let n = 0; n < 5; n++) await store.saveLoad({ load_ref: `synthetic-${n}`, pickup_arrival: '2026-11-14T12:00:00-05:00' }, { loadId: `load-${n}`, attachments: [new Blob([`proof-${n}`], { type: 'text/plain' })] });
      await store.close();
    });
    await boot();
    await page.evaluate(async () => {
      window.store = new Store(binding);
      check((await store.listLoads()).length === 5, 'loads lost on reopen');
      const attachments = await store.listAttachments();
      check(attachments.length === 5 && await attachments.find(a => a.load_id === 'load-0').blob.text() === 'proof-0', 'Blob lost');
    });
  });
  await test('owner namespace isolation', () => page.evaluate(async () => {
    const other = new Store({ ...binding, owner: 'synthetic-owner-b' });
    check((await other.listLoads()).length === 0 && (await other.listOutbox()).length === 0, 'owner data leaked');
    await other.close();
  }));
  await test('limits and invalid timestamps preserve prior transaction', () => page.evaluate(async () => {
    const before = (await store.listOutbox()).length;
    for (const args of [[{ pickup_arrival: '2026-11-14T12:00:00' }, {}], [{}, { attachments: [new Blob([new Uint8Array(10 * 1024 * 1024 + 1)])] }], [{}, { attachments: Array.from({ length: 21 }, () => new Blob(['x'])) }], [{}, { attachments: Array.from({ length: 6 }, () => new Blob([new Uint8Array(9 * 1024 * 1024)])) }]]) {
      let rejected = false; try { await store.saveLoad(...args); } catch { rejected = true; } check(rejected, 'invalid save accepted');
    }
    check((await store.listOutbox()).length === before && (await store.listLoads()).length === 5, 'partial commit');
  }));
  await test('interrupted upload replays exact operation and retains Blob', () => page.evaluate(async () => {
    const retry = new Store({ ...binding, owner: 'synthetic-retry' });
    await retry.saveLoad({ notes: 'original' }, { loadId: 'retry', attachments: [new Blob(['receipt'], { type: 'text/plain' })] });
    const seen = [];
    retry.transport = async req => { seen.push(req); throw new Error('synthetic interruption'); };
    await retry.sync().catch(() => {});
    check((await retry.listOutbox()).length === 2 && (await retry.listAttachments())[0].blob.size === 7, 'interrupted data lost');
    for (const invalid of [{ load_id: 'wrong-load', revision: 1 }, { load_id: 'retry', revision: 0 }, { load_id: 'retry', revision: 2 }]) {
      retry.transport = async req => { seen.push(req); return { status: 200, data: invalid }; };
      let rejected = false; try { await retry.sync(); } catch { rejected = true; }
      check(rejected && (await retry.listOutbox()).length === 2 && (await retry.listLoads())[0].revision === 0, 'invalid acknowledgement dequeued work');
    }
    retry.transport = async req => { seen.push(req); return req.body instanceof Blob ? { status: 200, data: { attachment_id: 'remote', sha256: 'a'.repeat(64), size: req.body.size, media_type: req.body.type } } : { status: 200, data: { load_id: req.body.load_id, revision: 1 } }; };
    await retry.sync();
    check(JSON.stringify(seen[0]) === JSON.stringify(seen[1]), 'replay changed');
    check((await retry.listOutbox()).length === 0 && (await retry.listAttachments())[0].state === 'synced', 'sync not acknowledged');
    await retry.close();
  }));
  await test('newer edit survives old response and conflict remains visible', () => page.evaluate(async () => {
    const edits = new Store({ ...binding, owner: 'synthetic-edits' });
    await edits.saveLoad({ notes: 'old' }, { loadId: 'edit' });
    let release; const waiting = new Promise(resolve => { release = resolve; });
    let entered; const enteredPromise = new Promise(resolve => { entered = resolve; });
    edits.transport = async () => { entered(); await waiting; return { status: 200, data: { load_id: 'edit', revision: 1 } }; };
    const syncing = edits.sync(); await enteredPromise;
    await edits.saveLoad({ notes: 'new' }, { loadId: 'edit' }); release(); await syncing;
    const remaining = await edits.listOutbox();
    check(remaining.length === 1 && remaining[0].base_revision === 1 && (await edits.listLoads())[0].payload.notes === 'new', 'new edit overwritten');
    edits.transport = async () => ({ status: 409, data: {} }); await edits.sync();
    check((await edits.listOutbox())[0].state === 'conflict', 'conflict discarded'); await edits.close();
  }));
  await test('revoked owner response cannot acknowledge retained operation', () => page.evaluate(async () => {
    const revoked = new Store({ ...binding, owner: 'synthetic-revoked' });
    await revoked.saveLoad({ notes: 'retain' }, { loadId: 'retained' });
    let release, entered; const wait = new Promise(resolve => { release = resolve; }); const ready = new Promise(resolve => { entered = resolve; });
    revoked.transport = async () => { entered(); await wait; return { status: 200, data: { load_id: 'retained', revision: 1 } }; };
    const pending = revoked.sync().catch(() => {}); await ready; await revoked.close(); release(); await pending;
    const reopened = new Store({ ...binding, owner: 'synthetic-revoked' });
    check((await reopened.listOutbox()).length === 1 && (await reopened.listLoads())[0].revision === 0, 'stale response acknowledged');
    await reopened.close(); await store.close();
  }));
  assert.equal(results.length, 7);
  console.log(JSON.stringify({ checks: results.length, results, qualification: 'Synthetic Chromium IndexedDB only; no Android, reboot, live authentication or backend qualification' }));
  await context.close();
} finally { await browser.close(); }
