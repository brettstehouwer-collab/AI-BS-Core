import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';
import { createAccountingSession } from '../../frontend/src/utils/accountingSession.js';

const frontend = fileURLToPath(new URL('../../frontend/', import.meta.url));
const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const held = () => ({ schema_version: 1, status: 'unavailable',
  reason: 'Verified owned compute receipts and treasury records are unavailable.',
  payouts_enabled: false, job_dispatch_enabled: false, registration_enabled: false,
  ledger: { total_earned_usd: null, pending_usd: null, redeemed_usd: null, total_compute_hours: null },
  hardware: null, treasury: null, idle_policy: { status: 'unavailable', enforced: false } });
const tick = () => new Promise(resolve => setImmediate(resolve));
const utilities = () => import('../../frontend/src/utils/networkWorkspace.js');

async function component(name) {
  const { build } = require('esbuild');
  const result = await build({ absWorkingDir: frontend, entryPoints: [`components/${name}.jsx`],
    bundle: true, write: false, platform: 'node', format: 'cjs', external: ['react'], logLevel: 'silent',
    plugins: [{ name: 'offline-network-fixtures', setup(builder) {
      builder.onResolve({ filter: /FinancialAccountBoundary\.jsx$/ }, () => ({ path: 'boundary', namespace: 'fixture' }));
      builder.onResolve({ filter: /^(firebase\/auth)$|(^|\/)firebase\.js$/ }, () => ({ path: 'auth', namespace: 'fixture' }));
      builder.onResolve({ filter: /\/(VisualScriptingTab|StudioWorkspaceTab|PlaywrightTab|VideoStudioTab|ComfyUIStudio)\.jsx$/ }, () => ({ path: 'tool', namespace: 'fixture' }));
      builder.onLoad({ filter: /.*/, namespace: 'fixture' }, args => ({ contents: args.path === 'boundary'
        ? 'export default function Boundary({children}) { return children(async()=>{throw Error("No requests during SSR")}); }'
        : args.path === 'auth'
          ? 'export const auth={currentUser:null};export const onAuthStateChanged=()=>{throw Error("No auth effects during SSR")};'
          : 'export default function Tool(){return null;}' }));
      builder.onResolve({ filter: /^\/src\// }, args => ({ path: frontend + args.path.slice(1) }));
    } }],
  });
  const module = { exports: {} };
  new Function('require', 'module', 'exports', result.outputFiles[0].text)(require, module, module.exports);
  return module.exports;
}

test('actual Network rendering has unavailable metrics and held dispatch without fabricated activity', async () => {
  const module = await component('GpuNetworkTab');
  const markup = renderToStaticMarkup(React.createElement(module.default, { backendUrl: 'http://offline.invalid' }));
  assert.ok(/Unavailable/.test(markup), 'Missing unavailable state');
  assert.ok(/Payouts held/.test(markup), 'Missing payout hold');
  assert.ok(/Job dispatch held/.test(markup), 'Missing job hold');
  assert.ok(/Idle policy: Unavailable/.test(markup), 'Missing idle-policy unavailable state');
  assert.ok((markup.match(/disabled=""/g) || []).length >= 2);
  assert.ok(!/\$[0-9]|RTX4090-Desktop|IDLE &amp; COMPUTING|Optimal Cooling|Node Assigned|Connecting to Polygon|Active Polygon Deposit/.test(markup), 'Unsupported live or monetary claim');
});

test('actual Network error view remains unavailable and offers explicit retry', async () => {
  const module = await component('GpuNetworkTab');
  const markup = renderToStaticMarkup(React.createElement(module.NetworkWorkspaceView, {
    state: { status: 'error', error: 'Network status is unavailable. Refresh to retry.' }, onRefresh() {},
  }));
  assert.match(markup, /role="alert"/); assert.match(markup, /Refresh status/);
  assert.match(markup, /Unavailable/); assert.doesNotMatch(markup, /\$[0-9]|Connecting|Active|Processing Payout/);
});

test('network reads reject fabricated, partial, enabled and wrong-version contracts', async () => {
  const { validateNetworkAvailability } = await utilities();
  assert.doesNotThrow(() => validateNetworkAvailability(held()));
  for (const value of [null, {}, { ...held(), schema_version: 2 }, { ...held(), status: 'success' },
    { ...held(), payouts_enabled: true }, { ...held(), job_dispatch_enabled: true },
    { ...held(), registration_enabled: true }, { ...held(), hardware: {} }, { ...held(), treasury: {} },
    { ...held(), ledger: { ...held().ledger, pending_usd: '0.00' } },
    { ...held(), idle_policy: { status: 'unavailable', enforced: true } }]) {
    assert.throws(() => validateNetworkAvailability(value));
  }
});

test('real shared session supplies auth, no-store and timeout to the only read endpoint', async () => {
  const { createNetworkWorkspaceLoader } = await utilities();
  let calls = 0; const events = [];
  const session = createAccountingSession({ uid: 'fixture-owner', currentUid: () => 'fixture-owner',
    getHeaders: async () => ({ Authorization: 'Bearer offline-fixture' }), fetchImpl: async (url, options) => {
      calls++; assert.equal(url, 'http://offline.invalid/v1/network/earnings/held-node');
      assert.equal(options.method, 'GET'); assert.equal(options.cache, 'no-store');
      assert.equal(options.headers.Authorization, 'Bearer offline-fixture'); assert.ok(options.signal);
      return { ok: true, status: 200, json: async () => held() };
    } });
  const loader = createNetworkWorkspaceLoader({ request: session.request, backendUrl: 'http://offline.invalid/', onState: state => events.push(state) });
  await loader.refresh(); assert.equal(calls, 1); assert.equal(events.at(-1).status, 'unavailable');
  assert.equal(events.at(-1).data, undefined); loader.stop(); session.dispose();
});

test('overlap is suppressed and stopped generations never publish late state', async () => {
  const { createNetworkWorkspaceLoader } = await utilities();
  let finish; let calls = 0; const events = [];
  const loader = createNetworkWorkspaceLoader({ backendUrl: '', onState: state => events.push(state),
    request: async () => { calls++; return new Promise(resolve => { finish = resolve; }); } });
  const first = loader.refresh(); const second = loader.refresh(); assert.equal(calls, 1);
  loader.stop(); finish({ json: async () => held() }); await Promise.all([first, second]);
  assert.deepEqual(events.map(state => state.status), ['loading']);
  await loader.refresh(); assert.equal(calls, 1);
});

test('authorization and malformed-body failures become persistent sanitized unavailable states', async () => {
  const { createNetworkWorkspaceLoader } = await utilities();
  for (const response of [{ json: async () => ({ status: 'success', ledger: { pending_usd: 50 } }) },
    { json: async () => { throw new Error('private provider detail'); } }, null]) {
    const events = [];
    const loader = createNetworkWorkspaceLoader({ backendUrl: '', onState: state => events.push(state), request: async () => {
      if (!response) throw new Error('private credential detail'); return response;
    } });
    await loader.refresh(); assert.equal(events.at(-1).status, 'error');
    assert.match(events.at(-1).error, /unavailable/i); assert.doesNotMatch(events.at(-1).error, /private|provider detail|credential detail/);
    loader.stop();
  }
});

test('timeout settles despite ignored abort, and a later refresh can recover', async () => {
  const { createNetworkWorkspaceLoader } = await utilities();
  let calls = 0; const events = [];
  const session = createAccountingSession({ uid: 'a', currentUid: () => 'a', timeoutMs: 10,
    getHeaders: async () => ({ Authorization: 'Bearer offline-fixture' }), fetchImpl: async () => {
      if (++calls === 1) return new Promise(() => {});
      return { ok: true, status: 200, json: async () => held() };
    } });
  const loader = createNetworkWorkspaceLoader({ request: session.request, backendUrl: '', onState: state => events.push(state) });
  await loader.refresh(); assert.equal(events.at(-1).status, 'error');
  await loader.refresh(); assert.equal(events.at(-1).status, 'unavailable');
  loader.stop(); session.dispose();
});

test('owner change while token resolves cannot dispatch or publish private data', async () => {
  const { createNetworkWorkspaceLoader } = await utilities();
  let owner = 'a'; let token; let calls = 0; const events = [];
  const session = createAccountingSession({ uid: 'a', currentUid: () => owner,
    getHeaders: () => new Promise(resolve => { token = resolve; }), fetchImpl: async () => { calls++; } });
  const loader = createNetworkWorkspaceLoader({ request: session.request, backendUrl: '', onState: state => events.push(state) });
  const pending = loader.refresh(); owner = 'b'; loader.stop(); session.dispose();
  token({ Authorization: 'Bearer offline-fixture' }); await pending; await tick();
  assert.equal(calls, 0); assert.deepEqual(events.map(state => state.status), ['loading']);
});

test('Creation route preserves existing tools and distinguishes stale Network and unknown links', async () => {
  const { resolveCreationTool } = await utilities();
  assert.equal(resolveCreationTool(''), 'playwright');
  for (const tool of ['playwright', 'video', 'comfyui', 'visual', 'network']) assert.equal(resolveCreationTool(`?subtab=${tool}`), tool);
  assert.equal(resolveCreationTool('?subtab=missing'), 'unknown');
});

test('actual stale Creation Network link has a clear destination without opening the writer', async () => {
  const module = await component('UniversalCreationSuite');
  const previous = globalThis.window;
  const previousStorage = globalThis.sessionStorage;
  try {
    globalThis.window = { location: { search: '?tab=unified_creation&subtab=network', hostname: 'localhost', protocol: 'http:' } };
    globalThis.sessionStorage = { getItem: () => null };
    const markup = renderToStaticMarkup(React.createElement(module.default));
    assert.ok(/unified_crypto&amp;subtab=network/.test(markup), 'Missing correct Network destination');
    assert.ok(/GPU Network/.test(markup), 'Missing Network route explanation');
    assert.ok(!/Password|Identity Verified|Writing Studio|Loading Tool/.test(markup), 'Stale route opened an unrelated or browser-locked tool');
  } finally {
    if (previous === undefined) delete globalThis.window; else globalThis.window = previous;
    if (previousStorage === undefined) delete globalThis.sessionStorage; else globalThis.sessionStorage = previousStorage;
  }
});

test('Creation signed-out view never grants access through a name or local browser state', async () => {
  const module = await component('UniversalCreationSuite');
  const markup = renderToStaticMarkup(React.createElement(module.default, { currentUser: { email: 'julie-fixture@example.invalid' } }));
  assert.ok(/Sign in/.test(markup), 'Verified sign-in is required');
  assert.ok(!/Password|Identity Verified|CREATION SUITE|Loading Tool/.test(markup), 'Client identity label granted workspace access');
});

test('four mirrors retain the same safe implementation and no simulated execution controls', async () => {
  for (const name of ['GpuNetworkTab', 'UniversalCreationSuite']) {
    const paths = ['components/', 'src/components/', 'components/components/', 'src/components/components/'];
    const texts = await Promise.all(paths.map(path => readFile(new URL(`../../frontend/${path}${name}.jsx`, import.meta.url), 'utf8')));
    for (const text of texts.slice(1)) assert.equal(text, texts[0]);
    if (name === 'GpuNetworkTab') {
      assert.ok(/FinancialAccountBoundary/.test(texts[0]), 'Network owner boundary is required');
      assert.ok(!/setInterval|Math\.random|fetch\(|redeem-payout|submit-job|setIsIdleOnly/.test(texts[0]), 'Network dispatch or simulation code remains');
    } else {
      assert.ok(/onAuthStateChanged/.test(texts[0]), 'Creation must observe verified identity');
      assert.ok(!/enteredPassword|AUTHORIZED_EMAILS|JULIE_EMAILS|sessionStorage|userEmail\.includes|isLocalDev/.test(texts[0]), 'Browser privilege or password rule remains');
      for (const label of ['Writing Studio', 'Video Studio', 'ComfyUI Studio', 'Visual Scripting']) assert.ok(texts[0].includes(label));
    }
  }
});

test('actual hardware view preserves fan controls and shows unavailable missing telemetry', async () => {
  const module = await component('GpuHardwareTelemetryTab');
  const markup = renderToStaticMarkup(React.createElement(module.default, { backendUrl: 'http://offline.invalid' }));
  assert.ok(/Unavailable/.test(markup), 'Missing sensor values must remain unavailable');
  assert.ok(/Lock Fans 100%/.test(markup) && /Auto Curve/.test(markup), 'Legitimate hardware controls must remain available');
  assert.ok(!/32°C|Frosty \/ Optimal|Simulated \/ Standby|Active Compute Pipeline|Doctor Sentinel Enabled/.test(markup), 'Missing hardware data must not fabricate a safety or activity state');
});

test('fan control uses shared verified session with exact manual and automatic payloads', async () => {
  const { requestFanControl } = await utilities();
  const seen = [];
  const session = createAccountingSession({ uid: 'a', currentUid: () => 'a',
    getHeaders: async () => ({ Authorization: 'Bearer offline-fixture' }), fetchImpl: async (url, options) => {
      seen.push({ url, options });
      return { ok: true, status: 200, json: async () => ({ status: 'success', result: { success: true, message: 'Offline acknowledgement' } }) };
    } });
  for (const [speed, auto] of [[100, false], [30, false], [0, true]]) {
    await requestFanControl({ request: session.request, backendUrl: 'http://offline.invalid/', speed, auto });
  }
  assert.equal(seen.length, 3);
  for (const call of seen) {
    assert.equal(call.url, 'http://offline.invalid/api/v1/hardware/gpu/fan-control');
    assert.equal(call.options.method, 'POST'); assert.equal(call.options.cache, 'no-store');
    assert.equal(call.options.headers.Authorization, 'Bearer offline-fixture');
    assert.ok(call.options.headers['Idempotency-Key']); assert.ok(call.options.signal);
  }
  assert.deepEqual(seen.map(call => JSON.parse(call.options.body)), [{ speed: 100, auto: false }, { speed: 30, auto: false }, { speed: 0, auto: true }]);
  session.dispose();
});

test('fan requests reject unsafe/coerced inputs and invalid success claims', async () => {
  const { requestFanControl } = await utilities(); let calls = 0;
  for (const [speed, auto] of [[29, false], [101, false], [-1, true], ['100', false], [true, false], [100, 'false']]) {
    await assert.rejects(requestFanControl({ request: async () => { calls++; }, speed, auto }));
  }
  assert.equal(calls, 0);
  await assert.rejects(requestFanControl({ request: async () => ({ json: async () => ({ status: 'success', result: { success: false } }) }), speed: 100, auto: false }));
  const warning = await requestFanControl({ request: async () => ({ json: async () => ({ status: 'warning', result: { success: false, message: 'Offline driver unavailable' } }) }), speed: 0, auto: true });
  assert.equal(warning.success, false); assert.equal(warning.message, 'Offline driver unavailable');
});

test('all four hardware mirrors use the owner boundary without hardcoded endpoint or direct fetch', async () => {
  const paths = ['components/', 'src/components/', 'components/components/', 'src/components/components/'];
  const texts = await Promise.all(paths.map(path => readFile(new URL(`../../frontend/${path}GpuHardwareTelemetryTab.jsx`, import.meta.url), 'utf8')));
  for (const text of texts.slice(1)) assert.equal(text, texts[0]);
  assert.ok(/FinancialAccountBoundary/.test(texts[0]), 'Hardware controls require the verified owner boundary');
  assert.ok(/requestFanControl/.test(texts[0]), 'Hardware controls require the validated session helper');
  assert.ok(!/fetch\(|http:\/\/127\.0\.0\.1|setInterval/.test(texts[0]), 'Hardware requests must use bounded authenticated sessions and nonoverlapping polling');
});

test('hardware metric presentation requires a measured per-field receipt, preserving verified zero', async () => {
  const { reportedHardwareValue } = await utilities();
  const measured = { nvml_online: true, fan_speed_pct: 0, field_status: { fan_speed_pct: 'measured' } };
  assert.equal(reportedHardwareValue(measured, 'fan_speed_pct', 100), 0);
  for (const value of [null, { ...measured, nvml_online: false }, { ...measured, field_status: {} },
    { ...measured, fan_speed_pct: '100' }, { ...measured, fan_speed_pct: 101 }]) {
    assert.equal(reportedHardwareValue(value, 'fan_speed_pct', 100), null);
  }
});

test('fan acknowledgement explicitly separates accepted request from verified enforcement', async () => {
  const { requestFanControl } = await utilities();
  for (const enforcement_verified of [false, true]) {
    const result = await requestFanControl({ speed: 100, auto: false,
      request: async () => ({ json: async () => ({ status: 'success',
        result: { success: true, enforcement_verified, message: 'Offline acknowledgement' } }) }) });
    assert.equal(result.enforcement_verified, enforcement_verified);
  }
});
