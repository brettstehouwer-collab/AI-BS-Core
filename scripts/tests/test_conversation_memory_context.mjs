// Synthetic async-storage fixtures: no browser profile, server, SQLite or provider.
// Run: node --experimental-vm-modules --test scripts/tests/test_conversation_memory_context.mjs
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { webcrypto } from 'node:crypto';
import { SourceTextModule, SyntheticModule, createContext } from 'node:vm';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const source = await readFile(path.join(root, 'frontend/src/utils/conversationMemory.js'), 'utf8');
const httpSource = await readFile(path.join(root, 'frontend/src/utils/chatHttpResponse.js'), 'utf8');
const authSource = await readFile(path.join(root, 'frontend/src/utils/chatAuth.js'), 'utf8');
const A = 'http://127.0.0.1:8080', B = 'http://127.0.0.1:8081';
const historyId = 'e'.repeat(32);
const clone = value => structuredClone(value);
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

async function fixture() {
  const calls = [], records = new Map(), timers = new Map(), session = new Map();
  let gate = null, nextTimer = 0;
  const key = row => JSON.stringify([row.backendUrl, row.owner, row.conversationId]);
  const outbox = {
    async queueSnapshot(options) {
      calls.push({ action: 'queue', ...clone(options) });
      if (gate?.action === 'queue') {
        const selected = gate; gate = null;
        selected.entered.resolve(); await selected.release.promise;
      }
      const previous = records.get(key(options));
      assert.equal(previous?.head.local_revision || 0, options.expectedLocalRevision);
      const revision = options.expectedLocalRevision + 1;
      const entry = { status: 'queued', snapshot: { messages: clone(options.messages), title: options.title } };
      records.set(key(options), { head: { local_revision: revision, closed: false }, entries: [...previous?.entries || [], entry] });
      return { local_revision: revision };
    },
    async loadConversation(options) {
      calls.push({ action: 'load', ...clone(options) });
      if (gate?.action === 'load' && options.conversationId === historyId) {
        const selected = gate; gate = null;
        selected.entered.resolve(); await selected.release.promise;
      }
      return clone(records.get(key(options)) || null);
    },
    async listConversations(options) {
      return [...records].filter(([id]) => id.startsWith(JSON.stringify([options.backendUrl, options.owner]).slice(0, -1) + ','))
        .map(([id, row]) => ({ conversation_id: JSON.parse(id)[2], closed: row.head.closed }));
    },
    async prepareNext() { return null; },
    async closeConversation(options) { records.get(key(options)).head.closed = true; },
  };
  const subscribers = new Set();
  let state;
  const store = {
    getState: () => state,
    setState(patch) {
      const previous = state; state = { ...state, ...patch };
      subscribers.forEach(fn => fn(state, previous));
    },
    subscribe(fn) { subscribers.add(fn); return () => subscribers.delete(fn); },
  };
  state = { BACKEND_URL: A, currentUser: { uid: 'alice' }, chatMessages: [], footerInput: '',
    setChatMessages(updater) { store.setState({ chatMessages: typeof updater === 'function' ? updater(state.chatMessages) : updater }); },
    setFooterInput(updater) { store.setState({ footerInput: typeof updater === 'function' ? updater(state.footerInput) : updater }); },
  };
  const context = createContext({ URL, AbortSignal, crypto: webcrypto, TextEncoder,
    setTimeout(fn) { const id = ++nextTimer; timers.set(id, fn); return id; },
    clearTimeout(id) { timers.delete(id); },
    sessionStorage: { getItem: key => session.get(key) || null, setItem: (key, value) => session.set(key, value) },
    fetch: async url => ({ ok: true, status: 200, text: async () => JSON.stringify(url.endsWith('/identity')
      ? { storage: 'sqlite_vault', owner: 'firebase:fixture:' + state.currentUser.uid } : { items: [] }) }),
  });
  const dependency = new SyntheticModule(['openConversationOutbox'], function () {
    this.setExport('openConversationOutbox', async () => outbox);
  }, { context });
  const http = new SourceTextModule(httpSource, { context });
  await http.link(() => { throw Error('Unexpected HTTP helper dependency'); });
  // Execute the real auth helper against an owned synthetic Firebase user.
  // No Firebase SDK, browser session or token/provider transport is imported.
  const firebase = new SyntheticModule(['auth'], function () {
    this.setExport('auth', {
      get currentUser() {
        const user = state.currentUser;
        return user ? { ...user, getIdToken: async () => `fixture-token:${user.uid}` } : null;
      },
    });
  }, { context });
  const authentication = new SourceTextModule(authSource, { context });
  await authentication.link(specifier => {
    if (specifier === '../firebase.js') return firebase;
    throw Error('Unexpected auth helper dependency: ' + specifier);
  });
  const module = new SourceTextModule(source, { context });
  await module.link(specifier => {
    if (specifier === './conversationOutbox.js') return dependency;
    if (specifier === './chatHttpResponse.js') return http;
    if (specifier === './chatAuth.js') return authentication;
    throw Error('Unexpected production dependency: ' + specifier);
  });
  await module.evaluate();
  const manager = module.namespace.conversationMemoryFor(store);
  await manager.configure(A, 'alice', A);
  assert.equal(manager.getStatus().viewReady, true, manager.getStatus().error);
  const original = [{ role: 'user', content: 'ALICE current source', attachment: { text: 'full source' } }];
  store.setState({ chatMessages: original, footerInput: 'ALICE unfinished draft' });
  await manager.flushLocal();
  const oldBinding = manager.getBinding();
  records.set(key({ backendUrl: A, owner: oldBinding.owner, conversationId: historyId }), {
    head: { local_revision: 1, closed: false }, entries: [{ status: 'acknowledged', snapshot: { messages: [
      { id: '1'.repeat(32), kind: 'aibs_state_v1', draft: 'ALICE recovered draft' },
      { id: '2'.repeat(32), kind: 'aibs_message_v1', message: { role: 'assistant', content: 'ALICE history' } },
    ] } }],
  });
  return { manager, store, calls, records, key, original, oldBinding,
    block(action) { gate = { action, entered: deferred(), release: deferred() }; return gate; },
    switchContext(kind) {
      const patch = { chatMessages: [{ role: 'user', content: 'NEW context source' }], footerInput: 'NEW context draft' };
      if (kind === 'owner') patch.currentUser = { uid: 'bob' };
      else patch.BACKEND_URL = B;
      store.setState(patch);
      return clone(patch);
    },
  };
}

for (const kind of ['owner', 'backend']) {
  test(`separate copy stops after ${kind} changes during local commit`, async () => {
    const f = await fixture();
    f.store.setState({ footerInput: 'ALICE draft awaiting commit' });
    const gate = f.block('queue');
    const operation = f.manager.saveSeparateCopy();
    const rejected = assert.rejects(operation, /identity or backend changed/i);
    await gate.entered.promise;
    const selected = f.switchContext(kind);
    gate.release.resolve();
    await rejected;
    assert.deepEqual(f.store.getState().chatMessages, selected.chatMessages);
    assert.equal(f.store.getState().footerInput, selected.footerInput);
    assert.equal(f.manager.getBinding(), f.oldBinding, 'A stale action must not replace the active binding');
    assert.equal(f.calls.filter(row => row.action === 'queue').length, 2, 'Only the old context may finish its own pending commit');
    assert.ok(f.calls.filter(row => row.action === 'queue').every(row => !JSON.stringify(row.messages).includes('NEW context')));
  });

  test(`history recovery stops after ${kind} changes during local commit`, async () => {
    const f = await fixture();
    f.store.setState({ footerInput: 'ALICE draft awaiting commit' });
    const gate = f.block('queue');
    const operation = f.manager.recover(historyId);
    const rejected = assert.rejects(operation, /identity or backend changed/i);
    await gate.entered.promise;
    const selected = f.switchContext(kind);
    gate.release.resolve();
    await rejected;
    assert.equal(f.manager.getBinding(), f.oldBinding);
    assert.deepEqual(f.store.getState().chatMessages, selected.chatMessages);
    assert.equal(f.calls.filter(row => row.action === 'load' && row.conversationId === historyId).length, 0);
  });

  test(`history recovery stops after ${kind} changes during retained-history read`, async () => {
    const f = await fixture();
    const gate = f.block('load');
    const operation = f.manager.recover(historyId);
    const rejected = assert.rejects(operation, /identity or backend changed/i);
    await gate.entered.promise;
    const selected = f.switchContext(kind);
    gate.release.resolve();
    await rejected;
    assert.deepEqual(f.store.getState().chatMessages, selected.chatMessages);
    assert.equal(f.store.getState().footerInput, selected.footerInput);
    assert.equal(f.manager.getStatus().viewReady, false);
    assert.ok(f.records.has(f.key({ backendUrl: A, owner: f.oldBinding.owner, conversationId: historyId })), 'Recovered source stays retained');
  });

  test(`late recovery cannot replace a newly admitted ${kind} context`, async () => {
    const f = await fixture();
    const gate = f.block('load');
    const operation = f.manager.recover(historyId);
    const rejected = assert.rejects(operation, /identity or backend changed/i);
    await gate.entered.promise;
    f.store.setState({ chatMessages: [], footerInput: '', ...(kind === 'owner'
      ? { currentUser: { uid: 'bob' } } : { BACKEND_URL: B }) });
    await f.manager.configure(kind === 'owner' ? A : B, kind === 'owner' ? 'bob' : 'alice', kind === 'owner' ? A : B);
    const newBinding = f.manager.getBinding();
    f.store.setState({ chatMessages: [{ role: 'user', content: 'NEW admitted context' }], footerInput: 'NEW admitted draft' });
    await f.manager.flushLocal();
    gate.release.resolve();
    await rejected;
    assert.equal(f.manager.getBinding(), newBinding);
    assert.equal(f.manager.getStatus().viewReady, true);
    assert.deepEqual(f.store.getState().chatMessages, [{ role: 'user', content: 'NEW admitted context' }]);
    assert.equal(f.store.getState().footerInput, 'NEW admitted draft');
  });
}

test('unchanged-context recovery restores messages and draft as data', async () => {
  const f = await fixture();
  await f.manager.recover(historyId);
  assert.deepEqual(clone(f.store.getState().chatMessages), [{ role: 'assistant', content: 'ALICE history' }]);
  assert.equal(f.store.getState().footerInput, 'ALICE recovered draft');
  assert.equal(f.manager.getStatus().viewReady, true);
  assert.equal(f.manager.getBinding().cid, historyId);
});

test('unchanged-context separate copy keeps the original and full source', async () => {
  const f = await fixture();
  await f.manager.saveSeparateCopy();
  const next = f.manager.getBinding();
  assert.notEqual(next.cid, f.oldBinding.cid);
  assert.equal(next.owner, f.oldBinding.owner);
  assert.deepEqual(clone(f.store.getState().chatMessages), f.original);
  assert.equal(f.store.getState().footerInput, 'ALICE unfinished draft');
  assert.equal(f.records.size, 3, 'Original, history and the new copy remain retained');
});
