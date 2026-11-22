// Actual component render/handlers with mocked hooks, storage and deferred HTTP.
// No browser, authentication service, provider request or generation is started.
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { transformSync } = require('esbuild');
const filename = process.env.AIBS_PROVIDER_SETTINGS_TEST_SOURCE || path.join(root, 'frontend/src/components/AIProviderSettingsModal.jsx');
const source = await readFile(filename, 'utf8');
const compiled = transformSync(source, { loader: 'jsx', jsx: 'automatic', format: 'cjs', target: 'es2022' }).code;

const fixtureConfig = () => ({ active_provider: 'openai', providers: [
  { id: 'openai', name: 'OpenAI API', icon: 'O', models: ['fixture-a', 'fixture-b'], requires_key: true,
    saved_model: 'fixture-a', is_configured: true },
  { id: 'anthropic', name: 'Anthropic API', icon: 'A', models: ['fixture-other'], requires_key: true,
    saved_model: 'fixture-other', masked_key: '***fixture' },
  { id: 'local', name: 'Local AI', icon: 'L', models: ['fixture-local'], requires_key: false },
] });
const response = data => ({ ok: true, json: async () => data });
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function descendants(element) {
  if (!React.isValidElement(element)) return [];
  return [element, ...React.Children.toArray(element.props.children).flatMap(descendants)];
}
function text(element) {
  if (typeof element === 'string' || typeof element === 'number') return String(element);
  if (!React.isValidElement(element)) return '';
  return React.Children.toArray(element.props.children).map(text).join('');
}

function harness({ headers = async extra => ({ ...extra, Authorization: 'Bearer synthetic-user' }), configRequests } = {}) {
  const slots = [];
  let cursor = 0, dirty = true, tree = null, effects = [];
  const validations = [], storageWrites = [], configCalls = [];
  const props = { isOpen: true, backendUrl: 'http://offline.invalid', onClose: () => updateProps({ isOpen: false }) };
  const hooks = {
    useState(initial) {
      const index = cursor++;
      if (!slots[index]) slots[index] = { value: typeof initial === 'function' ? initial() : initial };
      return [slots[index].value, update => {
        const previous = slots[index].value;
        const next = typeof update === 'function' ? update(previous) : update;
        if (!Object.is(previous, next)) { slots[index].value = next; dirty = true; }
      }];
    },
    useRef(initial) {
      const index = cursor++;
      if (!slots[index]) slots[index] = { current: initial };
      return slots[index];
    },
    useEffect(callback, dependencies) {
      const index = cursor++;
      const previous = slots[index];
      if (!previous || dependencies.some((value, offset) => !Object.is(value, previous.dependencies[offset]))) {
        slots[index] = { dependencies, cleanup: previous?.cleanup };
        effects.push(() => { slots[index].cleanup?.(); slots[index].cleanup = callback(); });
      }
    },
  };
  const fetchMock = async (url, options = {}) => {
    assert.equal(options.headers.Authorization, 'Bearer synthetic-user');
    if (url.endsWith('/api/ai/providers')) {
      configCalls.push(url);
      return configRequests?.[configCalls.length - 1]?.promise || response(fixtureConfig());
    }
    assert.ok(url.endsWith('/api/ai/validate-key'), `Unexpected HTTP request: ${url}`);
    const pending = deferred();
    validations.push({ ...pending, body: JSON.parse(options.body), url });
    return pending.promise;
  };
  const module = { exports: {} };
  const mockedRequire = name => name === 'react' ? { ...React, ...hooks }
    : name === '/src/utils/chatAuth.js' ? { chatAuthHeaders: headers } : require(name);
  new Function('require', 'module', 'exports', 'fetch', 'localStorage', compiled)(mockedRequire, module, module.exports,
    fetchMock, { getItem: () => '{}', setItem: (...args) => storageWrites.push(args) });
  const Component = module.exports.default;
  function render() {
    let rounds = 0;
    do {
      assert.ok(rounds++ < 20, 'Component render did not settle');
      dirty = false; cursor = 0; effects = [];
      tree = Component(props);
      effects.forEach(effect => effect());
    } while (dirty);
  }
  function updateProps(update) { Object.assign(props, update); dirty = true; render(); }
  async function flush() {
    for (let turn = 0; turn < 8; turn++) { await Promise.resolve(); if (dirty) render(); }
  }
  function find(type, predicate = () => true) {
    const found = descendants(tree).find(element => element.type === type && predicate(element));
    assert.ok(found, `Missing rendered ${type}`); return found;
  }
  render();
  return { flush, updateProps, validations, storageWrites, configCalls,
    markup: () => renderToStaticMarkup(tree),
    selectModel(value) { find('select').props.onChange({ target: { value } }); render(); },
    setKey(value) { find('input').props.onChange({ target: { value } }); render(); },
    selectProvider(name) { find('button', element => text(element).includes(name)).props.onClick(); render(); },
    testConnection() { return find('button', element => /Test Connection|Testing\.\.\./.test(text(element))).props.onClick(); },
    cancel() { find('button', element => text(element) === 'Cancel').props.onClick(); },
  };
}

test('rendered validation resets when the selected model changes', async () => {
  const h = harness(); await h.flush();
  const pending = h.testConnection(); await h.flush();
  h.validations[0].resolve(response({ status: 'valid', message: 'fixture-a access checked' }));
  await pending; await h.flush();
  assert.match(h.markup(), /fixture-a access checked/);
  h.selectModel('fixture-b');
  assert.doesNotMatch(h.markup(), /fixture-a access checked/);
});

test('late validation for an earlier model cannot mark the new model valid', async () => {
  const h = harness(); await h.flush();
  const pending = h.testConnection(); await h.flush();
  assert.deepEqual(h.validations[0].body, { provider: 'openai', api_key: '', model: 'fixture-a' });
  h.selectModel('fixture-b');
  h.validations[0].resolve(response({ status: 'valid', message: 'old model was valid' }));
  await pending; await h.flush();
  assert.doesNotMatch(h.markup(), /old model was valid/);
  assert.equal(h.storageWrites.length, 0, 'Validation must not save or activate credentials');
});

test('late key validation and errors are ignored after key edits', async () => {
  for (const reject of [false, true]) {
    const h = harness(); await h.flush(); h.setKey('synthetic-first-key');
    const pending = h.testConnection(); await h.flush();
    h.setKey('synthetic-new-key');
    if (reject) h.validations[0].reject(new Error('synthetic delayed network error'));
    else h.validations[0].resolve(response({ status: 'valid', message: 'old key was valid' }));
    await pending; await h.flush();
    assert.doesNotMatch(h.markup(), /old key was valid|Network error connecting/);
  }
});

test('a newer validation owns its status when earlier responses arrive out of order', async () => {
  const h = harness(); await h.flush();
  const older = h.testConnection(); await h.flush(); h.selectModel('fixture-b');
  const newer = h.testConnection(); await h.flush();
  h.validations[1].resolve(response({ status: 'valid', message: 'current model checked' }));
  await newer; await h.flush();
  h.validations[0].resolve(response({ status: 'error', message: 'stale error must disappear' }));
  await older; await h.flush();
  assert.match(h.markup(), /current model checked/);
  assert.doesNotMatch(h.markup(), /stale error must disappear/);
});

test('closing and reopening removes old receipts and ignores responses from the prior opening', async () => {
  const h = harness(); await h.flush();
  const pending = h.testConnection(); await h.flush(); h.cancel();
  assert.equal(h.markup(), '');
  h.updateProps({ isOpen: true }); await h.flush();
  h.validations[0].resolve(response({ status: 'valid', message: 'previous opening checked' }));
  await pending; await h.flush();
  assert.doesNotMatch(h.markup(), /previous opening checked/);
});

test('editing away and back cannot revive an earlier validation snapshot', async () => {
  const h = harness(); await h.flush();
  const pending = h.testConnection(); await h.flush();
  h.selectModel('fixture-b'); h.selectModel('fixture-a');
  h.validations[0].resolve(response({ status: 'valid', message: 'revived old result' }));
  await pending; await h.flush();
  assert.doesNotMatch(h.markup(), /revived old result/);
});

test('changing backend invalidates its pending receipt and a closed receipt stays cleared after reopen', async () => {
  const h = harness(); await h.flush();
  const older = h.testConnection(); await h.flush();
  h.updateProps({ backendUrl: 'http://second-offline.invalid' }); await h.flush();
  h.validations[0].resolve(response({ status: 'valid', message: 'previous backend result' }));
  await older; await h.flush();
  assert.doesNotMatch(h.markup(), /previous backend result/);
  const newer = h.testConnection(); await h.flush();
  h.validations[1].resolve(response({ status: 'valid', message: 'current backend result' }));
  await newer; await h.flush();
  assert.match(h.markup(), /current backend result/);
  h.cancel(); h.updateProps({ isOpen: true }); await h.flush();
  assert.doesNotMatch(h.markup(), /current backend result/);
});

test('late configuration from a prior opening cannot overwrite the reopened model', async () => {
  const first = deferred();
  const next = fixtureConfig(); next.providers[0].saved_model = 'fixture-b';
  const second = { promise: Promise.resolve(response(next)) };
  const h = harness({ configRequests: [first, second] }); await h.flush();
  h.cancel(); h.updateProps({ isOpen: true }); await h.flush();
  assert.match(h.markup(), /value="fixture-b" selected=""/);
  first.resolve(response(fixtureConfig())); await h.flush();
  assert.match(h.markup(), /value="fixture-b" selected=""/);
});

test('authentication that resolves after a model edit does not dispatch stale validation', async () => {
  const token = deferred(); let headersCalls = 0;
  const h = harness({ headers: extra => ++headersCalls === 1
    ? Promise.resolve({ ...extra, Authorization: 'Bearer synthetic-user' }) : token.promise });
  await h.flush();
  const pending = h.testConnection(); h.selectModel('fixture-b');
  token.resolve({ Authorization: 'Bearer synthetic-user' });
  await h.flush();
  if (h.validations.length) h.validations[0].resolve(response({ status: 'valid', message: 'stale auth response' }));
  await pending; await h.flush();
  assert.equal(h.validations.length, 0);
});

test('model-access-only receipt preserves backend explanation and does not imply generation verification', async () => {
  const h = harness(); await h.flush();
  const pending = h.testConnection(); await h.flush();
  h.validations[0].resolve(response({ status: 'valid', generation_verified: false,
    message: 'Selected model is listed for the configured connection.' }));
  await pending; await h.flush();
  assert.match(h.markup(), /Selected model is listed for the configured connection/);
  assert.match(h.markup(), /Text generation (?:has not been verified|was not tested)/);
});

test('canonical provider settings and its existing mirrors match byte for byte', async () => {
  const paths = ['src/components/', 'components/', 'src/components/components/', 'components/components/'];
  const copies = await Promise.all(paths.map(directory => readFile(path.join(root, 'frontend', directory, 'AIProviderSettingsModal.jsx'))));
  copies.slice(1).forEach(copy => assert.ok(copy.equals(copies[0])));
});
