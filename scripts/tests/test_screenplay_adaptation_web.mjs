import assert from 'node:assert/strict';
import { test } from 'node:test';
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const moduleUrl = pathToFileURL('C:/AI-BS/frontend/src/utils/screenplayAdaptation.js');
const { validateAdaptationAcceptance, readAdaptationJob, isAdaptationTerminal,
  requestAdaptationAction, monitorAdaptation } = await import(moduleUrl);
const token = 'a'.repeat(32);
const job = (status = 'processing', changes = {}) => ({ contract: 'create-only-v1', project_name: 'Fixture',
  projectName: 'Fixture', job_id: token, status, progress: 32, ...changes });
const accepted = changes => ({ status: 'success', contract: 'create-only-v1', project_name: 'Fixture', job_id: token, ...changes });
const require = createRequire(pathToFileURL('C:/AI-BS/frontend/package.json'));
const { parse } = require('@babel/parser');
function actualHandler(component, name, dependencies) {
  const source = readFileSync(`C:/AI-BS/frontend/src/components/${component}.jsx`, 'utf8');
  const tree = parse(source, { sourceType: 'module', plugins: ['jsx'] });
  let target;
  function visit(value) {
    if (!value || typeof value !== 'object') return;
    if (value.type === 'VariableDeclarator' && value.id?.name === name) target = value.init;
    if (name === 'catalogEffect' && value.type === 'CallExpression' && value.callee?.name === 'useEffect') target = value.arguments[0];
    for (const item of Object.values(value)) {
      if (Array.isArray(item)) item.forEach(visit);
      else if (item && typeof item === 'object') visit(item);
    }
  }
  visit(tree);
  assert.ok(target, `Actual ${name} implementation exists`);
  return Function(...Object.keys(dependencies), `return (${source.slice(target.start, target.end)});`)(...Object.values(dependencies));
}

test('acceptance requires protected contract, exact project and valid ownership token', () => {
  assert.equal(validateAdaptationAcceptance(accepted(), 'Fixture').job_id, token);
  for (const bad of [accepted({ status: 'processing' }), accepted({ contract: undefined }),
    accepted({ project_name: 'Other' }), accepted({ job_id: 'old' }), accepted({ project: 'Other' })]) {
    assert.throws(() => validateAdaptationAcceptance(bad, 'Fixture'));
  }
});
test('all durable terminal states stop monitoring without being relabeled complete', () => {
  for (const status of ['complete', 'error', 'canceled', 'cancelled', 'interrupted', 'reset', 'not_found']) {
    assert.equal(isAdaptationTerminal(status), true);
    const raw = status === 'not_found' ? { status } : job(status);
    assert.equal(readAdaptationJob(raw, 'Fixture', token).status, status);
  }
  assert.equal(isAdaptationTerminal('processing'), false);
  assert.throws(() => readAdaptationJob(job('complete', { job_id: 'b'.repeat(32) }), 'Fixture', token));
});
test('cancel and reset carry the known job token and require backend acknowledgment', async () => {
  for (const action of ['cancel', 'reset']) {
    const calls = [];
    const result = await requestAdaptationAction('https://fixture.invalid', job(), action, async (url, options) => {
      calls.push({ url, payload: JSON.parse(options.body) });
      return { ok: true, status: 200, json: async () => ({ status: 'success', project_name: 'Fixture' }) };
    });
    assert.deepEqual(calls[0].payload, { project_name: 'Fixture', job_id: token });
    assert.equal(result.status, action === 'cancel' ? 'canceled' : 'reset');
    for (const response of [{ ok: false, status: 409, data: { detail: 'Job changed' } },
      { ok: true, status: 200, data: { status: 'not_found', project_name: 'Fixture' } },
      { ok: true, status: 200, data: { status: 'success', project_name: 'Other' } }]) {
      await assert.rejects(requestAdaptationAction('https://fixture.invalid', job(), action,
        async () => ({ ...response, json: async () => response.data })));
    }
  }
});
function harness(fetchImpl) {
  const source = { onmessage: null, onerror: null, closed: false, close() { this.closed = true; } };
  const seen = [], errors = [];
  let poll, intervalCleared = false;
  const stop = monitorAdaptation({ baseUrl: 'https://fixture.invalid', projectName: 'Fixture', jobId: token,
    eventSourceFactory: () => source, fetchImpl,
    setIntervalImpl: callback => { poll = callback; return 7; },
    clearIntervalImpl: () => { intervalCleared = true; },
    onStatus: value => seen.push(value), onError: error => errors.push(error) });
  return { source, seen, errors, stop, poll: () => poll(), cleared: () => intervalCleared };
}
test('clean stream EOF cannot hide an observed terminal status: status poll closes it', async () => {
  const h = harness(async () => ({ ok: true, json: async () => job('interrupted') }));
  await h.poll();
  assert.equal(h.seen[0].status, 'interrupted');
  assert.equal(h.source.closed, true);
  assert.equal(h.cleared(), true);
  assert.equal(h.errors.length, 0);
});
test('mismatched stream ownership stops with an error and never confirms completion', () => {
  const h = harness(async () => { throw Error('must not fetch'); });
  h.source.onmessage({ data: JSON.stringify(job('complete', { job_id: 'b'.repeat(32) })) });
  assert.equal(h.seen.length, 0); assert.equal(h.errors.length, 1); assert.equal(h.source.closed, true);
});
test('HTTP rejection or lost progress connection never becomes a completed job', async () => {
  const h = harness(async () => ({ ok: false, status: 503, json: async () => ({}) }));
  await h.poll();
  assert.equal(h.seen.length, 0); assert.equal(h.errors.length, 1); assert.equal(h.source.closed, true);
});
test('closing a monitor ignores late status replies and releases timers and requests', async () => {
  let resolve;
  const h = harness(() => new Promise(done => { resolve = done; }));
  const pending = h.poll(); h.stop();
  resolve({ ok: true, json: async () => job('complete') }); await pending;
  assert.equal(h.seen.length, 0); assert.equal(h.errors.length, 0); assert.equal(h.cleared(), true);
});

function startFixture(response, flush = async () => {}) {
  const calls = [], streams = [], errors = [], adapting = [];
  const scope = { adaptFile: new Blob(['synthetic PDF fixture']), adaptProjectName: 'Fixture', adaptType: 'Feature Film',
    adaptationStartRef: { current: false }, adaptationMountedRef: { current: true }, adaptationMonitorRef: { current: null },
    flushDraftForTransition: flush, BACKEND_URL: 'https://fixture.invalid', FormData,
    setIsAdapting: value => adapting.push(value), setAdaptProgress: () => {}, setShowAdaptModal: () => {},
    validateAdaptationAcceptance, startAdaptationStream: (...args) => streams.push(args), alert: message => errors.push(message),
    fetch: async (url, options = {}) => {
      calls.push({ url, options });
      return url.endsWith('/capabilities') ? { ok: true, json: async () => ({ contract: 'create-only-v1', create_only: true }) }
        : { ...response, json: async () => response.data };
    },
  };
  return { run: actualHandler('ScreenwritingTab', 'handleStartAdaptation', scope), calls, streams, errors, adapting };
}
test('actual submit handler refuses create-only409 without force, attachment or retries', async () => {
  const f = startFixture({ ok: false, status: 409, data: { detail: 'Project exists' } });
  await f.run();
  assert.equal(f.calls.length, 2);
  assert.equal(f.calls[1].options.body.has('force'), false);
  assert.deepEqual(f.streams, []);
  assert.match(f.errors[0], /choose a new project name/i);
  assert.equal(f.adapting.at(-1), false);
});
test('actual submit handler opens only an acknowledged project/job stream', async () => {
  for (const [data, expected] of [[accepted(), 1], [accepted({ job_id: 'unconfirmed' }), 0]]) {
    const f = startFixture({ ok: true, status: 200, data });
    await f.run();
    assert.equal(f.streams.length, expected);
    if (expected) assert.deepEqual(f.streams[0], ['Fixture', token]);
  }
});
test('actual submit handler retains a dirty draft and fences concurrent uploads', async () => {
  const blocked = startFixture({ ok: true, status: 200, data: accepted() }, async () => { throw Error('Draft not saved'); });
  await blocked.run(); assert.equal(blocked.calls.length, 0); assert.deepEqual(blocked.streams, []);
  let release;
  const f = startFixture({ ok: true, status: 200, data: accepted() }, () => new Promise(done => { release = done; }));
  const first = f.run(); await f.run(); release(); await first;
  assert.equal(f.calls.filter(entry => entry.options.method === 'POST').length, 1);
});
test('actual catalog poll reports disappearance as unverified, never successful completion', async () => {
  const original = job();
  const activeJobRef = { current: original };
  const seen = [];
  const poll = actualHandler('AdaptationStatusBar', 'checkActiveJobs', {
    polling: false, catalogController: null, catalogTimeout: null, AbortController, setTimeout, clearTimeout,
    activeJobRef, actionBusyRef: { current: false }, mounted: true, baseUrl: 'https://fixture.invalid',
    fetch: async () => ({ ok: true, json: async () => ({ jobs: {} }) }),
    updateJob: value => { seen.push(value); activeJobRef.current = value; },
    isAdaptationTerminal, readAdaptationJob, setIsDismissed: () => {}, connectStream: () => {},
    monitorRef: { current: null }, monitorKeyRef: { current: '' },
  });
  await poll(); assert.equal(seen.length, 1);
  assert.equal(seen[0].status, 'processing'); assert.equal(seen[0].progress, 32);
  assert.match(seen[0].connectionError, /completion is unverified/i);
});
test('actual cancel handler never claims success after a rejected ownership check', async () => {
  const original = job();
  const activeJobRef = { current: original }, errors = [], seen = [];
  const handle = actualHandler('AdaptationStatusBar', 'handleAction', {
    activeJobRef, actionBusyRef: { current: false }, setIsChanging: () => {}, baseUrl: 'https://fixture.invalid',
    requestAdaptationAction: (...args) => requestAdaptationAction(...args,
      async () => ({ ok: false, status: 409, json: async () => ({ detail: 'Job changed' }) })),
    monitorRef: { current: null }, monitorKeyRef: { current: '' }, updateJob: value => seen.push(value),
    alert: message => errors.push(message),
  });
  await handle('cancel'); assert.equal(seen.length, 0); assert.equal(activeJobRef.current, original);
  assert.match(errors[0], /not confirmed.*job changed/i);
});
test('actual catalog effect prevents overlapping requests and aborts pending fetch on unmount', async () => {
  const requests = [], replies = [], seen = [];
  let tick;
  let cleared = false;
  const mount = actualHandler('AdaptationStatusBar', 'catalogEffect', {
    activeJobRef: { current: job() }, actionBusyRef: { current: false }, baseUrl: 'https://fixture.invalid',
    fetch: (url, options) => { requests.push({ url, options }); return new Promise(resolve => replies.push(resolve)); },
    setInterval: callback => { tick = callback; return 1; }, clearInterval: () => { cleared = true; },
    setTimeout: (callback, milliseconds) => { assert.equal(milliseconds, 15000); return 2; }, clearTimeout: () => {},
    AbortController, updateJob: value => seen.push(value), setIsDismissed: () => {}, connectStream: () => {},
    readAdaptationJob, isAdaptationTerminal, monitorRef: { current: null }, monitorKeyRef: { current: '' },
  });
  const unmount = mount();
  try {
    assert.equal(requests.length, 1);
    void tick();
    assert.equal(requests.length, 1, 'a pending catalog read must not dispatch another request');
  } finally {
    unmount();
    for (const resolve of replies) resolve({ ok: true, json: async () => ({ jobs: {} }) });
  }
  assert.equal(requests[0].options.signal.aborted, true);
  assert.equal(cleared, true);
  await Promise.resolve(); await Promise.resolve();
  assert.equal(seen.length, 0, 'an unmounted catalog effect must ignore late responses');
});
