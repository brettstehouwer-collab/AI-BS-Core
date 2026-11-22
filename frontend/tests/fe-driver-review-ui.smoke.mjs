// Real React/client/IndexedDB; synthetic identity and API only. No live account.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { build } = require('../node_modules/esbuild');
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const output = path.resolve('backups/fe_review_ui_20261114_v01');
fs.mkdirSync(output,{recursive:true});
const fixture = `const listeners=new Set();const user=uid=>uid?{uid,email:'synthetic@fixture.invalid',emailVerified:true,getIdToken:async force=>{window.fixture.tokens.push(force);return 'synthetic:'+uid;}}:null;
export const auth={currentUser:user(localStorage.getItem('fixture-uid')),authStateReady:async()=>{}};
window.fixture={tokens:[],signin(uid){auth.currentUser=user(uid);if(uid)localStorage.setItem('fixture-uid',uid);else localStorage.removeItem('fixture-uid');for(const callback of [...listeners])callback(auth.currentUser);}};
export function onAuthStateChanged(_auth,callback){listeners.add(callback);queueMicrotask(()=>{if(listeners.has(callback))callback(auth.currentUser);});return()=>listeners.delete(callback);}
export async function signOut(){window.fixture.signin(null);}`;
const bundle=await build({stdin:{contents:`import React from 'react';import{createRoot}from'react-dom/client';import DriverPortal from './src/fe-express/DriverPortal.jsx';createRoot(document.getElementById('root')).render(<DriverPortal/>);`,resolveDir:path.resolve('frontend'),loader:'jsx'},bundle:true,write:false,format:'iife',plugins:[{name:'synthetic-auth-only',setup(builder){
  builder.onResolve({filter:/^firebase\/auth$|(^|\/)firebase\.js$/},()=>({path:'auth',namespace:'fixture'}));
  builder.onResolve({filter:/LoginModal\.jsx$/},()=>({path:'login',namespace:'fixture'}));
  builder.onResolve({filter:/accessControl\.js$/},()=>({path:'allowlist',namespace:'fixture'}));
  builder.onLoad({filter:/.*/,namespace:'fixture'},({path:name})=>({loader:'jsx',resolveDir:path.resolve('frontend'),contents:name==='auth'?fixture:name==='allowlist'?`export const ADMIN_EMAILS=['synthetic@fixture.invalid'];export const ADMIN_UIDS=[];`:`import React from 'react';export default function LoginModal(){return <p>Synthetic existing sign in</p>;}`}));
}}]});
const source=bundle.outputFiles[0].text, results=[], failures=[], requests=[];
const evidence=Buffer.from('original remote synthetic evidence'), hash=crypto.createHash('sha256').update(evidence).digest('hex');
const remote=new Map([['review-owner:load1',{load_id:'load1',revision:1,payload:{load_ref:'Server load',notes:'server original\n  spaces',dispatch_text:'raw server dispatch'},updated_at:'2026-11-14T10:00:00+00:00',attachments:[{attachment_id:'proof1',sha256:hash,size:evidence.length,media_type:'application/pdf'}]}]]);
let disconnected=false,badDownload=false,page;
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
  const context=await browser.newContext();
  await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(url.origin==='https://driver-review.invalid')return route.fulfill({contentType:url.pathname.endsWith('.js')?'text/javascript':'text/html',body:url.pathname.endsWith('.js')?source:'<!doctype html><div id="root"></div><script src="/fixture.js"></script>'});
    assert.equal(url.origin,'https://api.brettstehouwer.live');
    const headers={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'GET,POST,OPTIONS','access-control-expose-headers':'ETag,Content-Type,Content-Length'};
    if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});
    const uid=request.headers().authorization?.replace('Bearer synthetic:','');assert.ok(uid);
    requests.push({method:request.method(),path:url.pathname,authorization:request.headers().authorization});
    if(disconnected)return route.abort('internetdisconnected');
    let body,status=200;
    if(url.pathname.endsWith('/identity'))body={owner:'firebase:ai-bs-dashboard:'+uid,scope:'driver_work'};
    else if(url.pathname.endsWith('/loads'))body={loads:[...remote].filter(([key])=>key.startsWith(uid+':')).map(([,load])=>structuredClone(load))};
    else if(url.pathname.endsWith('/sync')){
      const operation=request.postDataJSON(),key=uid+':'+operation.load_id,old=remote.get(key);
      if(operation.base_revision!==(old?.revision||0)){status=409;body={detail:{message:'Revision conflict',current_revision:old?.revision||0}};}
      else{body={load_id:operation.load_id,revision:(old?.revision||0)+1,payload:operation.payload,updated_at:'2026-11-14T11:00:00+00:00',attachments:old?.attachments||[]};remote.set(key,body);}
    }else if(url.pathname.endsWith('/attachments/proof1'))return route.fulfill({status:200,headers:{...headers,ETag:'"'+hash+'"'},contentType:'application/pdf',body:badDownload?Buffer.from('corrupted synthetic evidence'):evidence});
    else throw Error('Unexpected fixture path '+url.pathname);
    return route.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(body)});
  });
  page=await context.newPage();page.setDefaultTimeout(8000);page.on('pageerror',error=>failures.push(error.message));
  const button=name=>page.getByRole('button',{name,exact:true});
  const click=async name=>{await button(name).click();if(['Sync now','Pull records for review','Keep local fields','Use server fields','Save local as new copy'].includes(name))await page.waitForFunction(()=>document.querySelector('main')?.getAttribute('aria-busy')!=='true');};
  const label=name=>name==='Saved loads'?page.locator('select'):page.locator('form label').filter({hasText:new RegExp('^'+name)}).locator('input,textarea').first();
  const text=value=>page.getByText(value,{exact:true}).waitFor();
  const raw=name=>page.getByLabel(name,{exact:true});
  const serverLoad=()=>remote.get('review-owner:load1');
  const waitRemote=async note=>{await page.waitForFunction(note=>document.querySelector('[aria-label="Server raw fields"]')?.textContent.includes(note),note);};
  const test=async(name,action)=>{try{await action();results.push({name,status:'PASS'});}catch(error){results.push({name,status:'FAILED',error:error.stack});throw error;}};
  await page.goto('https://driver-review.invalid');
  await test('signed-out review gates access and owner open pulls server records',async()=>{
    await text('Synthetic existing sign in');assert.equal(requests.length,0);
    await page.evaluate(()=>fixture.signin('review-owner'));
    await label('Saved loads').selectOption('load1');
    await raw('Server raw fields').waitFor();assert.ok(requests.some(r=>r.path.endsWith('/loads')));
  });
  await test('side-by-side raw originals preserve whitespace and evidence counts',async()=>{
    assert.ok((await raw('Server raw fields').textContent()).includes('server original\\n  spaces'));
    assert.equal(await page.getByRole('heading',{name:'Local original',exact:true}).count(),1);
    assert.equal(await page.getByRole('heading',{name:'Server snapshot',exact:true}).count(),1);
    await page.getByText('Revision 1 · 1 server evidence files',{exact:true}).waitFor();
  });
  await test('pull flushes pending form text and never replaces active draft',async()=>{
    await label('Notes').fill('local original\n  retained');await click('Pull records for review');
    assert.equal(await label('Notes').inputValue(),'local original\n  retained');
    assert.ok((await raw('Local raw fields').textContent()).includes('local original\\n  retained'));
    assert.ok((await raw('Server raw fields').textContent()).includes('server original'));
  });
  await test('409 conflict remains visible with both versions and retained local form',async()=>{
    serverLoad().revision=2;serverLoad().payload.notes='server changed';await click('Sync now');await text('Conflicts need review');
    await click('Pull records for review');await waitRemote('server changed');assert.equal(await label('Notes').inputValue(),'local original\n  retained');
  });
  await test('cached review survives offline reload while all resolutions are disabled',async()=>{
    disconnected=true;await page.evaluate(()=>window.dispatchEvent(new Event('offline')));await page.reload();
    await label('Saved loads').selectOption('load1');await raw('Server raw fields').waitFor();
    await page.evaluate(()=>window.dispatchEvent(new Event('offline')));
    assert.ok((await raw('Server raw fields').textContent()).includes('server changed'));
    for(const name of ['Keep local fields','Use server fields','Save local as new copy'])assert.equal(await button(name).isDisabled(),true);
    disconnected=false;await page.evaluate(()=>window.dispatchEvent(new Event('online')));await click('Pull records for review');
  });
  await test('stale server revision rejects resolution without changing local draft',async()=>{
    serverLoad().revision=3;serverLoad().payload.notes='server revision three';await click('Keep local fields');
    await page.getByRole('alert').waitFor();assert.equal(await label('Notes').inputValue(),'local original\n  retained');
    assert.equal(serverLoad().payload.notes,'server revision three');await click('Pull records for review');await waitRemote('server revision three');
  });
  await test('explicit keep-local archives journal and queues reviewed revision',async()=>{
    await click('Keep local fields');await page.getByText(/Retained review journal \(1\)/).waitFor();
    assert.equal(await label('Notes').inputValue(),'local original\n  retained');assert.equal(serverLoad().payload.notes,'server revision three');
    await click('Sync now');await page.waitForFunction(()=>document.querySelector('.status')?.textContent.includes('0 unsynced operations'));
    assert.equal(serverLoad().payload.notes,'local original\n  retained');
  });
  await test('explicit use-server retains previous local original in journal',async()=>{
    await label('Notes').fill('second local original');await click('Save locally now');
    serverLoad().revision++;serverLoad().payload.notes='server adopted explicitly';await click('Pull records for review');await waitRemote('server adopted explicitly');
    await click('Use server fields');await page.waitForFunction(()=>document.querySelector('textarea')!==null);
    await page.waitForFunction(()=>Array.from(document.querySelectorAll('label')).find(l=>l.firstChild?.textContent==='Notes')?.querySelector('textarea')?.value==='server adopted explicitly');
    await page.getByText(/Retained review journal \(2\)/).waitFor();
    assert.ok((await page.locator('.review details').textContent()).includes('second local original'));
  });
  await test('save-copy uses a separate ID and retains source and journal',async()=>{
    await label('Notes').fill('copy local original');await click('Save locally now');await click('Pull records for review');
    const previous=await label('Saved loads').inputValue();await click('Save local as new copy');
    await page.waitForFunction(previous=>document.querySelector('select')?.value!==previous,previous);
    assert.equal(await label('Notes').inputValue(),'copy local original');
    assert.ok(await page.locator('select option').count()>=3);assert.equal(serverLoad().payload.notes,'server adopted explicitly');
    await label('Saved loads').selectOption(previous);await raw('Server raw fields').waitFor();
  });
  await test('corrupt remote evidence fails hash admission and exposes no backend download link',async()=>{
    badDownload=true;await click('Download verified evidence proof1');await page.getByRole('alert').waitFor();
    assert.equal(await page.getByRole('link',{name:'Download original evidence',exact:true}).count(),0);
    assert.equal(await page.locator('a[href*="api.brettstehouwer.live"]').count(),0);badDownload=false;
  });
  await test('verified remote evidence becomes a local Blob download only',async()=>{
    await click('Download verified evidence proof1');const link=page.getByRole('link',{name:'Download original evidence',exact:true});await link.waitFor();
    assert.ok((await link.getAttribute('href')).startsWith('blob:'));
    assert.ok(requests.some(r=>r.path.endsWith('/attachments/proof1')&&r.authorization==='Bearer synthetic:review-owner'));
    assert.ok(await page.evaluate(()=>fixture.tokens.every(Boolean)));
  });
  await test('account change clears review snapshots raw text evidence and drafts',async()=>{
    await page.evaluate(()=>fixture.signin('second-owner'));await text('ready');
    await page.waitForFunction(()=>!document.querySelector('[aria-label="Server raw fields"]'));
    assert.equal(await label('Notes').count(),0);assert.equal(await page.getByRole('link',{name:'Download original evidence'}).count(),0);
    assert.equal(failures.length,0,failures.join('\n'));await click('Sign out');await text('Synthetic existing sign in');
  });
  assert.equal(results.length,12);
}catch(error){if(page){await page.screenshot({path:path.join(output,'failure.png')});fs.writeFileSync(path.join(output,'failure.html'),await page.content());}console.error(error.stack);process.exitCode=1;}
finally{await browser.close();const receipt={status:process.exitCode?'FAILED':'PASS',checks:results.length,results,failures,scope:'Synthetic composed UI with real IndexedDB; no live account or private payload'};fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt,null,2));}
