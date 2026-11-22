import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
import {parseFDXDocument,updateFDXBlockText} from '../../frontend/utils/fdxDocumentFormat.js';
import {cloneRichFDX,richFDXProjection,prepareRichFDXWrite,confirmedRichEdit,importRichFDX,richBlockHistory,recordRichBlockHistory,restoreRichBlockHistory} from '../../frontend/src/utils/richFdxDraft.js';
import {createScreenplayDraftCoordinator} from '../../frontend/src/utils/screenplayDraftCoordinator.js';
import {validateScreenplayExport,screenplayExportFilename} from '../../frontend/src/utils/screenplayHandoff.js';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url)),babel=require('@babel/parser'),traverse=require('@babel/traverse').default;
globalThis.DOMParser=require('@xmldom/xmldom').DOMParser;globalThis.XMLSerializer=require('@xmldom/xmldom').XMLSerializer;
const xml='<FinalDraft><TitlePage><Content><Paragraph Type="Title"><Text>Title *literal*</Text></Paragraph><Paragraph Type="Author"><Text>Author</Text></Paragraph></Content></TitlePage><Content><Paragraph Type="Action" StartsNewPage="Yes"><Text Style="Bold" RevisionID="5">aa😀</Text><Text Style="Italic">aa &amp; *literal*</Text><ScriptNote><Paragraph><Text>NOTE</Text></Paragraph></ScriptNote></Paragraph></Content><Unknown Keep="Yes"/></FinalDraft>';
const doc=()=>({...parseFDXDocument(xml),source_sha256:'a'.repeat(64),document_sha256:'a'.repeat(64),applied_operation_ids:[]});
async function declaration(file,name){const source=await readFile(`frontend/src/components/${file}.jsx`,'utf8');let result;traverse(babel.parse(source,{sourceType:'module',plugins:['jsx']}),{VariableDeclarator(path){if(path.node.id.name===name)result=source.slice(path.parent.start,path.parent.end);},FunctionDeclaration(path){if(path.node.id.name===name)result=source.slice(path.node.start,path.node.end);}});assert.ok(result,name);return result;}
test('precise Unicode edit deletes the selected repeated styled characters without moving style/revision metadata',()=>{
 const original=doc(),before=original.blocks[0],text='aa😀a! & *literal*',range=confirmedRichEdit(before.text,text,5,6,'insertText');
 assert.deepEqual(range,{start:4,end:5,text:'!'});const changed=updateFDXBlockText(before,text,range);
 assert.equal(changed.runs[0].text,'aa😀');assert.equal(changed.runs[0].attributes.RevisionID,'5');assert.equal(changed.runs[1].attributes.Style,'Italic');
 const current={...original,blocks:[changed]};const prepared=prepareRichFDXWrite(current,original);
 assert.equal(richFDXProjection(prepared),richFDXProjection(current));assert.equal(prepared.blocks[0].notes[0].text,'NOTE');assert.equal(prepared.title_page[1].text,'Author');
 assert.throws(()=>confirmedRichEdit(before.text,'unrelated',0,0,'insertText'),/not be verified/);
});
test('queued actual coordinator saves rebase only acknowledged operation IDs and type-only changes remain dirty',async()=>{
 const original=doc();delete original.original_xml;let server=cloneRichFDX(original),calls=[];
 const coordinator=createScreenplayDraftCoordinator({write:async payload=>{
   calls.push(cloneRichFDX(payload));assert.equal(payload.expected_revision,server.document_sha256);
   const next=cloneRichFDX(payload.fdx_document);next.document_sha256=String(calls.length+1).repeat(64);next.applied_operation_ids=[...server.applied_operation_ids,...next.blocks.flatMap(b=>b.edit_operations.map(op=>op.id))];
   next.blocks.forEach(block=>{block.edit_operations=[];block.attributes.Type=block.type;});server=next;
   return {project:'Fixture',revision:next.document_sha256,content:richFDXProjection(next),fdx_document:next};
 }});
 coordinator.load('Fixture',richFDXProjection(original),original.document_sha256,undefined,original);
 const first=cloneRichFDX(original);
 // Use actual Unicode positions, independent of UTF16 code-unit count.
 const size=Array.from(original.blocks[0].text).length;
 first.blocks[0]=updateFDXBlockText(original.blocks[0],original.blocks[0].text+' first',{start:size,end:size,text:' first'});
 const second=cloneRichFDX(first);second.blocks[0]=updateFDXBlockText(second.blocks[0],second.blocks[0].text+' second',{start:size+6,end:size+6,text:' second'});
 await Promise.all([coordinator.save('Fixture',richFDXProjection(first),undefined,first),coordinator.save('Fixture',richFDXProjection(second),undefined,second)]);
 assert.equal(calls.length,2);assert.equal(calls[1].fdx_document.blocks[0].edit_operations.length,1);assert.equal(server.blocks[0].text,second.blocks[0].text);
 const typed=cloneRichFDX(server);typed.blocks[0].type='General';assert.equal(coordinator.isDirty('Fixture',richFDXProjection(typed),typed),true);
 await coordinator.save('Fixture',richFDXProjection(typed),undefined,typed);assert.equal(calls.at(-1).fdx_document.blocks[0].type,'General');
 assert.equal(coordinator.isDirty('Fixture',richFDXProjection(server),server),false);
});
test('actual rich editor range handler preserves literal punctuation and metadata; unverified edits remain separate draft data',async()=>{
 const blocks=doc().blocks;let changed,retained,pending={};const context={blocks,baselineBlocks:blocks,revision:'a'.repeat(64),histories:{current:{entries:{}}},pendingDrafts:{current:{}},onQualified(){},richBlockHistory,recordRichBlockHistory,restoreRichBlockHistory,updateFDXBlockText,confirmedRichEdit,selections:{current:{'fdx-0':{from:2,to:2,inputType:'insertText'}}},setPending:fn=>pending=fn(pending),onChange:value=>changed=value,onUnqualified:(value,message)=>retained={value,message},Error};
 runInNewContext(await declaration('RichFDXEditor','edit')+'globalThis.editText=edit;',context);
 context.editText({currentTarget:{value:'aaX😀aa & *literal*'}},blocks[0]);assert.equal(changed[0].text,'aaX😀aa & *literal*');assert.equal(changed[0].notes[0].text,'NOTE');assert.equal(changed[0].runs[0].attributes.RevisionID,'5');
 context.selections.current={};context.editText({currentTarget:{value:'retain unsupported structural edit'}},blocks[0]);assert.match(retained.message,/retained/);assert.equal(retained.value[0].text,'retain unsupported structural edit');assert.equal(blocks[0].text,'aa😀aa & *literal*');
 const styling={};runInNewContext(await declaration('RichFDXEditor','richRunStyle')+'globalThis.style=richRunStyle;',styling);
 assert.equal(styling.style({attributes:{Style:'Bold+Italic',Color:'javascript:bad',Font:'<script>'}}).fontStyle,'italic');assert.equal(Object.hasOwn(styling.style({attributes:{}}),'color'),false);
});
test('raw FDX import preserves byte SHA, authenticated multipart boundary and owner-derived server route',async()=>{
 const file=new File([new Uint8Array([239,187,191]),xml],'Original.fdx',{type:'application/xml'});let sent;
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer()))).map(v=>v.toString(16).padStart(2,'0')).join('');
 const imported=await importRichFDX({backendUrl:'http://fixture',project:'Fixture',file,headers:()=>({'Content-Type':'application/json',Authorization:'Bearer fixture'}),fetchImpl:async(url,options)=>{sent={url,options};return {ok:true,json:async()=>({status:'success',project:'Fixture',revision:digest,source:{sha256:digest},fdx_document:{source_sha256:digest}})};}});
 assert.equal(imported.revision,digest);assert.equal(sent.options.headers.has('Content-Type'),false);assert.equal(sent.options.headers.get('Authorization'),'Bearer fixture');assert.equal(sent.options.body.get('file'),file);assert.equal(sent.options.body.get('source_sha256'),digest);assert.equal(sent.options.body.has('owner'),false);
});
test('actual Screenwriting FDX import dispatch uses raw-file API and retains a newer unrelated draft',async()=>{
 const source=await readFile('frontend/src/components/ScreenwritingTab.jsx','utf8');let branch;
 traverse(babel.parse(source,{sourceType:'module',plugins:['jsx']}),{IfStatement(path){if(source.slice(path.node.test.start,path.node.test.end)==="fileName.endsWith('.fdx')")branch=source.slice(path.node.start,path.node.end);}});assert.ok(branch);
 for(const newer of [false,true]){
  const calls=[],problems=[];let retained=true;
  const file=new File([xml],'original.fdx');const context={fileName:'original.fdx',file,projName:'New rich copy',isCurrent:()=>true,transitionRef:{current:false},setIsLoading(){},flushDraftForTransition:async()=>({project:'Unrelated',content:'keep me'}),importRichFDX:async args=>{calls.push(['import',args.file,args.project]);if(newer)retained=false;return {project:'New rich copy'};},BACKEND_URL:'fixture',chatAuthHeaders:async()=>({}),draftStillCurrent:()=>retained,setSaveProblem:p=>problems.push(p),loadProjects:async()=>calls.push(['projects']),loadScreenplay:async p=>calls.push(['load',p]),e:{target:{value:'original.fdx'}}};
  await runInNewContext(`(async()=>{${branch}})()`,context);assert.equal(calls[0][1],file);assert.equal(calls[0][2],'New rich copy');
  assert.equal(calls.some(call=>call[0]==='load'),!newer);if(newer)assert.match(problems[0].message,/newer draft remains open/);
 }
});
test('actual rich load bypasses Fountain normalization and a clean read/save makes no write',async()=>{
 const original=doc();delete original.original_xml;const content=richFDXProjection(original);let visible='',ast=[],writes=0;
 const coordinator=createScreenplayDraftCoordinator({write:async()=>{writes++;throw Error('unexpected write');}});
 const data={project:'Rich',content,revision:original.document_sha256,fdx_document:original,metadata:{source_fdx:{sha256:original.source_sha256}},initialized:false,workflow_revision:0,active_branch:'main',pending_operation:null};
 const context={reorderInFlightRef:{current:false},screenplayLoadSequenceRef:{current:0},captureDraft:()=>null,flushDraftForTransition:async()=>null,sharedActiveDoc:'',currentProjectRef:{current:'Unrelated'},loadedProjectRef:{current:'Unrelated'},screenplayRef:{current:'original unrelated draft'},draftRevisionRef:{current:0},sharedContent:'',BACKEND_URL:'fixture',fetch:async()=>({ok:true,json:async()=>data}),validateScreenplayRead:()=>{},sourceScreenplayAST:()=>null,draftStillCurrent:()=>true,saveCoordinator:coordinator,manualReviewRef:{current:new Set()},titleHeaderRef:{current:''},richDocumentRef:{current:null},richAckEpochRef:{current:0},setRichEditorEpoch(){},cloneRichFDX,setRichWorkingDraft(){},astRef:{current:[]},fountainTitleHeader:()=>'',fountainToAST:()=>{throw Error('Rich source must not be normalized through Fountain');},setExportLayout(){},setExportReceipt(){},setIsInternalChange(){},setCurrentProject(){},setSaveProblem:e=>{if(e)throw Error(e.message);},setCharacters(){},setShowCharacterVault(){},setDraggedBeatIndex(){},setScreenplay:text=>visible=text,setAst:value=>ast=value,setLastSavedTime(){},setAutoSaveStatus(){},preserveDraft(){},refreshRecoveryDrafts(){},parseScreenplay:async()=>{},setCurrentBranch(){},setProjectMetadata(){},loadCharacters:async()=>{}};
 runInNewContext(await declaration('ScreenwritingTab','loadScreenplay')+'globalThis.load=loadScreenplay;',context);
 assert.equal(await context.load('Rich'),true);assert.equal(visible,content);assert.equal(ast[0].text,'aa😀aa & *literal*');assert.equal(ast[0].notes[0].text,'NOTE');
 await coordinator.save('Rich',visible,undefined,context.richDocumentRef.current);assert.equal(writes,0);
});
test('preserved rich FDX downloads require matching SHA and have separate original filenames',async()=>{
 const blob=new Blob([xml]),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))).map(v=>v.toString(16).padStart(2,'0')).join('');
 const headers=new Headers({'X-AI-BS-Profile':'fdx-preservation-v1','X-AI-BS-Layout':'original','X-AI-BS-Renderer':'fdx-dom-patch-v1','X-AI-BS-Artifact-SHA256':digest});
 const receipt=await validateScreenplayExport(blob,{format:'fdx',layout:'original',headers});assert.equal(receipt.output_sha256,digest);
 headers.set('X-AI-BS-Artifact-SHA256','0'.repeat(64));await assert.rejects(validateScreenplayExport(blob,{format:'fdx',layout:'original',headers}),/digest/);
 assert.equal(screenplayExportFilename('Fixture','fdx','original'),'Fixture.original-import.fdx');
});
