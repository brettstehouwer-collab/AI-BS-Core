import { readChatHttpResponse } from './chatHttpResponse.js';

const ID = /^[a-f0-9]{32}$/, HASH = /^[a-f0-9]{64}$/;
const STATES = new Set(['PREPARING', 'PREPARED', 'FAILED', 'INTERRUPTED']);
const PLAN_STATES = new Set(['RUNNING', 'INCOMPLETE', 'PLAN_PROPOSED', 'NEEDS_CLARIFICATION', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'INTERRUPTED']);
const PLAN_TERMINAL = new Set(['PLAN_PROPOSED', 'NEEDS_CLARIFICATION', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'INTERRUPTED']);
const PROPOSAL_TERMINAL = new Set(['PROPOSAL_READY', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'INTERRUPTED']);
const PROPOSAL_STATES = new Set(['RUNNING', 'INCOMPLETE', ...PROPOSAL_TERMINAL]);
const blankProposals = () => ({ proposalReview: null, proposalRecord: null, proposalPendingId: null, proposalBusy: false,
  proposalCancelBusy: false, proposalCancelRequested: false, proposalError: '', proposalIdInput: '', proposalSeen: [],
  proposalItems: [], proposalNextCursor: null, proposalsLoaded: false });
const blankPlanning = () => ({ planRecord: null, planPendingId: null, planBusy: false, planCancelBusy: false,
  planCancelRequested: false, planItems: [], planNextCursor: null, plansLoaded: false, planError: '', planIdInput: '', ...blankProposals() });
const blank = () => ({ objective: '', editable: '', verification: '', dependencies: '', python: '', node: '', npm: '' });
const copy = value => JSON.parse(JSON.stringify(value));
const canonical = value => JSON.stringify(value, (_, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
const same = (a, b) => canonical(a) === canonical(b);
function freeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function lines(value) {
  if (typeof value !== 'string') throw Error('Enter text for each selection.');
  const rows = value.split(/\r\n|\n|\r/).filter(row => row !== '');
  if (rows.some(row => row !== row.trim())) throw Error('Remove leading or trailing spaces from selected paths and checks.');
  return rows;
}
function safePath(name) {
  return name.length <= 240 && !/[\\<>:"|?*\x00-\x1f\x7f]/.test(name) && name.split('/').every(part => part && !['.', '..'].includes(part) && !/[ .]$/.test(part));
}
export function buildPreparationPlan(form, requestId) {
  if (!ID.test(requestId || '') || typeof form?.objective !== 'string' || !form.objective.trim() || form.objective.length > 8000) throw Error('Enter an objective of up to 8,000 characters.');
  const files = [['editable', 'editable'], ['verification', 'verification'], ['dependencies', 'dependency']]
    .flatMap(([field, role]) => lines(form[field]).map(relative_path => ({ relative_path, role })));
  const names = files.map(row => row.relative_path.toLowerCase());
  if (!files.some(row => row.role === 'editable') || files.length > 20 || new Set(names).size !== names.length || files.some(row => !safePath(row.relative_path))) throw Error('Select up to 20 distinct relative paths, including at least one file to change.');
  if (names.some(name => name.split('/').some((_, i, parts) => i > 0 && names.includes(parts.slice(0, i).join('/'))))) throw Error('A selected file conflicts with a selected directory.');
  const checks = [['python', 'python_unittest'], ['node', 'node_test'], ['npm', 'npm_script']]
    .map(([check_id, profile]) => ({ check_id, profile, targets: lines(form[check_id]) })).filter(row => row.targets.length);
  if (!checks.length || checks.some(row => row.targets.length > 61 || row.targets.some(target => target.length > 1024)) || checks.some(row => row.profile === 'npm_script' && row.targets.length !== 1)) throw Error('Select fixed checks; enter one existing npm script at most.');
  return { request_id: requestId, repository_id: 'ai-bs', objective: form.objective, files, checks,
    limits: { check_seconds: 30, total_seconds: 180, output_bytes: 262144 } };
}
const compiled = plan => plan.checks.map(row => ({ check_id: row.check_id, argv: row.profile === 'python_unittest'
  ? ['python', '-m', 'unittest', ...row.targets] : row.profile === 'node_test' ? ['node', '--test', ...row.targets] : ['npm', 'run', ...row.targets] }));
function validOwner(value) { return typeof value === 'string' && value.length <= 512 && !/[\x00-\x1f\x7f]/.test(value) && (value === 'local_admin' || /^firebase:[^:]+:.+$/.test(value)); }
function validFiles(files) {
  return Array.isArray(files) && files.length > 0 && files.length <= 20 && new Set(files.map(row => row?.relative_path?.toLowerCase())).size === files.length &&
    files.every(row => typeof row?.relative_path === 'string' && safePath(row.relative_path) && ['editable', 'verification', 'dependency'].includes(row.role) && Number.isInteger(row.length) && row.length >= 0 && row.length <= 2097152 && HASH.test(row.sha256 || '') && !('content' in row)) && files.reduce((sum, row) => sum + row.length, 0) <= 16777216;
}
function baseURL(raw) {
  const origin = globalThis.location?.origin;
  const value = new URL(raw || origin, origin);
  if (!['http:', 'https:'].includes(value.protocol) || value.username || value.password || value.search || value.hash) throw Error('Select a valid backend without embedded credentials.');
  return value.href.replace(/\/+$/, '');
}
const emptyState = () => ({ phase: 'closed', connected: false, busy: false, owner: '', form: blank(), preview: null, receipt: null,
  items: [], nextCursor: null, historyLoaded: false, pendingId: null, unconfirmedIds: [], error: '', ...blankPlanning() });

export function createPreparationClient({ getContext, fetchImpl = (...args) => globalThis.fetch(...args), uuid = () => crypto.randomUUID().replace(/-/g, '') }) {
  const listeners = new Set(), contexts = new Map(), controllers = new Set();
  let active = null, epoch = 0, state = freeze(emptyState());
  const stamp = () => { const value = getContext(); return JSON.stringify([value.backendUrl, value.actor || '']); };
  const current = ctx => Boolean(ctx && ctx === active && ctx.epoch === epoch && ctx.stamp === stamp());
  function publish(ctx, patch) {
    if (ctx && !current(ctx)) return;
    state = freeze({ ...state, ...copy(patch) }); listeners.forEach(fn => fn());
  }
  function close() {
    epoch++; active = null; controllers.forEach(controller => controller.abort()); controllers.clear();
    state = freeze(emptyState()); listeners.forEach(fn => fn());
  }
  function ensure(ctx) { if (!current(ctx)) throw Error('Preparation scope changed; reconnect before continuing.'); }
  function own(ctx, data) {
    if (data?.owner !== ctx.owner) { const error = Error('Preparation response belongs to another owner.'); error.scopeMismatch = true; throw error; }
  }
  async function request(ctx, path, method = 'GET', body) {
    ensure(ctx); const controller = new AbortController(); controllers.add(controller);
    try {
      const response = await fetchImpl(`${ctx.url}/api/chat/coding-tasks/preparations${path}`, { method, signal: controller.signal,
        ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) });
      ensure(ctx);
      let data; try { data = await readChatHttpResponse(response); } catch (error) { error.httpStatus = response.status; throw error; }
      ensure(ctx); return data;
    } finally { controllers.delete(controller); }
  }
  function pendingFields(ctx) { return { pendingId: ctx.cache?.pending?.payload.request_id || null, unconfirmedIds: [...(ctx.cache?.unconfirmedIds || [])] }; }
  function fail(ctx, error) {
    if (!current(ctx)) return;
    if ([401, 403].includes(error.httpStatus)) { close(); publish(null, { phase: 'error', error: error.message }); }
    else publish(ctx, { error: error.message || String(error), ...(error.scopeMismatch
      ? { connected: false, items: [], preview: null, receipt: null, ...blankPlanning() } : {}) });
  }
  async function operate(action) {
    const ctx = active;
    if (!current(ctx) || !state.connected) throw Error('Connect to the selected preparation backend first.');
    if (state.busy || state.planBusy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy) throw Error('A preparation, planning or proposal operation is already active.');
    publish(ctx, { busy: true, error: '' });
    try { return await action(ctx); } catch (error) { fail(ctx, error); throw error; }
    finally { publish(ctx, { busy: false }); }
  }
  async function loadHistory(ctx, more = false) {
    const cursor = more ? state.nextCursor : null;
    if (more && !cursor) return;
    const data = await request(ctx, `?limit=20${cursor ? '&cursor=' + encodeURIComponent(cursor) : ''}`);
    own(ctx, data);
    if (data.metadata_only !== true || !Array.isArray(data.items) || data.items.length > 20 || data.items.some(row => !ID.test(row?.request_id || '') || !STATES.has(row.state) || typeof row.title !== 'string' || row.title.length > 200 || row.execution_authorized !== false || row.verification_status !== 'not_run' || row.retained_inputs_revalidated !== false) ||
      !(data.next_cursor === null || (ID.test(data.next_cursor || '') && data.items.at(-1)?.request_id === data.next_cursor && (!cursor || data.next_cursor > cursor)))) throw Error('Preparation history response is invalid.');
    const items = more ? [...new Map([...state.items, ...data.items].map(row => [row.request_id, row])).values()] : data.items;
    publish(ctx, { items, nextCursor: data.next_cursor, historyLoaded: true });
  }
  function validateRecord(ctx, data, id) {
    own(ctx, data);
    if (data.kind !== 'project_preparation' || data.request_id !== id || data.repository_id !== 'ai-bs' || !STATES.has(data.state) || data.execution_authorized !== false || data.verification_status !== 'not_run' || data.execution_mode !== 'windows_vm' || data.vm_admission_status !== 'pending_accepted_worker' || data.current_sources_rechecked !== false || data.durable !== (data.state === 'PREPARED') || !validFiles(data.files) || !HASH.test(data.snapshot_sha256 || '') || !HASH.test(data.review_digest || '') || !Array.isArray(data.checks) || !data.checks.length || data.checks.length > 10 || data.checks.some(row => !Array.isArray(row.argv) || row.argv.some(arg => typeof arg !== 'string' || arg.length > 1024))) throw Error('Retained preparation response is invalid.');
  }
  async function inspect(ctx, id, recover) {
    if (!ID.test(id || '')) throw Error('Enter a valid saved preparation ID.');
    const data = await request(ctx, '/' + id + (recover ? '/recover' : ''), recover ? 'POST' : 'GET');
    validateRecord(ctx, data, id);
    if (ctx.cache.pending?.payload.request_id === id && data.state !== 'PREPARING') ctx.cache.pending = null;
    ctx.approved = null;
    selectReceipt(ctx, data); return data;
  }
  const receiptKey = record => canonical([record.request_id, record.snapshot_sha256, record.review_digest]);
  function binding(ctx) {
    ensure(ctx); const receipt = ctx.selectedReceipt;
    if (!receipt || receipt.state !== 'PREPARED' || !receipt.durable || receipt.owner !== ctx.owner) throw Error('Inspect or save a prepared input snapshot before planning.');
    const key = receiptKey(receipt);
    if (!ctx.cache.plans.has(key)) ctx.cache.plans.set(key, { pendingId: null, record: null, cancelRequested: false });
    return { receipt, key, cache: ctx.cache.plans.get(key) };
  }
  function ensurePlan(ctx, selected) {
    ensure(ctx);
    if (!ctx.selectedReceipt || receiptKey(ctx.selectedReceipt) !== selected.key) throw Error('Selected preparation changed. Inspect it before continuing.');
  }
  const planFields = selected => ({ planRecord: selected.cache.record, planPendingId: selected.cache.pendingId,
    planCancelRequested: selected.cache.cancelRequested, ...blankProposals(), ...proposalFields(proposalSelection(selected)) });
  function selectReceipt(ctx, data) {
    ctx.selectedReceipt = copy(data);
    const fields = data.state === 'PREPARED' ? planFields(binding(ctx)) : {};
    publish(ctx, { receipt: data, preview: null, ...pendingFields(ctx), ...blankPlanning(), ...fields });
  }
  function validatePlan(ctx, selected, data, id) {
    own(ctx, data); const r = selected.receipt;
    if (data.kind !== 'project_plan' || data.request_id !== r.request_id || data.plan_id !== id || !PLAN_STATES.has(data.state) ||
      data.snapshot_sha256 !== r.snapshot_sha256 || data.review_digest !== r.review_digest || data.execution_authorized !== false ||
      data.verification_status !== 'not_run' || data.source_status !== 'retained_inputs' || data.current_sources_rechecked !== false ||
      data.model !== 'stehouwer_llm:latest' || !(data.error_code === null || (typeof data.error_code === 'string' && data.error_code.length <= 100))) throw Error('Plan response did not match the saved preparation.');
    if (['PLAN_PROPOSED', 'NEEDS_CLARIFICATION'].includes(data.state)) {
      const p = data.proposal, allowed = r.files.filter(f => f.role === 'editable').map(f => f.relative_path);
      if (!p || !same(Object.keys(p).sort(), ['questions', 'steps', 'summary']) || typeof p.summary !== 'string' || !p.summary.trim() || p.summary.length > 2000 ||
        !Array.isArray(p.steps) || p.steps.length !== allowed.length || new Set(p.steps.map(s => s?.path)).size !== allowed.length ||
        p.steps.some(s => !s || !same(Object.keys(s).sort(), ['change', 'path']) || !allowed.includes(s.path) || typeof s.change !== 'string' || !s.change.trim() || s.change.length > 2000) ||
        !Array.isArray(p.questions) || p.questions.length > 3 || p.questions.some(q => typeof q !== 'string' || !q.trim() || q.length > 500) ||
        (p.questions.length > 0) !== (data.state === 'NEEDS_CLARIFICATION')) throw Error('Public model plan changed the selected scope or outcome.');
    } else if (data.proposal !== null) throw Error('An unfinished or failed plan cannot claim a proposal.');
  }
  function acceptPlan(ctx, selected, data, id) {
    ensurePlan(ctx, selected); validatePlan(ctx, selected, data, id);
    const record = copy(data); delete record.cancel_requested;
    const previous = selected.cache.record;
    if (previous?.plan_id === id && PLAN_TERMINAL.has(previous.state)) {
      if (!PLAN_TERMINAL.has(data.state)) return previous;
      if (!same(previous, record)) throw Error('Terminal planning evidence changed. Inspect the saved record.');
    }
    selected.cache.record = record;
    if (PLAN_TERMINAL.has(record.state) && selected.cache.pendingId === id) selected.cache.pendingId = null;
    if (PLAN_TERMINAL.has(record.state)) selected.cache.cancelRequested = false;
    publish(ctx, planFields(selected)); return record;
  }
  async function planOperate(action) {
    const ctx = active;
    if (!current(ctx) || !state.connected) throw Error('Connect to the selected preparation backend first.');
    if (state.busy || state.planBusy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy) throw Error('Another preparation, planning or proposal operation is active.');
    const selected = binding(ctx); publish(ctx, { planBusy: true, planError: '', error: '' });
    try { return await action(ctx, selected); }
    catch (error) { fail(ctx, error); publish(ctx, { planError: error.message || String(error) }); throw error; }
    finally { publish(ctx, { planBusy: false }); }
  }
  async function inspectPlan(ctx, selected, id, recover) {
    if (!ID.test(id || '')) throw Error('Enter a valid saved plan ID.');
    const data = await request(ctx, '/' + selected.receipt.request_id + '/plans/' + id + (recover ? '/recover' : ''), recover ? 'POST' : 'GET');
    return acceptPlan(ctx, selected, data, id);
  }
  async function loadPlans(ctx, selected, more = false) {
    const cursor = more ? state.planNextCursor : null;
    if (more && !cursor) return;
    const data = await request(ctx, '/' + selected.receipt.request_id + '/plans?limit=20' + (cursor ? '&cursor=' + encodeURIComponent(cursor) : ''));
    ensurePlan(ctx, selected); own(ctx, data); const r = selected.receipt;
    if (data.request_id !== r.request_id || data.snapshot_sha256 !== r.snapshot_sha256 || data.review_digest !== r.review_digest || data.metadata_only !== true ||
      !Array.isArray(data.items) || data.items.length > 20 || data.items.some(item => !ID.test(item?.plan_id || '') || !PLAN_STATES.has(item.state) || item.proposal_revalidated !== false || item.execution_authorized !== false || item.verification_status !== 'not_run') ||
      !(data.next_cursor === null || (ID.test(data.next_cursor || '') && data.items.at(-1)?.plan_id === data.next_cursor && (!cursor || data.next_cursor > cursor)))) throw Error('Saved plan history response is invalid.');
    const items = more ? [...new Map([...state.planItems, ...data.items].map(item => [item.plan_id, item])).values()] : data.items;
    publish(ctx, { planItems: items, planNextCursor: data.next_cursor, plansLoaded: true });
  }
  function proposalSelection(selected) {
    const parent = selected.cache.record;
    if (parent?.state !== 'PLAN_PROPOSED' || parent.proposal.questions.length) return null;
    const key = canonical(parent);
    if (!selected.cache.proposals) selected.cache.proposals = new Map();
    if (!selected.cache.proposals.has(key)) selected.cache.proposals.set(key, { review: null, record: null, pending: null, cancelRequested: false, records: new Map(), items: [], nextCursor: null, loaded: false });
    return { ...selected, parent: copy(parent), proposalKey: key, proposalCache: selected.cache.proposals.get(key) };
  }
  function proposalBinding(ctx) {
    const selected = proposalSelection(binding(ctx));
    if (!selected) throw Error('Inspect a question-free proposed plan before requesting code.');
    return selected;
  }
  function ensureProposal(ctx, selected) {
    ensurePlan(ctx, selected);
    if (canonical(selected.cache.record) !== selected.proposalKey) throw Error('Selected parent plan changed. Inspect the saved proposal again.');
  }
  function proposalFields(selected) {
    if (!selected) return {};
    const cache = selected.proposalCache;
    return { proposalReview: cache.review, proposalRecord: cache.record, proposalPendingId: cache.pending?.id || null,
      proposalCancelRequested: cache.cancelRequested, proposalSeen: [...cache.records].map(([proposal_id, record]) => ({ proposal_id, state: record.state })),
      proposalItems: cache.items, proposalNextCursor: cache.nextCursor, proposalsLoaded: cache.loaded };
  }
  async function proposalOperate(action) {
    const ctx = active;
    if (!current(ctx) || !state.connected) throw Error('Connect to the selected preparation backend first.');
    if (state.busy || state.planBusy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy) throw Error('Another preparation, planning or proposal operation is active.');
    const selected = proposalBinding(ctx); publish(ctx, { proposalBusy: true, proposalError: '', error: '' });
    try { return await action(ctx, selected); }
    catch (error) { fail(ctx, error); publish(ctx, { proposalError: error.message || String(error) }); throw error; }
    finally { publish(ctx, { proposalBusy: false }); }
  }
  const proposalBase = selected => '/' + selected.receipt.request_id + '/plans/' + selected.parent.plan_id;
  async function reviewProposal(ctx, selected) {
    const data = await request(ctx, proposalBase(selected) + '/proposal-review');
    ensureProposal(ctx, selected); own(ctx, data);
    validatePlan(ctx, selected, { ...data, kind: 'project_plan', state: 'PLAN_PROPOSED' }, selected.parent.plan_id);
    const files = selected.receipt.files.map(f => ({ path: f.relative_path, role: f.role, sha256: f.sha256 }));
    if (data.kind !== 'project_proposal_review' || data.state !== 'PLAN_REVIEW_READY' || data.apply_authorized !== false ||
      data.source_complete !== true || data.source_bytes_limit !== 20000 || !HASH.test(data.reviewed_plan_sha256 || '') ||
      !same(data.proposal, selected.parent.proposal) || !same(data.files, files) || !same(data.checks, selected.receipt.checks)) throw Error('Proposal review changed the selected parent or inputs.');
    const cache = selected.proposalCache;
    if (cache.pending && cache.pending.digest !== data.reviewed_plan_sha256) throw Error('Pending proposal review changed; preserve its ID and inspect saved evidence.');
    cache.review = copy(data); publish(ctx, proposalFields(selected)); return data;
  }
  async function validateProposal(ctx, selected, data, id) {
    own(ctx, data); const r = selected.receipt, cache = selected.proposalCache;
    const allowed = ['owner', 'request_id', 'plan_id', 'proposal_id', 'snapshot_sha256', 'review_digest', 'reviewed_plan_sha256',
      'kind', 'state', 'proposal', 'error_code', 'source_status', 'current_sources_rechecked', 'execution_authorized', 'apply_authorized',
      'verification_status', 'model', 'cancel_requested'];
    if (Object.keys(data).some(k => !allowed.includes(k)) || data.kind !== 'project_proposal' || data.request_id !== r.request_id ||
      data.plan_id !== selected.parent.plan_id || data.proposal_id !== id || !PROPOSAL_STATES.has(data.state) ||
      data.snapshot_sha256 !== r.snapshot_sha256 || data.review_digest !== r.review_digest ||
      data.reviewed_plan_sha256 !== cache.review?.reviewed_plan_sha256 || data.execution_authorized !== false || data.apply_authorized !== false ||
      data.verification_status !== 'not_run' || data.source_status !== 'retained_inputs' || data.current_sources_rechecked !== false ||
      data.model !== 'stehouwer_llm:latest' || !(data.error_code === null || typeof data.error_code === 'string' && data.error_code.length <= 100)) throw Error('Proposal response changed the reviewed scope or authority.');
    if (data.state !== 'PROPOSAL_READY') {
      if (data.proposal !== null) throw Error('An unfinished or failed proposal cannot contain candidate source.');
      return;
    }
    const p = data.proposal, editable = r.files.filter(f => f.role === 'editable');
    if (!p || !same(Object.keys(p).sort(), ['diff', 'files', 'summary']) || typeof p.summary !== 'string' || !p.summary.trim() || p.summary.length > 2000 ||
      !Array.isArray(p.files) || p.files.length !== editable.length || new Set(p.files.map(f => f?.path)).size !== editable.length ||
      typeof p.diff !== 'string' || new TextEncoder().encode(JSON.stringify(data)).length > 65536) throw Error('Saved proposal is malformed or too large.');
    for (const file of p.files) {
      const original = editable.find(f => f.relative_path === file?.path);
      if (!original || !same(Object.keys(file).sort(), ['base_sha256', 'content', 'diff', 'path', 'proposed_sha256']) ||
        file.base_sha256 !== original.sha256 || !HASH.test(file.proposed_sha256 || '') || typeof file.content !== 'string' ||
        file.content.includes('\0') || new TextEncoder().encode(file.content).length > 20000 || typeof file.diff !== 'string' ||
        !file.diff.startsWith('--- a/' + file.path + '\n+++ b/' + file.path + '\n')) throw Error('Candidate file changed selected paths, hashes or limits.');
      if (!globalThis.crypto?.subtle) throw Error('Secure content verification is unavailable in this browser.');
      const bytes = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(file.content));
      ensureProposal(ctx, selected);
      const digest = [...new Uint8Array(bytes)].map(value => value.toString(16).padStart(2, '0')).join('');
      if (digest !== file.proposed_sha256) throw Error('Candidate content does not match its saved SHA-256.');
    }
    if (p.diff !== p.files.map(f => f.diff).join('')) throw Error('Combined proposal diff changed.');
  }
  async function acceptProposal(ctx, selected, data, id) {
    ensureProposal(ctx, selected); await validateProposal(ctx, selected, data, id); ensureProposal(ctx, selected);
    const cache = selected.proposalCache, record = copy(data); delete record.cancel_requested;
    const previous = cache.records.get(id);
    if (previous && PROPOSAL_TERMINAL.has(previous.state)) {
      if (!PROPOSAL_TERMINAL.has(record.state)) return previous;
      if (!same(previous, record)) throw Error('Terminal proposal evidence changed. Inspect the retained record.');
    }
    cache.record = record; cache.records.set(id, record);
    if (PROPOSAL_TERMINAL.has(record.state)) { if (cache.pending?.id === id) cache.pending = null; cache.cancelRequested = false; }
    publish(ctx, proposalFields(selected)); return record;
  }
  async function inspectProposal(ctx, selected, id, recover) {
    if (!ID.test(id || '')) throw Error('Enter a valid saved proposal ID.');
    if (!selected.proposalCache.review) await reviewProposal(ctx, selected);
    const data = await request(ctx, proposalBase(selected) + '/proposals/' + id + (recover ? '/recover' : ''), recover ? 'POST' : 'GET');
    return acceptProposal(ctx, selected, data, id);
  }
  async function loadProposals(ctx, selected, more = false) {
    const cache = selected.proposalCache, cursor = more ? cache.nextCursor : null;
    if (more && !cursor) return;
    const data = await request(ctx, proposalBase(selected) + '/proposals?limit=20' + (cursor ? '&cursor=' + encodeURIComponent(cursor) : ''));
    ensureProposal(ctx, selected); own(ctx, data); const r = selected.receipt;
    const keys = ['apply_authorized', 'execution_authorized', 'proposal_id', 'proposal_revalidated', 'state', 'verification_status'];
    if (data.request_id !== r.request_id || data.plan_id !== selected.parent.plan_id || data.snapshot_sha256 !== r.snapshot_sha256 ||
      data.review_digest !== r.review_digest || data.metadata_only !== true || data.parent_plan_revalidated !== false ||
      !Array.isArray(data.items) || data.items.length > 20 || data.items.some((row, index) =>
        !row || !same(Object.keys(row).sort(), keys) || !ID.test(row.proposal_id || '') || !PROPOSAL_STATES.has(row.state) ||
        row.proposal_revalidated !== false || row.execution_authorized !== false || row.apply_authorized !== false || row.verification_status !== 'not_run' ||
        (cursor && row.proposal_id <= cursor) || (index && row.proposal_id <= data.items[index-1].proposal_id)) ||
      !(data.next_cursor === null || ID.test(data.next_cursor || '') && data.items.at(-1)?.proposal_id === data.next_cursor && (!cursor || data.next_cursor > cursor))) throw Error('Saved proposal history response is invalid.');
    cache.items = more ? [...new Map([...cache.items, ...data.items].map(item => [item.proposal_id, item])).values()] : copy(data.items);
    cache.nextCursor = data.next_cursor; cache.loaded = true; publish(ctx, proposalFields(selected)); return data;
  }
  const client = {
    subscribe(fn) { listeners.add(fn); return () => { listeners.delete(fn); if (!listeners.size) close(); }; },
    getState: () => state,
    syncContext() { if (active && !current(active)) close(); }, close,
    async open() {
      close(); const raw = getContext(); let ctx;
      try {
        ctx = { url: baseURL(raw.backendUrl), actor: raw.actor || '', stamp: stamp(), epoch, cache: null, approved: null }; active = ctx;
        publish(ctx, { phase: 'connecting', busy: true });
        const data = await request(ctx, '/identity');
        if (!validOwner(data?.owner) || !Array.isArray(data.repository_ids) || !data.repository_ids.includes('ai-bs') || data.execution_authorized !== false || data.verification_status !== 'not_run') throw Error('Preparation backend identity is unsupported.');
        ctx.owner = data.owner;
        const key = JSON.stringify([ctx.url, ctx.owner, ctx.actor]);
        if (!contexts.has(key)) contexts.set(key, { form: blank(), pending: null, unconfirmedIds: [], plans: new Map() });
        ctx.cache = contexts.get(key);
        publish(ctx, { phase: 'ready', owner: ctx.owner, connected: true, form: ctx.cache.form, ...pendingFields(ctx) });
        await loadHistory(ctx); return true;
      } catch (error) {
        if (ctx && current(ctx)) { fail(ctx, error); publish(ctx, { connected: false }); }
        else if (!ctx) publish(null, { phase: 'error', error: error.message });
        throw error;
      } finally { publish(ctx, { busy: false }); }
    },
    updateForm(patch) {
      const ctx = active;
      if (!current(ctx) || !state.connected || state.busy || state.planBusy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy || ctx.cache.pending) return false;
      if (Object.entries(patch).some(([key, value]) => !(key in blank()) || typeof value !== 'string')) throw Error('Unsupported preparation field.');
      ctx.cache.form = { ...ctx.cache.form, ...patch }; ctx.approved = null;
      ctx.selectedReceipt = null;
      publish(ctx, { form: ctx.cache.form, preview: null, receipt: null, error: '', ...blankPlanning() }); return true;
    },
    preview() { return operate(async ctx => {
      if (ctx.cache.pending) throw Error('Inspect or keep the pending request before preparing another.');
      const plan = buildPreparationPlan(ctx.cache.form, uuid());
      const data = await request(ctx, '/preview', 'POST', plan); own(ctx, data);
      if (data.state !== 'PREVIEW' || data.request_id !== plan.request_id || data.repository_id !== 'ai-bs' || data.execution_authorized !== false || data.verification_status !== 'not_run' || data.durable !== false || !HASH.test(data.review_digest || '') || !validFiles(data.files) || !same(data.files.map(({ relative_path, role }) => ({ relative_path, role })), plan.files) || !same(data.checks, compiled(plan))) throw Error('Preview did not match the selected plan.');
      ctx.approved = { plan: copy(plan), data: copy(data), formSignature: canonical(ctx.cache.form) };
      ctx.selectedReceipt = null;
      publish(ctx, { preview: data, receipt: null, ...blankPlanning() }); return data;
    }); },
    save() { return operate(async ctx => {
      if (!ctx.cache.pending) {
        if (!ctx.approved || ctx.approved.formSignature !== canonical(ctx.cache.form)) throw Error('Preview the current selected inputs first.');
        ctx.cache.pending = { payload: { ...copy(ctx.approved.plan), review_digest: ctx.approved.data.review_digest }, preview: copy(ctx.approved.data) };
      }
      const pending = ctx.cache.pending; publish(ctx, pendingFields(ctx));
      const data = await request(ctx, '', 'POST', pending.payload);
      validateRecord(ctx, data, pending.payload.request_id);
      if (data.state !== 'PREPARED' || !same(data.files, pending.preview.files) || !same(data.checks, pending.preview.checks) || data.review_digest !== pending.payload.review_digest || !same(data.limits, pending.payload.limits)) throw Error('Saved evidence did not match the reviewed inputs.');
      ctx.cache.pending = null; ctx.approved = null;
      selectReceipt(ctx, data); return data;
    }); },
    inspect(id) { return operate(ctx => inspect(ctx, id, false)); },
    recover(id) { return operate(ctx => inspect(ctx, id, true)); },
    refresh() { return operate(ctx => loadHistory(ctx)); },
    more() { return operate(ctx => loadHistory(ctx, true)); },
    generatePlan() { return planOperate(async (ctx, selected) => {
      const id = selected.cache.pendingId || uuid();
      if (!ID.test(id || '')) throw Error('Invalid new plan ID.');
      if (selected.cache.record?.plan_id !== id) selected.cache.record = null;
      selected.cache.pendingId = id; selected.cache.cancelRequested = false;
      publish(ctx, planFields(selected));
      const data = await request(ctx, '/' + selected.receipt.request_id + '/plans', 'POST', { plan_id: id });
      return acceptPlan(ctx, selected, data, id);
    }); },
    inspectPlan(id) { return planOperate((ctx, selected) => inspectPlan(ctx, selected, id, false)); },
    recoverPlan(id) { return planOperate((ctx, selected) => inspectPlan(ctx, selected, id, true)); },
    refreshPlans() { return planOperate((ctx, selected) => loadPlans(ctx, selected)); },
    morePlans() { return planOperate((ctx, selected) => loadPlans(ctx, selected, true)); },
    reviewProposal() { return proposalOperate((ctx, selected) => reviewProposal(ctx, selected)); },
    generateProposal() { return proposalOperate(async (ctx, selected) => {
      const cache = selected.proposalCache;
      if (!cache.review) throw Error('Review the saved plan and complete source scope before generating code.');
      if (!cache.pending) {
        const id = uuid(); if (!ID.test(id || '')) throw Error('Invalid new proposal ID.');
        cache.pending = { id, digest: cache.review.reviewed_plan_sha256 }; cache.record = null;
      }
      cache.cancelRequested = false; publish(ctx, proposalFields(selected));
      const body = { proposal_id: cache.pending.id, reviewed_plan_sha256: cache.pending.digest };
      const data = await request(ctx, proposalBase(selected) + '/proposals', 'POST', body);
      return acceptProposal(ctx, selected, data, body.proposal_id);
    }); },
    inspectProposal(id) { return proposalOperate((ctx, selected) => inspectProposal(ctx, selected, id, false)); },
    recoverProposal(id) { return proposalOperate((ctx, selected) => inspectProposal(ctx, selected, id, true)); },
    refreshProposals() { return proposalOperate((ctx, selected) => loadProposals(ctx, selected)); },
    moreProposals() { return proposalOperate((ctx, selected) => loadProposals(ctx, selected, true)); },
    setProposalId(value) {
      if (!active || !current(active) || !state.connected || state.busy || state.planBusy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy ||
        typeof value !== 'string' || !/^[a-f0-9]{0,32}$/.test(value)) return false;
      publish(active, { proposalIdInput: value }); return true;
    },
    async cancelProposal(id) {
      const ctx = active;
      if (!current(ctx) || !state.connected || state.busy || state.planBusy || state.planCancelBusy || state.proposalCancelBusy) throw Error('Connect and finish the current cancellation first.');
      if (!ID.test(id || '')) throw Error('Enter a valid saved proposal ID.');
      const selected = proposalBinding(ctx);
      if (!selected.proposalCache.review) throw Error('Inspect the saved proposal scope before cancellation.');
      publish(ctx, { proposalCancelBusy: true, proposalError: '' });
      try {
        const data = await request(ctx, proposalBase(selected) + '/proposals/' + id + '/cancel', 'POST');
        if (typeof data.cancel_requested !== 'boolean') throw Error('Proposal cancellation acknowledgement is invalid.');
        const record = await acceptProposal(ctx, selected, data, id);
        selected.proposalCache.cancelRequested = data.cancel_requested && !PROPOSAL_TERMINAL.has(record.state);
        publish(ctx, proposalFields(selected)); return record;
      } catch (error) { fail(ctx, error); publish(ctx, { proposalError: error.message || String(error) }); throw error; }
      finally { publish(ctx, { proposalCancelBusy: false }); }
    },
    setPlanId(value) {
      if (!active || !current(active) || state.busy || state.planBusy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy || !state.connected || typeof value !== 'string' || !/^[a-f0-9]{0,32}$/.test(value)) return false;
      publish(active, { planIdInput: value }); return true;
    },
    async cancelPlan(id) {
      const ctx = active;
      if (!current(ctx) || !state.connected || state.busy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy) throw Error('Connect and finish the current cancellation first.');
      if (!ID.test(id || '')) throw Error('Enter a valid saved plan ID.');
      const selected = binding(ctx); publish(ctx, { planCancelBusy: true, planError: '' });
      try {
        const data = await request(ctx, '/' + selected.receipt.request_id + '/plans/' + id + '/cancel', 'POST');
        if (typeof data.cancel_requested !== 'boolean') throw Error('Cancellation acknowledgement is invalid.');
        const record = acceptPlan(ctx, selected, data, id);
        selected.cache.cancelRequested = data.cancel_requested && !PLAN_TERMINAL.has(record.state);
        publish(ctx, planFields(selected)); return record;
      } catch (error) { fail(ctx, error); publish(ctx, { planError: error.message || String(error) }); throw error; }
      finally { publish(ctx, { planCancelBusy: false }); }
    },
    keepPending() {
      const ctx = active;
      if (!current(ctx) || !state.connected || state.busy || !ctx.cache.pending) return false;
      const id = ctx.cache.pending.payload.request_id;
      if (!ctx.cache.unconfirmedIds.includes(id)) ctx.cache.unconfirmedIds.push(id);
      ctx.cache.pending = null; ctx.approved = null;
      publish(ctx, { preview: null, ...pendingFields(ctx) }); return true;
    }
  };
  return client;
}

const clients = new WeakMap();
export function preparationClientFor(store) {
  if (!clients.has(store)) {
    const client = createPreparationClient({ getContext: () => ({ backendUrl: store.getState().BACKEND_URL, actor: store.getState().currentUser?.uid || '' }) });
    store.subscribe(() => client.syncContext()); clients.set(store, client);
  }
  return clients.get(store);
}
