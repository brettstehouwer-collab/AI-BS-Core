const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.env.AIBS_AUDIT_SOURCE_ROOT || path.resolve(__dirname, '../..');
const parser = require(path.join(path.resolve(__dirname, '../..'), 'frontend/node_modules/@babel/parser'));
const relative = 'frontend/src/components/BroadcastStudio.jsx';
const source = fs.readFileSync(path.join(root, relative), 'utf8');
const tree = parser.parse(source, {sourceType:'module',plugins:['jsx']});
const all=[];
(function visit(n) { if (!n || typeof n !== 'object') return; if (n.type) all.push(n); for(const [k,v] of Object.entries(n)) { if(['loc','comments','tokens'].includes(k)) continue; if(Array.isArray(v)) v.forEach(visit); else visit(v); } })(tree.program);
const helpers = tree.program.body.filter(n=>n.type==='FunctionDeclaration').map(n=>source.slice(n.start,n.end)).join('\n');
function callback(name, context) {
  const n=all.find(n=>n.type==='VariableDeclarator'&&n.id.name===name);
  assert.ok(n, `production ${name} callback exists`);
  return vm.runInNewContext(`(function(){${helpers}; return (${source.slice(n.init.start,n.init.end)});})()`, context);
}
function setup(response, reject=false) {
  const writes={streaming:[],unknown:[],requiresStop:[],pending:[],messages:[]}; const calls=[];const timers=new Map();let timerId=0;
  const context={Error,JSON,AbortController,Number,Math,
    selectedGameSource:'Fixture capture',customProcessName:'',hardwareEncoder:'h264_nvenc',encoderPreset:'p1',canvasOrientation:'horizontal',
    videoResolution:'1920x1080',videoFramerate:'60',videoBitrate:'6000k',audioBitrate:'160k',recordingFormat:'mkv',endpoints:[],sources:[],
    streamRequestRef:{current:false},stopRequestedRef:{current:false},setIsStreaming:x=>writes.streaming.push(x),setStreamStateUnknown:x=>writes.unknown.push(x),
    setRequiresStreamStop:x=>writes.requiresStop.push(x),setIsStreamRequestPending:x=>writes.pending.push(x),setStatusMessage:x=>writes.messages.push(x),
    setTimeout:fn=>{timers.set(++timerId,fn);return timerId;},clearTimeout:id=>timers.delete(id),
    fetch:async(...args)=>{calls.push(args);if(reject)throw Error('fixture transport failure');return response;}
  };
  return {context,writes,calls,timers};
}
const response=(ok,status,payload)=>({ok,status,json:async()=>payload});
for(const [name,value,reject] of [
  ['HTTP503',response(false,503,{status:'streaming'}),false],
  ['HTTP200error',response(true,200,{status:'error'}),false],
  ['HTTP200empty',response(true,200,{}),false],
  ['network',null,true],
])test(`broadcast start ${name} cannot invent successful streaming`,async()=>{
  const s=setup(value,reject);await callback('startStream',s.context)();
  assert.ok(!s.writes.streaming.includes(true));assert.equal(s.writes.unknown.at(-1),true);
  assert.equal(s.writes.requiresStop.at(-1),true,'uncertain dispatch retains a stop action');
  assert.match(s.writes.messages.at(-1),/unverified|unknown|failed|rejected/i);
  assert.equal(s.timers.size,0,'deadline cleared');assert.equal(s.context.streamRequestRef.current,false);
});
test('broadcast start explicit daemon acknowledgement is distinct from ingest proof',async()=>{
  const s=setup(response(true,200,{status:'streaming'}));await callback('startStream',s.context)();
  assert.equal(s.writes.streaming.at(-1),true);assert.equal(s.writes.unknown.at(-1),false);
  assert.match(s.writes.messages.at(-1),/daemon/i);assert.match(s.writes.messages.at(-1),/unverified/i);assert.equal(s.timers.size,0);
});
test('broadcast duplicate starts are coalesced before awaiting transport',async()=>{
  const s=setup(response(true,200,{status:'streaming'}));let release;
  s.context.fetch=async(...args)=>{s.calls.push(args);return await new Promise(resolve=>{release=resolve;});};
  const start=callback('startStream',s.context);const first=start();const second=start();
  assert.equal(s.calls.length,1);release(response(true,200,{status:'streaming'}));await Promise.all([first,second]);
  assert.equal(s.context.streamRequestRef.current,false);assert.equal(s.timers.size,0);
});
for(const [name,value,reject] of [
  ['HTTP503',response(false,503,{status:'stopped'}),false],
  ['HTTP200error',response(true,200,{status:'error'}),false],
  ['network',null,true],
])test(`broadcast stop ${name} retains uncertainty and makes no archive claim`,async()=>{
  const s=setup(value,reject);await callback('stopStream',s.context)();
  assert.ok(!s.writes.streaming.includes(false));assert.equal(s.writes.unknown.at(-1),true);
  assert.equal(s.writes.requiresStop.at(-1),true);assert.doesNotMatch(s.writes.messages.join(' '),/archive saved|stream offline/i);
  assert.equal(s.timers.size,0);
});
test('broadcast stop explicit acknowledgement does not imply archive integrity',async()=>{
  const s=setup(response(true,200,{status:'stopped',message:'Stream stopped and archive saved'}));await callback('stopStream',s.context)();
  assert.equal(s.writes.streaming.at(-1),false);assert.equal(s.writes.unknown.at(-1),false);assert.equal(s.writes.requiresStop.at(-1),false);
  assert.match(s.writes.messages.at(-1),/archive.*unverified/i);assert.equal(s.timers.size,0);
});
test('panic stop releases browser tracks even when remote stop fails',async()=>{
  const s=setup(null,true);let localStops=0;
  s.context.stopStream=callback('stopStream',s.context);
  s.context.screenStream={getTracks:()=>[{stop(){localStops++;}}]};s.context.webcamStream={getTracks:()=>[{stop(){localStops++;}}]};
  s.context.setScreenStream=()=>{};s.context.setWebcamStream=()=>{};
  await callback('panicStop',s.context)();assert.equal(localStops,2);assert.ok(!s.writes.streaming.includes(false));assert.equal(s.writes.unknown.at(-1),true);
});
test('panic during pending start queues a remote stop after acknowledgement',async()=>{
  const s=setup();let release;let localStops=0;
  s.context.fetch=async(url,options)=>{s.calls.push([url,options]);if(s.calls.length===1)return await new Promise(resolve=>{release=resolve;});return response(true,200,{status:'stopped'});};
  s.context.stopStream=callback('stopStream',s.context);
  s.context.screenStream={getTracks:()=>[{stop(){localStops++;}}]};s.context.webcamStream=null;s.context.setScreenStream=()=>{};s.context.setWebcamStream=()=>{};
  const start=callback('startStream',s.context)();await callback('panicStop',s.context)();
  assert.equal(localStops,1);release(response(true,200,{status:'streaming'}));await start;
  assert.equal(s.calls.length,2);assert.match(s.calls[1][0],/\/stream\/stop$/);assert.equal(s.writes.streaming.at(-1),false);
});
test('default broadcast telemetry contains unavailable measurements',()=>{
  const n=all.find(n=>n.type==='VariableDeclarator'&&n.id.type==='ArrayPattern'&&n.id.elements[0]?.name==='telemetry');
  const state=vm.runInNewContext(`(function(){${helpers};return (${source.slice(n.init.arguments[0].start,n.init.arguments[0].end)});})()`,{Number,Math});
  const initial=typeof state==='function'?state():state;
  for(const key of ['fps','bitrate','speed','dropped','game_name'])assert.equal(initial[key],null,key);
});
test('broadcast metric normalization accepts measured zero and rejects forged metrics',()=>{
  const f=vm.runInNewContext(`(function(){${helpers};return normalizeBroadcastTelemetry;})()`,{Number,Math});
  const valid=f({fps:'0.0',bitrate:'0.0kbits/s',speed:'0.0x',dropped:'0',game_name:'Fixture'});
  assert.equal(valid.fps,'0.0');assert.equal(valid.dropped,'0');
  const invalid=f({fps:'NaN',bitrate:'<svg>',speed:'Infinityx',dropped:-1,game_name:{title:'not scalar'}});
  for(const key of ['fps','bitrate','speed','dropped','game_name'])assert.equal(invalid[key],null,key);
});
function telemetryFixture() {
  const marker=source.indexOf('// Connect to Broadcast Telemetry Daemon');
  const effect=all.find(n=>n.type==='CallExpression'&&n.callee.name==='useEffect'&&n.start>marker);
  assert.ok(effect);
  const writes=[];const games=[];const timers=new Map();const sockets=[];let timerId=0;
  class Socket {static OPEN=1;static CONNECTING=0;constructor(){this.readyState=1;sockets.push(this);}close(){this.readyState=3;this.onclose?.();}}
  const context={Error,Number,Math,JSON,WebSocket:Socket,autoDetectGame:true,
    setTelemetry:x=>writes.push(typeof x==='function'?x(writes.at(-1)):x),setStreamStateUnknown:()=>{},setDaemonConnected:()=>{},setStatusMessage:()=>{},
    setSelectedGameSource:x=>games.push(x),setTimeout:(fn,delay)=>{timers.set(++timerId,{fn,delay});return timerId;},clearTimeout:id=>timers.delete(id)};
  const run=vm.runInNewContext(`(function(){${helpers};return (${source.slice(effect.arguments[0].start,effect.arguments[0].end)});})()`,context);
  const cleanup=run();return {writes,games,timers,sockets,cleanup};
}
test('broadcast WebSocket measurements expire while socket remains open',()=>{
  const s=telemetryFixture();const socket=s.sockets[0];socket.onopen();
  socket.onmessage({data:JSON.stringify({fps:'30.0',bitrate:'6000kbits/s',dropped:'0',game_name:'Fixture'})});
  assert.equal(s.writes.at(-1).fps,'30.0');assert.deepEqual(s.games,['Fixture']);
  const freshness=[...s.timers.values()].find(x=>x.delay===6000);assert.ok(freshness);freshness.fn();
  assert.equal(s.writes.at(-1).fps,null);s.cleanup();assert.equal(s.timers.size,0);
});
test('broadcast WebSocket disconnect invalidates measurements and cleanup prevents late writes',()=>{
  const s=telemetryFixture();const socket=s.sockets[0];socket.onmessage({data:JSON.stringify({fps:'60.0'})});
  socket.onclose();assert.equal(s.writes.at(-1).fps,null);assert.equal([...s.timers.values()].filter(x=>x.delay===3000).length,1);
  s.cleanup();const before=s.writes.length;socket.onmessage({data:JSON.stringify({fps:'120.0'})});
  assert.equal(s.writes.length,before);assert.equal(s.timers.size,0);
});
test('broadcast malformed telemetry cannot change selected capture source',()=>{
  const s=telemetryFixture();const socket=s.sockets[0];
  socket.onmessage({data:JSON.stringify({fps:'NaN',game_name:{injected:true}})});
  assert.equal(s.writes.at(-1).fps,null);assert.equal(s.games.length,0);
  socket.onmessage({data:'not-json'});assert.equal(s.writes.at(-1).fps,null);s.cleanup();
});
test('synthetic audio meters and cohost acknowledgements are absent',()=>{
  assert.equal(/const jitter = \(Math\.random\(\) - 0\.5\) \* 15/.test(source),false);
  assert.equal(/Social Hub & AI Sidekick connected \(Port 8006\)\.|llama3\.2 Active|AI CO-HOST', text: 'Ready!/.test(source),false);
  assert.equal(/Meter unavailable|Not measured/i.test(source),true);
});
test('daemon start acknowledgement cannot label individual destinations as live ingest',()=>{
  assert.equal(/● LIVE INGEST|LIVE ON AIR/.test(source),false);
  assert.equal(/setStatusMessage\(prev => prev\.includes\('Recording'\)/.test(source),false,'recording hotkey must not invent a recorder');
});
test('all broadcast mirrors retain exact byte parity',()=>{
  for(const prefix of ['frontend/components','frontend/src/components/components','frontend/components/components'])
    assert.equal(fs.readFileSync(path.join(root,prefix,'BroadcastStudio.jsx'),'utf8'),source);
});
