// Offline component rendering and extracted-handler regressions. No application bootstrap or providers.
import assert from 'node:assert/strict';
import { test, after } from 'node:test';
import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';

const root = process.env.AI_BS_TEST_ROOT || 'C:/AI-BS';
const frontend = path.join(root, 'frontend');
const require = createRequire(path.join(frontend, 'package.json'));
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { parse } = require('@babel/parser');
const { build } = require('esbuild');
const originalFetch = globalThis.fetch;
globalThis.fetch = async () => { throw new Error('Unexpected transport outside offline fixture'); };
after(() => { globalThis.fetch = originalFetch; });

function walk(node, predicate, result = []) {
  if (!node || typeof node !== 'object') return result;
  if (predicate(node)) result.push(node);
  for (const [key, value] of Object.entries(node)) {
    if (['loc', 'extra', 'comments', 'tokens'].includes(key)) continue;
    if (Array.isArray(value)) value.forEach(child => walk(child, predicate, result));
    else if (value && typeof value === 'object') walk(value, predicate, result);
  }
  return result;
}

async function actualCallback(name, bindings) {
  const source = await readFile(path.join(frontend, 'src/components/BsMediaCreatorTab.jsx'), 'utf8');
  const ast = parse(source, { sourceType: 'module', plugins: ['jsx'] });
  const declaration = walk(ast, node => node.type === 'VariableDeclarator' && node.id?.name === name)[0];
  assert.ok(declaration?.init, 'Expected actual media control callback exists');
  return Function(...Object.keys(bindings), '"use strict"; return (' + source.slice(declaration.init.start, declaration.init.end) + ');')(...Object.values(bindings));
}

async function component(name, mode) {
  const result = await build({
    absWorkingDir: frontend, entryPoints: ['src/components/' + name + '.jsx'], bundle: true,
    write: false, format: 'cjs', platform: 'node', external: ['react'], logLevel: 'silent',
    define: { 'import.meta.env.VITE_BACKEND_URL': '"https://offline.invalid"', 'import.meta.env.DEV': 'false' },
    plugins: [{ name: 'offline-only-boundaries', setup(builder) {
      builder.onResolve({ filter: /useAppStore(?:\.js)?$/ }, () => ({ path: 'store', namespace: 'fixture' }));
      builder.onResolve({ filter: /FinancialAccountBoundary\.jsx$/ }, () => ({ path: 'boundary', namespace: 'fixture' }));
      builder.onResolve({ filter: /^(firebase\/auth)$|(^|\/)firebase\.js$/ }, () => ({ path: 'auth', namespace: 'fixture' }));
      builder.onLoad({ filter: /.*/, namespace: 'fixture' }, args => ({ contents:
        args.path === 'store' ? 'export const useAppStore=()=>{throw Error("No store initialization in fixture")};' :
        args.path === 'boundary' ? 'export default function Boundary({children}) { return children(async()=>{throw Error("No requests during SSR")}); }' :
        'export const auth={currentUser:null};export const onAuthStateChanged=()=>{throw Error("No auth effects during SSR")};'
      }));
      builder.onResolve({ filter: /^\/src\// }, args => ({ path: path.join(frontend, args.path.slice(1)) }));
    } }],
  });
  const reactFixture = mode ? { ...React, useState(initial) { return React.useState(initial === 'chat' ? mode : initial); } } : React;
  const module = { exports: {} };
  Function('require', 'module', 'exports', result.outputFiles[0].text)(name => name === 'react' ? reactFixture : require(name), module, module.exports);
  return module.exports.default;
}

async function render(name, mode, props = {}) {
  return renderToStaticMarkup(React.createElement(await component(name, mode), { backendUrl: 'https://offline.invalid', ...props }));
}

function button(markup, label) {
  const match = [...markup.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)].find(value => value[2].includes(label));
  assert.ok(match, `Actual ${label} control must exist`);
  return match;
}

test('Money Track actual rendering never fabricates balances, fills or active workloads', async () => {
  const markup = await render('MoneyTrackTab');
  assert.ok(!/\$\s*[0-9]/.test(markup));
  assert.ok(!/>\s*Filled\s*</.test(markup));
  assert.ok(!/Mining \(Active\)|Container - Active Compute Job/.test(markup));
  assert.ok(/Unavailable/.test(markup));
  assert.ok(/owned records|verified records|reconcil/i.test(markup));
});

test('Money Track distinguishes unavailable records and held actions from verified zero', async () => {
  const markup = await render('MoneyTrackTab', undefined, { totalBalance: 0, activeTrades: 0 });
  assert.ok(!/\$\s*0|>\s*0\s*</.test(markup));
  assert.ok(/trading.*disabled|trading.*held/i.test(markup));
  assert.ok(/daemon.*disabled|daemon.*held/i.test(markup));
});

test('Money Track has no unauthenticated polling, rolling fixture timestamps or daemon dispatch', async () => {
  const source = await readFile(path.join(frontend, 'src/components/MoneyTrackTab.jsx'), 'utf8');
  const ast = parse(source, { sourceType: 'module', plugins: ['jsx'] });
  assert.equal(walk(ast, node => node.type === 'CallExpression' && ['fetch', 'setInterval'].includes(node.callee?.name)).length, 0);
  assert.ok(!/Date\.now\(|formatTxTime|ORD-[1-5]|chia-start/.test(source));
});

test('Sound Lab actual rendering has no seeded ready outputs, fabricated timing or quality evidence', async () => {
  const markup = await render('BsMediaCreatorTab', 'audio');
  assert.ok(!/>\s*READY\s*</.test(markup));
  assert.ok(!/sess_demucs_0[12]|the_bad_side_theme|48kHz|24-bit PCM|-14\.2 LUFS|00:15\.00/.test(markup));
  assert.ok(/no verified|no confirmed|no completed/i.test(markup));
  assert.ok(/unavailable/i.test(markup));
});

test('Actual separation and preview controls stay disabled while artifact verification is unavailable', async () => {
  const markup = await render('BsMediaCreatorTab', 'audio');
  assert.match(button(markup, 'Isolate Stems')[1], /disabled/);
  assert.match(button(markup, 'Play Master')[1], /disabled/);
});

test('Blocked separation callback cannot send work, fabricate output, erase prior output or alter the draft', async () => {
  const sessions = [{ id: 'offline-existing-complete', status: 'READY', stems: ['offline-existing.wav'] }];
  let output = sessions;
  let draft = 'offline-input.wav';
  let requests = 0;
  let status = '';
  const busy = [];
  const handler = await actualCallback('handleSeparateStems', {
    audioInputPath: draft, activeBackend: 'https://offline.invalid', demucsModel: 'offline-model', demucsSplitMode: '4stems',
    setAudioStatus: value => { status = value; }, setAudioInputPath: value => { draft = value; },
    setIsProcessingAudio: value => busy.push(value), setStemSessions: value => { output = typeof value === 'function' ? value(output) : value; },
    fetch: async () => { requests++; throw new Error('No route dispatch is authorized'); }, console: { warn() {}, error() {} },
  });
  await handler();
  assert.equal(requests, 0, 'Held control must not invoke even a supplied transport');
  assert.equal(output, sessions);
  assert.equal(draft, 'offline-input.wav');
  assert.ok(!busy.includes(true), 'Blocked work must not be represented as running');
  assert.match(status, /unavailable|held|verification/i);
});

test('Media vault actual rendering does not fabricate zero, online state or a successful empty search', async () => {
  const markup = await render('BsMediaCreatorTab', 'vault');
  assert.ok(!/\b(?:0|44) (?:Vectors|Items|Media Vectors)/.test(markup));
  assert.ok(/Unavailable/.test(markup));
  assert.ok(/own|verif/i.test(markup));
  assert.match(button(markup, 'Vector Search')[1], /disabled/);
});

test('Blocked vault stats callback never reads the unowned endpoint or turns unavailable into online', async () => {
  let state = { status: 'unavailable', count: null };
  let requests = 0;
  const handler = await actualCallback('fetchVaultStats', {
    activeBackend: 'https://offline.invalid', fetch: async () => { requests++; throw new Error('No unowned vault reads'); },
    setVaultStats: value => { state = typeof value === 'function' ? value(state) : value; },
  });
  await handler();
  assert.equal(requests, 0);
  assert.equal(state.status, 'unavailable');
  assert.equal(state.count, null);
  assert.match(state.error, /own|verif|unavailable/i);
});

test('Blocked vault search preserves the editable query and previously retrieved results', async () => {
  const results = [{ id: 'offline-existing-owned-result' }];
  let published = results;
  let query = 'offline draft search';
  let requests = 0;
  let status = '';
  const handler = await actualCallback('handleVaultSearch', {
    activeBackend: 'https://offline.invalid', vaultQuery: query, setVaultQuery: value => { query = value; },
    setVaultStats: () => {}, setVaultStatus: value => { status = value; }, setIsSearchingVault: () => {},
    setVaultResults: value => { published = value; }, fetch: async () => { requests++; throw new Error('No unowned vault search'); },
    console: { error() {} },
  });
  await handler();
  assert.equal(requests, 0);
  assert.equal(query, 'offline draft search');
  assert.equal(published, results);
  assert.match(status, /own|verif|unavailable|held/i);
});

test('Unimplemented DAW export does not claim that an export started', async () => {
  const source = await readFile(path.join(frontend, 'src/components/BsMediaCreatorTab.jsx'), 'utf8');
  assert.ok(!/alert\(`Exporting/.test(source));
});

test('All eight recovery-approved component paths have exact four-mirror parity', async () => {
  for (const name of ['MoneyTrackTab.jsx', 'BsMediaCreatorTab.jsx']) {
    const hashes = await Promise.all(['src/components', 'components', 'src/components/components', 'components/components'].map(async dir => createHash('sha256').update(await readFile(path.join(frontend, dir, name))).digest('hex')));
    assert.ok(hashes.every(value => value === hashes[0]), 'All four mirrors must match byte-for-byte');
  }
});
