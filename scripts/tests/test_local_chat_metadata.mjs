import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';
import test from 'node:test';
let root=path.dirname(fileURLToPath(import.meta.url));
while(!fs.existsSync(path.join(root,'frontend/package.json'))){const parent=path.dirname(root);assert.notEqual(parent,root,'Repository root not found');root=parent;}
const cp=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const stagedChat=process.env.AIBS_LOCAL_CHAT_STAGE_ROOT&&path.join(process.env.AIBS_LOCAL_CHAT_STAGE_ROOT,'frontend/src/components/ChatTab.jsx');
const text=fs.readFileSync(stagedChat&&fs.existsSync(stagedChat)?stagedChat:path.join(root,'frontend/src/components/ChatTab.jsx'),'utf8');
const require=createRequire(pathToFileURL(path.join(root,'frontend/package.json')));
const parser=require('@babel/parser');
const tree=parser.parse(text,{sourceType:'module',plugins:['jsx']});
const names=['readCognitiveMetadata','parseCognitiveContent','canFallbackToLegacyStream','createChatStreamDecoder'];
const nodes=names.map(name=>{const node=tree.program.body.find(row=>row.type==='FunctionDeclaration'&&row.id.name===name);assert.ok(node,`Missing actual ${name}`);return node;});
const context=vm.createContext({console:{warn(){}},TextDecoder});
vm.runInContext(nodes.map(node=>text.slice(node.start,node.end)).join('\n')+'\nglobalThis.actual={'+names.join(',')+'}',context);
const {readCognitiveMetadata,parseCognitiveContent,canFallbackToLegacyStream,createChatStreamDecoder}=context.actual;
const frame=meta=>'\n<!--AI-BS-METADATA:'+JSON.stringify(meta)+'-->\n';
test('late final provider receipt replaces pending stage while retaining explicit source receipt',()=>{
 const source={schema:'aibs.attached_source_retrieval.v1',sources:[{source_sha256:'a'.repeat(64)}]};
 const value=readCognitiveMetadata(frame({source_retrieval:source})+frame({status:'running',model:'specialist'})+'plain answer'+frame({status:'completed',model:'selected8B',actual_model:'selected8B',role:'primary'}));
 assert.equal(value.status,'completed');assert.equal(value.actual_model,'selected8B');assert.equal(value.source_retrieval.sources[0].source_sha256,'a'.repeat(64));
});
test('all metadata comments are removed from readable answer and malformed intermediate frame is inert',()=>{
 const value=parseCognitiveContent(frame({model:'old'})+'answer\n<!--AI-BS-METADATA:{invalid}-->\n'+frame({model:'current',status:'error'}));
 assert.equal(value.meta.model,'current');assert.equal(value.meta.status,'error');assert.equal(value.body.trim(),'answer');
});
test('cancellation, HTTP provider failures, partial or empty accepted streams cannot replay via legacy chat',()=>{
 for(const status of [0,200,400,401,403,408,429,500,502,503])assert.equal(canFallbackToLegacyStream(status,false,false),false);
 assert.equal(canFallbackToLegacyStream(404,true,false),false);assert.equal(canFallbackToLegacyStream(404,false,true),false);
 assert.equal(canFallbackToLegacyStream(404,false,false),true);assert.equal(canFallbackToLegacyStream(405,false,false),true);
});
test('fallback primary frame retains prior failed role evidence and updates the same stage identity',()=>{
 const value=readCognitiveMetadata(frame({steps:[{request_id:'helper-id',name:'explicit_shadow_coder',status:'error'}]})+
   frame({steps:[]})+frame({steps:[{request_id:'primary-id',name:'primary',status:'completed'}]}));
 assert.equal(value.steps.length,2);assert.equal(value.steps[0].status,'error');assert.equal(value.steps[1].status,'completed');
});
test('UTF8 characters split across arbitrary network byte boundaries stay exact; invalid tails fail',()=>{
 const expected='Greek Ωμεγα and emoji 👩‍💻.';const bytes=new TextEncoder().encode(expected);const decoder=createChatStreamDecoder();
 let output='';for(const byte of bytes)output+=decoder.decode(Uint8Array.of(byte));output+=decoder.finish();assert.equal(output,expected);
 const invalid=createChatStreamDecoder();invalid.decode(Uint8Array.of(0xe2));assert.throws(()=>invalid.finish());
});
test('actual mocked transport terminal reason cannot forge a later model receipt',()=>{
 const fixture=process.env.AIBS_LOCAL_CHAT_STAGE_ROOT
  ?path.join(path.dirname(process.env.AIBS_LOCAL_CHAT_STAGE_ROOT),'tests/test_local_chat_inference.py')
  :path.join(root,'scripts/tests/test_local_chat_inference.py');
 const result=spawnSync('python',['-B','-X','utf8',fixture,'--emit-forged-reason-wire'],{encoding:'utf8',timeout:10000,windowsHide:true,env:{...process.env,PYTHONPATH:root}});
 assert.equal(result.status,0,result.stderr);const value=readCognitiveMetadata(result.stdout);
 assert.equal(value.actual_model,'fixture:latest');assert.equal(value.completion_reason,'unrecognized');assert.equal(value.completion_verified,false);
 assert.equal((result.stdout.match(/<!--AI-BS-METADATA:/g)||[]).length,2);
});

// Render the actual header function with synthetic frame data and only its
// two drawer hooks opened; no application imports, browser or service calls.
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const {transformSync}=require('esbuild');
const headerNodes=['cognitiveStagePresentation','DesktopCognitiveMetaHeader'].map(name=>tree.program.body.find(row=>row.type==='FunctionDeclaration'&&row.id.name===name)).filter(Boolean);
const headerCode=transformSync(headerNodes.map(node=>text.slice(node.start,node.end)).join('\n')+'\nmodule.exports=DesktopCognitiveMetaHeader;', {loader:'jsx',jsx:'automatic',format:'cjs',target:'es2022'}).code;
const headerModule={exports:{}};
new Function('require','module','exports','useState',headerCode)(require,headerModule,headerModule.exports,()=>[true,()=>{}]);
const renderHeader=meta=>renderToStaticMarkup(React.createElement(headerModule.exports,{meta}));
const runtimeReceipt=()=>({schema:'aibs.local_inference.v1',type:'aibs_cognitive_meta',provider:'local',request_id:'1'.repeat(32),
 model:'llama3.1:latest',actual_model:'llama3.1:latest',status:'completed',generation_verified:true,completion_verified:true,completion_reason:'stop',
 steps:[{request_id:'1'.repeat(32),name:'primary',model:'llama3.1:latest',status:'completed',generation_verified:true,completion_verified:true}]});

test('actual three-frame parse and render updates pending source-bound request to recorded provider stop',()=>{
 const source={schema:'aibs.attached_source_retrieval.v1',status:'retrieved',sources:[{source_sha256:'a'.repeat(64)}]};
 const final=runtimeReceipt();const pending={...final,status:'running',generation_verified:false,completion_verified:false,steps:[]};delete pending.completion_reason;
 const beginning=frame({source_retrieval:source})+frame(pending);
 const waiting=renderHeader(parseCognitiveContent(beginning).meta);
 assert.match(waiting,/Provider request in progress/);assert.doesNotMatch(waiting,/Final provider stop recorded/);
 const parsed=parseCognitiveContent(beginning+'Synthetic answer.'+frame(final));
 assert.equal(parsed.meta.completion_verified,true);assert.equal(parsed.meta.steps[0].completion_verified,true);
 const rendered=renderHeader(parsed.meta);
 assert.match(rendered,/Final provider stop recorded/);assert.match(rendered,/Provider stop recorded for this stage/);
 assert.doesNotMatch(rendered,/Completion not verified|no runtime completion receipt attached/);
 assert.equal(parsed.meta.source_retrieval.sources[0].source_sha256,'a'.repeat(64));
});

test('legacy, unknown-schema and malformed runtime claims remain visibly unverified',()=>{
 for(const modify of [value=>{delete value.schema;},value=>{value.schema='unrecognized.v1';},value=>{value.request_id='legacy';},value=>{value.completion_verified='true';value.steps[0].completion_verified='true';}]){
  const value=runtimeReceipt();modify(value);const rendered=renderHeader(readCognitiveMetadata(frame(value)));
  assert.match(rendered,/Completion not verified/);assert.doesNotMatch(rendered,/Final provider stop recorded|Provider stop recorded for this stage/);
 }
});

test('length-limited output and failed or cancelled stages never render as completed',()=>{
 const limited=runtimeReceipt();limited.completion_verified=false;limited.completion_reason='length';limited.steps[0].completion_verified=false;
 const partial=renderHeader(readCognitiveMetadata(frame(limited)));
 assert.match(partial,/Output limit reached; completion not verified/);assert.match(partial,/Output received; clean completion not verified/);
 for(const status of ['error','cancelled']){
  const value=runtimeReceipt();value.status=status;value.generation_verified=false;value.completion_verified=false;
  value.steps[0]={...value.steps[0],status,generation_verified:false,completion_verified:false};
  const rendered=renderHeader(readCognitiveMetadata(frame(value)));
  assert.match(rendered,status==='error'?/Request failed; completion not verified/:/Request cancelled; completion not verified/);
  assert.doesNotMatch(rendered,/Final provider stop recorded|Provider stop recorded for this stage/);
 }
});

test('earlier failed helper remains failed when the selected primary later records its own clean stop',()=>{
 const value=runtimeReceipt();const failed={request_id:'2'.repeat(32),name:'explicit_shadow_coder',model:'fixture-helper',status:'error',generation_verified:false,completion_verified:false};
 const parsed=readCognitiveMetadata(frame({...value,status:'error',steps:[failed]})+frame(value));
 const rendered=renderHeader(parsed);assert.equal(parsed.steps.length,2);
 assert.match(rendered,/Stage failed; no completed generation recorded/);assert.match(rendered,/Final provider stop recorded/);
 assert.match(rendered,/Provider stop recorded for this stage/);
});

test('a later unversioned completion cannot inherit a runtime envelope from an earlier pending frame',()=>{
 const pending={...runtimeReceipt(),status:'running',generation_verified:false,completion_verified:false,steps:[]};delete pending.completion_reason;
 const legacy=runtimeReceipt();delete legacy.schema;delete legacy.type;
 const value=readCognitiveMetadata(frame(pending)+frame(legacy));
 assert.equal(value.completion_verified,true,'Preserve the reported field without promoting its provenance');
 const rendered=renderHeader(value);assert.match(rendered,/Completion not verified/);
 assert.doesNotMatch(rendered,/Final provider stop recorded|Provider stop recorded for this stage/);
});
