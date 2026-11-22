import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import { isLocalMaintenanceBuild, requestProjectBuild, waitForProjectMaintenance,
  pendingProjectMaintenance, projectMaintenanceReply } from '../../frontend/src/utils/projectMaintenance.js';

const id='1'.repeat(32);
const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
const { parse } = require('@babel/parser');
const traverse = require('@babel/traverse').default;
const headers={Authorization:'Bearer synthetic-fixture','Content-Type':'application/json'};
const response=(body,status=200)=>({ok:status>=200&&status<300,status,json:async()=>body});
const protocol=()=>response({local_maintenance_protocol:1});
function storage(){const values=new Map();return {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};}
function clock(){let time=0;return {now:()=>time,sleep:async n=>{time+=n;}};}

test('only default canonical local targets select maintenance',()=>{
  for(const target of ['AI-BS','frontend','backend','C:\\AI-BS','C:/AI-BS/frontend/'])assert.equal(isLocalMaintenanceBuild(target,null),true);
  assert.equal(isLocalMaintenanceBuild('my-app',null),false);
  assert.equal(isLocalMaintenanceBuild('frontend','npm run custom'),false);
});
test('actual ChatTab dispatch sends canonical /build targets past the earlier grill branch',async()=>{
  const source = await readFile(new URL('../../frontend/src/components/ChatTab.jsx', import.meta.url),'utf8');
  const tree = parse(source,{sourceType:'module',plugins:['jsx','typescript']});
  const branches=[];
  traverse(tree,{IfStatement(p){
    const body=source.slice(p.node.start,p.node.end);
    if(body.includes('/api/mission/grill-conclude') && body.startsWith("if (['/build'")) branches.push(p.node);
    else if(source.slice(p.node.test.start,p.node.test.end)==="command === '/build'") branches.push(p.node);
  }});
  assert.equal(branches.length,2,'Exercise both real dispatch branches in source order');
  for(const target of ['AI-BS','frontend','backend','C:\\AI-BS','C:/AI-BS/frontend/','fixture-grill-id','']){
    const calls=[];let messages=[];
    const context={command:'/build',rest:target,isLocalMaintenanceBuild,BACKEND_URL:'http://fixture',reqHeaders:headers,
      chatAuthHeaders:async()=>headers,projectMaintenanceReply,
      setIsLoading(){},setChatMessages:fn=>{messages=fn(messages);},errorMessage:e=>e.message,
      fetch:async(url)=>{calls.push(['grill',url]);return response({status:'not_found',message:'retained legacy grill path'});},
      requestProjectBuild:async options=>{calls.push(['maintenance',options.target]);return {result:{job_id:id,state:'succeeded',status:'success'}};}};
    await runInNewContext(`(async()=>{${branches.map(n=>source.slice(n.start,n.end)).join('\n')}})()`,context);
    assert.equal(calls.length,1,target);
    assert.equal(calls[0][0],target && isLocalMaintenanceBuild(target,null)?'maintenance':'grill',target);
  }
});
test('custom builds preserve their one-request contract',async()=>{
  const calls=[];const result=await requestProjectBuild({baseUrl:'http://fixture',target:'my-app',command:'custom build',headers,
    storage:storage(),fetchImpl:async(url,options)=>{calls.push([url,options]);return response({result:{status:'success',exit_code:0}});}});
  assert.equal(result.result.status,'success');assert.equal(calls.length,1);
  assert.deepEqual(JSON.parse(calls[0][1].body).payload,{build_command:'custom build',timeout_seconds:300});
});
test('server-resolved relative canonical targets follow acknowledged durable jobs',async()=>{
  let legacySubmissions=0;let statuses=0;
  const result=await requestProjectBuild({baseUrl:'http://fixture',target:'./frontend',headers,storage:storage(),...clock(),
    fetchImpl:async(url,options)=>{
      if(url.endsWith('/api/health'))return protocol();
      const body=JSON.parse(options.body);
      if(body.payload.maintenance_action==='status'){
        statuses+=1;return response({result:{job_id:id,state:'succeeded',status:'success'}});
      }
      legacySubmissions+=1;return response({result:{job_id:id,state:'queued',status:'queued'}});
    }});
  assert.equal(legacySubmissions,1);assert.equal(statuses,1);assert.equal(result.result.state,'succeeded');
});
test('default build polls authenticated status through API outage without replay',async()=>{
  const calls=[];let statusCalls=0;const store=storage();
  const result=await requestProjectBuild({baseUrl:'http://fixture',target:'frontend',headers:async()=>headers,makeId:()=>id,storage:store,...clock(),
    fetchImpl:async(url,options)=>{
      calls.push([url,options]);assert.equal(options.headers.Authorization,headers.Authorization);
      if(url.endsWith('/api/health'))return protocol();
      const body=JSON.parse(options.body);
      if(body.payload.maintenance_action==='start')return response({result:{job_id:id,state:'queued',status:'queued'}});
      statusCalls+=1;
      if(statusCalls===1)return response({result:{job_id:id,state:'restarting',status:'queued'}});
      if(statusCalls===2)throw new TypeError('synthetic network outage');
      return response({result:{job_id:id,state:'succeeded',status:'success',restart:{api_ready:true}}});
    }});
  assert.equal(result.result.state,'succeeded');assert.equal(pendingProjectMaintenance(store),null);
  assert.equal(calls.filter(([,o])=>o.body&&JSON.parse(o.body).payload.maintenance_action==='start').length,1);
  assert.equal(calls.filter(([url])=>url.endsWith('/api/health')).length,4);
});
test('lost submission ACK retries exactly the same durable identifier once',async()=>{
  const starts=[];let executeCount=0;const jobs=new Set();
  const result=await requestProjectBuild({baseUrl:'http://fixture',target:'AI-BS',headers,makeId:()=>id,storage:storage(),...clock(),
    fetchImpl:async(url,options)=>{
      if(url.endsWith('/api/health'))return protocol();
      const body=JSON.parse(options.body);
      if(body.payload.maintenance_action==='start'){
        const token=body.payload.maintenance_job_id;starts.push(token);
        if(!jobs.has(token)){jobs.add(token);executeCount+=1;throw new TypeError('ACK lost after durable admission');}
        return response({result:{job_id:id,state:'queued',status:'queued'}});
      }
      return response({result:{job_id:id,state:'succeeded',status:'success'}});
    }});
  assert.equal(result.result.state,'succeeded');assert.deepEqual(starts,[id,id]);assert.equal(executeCount,1);
});
test('old API protocol cannot receive a start or status build request',async()=>{
  const calls=[];const store=storage();
  await assert.rejects(requestProjectBuild({baseUrl:'http://fixture',target:'backend',headers,storage:store,
    fetchImpl:async(url,options)=>{calls.push([url,options]);return response({service:'old API'});}}),/not loaded/);
  assert.equal(calls.length,1);assert.equal(calls[0][1].method,undefined);assert.equal(pendingProjectMaintenance(store),null);
});
test('explicit backend restart uses the same durable checked workflow without a build replay',async()=>{
  const actions=[];
  const result=await requestProjectBuild({baseUrl:'fixture',target:'backend',action:'restart',headers,makeId:()=>id,storage:storage(),...clock(),
    fetchImpl:async(url,options)=>{
      if(url.endsWith('/api/health'))return protocol();
      const body=JSON.parse(options.body);actions.push(body.payload.maintenance_action);
      return response({result:{job_id:id,state:body.payload.maintenance_action==='status'?'succeeded':'queued',status:'queued'}});
    }});
  assert.equal(result.result.state,'succeeded');assert.deepEqual(actions,['restart','status']);
  await assert.rejects(requestProjectBuild({baseUrl:'fixture',target:'other-app',action:'restart',headers}),/canonical local project/);
});
test('resumed polling checks the protocol before sending status',async()=>{
  let posts=0;
  const result=await waitForProjectMaintenance({baseUrl:'http://fixture',headers,pending:{job_id:id,target:'backend'},storage:storage(),...clock(),outageLimitMs:1000,
    fetchImpl:async(url,options)=>{if(options.method==='POST')posts+=1;return response({service:'old API'});}});
  assert.equal(posts,0);assert.equal(result.result.status,'queued');assert.doesNotMatch(projectMaintenanceReply(result.result),/completed/);
});
test('failed job is a failure receipt, never exit0 or healthy',async()=>{
  const result=await waitForProjectMaintenance({baseUrl:'http://fixture',headers,pending:{job_id:id,target:'backend'},storage:storage(),...clock(),
    fetchImpl:async(url)=>url.endsWith('/api/health')?protocol():response({result:{job_id:id,state:'failed',status:'error',message:'retained failure'}})});
  const text=projectMaintenanceReply(result.result);
  assert.match(text,/Local update failed/);assert.match(text,/Not verified/);assert.doesNotMatch(text,/Exit Code.*0/);
});
test('poll deadline keeps durable pending state without forced reload',async()=>{
  const store=storage();let alive=true;
  const result=await waitForProjectMaintenance({baseUrl:'http://fixture',headers,pending:{job_id:id,target:'backend'},storage:store,...clock(),maxWaitMs:1000,
    fetchImpl:async(url)=>url.endsWith('/api/health')?protocol():response({result:{job_id:id,state:'checking',status:'queued'}})});
  assert.equal(result.result.state,'checking');assert.match(result.result.message,/worker keeps running/);
  assert.equal(alive,true);
});
test('leaving a view stops its polling without cancelling the server job',async()=>{
  let requests=0;const result=await waitForProjectMaintenance({baseUrl:'http://fixture',headers,pending:{job_id:id,target:'backend'},storage:storage(),active:()=>false,
    fetchImpl:async()=>{requests+=1;return protocol();}});
  assert.equal(requests,0);assert.equal(result.result.status,'queued');
});
test('authorization errors do not generate restart/build retries',async()=>{
  let posts=0;
  await assert.rejects(requestProjectBuild({baseUrl:'http://fixture',target:'frontend',headers,makeId:()=>id,storage:storage(),...clock(),
    fetchImpl:async(url)=>{
      if(url.endsWith('/api/health'))return protocol();posts+=1;return response({detail:'synthetic admission denial'},403);
    }}),/admission denial/);
  assert.equal(posts,1);
});
test('pending browser state contains identifiers, never auth headers',async()=>{
  const store=storage();await requestProjectBuild({baseUrl:'http://fixture',target:'frontend',headers,makeId:()=>id,storage:store,...clock(),maxWaitMs:0,
    fetchImpl:async(url)=>url.endsWith('/api/health')?protocol():response({result:{job_id:id,state:'queued',status:'queued'}})});
  assert.deepEqual(pendingProjectMaintenance(store),{job_id:id,target:'frontend'});
  assert.doesNotMatch(JSON.stringify(pendingProjectMaintenance(store)),/Bearer/);
});
