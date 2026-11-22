// Offline source-contract tests: execute only extracted navigation callbacks and
// the cast-controls opening effect. Never import App, stores, providers or media.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const root = path.resolve(__dirname, '../..');
const sourceRoot = process.env.AIBS_NAV_SOURCE_ROOT || root;
const { parse } = require(path.join(root, 'frontend/node_modules/@babel/parser'));

function source(relative) {
  const candidate = path.join(sourceRoot, relative);
  const text = fs.readFileSync(fs.existsSync(candidate) ? candidate : path.join(root, relative), 'utf8');
  return { text, ast: parse(text, { sourceType: 'module', plugins: ['jsx'] }) };
}
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
function extract(file, node) { assert.ok(node, 'Expected source node exists'); return file.text.slice(node.start, node.end); }
function evaluate(file, node, bindings = {}) {
  return Function(...Object.keys(bindings), `"use strict"; return (${extract(file, node)});`)(...Object.values(bindings));
}
function variable(file, name) { return walk(file.ast, node => node.type === 'VariableDeclarator' && node.id.name === name)[0]; }
function prop(file, component, name) {
  return walk(file.ast, node => node.type === 'JSXOpeningElement' && node.name.name === component)
    .map(node => node.attributes.find(attr => attr.name?.name === name)?.value?.expression);
}
function callback(file, token) {
  return walk(file.ast, node => node.type === 'JSXAttribute' && node.name.name === 'onClick')
    .map(node => node.value.expression).find(node => extract(file, node).includes(token));
}
const app = source('frontend/App.jsx');
const dock = source('frontend/components/TopNavbar.jsx');
const sidebar = source('frontend/components/Sidebar.jsx');
const subTabs = source('frontend/components/SubTabBar.jsx');
const mobile = source('frontend/components/MobileNavDrawer.jsx');
const ide = source('frontend/components/SplitPaneIDEWorkspace.jsx');
const chat = source('frontend/components/ChatTab.jsx');
const aliases = evaluate(app, variable(app, 'TAB_ALIASES').init);
const tabs = variable(app, 'tabs').init.elements.map(node => ({
  key: node.properties.find(p => p.key.name === 'key').value.value,
  Component: node.properties.find(p => p.key.name === 'Component').value.name,
}));
function resolve(activeTab) {
  const effectiveTab = evaluate(app, variable(app, 'effectiveTab').init, { TAB_ALIASES: aliases, activeTab });
  return evaluate(app, variable(app, 'activeTabConfig').init, { tabs, effectiveTab });
}
function navigationHarness(initial = 'dashboard') {
  let activeTab = initial;
  let request = 0;
  const bindings = {
    setActiveTab: tab => { activeTab = tab; },
    setWirelessCastOpenRequest: update => { request = typeof update === 'function' ? update(request) : update; },
    useCallback: fn => fn,
    setIsMobileMenuOpen() {}, setIsMobileDrawerOpen() {},
  };
  const navigation = variable(app, 'navigateWorkspaceTab');
  if (navigation) bindings.navigateWorkspaceTab = evaluate(app, navigation.init, bindings);
  return {
    bindings,
    get activeTab() { return activeTab; },
    get request() { return request; },
    select(key) {
      evaluate(app, prop(app, 'TopNavbar', 'onTabChange')[0], bindings)(key);
    },
    requestForLayout(index) {
      const values = prop(app, 'ActiveComponent', 'wirelessCastOpenRequest');
      assert.equal(values.length, 2, 'Both workspace layouts must pass the request');
      assert.ok(values[index], 'Active component receives pending cast-controls request');
      return evaluate(app, values[index], { activeTab, wirelessCastOpenRequest: request });
    },
  };
}
function passThroughIde(request) {
  const declaration = walk(ide.ast, node => node.type === 'FunctionDeclaration' && node.id.name === 'SplitPaneIDEWorkspace')[0];
  const params = declaration.params.map(node => extract(ide, node)).join(', ');
  const bindings = Function(`return function(${params}) { return { wirelessCastOpenRequest: typeof wirelessCastOpenRequest === 'undefined' ? undefined : wirelessCastOpenRequest }; };`)()({ wirelessCastOpenRequest: request });
  const values = prop(ide, 'ChatTab', 'wirelessCastOpenRequest');
  assert.equal(values.length, 1);
  assert.ok(values[0], 'IDE forwards pending request to the lazily mounted chat controls');
  return evaluate(ide, values[0], bindings);
}
function openingEffect(request, initial = false) {
  let open = initial;
  const declaration = walk(chat.ast, node => node.type === 'FunctionDeclaration' && node.id.name === 'ChatTab')[0];
  const params = declaration.params.map(node => extract(chat, node)).join(', ');
  const received = Function(`return function(${params}) { return typeof wirelessCastOpenRequest === 'undefined' ? undefined : wirelessCastOpenRequest; };`)()({ wirelessCastOpenRequest: request });
  assert.equal(received, request, 'Chat binds the forwarded request prop');
  const effects = walk(chat.ast, node => node.type === 'CallExpression' && node.callee.name === 'useEffect');
  const effect = effects.find(node => node.arguments[1]?.elements?.some(dep => dep.name === 'wirelessCastOpenRequest'));
  assert.ok(effect, 'Chat handles each cast-controls request after mounting');
  const forbidden = () => assert.fail('Opening controls must not start a backend action, capture or cast');
  const bindings = {
    wirelessCastOpenRequest: received,
    setShowWirelessCastHub: update => { open = typeof update === 'function' ? update(open) : update; },
    fetch: forbidden, handleWirelessCastAction: forbidden, handleStartLiveScreenCast: forbidden,
    window: { dispatchEvent: forbidden }, navigator: { mediaDevices: { getDisplayMedia: forbidden } },
  };
  evaluate(chat, effect.arguments[0], bindings)();
  return open;
}

test('Steam quick-dock click opens the registered Central Gaming Hub', () => {
  const h = navigationHarness();
  evaluate(dock, callback(dock, 'onTabChange(pt.key)'), { pt: { key: 'steam_gaming' }, onTabChange: key => h.select(key) })();
  assert.equal(resolve(h.activeTab).key, 'central_gaming_hub');
  assert.equal(resolve(h.activeTab).Component, 'CentralGamingHubTab');
});
test('Gaming Lab sub-tab click opens the same hub rather than fallback chat', () => {
  const h = navigationHarness();
  evaluate(subTabs, callback(subTabs, 'onTabChange(sub.key)'), { sub: { key: 'gaming_lab' }, isEditingLayout: false, onTabChange: key => h.select(key) })();
  assert.equal(resolve(h.activeTab).key, 'central_gaming_hub');
});
test('Retained customized Sidebar hub defaults can still use the Steam legacy key', () => {
  const h = navigationHarness();
  evaluate(sidebar, callback(sidebar, 'hub.defaultTab'), { hub: { defaultTab: 'steam_gaming' }, isHubActive: false, activeTab: 'dashboard', isEditingLayout: false, onTabChange: key => h.select(key) })();
  assert.equal(resolve(h.activeTab).key, 'central_gaming_hub');
});
test('Mobile drawer selection forwards the same route and closes the drawer', () => {
  const h = navigationHarness();
  let closed = false;
  evaluate(mobile, variable(mobile, 'handleSelectTool').init, { onTabChange: key => h.select(key), onClose: () => { closed = true; } })('steam_gaming');
  assert.equal(resolve(h.activeTab).key, 'central_gaming_hub');
  assert.equal(closed, true);
});
test('Every App navigation entry point delivers fresh requests through the shared handler', () => {
  const h = navigationHarness();
  for (const [component, name] of [['TopNavbar', 'onTabChange'], ['Sidebar', 'onTabChange'], ['SubTabBar', 'onTabChange'], ['MobileNavDrawer', 'onTabChange'], ['MobileBottomNav', 'onTabChange'], ['ActiveComponent', 'onNavigateTab']]) {
    const callbacks = prop(app, component, name);
    assert.ok(callbacks.length > 0, component);
    for (const node of callbacks) {
      const previous = h.request;
      evaluate(app, node, h.bindings)('screen_mirror');
      assert.ok(h.request > previous, component + ' must create a new controls request');
      assert.equal(resolve(h.activeTab).key, 'ide');
    }
  }
});
for (const layout of [0, 1]) test(`Screen-mirror dock opens IDE controls in workspace layout ${layout + 1}`, () => {
  const h = navigationHarness();
  evaluate(dock, callback(dock, 'onTabChange(pt.key)'), { pt: { key: 'screen_mirror' }, onTabChange: key => h.select(key) })();
  assert.equal(resolve(h.activeTab).key, 'ide');
  assert.equal(resolve(h.activeTab).Component, 'IdeView');
  assert.equal(openingEffect(passThroughIde(h.requestForLayout(layout))), true);
});
test('Selecting screen mirror again after closing creates a fresh idempotent open request', () => {
  const h = navigationHarness();
  h.select('screen_mirror');
  const first = passThroughIde(h.requestForLayout(0));
  assert.equal(openingEffect(first), true);
  h.select('screen_mirror');
  const second = passThroughIde(h.requestForLayout(0));
  assert.ok(second > first, 'Repeated selection must wake an already-mounted IDE');
  assert.equal(openingEffect(second, false), true, 'Reopens closed controls');
  assert.equal(openingEffect(second, true), true, 'Opens rather than toggles already-open controls');
});
test('A request made before lazy chat readiness is delivered when it mounts', () => {
  const h = navigationHarness();
  h.select('screen_mirror');
  const pending = h.requestForLayout(0);
  assert.ok(pending > 0);
  assert.equal(openingEffect(passThroughIde(pending)), true);
  assert.equal(openingEffect(passThroughIde(pending)), true, 'A later remount retains the pending selection');
});
test('Initial screen-mirror URL opens controls without requiring a preceding click', async () => {
  const routing = await import(pathToFileURL(path.join(root, 'frontend/components/portalRouting.js')));
  const h = navigationHarness(routing.resolveInitialWorkspaceTab('?tab=screen_mirror', null));
  assert.equal(resolve(h.activeTab).key, 'ide');
  assert.equal(openingEffect(passThroughIde(h.requestForLayout(1))), true);
});
test('Ordinary IDE and gaming navigation do not request casting or close manually opened controls', () => {
  const h = navigationHarness();
  h.select('screen_mirror');
  h.select('ide');
  assert.equal(h.requestForLayout(0), 0);
  assert.equal(openingEffect(passThroughIde(h.requestForLayout(0)), false), false);
  assert.equal(openingEffect(passThroughIde(h.requestForLayout(0)), true), true);
  const request = h.request;
  h.select('gaming_lab');
  assert.equal(h.request, request);
  assert.equal(h.requestForLayout(1), 0);
});
test('Existing canonical routes and aliases retain their destinations', () => {
  for (const [key, expected] of [['chat', 'chat'], ['central_gaming_hub', 'central_gaming_hub'], ['host_terminal', 'terminal'], ['team_chat', 'chat'], ['cloud_drive', 'shared_cloud_drive'], ['ide', 'ide']]) {
    assert.equal(resolve(key).key, expected);
  }
});
test('Existing gaming URL migrations retain their destination', async () => {
  const routing = await import(pathToFileURL(path.join(root, 'frontend/components/portalRouting.js')));
  for (const key of ['steam_gaming', 'gaming_lab']) {
    assert.equal(routing.resolveInitialWorkspaceTab('?tab=' + key, null), 'central_gaming_hub');
    assert.equal(routing.resolveInitialWorkspaceTab('', key), 'central_gaming_hub');
  }
});
