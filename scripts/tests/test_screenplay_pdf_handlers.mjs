import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
import {createScreenplayDraftCoordinator} from '../../frontend/src/utils/screenplayDraftCoordinator.js';
import {fountainToAST,fountainTitleHeader} from '../../frontend/utils/FountainAdapter.js';
import {screenplayWorkflowIntent,isPdfAttachment,selectPdfSource,validateScreenplayRead,sourceScreenplayAST,validateScreenplayExport,screenplayExportFilename} from '../../frontend/src/utils/screenplayHandoff.js';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {parse}=require('@babel/parser');const traverse=require('@babel/traverse').default;
async function sourceFile(file){
 const source=await readFile(new URL(`../../frontend/src/components/${file}.jsx`,import.meta.url),'utf8');
 const nodes=[];traverse(parse(source,{sourceType:'module',plugins:['jsx']}),{enter(p){nodes.push(p.node);}});
 const code=node=>source.slice(node.start,node.end);
 const declaration=name=>{const node=nodes.find(node=>node.type==='VariableDeclarator'&&node.id.name===name);assert.ok(node,name);return `const ${name}=${code(node.init)};`;};
 return {source,nodes,code,declaration};
}
const chat=await sourceFile('ChatTab'),writer=await sourceFile('ScreenwritingTab');
const sha='a'.repeat(64),revision='b'.repeat(64),id='c'.repeat(32);
const file={name:'Fixture.pdf',ext:'.pdf',type:'application/pdf',source_id:id,source_sha256:sha,page_count:86,source_layout_available:true,parsing_status:'complete',indexing_status:'lexical_chunks_indexed',retrieval_status:'source_passage_readback_verified',rag_receipt:{derived_source_sha256:'d'.repeat(64),chunk_count:3,retrieval_hits:2,search_type:'lexical_scan',model_context_expanded:false},content:'PRIVATE PDF TEXT /backend restart'};
const imported={project:'Fixture_aaaaaaaaaaaa',revision,handoff:{project:'Fixture_aaaaaaaaaaaa',revision,source_sha256:sha}};
const pdfBranch=chat.nodes.find(node=>node.type==='IfStatement'&&chat.code(node.test).startsWith('screenplayIntent &&'));
assert.ok(pdfBranch);
async function runChat({fail=false,newerDraft=false,plan=false,unsupported=false}={}){
 let draft='/screenplay convert FDX and export PDF',attachments=[unsupported?{...file,source_layout_available:false}:file,{name:'unrelated.txt',content:'keep'}],messages=[],calls=[];
 const context={rawText:draft,attachments,activeTools:{plan_and_review:plan},screenplayIntent:screenplayWorkflowIntent(draft),
   isPdfAttachment,selectPdfSource,BACKEND_URL:'fixture',crypto:{randomUUID:()=>id},conversationMemory:{isCurrent:()=>true},
   chatAuthHeaders:async()=>({Authorization:'fixture'}),setIsLoading:()=>{},errorMessage:e=>e.message,
   setFooterInput:fn=>{draft=fn(draft);},setAttachments:fn=>{attachments=fn(attachments);},setChatMessages:fn=>{messages=fn(messages);},
   importPdfScreenplay:async options=>{calls.push(['import',options.file.source_id]);if(newerDraft)draft='newer unrelated draft';if(fail)throw new Error('Source is unavailable for this account');return imported;},
   fetchScreenplayExport:async options=>{calls.push(['export',options.format,options.revision]);return new Blob(['fixture']);},
   downloadScreenplayBlob:(_,name)=>calls.push(['download',name]),navigateToScreenplay:value=>calls.push(['navigate',value])};
 await runInNewContext(`(async()=>{${chat.code(pdfBranch)};throw new Error('Generic model dispatch reached');})()`,context);
 return {draft,attachments,messages,calls};
}
test('actual chat workflow imports/exports/opens source IDs and never sends the PDF to a model',async()=>{
 const result=await runChat();assert.equal(result.draft,'');assert.deepEqual(result.attachments.map(file=>file.name),['unrelated.txt']);
 assert.deepEqual(result.calls.filter(call=>call[0]==='export').map(call=>call.slice(1)),[['fdx',revision],['pdf',revision]]);
 assert.equal(result.calls.at(-1)[0],'navigate');assert.doesNotMatch(JSON.stringify(result.messages),/PRIVATE PDF TEXT|backend restart/);
 assert.match(result.messages.at(-1).content,/No model call/);
});
test('actual chat failure/plan mode retain source attachment and input without falling through',async()=>{
 for(const options of [{fail:true},{plan:true}]){
  const result=await runChat(options);assert.match(result.draft,/screenplay/);assert.equal(result.attachments[0],file);
  assert.equal(result.calls.filter(call=>['export','navigate'].includes(call[0])).length,0);
 }
 const newer=await runChat({newerDraft:true});assert.equal(newer.draft,'newer unrelated draft');
});
test('actual unsupported-layout chat stops before import or navigation and retains attachment/draft',async()=>{
 const result=await runChat({unsupported:true});assert.equal(result.calls.length,0);
 assert.equal(result.attachments.length,2);assert.match(result.draft,/screenplay/);
 assert.match(result.messages.at(-1).content,/Preserved-layout screenplay conversion is unavailable/);
});
test('actual command catalog exposes real workflows and automatic palette does not take focus',()=>{
 const context={};runInNewContext(chat.declaration('SLASH_COMMANDS')+'globalThis.catalog=SLASH_COMMANDS;',context);
 for(const command of ['/rag','/backend','/screenplay','/build','/conclude-grill'])assert.ok(context.catalog.some(row=>row.cmd===command),command);
 const searchInput=chat.nodes.find(node=>node.type==='JSXOpeningElement'&&node.name.name==='input'&&node.attributes.some(attr=>attr.type==='JSXAttribute'&&attr.name.name==='value'&&attr.value?.expression?.name==='commandSearchQuery'));
 assert.ok(searchInput);assert.equal(searchInput.attributes.some(attr=>attr.name?.name==='autoFocus'),false);
 let query='',draft='';const change={setFooterInput:value=>draft=value,setShowCommandsDropdown(){},setCommandSearchQuery:value=>query=value,showCommandsDropdown:false};
 runInNewContext(chat.declaration('handleInputChange')+"handleInputChange({target:{value:'/rag search literal source'}});",change);
 assert.equal(draft,'/rag search literal source');assert.equal(query,'rag');
});
function writerContext({mismatch=false,dirty=false}={}){
 const oldProject='Existing project',oldText='UNSAVED unrelated draft';let currentProject=oldProject,screenplay=oldText,ast=[],loaded=0,writes=0,problems=[];
 const coordinator=createScreenplayDraftCoordinator({write:async()=>{writes++;throw new Error('Unexpected write');}});
 const content='Title: Original\nAuthor: Writer\n\nExact preserved body.\n\n===\n\nSecond page.';
 const data={project:imported.project,revision,content,metadata:{source_pdf:{sha256:mismatch?'e'.repeat(64):sha,page_count:3}},source_layout_preserved:true,
  body_ast:[{id:'first',type:'Action',text:'Exact preserved body.',sourcePage:2,startsNewPage:false},{id:'second',type:'Action',text:'Second page.',sourcePage:3,startsNewPage:true}]};
 const context={targetProj:imported.project,reorderInFlightRef:{current:false},screenplayLoadSequenceRef:{current:0},
  captureDraft:()=>null,flushDraftForTransition:async()=>{if(dirty)throw new Error('Existing draft save failed; retained.');return null;},
  sharedActiveDoc:'',currentProjectRef:{current:oldProject},loadedProjectRef:{current:oldProject},screenplayRef:{current:oldText},draftRevisionRef:{current:0},sharedContent:'',
  BACKEND_URL:'fixture',fetch:async()=>({ok:true,json:async()=>data}),validateScreenplayRead,sourceScreenplayAST,
  draftStillCurrent:()=>true,saveCoordinator:{load:(...args)=>{loaded++;coordinator.load(...args);}},manualReviewRef:{current:new Set()},
  titleHeaderRef:{current:''},richDocumentRef:{current:null},richAckEpochRef:{current:0},setRichEditorEpoch(){},cloneRichFDX:value=>value?JSON.parse(JSON.stringify(value)):null,setRichWorkingDraft(){},astRef:{current:[]},fountainTitleHeader,fountainToAST,setExportLayout(){},setExportReceipt(){},setIsInternalChange(){},
  setCurrentProject:value=>currentProject=value,setSaveProblem:value=>problems.push(value),setCharacters(){},setShowCharacterVault(){},setDraggedBeatIndex(){},
  setScreenplay:value=>screenplay=value,setAst:value=>ast=value,setLastSavedTime(){},setAutoSaveStatus(){},preserveDraft(){},refreshRecoveryDrafts(){},parseScreenplay:async()=>{},setCurrentBranch(){},setProjectMetadata(){},loadCharacters:async()=>{}};
 return {context,coordinator,data,read:()=>({currentProject,screenplay,ast,loaded,writes,problems})};
}
test('actual project load refuses wrong-source read and failed departure without replacing existing draft',async()=>{
 for(const options of [{mismatch:true},{dirty:true}]){
  const f=writerContext(options);runInNewContext(writer.declaration('loadScreenplay')+'globalThis.load=loadScreenplay;',f.context);
  assert.equal(await f.context.load(imported.project,{handoff:imported.handoff}),false);
  const state=f.read();assert.equal(state.currentProject,'Existing project');assert.equal(state.screenplay,'UNSAVED unrelated draft');assert.equal(state.loaded,0);
 }
});
test('actual clean source load retains canonical bytes and separate title/body AST without a save',async()=>{
 const f=writerContext();runInNewContext(writer.declaration('loadScreenplay')+'globalThis.load=loadScreenplay;',f.context);
 assert.equal(await f.context.load(imported.project,{handoff:imported.handoff}),true);
 const state=f.read();assert.equal(state.screenplay,f.data.content);assert.equal(state.ast.length,2);assert.doesNotMatch(state.ast[0].text,/Title:/);
 await f.coordinator.save(imported.project,state.screenplay);assert.equal(f.read().writes,0);
});
test('actual save/export handler retains the explicit profile/revision and distinct filenames through both FDX buttons',async()=>{
 const calls=[],downloads=[];let selectedLayout='source';
 const body=new Blob(['<FinalDraft/>']);const digest=Buffer.from(await crypto.subtle.digest('SHA-256',await body.arrayBuffer())).toString('hex');
 const context={currentProject:imported.project,loadedProjectRef:{current:imported.project},isLoading:false,
  captureDraft:()=>({project:imported.project,content:'exact canonical'}),autoSaveTimerRef:{current:null},clearTimeout(){},setIsLoading(){},
  adaptationMountedRef:{current:true},draftStillCurrent:()=>true,
  manualReviewRef:{current:new Set()},saveCapturedDraft:async()=>({revision,unchanged:true}),projectMetadata:{source_pdf:{sha256:sha}},exportLayout:'source',
  validateScreenplayExport,screenplayExportFilename,setExportReceipt(){},
  URL:class extends URL{static createObjectURL(){return 'blob:fixture';}static revokeObjectURL(){}},URLSearchParams,
  BACKEND_URL:'fixture',fetch:async url=>{calls.push(url);return {ok:true,headers:new Headers({'X-AI-BS-Layout':selectedLayout,'X-AI-BS-Profile':'us-spec-courier12-v1','X-AI-BS-Renderer':'fixture','X-AI-BS-Artifact-SHA256':digest}),blob:async()=>body};},
  document:{createElement:()=>({download:'',click(){downloads.push(this.download);},remove(){}}),body:{appendChild(){}}},setTimeout:()=>{},alert:message=>{throw new Error(message);}};
 runInNewContext(writer.declaration('downloadScreenplayExport')+writer.declaration('handleExportFDX')+writer.declaration('exportFDX')+'globalThis.top=handleExportFDX;globalThis.ribbon=exportFDX;',context);
 for(const layout of ['source','professional','reflow']){
  selectedLayout=layout;context.exportLayout=layout;await context.top();await context.ribbon();
 }
 assert.equal(calls.length,6);assert.equal(new Set(downloads).size,3);
 for(let index=0;index<calls.length;index++){
  const layout=['source','professional','reflow'][Math.floor(index/2)];
  assert.match(calls[index],/export\/fdx/);assert.match(calls[index],new RegExp(`layout=${layout}`));assert.match(calls[index],new RegExp(`expected_revision=${revision}`));
  assert.equal(downloads[index],screenplayExportFilename(imported.project,'fdx',layout));
 }
 const errors=[];context.draftStillCurrent=()=>false;context.alert=message=>errors.push(message);
 await context.top();assert.equal(downloads.length,6);assert.match(errors.at(-1),/draft.*changed during export/i);
});
test('actual profile selector offers archival/professional/legacy choices without changing the source default',()=>{
 const selector=writer.nodes.find(node=>node.type==='JSXElement'&&node.openingElement.name.name==='select'&&node.openingElement.attributes.some(attr=>attr.name?.name==='aria-label'&&attr.value?.value==='Screenplay export layout'));
 assert.ok(selector);for(const value of ['source','professional','reflow'])assert.ok(selector.children.some(node=>node.type==='JSXElement'&&node.openingElement.attributes.some(attr=>attr.name?.name==='value'&&attr.value?.value===value)),value);
 const state=writer.nodes.find(node=>node.type==='VariableDeclarator'&&node.id.type==='ArrayPattern'&&node.id.elements[0]?.name==='exportLayout');
 assert.equal(state?.init?.callee?.name,'useState');assert.equal(state?.init?.arguments[0]?.value,'source');
});
