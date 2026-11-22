import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import 'fixture-media-store';
import { AuthenticatedDriveMedia, AuthenticatedDriveDownload, requestDriveMediaUrl } from '../../frontend/src/components/AuthenticatedDriveMedia.jsx';
import AdminSharedDriveTab from '../../frontend/src/components/AdminSharedDriveTab.jsx';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const host = document.getElementById('component'), results = [], requests = [], textReads = [];
const backend = 'http://fixture.invalid';
let root, navigations = 0, unexpectedRequests = 0;
window.__fixtureNavigate = () => { navigations++; };
window.alert = () => {};
Element.prototype.scrollIntoView = function () {};
const wait = () => new Promise(resolve => setTimeout(resolve, 0));
const assert = value => { if (!value) throw Error('assertion'); };
async function check(id, fn) { try { await fn(); results.push({ id, passed: true }); } catch { results.push({ id, passed: false }); } }
const setActor = uid => window.__mediaSetState({ currentUser: uid ? { uid } : null });
window.fetch = async (url, options = {}) => {
  const parsed = new URL(url, location.href);
  if (parsed.origin !== backend && parsed.origin !== 'http://fixture-b.invalid') { unexpectedRequests++; throw Error('Unexpected request'); }
  if (parsed.pathname === '/api/drive/media-ticket') return new Promise(resolve => requests.push({ id: requests.length + 1, action: JSON.parse(options.body).action, signal: options.signal, resolve, done: false }));
  if (parsed.pathname === '/api/drive/files') return { ok: true, json: async () => ({ items: [{ path: window.__mediaUseTextSample ? '/synthetic/sample.txt' : '/synthetic/sample.pdf', name: window.__mediaUseTextSample ? 'Synthetic Text' : 'Synthetic PDF', extension: window.__mediaUseTextSample ? '.txt' : '.pdf', category: 'document', icon: '📄', is_dir: false, size: 10, size_formatted: '10 B', modified: '2030-01-01' }], breadcrumbs: [{ name: 'Synthetic root', path: '/' }] }) };
  if (parsed.pathname === '/api/drive/read_document') return new Promise(resolve => textReads.push(resolve));
  if (parsed.pathname === '/api/drive/storage_stats') return { ok: true, json: async () => ({ drive_total_files: 1, drive_total_folders: 0, drive_total_formatted: '10 B', disk_free_formatted: '10 GB', disk_total_formatted: '20 GB', disk_used_pct: 50, categories_breakdown: [] }) };
  unexpectedRequests++; throw Error('Unexpected request');
};
async function finish(batch, urlOverride) {
  await act(async () => { batch.filter(item => !item.done).forEach(item => { item.done = true; item.resolve({ ok: true, json: async () => ({ url: urlOverride || `/api/drive/${item.action}?fixture=${item.id}` }) }); }); await wait(); });
}
async function unmount() { if (root) { await act(async () => { root.unmount(); await wait(); }); root = null; } }
async function mount(kind = 'helper', strict = false, suppliedBackend = backend, textSample = false) {
  await unmount(); window.__mediaUseTextSample = textSample; window.__mediaSetState({ BACKEND_URL: suppliedBackend, currentUser: { uid: 'actor-A' } });
  const start = requests.length;
  await act(async () => {
    root = createRoot(host);
    const content = kind === 'consumer' ? <AdminSharedDriveTab backendUrl={suppliedBackend} /> : <><AuthenticatedDriveMedia backendUrl={suppliedBackend} path="/synthetic/sample.pdf" title="Synthetic preview" /><AuthenticatedDriveDownload backendUrl={suppliedBackend} path="/synthetic/sample.pdf">Synthetic download</AuthenticatedDriveDownload></>;
    root.render(strict ? <React.StrictMode>{content}</React.StrictMode> : content); await wait();
  }); return requests.slice(start);
}
const helperReady = () => Boolean(host.querySelector('iframe[src]') && host.querySelector('a[href]'));
const helperHidden = () => !host.querySelector('iframe[src]') && !host.querySelector('a[href]');
async function openConsumer() {
  const label = [...host.querySelectorAll('*')].find(item => item.childElementCount === 0 && ['Synthetic PDF', 'Synthetic Text'].includes(item.textContent));
  assert(label); await act(async () => { label.dispatchEvent(new MouseEvent('dblclick', { bubbles: true })); await wait(); });
}
async function consumerDownload() {
  const button = host.querySelector('button[title="Download file"]') || host.querySelector('button[title="Download"]') || [...host.querySelectorAll('.drive-preview-modal button')].find(item => /Download/.test(item.textContent));
  assert(button); await act(async () => { button.click(); await wait(); });
}
(async () => {
  for (const strict of [false, true]) {
    const prefix = strict ? 'strict_' : '';
    await check(prefix + 'normal_preview_and_download', async () => { const batch = await mount('helper', strict); await finish(batch); assert(helperReady()); });
    await check(prefix + 'actor_switch_hides_loaded_tickets', async () => { await act(async () => { setActor('actor-B'); await wait(); }); assert(helperHidden()); });
    await check(prefix + 'actor_switch_retires_late_tickets', async () => { const batch = await mount('helper', strict); await act(async () => { setActor('actor-B'); await wait(); }); await finish(batch); assert(helperHidden() && batch.every(item => item.signal?.aborted)); });
    await check(prefix + 'batched_logout_same_uid_hides_loaded_tickets', async () => { const batch = await mount('helper', strict); await finish(batch); await act(async () => { setActor(null); setActor('actor-A'); await wait(); }); assert(helperHidden()); });
    await check(prefix + 'batched_logout_same_uid_retires_late_tickets', async () => { const batch = await mount('helper', strict); await act(async () => { setActor(null); setActor('actor-A'); await wait(); }); await finish(batch); assert(helperHidden() && batch.every(item => item.signal?.aborted)); });
    await check(prefix + 'backend_change_hides_and_retires_tickets', async () => { const batch = await mount('helper', strict); await finish(batch); await act(async () => { window.__mediaSetState({ BACKEND_URL: 'http://fixture-b.invalid' }); await wait(); }); assert(helperHidden()); });
    await check(prefix + 'unmount_aborts_and_ignores_late_results', async () => { const batch = await mount('helper', strict); await unmount(); await finish(batch); assert(host.children.length === 0 && batch.every(item => item.signal?.aborted)); });
    await check(prefix + 'consumer_loaded_preview_cleared_on_actor_switch', async () => { await mount('consumer', strict); await openConsumer(); await finish(requests.filter(item => !item.done)); assert(host.querySelector('.drive-preview-modal')); await act(async () => { setActor('actor-B'); await wait(); }); assert(!host.querySelector('.drive-preview-modal')); });
    await check(prefix + 'consumer_batched_logout_same_uid_clears_preview', async () => { await mount('consumer', strict); await openConsumer(); await finish(requests.filter(item => !item.done)); assert(host.querySelector('.drive-preview-modal')); await act(async () => { setActor(null); setActor('actor-A'); await wait(); }); assert(!host.querySelector('.drive-preview-modal')); });
    await check(prefix + 'consumer_late_preview_retired', async () => { await mount('consumer', strict); await openConsumer(); const batch = requests.filter(item => !item.done); await act(async () => { setActor('actor-B'); await wait(); }); await finish(batch); assert(!host.querySelector('.drive-preview-modal')); });
    await check(prefix + 'consumer_current_download_still_works', async () => { await mount('consumer', strict); const before = navigations; await consumerDownload(); await finish(requests.filter(item => !item.done)); assert(navigations === before + 1); });
    await check(prefix + 'consumer_after_helper_return_download_guard', async () => { await mount('consumer', strict); const before = navigations; await consumerDownload(); window.__mediaSwitchAfterReturn = true; await finish(requests.filter(item => !item.done)); assert(navigations === before); });
    await check(prefix + 'obsolete_text_read_cannot_start_fallback_ticket', async () => {
      await mount('consumer', strict, backend, true); const readsBefore = textReads.length; await openConsumer(); assert(textReads.length === readsBefore + 1);
      await act(async () => { setActor('actor-B'); await wait(); }); const before = requests.length;
      await act(async () => { textReads.at(-1)({ ok: false }); await wait(); }); assert(requests.length === before);
    });
  }
  await unmount();
  await check('standalone_actor_switch_rejects_late_result', async () => {
    setActor('actor-A'); let rejected = false, returned = false;
    const pending = requestDriveMediaUrl(backend, '/synthetic/sample.pdf').then(() => { returned = true; }, () => { rejected = true; });
    setActor('actor-B'); await finish(requests.filter(item => !item.done)); await pending; assert(rejected && !returned);
  });
  await check('standalone_batched_logout_rejects_late_result', async () => {
    setActor('actor-A'); let rejected = false;
    const pending = requestDriveMediaUrl(backend, '/synthetic/sample.pdf').catch(() => { rejected = true; });
    setActor(null); setActor('actor-A'); await finish(requests.filter(item => !item.done)); await pending; assert(rejected);
  });
  for (const [id, value] of [['cross_origin', 'https://other.invalid/api/drive/preview'], ['wrong_path', '/outside/preview']]) {
    await check('validation_' + id + '_rejected', async () => { let rejected = false; const pending = requestDriveMediaUrl(backend, '/synthetic/sample.pdf').catch(() => { rejected = true; }); await finish(requests.filter(item => !item.done), value); await pending; assert(rejected); });
  }
  await check('only_mocked_readonly_ticket_and_listing_requests', async () => assert(unexpectedRequests === 0));
  window.__mediaFixtureReport = { results, realBackendRequests: 0, modelRequests: 0, vmOperations: 0, unexpectedRequests, mockedNavigationCount: navigations };
})().catch(() => { window.__mediaFixtureReport = { results, fixtureFailure: true, realBackendRequests: 0, modelRequests: 0, vmOperations: 0 }; });
