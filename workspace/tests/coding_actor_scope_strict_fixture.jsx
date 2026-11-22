import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import History from 'C:/AI-BS/frontend/src/components/CodingTaskHistory.jsx';
import Card from 'C:/AI-BS/frontend/src/components/CodingTaskReviewCard.jsx';

window.IS_REACT_ACT_ENVIRONMENT = true;
const nativeFetch = window.fetch.bind(window), calls = [], results = [];
const task = 'a'.repeat(32), other = 'b'.repeat(32), backend = 'http://fixture-a.invalid';
let root;
window.fetch = (url, options = {}) => new Promise((resolve, reject) => calls.push({ url: String(url), options, resolve, reject, resolved: false }));
const tick = () => new Promise(resolve => setTimeout(resolve, 0));
const text = () => document.getElementById('component').textContent;
const buttons = label => [...document.querySelectorAll('#component button')].filter(node => node.textContent === label);
const apply = () => buttons('Apply Verified Change')[0];
function assert(value, message) { if (!value) throw Error(message); }
function state(uid = 'actor-A') { window.__fixtureSetState({ BACKEND_URL: backend, currentUser: uid === null ? null : { uid } }); }
function review(marker) { return { task_id: task, can_apply: true, review_token: 'synthetic-review-token', state: 'VERIFIED', changed_files: ['example.py'], review_diff: marker, checks: [], execution_mode: 'trusted_host' }; }
function retained(node) { const key = Object.keys(node).find(name => name.startsWith('__reactProps$')); assert(typeof node[key]?.onClick === 'function', 'Missing retained DOM handler'); return node[key].onClick; }
async function click(label) { const node = buttons(label)[0]; assert(node && !node.disabled, 'Expected enabled ' + label); await act(async () => node.click()); }
async function reply(call, data) { assert(call && !call.resolved, 'Expected unanswered request'); call.resolved = true; await act(async () => { call.resolve(new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } })); await tick(); }); }
async function reads(marker = 'strict-private-A', id = task, exclude = new Set()) {
  for (let round = 0; round < 8; round++) {
    const pending = calls.filter(call => !call.resolved && call.options.method !== 'POST' && !exclude.has(call));
    if (!pending.length) return;
    for (const call of pending) await reply(call, call.url.endsWith('/review') ? review(marker) : { items: [{ kind: 'task', id, state: 'CHECKING' }] });
  }
  throw Error('Read effects did not settle within eight rounds');
}
async function mount(kind = 'card') { await act(async () => root.render(<StrictMode>{kind === 'history' ? <History /> : <Card taskId={task} />}</StrictMode>)); }
async function run(name, test) {
  if (root) await act(async () => root.unmount()); document.getElementById('component').replaceChildren(); calls.length = 0; state(); root = createRoot(document.getElementById('component'));
  try { await test(); results.push({ name, passed: true }); } catch (error) { results.push({ name, passed: false, error: error.message }); }
}
await run('StrictMode replay settles reads and never replays an explicit Apply write', async () => {
  await mount(); await reads(); assert(text().includes('strict-private-A') && apply() && !apply().disabled, 'Current strict review did not settle');
  await click('Apply Verified Change'); const writes = calls.filter(call => call.options.method === 'POST'); assert(writes.length === 1 && !writes[0].options.signal, 'Write was replayed or tied to read cancellation');
  await reply(writes[0], { task_id: task, application: { state: 'APPLIED', backup: 'synthetic-strict-backup' } }); assert(text().includes('APPLIED') && calls.filter(call => call.options.method === 'POST').length === 1, 'StrictMode replayed apply');
});
await run('StrictMode actor switch retires visible evidence and retained Apply callback', async () => {
  await mount(); await reads(); const old = retained(apply()); const count = calls.filter(call => call.options.method === 'POST').length;
  await act(async () => { state('actor-B'); void old(); await tick(); }); assert(!text().includes('strict-private-A'), 'Old actor evidence survived replay'); assert(calls.filter(call => call.options.method === 'POST').length === count, 'Old actor callback dispatched');
  await reads('strict-private-B'); assert(text().includes('strict-private-B'), 'New strict actor review missing');
});
await run('StrictMode batched logout to same UID does not revive a token', async () => {
  await mount(); await reads(); const old = retained(apply());
  await act(async () => { state(null); state(); void old(); await tick(); }); assert(!text().includes('strict-private-A') && !calls.some(call => call.options.method === 'POST'), 'Old login was revived');
  await reads('strict-fresh-login'); assert(text().includes('strict-fresh-login'), 'Fresh strict login missing');
});
await run('StrictMode late old GET cannot replace the next actor after read replay', async () => {
  await mount(); const old = new Set(calls); await act(async () => state('actor-B')); await reads('strict-private-B', task, old);
  for (const call of old) await reply(call, review('strict-late-A'));
  assert(text().includes('strict-private-B') && !text().includes('strict-late-A'), 'Late old strict read leaked');
});
await run('StrictMode history and selected review retire together on actor change', async () => {
  await mount('history'); await click('Saved coding tasks'); await reads(); await click('Review'); await reads(); assert(text().includes('strict-private-A'), 'Initial strict history review missing');
  await act(async () => state('actor-B')); assert(!text().includes('aaaaaaaa') && !text().includes('strict-private-A') && !buttons('Recover Task').length, 'Old strict history survived');
  await click('Saved coding tasks'); await reads('strict-private-B', other); assert(text().includes('bbbbbbbb') && !text().includes('aaaaaaaa'), 'Strict history mixed actors');
});
await run('StrictMode old recovery response cannot continue after batched same-UID login', async () => {
  await mount('history'); await click('Saved coding tasks'); await reads(); await click('Recover Task'); const old = calls.find(call => call.options.method === 'POST'); assert(old, 'Recovery not dispatched');
  await act(async () => { state(null); state(); }); const count = calls.length; await reply(old, { recovery: { note: 'strict-old-recovery' } });
  assert(calls.length === count && !text().includes('strict-old-recovery'), 'Old recovery continued after strict replay');
});
if (root) await act(async () => root.unmount());
const report = { scope: 'Actual installed React DOM under StrictMode replay; synthetic store and deferred HTTP only', realBackendRequests: 0, modelRequests: 0, vmOperations: 0, results };
document.getElementById('status').textContent = results.filter(row => row.passed).length + '/' + results.length + ' passed';
document.getElementById('results').textContent = results.map(row => (row.passed ? 'PASS ' : 'FAIL ') + row.name + (row.error ? ': ' + row.error : '')).join('\n');
document.getElementById('test-report').textContent = JSON.stringify(report, null, 2);
await nativeFetch(__REPORT_URL__, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(report) });
