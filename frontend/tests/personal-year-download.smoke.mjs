import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {build}=require('../node_modules/esbuild');
const {chromium}=require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve('.'),out=path.join(root,'backups/personal_phone_20261114_archive_v01');
fs.mkdirSync(out,{recursive:true});assert.ok(!fs.existsSync(path.join(out,'server-ready.json')));
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const sources=['frontend/src/personal-finance/PersonalFinancePortal.jsx','frontend/src/personal-finance/personalClient.js',
  'backend/modules/personal_year_archive.py','backend/modules/personal_ledger_export.py'];
const pin=()=>Object.fromEntries(sources.map(n=>[n,sha(fs.readFileSync(path.join(root,n)))]));
const before=pin();let browser,server;
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){const end=Date.now()+10000;while(Date.now()<end){if(await fn())return;await pause(60);}throw Error('Fixture readiness timeout');}
try{
  const stdout=fs.openSync(path.join(out,'server.stdout.log'),'wx'),stderr=fs.openSync(path.join(out,'server.stderr.log'),'wx');
  const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>/^(SYSTEMROOT|WINDIR|COMSPEC|PATH|PATHEXT|TEMP|TMP|USERPROFILE|USERNAME|USERDOMAIN|LOCALAPPDATA|APPDATA|PROGRAMDATA|HOMEDRIVE|HOMEPATH)$/i.test(key)));
  server=spawn(path.join(root,'runtime/recovery-20261110/Scripts/python.exe'),[path.join(root,'backend/tests/fixtures/personal_finance_api_server.py'),out],{cwd:root,env,windowsHide:true,stdio:['pipe',stdout,stderr]});fs.closeSync(stdout);fs.closeSync(stderr);
  await until(()=>fs.existsSync(path.join(out,'server-ready.json')));
  const port=JSON.parse(fs.readFileSync(path.join(out,'server-ready.json'))).port;
  const fixture=`export const auth={currentUser:{uid:'owner-a',email:'owner-a@example.test',emailVerified:true,getIdToken:async()=>'synthetic:owner-a'}};export function onAuthStateChanged(_a,fn){queueMicrotask(()=>fn(auth.currentUser));return()=>{};}export async function signOut(){}`;
  const bundle=await build({stdin:{contents:`import React from 'react';import{createRoot}from'react-dom/client';import Portal from'./src/personal-finance/PersonalFinancePortal.jsx';createRoot(document.getElementById('root')).render(<Portal/>);`,resolveDir:path.join(root,'frontend'),loader:'jsx'},bundle:true,write:false,format:'iife',metafile:true,plugins:[{name:'synthetic-auth-only',setup(b){b.onResolve({filter:/(^firebase\/auth$|firebase\.js$)/},()=>({path:'auth',namespace:'fixture'}));b.onResolve({filter:/PersonalSignIn\.jsx$/},()=>({path:'login',namespace:'fixture'}));b.onResolve({filter:/accessControl\.js$/},()=>({path:'allow',namespace:'fixture'}));b.onLoad({filter:/.*/,namespace:'fixture'},({path:name})=>({loader:'jsx',resolveDir:path.join(root,'frontend'),contents:name==='auth'?fixture:name==='allow'?`export const ADMIN_EMAILS=['owner-a@example.test'];export const ADMIN_UIDS=[];`:`import React from'react';export default function PersonalSignIn(){return <p>Fixture sign-in</p>;}`}));}}]});
  browser=await chromium.launch({channel:'chrome',headless:true});const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
  const api=`http://127.0.0.1:${port}`,headers={Authorization:'Bearer synthetic:owner-a','Idempotency-Key':'archive-payment'};
  const saved=await context.request.post(api+'/api/personal-finance/payments',{headers,data:{payment_date:'2026-11-14',week_start:'2026-11-02',amount:'5.67',payer:'Fixture payer',source:'Fixture transfer'}});assert.equal(saved.status(),201);const id=(await saved.json()).id;
  const evidence=Buffer.from('original fixture bytes\x00\xff','latin1');
  const uploaded=await context.request.post(api+`/api/personal-finance/payments/${id}/documents`,{headers:{...headers,'Idempotency-Key':'archive-original','X-Document-Name':'original.pdf','Content-Type':'application/pdf'},data:evidence});assert.equal(uploaded.status(),201);
  const expected=await context.request.get(api+'/api/personal-finance/exports/2026.zip',{headers});assert.equal(expected.status(),200);const expectedBytes=await expected.body();
  await context.route('**/*',async route=>{const request=route.request(),url=new URL(request.url());if(url.hostname==='ai-bs-dashboard.web.app')return route.fulfill({contentType:'text/html',body:`<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script>${bundle.outputFiles[0].text}</script></body></html>`});assert.equal(url.hostname,'api.brettstehouwer.live');const forward=Object.fromEntries(Object.entries(request.headers()).filter(([key])=>['authorization','origin','access-control-request-method','access-control-request-headers'].includes(key)));const response=await context.request.fetch(api+url.pathname+url.search,{method:request.method(),headers:forward});return route.fulfill({response});});
  const page=await context.newPage();await page.goto('https://ai-bs-dashboard.web.app/personal/');await page.getByText('Personal draft ready',{exact:true}).waitFor();await page.getByLabel('Year',{exact:true}).fill('2026');
  const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Download records and originals ZIP',exact:true}).click();const result=await downloading;const raw=fs.readFileSync(await result.path());
  assert.equal(result.suggestedFilename(),'personal-records-2026.zip');assert.deepEqual(raw,expectedBytes);assert.equal(raw.readUInt32LE(0),0x04034b50);assert.deepEqual(pin(),before);
  fs.writeFileSync(path.join(out,'downloaded-fixture.zip'),raw);
  fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({status:'PASS',checks:1,actualPhoneUI:true,actualOwnerAPI:true,downloadBytes:raw.length,sha256:sha(raw),sourcePins:before,actualBundleInputs:bundle.metafile.inputs,mockBoundary:'SDK verification and client sign-in only',privateRecordsAccessed:false,liveEnabled:false},null,2));
  console.log(JSON.stringify({status:'PASS',checks:1,downloadBytes:raw.length}));
}catch(error){fs.writeFileSync(path.join(out,'failed.json'),JSON.stringify({error:error.stack}));console.error(error.stack);process.exitCode=1;}
finally{await browser?.close();if(server&&server.exitCode===null){server.stdin.write('STOP\n');await new Promise(resolve=>server.once('exit',resolve));}fs.writeFileSync(path.join(out,'cleanup.json'),JSON.stringify({ownedBrowserClosed:true,serverExit:server?.exitCode,standingServicesModified:false}));}
