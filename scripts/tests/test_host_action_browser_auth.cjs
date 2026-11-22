// Exercise the component request handlers with inert authentication and transport.
// No frontend imports, credentials, network, backend imports, or host commands run.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = process.env.AIBS_AUDIT_SOURCE_ROOT || path.resolve(__dirname, '../..');
const parser = require(path.join(__dirname, '../../frontend/node_modules/@babel/parser'));
const origin = 'https://browser-fixture.invalid';
const fixtures = new Map();

function fixture(name) {
  if (fixtures.has(name)) return fixtures.get(name);
  const source = fs.readFileSync(path.join(root, 'frontend/src/components', name), 'utf8');
  const tree = parser.parse(source, { sourceType: 'module', plugins: ['jsx'] });
  const nodes = [];
  (function walk(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type) nodes.push(node);
    for (const [key, value] of Object.entries(node)) {
      if (['loc', 'comments', 'tokens'].includes(key)) continue;
      if (Array.isArray(value)) value.forEach(walk);
      else walk(value);
    }
  })(tree.program);
  const value = { source, tree, nodes };
  fixtures.set(name, value);
  return value;
}

function handler(component, name, { signedIn = true } = {}) {
  const { source, tree, nodes } = fixture(component);
  const declaration = nodes.find(node => node.type === 'VariableDeclarator' && node.id.name === name);
  assert.ok(declaration?.init, `Actual ${name} handler exists`);
  const requests = [], headerInputs = [], messages = [];
  const noEffect = () => {};
  const scope = {
    activeBackend: origin, backendUrl: origin, chatInput: '', isSendingChat: false,
    selectedModel: 'fixture-model', autonomyMode: 'SAFE', PROMPT: 'fixture> ',
    commandRef: { current: '' }, term: { write: noEffect, writeln: text => messages.push(text) },
    window: { confirm: () => true }, alert: noEffect, errorMessage: error => String(error),
    console: { warn: noEffect, error: noEffect },
    chatAuthHeaders: async (headers = {}) => {
      await Promise.resolve();
      headerInputs.push({ ...headers });
      if (!signedIn) throw new Error('Sign in to use BS-Chat.');
      return { ...headers, Authorization: 'Bearer synthetic-admin', 'X-Fixture': 'awaited' };
    },
    fetch: async (url, options = {}) => {
      requests.push({ url, options });
      // An authenticated caller can still be denied by the backend. No success
      // response or follow-up action is fabricated by this transport fixture.
      return { ok: false, status: 403, json: async () => ({ detail: 'Fixture administrator access denied.' }) };
    },
  };
  for (const node of nodes) {
    if (node.type === 'Identifier' && /^set[A-Z]/.test(node.name)) scope[node.name] = noEffect;
  }
  const helpers = tree.program.body.filter(node => node.type === 'FunctionDeclaration')
    .map(node => source.slice(node.start, node.end)).join('\n');
  const fn = vm.runInNewContext(`(function () { ${helpers}; return (${source.slice(declaration.init.start, declaration.init.end)}); })()`, scope);
  return { fn, requests, headerInputs, messages };
}

const cases = [
  ['TerminalPanel.jsx', 'runCommand', ['Write-Output "original ✓"'], '/api/terminal/run', { command: 'Write-Output "original ✓"' }],
  ['ExecutiveCockpitTab.jsx', 'fetchMatrixStatus', [], '/api/v1/executive/matrix/status'],
  ['ExecutiveCockpitTab.jsx', 'fetchPendingActions', [], '/api/v1/executive/actions/pending'],
  ['ExecutiveCockpitTab.jsx', 'fetchActionHistory', [], '/api/v1/executive/actions/history?limit=25'],
  ['ExecutiveCockpitTab.jsx', 'fetchSentinelAlerts', [], '/api/v1/executive/sentinel/alerts?limit=10'],
  ['ExecutiveCockpitTab.jsx', 'fetchCloudStatus', [], '/api/v1/executive/cloud/status'],
  ['ExecutiveCockpitTab.jsx', 'fetchVoiceStatus', [], '/api/v1/executive/voice/status'],
  ['ExecutiveCockpitTab.jsx', 'handleTriggerSentinelScan', [], '/api/v1/executive/sentinel/scan', null],
  ['ExecutiveCockpitTab.jsx', 'handleExpandMedia', ['fixture-hash', 'reframe_9_16'], '/api/v1/executive/sentinel/expand-media', { file_hash: 'fixture-hash', action: 'reframe_9_16' }],
  ['ExecutiveCockpitTab.jsx', 'handleSendMessage', ['original prompt ✓'], '/api/v1/executive/chat', { prompt: 'original prompt ✓', model: 'fixture-model', autonomy_mode: 'SAFE' }],
  ['ExecutiveCockpitTab.jsx', 'handleResolveAction', ['fixture-id', 'REJECT'], '/api/v1/executive/actions/fixture-id/resolve', { decision: 'REJECT', operator_note: 'Manual resolution via Executive Cockpit HUD.' }],
  ['ExecutiveCockpitTab.jsx', 'handleSetAutonomy', ['SAFE'], '/api/v1/executive/settings/autonomy', { mode: 'SAFE' }],
  ['ExecutiveCockpitTab.jsx', 'handleEmergencyHalt', [], '/api/v1/executive/actions/halt', null],
  ['ExecutiveCockpitTab.jsx', 'handleCreateVibeCheckpoint', [], '/api/v1/executive/vibe-checkpoint', { label: 'Manual Executive Vibe Checkpoint', author: 'Operator' }],
  ['ExecutiveCockpitTab.jsx', 'handleRollbackVibeCheckpoint', [], '/api/v1/executive/vibe-rollback', {}],
];

for (const [component, name, args, route, body] of cases) {
  test(`${name}: actual request awaits identity headers and preserves destination/body`, async () => {
    const state = handler(component, name);
    await state.fn(...args);
    assert.equal(state.headerInputs.length, 1, 'Uses the existing authentication helper once');
    assert.equal(state.requests.length, 1, 'Backend denial causes no automatic retry or alternate route');
    const { url, options } = state.requests[0];
    assert.equal(url, origin + route);
    assert.equal(options.headers?.Authorization, 'Bearer synthetic-admin');
    assert.equal(options.headers?.['X-Fixture'], 'awaited');
    assert.equal(options.method || 'GET', body === undefined ? 'GET' : 'POST');
    if (body && typeof body === 'object') {
      assert.equal(options.headers['Content-Type'], 'application/json');
      assert.deepEqual(JSON.parse(options.body), body);
    } else assert.equal(options.body, undefined);
  });
  test(`${name}: missing identity sends no request`, async () => {
    const state = handler(component, name, { signedIn: false });
    await state.fn(...args);
    assert.equal(state.headerInputs.length, 1);
    assert.equal(state.requests.length, 0, 'No anonymous request, fallback, or retry');
  });
}

test('terminal preserves the backend authentication refusal in its output', async () => {
  const state = handler('TerminalPanel.jsx', 'runCommand');
  await state.fn('synthetic command text only');
  assert.ok(state.messages.some(text => text.includes('API Error 403') && text.includes('Fixture administrator access denied.')));
});

for (const component of ['TerminalPanel.jsx', 'ExecutiveCockpitTab.jsx']) {
  test(`${component}: imports the shared helper and scoped mirrors match`, () => {
    const { source, tree } = fixture(component);
    assert.ok(tree.program.body.some(node => node.type === 'ImportDeclaration' && node.source.value === '/src/utils/chatAuth.js'
      && node.specifiers.some(specifier => specifier.imported?.name === 'chatAuthHeaders' && specifier.local.name === 'chatAuthHeaders')));
    for (const prefix of ['frontend/components', 'frontend/src/components/components', 'frontend/components/components']) {
      assert.equal(fs.readFileSync(path.join(root, prefix, component), 'utf8'), source);
    }
  });
}
