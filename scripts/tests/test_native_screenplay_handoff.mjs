import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {SourceTextModule,SyntheticModule,createContext,runInNewContext} from 'node:vm';
import {launchNativeScreenplay} from '../../frontend/src/utils/nativeScreenplayHandoff.js';

const handoff={project:'Bound',revision:'a'.repeat(64),source_sha256:'b'.repeat(64)};
const success={status:202,json:async()=>({status:'starting',project:'Bound'})};

test('launch submits one fixed endpoint request with only pinned saved scope',async()=>{
  const calls=[];
  const result=await launchNativeScreenplay({backendUrl:'http://127.0.0.1:8000',handoff,
    getFreshHeaders:async()=>({Authorization:'Bearer synthetic'}),fetchImpl:async(...args)=>{calls.push(args);return success;}});
  assert.equal(result.status,'starting');assert.equal(calls.length,1);
  assert.equal(calls[0][0],'http://127.0.0.1:8000/api/screenwriting/native/launch');
  assert.deepEqual(JSON.parse(calls[0][1].body),{project_name:'Bound',expected_revision:handoff.revision,expected_source_sha256:handoff.source_sha256});
  assert.ok(!calls[0][1].body.includes('synthetic'));
});

test('missing auth or context change during refresh makes no request',async()=>{
  let current=true,calls=0;
  for(const headers of [{}, {Authorization:'Bearer synthetic'}]){
    current=true;
    await assert.rejects(launchNativeScreenplay({backendUrl:'fixture',handoff,isCurrent:()=>current,
      getFreshHeaders:async()=>{if(headers.Authorization)current=false;return headers;},
      fetchImpl:async()=>{calls++;return success;}}));
  }
  assert.equal(calls,0);
});

test('refusals, malformed success and network loss are never replayed',async()=>{
  for(const response of [{status:503,json:async()=>({detail:'Native launch unavailable'})},
      {status:200,json:success.json},{status:202,json:async()=>({status:'ready',project:'Bound'})},
      {status:202,json:async()=>({status:'starting',project:'Other'})},null]){
    let calls=0;
    await assert.rejects(launchNativeScreenplay({backendUrl:'fixture',handoff,getFreshHeaders:async()=>({Authorization:'Bearer synthetic'}),
      fetchImpl:async()=>{calls++;if(!response)throw Error('offline');return response;}}));
    assert.equal(calls,1);
  }
});

test('invalid saved scope is rejected before auth or network',async()=>{
  let calls=0;
  await assert.rejects(launchNativeScreenplay({backendUrl:'fixture',handoff:{...handoff,revision:'stale'},
    getFreshHeaders:async()=>{calls++;return {};},fetchImpl:async()=>{calls++;return success;}}));
  assert.equal(calls,0);
});

async function authFixture(user){
  const context=createContext({Error});const state={currentUser:user};
  const firebase=new SyntheticModule(['auth'],function(){this.setExport('auth',state);},{context});
  const source=await readFile(new URL('../../frontend/src/utils/chatAuth.js',import.meta.url),'utf8');
  const auth=new SourceTextModule(source,{context});await auth.link(()=>firebase);await auth.evaluate();
  return {state,headers:auth.namespace.chatAuthHeaders};
}
test('actual auth helper refreshes token explicitly and fences account changes',async()=>{
  const seen=[];const user={uid:'owner',getIdToken:async value=>{seen.push(value);return 'synthetic';}};
  const f=await authFixture(user);
  assert.equal((await f.headers({},'owner',{forceRefresh:true})).Authorization,'Bearer synthetic');
  assert.deepEqual(seen,[true]);
  user.getIdToken=async()=>{f.state.currentUser={uid:'other'};return 'stale';};
  await assert.rejects(f.headers({},'owner',{forceRefresh:true}),/account changed/);
});

const source=await readFile(new URL('../../frontend/src/components/ScreenwritingTab.jsx',import.meta.url),'utf8');
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {parse}=require('@babel/parser');const tree=parse(source,{sourceType:'module',plugins:['jsx']});
function find(node){
  if(node?.type==='VariableDeclarator'&&node.id?.name==='handleOpenNativeScreenplay')return node.init;
  if(!node||typeof node!=='object')return null;
  for(const value of Object.values(node)){
    if(Array.isArray(value)){for(const child of value){const found=find(child);if(found)return found;}}
    else if(value&&typeof value==='object'){const found=find(value);if(found)return found;}
  }return null;
}
const handlerNode=find(tree);assert.ok(handlerNode);
function handlerFixture({changed=false,saveFails=false,refresh=null,handlerCode=source.slice(handlerNode.start,handlerNode.end)}={}){
  const calls=[],messages=[],transitionRef={current:false};
  const ctx={Error,transitionRef,isNativeLaunching:false,isLoading:false,BACKEND_URL:'fixture',projectMetadata:{source_pdf:{sha256:handoff.source_sha256}},
    loadedProjectRef:{current:'Bound'},backendUrlRef:{current:'fixture'},
    adaptationMountedRef:{current:true},screenplayLoadSequenceRef:{current:1},
    setIsNativeLaunching:value=>calls.push(['busy',value]),setNativeLaunchMessage:value=>messages.push(value),
    flushDraftForTransition:async()=>{calls.push(['save']);if(saveFails)throw Error('save conflict');return {project:'Bound'};},
    saveCoordinator:{snapshot:()=>({revision:handoff.revision})},draftStillCurrent:()=>!changed,
    chatAuthHeaders:async(...args)=>{calls.push(['auth',args]);if(refresh)await refresh;return {Authorization:'Bearer synthetic'};},
    launchNativeScreenplay:options=>launchNativeScreenplay({...options,fetchImpl:async()=>{calls.push(['launch',options.handoff]);return success;}})};
  return {calls,messages,transitionRef,ctx,run:runInNewContext(`(${handlerCode})`,ctx)};
}
test('actual UI handler saves then requests fresh auth and launch, retaining browser project',async()=>{
  const f=handlerFixture();await f.run();
  assert.deepEqual(f.calls.map(c=>c[0]),['busy','save','auth','launch','busy']);
  assert.equal(f.calls.find(c=>c[0]==='auth')[1][2].forceRefresh,true);
  assert.equal(f.transitionRef.current,false);assert.match(f.messages.at(-1),/browser project remains open/);
});
test('actual UI handler does not launch on save conflict or changed draft',async()=>{
  for(const options of [{saveFails:true},{changed:true}]){
    const f=handlerFixture(options);await f.run();
    assert.ok(!f.calls.some(c=>c[0]==='launch'));assert.equal(f.transitionRef.current,false);
  }
});

test('actual UI handler cancels launch if unmounted or another load starts during token refresh',async()=>{
  for(const departure of ['unmount','load']){
    let release;const refresh=new Promise(resolve=>{release=resolve;});
    const f=handlerFixture({refresh});const pending=f.run();
    while(!f.calls.some(c=>c[0]==='auth'))await new Promise(resolve=>setImmediate(resolve));
    const messageCount=f.messages.length;
    if(departure==='unmount')f.ctx.adaptationMountedRef.current=false;
    else f.ctx.screenplayLoadSequenceRef.current++;
    release();await pending;
    assert.ok(!f.calls.some(c=>c[0]==='launch'));
    assert.equal(f.messages.length,messageCount);
    assert.equal(f.transitionRef.current,false);
    if(departure==='unmount')assert.equal(f.calls.filter(c=>c[0]==='busy').length,1);
  }
});

for(const mirror of ['components','components/components','src/components','src/components/components']){
  const text=await readFile(new URL(`../../frontend/${mirror}/ScreenwritingTab.jsx`,import.meta.url),'utf8');
  const node=find(parse(text,{sourceType:'module',plugins:['jsx']}));assert.ok(node);
  const handlerCode=text.slice(node.start,node.end);
  test(`${mirror}: actual native handler launches the saved FDX source with fresh auth`,async()=>{
    const f=handlerFixture({handlerCode});
    f.ctx.projectMetadata={source_fdx:{sha256:handoff.source_sha256}};
    await f.run();
    assert.deepEqual(f.calls.map(c=>c[0]),['busy','save','auth','launch','busy']);
    assert.equal(f.calls.find(c=>c[0]==='launch')[1].source_sha256,handoff.source_sha256);
    assert.equal(f.ctx.loadedProjectRef.current,'Bound');
  });
  test(`${mirror}: missing, malformed or conflicting source metadata never launches`,async()=>{
    for(const metadata of [{},{source_fdx:{sha256:'bad'}},
        {source_pdf:{sha256:handoff.source_sha256},source_fdx:{sha256:handoff.source_sha256}}]){
      const f=handlerFixture({handlerCode});f.ctx.projectMetadata=metadata;await f.run();
      assert.ok(!f.calls.some(c=>c[0]==='launch'));
      assert.equal(f.transitionRef.current,false);
    }
  });
}
