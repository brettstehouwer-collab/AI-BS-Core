import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const root = process.env.AIBS_SOURCE_ROOT || 'C:/AI-BS';
const require = createRequire(path.join(process.env.AIBS_DEPENDENCY_ROOT || root, 'frontend/package.json'));
const {parse} = require('@babel/parser');
function source(relative) { return fs.readFileSync(path.join(root,relative),'utf8'); }
function nodes(text) {
 const all=[]; const visit=n=>{if(!n || typeof n!=='object')return;if(n.type)all.push(n);for(const [k,v] of Object.entries(n)){if(['loc','tokens','comments'].includes(k))continue;if(Array.isArray(v))v.forEach(visit);else visit(v);}};
 visit(parse(text,{sourceType:'module',plugins:['jsx','typescript']})); return all;
}
function callback(relative,name,context) {
 const text=source(relative);const declaration=nodes(text).find(n=>n.type==='VariableDeclarator'&&n.id.name===name);
 assert.ok(declaration,`callback ${name} exists`);
 return Function(...Object.keys(context),`return (${text.slice(declaration.init.start,declaration.init.end)})`)(...Object.values(context));
}
const cluster='frontend/src/components/ClusterEngineDashboard.jsx';
for(const name of ['runTemporalWorkflow','runNatsBenchmark','testDragonflyCache','testGrpcHandshake','sweepZombieNodes']) {
 test(`cluster ${name} holds unsupported work`,()=>{
  const logs=[];let timers=0;
  callback(cluster,name,{appendLog:x=>logs.push(x),setActiveWorkflow:()=>{},setTimeout:fn=>{timers++;fn();}})();
  assert.equal(timers,0,'elapsed time cannot acknowledge system work');
  assert.match(logs.join(' '),/unavailable|held|not configured|not connected/i);
  assert.doesNotMatch(logs.join(' '),/Status: SUCCESS|100% HIT|verified clean|packets acknowledged/i);
 });
}
for(const name of ['handleTriggerInpaint','handleSelectSubject','handleTriggerOutpaint']) {
 test(`media ${name} retains editing inputs without invented artifacts`,()=>{
  const logs=[];let cleared=false;let timers=0;
  callback('frontend/src/components/MediaStudioTab.jsx',name,{
   addLog:(...x)=>logs.push(x.join(' ')),setInpaintMaskPoints:()=>{cleared=true;},setIsOutpainting:()=>{},
   outpaintPrompt:'draft',outpaintBounds:{left:10,right:10,top:0,bottom:0},setTimeout:fn=>{timers++;fn();}
  })();
  assert.equal(cleared,false,'failed/unavailable renderer must preserve mask');
  assert.equal(timers,0);assert.match(logs.join(' '),/unavailable|held|not configured|not connected/i);
 });
}
for(const response of [{type:'opaque',status:0,ok:false},{type:'basic',status:503,ok:false},{type:'basic',status:200,ok:true}]) {
 test(`broadcast probe does not infer health from HTTP ${response.status}`,async()=>{
  let result;let pending=0;
  await callback('BroadcastStudioApp/src/App.jsx','probeLocalhostServices',{
   setIsProbing:()=>{},localhostServices:[{url:'http://fixture.invalid/status'}],performance:{now:()=>0},
   AbortController,fetch:async()=>response,setTimeout:()=>{pending++;return 1;},clearTimeout:()=>{pending--;},
   setLocalhostServices:x=>{result=x;},setDevLogs:()=>{}
  })();
  assert.notEqual(result[0].status,'online','no authenticated health contract is established');assert.equal(pending,0);
 });
}
test('broadcast rejection clears its deadline',async()=>{
 let pending=0;let result;
 await callback('BroadcastStudioApp/src/App.jsx','probeLocalhostServices',{
  setIsProbing:()=>{},localhostServices:[{url:'http://fixture.invalid/status'}],performance:{now:()=>0},AbortController,
  fetch:async()=>{throw Error('fixture offline');},setTimeout:()=>{pending++;return 1;},clearTimeout:()=>{pending--;},
  setLocalhostServices:x=>{result=x;},setDevLogs:()=>{}
 })();
 assert.equal(pending,0);assert.notEqual(result[0].status,'online');
});
function mobileAction(number,context) {
 const text=source('mobile-app/App.tsx');const start=text.indexOf(`Action ${number}:`);assert.ok(start>=0);
 const attr=nodes(text).find(n=>n.type==='JSXAttribute'&&n.name.name==='onPress'&&n.start>start);
 const fn=attr.value.expression;
 return Function(...Object.keys(context),`return (${text.slice(fn.start,fn.end).replace(/: any/g,'')})`)(...Object.values(context));
}
for(const number of [2,4,5])test(`mobile action ${number} cannot invent provider or harvest results`,async()=>{
 const logs=[];let calls=0;let timers=0;
 await mobileAction(number,{setDeckActionStatus:x=>logs.push(x),fetch:async()=>{calls++;},setTimeout:fn=>{timers++;fn();}})();
 assert.equal(calls,0);assert.equal(timers,0);assert.match(logs.join(' '),/unavailable|held|not connected/i);
 assert.doesNotMatch(logs.join(' '),/100% Win Rate|Leads stored|Probe: Zero-Cost Governance Active/);
});
for(const ok of [false,true])test(`mobile flush ${ok?'acknowledgement':'HTTP failure'} does not invent headroom`,async()=>{
 const logs=[];
 await mobileAction(6,{activeUrl:'http://fixture.invalid',setDeckActionStatus:x=>logs.push(x),fetch:async()=>({ok,status:ok?200:503})})();
 assert.doesNotMatch(logs.at(-1),/24GB|Cache Cleared|purge sent/i);
 assert.match(logs.at(-1),ok?/acknowledged.*unverified/i:/failed|rejected|error/i);
});
for(const command of ['/auto-shorts','/create-cover','render a clip'])test(`media director ${command} remains editable held draft`,async()=>{
 const logs=[];let calls=0;let timers=0;let edits=0;
 await callback('frontend/src/components/MediaStudioTab.jsx','handleExecuteCopilot',{
  copilotCommand:command,addLog:(...x)=>logs.push(x.join(' ')),setIsExecutingCopilot:()=>{},setCopilotCommand:()=>{edits++;},
  setCropBox:()=>{edits++;},setSilenceGaps:()=>{edits++;},setStudioMode:()=>{},setSelectedLayerId:()=>{},
  activeBackend:'http://fixture.invalid',fetch:async()=>{calls++;return {json:async()=>({})};},setTimeout:fn=>{timers++;fn();}
 })();
 assert.equal(calls,0);assert.equal(timers,0);assert.equal(edits,0);assert.match(logs.join(' '),/held|unavailable/i);
});

for(const name of ['handleStripSilence','handleSnapToBeats'])test(`media ${name} cannot infer audio analysis from elapsed time`,()=>{
 let timers=0;let cleared=false;const logs=[];
 callback('frontend/src/components/MediaStudioTab.jsx',name,{addLog:(...x)=>logs.push(x.join(' ')),silenceGaps:[1],setSilenceGaps:()=>{cleared=true;},setTimeout:fn=>{timers++;fn();}})();
 assert.equal(timers,0);assert.equal(cleared,false);assert.match(logs.join(' '),/unavailable|held/i);
});
for(const name of ['handleFlushVram','handleTestBuffer'])test(`media ${name} rejects HTTP failure before claiming success`,async()=>{
 const logs=[];let polls=0;
 await callback('frontend/src/components/MediaStudioTab.jsx',name,{
  setIsFlushingVram:()=>{},setIsAllocatingBuffer:()=>{},activeBackend:'http://fixture.invalid',addLog:(...x)=>logs.push(x.join(' ')),
  fetch:async()=>({ok:false,status:503,json:async()=>({})}),fetchTelemetry:async()=>{polls++;}
 })();
 assert.match(logs.at(-1),/ERROR|failed|rejected/i);assert.equal(polls,0);
 assert.doesNotMatch(logs.join(' '),/successfully|mapped into DDR5/i);
});
for(const response of [{ok:false,status:503},{ok:true,json:async()=>({total_mb:24564,used_mb:0,free_mb:24564,used_percent:0})},{ok:true,json:async()=>({total_mb:24564,used_mb:'bad',free_mb:10,used_percent:90})}]) {
 test(`media telemetry validates ${response.status||'data'} without retaining seeded/stale values`,async()=>{
  let state={used_mb:999};
  await callback('frontend/src/components/MediaStudioTab.jsx','fetchTelemetry',{activeBackend:'http://fixture.invalid',fetch:async()=>response,setTelemetry:x=>{state=x;}})();
  if(response.ok&&((await response.json()).used_mb===0))assert.equal(state.used_mb,0);
  else assert.equal(state.used_mb,null);
 });
}
function renderComponent(relative,props={}) {
 const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');const {transformSync}=require('esbuild');
 const text=source(relative).replace(/^import .*;\r?\n/gm,'').replace('export default function','function');
 const name=relative.includes('Cluster')?'ClusterEngineDashboard':'MediaStudioTab';
 const compiled=transformSync(text,{loader:'jsx',jsx:'transform'}).code;
 const Component=Function('React','useState','useEffect','useRef','useAppStore',`${compiled}; return ${name};`)(React,React.useState,React.useEffect,React.useRef,()=>null);
 return renderToStaticMarkup(React.createElement(Component,props));
}
test('cluster SSR never shows seeded benchmark metrics or optimal state',()=>{
 const html=renderComponent(cluster);assert.match(html,/Unavailable|UNAVAILABLE/);
 assert.doesNotMatch(html,/124,500|99\.4%|CLUSTER STATE: OPTIMAL|14 Active|12 Streams/);
});
test('media SSR shows unavailable GPU measurements while preserving canvas and timeline editing workspace',()=>{
 const html=renderComponent('frontend/src/components/MediaStudioTab.jsx',{backendUrl:'http://fixture.invalid'});
 assert.match(html,/Telemetry unavailable/);assert.doesNotMatch(html,/Zero-Copy Acceleration|2\.6 \/ 24GB/);
 assert.match(html,/Canvas|canvas/);
});
import vm from 'node:vm';
function accessFixture(){const text=source('frontend/src/components/accessControl.js').replaceAll('export const ','const ');return Function(`${text};return {getUserTier,canAccessTab,USER_TIERS};`)();}
test('subscription visibility matches caller tier without enterprise or public-tier wildcard',()=>{
 const f=accessFixture();
 for(const user of [null,{}, {uid:'fixture',emailVerified:true,plan:'unknown'}])assert.equal(f.getUserTier(user).id,'free_demo');
 assert.equal(f.getUserTier(null,'ADMIN').id,'free_demo');
 assert.equal(f.getUserTier({uid:'fixture',emailVerified:true,plan:'screenwriting'}).id,'screenwriting');
 assert.equal(f.canAccessTab('screenwriting','digital_storefront'),false);
 assert.equal(f.canAccessTab('enterprise_all_access','terminal'),false);
 assert.equal(f.canAccessTab('unknown','dashboard'),false);
 assert.equal(f.canAccessTab('free_demo','dashboard'),true);
 assert.equal(f.canAccessTab('admin','terminal'),true);
});
function interceptorFixture(transport=null){
 let notify=()=>{};const calls=[];const admin={uid:'owner-a',email:'fixture-admin@example.test',emailVerified:true,getIdToken:async()=> 'fixture-token'};
 const auth={currentUser:admin};const location=new URL('https://dashboard.example.test/');
 const window={location,fetch:async(resource,config)=>{calls.push({resource,config});return transport ? transport(resource,config) : {ok:true};}};
 const text=source('frontend/main.jsx');const a=text.indexOf('const originalFetch = window.fetch;');const b=text.indexOf('ReactDOM.createRoot',a);
 const context={window,auth,ADMIN_EMAILS:[admin.email],ADMIN_UIDS:[],URL,Request,Headers,DOMException,navigator:{userAgent:'fixture'},onAuthStateChanged:(a,callback)=>{notify=callback;return ()=>{};}};
 vm.createContext(context);vm.runInContext(text.slice(a,b),context);
 return {window,auth,admin,calls,change:user=>{auth.currentUser=user;notify(user);}};
}
for(const url of ['https://api.brettstehouwer.live.attacker.test/api/read','https://evilbrettstehouwer.live/api/read','https://external.example/api/read?redirect=https://api.brettstehouwer.live','http://localhost.attacker.test:8080/api/read'])test(`interceptor never injects credentials into untrusted ${new URL(url).hostname}`,async()=>{
 const f=interceptorFixture();f.window.location=new URL('http://localhost:5173/');await f.window.fetch(url);
 assert.equal(new URL(String(f.calls[0].resource)).origin,new URL(url).origin);
 assert.equal(new Headers(f.calls[0].config?.headers).has('Authorization'),false);
});
test('interceptor rejects a previous account delayed token before dispatch',async()=>{
 const f=interceptorFixture();let finish;f.admin.getIdToken=()=>new Promise(resolve=>{finish=resolve;});const pending=f.window.fetch('https://api.brettstehouwer.live/api/read');
 f.change({...f.admin,uid:'owner-b'});finish('previous-token');await assert.rejects(pending,{name:'AbortError'});assert.equal(f.calls.length,0);
});
test('interceptor rejects ABA account generation changes during token lookup',async()=>{
 const f=interceptorFixture();let finish;f.window.location=new URL('https://dashboard.example/');
 // The original fetch is captured at installation; its response can remain pending independently.
 f.admin.getIdToken=()=>new Promise(resolve=>{finish=resolve;});const pending=f.window.fetch('https://api.brettstehouwer.live/api/read');
 f.change({...f.admin,uid:'owner-b'});f.change(f.admin);finish('old-token');await assert.rejects(pending,{name:'AbortError'});assert.equal(f.calls.length,0);
});
test('interceptor retains Request/init headers, signal and blocks credential redirects',async()=>{
 const f=interceptorFixture();const controller=new AbortController();const request=new Request('https://api.brettstehouwer.live/api/read',{method:'POST',headers:{'X-Fixture':'request'},body:'draft'});
 await f.window.fetch(request,{headers:{'X-Override':'init'},signal:controller.signal});const c=f.calls[0];
 assert.equal(c.resource,request);assert.equal(c.config.signal,controller.signal);assert.equal(c.config.headers.get('X-Fixture'),'request');assert.equal(c.config.headers.get('X-Override'),'init');assert.equal(c.config.headers.get('Authorization'),'Bearer fixture-token');assert.equal(c.config.redirect,'error');
 controller.abort();await assert.rejects(f.window.fetch(request,{signal:controller.signal}),{name:'AbortError'});assert.equal(f.calls.length,1);
});
const standaloneBase='apps/digital_storefront_mobile/src/';
function renderStandalone(relative,props={}) {
 const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');const {transformSync}=require('esbuild');
 let text=source(standaloneBase+relative).replace(/^import .*;\r?\n/gm,'');
 text=text.replace('export default function App','function App').replace(/^export default \w+;?\s*$/m,'');
 const name=relative==='App.jsx'?'App':path.basename(relative,'.jsx');const compiled=transformSync(text,{loader:'jsx',jsx:'transform'}).code;
 const child=({currentUser})=>React.createElement('span',null,currentUser?.email||'No verified actor');
 const imports=relative==='App.jsx'?{DigitalStorefrontTab:child,CryptoSwarmMobileController:child}:{};
 const Component=Function('React','useState','useEffect','useRef',...Object.keys(imports),`${compiled};return ${name};`)(React,React.useState,React.useEffect,React.useRef,...Object.values(imports));
 return renderToStaticMarkup(React.createElement(Component,props));
}
test('standalone shell does not fabricate an authenticated actor or production verification',()=>{
 const html=renderStandalone('App.jsx');assert.ok(!html.includes('Live Production'));assert.ok(!html.includes('brettstehouwer@gmail.com'));assert.ok(html.includes('No verified actor'));
});
test('standalone storefront has unavailable account state and no seeded lead subscriptions',()=>{
 const html=renderStandalone('components/DigitalStorefrontTab.jsx',{subView:'lead_tracker'});assert.ok(/unavailable/i.test(html));assert.ok(!/Active Trial|Subscribed/.test(html));
 const hub=renderStandalone('components/DigitalStorefrontTab.jsx');assert.ok(hub.includes('Credits unavailable'));
});
test('standalone crypto missing metrics remain unavailable and never imply an active bot',()=>{
 const html=renderStandalone('components/CryptoSwarmMobileController.jsx');assert.ok(!html.includes('Bot Active'));assert.ok(html.includes('Unavailable'));assert.ok(!html.includes('$0.00'));
 const fmt=callback(standaloneBase+'components/CryptoSwarmMobileController.jsx','fmt',{});assert.equal(fmt(null),'Unavailable');assert.equal(fmt(0),'0.00');assert.equal(fmt(''),'Unavailable');assert.equal(fmt(Infinity),'Unavailable');
});
for(const name of ['handleSaveParameters','handleForceSwap'])test(`standalone crypto ${name} keeps live trading held with zero dispatch`,async()=>{
 const logs=[];let calls=0;
 await callback(standaloneBase+'components/CryptoSwarmMobileController.jsx',name,{setParamStatus:x=>logs.push(x),setSwapMessage:x=>logs.push(x),setSavingParams:()=>{},setSwapping:()=>{},buyDipPct:1,takeProfitPct:2,tradeUsdAmount:3,fromSymbol:'BTC',toSymbol:'ETH',apiHost:'http://fixture.invalid',fetch:async()=>{calls++;return {ok:true,json:async()=>({status:'success'})};},fetchStatus:()=>{},setFromSymbol:()=>{},setToSymbol:()=>{}})({preventDefault(){}});
 assert.equal(calls,0);assert.match(logs.at(-1),/held|disabled/i);
});
test('standalone crypto failed read clears prior metrics and update timestamp',async()=>{
 let data={total_profit_usd:100},updated='previous';
 await callback(standaloneBase+'components/CryptoSwarmMobileController.jsx','fetchStatus',{setLoading:()=>{},requestOwned:async()=>{throw Error('fixture unavailable');},fetch:async()=>{throw Error('fixture unavailable');},apiHost:'http://fixture.invalid',setData:x=>{data=x;},setError:()=>{},setLastUpdated:x=>{updated=x;},console:{error(){}},setBuyDipPct:()=>{},setTakeProfitPct:()=>{},setTradeUsdAmount:()=>{}})();
 assert.equal(data,null);assert.equal(updated,null);
});
for(const name of ['handleGenerate','handleAddLead'])test(`standalone storefront ${name} holds external dispatch and retains draft`,async()=>{
 let calls=0;let edited=0;const logs=[];
 await callback(standaloneBase+'components/DigitalStorefrontTab.jsx',name,{setAccountNotice:x=>logs.push(x),prompt:'fixture',newLeadName:'draft',newLeadContact:'draft@example.test',setIsGenerating:()=>{},setGeneratedContent:()=>{edited++;},setCopied:()=>{},backendUrl:'http://fixture.invalid',contentType:'ad_copy',userEmail:'fixture@example.test',selectedModel:'fixture',setCredits:()=>{},setLeads:()=>{},leads:[],setNewLeadName:()=>{edited++;},setNewLeadContact:()=>{edited++;},fetch:async()=>{calls++;return {json:async()=>({status:'success'})};}})({preventDefault(){}});
 assert.equal(calls,0);assert.equal(edited,0);assert.match(logs.at(-1),/held|disabled/i);
});
test('interceptor discards an HTTP response after the originating account changes',async()=>{
 let finish;const f=interceptorFixture(()=>new Promise(resolve=>{finish=resolve;}));
 const pending=f.window.fetch('https://api.brettstehouwer.live/api/read');await new Promise(resolve=>setImmediate(resolve));assert.equal(f.calls.length,1);
 f.change({...f.admin,uid:'owner-b'});finish({ok:true,body:'old account'});await assert.rejects(pending,{name:'AbortError'});
});
test('interceptor never dispatches when token lookup fails or an abort happens during lookup',async()=>{
 const f=interceptorFixture();f.admin.getIdToken=async()=>{throw Error('fixture token unavailable');};await assert.rejects(f.window.fetch('https://api.brettstehouwer.live/api/read'));assert.equal(f.calls.length,0);
 const g=interceptorFixture();let finish;g.admin.getIdToken=()=>new Promise(resolve=>{finish=resolve;});const c=new AbortController();const pending=g.window.fetch('https://api.brettstehouwer.live/api/read',{signal:c.signal});c.abort();finish('fixture-token');await assert.rejects(pending,{name:'AbortError'});assert.equal(g.calls.length,0);
});
for(const component of ['DigitalStorefrontTab.jsx','CryptoSwarmMobileController.jsx']) {
 const relative=standaloneBase+'components/'+component;
 test(`standalone ${component} refuses anonymous reads and sends owned no-store token-bound reads`,async()=>{
  let calls=0;let sent;const ownerSessionRef={current:{user:null}};
  const owned=callback(relative,'requestOwned',{ownerSessionRef,URL,Headers,DOMException,fetch:async(url,options)=>{calls++;sent=options;return {ok:true,json:async()=>({credits:0})};}});
  await assert.rejects(owned('https://api.brettstehouwer.live/api/crypto/swarm-status'));assert.equal(calls,0);
  ownerSessionRef.current={user:{uid:'fixture',email:'fixture@example.test',emailVerified:true,getIdToken:async()=> 'fixture-only'}};
  assert.equal((await owned('https://api.brettstehouwer.live/api/crypto/swarm-status')).credits,0);assert.equal(sent.cache,'no-store');assert.equal(sent.redirect,'error');assert.equal(sent.headers.get('Authorization'),'Bearer fixture-only');
 });
 test(`standalone ${component} discards delayed token and response after account replacement`,async()=>{
  let finish;let calls=0;const ownerSessionRef={current:{user:{uid:'a',email:'a@example.test',emailVerified:true,getIdToken:()=>new Promise(resolve=>{finish=resolve;})}}};
  const owned=callback(relative,'requestOwned',{ownerSessionRef,URL,Headers,DOMException,fetch:async()=>{calls++;return {ok:true,json:async()=>({credits:0})};}});
  const pending=owned('https://api.brettstehouwer.live/api/crypto/swarm-status');ownerSessionRef.current={user:{uid:'b'}};finish('old-token');await assert.rejects(pending,{name:'AbortError'});assert.equal(calls,0);
  ownerSessionRef.current={user:{uid:'a',email:'a@example.test',emailVerified:true,getIdToken:async()=> 'fixture-only'}};
  let respond;const delayed=callback(relative,'requestOwned',{ownerSessionRef,URL,Headers,DOMException,fetch:()=>new Promise(resolve=>{respond=resolve;})});
  const responsePending=delayed('https://api.brettstehouwer.live/api/crypto/swarm-status');await new Promise(resolve=>setImmediate(resolve));ownerSessionRef.current={user:{uid:'b'}};respond({ok:true,json:async()=>({credits:999})});await assert.rejects(responsePending,{name:'AbortError'});
 });
}
test('subscription hints cannot promote an unverified actor or non-admin into admin presentation',()=>{
 const f=accessFixture();assert.equal(f.getUserTier({uid:'fixture',emailVerified:false,plan:'enterprise_all_access'}).id,'free_demo');assert.equal(f.getUserTier({uid:'fixture',emailVerified:true,plan:'admin'}).id,'free_demo');
});
for(const component of ['DigitalStorefrontTab.jsx','CryptoSwarmMobileController.jsx'])test(`standalone ${component} rejects token-bearing reads to untrusted origins`,async()=>{
 let calls=0;const ownerSessionRef={current:{user:{uid:'fixture',email:'fixture@example.test',emailVerified:true,getIdToken:async()=> 'fixture'}}};
 const owned=callback(standaloneBase+'components/'+component,'requestOwned',{ownerSessionRef,URL,Headers,DOMException,fetch:async()=>{calls++;return {ok:true,json:async()=>({})};}});
 await assert.rejects(owned('https://external.example/api/read'));assert.equal(calls,0);
});
