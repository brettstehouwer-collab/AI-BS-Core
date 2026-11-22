import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import History from 'C:/AI-BS/frontend/src/components/CodingTaskHistory.jsx';
import Card from 'C:/AI-BS/frontend/src/components/CodingTaskReviewCard.jsx';

// Trusted UI infrastructure: all HTTP results and account data are synthetic.
window.IS_REACT_ACT_ENVIRONMENT = true;
const nativeFetch = window.fetch.bind(window), calls = [], results = [];
const taskA = 'a'.repeat(32), taskB = 'b'.repeat(32);
const backendA = 'http://fixture-a.invalid', backendB = 'http://fixture-b.invalid';
let root;
window.fetch = (url, options = {}) => new Promise((resolve, reject) => calls.push({ url: String(url), options, resolve, reject }));
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
const text = () => document.getElementById('component').textContent;
const buttons = label => [...document.querySelectorAll('#component button')].filter(node => node.textContent === label);
const applyButton = () => [...document.querySelectorAll('#component button')].find(node => /^(Apply Verified Change|Applying…)$/.test(node.textContent));
function assert(value, message) { if (!value) throw Error(message); }
function state(actor = 'actor-A', backend = backendA) { window.__fixtureSetState({ BACKEND_URL: backend, currentUser: actor === null ? null : { uid: actor } }); }
async function scope(actor = 'actor-A', backend = backendA) { await act(async () => { state(actor, backend); }); }
function row(id = taskA) { return { id, kind: 'task', state: 'CHECKING' }; }
function review(id = taskA, marker = 'private-A', extra = {}) { return { task_id: id, can_apply: true, review_token: 'synthetic-review-token', state: 'VERIFIED', execution_mode: 'trusted_host', changed_files: ['example.py'], review_diff: marker, checks: [{ argv: ['python', '-m', 'unittest', 'test_example'], returncode: 0 }], ...extra }; }
async function render(kind = 'card', id = taskA) { await act(async () => { root.render(kind === 'history' ? <History /> : <Card taskId={id} />); }); }
async function click(label, index = 0) { const node = buttons(label)[index]; assert(node && !node.disabled, 'Expected enabled ' + label); await act(async () => { node.click(); }); }
async function clickApply() { assert(applyButton() && !applyButton().disabled, 'Expected enabled apply'); await act(async () => { applyButton().click(); }); }
async function reply(call, payload, status = 200) { assert(call, 'Expected deferred request'); await act(async () => { call.resolve(new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })); await tick(); }); }
function retainedClick(node) { assert(node, 'Expected action node'); const key = Object.keys(node).find(name => name.startsWith('__reactProps$')); const handler = node[key]?.onClick; assert(typeof handler === 'function', 'Expected actual React DOM action handler'); return handler; }
async function loadedCard() { await render(); await reply(calls[0], review()); }
async function openedHistory() { await render('history'); await click('Saved coding tasks'); await reply(calls[0], { items: [row()] }); }
async function run(name, test) {
  if (root) await act(async () => root.unmount());
  document.getElementById('component').replaceChildren(); calls.length = 0;
  state('actor-A', backendA); root = createRoot(document.getElementById('component'));
  try { await test(); results.push({ name, passed: true }); }
  catch (error) { results.push({ name, passed: false, error: error.message }); }
}

await run('Unchanged actor explicitly applies exactly once and keeps write uncertainty separate', async () => {
  await loadedCard(); await clickApply(); assert(calls.length === 2 && calls[1].options.method === 'POST', 'Expected one explicit apply');
  assert(!calls[1].options.signal, 'Do not imply an apply POST is undone by aborting a read');
  await reply(calls[1], { task_id: taskA, application: { state: 'APPLIED', backup: 'synthetic-backup' } });
  assert(text().includes('APPLIED') && applyButton().disabled && calls.length === 2, 'Normal apply did not complete once');
});
await run('Actor A to B immediately removes old diff and enabled token', async () => {
  await loadedCard(); await scope('actor-B');
  assert(!text().includes('private-A') && (!applyButton() || applyButton().disabled), 'Old actor diff/token remained');
  assert(calls.length === 2, 'New actor did not request a fresh review');
  await reply(calls[1], review(taskA, 'private-B')); assert(text().includes('private-B'), 'New actor review missing');
});
await run('Actor-switch aborts old review GET and ignores its late response', async () => {
  await render(); const old = calls[0]; await scope('actor-B'); const fresh = calls.at(-1);
  assert(fresh !== old, 'New actor reused the old request'); assert(old.options.signal?.aborted, 'Old read was not aborted');
  await reply(fresh, review(taskA, 'private-B')); await reply(old, review(taskA, 'late-A'));
  assert(text().includes('private-B') && !text().includes('late-A'), 'Late actor response replaced current review');
});
await run('Actor-switch ignores a late old review error', async () => {
  await render(); const old = calls[0]; await scope('actor-B'); await reply(calls.at(-1), review(taskA, 'private-B'));
  await act(async () => { old.reject(Error('old-private-error')); await tick(); });
  assert(text().includes('private-B') && !text().includes('old-private-error'), 'Old actor error leaked');
});
await run('Logout then same UID cannot revive an old review token', async () => {
  await loadedCard(); await scope(null); assert(!text().includes('private-A'), 'Logout retained private review');
  await scope('actor-A'); assert(!text().includes('private-A') && (!applyButton() || applyButton().disabled), 'Returning UID revived token');
  await reply(calls.at(-1), review(taskA, 'fresh-login-A')); assert(text().includes('fresh-login-A'), 'Fresh login review missing');
});
await run('Batched logout then same UID retires visible review before any new reply', async () => {
  await loadedCard(); await act(async () => { state(null); state('actor-A'); });
  assert(!text().includes('private-A') && (!applyButton() || applyButton().disabled), 'Batched logout revived old diff/token');
  assert(calls.length === 2, 'Batched login did not obtain fresh review');
});
await run('Batched logout aborts pending old GET even when final UID is unchanged', async () => {
  await render(); const old = calls[0]; await act(async () => { state(null); state('actor-A'); });
  assert(old.options.signal?.aborted && calls.length === 2, 'Batched logout retained old request');
  await reply(calls[1], review(taskA, 'fresh-login-A')); await reply(old, review(taskA, 'late-login-A'));
  assert(text().includes('fresh-login-A') && !text().includes('late-login-A'), 'Old login response returned');
});
await run('Retained apply handler cannot dispatch during actor transition before render', async () => {
  await loadedCard(); const old = retainedClick(applyButton()), before = calls.length;
  await act(async () => { state('actor-B'); void old(); await tick(); });
  assert(!calls.slice(before).some(call => call.options.method === 'POST'), 'Retired actor handler dispatched apply');
});
await run('Retained apply handler stays retired after batched logout to same UID', async () => {
  await loadedCard(); const old = retainedClick(applyButton()), before = calls.length;
  await act(async () => { state(null); state('actor-A'); void old(); await tick(); });
  assert(!calls.slice(before).some(call => call.options.method === 'POST'), 'Old login handler dispatched apply');
});
await run('Already-dispatched apply success cannot alter actor B or replay a write', async () => {
  await loadedCard(); await clickApply(); const old = calls[1]; await scope('actor-B'); const fresh = calls.at(-1);
  assert(fresh !== old && fresh.options.method !== 'POST', 'New actor review missing'); await reply(fresh, review(taskA, 'private-B'));
  const before = calls.length; await reply(old, { task_id: taskA, application: { state: 'APPLIED', backup: 'private-A-backup' } });
  assert(text().includes('private-B') && !text().includes('private-A-backup') && !applyButton().disabled && calls.length === before, 'Old apply result leaked or replayed');
});
await run('Already-dispatched apply failure cannot alter actor B', async () => {
  await loadedCard(); await clickApply(); const old = calls[1]; await scope('actor-B'); await reply(calls.at(-1), review(taskA, 'private-B'));
  await act(async () => { old.reject(Error('old-apply-failure')); await tick(); }); assert(!text().includes('old-apply-failure'), 'Old apply failure leaked');
});
await run('Same-UID profile refresh keeps current evidence without extra request', async () => {
  await loadedCard(); await act(async () => { window.__fixtureSetState({ currentUser: { uid: 'actor-A', displayName: 'Updated synthetic name' } }); });
  assert(text().includes('private-A') && calls.length === 1 && !applyButton().disabled, 'Ordinary profile refresh unnecessarily reset review');
});
await run('Backend change still retires review and old callback', async () => {
  await loadedCard(); const old = retainedClick(applyButton()), before = calls.length;
  await act(async () => { state('actor-A', backendB); void old(); await tick(); });
  assert(!text().includes('private-A') && !calls.slice(before).some(call => call.options.method === 'POST'), 'Backend transition retained old action');
  assert(calls.at(-1).url.startsWith(backendB), 'Wrong backend review');
});
await run('Task change keeps identity validation and old GET retirement', async () => {
  await render(); const old = calls[0]; await render('card', taskB); assert(old.options.signal?.aborted, 'Task switch read not aborted');
  await reply(calls[1], review(taskA, 'wrong-task')); assert(text().includes('did not match') && (!applyButton() || applyButton().disabled), 'Wrong task accepted');
});

await run('Actor change removes saved IDs, selected review and actions', async () => {
  await openedHistory(); await click('Review'); await reply(calls[1], review()); await scope('actor-B');
  assert(!text().includes('aaaaaaaa') && !text().includes('private-A') && buttons('Review').length === 0 && buttons('Recover Task').length === 0, 'Old actor history/actions survived');
});
await run('Old history GET is aborted and cannot overwrite actor B', async () => {
  await render('history'); await click('Saved coding tasks'); const old = calls[0]; await scope('actor-B'); await click('Saved coding tasks'); const fresh = calls.at(-1);
  assert(fresh !== old && old.options.signal?.aborted, 'Old history read retained');
  await reply(fresh, { items: [row(taskB)] }); await reply(old, { items: [row(taskA)] }); assert(text().includes('bbbbbbbb') && !text().includes('aaaaaaaa'), 'Old history overwrote current actor');
});
await run('Batched logout then same UID removes old saved IDs', async () => {
  await openedHistory(); await act(async () => { state(null); state('actor-A'); });
  assert(!text().includes('aaaaaaaa') && buttons('Recover Task').length === 0, 'Batched logout revived saved history');
});
await run('Retained recover and cancel handlers cannot dispatch during actor change', async () => {
  await openedHistory(); const recover = retainedClick(buttons('Recover Task')[0]), cancel = retainedClick(buttons('Cancel task')[0]), before = calls.length;
  await act(async () => { state('actor-B'); void recover(); void cancel(); await tick(); });
  assert(!calls.slice(before).some(call => call.options.method === 'POST'), 'Old history handlers dispatched a mutation');
});
await run('Retained recover remains retired after batched logout to same UID', async () => {
  await openedHistory(); const recover = retainedClick(buttons('Recover Task')[0]), before = calls.length;
  await act(async () => { state(null); state('actor-A'); void recover(); await tick(); });
  assert(!calls.slice(before).some(call => call.options.method === 'POST'), 'Old login recovery handler revived');
});
await run('Late old cancellation cannot start follow-up reads under actor B', async () => {
  await openedHistory(); await click('Cancel task'); const old = calls[1]; await scope('actor-B'); const before = calls.length;
  await reply(old, { cancel_requested: true }); assert(calls.length === before && !text().includes('Cancellation requested'), 'Old cancel followed into new actor');
});
await run('Late old recovery cannot start reads after logout and return to same UID', async () => {
  await openedHistory(); await click('Recover Task'); const old = calls[1]; await act(async () => { state(null); state('actor-A'); }); const before = calls.length;
  await reply(old, { recovery: { note: 'private-old-recovery' } }); assert(calls.length === before && !text().includes('private-old-recovery'), 'Old recovery followed into new login');
});
await run('Unchanged actor recovery refreshes selected review exactly once', async () => {
  await openedHistory(); await click('Review'); await reply(calls[1], review()); await click('Recover Task');
  await reply(calls[2], { recovery: { note: 'Synthetic recovery inspected' } }); await reply(calls[3], { items: [row()] });
  assert(calls.length === 5 && calls[4].url.endsWith('/review'), 'Selected review not refreshed once'); await reply(calls[4], review(taskA, 'fresh-recovery'));
  assert(text().includes('fresh-recovery') && !text().includes('private-A'), 'Selected review stayed stale');
});
await run('History backend transition still hides IDs and retires old handlers', async () => {
  await openedHistory(); const old = retainedClick(buttons('Cancel task')[0]), before = calls.length;
  await act(async () => { state('actor-A', backendB); void old(); await tick(); }); assert(!text().includes('aaaaaaaa') && !calls.slice(before).some(call => call.options.method === 'POST'), 'Old backend history action survived');
});
await run('Actor change removes old history errors', async () => {
  await render('history'); await click('Saved coding tasks'); await reply(calls[0], { detail: 'private-old-history-error' }, 503); await scope('actor-B');
  assert(!text().includes('private-old-history-error'), 'Old actor history error remained');
});
if (root) await act(async () => root.unmount());
const report = { scope: 'Actual installed React DOM; controlled subscribable store and deferred synthetic HTTP only', realBackendRequests: 0, modelRequests: 0, vmOperations: 0, results };
document.getElementById('status').textContent = results.filter(row => row.passed).length + '/' + results.length + ' passed';
document.getElementById('results').textContent = results.map(row => (row.passed ? 'PASS ' : 'FAIL ') + row.name + (row.error ? ': ' + row.error : '')).join('\n');
document.getElementById('test-report').textContent = JSON.stringify(report, null, 2);
await nativeFetch(__REPORT_URL__, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(report) });
