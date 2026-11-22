// Actual archive helper with synthetic HTTP/store fixtures only.
// Run: node --experimental-vm-modules --test scripts/tests/test_chat_archive_preservation.mjs
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { webcrypto } from 'node:crypto';
import { SourceTextModule, createContext } from 'node:vm';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const source = await readFile(path.join(root, 'frontend/src/utils/chatArchive.js'), 'utf8');
const httpSource = await readFile(path.join(root, 'frontend/src/utils/chatHttpResponse.js'), 'utf8');
const initial = () => [{ role: 'user', content: 'Unfinished synthetic question', id: 7,
  attachment: { name: 'fixture.md', text: 'complete synthetic source' } },
{ role: 'assistant', content: 'Partial synthetic reply', outcome: 'failed', metadata: { nested: ['retained'] } }];

async function fixture() {
  let messages = initial(), responseMode = 'success', onRequest = () => {};
  const calls = [], state = { busy: false, pending: null };
  const context = createContext({ crypto: webcrypto, AbortSignal,
    fetch: async (url, options) => {
      calls.push({ url, ...options });
      await onRequest();
      if (responseMode === 'offline') throw Error('Synthetic offline failure');
      const body = JSON.parse(options.body);
      const receipt = { durable: true, storage: 'sqlite_vault', owner: 'firebase:fixture:alice',
        archive_id: body.archive_id, message_count: body.messages.length,
        vault_item_id: 1, payload_sha256: 'a'.repeat(64) };
      const data = { status: 'success', items_saved: body.messages.length, archive_receipt: receipt };
      if (responseMode === 'partial') data.items_saved--;
      if (responseMode === 'nondurable') receipt.durable = false;
      if (responseMode === 'wrong_archive') receipt.archive_id = 'f'.repeat(32);
      if (responseMode === 'bad_digest') receipt.payload_sha256 = 'unconfirmed';
      return { ok: responseMode !== 'http_error', status: responseMode === 'http_error' ? 503 : 200,
        text: async () => JSON.stringify(data) };
    },
  });
  const http = new SourceTextModule(httpSource, { context });
  await http.link(() => { throw Error('Unexpected helper dependency'); });
  const module = new SourceTextModule(source, { context });
  await module.link(specifier => {
    if (specifier === './chatHttpResponse.js') return http;
    throw Error('Unexpected archive dependency');
  });
  await module.evaluate();
  const options = { state, backendUrl: 'http://127.0.0.1:8080',
    getMessages: () => messages, setMessages: updater => { messages = updater(messages); },
    isCurrentBackend: () => true, sessionTitle: 'Synthetic partial chat', source: 'synthetic_fixture' };
  return { calls, state, options, save: () => module.namespace.archiveChatAndClear(options),
    getMessages: () => messages, setMessages: value => { messages = value; },
    setMode: mode => { responseMode = mode; }, onRequest: fn => { onRequest = fn; } };
}

test('complete durable receipt clears only after preservation callback', async () => {
  const f = await fixture();
  let callback = false;
  f.options.beforeClear = async ({ serialized, backendUrl, receipt }) => {
    assert.deepEqual(JSON.parse(serialized), initial());
    assert.equal(backendUrl, f.options.backendUrl);
    assert.equal(receipt.owner, 'firebase:fixture:alice');
    assert.deepEqual(f.getMessages(), initial());
    callback = true;
  };
  const result = await f.save();
  assert.equal(callback, true);
  assert.equal(result.cleared, true);
  assert.deepEqual(Array.from(f.getMessages()), []);
  assert.deepEqual(JSON.parse(f.calls[0].body).messages, initial());
  assert.equal(f.state.pending, null);
  assert.equal(f.state.busy, false);
});

for (const mode of ['offline', 'http_error', 'partial', 'nondurable', 'wrong_archive', 'bad_digest']) {
  test(`${mode} preserves complete messages and retry identity`, async () => {
    const f = await fixture(); f.setMode(mode);
    await assert.rejects(f.save());
    assert.deepEqual(f.getMessages(), initial());
    assert.ok(f.state.pending?.id);
    assert.equal(f.state.busy, false);
  });
}

test('lost reply retries the same request body on the same backend', async () => {
  const f = await fixture(); f.setMode('offline');
  await assert.rejects(f.save());
  const pending = f.state.pending.id;
  f.setMode('success');
  assert.equal((await f.save()).cleared, true);
  assert.equal(f.calls.length, 2);
  assert.equal(f.calls[0].body, f.calls[1].body);
  assert.equal(f.calls[0].url, f.calls[1].url);
  assert.equal(JSON.parse(f.calls[1].body).archive_id, pending);
});

test('failed local preservation callback leaves the view and retry intact', async () => {
  const f = await fixture();
  f.options.beforeClear = async () => { throw Error('Synthetic storage quota failure'); };
  await assert.rejects(f.save(), /storage quota/);
  assert.deepEqual(f.getMessages(), initial());
  assert.ok(f.state.pending);
  assert.equal(f.state.busy, false);
});

test('owner mismatch rejected by the bound callback keeps current chat', async () => {
  const f = await fixture();
  f.options.beforeClear = async ({ receipt }) => receipt.owner === 'firebase:fixture:bob';
  assert.equal((await f.save()).cleared, false);
  assert.deepEqual(f.getMessages(), initial());
  assert.ok(f.state.pending);
});

test('new messages received during archive confirmation remain on screen', async () => {
  const f = await fixture();
  const newer = [...initial(), { role: 'user', content: 'Newer unarchived message' }];
  f.onRequest(() => f.setMessages(newer));
  assert.equal((await f.save()).cleared, false);
  assert.deepEqual(f.getMessages(), newer);
  assert.deepEqual(JSON.parse(f.calls[0].body).messages, initial());
});

test('changed backend keeps the current view despite confirmed old archive', async () => {
  const f = await fixture(); f.options.isCurrentBackend = () => false;
  assert.equal((await f.save()).cleared, false);
  assert.deepEqual(f.getMessages(), initial());
});
