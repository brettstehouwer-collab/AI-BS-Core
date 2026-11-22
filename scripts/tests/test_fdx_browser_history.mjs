import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
import * as draft from '../../frontend/src/utils/richFdxDraft.js';
import {parseFDXDocument,serializeFDXDocument,updateFDXBlockText} from '../../frontend/utils/fdxDocumentFormat.js';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));globalThis.DOMParser=require('@xmldom/xmldom').DOMParser;globalThis.XMLSerializer=require('@xmldom/xmldom').XMLSerializer;
const parser=require('@babel/parser'),traverse=require('@babel/traverse').default;
const xml='<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold" RevisionID="5">aa</Text><Text Style="Italic">aa</Text></Paragraph></Content></FinalDraft>';
async function declaration(name,file='RichFDXEditor'){const source=await readFile(`frontend/src/components/${file}.jsx`,'utf8');let text;traverse(parser.parse(source,{sourceType:'module',plugins:['jsx']}),{VariableDeclarator(p){if(p.node.id.name===name)text=source.slice(p.parent.start,p.parent.end);}});assert.ok(text);return text;}
test('actual browser controller exact first-character delete, undo, redo and later edit preserve original run identity',async()=>{
 const document=parseFDXDocument(xml),cache={entries:{}};let blocks=document.blocks,pending={},retained;
 const context={blocks,revision:'a'.repeat(64),baselineBlocks:document.blocks,histories:{current:cache},pendingDrafts:{current:{}},onQualified(){},confirmedRichEdit:draft.confirmedRichEdit,richBlockHistory:draft.richBlockHistory,recordRichBlockHistory:draft.recordRichBlockHistory,restoreRichBlockHistory:draft.restoreRichBlockHistory,updateFDXBlockText,selections:{current:{}},setPending:fn=>pending=fn(pending),onChange:value=>{blocks=value;context.blocks=value;},onUnqualified:(value,message)=>retained={value,message},Error};
 runInNewContext(await declaration('edit')+'globalThis.change=edit;',context);
 const input=(text,from,to,inputType)=>{context.selections.current['fdx-0']={from,to,inputType};context.change({currentTarget:{value:text},nativeEvent:{inputType}},blocks[0]);};
 input('aaa',0,0,'deleteContentForward');assert.equal(blocks[0].edit_operations[0].start,0);assert.equal(blocks[0].edit_operations[0].end,1);
 input('aaaa',0,0,'historyUndo');assert.equal(retained,undefined);assert.deepEqual(blocks[0].runs,document.blocks[0].runs);assert.equal(blocks[0].edit_operations.length,0);
 input('aaa',0,0,'historyRedo');assert.equal(blocks[0].edit_operations.length,1);
 input('aaaa',0,0,'historyUndo');input('aaaa!',4,4,'insertText');
 const output=parseFDXDocument(serializeFDXDocument(document,blocks));assert.deepEqual(output.blocks[0].runs[0],document.blocks[0].runs[0]);assert.equal(output.blocks[0].text,'aaaa!');
});
test('browser history refuses undo older than an acknowledged revision while retaining full text',()=>{
 assert.equal(typeof draft.richBlockHistory,'function');const document=parseFDXDocument(xml),cache={entries:{}};
 const entry=draft.richBlockHistory(cache,document.blocks[0],document.blocks[0],'a'.repeat(64));
 const changed=updateFDXBlockText(document.blocks[0],'aaa',{start:0,end:1,text:''});draft.recordRichBlockHistory(entry,changed);
 const acknowledged=parseFDXDocument(serializeFDXDocument(document,[changed])).blocks[0];acknowledged.edit_operations=[];
 const fresh=draft.richBlockHistory(cache,acknowledged,acknowledged,'b'.repeat(64));
 assert.throws(()=>draft.restoreRichBlockHistory(fresh,'aaaa','historyUndo'),/acknowledged|working copy|retained/i);
 assert.deepEqual(fresh.states[fresh.index],acknowledged);
});
test('actual Save refuses visible unqualified draft before any request or saved status',async()=>{
 let writes=0,saved=0,recovered;
 const context={richWorkingDraft:'Full visible unsaved text',loadedProjectRef:{current:'Rich'},saveCoordinator:{isDirty:()=>true,save:async()=>{writes++;return {}; }},preserveDraft:value=>recovered=value,reportSaveFailure:(value,error)=>{recovered=value;},setAutoSaveStatus:()=>saved++,setSaveProblem:()=>saved++,setLastSavedTime:()=>saved++,draftStillCurrent:()=>true,Error};
 runInNewContext(await declaration('saveCapturedDraft','ScreenwritingTab')+'globalThis.save=saveCapturedDraft;',context);
 await assert.rejects(context.save({project:'Rich',content:'Full visible unsaved text'}),/unqualified edit/);assert.equal(writes,0);assert.equal(saved,0);assert.equal(recovered.content,'Full visible unsaved text');
});
test('actual acknowledgement advances rich anchor and keeps later pending operations unsaved',async()=>{
 const document=parseFDXDocument(xml);delete document.original_xml;document.schema='aibs_rich_fdx_v1';document.source_sha256='a'.repeat(64);document.document_sha256='a'.repeat(64);document.applied_operation_ids=[];
 const first=draft.cloneRichFDX(document);first.blocks[0]=updateFDXBlockText(first.blocks[0],'aaa',{start:0,end:1,text:''});
 const pending=draft.cloneRichFDX(first);pending.blocks[0]=updateFDXBlockText(pending.blocks[0],'aaa!',{start:3,end:3,text:'!'});
 const original=parseFDXDocument(xml);const ack=parseFDXDocument(serializeFDXDocument(original,first.blocks));delete ack.original_xml;ack.source_sha256=document.source_sha256;ack.document_sha256='b'.repeat(64);ack.applied_operation_ids=[first.blocks[0].edit_operations[0].id];
 const result={fdx_document:ack,revision:ack.document_sha256,content:draft.richFDXProjection(ack)};let visible,saved=0;
 const context={richWorkingDraft:null,loadedProjectRef:{current:'Rich'},saveCoordinator:{isDirty:()=>true,save:async()=>result},preserveDraft(){},reportSaveFailure(){},currentRichDocument:()=>pending,cloneRichFDX:draft.cloneRichFDX,prepareRichFDXWrite:draft.prepareRichFDXWrite,richDocumentRef:{current:document},richAckEpochRef:{current:3},astRef:{current:pending.blocks},setAst:blocks=>visible=blocks,draftStillCurrent:()=>false,setAutoSaveStatus:()=>saved++,setSaveProblem:()=>saved++,setLastSavedTime:()=>saved++,Error};
 runInNewContext(await declaration('saveCapturedDraft','ScreenwritingTab')+'globalThis.save=saveCapturedDraft;',context);
 await context.save({project:'Rich',content:draft.richFDXProjection(first)});assert.equal(context.richAckEpochRef.current,4);assert.equal(context.richDocumentRef.current.document_sha256,'b'.repeat(64));assert.equal(visible[0].text,'aaa!');assert.equal(visible[0].edit_operations.length,1);assert.equal(visible[0].edit_operations[0].id,pending.blocks[0].edit_operations[1].id);assert.equal(saved,0);
});
test('actual controller retains all unqualified fields and resolves only after every visible field is known',async()=>{
 const document=parseFDXDocument(xml.replace('</Content>','<Paragraph Type="Action"><Text>Second.</Text></Paragraph></Content>'));let blocks=document.blocks,retained,resolved=0;
 const context={blocks,revision:'a'.repeat(64),baselineBlocks:document.blocks,histories:{current:{entries:{}}},pendingDrafts:{current:{}},onQualified:()=>resolved++,confirmedRichEdit:draft.confirmedRichEdit,richBlockHistory:draft.richBlockHistory,recordRichBlockHistory:draft.recordRichBlockHistory,restoreRichBlockHistory:draft.restoreRichBlockHistory,updateFDXBlockText,selections:{current:{}},setPending:()=>{},onChange:value=>{blocks=value;context.blocks=value;},onUnqualified:(value,message)=>retained={value,message},Error};
 runInNewContext(await declaration('edit')+'globalThis.change=edit;',context);
 context.change({currentTarget:{value:'First unsupported visible draft'}},blocks[0]);context.change({currentTarget:{value:'Second unsupported visible draft'}},blocks[1]);
 assert.deepEqual(Array.from(retained.value,block=>block.text),['First unsupported visible draft','Second unsupported visible draft']);assert.equal(resolved,0);
 context.change({currentTarget:{value:blocks[0].text},nativeEvent:{inputType:'historyUndo'}},blocks[0]);assert.equal(resolved,0);assert.equal(retained.value[1].text,'Second unsupported visible draft');
 context.change({currentTarget:{value:blocks[1].text},nativeEvent:{inputType:'historyUndo'}},blocks[1]);assert.equal(resolved,1);assert.deepEqual(context.pendingDrafts.current,{});
});
