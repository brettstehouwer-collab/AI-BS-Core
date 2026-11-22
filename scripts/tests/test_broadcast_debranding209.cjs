const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const parser = require(path.join(root, 'frontend/node_modules/@babel/parser'));
const canonical = 'frontend/src/components';
const standalone = 'BroadcastStudioApp/src';
function read(relative) { return fs.readFileSync(path.join(root, relative), 'utf8'); }
function tree(relative) { return parser.parse(read(relative), { sourceType: 'module', plugins: ['jsx'] }); }
function nodes(value, result = []) {
  if (!value || typeof value !== 'object') return result;
  if (value.type) result.push(value);
  for (const [key, child] of Object.entries(value)) {
    if (['loc', 'comments', 'tokens'].includes(key)) continue;
    if (Array.isArray(child)) child.forEach(item => nodes(item, result));
    else nodes(child, result);
  }
  return result;
}

test('standalone broadcast defaults contain no embedded stream-key credentials', () => {
  const all = nodes(tree(standalone + '/components/BroadcastStudio.jsx'));
  const keyLike = /^(?:live_[A-Za-z0-9_-]{12,}|FB-[A-Za-z0-9_-]{12,})$/;
  assert.equal(all.filter(n => n.type === 'StringLiteral' && keyLike.test(n.value)).length, 0,
    'Embedded stream-key literals must be absent; credential values are never included in diagnostics.');
  const destinations = all.filter(n => n.type === 'ObjectExpression' &&
    n.properties.some(p => p.key?.name === 'url' && p.value?.type === 'StringLiteral' &&
      /^rtmps?:\/\/[^/]*(?:twitch\.tv|facebook\.com)(?::\d+)?\//i.test(p.value.value)));
  assert.equal(destinations.length, 2);
  assert.ok(destinations.every(n => n.properties.find(p => p.key?.name === 'key')?.value?.value === ''),
    'Twitch and Facebook credential defaults must be empty; saved user settings remain separate.');
});

test('Omni workspace component imports resolve to actual canonical source files', () => {
  const relative = canonical + '/OmniStudioTab.jsx';
  for (const node of tree(relative).program.body.filter(n => n.type === 'ImportDeclaration')) {
    if (node.source.value.startsWith('.')) {
      assert.ok(fs.existsSync(path.resolve(path.dirname(path.join(root, relative)), node.source.value)), node.source.value);
    } else if (node.source.value.startsWith('/src/')) {
      assert.ok(fs.existsSync(path.join(root, 'frontend', node.source.value.slice(1))), node.source.value);
    }
  }
});

for (const relative of [canonical + '/OmniStudioTab.jsx', canonical + '/BroadcastStudio.jsx',
  standalone + '/App.jsx', standalone + '/components/BroadcastStudio.jsx']) {
  test(relative + ' current workspace has no OBS branding or 4455 bridge', () => {
    const source = read(relative);
    assert.doesNotMatch(source, /\bOBS\b|obs-websocket|localhost:4455|127\.0\.0\.1:4455/i);
    tree(relative);
  });
}

for (const relative of [canonical + '/BroadcastStudio.jsx', standalone + '/components/BroadcastStudio.jsx']) {
  test(relative + ' replaces external-engine panel references with app-owned web capture settings', () => {
    const all = nodes(tree(relative));
    assert.equal(all.some(n => n.type === 'Identifier' && ['showSettingsModal', 'setShowSettingsModal', 'activeSettingsTab', 'setActiveSettingsTab'].includes(n.name)), false);
    assert.ok(all.some(n => n.type === 'StringLiteral' && n.value === 'settings'));
    assert.ok(all.some(n => n.type === 'StringLiteral' && n.value === 'Stream Settings'));
    assert.match(read(relative), /Web capture & audio settings/);
    assert.match(read(relative), /Local web drafts only/);
  });
}

test('retired compatibility telemetry hook never opens sockets, schedules retries or dispatches scenes', () => {
  const relative = standalone + '/hooks/useOBSTelemetry.js';
  const source = read(relative);
  const fn = nodes(tree(relative)).find(n => n.type === 'FunctionDeclaration' && n.id.name === 'useOBSTelemetry');
  let sockets = 0, timers = 0;
  const context = {
    useState: value => [value, () => {}], useRef: () => ({ current: null }), useEffect: fn => fn(),
    WebSocket: class { constructor() { sockets++; } }, setTimeout() { timers++; }, console: { error() {} }
  };
  const api = vm.runInNewContext('(' + source.slice(fn.start, fn.end) + ')', context)();
  assert.equal(sockets, 0); assert.equal(timers, 0); assert.equal(api.connected, false);
  assert.equal(api.telemetry.fps, null); assert.equal(api.telemetry.streaming, null);
  assert.equal(api.setScene('fixture'), false);
});

test('standalone DAW broadcast preview does not invent on-air status or encoder measurements', () => {
  const source = read(standalone + '/components/daw/MusicDAWStudioTab.jsx');
  assert.doesNotMatch(source, /OBS \/ NVENC ENGINE ACTIVE|ON-AIR BROADCAST PiP|DAW Master Stem Live Stream Synced|60\.0 FPS • 6000 kbps/);
  assert.match(source, /Broadcast preview unavailable/);
});

test('canonical broadcast and Omni components retain exact four-tree mirror parity', () => {
  for (const name of ['BroadcastStudio.jsx', 'OmniStudioTab.jsx']) {
    const source = read(canonical + '/' + name);
    for (const mirror of ['frontend/components', 'frontend/src/components/components', 'frontend/components/components']) {
      assert.equal(read(mirror + '/' + name), source, mirror + '/' + name);
    }
  }
});

test('executive broadcast card does not report retired process telemetry or offer retired scene dispatch', () => {
  const source = read(canonical + '/ExecutiveCockpitTab.jsx');
  assert.doesNotMatch(source, /\bOBS\b|is_obs_running|4455/);
  assert.match(source, /Native Broadcast Studio/);
  assert.match(source, /Stream status unverified here/);
  tree(canonical + '/ExecutiveCockpitTab.jsx');
});

test('lexicon keeps lookup controls without proposed broadcast scene automation', () => {
  const source = read(canonical + '/LexiconTheatricalDashboard.jsx');
  assert.doesNotMatch(source, /\bOBS\b|Coming in Phase 2|scene swaps|Live Stream Simulator/);
  assert.match(source, /handleLookup/);
  assert.match(source, /handleEnrich/);
  tree(canonical + '/LexiconTheatricalDashboard.jsx');
  for (const name of ['ExecutiveCockpitTab.jsx', 'LexiconTheatricalDashboard.jsx']) {
    for (const mirror of ['frontend/components', 'frontend/src/components/components', 'frontend/components/components']) {
      assert.equal(read(mirror + '/' + name), read(canonical + '/' + name));
    }
  }
});
