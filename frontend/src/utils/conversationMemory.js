/**
 * @typedef {import('/types/domain').ChatMessage} ChatMessage
 * @typedef {{messages: ChatMessage[]; draft: string}} ConversationSnapshot
 * @typedef {{id: string; kind: string; draft?: string; message?: ChatMessage}} WireMessage
 * @typedef {{conversation_id: string; title?: string; local_revision?: number; ack_local_revision?: number; server_revision?: number; closed?: boolean; [key: string]: unknown}} ConversationChoice
 * @typedef {{phase: string; viewReady: boolean; error: string; choices: ConversationChoice[]; owner: string; backendUrl: string; conversationId: string}} MemoryStatus
 * @typedef {{backend: string; owner: string; uid: string; storeBackend: string; cid: string; epoch: number; actorEpoch: number; retired: boolean; metaId: string; ids: string[]; localRevision: number; latest: ConversationSnapshot; lastSignature: string; dirty: boolean; operations: number; tail: Promise<void>; timer: ReturnType<typeof setTimeout> | null; maximum: ReturnType<typeof setTimeout> | null; remoteTimer?: ReturnType<typeof setTimeout>; closed: boolean; admitted: boolean; blocked: boolean; remote: Promise<void> | null; detached?: MemoryContext; quarantine?: MemoryContext; pending?: {signature: string; requestId: string; messages: WireMessage[]} | null}} MemoryContext
 * @typedef {import('zustand').StoreApi<import('/types/domain').AppStore>} ConversationStore
 */
import { openConversationOutbox } from './conversationOutbox.js';
import { readChatHttpResponse } from './chatHttpResponse.js';
import { chatAuthHeaders } from './chatAuth.js';

/** @type {WeakMap<ConversationStore, ReturnType<typeof createConversationMemory>>} */
const managers = new WeakMap();
const uuid = () => crypto.randomUUID().replace(/-/g, '');
/** @template T @param {T} value @returns {T} */
const copy = value => JSON.parse(JSON.stringify(value, (_, item) => {
  if (typeof item === 'number' && !Number.isFinite(item)) throw Error('Nonfinite conversation data cannot be saved.');
  if (['function', 'symbol', 'bigint'].includes(typeof item)) throw Error('Unsupported conversation data cannot be saved.');
  return item;
}));
/** @param {unknown} value */
const canonical = value => JSON.stringify(value, (_, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
/** @param {ConversationStore} store */
const uid = store => store.getState().currentUser?.uid || '';
/** @param {import("/types/domain").AppStore} state @returns {ConversationSnapshot} */
const snapshot = state => ({ messages: state.chatMessages || [], draft: state.footerInput || '' });
/** @param {ConversationSnapshot} state */
const signature = state => JSON.stringify(copy(state));
/** @param {string} value */
const baseURL = value => {
  const parsed = new URL(value, globalThis.location?.href);
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password || parsed.search || parsed.hash) throw Error('Select a valid chat backend.');
  return parsed.href.replace(/\/+$/, '');
};
/** @param {string} left @param {string} right */
export function conversationBackendMatches(left, right) {
  try { return baseURL(left) === baseURL(right); } catch { return false; }
}
/** @param {WireMessage[]} messages @returns {ConversationSnapshot & {metaId: string; ids: string[]}} */
function decode(messages) {
  if (!Array.isArray(messages) || messages[0]?.kind !== 'aibs_state_v1' || typeof messages[0]?.draft !== 'string' ||
      messages.slice(1).some(row => row.kind !== 'aibs_message_v1' || !row.message || typeof row.message !== 'object' || Array.isArray(row.message))) {
    throw Error('Saved conversation format needs review; no history was replaced.');
  }
  return { messages: messages.slice(1).map(row => /** @type {ChatMessage} */ (row.message)), draft: messages[0].draft,
    metaId: messages[0].id, ids: messages.slice(1).map(row => row.id) };
}

/** @param {ConversationStore} store */
function createConversationMemory(store) {
  const listeners = new Set(/** @type {(() => void)[]} */ ([]));
  const contexts = new Set(/** @type {MemoryContext[]} */ ([]));
  /** @type {MemoryStatus} */
  let status = { phase: 'connecting', viewReady: false, error: '', choices: [], owner: '', backendUrl: '', conversationId: '' };
  /** @type {MemoryContext | null} */
  let active = null;
  /** @type {Promise<void> | undefined} */
  let configuring;
  let epoch = 0, actorEpoch = 0, configured = '', suppress = false, cancel = () => {};
  const db = openConversationOutbox();
  // Attach a rejection handler immediately; unavailable storage stays a failure.
  db.catch(() => {});
  /** @param {Partial<MemoryStatus>} patch */
  const notify = patch => { status = { ...status, ...patch }; listeners.forEach(fn => fn()); };
  /** @param {MemoryContext | null | undefined} ctx @returns {boolean} */
  const current = ctx => Boolean(ctx && !ctx.retired && ctx === active && ctx.epoch === epoch && ctx.actorEpoch === actorEpoch && uid(store) === ctx.uid && store.getState().BACKEND_URL === ctx.storeBackend);
  /** @param {MemoryContext} ctx */
  const requireCurrent = ctx => { if (!current(ctx)) throw Error('Chat identity or backend changed.'); };
  /** @param {MemoryContext} ctx */
  const scope = ctx => ({ backendUrl: ctx.backend, owner: ctx.owner, conversationId: ctx.cid });
  /** @param {MemoryContext} ctx */
  const pointerKey = ctx => 'aibs-conversation:' + JSON.stringify([ctx.backend, ctx.owner]);
  /** @param {ConversationSnapshot} source */
  const restore = source => {
    suppress = true;
    try { store.setState({ chatMessages: source.messages, footerInput: source.draft }); } finally { suppress = false; }
  };
  /** @param {string} backend @param {string} owner @param {string} actor @param {string} storeBackend @param {string} [cid] @returns {MemoryContext} */
  function context(backend, owner, actor, storeBackend, cid = uuid()) {
    /** @type {MemoryContext} */
    const ctx = { backend, owner, uid: actor, storeBackend, cid, epoch, actorEpoch, retired: false, metaId: uuid(), ids: [], localRevision: 0,
      latest: { messages: [], draft: '' }, lastSignature: '', dirty: false, operations: 0, tail: Promise.resolve(),
      timer: null, maximum: null, closed: false, admitted: false, blocked: false, remote: null };
    contexts.add(ctx); return ctx;
  }
  /** @param {MemoryContext | null} ctx @param {ConversationSnapshot} source */
  function retire(ctx, source) {
    if (!ctx || ctx.retired) return;
    ctx.retired = true;
    // Capture the last owned state once, before a new actor can replace the store.
    ctx.latest = copy(source);
    clearTimeout(ctx.remoteTimer);
    if (ctx.admitted) flushLocal(ctx).catch(error => fail(ctx, error));
  }
  /** @param {MemoryContext} ctx @param {boolean} [closed] */
  function choice(ctx, closed = false) {
    if (current(ctx)) notify({ choices: [...new Map([...status.choices,
      { conversation_id: ctx.cid, title: 'BS-Chat conversation', closed }].map(row => [row.conversation_id, row])).values()] });
  }
  /** @param {MemoryContext | null} ctx @param {unknown} error */
  function fail(ctx, error) {
    if (ctx && current(ctx)) notify({ phase: ctx.blocked ? 'conflict' : 'error', error: error instanceof Error ? error.message : String(error) });
  }
  /** @param {MemoryContext} ctx @param {ConversationSnapshot} source */
  function wire(ctx, source) {
    const value = copy(source);
    /** @type {WireMessage[]} */
    const result = [{ id: ctx.metaId, kind: 'aibs_state_v1', draft: value.draft }];
    value.messages.forEach((message, index) => result.push({ id: ctx.ids[index] ||= uuid(), kind: 'aibs_message_v1', message }));
    ctx.ids.length = value.messages.length;
    return result;
  }
  /** @param {MemoryContext} ctx */
  function arm(ctx) {
    ctx.dirty = true;
    if (ctx && current(ctx)) notify({ phase: ctx.blocked ? 'conflict' : 'pending', error: ctx.blocked ? status.error : '' });
    clearTimeout(ctx.timer ?? undefined);
    const save = () => flushLocal(ctx).then(() => { if (current(ctx)) scheduleRemote(ctx); }).catch(error => fail(ctx, error));
    ctx.timer = setTimeout(save, ctx.localRevision ? 500 : 0);
    if (!ctx.maximum) ctx.maximum = setTimeout(save, 3000);
  }
  /** @param {MemoryContext | null} [ctx] @returns {Promise<void>} */
  async function flushLocal(ctx = active) {
    if (!ctx) throw Error('Conversation identity is not ready.');
    clearTimeout(ctx.timer ?? undefined); clearTimeout(ctx.maximum ?? undefined); ctx.timer = ctx.maximum = null;
    ctx.operations++;
    ctx.tail = ctx.tail.catch(() => {}).then(async () => {
      const source = copy(ctx.latest), sig = signature(source);
      if (!source.messages.length && !source.draft && !ctx.localRevision) { ctx.dirty = false; return; }
      if (ctx.closed) {
        ctx.detached ||= context(ctx.backend, ctx.owner, ctx.uid, ctx.storeBackend);
        ctx.detached.admitted = true; ctx.detached.latest = source;
        await flushLocal(ctx.detached); ctx.dirty = false; return;
      }
      const outbox = await db;
      if (sig !== ctx.lastSignature) {
        if (ctx.pending?.signature !== sig) ctx.pending = { signature: sig, requestId: uuid(), messages: wire(ctx, source) };
        const saved = await outbox.queueSnapshot({ ...scope(ctx), expectedLocalRevision: ctx.localRevision,
          requestId: ctx.pending.requestId, messages: ctx.pending.messages, title: 'BS-Chat conversation' });
        ctx.localRevision = saved.local_revision; ctx.lastSignature = sig; ctx.pending = null;
        choice(ctx);
      }
      sessionStorage.setItem(pointerKey(ctx), ctx.cid);
      ctx.dirty = signature(ctx.latest) !== sig;
      if (current(ctx)) notify({ conversationId: ctx.cid });
    }).finally(() => { ctx.operations--; });
    return ctx.tail;
  }
  /** @param {MemoryContext} ctx @param {string} path @param {RequestInit} [options] */
  async function json(ctx, path, options = {}) {
    if (!current(ctx)) throw Error('Chat identity or backend changed.');
    const headers = await chatAuthHeaders(options.headers, ctx.uid);
    if (!current(ctx)) throw Error('Chat identity or backend changed.');
    const response = await fetch(ctx.backend + path, { ...options, headers,
      signal: typeof AbortSignal.timeout === 'function' ? AbortSignal.timeout(15000) : undefined });
    if (response.status === 409) {
      const error = Error('Another save changed this conversation. Pending edits are retained; save a separate copy to continue.');
      throw Object.assign(error, {conflict: true});
    }
    const result = await readChatHttpResponse(response);
    if (!current(ctx)) throw Error('Chat identity or backend changed.');
    return result;
  }
  /** @param {MemoryContext} ctx */
  function scheduleRemote(ctx) {
    if (ctx.blocked || !ctx.admitted || !current(ctx)) return;
    clearTimeout(ctx.remoteTimer);
    ctx.remoteTimer = setTimeout(() => flushRemote(ctx).catch(error => fail(ctx, error)), 750);
  }
  /** @param {MemoryContext | null} [ctx] @returns {Promise<void>} */
  async function flushRemote(ctx = active) {
    if (!ctx || !current(ctx) || !ctx.admitted) throw Error('Verify the current conversation identity first.');
    if (ctx.blocked) throw Error('Resolve the retained conflict or save a separate copy.');
    clearTimeout(ctx.remoteTimer);
    if (ctx.remote) { await ctx.remote; return flushRemote(ctx); }
    ctx.remote = (async () => {
      await flushLocal(ctx);
      const outbox = await db;
      while (current(ctx) && !ctx.closed) {
        const prepared = await outbox.prepareNext(scope(ctx));
        if (!prepared) break;
        notify({ phase: 'saving', error: '' });
        let result;
        try {
          result = await json(ctx, '/api/memory/conversations/' + ctx.cid, { method: 'POST',
            headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(prepared.body) });
        } catch (error) {
          if (error instanceof Error && 'conflict' in error && error.conflict) { await outbox.markConflict({ ...scope(ctx), requestId: prepared.body.request_id }); ctx.blocked = true; }
          throw error;
        }
        if (result?.status !== 'success' || !result.receipt) throw Error('Server save was not confirmed.');
        const readback = await json(ctx, '/api/memory/conversations/' + ctx.cid + '?revision=' + result.receipt.revision);
        if (readback.conversation_id !== ctx.cid || canonical(readback.receipt) !== canonical(result.receipt) ||
            canonical({ messages: readback.messages, title: readback.title }) !== canonical({ messages: prepared.body.messages, title: prepared.body.title })) {
          throw Error('Server readback does not match the complete pending source.');
        }
        await outbox.acknowledge({ ...scope(ctx), requestId: prepared.body.request_id, receipt: result.receipt });
      }
      if (current(ctx)) notify({ phase: ctx.dirty || ctx.operations ? 'pending' : 'saved', error: '' });
    })();
    try { return await ctx.remote; } finally { ctx.remote = null; }
  }
  /** @param {MemoryContext} ctx @param {NonNullable<Awaited<ReturnType<Awaited<ReturnType<typeof openConversationOutbox>>['loadConversation']>>>} saved */
  async function loadInto(ctx, saved) {
    const latest = saved.entries[saved.entries.length - 1];
    const source = decode(latest.snapshot.messages);
    ctx.localRevision = saved.head.local_revision; ctx.metaId = source.metaId; ctx.ids = source.ids;
    ctx.latest = { messages: source.messages, draft: source.draft }; ctx.lastSignature = signature(ctx.latest);
    ctx.blocked = saved.entries.some(row => row.status === 'conflict'); ctx.closed = saved.head.closed;
  }
  /** @param {MemoryContext} ctx */
  async function refreshChoices(ctx) {
    const local = await (await db).listConversations(scope(ctx));
    /** @type {ConversationChoice[]} */
    let remote = [];
    try {
      const response = await json(ctx, '/api/memory/conversations');
      if (!Array.isArray(response.items)) throw Error('History list was not confirmed.');
      remote = response.items;
    } catch (error) { if (current(ctx)) notify({ error: 'History list unavailable: ' + (error instanceof Error ? error.message : String(error)) }); }
    if (current(ctx)) notify({ choices: [...new Map([...remote, ...local].map(row => [row.conversation_id, row])).values()] });
    return local;
  }
  /** @param {string} backendUrl @param {string} actor @param {string} storeBackend @param {() => void} [onCancel] */
  async function configure(backendUrl, actor, storeBackend, onCancel) {
    cancel = onCancel || (() => {});
    const backend = baseURL(backendUrl), key = JSON.stringify([backend, actor, storeBackend, actorEpoch]);
    if (configured === key) return configuring;
    configured = key; const old = active; const oldSource = old?.retired ? old.latest : snapshot(store.getState());
    retire(old, oldSource);
    const configuringEpoch = ++epoch, configuringActorEpoch = actorEpoch;
    const stillConfiguring = () => configured === key && epoch === configuringEpoch && actorEpoch === configuringActorEpoch && uid(store) === actor && store.getState().BACKEND_URL === storeBackend;
    notify({ phase: 'connecting', viewReady: false, error: '', choices: [], backendUrl: backend, owner: '', conversationId: '' }); cancel();
    configuring = (async () => {
      if (old?.admitted) { await flushLocal(old); if (!stillConfiguring()) return; restore({ messages: [], draft: '' }); }
      else if (old && (old.retired || old.uid !== actor || old.backend !== backend) && (oldSource.messages.length || oldSource.draft)) {
        old.quarantine ||= context(old.backend, 'unassigned:profile:' + old.uid, old.uid, old.storeBackend);
        old.quarantine.latest = oldSource; await flushLocal(old.quarantine);
        if (!stillConfiguring()) return;
        restore({ messages: [], draft: '' });
      }
      if (!stillConfiguring()) return;
      if (!actor) throw Error('Sign in before opening saved chat history.');
      const ctx = context(backend, '', actor, storeBackend); active = ctx;
      const identity = await json(ctx, '/api/memory/conversations/identity');
      if (identity?.storage !== 'sqlite_vault' || typeof identity.owner !== 'string' ||
          !(identity.owner === 'local_admin' || identity.owner.startsWith('firebase:') && identity.owner.endsWith(':' + actor))) throw Error('The backend did not confirm this signed-in identity.');
      ctx.owner = identity.owner;
      await db;
      if (!current(ctx)) return;
      const initial = snapshot(store.getState());
      if (!old?.admitted && (initial.messages.length || initial.draft)) {
        const quarantine = context(backend, 'unassigned:profile:' + actor, actor, storeBackend);
        quarantine.latest = initial; await flushLocal(quarantine);
        ctx.latest = initial; ctx.quarantine = quarantine;
        notify({ phase: 'unassigned', viewReady: false, owner: ctx.owner, backendUrl: ctx.backend,
          error: 'Existing chat was retained locally. Confirm ownership before adding it to this history.' });
        return;
      }
      const local = await refreshChoices(ctx);
      if (!current(ctx)) return;
      const pointer = sessionStorage.getItem(pointerKey(ctx));
      const candidate = pointer || (local.filter(row => !row.closed).length === 1 ? local.find(row => !row.closed)?.conversation_id : null);
      if (candidate) {
        const saved = await (await db).loadConversation({ ...scope(ctx), conversationId: candidate });
        if (!current(ctx)) return;
        if (saved && !saved.head.closed) { ctx.cid = candidate; await loadInto(ctx, saved); }
        if (!current(ctx)) return;
      }
      if (!ctx.localRevision) {
        const outbox = await db, owner = 'unassigned:profile:' + actor;
        const unknown = (await outbox.listConversations({ backendUrl: backend, owner })).filter(row => !row.closed);
        if (!current(ctx)) return;
        const pending = sessionStorage.getItem('aibs-conversation:' + JSON.stringify([backend, owner]));
        const selected = unknown.find(row => row.conversation_id === pending) || (unknown.length === 1 ? unknown[0] : null);
        if (selected) {
          const retained = await outbox.loadConversation({ backendUrl: backend, owner, conversationId: selected.conversation_id });
          if (!current(ctx)) return;
          if (!retained) throw Error('Retained conversation is missing; existing chat was preserved.');
          const source = decode(retained.entries[retained.entries.length - 1].snapshot.messages);
          ctx.quarantine = context(backend, owner, actor, storeBackend, selected.conversation_id);
          await loadInto(ctx.quarantine, retained);
          if (!current(ctx)) return;
          ctx.latest = { messages: source.messages, draft: source.draft };
          notify({ phase: 'unassigned', viewReady: false, owner: ctx.owner, backendUrl: ctx.backend,
            error: 'Existing chat was retained locally. Confirm ownership before adding it to this history.' });
          return;
        }
        if (unknown.length) throw Error('Multiple unassigned chats are retained locally and need individual review.');
      }
      if (!current(ctx)) return;
      ctx.admitted = true; restore(ctx.latest);
      notify({ phase: ctx.blocked ? 'conflict' : 'ready', viewReady: true, owner: ctx.owner, backendUrl: ctx.backend, conversationId: ctx.cid });
      if (ctx.localRevision && !ctx.blocked) scheduleRemote(ctx);
    })().catch(error => {
      if (configured === key) notify({ phase: 'error', viewReady: false, error: error instanceof Error ? error.message : String(error) });
    });
    return configuring;
  }
  store.subscribe((state, previous) => {
    if (state.BACKEND_URL !== previous.BACKEND_URL || (state.currentUser?.uid || '') !== (previous.currentUser?.uid || '')) {
      actorEpoch++; configured = '';
      retire(active, snapshot(previous));
      notify({ phase: 'connecting', viewReady: false, error: '', choices: [] }); cancel();
      return;
    }
    if (suppress || !active) return;
    const ctx = active;
    if (!current(ctx)) {
      if (!ctx.retired && ctx.admitted && (previous.chatMessages.length || previous.footerInput)) { ctx.latest = snapshot(previous); flushLocal(ctx).catch(error => fail(ctx, error)); }
      notify({ viewReady: false }); return;
    }
    if (!ctx.admitted || state.chatMessages === previous.chatMessages && state.footerInput === previous.footerInput) return;
    if (ctx.closed) { active = context(ctx.backend, ctx.owner, ctx.uid, ctx.storeBackend); active.admitted = true; notify({ conversationId: active.cid }); }
    active.latest = snapshot(state);
    arm(active);
  });
  if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
    if ([...contexts].some(ctx => ctx.dirty || ctx.operations) || status.phase === 'unassigned' || status.phase === 'error') {
      event.preventDefault(); event.returnValue = '';
    }
  });
  const manager = {
    subscribe: /** @param {() => void} fn */ fn => { listeners.add(fn); return () => listeners.delete(fn); }, getStatus: () => status,
    configure, getBinding: () => active, isCurrent: current,
    getActorSnapshot: () => JSON.stringify([store.getState().BACKEND_URL, uid(store), actorEpoch]),
    /** @template {keyof ConversationSnapshot} K @param {MemoryContext | null} ctx @param {K} field @param {import('/types/domain').Update<ConversationSnapshot[K]>} updater */
    change(ctx, field, updater) {
      if (!ctx?.admitted) throw Error('Verify conversation ownership before editing chat.');
      if (current(ctx)) {

        if (field === 'messages') store.getState().setChatMessages(/** @type {import('/types/domain').Update<ChatMessage[]>} */ (updater));
        else store.getState().setFooterInput(/** @type {import('/types/domain').Update<string>} */ (updater));
      } else {
        ctx.latest = { ...ctx.latest, [field]: typeof updater === 'function' ? updater(ctx.latest[field]) : updater };
        arm(ctx);
      }
    },
    flushLocal: () => flushLocal(),
    async retry() {
      if (!active?.admitted || !current(active)) { configured = ''; return configure(status.backendUrl || active?.backend || "", uid(store), store.getState().BACKEND_URL, cancel); }
      try {
        for (const ctx of contexts) if (ctx.dirty || ctx.operations) await flushLocal(ctx);
        await flushLocal(); await flushRemote();
      } catch (error) { fail(active, error); throw error; }
    },
    /** @param {MemoryContext | null} ctx @param {{serialized?: string; backendUrl?: string; receipt?: {owner?: string}}} [options] */
    async beforeClear(ctx, { serialized, backendUrl, receipt } = {}) {
      if (!ctx || !current(ctx) || !ctx.admitted || receipt?.owner !== ctx.owner || (!backendUrl || baseURL(backendUrl) !== ctx.backend) || serialized !== JSON.stringify(store.getState().chatMessages)) return false;
      ctx.latest = snapshot(store.getState()); await flushLocal(ctx);
      if (!ctx || !current(ctx) || serialized !== JSON.stringify(store.getState().chatMessages)) return false;
      await (await db).closeConversation({ ...scope(ctx), expectedLocalRevision: ctx.localRevision });
      ctx.closed = true; clearTimeout(ctx.remoteTimer);
      choice(ctx, true);
      return true;
    },
    async adoptExisting() {
      const ctx = active;
      if (!ctx || !current(ctx) || status.phase !== 'unassigned') throw Error('No unassigned conversation is selected.');
      try {
        ctx.admitted = true; restore(ctx.latest);
        notify({ viewReady: true, phase: 'pending', error: '' });
        await flushLocal(ctx);
        if (ctx.quarantine) await (await db).closeConversation({ ...scope(ctx.quarantine), expectedLocalRevision: ctx.quarantine.localRevision });
        await flushRemote(ctx);
      } catch (error) { fail(ctx, error); throw error; }
    },
    async saveSeparateCopy() {
      const old = active;
      if (!old || !current(old) || !old.admitted) throw Error('Verify the current chat first.');
      await flushLocal(old);
      // A local commit can finish after an account/backend switch. Never copy
      // that new view into the owner captured by the earlier action.
      requireCurrent(old);
      const ctx = context(old.backend, old.owner, old.uid, old.storeBackend);
      ctx.latest = snapshot(store.getState()); ctx.admitted = true; active = ctx;
      notify({ phase: 'pending', error: '', conversationId: ctx.cid });
      await flushLocal(ctx); requireCurrent(ctx);
      await flushRemote(ctx); requireCurrent(ctx);
      await refreshChoices(ctx);
    },
    /** @param {string} cid */
    async recover(cid) {
      const old = active;
      if (!old || !current(old) || !old.admitted || !/^[a-f0-9]{32}$/.test(cid)) throw Error('Select a current authorized history entry.');
      await flushLocal(old); requireCurrent(old);
      cancel(); requireCurrent(old); epoch++;
      const ctx = context(old.backend, old.owner, old.uid, old.storeBackend, cid); active = ctx;
      notify({ phase: 'connecting', viewReady: false, error: '' });
      try {
        const outbox = await db; requireCurrent(ctx);
        let saved = await outbox.loadConversation(scope(ctx)); requireCurrent(ctx);
        if (!saved) {
          const remote = await json(ctx, '/api/memory/conversations/' + cid);
          decode(remote.messages);
          if (remote.conversation_id !== cid || remote.receipt?.durable !== true || remote.receipt.revision !== remote.revision) throw Error('Remote history was not confirmed.');
          await outbox.queueSnapshot({ ...scope(ctx), expectedLocalRevision: 0, baseServerRevision: remote.receipt.expected_revision,
            requestId: remote.receipt.request_id, messages: remote.messages, title: remote.title });
          requireCurrent(ctx);
          await outbox.prepareNext(scope(ctx)); requireCurrent(ctx);
          await outbox.acknowledge({ ...scope(ctx), requestId: remote.receipt.request_id, receipt: remote.receipt }); requireCurrent(ctx);
          saved = await outbox.loadConversation(scope(ctx)); requireCurrent(ctx);
        }
        if (!saved) throw Error('Conversation is missing; existing chat was preserved.');
        await loadInto(ctx, saved); requireCurrent(ctx);
        const closedCopy = ctx.closed;
        if (closedCopy) { ctx.cid = uuid(); ctx.localRevision = 0; ctx.closed = false; ctx.lastSignature = ''; ctx.metaId = uuid(); ctx.ids = []; }
        ctx.admitted = true; restore(ctx.latest); sessionStorage.setItem(pointerKey(ctx), ctx.cid);
        if (closedCopy) { await flushLocal(ctx); requireCurrent(ctx); }
        notify({ phase: ctx.blocked ? 'conflict' : 'ready', viewReady: true, conversationId: ctx.cid });
        if (closedCopy) scheduleRemote(ctx);
      } catch (error) { fail(ctx, error); throw error; }
    },
  };
  return manager;
}

/** @param {ConversationStore} store */
export function conversationMemoryFor(store) {
  let manager = managers.get(store);
  if (!manager) { manager = createConversationMemory(store); managers.set(store, manager); }
  return manager;
}
