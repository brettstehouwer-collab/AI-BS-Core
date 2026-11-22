// Render the actual source components without mounting the app or calling services.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { createRequire } = require('node:module');
const localRequire = createRequire(path.resolve('frontend/package.json'));
const React = localRequire('react');
const { renderToStaticMarkup } = localRequire('react-dom/server');
const esbuild = localRequire('esbuild');
const source = fs.readFileSync('frontend/src/components/ChatTab.jsx', 'utf8');

function component(text, name) {
  const start = text.indexOf(`function ${name}(`);
  assert.ok(start >= 0, name + ' source missing');
  const end = text.indexOf('\nfunction ', start + 1);
  const declaration = text.slice(start, end < 0 ? undefined : end);
  const { code } = esbuild.transformSync(declaration + `\nmodule.exports = ${name};`, { loader: 'jsx', format: 'cjs' });
  const scope = { React, useState: () => [true, () => {}], module: { exports: {} } };
  vm.runInNewContext(code, scope, { timeout: 1000 });
  return props => renderToStaticMarkup(React.createElement(scope.module.exports, props));
}
const render = component(source, 'ReasoningInspector');
const header = component(source, 'DesktopCognitiveMetaHeader');

test('missing metadata makes no default latency, no-tool or memory claim', () => {
  const html = render({ msg: { role: 'assistant', content: 'fixture' } });
  assert.match(html, /Not recorded/);
  assert.match(html, /No per-message execution trace was recorded/);
  assert.doesNotMatch(html, /120 ms|Fast API Edge|without external tool invocation|ai_bs_context_memory|Zero-Mock/);
});

test('client timing and endpoint describe observation, not action success', () => {
  const html = render({ msg: { client_elapsed_ms: 1234.4, decision_context: {
    operation: 'Web research requested', route: '/api/v1/hybrid-chat/stream', status: 'stream_received'
  } } });
  assert.match(html, /1234 ms \(client measured\)/);
  assert.match(html, /Web research requested/);
  assert.match(html, /\/api\/v1\/hybrid-chat\/stream/);
  assert.match(html, /does not confirm the action completed/);
});

test('backend tool status and duration remain explicitly reported', () => {
  const html = render({ msg: { execution_time_ms: 42, tool_trace: {
    tool_name: 'fixture_tool', status: 'error', arguments: { fixture: true }
  } } });
  assert.match(html, /42 ms \(reported\)/);
  assert.match(html, /Reported Tool: fixture_tool/);
  assert.match(html, /Reported status: error/);
});

test('measured zero stays zero and invalid durations stay unknown', () => {
  assert.match(render({ msg: { client_elapsed_ms: 0 } }), /0 ms \(client measured\)/);
  for (const value of [NaN, Infinity, -1]) {
    assert.match(render({ msg: { client_elapsed_ms: value, execution_time_ms: value } }), /Duration: Not recorded/);
  }
});

test('legacy generated stages and hardware defaults cannot become verified events', () => {
  const html = header({ meta: { model: 'fixture', steps: [
    { id: 1, name: 'Memory Vault', status: 'done', detail: 'Vault Verified (0.12ms)' }
  ], live_telemetry: { core_temp_c: 38, nvml_online: true }, thinking_scope: 'Full Exhaustive Chain-of-Thought' } });
  assert.match(html, /Completion not verified/);
  assert.match(html, /no runtime completion receipt attached/);
  assert.doesNotMatch(html, /Vault Verified|0\.12ms|38°C|Full Exhaustive Chain-of-Thought|1 \/ 1 Complete/);
});

test('rendering historical messages does not add retrospective telemetry', () => {
  const msg = { role: 'assistant', model: 'AST Blast-Radius Engine', content: 'historical fixture' };
  const before = JSON.stringify(msg);
  render({ msg });
  assert.equal(JSON.stringify(msg), before);
});

test('negative control detects the original inspector defaults', () => {
  const before = fs.readFileSync('backups/decision_inspector_audit_20261025_record94/frontend__src__components__ChatTab.jsx.before', 'utf8');
  const html = component(before, 'ReasoningInspector')({ msg: { content: 'fixture' } });
  assert.match(html, /120/);
  assert.match(html, /without external tool invocation/);
  assert.match(html, /ai_bs_context_memory/);
});
