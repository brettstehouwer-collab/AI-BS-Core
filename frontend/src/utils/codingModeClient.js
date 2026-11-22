import { readChatHttpResponse } from './chatHttpResponse.js';
import { codingIdentifier, validateCodingExecution } from './codingMode.js';

/** @typedef {{owner:string,enabled:boolean,languages:string[],execution_available:boolean,apply_available:boolean,trusted_local_available?:boolean,blocked_reason?:string}} Capabilities */
/** @typedef {ReturnType<typeof validateCodingExecution> & {owner?:string}} Execution */
/** @typedef {{execution_id:string,state:string,verification_status:string,created_at_utc?:string}} HistoryItem */
/** @typedef {{capabilities:Capabilities|null,items:HistoryItem[],nextCursor:string|null,execution:Execution|null,executionId:string,busy:boolean,error:string,executionBackend:string,trustedLocalAck:boolean,reviewToken:string,polling:boolean}} ClientState */

/** All reads and writes bind to the backend/account generation that started them.
 * @param {{getContext:()=>{backendUrl:string,actor:string},headers:(actor:string)=>Promise<HeadersInit>,fetchImpl?:typeof fetch,uuid?:()=>string,schedule?:typeof setTimeout,unschedule?:typeof clearTimeout,pollLimit?:number}} options
 */
export function createCodingModeClient({ getContext, headers, fetchImpl = (...args) => fetch(...args), uuid = () => crypto.randomUUID().replace(/-/g, ''), schedule = setTimeout, unschedule = clearTimeout, pollLimit = 300 }) {
  const blank = () => (/** @type {ClientState} */ ({capabilities:null,items:[],nextCursor:null,execution:null,executionId:'',busy:false,error:'',executionBackend:'isolated',trustedLocalAck:false,reviewToken:'',polling:false}));
  let state = Object.freeze(blank());
  let context = getContext(), stamp = JSON.stringify(context), epoch = 0, disposed = false;
  const listeners = new Set(), controllers = new Set();
  const publish = patch => { if (disposed) return; state = Object.freeze({...state,...patch}); listeners.forEach(listener => listener()); };
  let pollTimer = null, pollId = '', pollCount = 0, pollStarted = 0;
  function stopPolling() {
    if (pollTimer !== null) unschedule(pollTimer);
    pollTimer = null; pollId = ''; pollCount = 0; pollStarted = 0;
  }
  function watch(value, generation) {
    if (!current(generation)) return;
    if (pollTimer !== null) unschedule(pollTimer);
    pollTimer = null;
    if (value.state !== 'RUNNING') { stopPolling(); publish({polling:false}); return; }
    if (pollId !== value.execution_id) { pollId = value.execution_id; pollStarted = Date.now(); pollCount = 0; }
    if (pollCount >= Math.min(300,pollLimit) || Date.now() - pollStarted >= 600000) {
      stopPolling(); publish({polling:false,error:'Automatic status refresh stopped after its limit. Inspect this saved execution to resume status reads; execution was not replayed.'}); return;
    }
    publish({polling:true});
    pollTimer = schedule(async () => {
      pollTimer = null;
      if (!current(generation) || state.executionId !== value.execution_id || state.execution?.state !== 'RUNNING') return;
      if (state.busy) { watch(value,generation); return; }
      pollCount++;
      await api.execution('inspect',{execution_id:value.execution_id,polling:true});
    },2000);
  }
  function syncContext() {
    const next = getContext(), key = JSON.stringify(next);
    if (key !== stamp) {
      context = next; stamp = key; epoch++;
      stopPolling();
      controllers.forEach(controller => controller.abort()); controllers.clear();
      publish(blank());
    }
  }
  const current = generation => { syncContext(); return !disposed && epoch === generation; };
  async function request(generation, suffix, method = 'GET', body = undefined) {
    if (!current(generation)) throw Error('Coding account or backend changed.');
    const selected = {...context};
    if (!selected.actor) throw Error('Sign in before connecting Coding mode.');
    const authHeaders = await headers(selected.actor);
    if (!current(generation)) throw Error('Coding account or backend changed.');
    const controller = new AbortController(); controllers.add(controller);
    try {
      const response = await fetchImpl(`${selected.backendUrl.replace(/\/$/, '')}/api/chat/coding-tasks/mode${suffix}`, {
        method, headers:authHeaders, signal:controller.signal, ...(body === undefined ? {} : {body:JSON.stringify(body)}) });
      const value = await readChatHttpResponse(response);
      if (!current(generation)) throw Error('Coding account or backend changed.');
      return value;
    } finally { controllers.delete(controller); }
  }
  function own(value) {
    if (!state.capabilities || value?.owner !== state.capabilities.owner) throw Error('Coding evidence belongs to another account.');
  }
  async function operate(action) {
    syncContext(); if (disposed || state.busy) return;
    const generation = epoch; publish({busy:true,error:''});
    try { return await action(generation); }
    catch (error) { if (current(generation)) { stopPolling(); publish({polling:false,error:error instanceof Error ? error.message : 'Coding evidence could not be confirmed.'}); } }
    finally { if (current(generation)) publish({busy:false}); }
  }
  async function history(generation, more = false) {
    if (!state.capabilities?.enabled) return;
    const cursor = more ? state.nextCursor : null;
    const value = await request(generation, `/executions${cursor ? `?cursor=${codingIdentifier(cursor)}` : ''}`);
    if (!Array.isArray(value.items)) throw Error('Saved coding history is invalid.');
    own(value);
    const items = value.items.map(item => {
      codingIdentifier(item.execution_id); codingIdentifier(item.request_id); codingIdentifier(item.plan_id); codingIdentifier(item.proposal_id);
      if (!['RUNNING','VERIFIED','FAILED','CANCELLED','INTERRUPTED','BLOCKED','INCOMPLETE'].includes(item.state)
          || !['not_run','passed','failed'].includes(item.verification_status) || typeof item.created_at_utc !== 'string') throw Error('Saved coding history is invalid.');
      return item;
    });
    const nextCursor = value.next_cursor === null || value.next_cursor === undefined ? null : codingIdentifier(value.next_cursor);
    const merged = more ? [...state.items, ...items] : items;
    publish({items:[...new Map(merged.map(item => [item.execution_id,item])).values()],nextCursor});
  }
  const api = {
    getState: () => state,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    syncContext,
    disconnect() { epoch++; stopPolling(); controllers.forEach(controller => controller.abort()); controllers.clear(); publish(blank()); },
    dispose() { disposed = true; epoch++; stopPolling(); controllers.forEach(controller => controller.abort()); controllers.clear(); listeners.clear(); },
    setExecutionId(value) { syncContext(); if (!state.busy) { stopPolling(); publish({executionId:value,execution:null,error:'',reviewToken:'',polling:false}); } },
    selectExecutionBackend(value) {
      syncContext(); if (state.busy) return;
      if (!['isolated','trusted_host'].includes(value)) throw Error('Unsupported execution mode.');
      publish({executionBackend:value,trustedLocalAck:false});
    },
    acknowledgeTrustedLocal(value) { syncContext(); if (!state.busy) publish({trustedLocalAck:state.executionBackend === 'trusted_host' && value === true}); },
    connect() { return operate(async generation => {
      const value = await request(generation, '/capabilities');
      if (!value || typeof value.owner !== 'string' || !value.owner || typeof value.enabled !== 'boolean'
          || typeof value.execution_available !== 'boolean' || typeof value.apply_available !== 'boolean'
          || !Array.isArray(value.languages) || value.languages.some(item => typeof item !== 'string')) throw Error('Coding capabilities are unconfirmed.');
      if (state.capabilities && state.capabilities.owner !== value.owner) {
        stopPolling(); publish({execution:null,executionId:'',reviewToken:'',polling:false});
      }
      publish({capabilities:value,items:[],nextCursor:null});
      await history(generation);
      return value;
    }); },
    refresh(more = false) { return operate(generation => history(generation, more)); },
    execution(action, payload = {}) { return operate(async generation => {
      if (!state.capabilities?.enabled) throw Error('Coding mode is disabled on the selected backend.');
      const allowed = new Set(['create','inspect','recover','cancel','review','apply']);
      if (!allowed.has(action)) throw Error('Unsupported coding action.');
      if (action === 'create' && state.executionBackend === 'trusted_host'
          && (state.capabilities?.trusted_local_available !== true || !state.trustedLocalAck)) throw Error('Trusted local checks require current backend support and acknowledgement for this task.');
      if (action === 'apply' && (!state.reviewToken || state.execution?.can_apply !== true || state.execution?.state !== 'VERIFIED'
          || state.execution?.verification_status !== 'passed')) throw Error('Review the verified candidate before applying it.');
      const id = action === 'create' ? codingIdentifier(uuid()) : codingIdentifier(payload.execution_id || state.executionId);
      if (action === 'apply' && id !== state.executionId) throw Error('The reviewed execution changed. Review this candidate again.');
      const body = action === 'create' ? {execution_id:id,request_id:codingIdentifier(payload.request_id),plan_id:codingIdentifier(payload.plan_id),proposal_id:codingIdentifier(payload.proposal_id),
        execution_backend:state.executionBackend,trusted_local_ack:state.trustedLocalAck} : action === 'apply' ? {review_token:state.reviewToken} : undefined;
      if (!payload.polling) stopPolling();
      publish({executionId:id,execution:payload.polling ? state.execution : null,reviewToken:'',...(!payload.polling ? {polling:false} : {}),
        ...(action === 'create' ? {executionBackend:'isolated',trustedLocalAck:false} : {})});
      const suffix = action === 'create' ? '' : `/${id}${action === 'inspect' ? '' : `/${action}`}`;
      const value = await request(generation, `/executions${suffix}`, action === 'inspect' ? 'GET' : 'POST', body);
      own(value); validateCodingExecution(value,id);
      const reviewToken = action === 'review' && value.can_apply === true && typeof value.review_token === 'string' && value.review_token ? value.review_token : '';
      publish({execution:value,items:[value,...state.items.filter(item => item.execution_id !== id)],reviewToken});
      watch(value,generation);
    }); }
  };
  return api;
}
