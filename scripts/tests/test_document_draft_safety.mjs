import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { test } from 'node:test';
import vm from 'node:vm';
import { transform } from '../../frontend/node_modules/esbuild/lib/main.js';
import * as safety from '../../frontend/src/utils/documentDraftSafety.js';
import * as intake from '../../frontend/src/utils/driveIntakeDocuments.js';

const revision = content => createHash('sha256').update(content).digest('hex');
const response = (data, ok = true, status = ok ? 200 : 409) => ({ ok, status, json: async () => data });
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const tick = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
function storage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return { values, fail: false, get length() { return values.size; }, key: i => [...values.keys()][i] ?? null,
    getItem: key => values.get(key) ?? null,
    setItem(key, value) { if (this.fail) throw new Error('QuotaExceededError'); values.set(key, String(value)); } };
}

test('A/B readers: stale A cannot overwrite B; blocked A cannot retry, while B remains usable', async () => {
  let disk = 'original', calls = 0;
  const write = async payload => {
    calls++;
    if (payload.expected_revision !== revision(disk)) throw new Error('HTTP 409 conflict');
    disk = payload.content;
    return { path: 'C:\\AI-BS\\shared_cloud_drive\\Documents\\A.txt', revision: revision(disk), unchanged: false };
  };
  const a = safety.createDocumentDraftCoordinator({ write }), b = safety.createDocumentDraftCoordinator({ write });
  a.load('Documents/A.txt', disk, revision(disk)); b.load('Documents/A.txt', disk, revision(disk));
  await b.save('Documents/A.txt', 'newer B');
  await assert.rejects(a.save('Documents/A.txt', 'older A edit'), /409/);
  await assert.rejects(a.save('Documents/A.txt', 'another A edit'), /paused/);
  assert.equal(disk, 'newer B'); assert.equal(calls, 2);
  await b.save('Documents/A.txt', 'B again'); assert.equal(disk, 'B again');
});

test('queued new edits use the acknowledged revision, including after create-only first save', async () => {
  const gate = deferred(), calls = [];
  const coordinator = safety.createDocumentDraftCoordinator({ write: async payload => {
    calls.push(payload); if (calls.length === 1) await gate.promise;
    return { path: 'C:/AI-BS/shared_cloud_drive/Documents/new.txt', revision: revision(payload.content), unchanged: false };
  }});
  coordinator.registerNew('Documents/new.txt');
  const one = coordinator.save('Documents/new.txt', 'first'), two = coordinator.save('Documents/new.txt', 'newer');
  await tick(); assert.equal(calls.length, 1); assert.equal(calls[0].create_only, true);
  gate.resolve(); await Promise.all([one, two]);
  assert.equal(calls[1].expected_revision, revision('first')); assert.equal(calls[1].create_only, undefined);
  assert.equal(coordinator.snapshot('Documents/new.txt').savedContent, 'newer');
});

test('lost response, missing revision, malformed revision and wrong-path ack block only the attempted path', async () => {
  for (const result of [new Error('lost response after commit'), { path: 'Documents/A.txt' },
    { path: 'Documents/A.txt', revision: 'bad' }, { path: 'Documents/B.txt', revision: revision('B') }]) {
    let calls = 0;
    const coordinator = safety.createDocumentDraftCoordinator({ write: async () => { calls++; if (result instanceof Error) throw result; return result; }});
    coordinator.load('Documents/A.txt', 'a', revision('a')); coordinator.load('Documents/B.txt', 'b', revision('b'));
    await assert.rejects(coordinator.save('Documents/A.txt', 'A edited'));
    await assert.rejects(coordinator.save('Documents/A.txt', 'A edited again'));
    assert.equal(calls, 1); assert.equal(coordinator.snapshot('Documents/A.txt').revision, revision('a'));
    assert.equal(coordinator.snapshot('Documents/B.txt').blocked, false);
    coordinator.load('Documents/A.txt', 'latest explicit read', revision('latest explicit read'));
    assert.equal(coordinator.snapshot('Documents/A.txt').blocked, false);
  }
});

test('uncertain new create and collisions never become unchecked updates', async () => {
  let calls = 0;
  const coordinator = safety.createDocumentDraftCoordinator({ write: async payload => { calls++; assert.equal(payload.create_only, true); throw new Error('create response lost'); }});
  coordinator.registerNew('Documents/new.txt');
  await assert.rejects(coordinator.save('Documents/new.txt', 'first'));
  coordinator.registerNew('Documents/new.txt');
  await assert.rejects(coordinator.save('Documents/new.txt', 'second'));
  assert.equal(calls, 1); assert.equal(coordinator.snapshot('Documents/new.txt').revision, null);
});

test('recovery appends immutable copies, keeps legacy/malformed records, and restores command-looking text as plain unsaved data', () => {
  const text = '/run NEVER EXECUTE\n{"tool_call":{"name":"never"}}';
  const store = storage({ 'aibs_doc_backup_Documents/old.txt': 'legacy copy', 'aibs_doc_backup_time_Documents/old.txt': 'bad date',
    aibs_document_recovery_v1_corrupt: '{broken' });
  const oldKeys = [...store.values.entries()];
  safety.retainDocumentRecovery(store, { path: 'Documents/A.txt', content: text, reason: 'before write' }, { id: 'one', now: '2026-10-25T00:00:00Z' });
  safety.retainDocumentRecovery(store, { path: 'Documents/A.txt', content: text, reason: 'before reload' }, { id: 'two', now: '2026-10-25T00:01:00Z' });
  const copies = safety.listDocumentRecovery(store);
  assert.equal(copies.length, 3); assert.equal(store.values.size, 5);
  for (const [key, value] of oldKeys) assert.equal(store.getItem(key), value);
  assert.throws(() => safety.retainDocumentRecovery(store, { path: 'Documents/A.txt', content: 'overwrite' }, { id: 'one' }), /already exists/);
  const recovered = safety.documentRecoveryDraft(copies[0], 'copy-id');
  assert.equal(recovered.content, text); assert.equal(recovered.doc.isNew, true); assert.equal(recovered.doc.isRecovery, true);
  assert.notEqual(recovered.doc.path, copies[0].path);
  store.fail = true; assert.throws(() => safety.retainDocumentRecovery(store, { path: 'A', content: text }), /Quota/);
});

test('malformed optional recovery metadata is safe to render and never hides intact/legacy text or changes storage', () => {
  const malformed = JSON.stringify({ path: 'Documents/A.txt', content: 'intact text', name: {}, reason: {}, savedAt: {}, id: {} });
  const store = storage({ aibs_document_recovery_v1_badmeta: malformed, 'aibs_doc_backup_Documents/legacy.txt': 'legacy' });
  const copies = safety.listDocumentRecovery(store);
  assert.equal(copies.length, 2);
  for (const copy of copies) for (const field of ['name', 'reason', 'savedAt', 'id']) assert.equal(typeof copy[field], 'string');
  assert.equal(store.getItem('aibs_document_recovery_v1_badmeta'), malformed);
  assert.ok(copies.some(copy => copy.content === 'intact text')); assert.ok(copies.some(copy => copy.content === 'legacy'));
});

// Execute the complete current component with a tiny hook scheduler and replaced
// transport/storage/DOM sinks. The injected capture only exposes its real local
// handlers; this is source/component synthetic evidence, not browser acceptance.
const source = readFileSync(new URL('../../frontend/src/components/DocumentsTab.jsx', import.meta.url), 'utf8');
const capturePoint = '  // ── Render file tree';
assert.ok(source.includes(capturePoint));
const instrumented = source.replace(capturePoint, `  globalThis.__documentsFixture = { loadFile, saveFile, createDocument, handleImportFile, handleContentChange, openRecoveryCopy };\n${capturePoint}`);
const compiled = (await transform(instrumented, { loader: 'jsx', jsx: 'automatic', format: 'cjs', define: { 'import.meta.env': '{}' } })).code;

function componentHarness({ fetcher, initialStorage } = {}) {
  const cells = [], effects = [], timers = new Map(), downloads = [], calls = [];
  const store = initialStorage || storage();
  let cursor = 0, nextTimer = 0, tree;
  const shared = { doc: null, content: '' };
  const depsEqual = (a, b) => a && b && a.length === b.length && a.every((x, i) => Object.is(x, b[i]));
  const hooks = {
    createElement: (type, props, ...children) => ({ type, props: { ...props, children } }), Fragment: 'fragment',
    useRef(value) { const i = cursor++; if (!cells[i]) cells[i] = { current: value }; return cells[i]; },
    useState(value) { const i = cursor++; if (!cells[i]) { const cell = { value: typeof value === 'function' ? value() : value }; cell.set = next => { cell.value = typeof next === 'function' ? next(cell.value) : next; }; cells[i] = cell; } return [cells[i].value, cells[i].set]; },
    useMemo(fn, deps) { const i = cursor++; if (!cells[i] || !depsEqual(cells[i].deps, deps)) cells[i] = { value: fn(), deps }; return cells[i].value; },
    useCallback(fn, deps) { return hooks.useMemo(() => fn, deps); },
    useEffect(fn, deps) { const i = cursor++; if (!cells[i] || !depsEqual(cells[i].deps, deps)) { const old = cells[i]; cells[i] = { deps, cleanup: old?.cleanup }; effects.push(() => { old?.cleanup?.(); cells[i].cleanup = fn(); }); } },
  };
  const module = { exports: {} };
  const sandbox = {
    module, exports: module.exports, console, localStorage: store, Blob, File, FormData, Date,
    crypto: { randomUUID }, setTimeout: (fn, delay) => { const id = ++nextTimer; timers.set(id, { fn, delay }); return id; },
    clearTimeout: id => timers.delete(id), setInterval: () => 1, clearInterval: () => {},
    URL: { createObjectURL: blob => { downloads.push(blob); return 'blob:fixture'; }, revokeObjectURL: () => {} },
    window: { innerWidth: 1440, addEventListener: () => {}, removeEventListener: () => {} },
    document: { body: { appendChild: () => {} }, createElement: () => ({ click: () => {}, remove: () => {} }) },
    confirm: () => true, alert: () => {}, prompt: () => null,
    fetch: async (url, options) => {
      calls.push({ url, options });
      if (url.endsWith('/api/tree')) return response({ files: [] });
      if (fetcher) return fetcher(url, options);
      throw new Error(`Unexpected synthetic request ${url}`);
    },
    require: name => name === 'react' ? hooks : name === 'react/jsx-runtime' ? {
      Fragment: hooks.Fragment,
      jsx: (type, props, key) => hooks.createElement(type, { ...props, key }, ...(Array.isArray(props?.children) ? props.children : [props?.children])),
      jsxs: (type, props, key) => hooks.createElement(type, { ...props, key }, ...(Array.isArray(props?.children) ? props.children : [props?.children])),
    } : name.includes('documentDraftSafety') ? safety : name.includes('driveIntakeDocuments') ? intake
      : name.endsWith('.css') ? {} : name.includes('AuthenticatedDriveMedia') ? { AuthenticatedDriveMedia: 'Media', AuthenticatedDriveDownload: 'Download' } : 'Stub',
  };
  vm.runInNewContext(compiled, sandbox, { filename: 'DocumentsTab.actual.component.fixture.cjs' });
  const Component = module.exports.default;
  const props = { backendUrl: 'http://fixture.invalid', setSharedContent: text => { shared.content = text; }, setSharedActiveDoc: doc => { shared.doc = typeof doc === 'function' ? doc(shared.doc) : doc; } };
  const render = () => {
    cursor = 0; tree = Component({ ...props, sharedContent: shared.content, sharedActiveDoc: shared.doc });
    while (effects.length) effects.shift()();
    return tree;
  };
  render();
  return { shared, store, calls, timers, downloads, render,
    get handlers() { return sandbox.__documentsFixture; }, get tree() { return tree; },
    async mountA() { await sandbox.__documentsFixture.loadFile('Documents/A.txt'); render(); },
    edit(text) { sandbox.__documentsFixture.handleContentChange(text); render(); },
    text() { const flatten = node => node === null || node === undefined || node === false ? '' : Array.isArray(node) ? node.map(flatten).join(' ') : typeof node === 'object' ? flatten(node.props?.children) : String(node); return flatten(tree); },
    button(label) { const visit = node => { if (!node || typeof node !== 'object') return null; if (Array.isArray(node)) { for (const child of node) { const found = visit(child); if (found) return found; } return null; } if (node.type === 'button' && node.props.children.flat().includes(label)) return node; return visit(node.props?.children); }; return visit(tree); },
  };
}

const readA = () => response({ path: 'C:/AI-BS/shared_cloud_drive/Documents/A.txt', content: 'original A', revision: revision('original A') });

test('only the actual shared-drive root aliases relative paths; legacy E: and repository-root files stay distinct', () => {
  assert.equal(safety.documentPathIdentity('C:\\AI-BS\\shared_cloud_drive\\Documents\\A.txt'), safety.documentPathIdentity('Documents/A.txt'));
  assert.notEqual(safety.documentPathIdentity('E:/AI-BS/Documents/A.txt'), safety.documentPathIdentity('Documents/A.txt'));
  assert.notEqual(safety.documentPathIdentity('C:/AI-BS/Documents/A.txt'), safety.documentPathIdentity('Documents/A.txt'));
});

test('actual component: edit during delayed read keeps current identity/content and does not install stale B', async () => {
  const gate = deferred();
  const h = componentHarness({ fetcher: url => url.includes('A.txt') ? readA() : gate.promise });
  await h.mountA();
  const opening = h.handlers.loadFile('Documents/B.txt'); await tick();
  h.edit('local edit during read');
  gate.resolve(response({ path: 'Documents/B.txt', content: 'server B', revision: revision('server B') }));
  assert.equal(await opening, false); h.render();
  assert.equal(h.shared.content, 'local edit during read'); assert.ok(h.shared.doc.path.endsWith('A.txt'));
  assert.match(h.text(), /draft changed/);
});

test('actual component: edit during preceding save cancels navigation and next save uses ack revision', async () => {
  const gate = deferred(), writes = [];
  const h = componentHarness({ fetcher: (url, options) => {
    if (url.includes('/api/read')) return readA();
    const payload = JSON.parse(options.body); writes.push(payload);
    return writes.length === 1 ? gate.promise : response({ path: 'C:/AI-BS/shared_cloud_drive/Documents/A.txt', revision: revision(payload.content), unchanged: false });
  }});
  await h.mountA(); h.edit('first edit');
  const opening = h.handlers.loadFile('Documents/B.txt'); await tick();
  h.edit('second edit during save');
  gate.resolve(response({ path: 'C:/AI-BS/shared_cloud_drive/Documents/A.txt', revision: revision('first edit'), unchanged: false }));
  assert.equal(await opening, false); h.render();
  assert.equal(h.shared.content, 'second edit during save');
  assert.ok(h.shared.doc.path.endsWith('A.txt')); assert.equal(h.calls.filter(call => call.url.includes('/api/read')).length, 1);
  assert.equal(await h.handlers.saveFile(), true);
  assert.equal(writes[1].expected_revision, revision('first edit'));
});

test('actual component: late A acknowledgement cannot relabel externally selected B or replace its content', async () => {
  const gate = deferred();
  const h = componentHarness({ fetcher: url => url.includes('/api/read') ? readA() : gate.promise });
  await h.mountA(); h.edit('save A'); const saving = h.handlers.saveFile(); await tick();
  h.shared.doc = { name: 'B.txt', path: 'Documents/B.txt', ext: 'txt' }; h.shared.content = 'B local draft'; h.render();
  gate.resolve(response({ path: 'Documents/A.txt', revision: revision('save A'), unchanged: false }));
  assert.equal(await saving, true); h.render();
  assert.equal(h.shared.doc.path, 'Documents/B.txt'); assert.equal(h.shared.content, 'B local draft');
});

test('actual component: lost acknowledgement blocks automatic/manual retry until preserving explicit reload', async () => {
  let writes = 0;
  const h = componentHarness({ fetcher: url => { if (url.includes('/api/read')) return readA(); writes++; throw new Error('lost response'); } });
  await h.mountA(); h.edit('retained draft'); assert.equal(await h.handlers.saveFile(), false); h.render();
  h.edit('newer retained draft'); assert.equal(await h.handlers.saveFile(), false); h.render();
  assert.equal(writes, 1); assert.match(h.text(), /Autosave paused/);
  await h.handlers.loadFile(h.shared.doc.path, { reload: true }); h.render();
  assert.equal(h.shared.content, 'original A');
  assert.ok(safety.listDocumentRecovery(h.store).some(copy => copy.content === 'newer retained draft'));
});

test('actual component: failed recovery storage blocks reload and exposes current-draft download', async () => {
  const h = componentHarness({ fetcher: () => readA() }); await h.mountA(); h.edit('must keep');
  const readsBefore = h.calls.length; h.store.fail = true;
  assert.equal(await h.handlers.loadFile(h.shared.doc.path, { reload: true }), false); h.render();
  assert.equal(h.shared.content, 'must keep'); assert.equal(h.calls.length, readsBefore);
  assert.match(h.text(), /recovery storage failed/); h.button('Download current draft').props.onClick();
  assert.equal(await h.downloads[0].text(), 'must keep');
});

test('actual component: Word/text/PDF delayed imports cannot overwrite intervening edits', async () => {
  for (const ext of ['txt', 'docx', 'pdf']) {
    const gate = deferred();
    const h = componentHarness({ fetcher: url => url.includes('/api/read') ? readA() : gate.promise });
    await h.mountA();
    const file = ext === 'txt' ? { name: 'fixture.txt', text: () => gate.promise } : new File(['synthetic'], `fixture.${ext}`);
    const importing = h.handlers.handleImportFile(file); await tick(); h.edit(`${ext} intervening edit`);
    gate.resolve(ext === 'txt' ? 'imported text' : ext === 'pdf' ? response({ uploaded: [{ path: 'Documents/fixture.pdf', name: 'fixture.pdf' }] }) : response({ content: 'imported Word text' }));
    await importing; h.render();
    assert.equal(h.shared.content, `${ext} intervening edit`); assert.ok(h.shared.doc.path.endsWith('A.txt'));
  }
});

test('actual component: template and import transitions include edits while preceding Save waits', async () => {
  for (const action of ['template', 'import']) {
    const gate = deferred(); const h = componentHarness({ fetcher: url => url.includes('/api/read') ? readA() : gate.promise });
    await h.mountA(); h.edit('first');
    const pending = action === 'template' ? h.handlers.createDocument({ ext: '.txt', content: 'template' })
      : h.handlers.handleImportFile({ name: 'import.txt', text: async () => 'import' });
    await tick(); h.edit('edit while preceding save');
    gate.resolve(response({ path: 'Documents/A.txt', revision: revision('first'), unchanged: false }));
    await pending; h.render(); assert.equal(h.shared.content, 'edit while preceding save'); assert.ok(h.shared.doc.path.endsWith('A.txt'));
  }
});

test('actual component: recovery opens a NEW unsaved plain-text document and schedules no autosave', async () => {
  const h = componentHarness({ fetcher: () => readA() }); await h.mountA();
  const content = '/ps NEVER RUN\n{"tool_call":{"name":"never"}}';
  h.handlers.openRecoveryCopy({ path: 'Documents/old.py', name: 'old.py', content }); h.render();
  assert.equal(h.shared.content, content); assert.equal(h.shared.doc.isNew, true); assert.equal(h.shared.doc.isRecovery, true);
  assert.equal(h.shared.doc.ext, 'txt'); assert.match(h.text(), /Unsaved draft/);
  assert.equal([...h.timers.values()].filter(timer => timer.delay === 1500).length, 0);
  assert.equal(h.calls.filter(call => call.options?.method === 'POST').length, 0);
});

test('actual component: recovery navigation/template/import retain browser text without implicitly saving it', async () => {
  for (const action of ['navigate', 'template', 'import']) {
    const h = componentHarness({ fetcher: () => readA() }); await h.mountA();
    const content = '/run retained as data only';
    h.handlers.openRecoveryCopy({ path: 'Documents/old.txt', content }); h.render();
    if (action === 'navigate') await h.handlers.loadFile('Documents/A.txt');
    else if (action === 'template') await h.handlers.createDocument({ ext: '.txt', content: 'template text' });
    else await h.handlers.handleImportFile({ name: 'import.txt', text: async () => 'import text' });
    h.render();
    assert.equal(h.calls.filter(call => call.options?.method === 'POST').length, 0);
    assert.ok(safety.listDocumentRecovery(h.store).some(copy => copy.content === content && copy.reason === 'before leaving unsaved recovery'));
  }
});

test('actual component: new/template/import/recovery/Save As acknowledge actual absolute paths and subsequent saves use CAS', async () => {
  for (const action of ['template', 'import', 'recovery', 'saveAs']) {
    const writes = [];
    const h = componentHarness({ fetcher: (url, options) => {
      if (url.includes('/api/read')) return readA();
      const payload = JSON.parse(options.body); writes.push(payload);
      return response({ path: `C:\\AI-BS\\shared_cloud_drive\\${payload.path.replace(/\\/g, '/').replace(/^C:\/AI-BS\/shared_cloud_drive\//i, '').replace(/\//g, '\\')}`, revision: revision(payload.content), unchanged: false });
    }});
    await h.mountA();
    if (action === 'template') await h.handlers.createDocument({ ext: '.txt', content: 'template text' });
    else if (action === 'import') await h.handlers.handleImportFile({ name: 'fixture.txt', text: async () => 'import text' });
    else if (action === 'recovery') h.handlers.openRecoveryCopy({ path: 'Documents/old.txt', content: 'recovered text' });
    h.render();
    const destination = action === 'saveAs' ? { ...h.shared.doc, path: 'Documents/save-as.txt', name: 'save-as.txt', isNew: true } : undefined;
    assert.equal(await h.handlers.saveFile(destination), true, action); h.render();
    assert.equal(writes[0].create_only, true, action); assert.equal(h.shared.doc.isNew, false, action);
    const previousText = h.shared.content; h.edit('newer after acknowledgement');
    assert.equal(await h.handlers.saveFile(), true, action);
    assert.equal(writes[1].expected_revision, revision(previousText), action);
  }
});

test('actual component: explicit reload drains pending write before reading; newer edits during wait cancel replacement', async () => {
  for (const editWhileWaiting of [false, true]) {
    const gate = deferred(); let disk = 'original A', reads = 0;
    const h = componentHarness({ fetcher: (url, options) => {
      if (url.includes('/api/read')) { reads++; return response({ path: 'Documents/A.txt', content: disk, revision: revision(disk) }); }
      return gate.promise.then(() => { disk = JSON.parse(options.body).content; return response({ path: 'Documents/A.txt', revision: revision(disk), unchanged: false }); });
    }});
    await h.mountA(); h.edit('pending saved text'); const saving = h.handlers.saveFile(); await tick();
    const reloading = h.handlers.loadFile(h.shared.doc.path, { reload: true }); await tick();
    assert.equal(reads, 1);
    if (editWhileWaiting) h.edit('new local edit while drain waited');
    gate.resolve(); await saving; await reloading; h.render();
    assert.equal(reads, editWhileWaiting ? 1 : 2);
    assert.equal(h.shared.content, editWhileWaiting ? 'new local edit while drain waited' : 'pending saved text');
  }
});

test('actual component: typing snapshots coalesce, but immediate save retains the latest whole draft', async () => {
  const h = componentHarness({ fetcher: (url, options) => url.includes('/api/read') ? readA()
    : response({ path: 'Documents/A.txt', revision: revision(JSON.parse(options.body).content), unchanged: false }) });
  await h.mountA();
  const before = safety.listDocumentRecovery(h.store).length;
  for (let i = 0; i < 30; i++) h.edit(`typing ${i}`);
  assert.equal(safety.listDocumentRecovery(h.store).length, before);
  const typingTimers = [...h.timers.values()].filter(timer => timer.delay === 750);
  assert.equal(typingTimers.length, 1); typingTimers[0].fn();
  assert.equal(safety.listDocumentRecovery(h.store).length, before + 1);
  h.edit('latest before immediate save');
  await h.handlers.saveFile();
  assert.ok(safety.listDocumentRecovery(h.store).some(copy => copy.content === 'latest before immediate save' && copy.reason === 'before save'));
});

test('actual component: missing/mismatched read acknowledgement never replaces the current draft', async () => {
  for (const result of [{ path: 'Documents/B.txt', content: 'unversioned' }, { path: 'Documents/C.txt', content: 'wrong document', revision: revision('wrong document') }]) {
    const h = componentHarness({ fetcher: url => url.includes('A.txt') ? readA() : response(result) });
    await h.mountA();
    assert.equal(await h.handlers.loadFile('Documents/B.txt'), false); h.render();
    assert.equal(h.shared.content, 'original A'); assert.ok(h.shared.doc.path.endsWith('A.txt'));
  }
});
