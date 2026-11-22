import test from 'node:test';
import assert from 'node:assert/strict';
import { screenplayWorkflowIntent,selectPdfSource,attachmentPromptContent,navigateToScreenplay,readScreenplayHandoff,validateScreenplayRead,importPdfScreenplay,fetchScreenplayExport } from '../../frontend/src/utils/screenplayHandoff.js';
const sha='a'.repeat(64), revision='b'.repeat(64), id='c'.repeat(32);
const file={name:'The Mafia.pdf',ext:'.pdf',source_id:id,source_sha256:sha,page_count:86,source_layout_available:true,parsing_status:'complete',indexing_status:'lexical_chunks_indexed',retrieval_status:'source_passage_readback_verified',rag_receipt:{derived_source_sha256:'d'.repeat(64),chunk_count:21,retrieval_hits:3,search_type:'lexical_scan',model_context_expanded:false},content:'PRIVATE SCRIPT TEXT /backend restart'};
const reply={status:'success',project:'The Mafia_aaaaaaaaaaaa_cccccccc',revision,source:{source_id:id,sha256:sha,page_count:86},source_layout_preserved:true};
const headers={'Authorization':'Bearer fixture','Content-Type':'application/json'};
const response=(body,status=200)=>({ok:status===200,status,json:async()=>body});
test('explicit user screenplay/export intent admits workflow without consulting PDF instructions',()=>{
  assert.deepEqual(screenplayWorkflowIntent('open the attached PDF in screenwriting, convert to FDX and export PDF'),{fdx:true,pdf:true});
  assert.deepEqual(screenplayWorkflowIntent('Open this PDF in the screen writing tool'),{fdx:false,pdf:false});
  assert.equal(screenplayWorkflowIntent('summarize this attachment'),null);
  assert.deepEqual(screenplayWorkflowIntent('/screenplay open'),{fdx:false,pdf:false});
  assert.doesNotMatch(attachmentPromptContent(file),/PRIVATE SCRIPT|backend restart/);
  assert.match(attachmentPromptContent(file),new RegExp(`context_${id}\\.txt`));
  assert.equal(attachmentPromptContent({name:'other.txt',content:'literal text'}),'literal text');
});
test('one fully verified source required; partial/legacy/multiple PDFs are retained',()=>{
  assert.equal(selectPdfSource([file]),file);
  for(const invalid of [{...file,source_id:''},{...file,indexing_status:'failed'},{...file,rag_receipt:{...file.rag_receipt,retrieval_hits:0}},{...file,rag_receipt:{...file.rag_receipt,retrieval_hits:undefined}},{...file,source_sha256:'fake'}])assert.throws(()=>selectPdfSource([invalid]));
  assert.throws(()=>selectPdfSource([file,file]),/one PDF/);assert.throws(()=>selectPdfSource([]),/Attach the PDF/);
});
test('generic indexed PDF remains referenceable but cannot falsely open a preserved-layout screenplay',()=>{
  const generic={...file,source_layout_available:false};
  assert.match(attachmentPromptContent(generic),new RegExp(`context_${id}\\.txt`));
  assert.throws(()=>selectPdfSource([generic]),/original PDF and indexed text were retained.*separate explicit choice/);
});
test('import transmits authenticated source IDs only and validates exact source/revision',async()=>{
  const calls=[];const value=await importPdfScreenplay({backendUrl:'http://fixture',file,headers,requestId:id,fetchImpl:async(url,options)=>{calls.push([url,options]);return response(reply);}});
  assert.equal(value.handoff.revision,revision);assert.equal(calls.length,1);
  const body=JSON.parse(calls[0][1].body);assert.deepEqual(Object.keys(body).sort(),['project_name','request_id','source_id','source_sha256']);
  assert.equal(calls[0][1].headers.Authorization,'Bearer fixture');assert.doesNotMatch(calls[0][1].body,/PRIVATE SCRIPT|owner|path|content/);
  await assert.rejects(importPdfScreenplay({backendUrl:'fixture',file,headers,requestId:id,fetchImpl:async()=>response({...reply,source:{...reply.source,sha256:'e'.repeat(64)}})}),/match/);
  await assert.rejects(importPdfScreenplay({backendUrl:'fixture',file,headers,requestId:id,fetchImpl:async()=>response({...reply,project:'Other saved project'})}),/match/);
});
test('cross-owner or stale import errors stop without retries or navigation',async()=>{
  let calls=0;await assert.rejects(importPdfScreenplay({backendUrl:'fixture',file,headers,requestId:id,fetchImpl:async()=>{calls++;return response({detail:'Source unavailable for this account'},403);}}),/account/);assert.equal(calls,1);
});
test('structured import/export error details keep their actual cause',async()=>{
  await assert.rejects(importPdfScreenplay({backendUrl:'fixture',file,headers,requestId:id,fetchImpl:async()=>response({detail:{message:'Canonical revision changed; use explicit reflow',project:reply.project}},409)}),/Canonical revision changed/);
  await assert.rejects(fetchScreenplayExport({backendUrl:'fixture',project:reply.project,revision,format:'pdf',headers,fetchImpl:async()=>response({detail:{message:'Source layout does not cover edited content'}},409)}),/does not cover edited/);
});
test('URL handoff uses App popstate contract and never reloads or includes manuscript/auth/path',()=>{
  let pushed;const events=[];const target={location:{href:'http://localhost:5173/?tab=ide'},history:{pushState:(_,__,url)=>{pushed=String(url);}},dispatchEvent:e=>events.push(e.type),PopStateEvent:class{constructor(type){this.type=type;}}};
  navigateToScreenplay({project:reply.project,revision,source_sha256:sha},target);
  const search=new URL(pushed).search;assert.deepEqual(readScreenplayHandoff(search),{project:reply.project,revision,source_sha256:sha});
  assert.deepEqual(events,['popstate']);assert.doesNotMatch(pushed,/PRIVATE|Bearer|owner|C:/);
  assert.throws(()=>navigateToScreenplay({project:'../other',revision,source_sha256:sha},target),/Invalid/);
});
test('read validation rejects a different project/source/revision before draft replacement',()=>{
  const expected={project:reply.project,revision,source_sha256:sha};const data={project:reply.project,revision,metadata:{source_pdf:{sha256:sha}}};
  validateScreenplayRead(data,expected);
  for(const bad of [{...data,project:'Other'},{...data,revision:sha},{...data,metadata:{source_pdf:{sha256:revision}}}])assert.throws(()=>validateScreenplayRead(bad,expected),/draft was retained/);
});
test('protected exports validate signatures and preserve source layout selection',async()=>{
  const calls=[];const blob=await fetchScreenplayExport({backendUrl:'fixture',project:reply.project,revision,format:'pdf',headers,fetchImpl:async(url,options)=>{calls.push([url,options]);return {ok:true,blob:async()=>new Blob(['%PDF-1.4 fixture'])};}});
  assert.equal(await blob.text(),'%PDF-1.4 fixture');assert.match(calls[0][0],/layout=source/);assert.equal(calls[0][1].headers.Authorization,'Bearer fixture');
  await assert.rejects(fetchScreenplayExport({backendUrl:'fixture',project:reply.project,revision,format:'fdx',headers,fetchImpl:async()=>({ok:true,blob:async()=>new Blob(['<html>Login</html>'])})}),/valid FDX/);
});
test('explicit professional export requires matching profile and output digest rather than an old API fallback',async()=>{
  const blob=new Blob(['<FinalDraft/>']);const digest=Buffer.from(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer())).toString('hex');
  const headersOut=new Headers({'X-AI-BS-Layout':'professional','X-AI-BS-Profile':'us-spec-courier12-v1','X-AI-BS-Renderer':'fixture-professional','X-AI-BS-Artifact-SHA256':digest});
  const calls=[];const result=await fetchScreenplayExport({backendUrl:'fixture',project:reply.project,revision,format:'fdx',layout:'professional',headers,
    fetchImpl:async(url)=>{calls.push(url);return {ok:true,headers:headersOut,blob:async()=>blob};}});
  assert.equal(await result.text(),'<FinalDraft/>');assert.match(calls[0],/layout=professional/);
  await assert.rejects(fetchScreenplayExport({backendUrl:'fixture',project:reply.project,revision,format:'fdx',layout:'professional',headers,
    fetchImpl:async()=>({ok:true,headers:new Headers(),blob:async()=>blob})}),/profile.*confirmed/i);
  headersOut.set('X-AI-BS-Artifact-SHA256','0'.repeat(64));
  await assert.rejects(fetchScreenplayExport({backendUrl:'fixture',project:reply.project,revision,format:'fdx',layout:'professional',headers,
    fetchImpl:async()=>({ok:true,headers:headersOut,blob:async()=>blob})}),/digest.*match/i);
});
