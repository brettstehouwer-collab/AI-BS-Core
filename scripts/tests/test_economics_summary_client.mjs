import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createEconomicsPoller, readEconomicsSummary, presentEconomicsMetric } from '../../frontend/src/utils/economicsSummary.js';

const now = Date.parse('2026-10-30T12:00:00Z');
const at = delta => new Date(now + delta).toISOString();
const summary = metrics => ({ schema: 'aibs.economics.summary.v1', status: 'unavailable',
  currency: 'USD', timestamp: at(0), window: { start: at(-30 * 86400000), end: at(0), coverage: 'unconfirmed' }, metrics });
const verified = (value, unit = 'USD') => ({ status: 'verified', verification: 'reconciled',
  value, unit, source: 'synthetic reconciliation receipt', observed_at: at(0), fresh_until: at(60000) });

test('missing, null, unverified, wrong-unit and malformed values stay unavailable', () => {
  for (const metric of [null, {}, { value: 0 }, { ...verified('0.00'), status: 'unavailable' },
    { ...verified('0.00'), verification: 'not_verified' }, { ...verified('0.00'), source: null },
    verified('NaN'), verified('Infinity'), verified(true), verified(0.1), verified('1.234'),
    verified('0.00', 'kWh'), verified('1e2'), verified('0001.00'), verified('-0.00')]) {
    assert.equal(presentEconomicsMetric(metric, 'USD', now).value, 'Unavailable');
  }
});

test('verified zero, losses and large exact decimal strings render without binary rounding', () => {
  assert.equal(presentEconomicsMetric(verified('0.00'), 'USD', now).value, '$0.00');
  assert.equal(presentEconomicsMetric(verified('-123.45'), 'USD', now).value, '-$123.45');
  assert.equal(presentEconomicsMetric(verified('9007199254740993.01'), 'USD', now).value, '$9,007,199,254,740,993.01');
  assert.equal(presentEconomicsMetric(verified('0', 'count'), 'count', now).value, '0');
  assert.equal(presentEconomicsMetric(verified('-1', 'count'), 'count', now).value, 'Unavailable');
});

test('stale, expired, future or undated evidence never appears current', () => {
  for (const metric of [{ ...verified('1.00'), status: 'stale' },
    { ...verified('1.00'), fresh_until: at(-1) }, { ...verified('1.00'), observed_at: at(60001) },
    { ...verified('1.00'), observed_at: null }, { ...verified('1.00'), fresh_until: null }]) {
    assert.notEqual(presentEconomicsMetric(metric, 'USD', now).value, '$1.00');
  }
});

test('reader rejects legacy successful mocks, wrong currency, stale or invalid summary windows', async () => {
  for (const payload of [{ status: 'success', data: { revenue: { total_revenue: 14500 } } },
    { ...summary({}), currency: 'EUR' }, { ...summary({}), timestamp: at(-120001) },
    { ...summary({}), timestamp: at(60001) }, { ...summary({}), window: { start: at(1), end: at(0) } },
    { ...summary({}), metrics: [] }]) {
    await assert.rejects(readEconomicsSummary({ apiBase: '', getHeaders: async () => ({}), now: () => now,
      fetchImpl: async () => ({ ok: true, json: async () => payload }) }));
  }
});

test('reader sends authentication and no-store, preserves unavailable state and propagates failures', async () => {
  let request;
  const controller = new AbortController();
  const payload = summary({ 'revenue.total_volume_30d': { status: 'unavailable', value: null } });
  assert.deepEqual(await readEconomicsSummary({ apiBase: 'http://127.0.0.1:8080/',
    getHeaders: async () => ({ Authorization: 'Bearer synthetic' }), signal: controller.signal, now: () => now,
    fetchImpl: async (url, options) => { request = { url, options }; return { ok: true, json: async () => payload }; },
  }), payload);
  assert.equal(request.url, 'http://127.0.0.1:8080/api/v1/economics/summary');
  assert.equal(request.options.cache, 'no-store');
  assert.equal(request.options.headers.Authorization, 'Bearer synthetic');
  assert.equal(request.options.signal, controller.signal);
  await assert.rejects(readEconomicsSummary({ getHeaders: async () => { throw Error('signed out'); },
    fetchImpl: async () => assert.fail('unauthenticated fetch'), now: () => now }));
  await assert.rejects(readEconomicsSummary({ getHeaders: async () => ({}),
    fetchImpl: async () => ({ ok: false, status: 403 }), now: () => now }), /403/);
});

const tick = () => new Promise(resolve => setImmediate(resolve));
function harness(request) {
  const timers = new Map(); let id = 0; const events = [];
  const poller = createEconomicsPoller({ request, onState: state => events.push(state),
    setTimer: (fn, delay) => { timers.set(++id, { fn, delay }); return id; },
    clearTimer: key => timers.delete(key) });
  const fire = delay => { const item = [...timers].find(([, value]) => value.delay === delay);
    assert.ok(item, `missing timer ${delay}`); timers.delete(item[0]); item[1].fn(); };
  return { poller, events, timers, fire };
}

test('polling serializes requests, times out a hung operation and ignores late results', async () => {
  let resolve; let calls = 0; let firstSignal;
  const h = harness(({ signal }) => { calls++; firstSignal = signal; return new Promise(r => { resolve = r; }); });
  h.poller.start(); h.poller.start(); await tick();
  assert.equal(calls, 1);
  assert.equal([...h.timers.values()].some(t => t.delay === 30000), false);
  h.fire(8000); await tick();
  assert.equal(firstSignal.aborted, true);
  assert.equal(h.events.at(-1).status, 'error');
  assert.equal(h.events.at(-1).summary, null);
  h.poller.stop(); resolve(summary({})); await tick();
  assert.notEqual(h.events.at(-1).status, 'ready');
});

test('a successful retry clears an earlier error; stop prevents further requests or publications', async () => {
  let calls = 0;
  const h = harness(async () => { if (++calls === 1) throw Error('offline'); return summary({}); });
  h.poller.start(); await tick(); assert.equal(h.events.at(-1).status, 'error');
  h.fire(30000); await tick();
  assert.equal(h.events.at(-1).status, 'ready'); assert.equal(h.events.at(-1).error, null);
  h.poller.stop(); assert.equal(h.timers.size, 0);
});

test('aborted or changed identity during token lookup never dispatches a financial request', async () => {
  for (const change of ['abort', 'identity']) {
    let finish; let current = true; let calls = 0;
    const controller = new AbortController();
    const pending = readEconomicsSummary({ signal: controller.signal, now: () => now,
      isCurrentIdentity: () => current,
      getHeaders: () => new Promise(resolve => { finish = resolve; }),
      fetchImpl: async () => { calls++; return { ok: true, json: async () => summary({}) }; } });
    if (change === 'abort') controller.abort(); else current = false;
    finish({ Authorization: 'Bearer synthetic' });
    await assert.rejects(pending);
    assert.equal(calls, 0);
  }
});

test('stop and restart discards the old generation without disturbing the new request', async () => {
  const pending = [];
  const h = harness(({ signal }) => new Promise(resolve => pending.push({ signal, resolve })));
  h.poller.start(); await tick(); h.poller.stop(); h.poller.start(); await tick();
  assert.equal(pending[0].signal.aborted, true);
  pending[0].resolve(summary({ old: true })); await tick();
  assert.equal(h.events.at(-1).status, 'loading');
  assert.equal([...h.timers.values()].filter(t => t.delay === 8000).length, 1);
  pending[1].resolve(summary({ current: true })); await tick();
  assert.deepEqual(h.events.at(-1).summary.metrics, { current: true });
  assert.equal(h.timers.size, 1); h.poller.stop();
});

test('timeout retry succeeds and a late first response cannot replace it', async () => {
  const pending = [];
  const h = harness(() => new Promise(resolve => pending.push(resolve)));
  h.poller.start(); await tick(); h.fire(8000); await tick(); h.fire(30000); await tick();
  pending[1](summary({ current: true })); await tick();
  pending[0](summary({ old: true })); await tick();
  assert.deepEqual(h.events.at(-1).summary.metrics, { current: true }); h.poller.stop();
});

test('authorization failure removes a ready summary and explains account access', async () => {
  let calls = 0;
  const h = harness(async () => {
    if (++calls === 1) return summary({ 'revenue.total_volume_30d': verified('0.00') });
    throw Object.assign(new Error('denied'), { status: 403 });
  });
  h.poller.start(); await tick(); h.fire(30000); await tick();
  assert.equal(h.events.at(-1).summary, null);
  assert.match(h.events.at(-1).error, /authorized account/i); h.poller.stop();
});

test('rendered financial states show unavailable or exact verified evidence without fabricated charts', async () => {
  const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
  const { build } = require('esbuild');
  const React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const frontend = fileURLToPath(new URL('../../frontend/', import.meta.url));
  const result = await build({ absWorkingDir: frontend, entryPoints: ['src/components/EconomicsSummaryPanel.jsx'],
    bundle: true, write: false, jsx: 'automatic', platform: 'node', format: 'cjs', external: ['react'], logLevel: 'silent',
    plugins: [{ name: 'offline-auth', setup(builder) {
      builder.onResolve({ filter: /^(firebase\/auth)$|(^|\/)firebase\.js$/ }, () => ({ path: 'auth', namespace: 'fixture' }));
      builder.onLoad({ filter: /.*/, namespace: 'fixture' }, () => ({ contents: 'export const auth={currentUser:null}; export const onAuthStateChanged=()=>{throw Error("auth should not run in view test")};' }));
      builder.onResolve({ filter: /^\/src\// }, args => {
        const path = frontend + args.path.slice(1);
        return { path: /\.[cm]?[jt]sx?$/.test(path) ? path : path + '.js' };
      });
    } }],
  });
  const module = { exports: {} };
  new Function('require', 'module', 'exports', result.outputFiles[0].text)(require, module, module.exports);
  const view = state => renderToStaticMarkup(React.createElement(module.exports.EconomicsSummaryView, { state, clock: now, title: 'Finance records' }));
  for (const state of [{ status: 'signed_out' }, { status: 'error', error: 'Financial records are unavailable.' },
    { status: 'ready', summary: summary({}) },
    { status: 'ready', summary: summary({ 'revenue.total_volume_30d': { ...verified('12.00'), fresh_until: at(-1) } }) }]) {
    const markup = view(state);
    assert.match(markup, /Unavailable/); assert.doesNotMatch(markup, /\$|<svg|Live Sync|12%|<canvas/);
  }
  const zero = view({ status: 'ready', summary: summary({ 'revenue.total_volume_30d': verified('0.00') }) });
  assert.match(zero, /\$0\.00/); assert.match(zero, /synthetic reconciliation receipt/);
});

test('manual accounting never presents missing totals, provider payouts or tax formulas as verified', async () => {
  const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
  const { build } = require('esbuild'); const React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const frontend = fileURLToPath(new URL('../../frontend/', import.meta.url));
  const result = await build({ absWorkingDir: frontend,
    entryPoints: ['src/components/MasterAccountingTab.jsx'], bundle: true, write: false, jsx: 'automatic',
    platform: 'node', format: 'cjs', external: ['react'], logLevel: 'silent',
    plugins:[{name:'offline-boundary',setup(builder){
      builder.onResolve({filter:/FinancialAccountBoundary\.jsx$/},()=>({path:'boundary',namespace:'fixture'}));
      builder.onLoad({filter:/.*/,namespace:'fixture'},()=>({contents:'export default function Boundary({children}) { return children(async()=>{throw Error("No requests during SSR")}); }'}));
      builder.onResolve({filter:/^\/src\//},args=>({path:frontend+args.path.slice(1)}));
    }}] });
  const module = { exports: {} };
  new Function('require', 'module', 'exports', result.outputFiles[0].text)(require, module, module.exports);
  const markup = renderToStaticMarkup(React.createElement(module.exports.default, { backendUrl: 'http://offline.invalid' }));
  assert.match(markup, /Unavailable/);
  assert.match(markup, /unreconciled/i);
  assert.doesNotMatch(markup, /\$0\.00|PayPal &amp; API Payouts|> Authorized|4\.25%/);
  const tax = renderToStaticMarkup(React.createElement(module.exports.AccountingTaxAvailability));
  assert.match(tax, /Unavailable/); assert.doesNotMatch(tax, /\$|4\.25%|15\.3%/);
});


test('manual crypto UI holds missing totals, bank links and wallet evidence', async () => {
  const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
  const {build}=require('esbuild');const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');
  const frontend=fileURLToPath(new URL('../../frontend/',import.meta.url));
  const result=await build({absWorkingDir:frontend,entryPoints:['src/components/CryptoAccountingTab.jsx'],bundle:true,write:false,jsx:'automatic',
    platform:'node',format:'cjs',external:['react'],logLevel:'silent',plugins:[{name:'offline-boundary',setup(builder){
      builder.onResolve({filter:/FinancialAccountBoundary\.jsx$/},()=>({path:'boundary',namespace:'fixture'}));
      builder.onLoad({filter:/.*/,namespace:'fixture'},()=>({contents:'export default function Boundary({children}) { return children(async()=>{throw Error("No requests during SSR")}); }'}));
      builder.onResolve({filter:/^\/src\//},args=>({path:frontend+args.path.slice(1)}));
    }}]});
  const module={exports:{}};new Function('require','module','exports',result.outputFiles[0].text)(require,module,module.exports);
  const markup=renderToStaticMarkup(React.createElement(module.exports.default));
  assert.match(markup,/Unavailable/);assert.match(markup,/unverified/);
  assert.doesNotMatch(markup,/\$0\.00|Clean Fiscal Slate|LINKED BANK DIRECT DEPOSIT|Live Vault|IRS Form 8949|Active Holding/);
});
