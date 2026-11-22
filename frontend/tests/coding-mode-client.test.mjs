import test from 'node:test';
import assert from 'node:assert/strict';
import { createCodingModeClient } from '../src/utils/codingModeClient.js';

const id = 'a'.repeat(32), plan = 'b'.repeat(32), proposal = 'c'.repeat(32);
const cap = {owner:'owner-a',enabled:true,languages:['python','javascript','jsx'],execution_available:false,apply_available:false};
const item = {execution_id:id,request_id:id,plan_id:plan,proposal_id:proposal,state:'BLOCKED',verification_status:'not_run',created_at_utc:'2026-11-14T00:00:00Z'};
const execution = {...item,owner:'owner-a',execution_authorized:false,apply_authorized:false};
const json = (body,status = 200) => new Response(JSON.stringify(body),{status});
function fixture(handler, headers = async () => ({Authorization:'Bearer synthetic'}), options = {}) {
  let context = {backendUrl:'http://127.0.0.1:8080',actor:'a'};
  const calls = [];
  const client = createCodingModeClient({...options,getContext:()=>context,headers,uuid:()=>id,fetchImpl:async (url,options) => {
    calls.push({url,options}); return handler(url,options);
  }});
  return {client,calls,setContext(value) {context = value; client.syncContext();}};
}

test('connect discovers retained IDs and inspect alone loads complete candidate evidence', async () => {
  const f = fixture(url => json(url.endsWith('/capabilities') ? cap : url.endsWith(`/executions/${id}`) ? execution : {owner:cap.owner,items:[item],next_cursor:null,metadata_only:true}));
  await f.client.connect();
  assert.equal(f.client.getState().items[0].execution_id,id);
  assert.equal(f.client.getState().execution,null);
  await f.client.execution('inspect',{execution_id:id});
  assert.equal(f.client.getState().execution.execution_id,id);
  assert.ok(f.calls.every(call => call.options.method === 'GET'));
  const reopened = fixture(url => json(url.endsWith('/capabilities') ? cap : {owner:cap.owner,items:[item],next_cursor:null}));
  await reopened.client.connect();
  assert.equal(reopened.client.getState().items[0].execution_id,id);
});

test('disabled backend is visible and cannot dispatch candidate creation', async () => {
  const f = fixture(() => json({...cap,enabled:false}));
  await f.client.connect();
  await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal});
  assert.equal(f.calls.length,1);
  assert.match(f.client.getState().error,/disabled/);
});

test('an account change during credential acquisition prevents dispatch', async () => {
  let resolveHeaders;
  const f = fixture(() => json(cap),() => new Promise(resolve => {resolveHeaders = resolve;}));
  const connecting = f.client.connect();
  f.setContext({backendUrl:'http://127.0.0.1:8080',actor:'b'});
  resolveHeaders({Authorization:'Bearer synthetic'});
  await connecting;
  assert.equal(f.calls.length,0);
  assert.equal(f.client.getState().capabilities,null);
  assert.equal(f.client.getState().error,'');
});

test('away-and-back account changes retire an in-flight response', async () => {
  let release;
  const f = fixture(() => new Promise(resolve => {release = resolve;}));
  const connecting = f.client.connect();
  await new Promise(resolve => setImmediate(resolve));
  f.setContext({backendUrl:'http://127.0.0.1:8080',actor:'b'});
  f.setContext({backendUrl:'http://127.0.0.1:8080',actor:'a'});
  release(json(cap)); await connecting;
  assert.equal(f.client.getState().capabilities,null);
  assert.equal(f.client.getState().busy,false);
});

test('owner-mismatched execution cannot replace selected evidence', async () => {
  const f = fixture(url => json(url.endsWith('/capabilities') ? cap : url.endsWith('/executions') ? {owner:cap.owner,items:[],next_cursor:null} : {...execution,owner:'owner-b'}));
  await f.client.connect(); await f.client.execution('inspect',{execution_id:id});
  assert.equal(f.client.getState().execution,null);
  assert.match(f.client.getState().error,/another account/);
});

test('failed candidate dispatch retains the exact ID for explicit inspection without replay', async () => {
  const f = fixture((url,options) => options.method === 'POST' ? json({detail:'Fixture unavailable'},503) : json(url.endsWith('/capabilities') ? cap : {owner:cap.owner,items:[],next_cursor:null}));
  await f.client.connect();
  await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal});
  assert.equal(f.client.getState().executionId,id);
  assert.equal(f.client.getState().execution,null);
  assert.match(f.client.getState().error,/503/);
  assert.equal(f.calls.filter(call => call.options.method === 'POST').length,1);
});

test('history pagination is explicit, deduplicates IDs and rejects malformed cursors', async () => {
  const second = {...item,execution_id:'d'.repeat(32)};
  const f = fixture(url => json(url.endsWith('/capabilities') ? cap : url.includes('?cursor=')
    ? {owner:cap.owner,items:[item,second],next_cursor:null}
    : {owner:cap.owner,items:[item],next_cursor:id}));
  await f.client.connect(); assert.equal(f.client.getState().items.length,1);
  await f.client.refresh(true); assert.equal(f.client.getState().items.length,2);
  assert.equal(f.client.getState().nextCursor,null);
  const invalid = fixture(url => json(url.endsWith('/capabilities') ? cap : {owner:cap.owner,items:[item],next_cursor:'../other'}));
  await invalid.client.connect(); assert.match(invalid.client.getState().error,/retained coding record/);
  assert.equal(invalid.client.getState().items.length,0);
});

test('isolated remains default and blocked checks never silently fall back to local execution', async () => {
  const f = fixture((url,options) => json(url.endsWith('/capabilities') ? {...cap,trusted_local_available:true}
    : options.method === 'POST' ? execution : {owner:cap.owner,items:[],next_cursor:null}));
  await f.client.connect();
  await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal});
  const posted = f.calls.filter(call => call.options.method === 'POST');
  assert.equal(posted.length,1);
  assert.equal(JSON.parse(posted[0].options.body).execution_backend,'isolated');
  assert.equal(JSON.parse(posted[0].options.body).trusted_local_ack,false);
  assert.equal(f.client.getState().execution.state,'BLOCKED');
});

test('trusted local checks require current support and an acknowledgement that resets after dispatch', async () => {
  const f = fixture((url,options) => json(url.endsWith('/capabilities') ? {...cap,trusted_local_available:true}
    : options.method === 'POST' ? execution : {owner:cap.owner,items:[],next_cursor:null}));
  await f.client.connect(); f.client.selectExecutionBackend('trusted_host');
  await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal});
  assert.equal(f.calls.filter(call => call.options.method === 'POST').length,0);
  f.client.acknowledgeTrustedLocal(true);
  await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal});
  const body = JSON.parse(f.calls.find(call => call.options.method === 'POST').options.body);
  assert.equal(body.execution_backend,'trusted_host'); assert.equal(body.trusted_local_ack,true);
  assert.equal(f.client.getState().executionBackend,'isolated'); assert.equal(f.client.getState().trustedLocalAck,false);
  f.setContext({backendUrl:'http://127.0.0.1:8080',actor:'b'});
  assert.equal(f.client.getState().trustedLocalAck,false);
});

test('passing checks never autoapply; an explicit review token and explicit apply are required', async () => {
  const verified = {...execution,state:'VERIFIED',verification_status:'passed',execution_authorized:true,apply_authorized:true,can_apply:true};
  const f = fixture(url => json(url.endsWith('/capabilities') ? cap : url.endsWith('/executions') ? {owner:cap.owner,items:[],next_cursor:null}
    : url.endsWith('/review') ? {...verified,review_token:'reviewed-current-source'}
      : url.endsWith('/apply') ? {...verified,can_apply:false,application:{state:'APPLIED'}} : verified));
  await f.client.connect(); await f.client.execution('inspect',{execution_id:id});
  assert.equal(f.calls.filter(call => call.options.method === 'POST').length,0);
  await f.client.execution('apply');
  assert.equal(f.calls.filter(call => call.options.method === 'POST').length,0);
  await f.client.execution('review');
  assert.equal(f.client.getState().reviewToken,'reviewed-current-source');
  assert.equal(f.calls.filter(call => call.url.endsWith('/apply')).length,0);
  await f.client.execution('apply');
  assert.deepEqual(JSON.parse(f.calls.find(call => call.url.endsWith('/apply')).options.body),{review_token:'reviewed-current-source'});
  assert.equal(f.client.getState().execution.application.state,'APPLIED');
  assert.equal(f.client.getState().reviewToken,'');
});

function clock() {
  let next = 0; const timers = new Map();
  return {timers,schedule(callback,delay) {assert.equal(delay,2000);timers.set(++next,callback);return next;},unschedule(id) {timers.delete(id);},
    async tick() {const [id,callback] = timers.entries().next().value;timers.delete(id);await callback();}};
}

test('RUNNING polling performs bounded inspect GETs and never replays execution', async () => {
  const timer = clock(); const running = {...execution,state:'RUNNING',execution_authorized:true};
  const f = fixture((url,options) => json(url.endsWith('/capabilities') ? cap : options.method === 'POST' ? running
    : url.endsWith('/executions') ? {owner:cap.owner,items:[],next_cursor:null} : running),undefined,{schedule:timer.schedule,unschedule:timer.unschedule,pollLimit:2});
  await f.client.connect(); await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal});
  assert.equal(timer.timers.size,1);
  await timer.tick(); await timer.tick();
  assert.equal(timer.timers.size,0); assert.equal(f.client.getState().polling,false);
  assert.match(f.client.getState().error,/refresh stopped/);
  assert.equal(f.calls.filter(call => call.options.method === 'POST').length,1);
  assert.equal(f.calls.filter(call => call.url.endsWith(`/executions/${id}`)).length,2);
});

test('terminal results and account changes stop status timers', async () => {
  const timer = clock(); const running = {...execution,state:'RUNNING',execution_authorized:true};
  const f = fixture((url,options) => json(url.endsWith('/capabilities') ? cap : options.method === 'POST' ? running
    : url.endsWith('/executions') ? {owner:cap.owner,items:[],next_cursor:null} : {...execution,state:'FAILED',verification_status:'failed'}),undefined,{schedule:timer.schedule,unschedule:timer.unschedule});
  await f.client.connect(); await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal});
  await timer.tick(); assert.equal(timer.timers.size,0);
  assert.equal(f.client.getState().execution.state,'FAILED');
  await f.client.execution('create',{request_id:id,plan_id:plan,proposal_id:proposal}); assert.equal(timer.timers.size,1);
  f.setContext({backendUrl:'http://127.0.0.1:8080',actor:'b'}); assert.equal(timer.timers.size,0);
  assert.equal(f.client.getState().execution,null);
});
