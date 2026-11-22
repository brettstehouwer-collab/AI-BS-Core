const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { createRequire } = require('node:module');
const fromFrontend = createRequire(path.resolve('frontend/package.json'));
const React = fromFrontend('react');
const { renderToStaticMarkup } = fromFrontend('react-dom/server');
const esbuild = fromFrontend('esbuild');

function performancePanel() {
  const text = fs.readFileSync('frontend/src/components/PlaywrightTab.jsx', 'utf8');
  const { code } = esbuild.transformSync(text, { loader: 'jsx', format: 'cjs' });
  let index = 0;
  const hooks = { ...React, useState: initial => [index++ === 0 ? 'play_performance' : initial, () => {}] };
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports,
    require: name => name === 'react' ? hooks : { default: () => null },
    fetch: () => { throw Error('Network forbidden in fixture'); } }, { timeout: 1000 });
  return renderToStaticMarkup(React.createElement(module.exports.default, { backendUrl: 'http://fixture.invalid' }));
}

test('unimplemented performance isolation cannot be enabled or accept uploads', () => {
  const html = performancePanel();
  assert.match(html, /not available|not implemented/i);
  for (const tag of html.matchAll(/<(?:input|button)\b[^>]*>/g)) assert.match(tag[0], /disabled/);
  assert.doesNotMatch(html, /will completely isolate|routes all queries exclusively/);
});

test('document counters reset for empty content and absent document identity', () => {
  const source = fs.readFileSync('frontend/src/components/DocumentsTab.jsx', 'utf8');
  const start = source.indexOf('  // Track word count changes');
  const end = source.indexOf('  const formatTime', start);
  const effects = source.slice(start, end);
  for (const [content, activeDoc] of [['', { path: 'fixture.md' }], ['retained shared screenplay text', null]]) {
    const state = { words: 38001, pages: 153 };
    vm.runInNewContext(effects, { content, activeDoc, useEffect: fn => fn(),
      setSprintWords: v => { state.words = v; }, setSprintPages: v => { state.pages = v; } });
    assert.deepEqual(state, { words: 0, pages: 0 });
  }
});
