import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const output=path.resolve('backups/fe_retrieval_20261114_v01'); fs.mkdirSync(output,{recursive:true});
const sources=Object.fromEntries(['fe-express/driverClient.js','utils/feExpressOfflineStore.js'].map(name=>['/'+name,fs.readFileSync('frontend/src/'+name,'utf8')]));
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[];
try {
  const page=await browser.newPage();
  await page.route('**/*',route=>route.fulfill({contentType:sources[new URL(route.request().url()).pathname]?'text/javascript':'text/html',body:sources[new URL(route.request().url()).pathname]||'<html>Retrieval fixture</html>'}));
  await page.goto('https://retrieval.invalid');
  await page.evaluate(async()=>{
    window.create=(await import('/fe-express/driverClient.js')).createDriverClient;
    window.LegacyStore=(await import('/utils/feExpressOfflineStore.js')).FEExpressOfflineStore;
    const nativeAdd=IDBObjectStore.prototype.add,nativePut=IDBObjectStore.prototype.put;
    IDBObjectStore.prototype.add=function(...args){if(window.failJournal&&this.name==='journal')throw new DOMException('Synthetic journal failure','QuotaExceededError');return nativeAdd.apply(this,args);};
    IDBObjectStore.prototype.put=function(...args){if(window.failConfirmation&&this.name==='commits')throw new DOMException('Synthetic confirmation interruption','QuotaExceededError');return nativePut.apply(this,args);};
    window.check=(value,message)=>{if(!value)throw new Error(message);};
    window.rejects=async action=>{let failed=false;try{await action();}catch{failed=true;}check(failed,'expected rejection');};
    window.record=(id='remote',revision=1,notes='server original')=>({load_id:id,revision,payload:{notes},updated_at:'2026-11-14T12:00:00Z',attachments:[]});
    window.make=async uid=>{
      const env={uid,online:true,remote:[record()],calls:[],binary:new Blob(['proof'],{type:'application/pdf'}),badHash:false,badType:false,badLength:false};
      env.auth={currentUser:{uid,getIdToken:async fresh=>{check(fresh,'token not fresh');return 'synthetic';}}};
      env.client=create({auth:env.auth,subscribeAuth:cb=>{env.notify=cb;return()=>{};},online:()=>env.online,fetchImpl:async(url,options)=>{
        env.calls.push({url,options}); if(env.pause&&url.endsWith('/loads'))await env.pause;
        check(options.redirect==='error'&&options.credentials==='omit','transport policy');
        if(url.endsWith('/identity'))return new Response(JSON.stringify({owner:'firebase:ai-bs-dashboard:'+uid,scope:'driver_work'}));
        if(url.endsWith('/loads'))return new Response(JSON.stringify({loads:env.remote}));
        if(options.method==='POST') { const body=JSON.parse(options.body); if(env.conflict)return new Response('{}',{status:409}); return new Response(JSON.stringify({load_id:body.load_id,revision:body.base_revision+1})); }
        return new Response(env.badHash?new Blob(['wrong']):env.binary,{headers:{'Content-Type':env.badType?'image/png':'application/pdf','Content-Length':String(env.badLength?100:env.binary.size)}});
      }});
      await env.client.open(); return env;
    };
    window.withEvidence=async env=>{const hash=await crypto.subtle.digest('SHA-256',await env.binary.arrayBuffer()); env.remote[0].attachments=[{attachment_id:'proof',size:env.binary.size,media_type:'application/pdf',sha256:Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('')}];};
  });
  const test=async(name,action)=>{await page.evaluate(action);results.push({name,status:'PASS'});};
  await test('fresh owner pull imports clean records while legacy consumer sees only five legitimate loads',async()=>{
    window.clean=await make('clean');const data=await clean.client.pull();check(data.loads.length===1&&data.loads[0].revision===1&&data.outbox.length===0,'remote import');check(data.loads[0].remote.reviewToken,'missing review');
    const e=await make('legacy-five');e.remote=Array.from({length:5},(_,n)=>record('load-'+n));await e.client.pull();
    const old=new LegacyStore({owner:'firebase:ai-bs-dashboard:legacy-five',scope:'driver_work',verified:true});const loads=await old.listLoads();check(loads.length===5&&loads.every(load=>load.payload&&load.id.startsWith('load-')),'legacy rows polluted with review metadata');await old.close();await e.client.close();
  });
  await test('missing remote rows never delete durable originals',async()=>{clean.remote=[];await clean.client.pull();check((await clean.client.list()).loads.length===1,'remote absence deleted local');});
  await test('pending local fields Blobs and exact operations survive remote snapshot merge',async()=>{window.pending=await make('pending');await pending.client.save({notes:'local original'},{loadId:'remote',attachments:[new Blob(['local'],{type:'image/png'})]});const before=await pending.client.list();await pending.client.pull();const after=await pending.client.list();check(after.loads[0].payload.notes==='local original'&&after.loads[0].remote.payload.notes==='server original','overwrite');check(JSON.stringify(after.outbox)===JSON.stringify(before.outbox)&&await after.attachments[0].blob.text()==='local','original altered');});
  await test('malformed remote catalogue fails atomically without partial imports',async()=>{const e=await make('malformed');e.remote=[record('valid'),{...record('invalid'),payload:{owner:'forbidden'}}];await rejects(()=>e.client.pull());check((await e.client.list()).loads.length===0,'partial merge');await e.client.close();});
  await test('verified evidence versions persist for offline reuse without outbox replay',async()=>{
    window.evidence=await make('evidence');await withEvidence(evidence);await evidence.client.pull();
    const blob=await evidence.client.downloadRemoteEvidence('remote','proof');check(await blob.blob.text()==='proof','bad bytes');
    evidence.binary=new Blob(['new proof version'],{type:'application/pdf'});await withEvidence(evidence);await evidence.client.pull();
    const [one,two]=await Promise.all([evidence.client.downloadRemoteEvidence('remote','proof'),evidence.client.downloadRemoteEvidence('remote','proof')]);
    check(one.id===two.id&&one.id!==blob.id,'version cache duplicate or stale');
    const versions=(await evidence.client.list()).attachments;check(versions.length===2&&await versions.find(item=>item.id===blob.id).blob.text()==='proof'&&await one.blob.text()==='new proof version','original evidence version lost');
    const before=evidence.calls.length;evidence.online=false;const cached=await evidence.client.downloadRemoteEvidence('remote','proof');check(cached.id===one.id&&evidence.calls.length===before,'cached evidence made request');check((await evidence.client.list()).outbox.length===0,'download replayed as upload');
  });
  await test('hash type and length mismatches retain prior records without caching bad bytes',async()=>{for(const failure of ['badHash','badType','badLength']){const e=await make(failure);await withEvidence(e);await e.client.pull();e[failure]=true;await rejects(()=>e.client.downloadRemoteEvidence('remote','proof'));check((await e.client.list()).attachments.length===0,'bad evidence cached');await e.client.close();}});
  await test('keep-local archives immutable originals and legacy save cannot erase the separate journal',async()=>{
    const before=await pending.client.list(),token=before.loads[0].remote.reviewToken;await pending.client.resolveConflict('remote',token,'keep-local');const after=await pending.client.list(),journal=after.loads[0].journal[0];check(journal.local.payload.notes==='local original'&&JSON.stringify(journal.outbox)===JSON.stringify(before.outbox),'original journal lost');check(after.outbox.find(op=>op.kind==='load').base_revision===1,'not rebased');check(after.loads[0].payload.notes==='local original','local choice lost');
    const old=new LegacyStore({owner:'firebase:ai-bs-dashboard:pending',scope:'driver_work',verified:true});await old.saveLoad({notes:'legacy edit after review'},{loadId:'remote'});await old.close();check((await pending.client.list()).loads[0].journal[0].local.payload.notes==='local original','legacy save erased journal');
  });
  await test('use-server retains local candidate and evidence as explicitly archived originals',async()=>{const e=await make('server-choice');await e.client.save({notes:'candidate'},{loadId:'remote',attachments:[new Blob(['keep'])]});await e.client.pull();const token=(await e.client.list()).loads[0].remote.reviewToken;await e.client.resolveConflict('remote',token,'use-server');const after=await e.client.list();check(after.loads[0].payload.notes==='server original'&&after.loads[0].journal[0].local.payload.notes==='candidate','choice/journal');check(after.outbox.length===0&&after.attachments[0].archived&&await after.attachments[0].blob.text()==='keep','evidence lost');await e.client.close();});
  await test('write-ahead failure preserves capture and interrupted copy confirmation reconciles without replay',async()=>{
    const e=await make('copy');await e.client.save({notes:'copy candidate'},{loadId:'remote',attachments:[new Blob(['copy'])]});await e.client.pull();const before=await e.client.list(),token=before.loads[0].remote.reviewToken;
    window.failJournal=true;await rejects(()=>e.client.resolveConflict('remote',token,'new-copy'));window.failJournal=false;
    const unchanged=await e.client.list();check(JSON.stringify(unchanged.outbox)===JSON.stringify(before.outbox)&&unchanged.loads.length===1&&unchanged.loads[0].journal.length===0,'journal failure mutated capture');
    window.failConfirmation=true;await rejects(()=>e.client.resolveConflict('remote',token,'new-copy'));window.failConfirmation=false;
    const interrupted=await e.client.list();check(interrupted.loads.length===2&&interrupted.loads.find(load=>load.id==='remote').journal[0].status==='confirmation pending','interruption not exposed');
    const [one,two]=await Promise.all([e.client.resolveConflict('remote',token,'new-copy'),e.client.resolveConflict('remote',token,'new-copy')]);check(one.copyId===two.copyId,'duplicate copy');const after=await e.client.list();check(after.loads.length===2&&after.loads.find(l=>l.id===one.copyId).revision===0,'copy missing');check(after.loads.find(l=>l.id==='remote').journal.length===1&&after.loads.find(l=>l.id==='remote').journal[0].status==='committed'&&after.attachments.length===2,'original lost or interrupted intent replayed');await e.client.close();
  });
  await test('changed local generation or fresh server snapshot rejects stale review',async()=>{const e=await make('stale');await e.client.save({notes:'candidate'},{loadId:'remote'});await e.client.pull();let token=(await e.client.list()).loads[0].remote.reviewToken;await e.client.save({notes:'new local'},{loadId:'remote'});await rejects(()=>e.client.resolveConflict('remote',token,'use-server'));await e.client.pull();token=(await e.client.list()).loads[0].remote.reviewToken;e.remote[0].revision=2;e.remote[0].payload.notes='new server';await rejects(()=>e.client.resolveConflict('remote',token,'keep-local'));const after=await e.client.list();check(after.loads[0].payload.notes==='new local'&&after.loads[0].journal.length===0,'stale review mutated data');await e.client.close();});
  await test('late account-switched pull cannot import or expose previous owner records',async()=>{const e=await make('late-pull');let resume;e.pause=new Promise(resolve=>{resume=resolve;});const work=e.client.pull();await new Promise(resolve=>setTimeout(resolve,20));e.auth.currentUser=null;e.notify(null);resume();await rejects(()=>work);check(e.client.getSnapshot().status==='locked','late pull remained active');});
  await test('offline cached review survives reopen while resolution remains online gated',async()=>{const before=await pending.client.list();await pending.client.close();const auth={currentUser:{uid:'pending',getIdToken:async()=>{throw new Error('unexpected offline token');}}};const reopened=create({auth,online:()=>false});await reopened.open();const data=await reopened.list();check(data.loads[0].journal.length===1&&data.loads[0].remote.reviewToken===before.loads[0].remote.reviewToken,'cached review lost');await rejects(()=>reopened.resolveConflict('remote',data.loads[0].remote.reviewToken,'use-server'));check((await reopened.list()).outbox.length===before.outbox.length,'offline resolution modified originals');await reopened.close();});
  assert.equal(results.length,12);fs.writeFileSync(path.join(output,'retrieval-smoke.json'),JSON.stringify({status:'PASS',checks:12,results},null,2));console.log(JSON.stringify({status:'PASS',checks:12,results},null,2));
}catch(error){fs.writeFileSync(path.join(output,'retrieval-failure.json'),JSON.stringify({status:'FAILED',results,error:error.stack},null,2));throw error;}finally{await browser.close();}
