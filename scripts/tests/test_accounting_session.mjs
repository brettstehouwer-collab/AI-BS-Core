import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createAccountingSession, decimalProductUSD } from '../../frontend/src/utils/accountingSession.js';

test('account change while token resolves never dispatches', async () => {
  let done;let owner='a';let calls=0;
  const session=createAccountingSession({uid:'a',currentUid:()=>owner,getHeaders:()=>new Promise(r=>done=r),fetchImpl:async()=>{calls++;}});
  const result=session.request('/entries');owner='b';done({Authorization:'Bearer fixture'});
  await assert.rejects(result);assert.equal(calls,0);session.dispose();
});
test('disposed or changed identity drops late response data', async () => {
  let finish;let owner='a';
  const session=createAccountingSession({uid:'a',currentUid:()=>owner,getHeaders:async()=>({Authorization:'Bearer fixture'}),
    fetchImpl:async()=>({ok:true,status:200,json:()=>new Promise(r=>finish=r)})});
  const promise=session.request('/entries');await new Promise(r=>setImmediate(r));owner='b';finish({entries:['private fixture']});
  await assert.rejects(promise);session.dispose();
});
test('all reads and mutations carry auth, no-store and bounded cancellation', async () => {
  let seen;
  const session=createAccountingSession({uid:'a',currentUid:()=> 'a',getHeaders:async()=>({Authorization:'Bearer fixture'}),
    fetchImpl:async(url,options)=>{seen={url,...options};return {ok:true,status:200,json:async()=>({status:'success'})};}});
  const response=await session.request('/entry',{method:'POST',body:JSON.stringify({amount:'0.10'})});
  assert.equal((await response.json()).status,'success');assert.equal(seen.headers.Authorization,'Bearer fixture');
  assert.equal(seen.cache,'no-store');assert.ok(seen.signal);assert.ok(seen.headers['Idempotency-Key']);session.dispose();
});
test('overlapping mutation is rejected and ambiguous retry retains idempotency identity', async () => {
  let finish;let seen=[];let attempt=0;
  const session=createAccountingSession({uid:'a',currentUid:()=> 'a',getHeaders:async()=>({Authorization:'Bearer fixture'}),
    fetchImpl:async(u,o)=>{seen.push(o.headers['Idempotency-Key']);if(attempt++===0)return new Promise(r=>finish=r);
      return {ok:true,status:200,json:async()=>({status:'success'})};}});
  const request=session.request('/entry',{method:'POST',body:'{"amount":"0.10"}'});
  await new Promise(r=>setImmediate(r));await assert.rejects(session.request('/entry',{method:'POST',body:'{}'}),/in progress/);
  finish({ok:false,status:503,json:async()=>({})});await assert.rejects(request);
  await session.request('/entry',{method:'POST',body:'{"amount":"0.10"}'});assert.equal(seen[0],seen[1]);session.dispose();
});
test('request timeout settles even when transport ignores abort', async () => {
  const session=createAccountingSession({uid:'a',currentUid:()=> 'a',getHeaders:async()=>({Authorization:'Bearer fixture'}),timeoutMs:10,
    fetchImpl:async()=>new Promise(()=>{})});
  await assert.rejects(session.request('/entries'),/timed out/);session.dispose();
});
test('timeout during token lookup never dispatches after token arrives', async () => {
  let finish; let calls=0;
  const session=createAccountingSession({uid:'a',currentUid:()=> 'a',timeoutMs:10,
    getHeaders:()=>new Promise(resolve=>finish=resolve),fetchImpl:async()=>{calls++;}});
  await assert.rejects(session.request('/entry',{method:'POST',body:'{}'}),/timed out/);
  finish({Authorization:'Bearer fixture'}); await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls,0);session.dispose();
});
test('manual USD calculation uses integer half-even rounding', () => {
  assert.equal(decimalProductUSD('0.1','0.2'),'0.02');
  assert.equal(decimalProductUSD('1','1.005'),'1.00');
  assert.equal(decimalProductUSD('1','1.015'),'1.02');
  assert.equal(decimalProductUSD('90071992547409.91','1'),'90071992547409.91');
  assert.equal(decimalProductUSD('NaN','1'),'');
});
