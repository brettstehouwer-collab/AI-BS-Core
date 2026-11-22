/** Actual ChatTab send-handler VM coverage; no mounted browser or provider execution. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import test from 'node:test';
import { isOpenCodeWorkerCommand, requestOpenCodeWorker } from '../../frontend/src/utils/opencodeWorkers.js';

const requireFrontend = createRequire(new URL('../../frontend/package.json', import.meta.url));
const { parse } = requireFrontend('@babel/parser');
const mirrors = [
  'frontend/src/components/ChatTab.jsx',
  'frontend/src/components/components/ChatTab.jsx',
  'frontend/components/ChatTab.jsx',
  'frontend/components/components/ChatTab.jsx',
];

function actualHandler(relativePath) {
  const filename = fileURLToPath(new URL(`../../${relativePath}`, import.meta.url));
  const source = readFileSync(filename, 'utf8');
  const tree = parse(source, { sourceType: 'module', plugins: ['jsx'] });
  const pending = [tree];
  const found = [];
  while (pending.length) {
    const node = pending.pop();
    if (!node || typeof node !== 'object') continue;
    if (node.type === 'VariableDeclarator' && node.id?.name === 'handleSendMessage') found.push(node.init);
    for (const [key, value] of Object.entries(node)) {
      if (key === 'loc' || key === 'comments' || key === 'tokens') continue;
      if (Array.isArray(value)) pending.push(...value);
      else if (value && typeof value === 'object') pending.push(value);
    }
  }
  assert.equal(found.length, 1, `${relativePath}: one actual send handler`);
  assert.equal(found[0].type, 'ArrowFunctionExpression');
  assert.equal(found[0].async, true);
  return { filename, source, initializer: source.slice(found[0].start, found[0].end) };
}

const handlers = mirrors.map(actualHandler);

function taskOfBytes(bytes) {
  const prefix = 'Review the code that can export FDX and convert screenplay PDF; propose fixes only.\n';
  return prefix + 'x'.repeat(bytes - new TextEncoder().encode(prefix).length);
}

function environment(handler, { planOnly = false, behavior = 'completed', sourceStaging = false } = {}) {
  const state = {
    current: true,
    messages: [{ role: 'assistant', content: 'PRIVATE_HISTORY_SENTINEL' }],
    input: 'initial draft', loading: false,
    forbidden: [], requests: [], workerCalls: [], sourceCalls: [], errors: [], attachmentReads: 0,
    clearedTimers: [], timers: new Map(), nextTimer: 0,
  };
  const pdf = Object.freeze({
    name: 'private-original.pdf', type: 'application/pdf', ext: '.pdf', size: 800,
    get content() { state.attachmentReads++; throw new Error('Private attachment body must remain unread.'); },
  });
  state.attachments = sourceStaging ? [] : [pdf];
  const originals = state.attachments;
  const primary = Object.freeze({ provider: 'local', model: 'existing-stehouwer-model' });
  const abortControllerRef = { current: null };
  const forbid = name => (..._args) => {
    state.forbidden.push(name);
    throw new Error(`Unexpected side effect: ${name}`);
  };
  const store = Object.freeze({
    get chatMessages() { return state.messages; },
    aiProvider: primary.provider,
    selectedModel: primary.model,
    setAIProvider: forbid('primary provider mutation'),
    setSelectedModel: forbid('primary model mutation'),
    setActiveTab: forbid('workspace navigation'),
  });
  const fetchImpl = async (url, options) => {
    state.requests.push({ url, options });
    assert.match(url, /^http:\/\/test-only\.invalid\/api\/ai\/opencode\/(?:work|models)$/);
    if (behavior === 'abort' || behavior === 'abort-late-success') abortControllerRef.current.abort();
    if (behavior === 'abort') throw new DOMException('Synthetic cancellation', 'AbortError');
    if (behavior === 'stale') state.current = false;
    if (url.endsWith('/models')) return Response.json({ models: [{ id: 'beam-free', label: 'Beam Free', privacy: '30-day safety retention' }] });
    const body = JSON.parse(options.body);
    return Response.json({ status: 'completed', model: `opencode/${body.model}`,
      content: 'Synthetic worker proposal', receipt: { complete: true, fixture: true } });
  };
  const sandbox = {
    AbortController,
    conversationMemory: { viewReady: true, owner: 'owner-a', conversationId: 'conversation-a', isCurrent: () => state.current },
    footerInput: state.input,
    attachments: originals,
    chatMessages: state.messages,
    isLoading: false,
    isBackendDisabled: false,
    activeTools: { plan_and_review: planOnly },
    isOpenCodeWorkerCommand,
    screenplayWorkflowIntent: sourceStaging ? () => null : forbid('PDF intent interception'),
    isPdfAttachment: forbid('PDF attachment dispatch'),
    selectPdfSource: forbid('PDF source selection'),
    importPdfScreenplay: forbid('PDF import'),
    fetchScreenplayExport: forbid('PDF/FDX export'),
    downloadScreenplayBlob: forbid('download'),
    navigateToScreenplay: forbid('screenplay navigation'),
    attachmentSourceReferences: sourceStaging ? () => [] : forbid('RAG attachment source references'),
    attachmentPromptContent: forbid('attachment body formatting'),
    stageRagSource: sourceStaging ? async options => {
      state.sourceCalls.push(options);
      if (behavior === 'stage-failed') throw new Error('Synthetic source staging failed');
      return { path:'C:\\AI-BS\\test-only-source.txt',
        bytes_written:new TextEncoder().encode(options.text).length, sha256:'a'.repeat(64),
        indexing_status:behavior === 'stage-unindexed' ? 'source_saved_index_unverified' : 'lexical_chunks_indexed',
        chunk_count:1, retrieval_hits:1, indexing_error:'Synthetic index readback unconfirmed' };
    } : forbid('source write/index'),
    indexSavedRagSource: forbid('RAG indexing'),
    searchRagSources: forbid('RAG retrieval'),
    streamBSChatProvider: forbid('primary provider request'),
    fetch: forbid('non-worker request/global memory'),
    useAppStore: { getState: () => store },
    BACKEND_URL: 'http://test-only.invalid',
    chatAuthHeaders: async extra => ({ ...extra, Authorization: 'synthetic-test-only' }),
    abortControllerRef,
    requestOpenCodeWorker: async options => {
      state.workerCalls.push(options);
      return requestOpenCodeWorker({ ...options, fetchImpl });
    },
    errorMessage: error => error?.message || String(error),
    setChatMessages: update => { state.messages = typeof update === 'function' ? update(state.messages) : update; },
    setFooterInput: update => { state.input = typeof update === 'function' ? update(state.input) : update; },
    setAttachments: update => { state.attachments = typeof update === 'function' ? update(state.attachments) : update; },
    setIsLoading: value => { state.loading = value; },
    setErrorPopup: sourceStaging ? value => state.errors.push(value) : forbid('unexpected error popup'),
    setTimeout: (callback, delay) => {
      const id = ++state.nextTimer;
      if (delay === 100) queueMicrotask(callback);
      else state.timers.set(id, callback);
      return id;
    },
    clearTimeout: id => { state.clearedTimers.push(id); state.timers.delete(id); },
  };
  const send = vm.runInNewContext(`(${handler.initializer})`, sandbox, { filename: handler.filename, timeout: 1000 });
  function verifyBoundaries(rawCommand, { networkCount = 1, assistantCount = 1 } = {}) {
    assert.equal(state.requests.length, networkCount);
    assert.equal(state.workerCalls.length, 1, 'actual handler entered only the explicit worker branch');
    assert.deepEqual(state.forbidden, []);
    assert.equal(state.attachmentReads, 0);
    assert.equal(state.attachments, originals, 'ignored PDF attachments remain staged by identity');
    assert.equal(state.attachments[0], pdf);
    assert.deepEqual(primary, { provider: 'local', model: 'existing-stehouwer-model' });
    assert.equal(store.aiProvider, 'local');
    assert.equal(store.selectedModel, 'existing-stehouwer-model');
    assert.equal(state.messages[0].content, 'PRIVATE_HISTORY_SENTINEL', 'previous local history remains intact');
    const user = state.messages.filter(row => row.role === 'user');
    assert.equal(user.length, 1, 'ordinary local chat records the explicit command');
    assert.equal(user[0].content, rawCommand, 'local transcript contains no formatted attachment body');
    assert.equal(user[0].displayContent, rawCommand);
    assert.equal(user[0].attachments.length, 0);
    assert.equal(user[0].source_references.length, 0);
    assert.equal(state.messages.filter(row => row.role === 'assistant').length - 1, assistantCount);
    assert.equal(abortControllerRef.current, null);
    assert.equal(state.timers.size, 0, 'request ceiling timer was cleared');
    if (state.current) assert.equal(state.loading, false);
    for (const request of state.requests) {
      assert.equal(request.options.headers.Authorization, 'synthetic-test-only');
      assert.ok(request.options.signal instanceof AbortSignal);
      if (request.options.method === 'POST') {
        const body = JSON.parse(request.options.body);
        assert.deepEqual(Object.keys(body).sort(), ['model', 'prompt']);
        assert.equal(body.model, 'beam-free');
        assert.ok(!request.options.body.includes('PRIVATE_HISTORY_SENTINEL'));
        assert.ok(!request.options.body.includes('private-original.pdf'));
      }
    }
  }
  function verifySourceBoundaries(rawText, { staged = true, retained = false } = {}) {
    assert.deepEqual(state.forbidden, []);
    assert.equal(state.requests.length, 0, 'no provider or worker network request');
    assert.equal(state.workerCalls.length, 0, 'no worker dispatch');
    assert.equal(state.attachmentReads, 0);
    assert.equal(state.sourceCalls.length, staged ? 1 : 0);
    if (staged) {
      assert.deepEqual(Object.keys(state.sourceCalls[0]).sort(), ['backendUrl','text']);
      assert.equal(state.sourceCalls[0].text, rawText, 'exact source text reaches staging');
      assert.equal(state.sourceCalls[0].backendUrl, 'http://test-only.invalid');
    }
    assert.equal(state.messages[0].content, 'PRIVATE_HISTORY_SENTINEL');
    assert.equal(state.messages.filter(row => row.role==='user').length, 1);
    assert.equal(state.messages.find(row => row.role==='user').displayContent, rawText);
    assert.equal(store.aiProvider, 'local');
    assert.equal(store.selectedModel, 'existing-stehouwer-model');
    assert.equal(state.input, retained ? rawText : '');
    assert.equal(state.loading, false);
    assert.equal(state.timers.size, 0);
  }
  return { state, send, verifyBoundaries, verifySourceBoundaries };
}

test('all four tested mirrors contain the same actual send-handler implementation', () => {
  const hashes = handlers.map(handler => createHash('sha256').update(handler.source).digest('hex'));
  assert.equal(new Set(hashes).size, 1);
  assert.equal(new Set(handlers.map(handler => handler.initializer)).size, 1);
});

for (const handler of handlers) {
  const label = mirrors[handlers.indexOf(handler)];
  for (const behavior of ['completed', 'plan-only', 'stage-failed', 'stage-unindexed']) {
    test(`${label}: ordinary large paste ${behavior} stops before tools or providers`, async () => {
      const rawText = 'Synthetic source é.\n'.repeat(900);
      assert.ok(rawText.trim().length > 16000);
      const planOnly = behavior==='plan-only';
      const env = environment(handler, { sourceStaging:true, planOnly, behavior });
      await env.send(rawText);
      env.verifySourceBoundaries(rawText, { staged:!planOnly, retained:behavior!=='completed' });
      const last = env.state.messages.at(-1).content;
      if (planOnly) assert.match(last, /Plan mode: source was not saved or indexed/);
      else if (behavior==='stage-failed') {
        assert.match(last, /Source staging was not confirmed; analysis stopped and input was retained/);
        assert.equal(env.state.errors.length, 1);
      } else if (behavior==='stage-unindexed') assert.match(last, /parsing\/indexing\/retrieval were not confirmed/);
      else assert.match(last, /No model call or document instruction was executed/);
    });
  }
  for (const bytes of [16384, 32768]) {
    test(`${label}: ${bytes}-byte FDX/PDF task and staged PDF reach only the chosen worker`, async () => {
      const task = taskOfBytes(bytes);
      const command = `  /OPENCODE opencode/beam-free ${task}`;
      const env = environment(handler);
      await env.send(command);
      env.verifyBoundaries(command);
      assert.equal(env.state.requests[0].options.method, 'POST');
      assert.deepEqual(JSON.parse(env.state.requests[0].options.body), { model: 'beam-free', prompt: task });
      assert.match(env.state.messages.at(-1).content, /No project file changes or test results are implied/);
    });
  }

  test(`${label}: plan mode blocks a long worker POST and retains staged PDF`, async () => {
    const command = `/opencode beam-free ${taskOfBytes(20000)}`;
    const env = environment(handler, { planOnly: true });
    await env.send(command);
    env.verifyBoundaries(command, { networkCount: 0 });
    assert.match(env.state.messages.at(-1).content, /Plan mode: no OpenCode worker was invoked/);
  });

  test(`${label}: plan mode permits only catalogue metadata GET`, async () => {
    const command = '  /opencode models';
    const env = environment(handler, { planOnly: true });
    await env.send(command);
    env.verifyBoundaries(command);
    assert.equal(env.state.requests[0].options.body, undefined);
    assert.equal(env.state.requests[0].options.method, undefined);
    assert.match(env.state.messages.at(-1).content, /30-day safety retention/);
  });

  for (const behavior of ['abort', 'abort-late-success', 'stale']) {
    test(`${label}: ${behavior} suppresses late worker output without replay`, async () => {
      const command = '/opencode beam-free Review export FDX code only';
      const env = environment(handler, { behavior });
      await env.send(command);
      env.verifyBoundaries(command, { assistantCount: 0 });
      assert.equal(env.state.requests[0].options.method, 'POST');
    });
  }

  test(`${label}: over-budget worker task is rejected without source staging or provider fallback`, async () => {
    const command = `/opencode beam-free ${taskOfBytes(32769)}`;
    const env = environment(handler);
    await env.send(command);
    env.verifyBoundaries(command, { networkCount: 0 });
    assert.match(env.state.messages.at(-1).content, /exceeds 32 KiB/);
  });
}
