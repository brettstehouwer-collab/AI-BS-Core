// Actual drawer handlers, synthetic HTTP/auth and React hooks; no real service.
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'frontend/package.json'));const React=require('react');
const {transformSync}=require('esbuild');const {renderToStaticMarkup}=require('react-dom/server');
const source=await readFile(path.join(root,'frontend/src/components/ScriptAssistantDrawer.jsx'),'utf8');
const compiled=transformSync(source,{loader:'jsx',jsx:'automatic',format:'cjs'}).code;
const descendants=e=>React.isValidElement(e)?[e,...React.Children.toArray(e.props.children).flatMap(descendants)]:[];
const text=e=>typeof e==='string'||typeof e==='number'?String(e):React.isValidElement(e)?React.Children.toArray(e.props.children).map(text).join(''):'';
const response=(data,ok=true)=>({ok,status:ok?200:503,json:async()=>data});
const receipt={schema:'aibs.project_rag_snapshot.v2',complete:true,snapshot_sha256:'a'.repeat(64),source_chunks:3,sources:[{type:'rich_fdx',source_file:'rich_canonical_fdx',revision:'b'.repeat(64)}]};
function harness(replies){
  const slots=[];let cursor=0,dirty=true,tree,effects=[];const calls=[];const auth={currentUser:{uid:'ownerA'}};
  const props={isOpen:true,projectName:'Project A',backendUrl:'http://fixture',onInsertScript:()=>{}};
  const hooks={useState(initial){const n=cursor++;if(!slots[n])slots[n]={value:typeof initial==='function'?initial():initial};return[slots[n].value,v=>{const next=typeof v==='function'?v(slots[n].value):v;if(!Object.is(next,slots[n].value)){slots[n].value=next;dirty=true;}}];},
    useRef(value){const n=cursor++;return slots[n]||(slots[n]={current:value});},
    useEffect(callback,deps){const n=cursor++;if(!slots[n]||deps.some((v,i)=>!Object.is(v,slots[n].deps[i]))){const prior=slots[n];slots[n]={deps};effects.push(()=>{prior?.cleanup?.();slots[n].cleanup=callback();});}}};
  let authListener;
  const mockedRequire=name=>name==='react'?{...React,...hooks}:name==='/src/firebase.js'?{auth}:name==='firebase/auth'?{onAuthStateChanged:(_auth,callback)=>{authListener=callback;callback(auth.currentUser);return()=>{};}}:require(name);
  const module={exports:{}};
  new Function('require','module','exports','fetch',compiled+'\nmodule.exports.TestSession=ScriptAssistantSession;')(mockedRequire,module,module.exports,async(url,options={})=>{calls.push({url,options});return url.includes('/stats?')?response({status:'success',total_docs:3,receipt}):replies.shift();});
  function render(){let n=0;do{assert.ok(n++<15);dirty=false;cursor=0;effects=[];tree=module.exports.TestSession(props);effects.forEach(e=>e());}while(dirty);}
  function find(type,predicate=()=>true){const e=descendants(tree).find(e=>e.type===type&&predicate(e));assert.ok(e,`Missing ${type}`);return e;}
  async function flush(){for(let i=0;i<20;i++){await Promise.resolve();if(dirty)render();}}
  render();
  return{calls,flush,markup:()=>renderToStaticMarkup(tree),async sync(){find('button',e=>text(e).includes('Sync')).props.onClick();await flush();},
    async ask(value){find('textarea').props.onChange({target:{value}});render();find('button',e=>text(e)==='➤').props.onClick();await flush();},
    input:()=>find('textarea').props.value,insertCount:()=>descendants(tree).filter(e=>e.type==='button'&&text(e).includes('Insert')).length,
    unmount(){slots.forEach(slot=>slot.cleanup?.());},
    wrapperKeys(){slots.length=0;cursor=0;effects=[];const first=module.exports.default(props).key;effects.forEach(effect=>effect());
      auth.currentUser={uid:'ownerB'};authListener(auth.currentUser);cursor=0;effects=[];const second=module.exports.default(props).key;
      props.backendUrl='http://other';cursor=0;const third=module.exports.default(props).key;props.projectName='Project B';cursor=0;const fourth=module.exports.default(props).key;return[first,second,third,fourth];}};
}

test('sync displays verified chunks and revision instead of invented scene counts',async()=>{
  const h=harness([response({status:'success',indexed_docs:3,total_docs:3,receipt})]);await h.flush();await h.sync();
  assert.match(h.markup(),/3.*chunks/);assert.doesNotMatch(h.markup(),/undefined|isolated Vector DB/);
  assert.match(h.markup(),/bbbbbbbbbbbb/);
});
test('HTTP error detail remains visible, keeps the question and cannot be inserted',async()=>{
  const h=harness([response({detail:{message:'Fixture local model unavailable'}},false)]);await h.flush();await h.ask('My retained question');
  assert.match(h.markup(),/Fixture local model unavailable/);assert.equal(h.input(),'My retained question');assert.equal(h.insertCount(),0);
});
test('stale indexes and no-hit receipts are explanations rather than editable generated prose',async()=>{
  const h=harness([response({status:'stale_index',response:'Current source is not indexed.',sources:[],receipt:null})]);await h.flush();await h.ask('Where is this?');
  assert.match(h.markup(),/Current source is not indexed/);assert.equal(h.insertCount(),0);
});
test('qualified answers expose bounded-source coverage and only then permit manual insertion',async()=>{
  const h=harness([response({status:'success',response:'Grounded fixture.',generation_verified:true,receipt,
    sources:[{type:'rich_fdx',label:'rich_fdx chunk1',excerpt:'Bounded excerpt',source_revision:'b'.repeat(64),chunk_sha256:'c'.repeat(64)}],
    retrieval:{returned_passages:1,missing_source_indices:[1]}})]);await h.flush();await h.ask('What happened?');
  assert.equal(h.insertCount(),1);assert.match(h.markup(),/1.*source.*not covered|Missing.*1|Uncovered.*1/i);assert.match(h.markup(),/cccccccccccc/);
});
test('owner, backend and project switches create distinct mounted sessions',async()=>{
  const h=harness([]);await h.flush();assert.equal(new Set(h.wrapperKeys()).size,4);
});
test('unmount aborts pending requests instead of applying them to another project',async()=>{
  let resolve;const reply=new Promise(done=>resolve=done);const h=harness([reply]);await h.flush();
  await h.ask('Pending question');const call=h.calls.find(call=>call.url.endsWith('/chat'));
  assert.equal(call.options.signal.aborted,false);h.unmount();assert.equal(call.options.signal.aborted,true);
  resolve(response({status:'success',response:'Late old-project text.',generation_verified:true,receipt,sources:[{}]}));await h.flush();
  assert.doesNotMatch(h.markup(),/Late old-project text/);
});
