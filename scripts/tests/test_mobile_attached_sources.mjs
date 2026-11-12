/** Actual mobile handlers in an isolated VM. Synthetic responses only; no browser/model calls. */
import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import {attachmentSourceReferences} from '../../frontend/src/utils/attachedSources.js';
import {attachmentPromptContent} from '../../frontend/src/utils/screenplayHandoff.js';
import {readChatHttpResponse} from '../../frontend/src/utils/chatHttpResponse.js';

const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {parse}=require('@babel/parser');
const mirrors=['components','src/components','components/components','src/components/components'];
const scope={owner:'firebase:fixture:owner',conversation_id:'fixture-conversation',backend_url:'http://fixture.invalid'};
const refs=[{source_id:'a'.repeat(32),source_sha256:'b'.repeat(64)}];
const pdf=()=>({name:'synthetic.pdf',ext:'.pdf',type:'application/pdf',size:20,...refs[0],
  parsing_status:'complete',indexing_status:'lexical_chunks_indexed',retrieval_status:'source_passage_readback_verified',
  rag_receipt:{derived_source_sha256:'c'.repeat(64),chunk_count:1,retrieval_hits:1,search_type:'lexical_scan',model_context_expanded:false},
  get content(){throw Error('Private PDF text must not be read');}});

function parsed(part){
 const source=readFileSync(new URL(`../../frontend/${part}/MobileStehouwerChat.jsx`,import.meta.url),'utf8');
 const tree=parse(source,{sourceType:'module',plugins:['jsx']});const nodes=[];const pending=[tree];
 while(pending.length){const n=pending.pop();if(!n||typeof n!=='object')continue;nodes.push(n);
  for(const [key,value]of Object.entries(n)){if(['loc','comments','tokens'].includes(key))continue;if(Array.isArray(value))pending.push(...value);else if(value&&typeof value==='object')pending.push(value);}}
 const declaration=name=>{const selected=nodes.filter(n=>n.type==='VariableDeclarator'&&n.id?.name===name);assert.equal(selected.length,1,`${part}:${name}`);return selected[0];};
 const code=n=>source.slice(n.start,n.end);return {source,nodes,code,declaration,handler:name=>code(declaration(name).init)};
}
function environment({files=[pdf()],history=[],provider='local',model='fixture',current=true}={}){
 const state={files,messages:history,input:'Find the relevant passage',loading:false,current,requests:[],providerCalls:[],authCalls:[],bins:{},inputValue:'selected',clears:0};
 const update=(field,value)=>{state[field]=typeof value==='function'?value(state[field]):value;};
 const signal={current:null};
 const sandbox={AbortController,AbortSignal,Date,Response,TextDecoder,TextEncoder,console:{log(){},warn(){},error(){}},
  BACKEND_URL:scope.backend_url,currentUser:{uid:'fixture-owner'},attachments:files,chatMessages:history,footerInput:state.input,isLoading:false,
  selectedProvider:provider,selectedModel:model,isMobileClient:false,autoSpeak:false,
  conversationMemory:{viewReady:true,owner:scope.owner,conversationId:scope.conversation_id,isCurrent:()=>state.current},
  useAppStore:{getState:()=>({chatMessages:state.messages,footerInput:state.input})},
  attachmentSourceReferences,attachmentPromptContent,isComfyStatusQuery:()=>false,errorMessage:error=>error?.message||String(error),
  setChatMessages:value=>update('messages',value),setFooterInput:value=>update('input',value),setAttachments:value=>{state.clears++;update('files',value);},
  setIsLoading:value=>update('loading',value),setIsUploadingFile:value=>update('uploading',value),setActionSheetOpen(){},
  abortControllerRef:signal,fileInputRef:{current:{get value(){return state.inputValue;},set value(value){state.inputValue=value;}}},
  chatAuthHeaders:async(...args)=>{state.authCalls.push(args);return {...args[0],Authorization:'Bearer synthetic-owner'};},
  FormData:class{constructor(){this.values=[];}append(...args){this.values.push(args);}},
  fetch:async(url,options)=>{state.requests.push({url,options});return Response.json({status:'success',response:'Synthetic answer',model:'fixture'});},
  readChatHttpResponse,chatResponseText:data=>data.response||'',speakText(){throw Error('Unexpected audio');},
  streamBSChatProvider:async options=>{state.providerCalls.push(options);options.onText('Synthetic cloud answer','Fixture',undefined);return {content:'Synthetic cloud answer'};}
 };return {state,sandbox};
}

for(const part of mirrors){const actual=parsed(part);
 test(`${part}: authenticated upload retains verified receipt`,async()=>{
  const f=environment({files:[]});const receipt=pdf();Object.defineProperty(receipt,'content',{value:'metadata only'});
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return Response.json({status:'success',file:receipt});};
  await vm.runInNewContext(`(${actual.handler('handleFileUpload')})`,f.sandbox)({target:{files:[{name:'synthetic.pdf',type:'application/pdf',size:20}]}});
  assert.equal(f.state.requests.length,1);assert.equal(f.state.requests[0].options.headers.Authorization,'Bearer synthetic-owner');
  assert.equal(f.state.authCalls[0][1],'fixture-owner');assert.equal(f.state.authCalls[0][2].forceRefresh,true);
  assert.deepEqual(attachmentSourceReferences(f.state.files,[],scope),refs);assert.equal(f.state.uploading,false);
 });
 test(`${part}: denied PDF upload retains original local File and blocks send`,async()=>{
  const original={name:'synthetic.pdf',type:'application/pdf',size:20};const f=environment({files:[]});
  f.sandbox.fetch=async()=>new Response('Forbidden',{status:403});
  await vm.runInNewContext(`(${actual.handler('handleFileUpload')})`,f.sandbox)({target:{files:[original]}});
  assert.equal(f.state.files[0].pendingFile,original);assert.ok(!JSON.stringify(f.state.files).includes('pendingFile'));
  assert.throws(()=>attachmentSourceReferences(f.state.files,[],scope),/not confirmed/);assert.match(f.state.messages.at(-1).content,/not confirmed/);
 });
 test(`${part}: account change during fresh authentication sends no upload`,async()=>{
  const f=environment({files:[]});f.sandbox.chatAuthHeaders=async()=>{f.state.current=false;return {Authorization:'synthetic'};};
  await vm.runInNewContext(`(${actual.handler('handleFileUpload')})`,f.sandbox)({target:{files:[{name:'synthetic.pdf',type:'application/pdf'}]}});
  assert.equal(f.state.requests.length,0);assert.equal(f.state.files.length,0);
 });
 test(`${part}: send preserves explicit scope and metadata-only PDF in selected backend`,async()=>{
  const f=environment();await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,1);assert.equal(f.state.requests[0].url,`${scope.backend_url}/api/chat`);
  const body=JSON.parse(f.state.requests[0].options.body);assert.deepEqual(body.source_references,refs);assert.match(body.messages.at(-1).content,/Preserved PDF reference/);
  assert.deepEqual(JSON.parse(JSON.stringify(f.state.messages.find(m=>m.role==='user').source_reference_scope)),scope);
  assert.equal(f.state.authCalls[0][2].forceRefresh,true);assert.equal(f.state.loading,false);
 });
 test(`${part}: malformed PDF stays staged with no request and draft unchanged`,async()=>{
  const files=[{name:'synthetic.pdf',ext:'.pdf',type:'application/pdf'}];const f=environment({files});
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,0);assert.equal(f.state.providerCalls.length,0);assert.equal(f.state.files,files);
  assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.clears,0);
 });
 test(`${part}: ordinary text attachments preserve their existing prompt content`,async()=>{
  const files=[{name:'synthetic.txt',ext:'.txt',type:'text/plain',size:30,content:'Synthetic ordinary text'}];
  const f=environment({files,provider:'openai'});await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.providerCalls.length,1);assert.match(f.state.providerCalls[0].prompt,/Synthetic ordinary text/);
  assert.deepEqual(JSON.parse(JSON.stringify(f.state.providerCalls[0].sourceReferences)),[]);
 });
 test(`${part}: stale account after send authentication causes no provider request`,async()=>{
  const f=environment({provider:'openai'});f.sandbox.chatAuthHeaders=async()=>{f.state.current=false;return {Authorization:'synthetic'};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,0);assert.equal(f.state.providerCalls.length,0);
  assert.deepEqual(JSON.parse(JSON.stringify(f.state.messages.find(m=>m.role==='user').source_references)),refs);
 });
 test(`${part}: OpenAI path receives references outside the prose`,async()=>{
  const f=environment({provider:'openai'});await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.providerCalls.length,1);assert.deepEqual(JSON.parse(JSON.stringify(f.state.providerCalls[0].sourceReferences)),refs);
  assert.equal(f.state.requests.length,0);assert.match(f.state.providerCalls[0].prompt,/Preserved PDF reference/);
 });
 for(const behavior of ['eof','disconnect','disconnect-release-error'])test(`${part}: hybrid reader released once after ${behavior}`,async()=>{
  const f=environment({model:'stehouwer_llm'});let reads=0,releases=0;
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return {ok:true,body:{getReader:()=>({
   read:async()=>{if(!reads++)return {done:false,value:new TextEncoder().encode('Synthetic partial answer')};if(behavior==='eof')return {done:true};throw Error('Original synthetic read failure');},
   releaseLock:()=>{releases++;if(behavior==='disconnect-release-error')throw Error('Synthetic cleanup failure');}
  })}};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(releases,1);assert.equal(f.state.requests.length,1);assert.ok(f.state.messages.some(m=>m.content==='Synthetic partial answer'));
  if(behavior!=='eof'){assert.match(f.state.messages.at(-1).content,/Original synthetic read failure/);assert.doesNotMatch(f.state.messages.at(-1).content,/Synthetic cleanup failure/);assert.equal(f.state.files.length,1);}
 });
 for(const failure of ['network',429,'no-body','empty','metadata-only','partial'])test(`${part}: attached hybrid ${failure} never replays and retains input`,async()=>{
  const f=environment({model:'stehouwer_llm'});let calls=0;
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});calls++;
   if(failure==='network')throw Error('Synthetic disconnect');
   if(failure===429)return Response.json({detail:'Synthetic quota'},{status:429});
   if(failure==='no-body')return {ok:true,body:null};
   if(failure==='empty')return new Response('');
   if(failure==='metadata-only')return new Response('<!--AI-BS-METADATA:{"display_name":"Fixture"}-->');
   let reads=0;return {ok:true,body:{getReader:()=>({read:async()=>{if(reads++)throw Error('Synthetic partial disconnect');return {done:false,value:new TextEncoder().encode('Synthetic partial answer')};}})}};
  };
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(calls,1);assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);
  assert.match(f.state.messages.at(-1).content,/Connection Notice/);
  if(failure==='partial')assert.ok(f.state.messages.some(m=>m.content==='Synthetic partial answer'));
 });
 test(`${part}: explicit unsupported hybrid route may use selected-backend chat once`,async()=>{
  const f=environment({model:'stehouwer_llm'});
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return url.endsWith('/stream')?new Response('Not found',{status:404}):Response.json({status:'success',response:'Synthetic answer'});};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,2);assert.equal(f.state.requests[1].url,`${scope.backend_url}/api/chat`);
 });
 test(`${part}: last supported source endpoint HTTP429 is terminal and reported accurately`,async()=>{
  const f=environment();f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return url.endsWith('/stream')?Response.json({detail:'Synthetic quota'},{status:429}):new Response('Unsupported',{status:404});};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,3);assert.ok(f.state.requests.every(r=>r.url.startsWith(scope.backend_url)));
  assert.match(f.state.messages.at(-1).content,/HTTP 429/);assert.equal(f.state.files.length,1);assert.equal(f.state.input,'Find the relevant passage');
 });
 test(`${part}: subsequent turns reuse only current conversation source references`,async()=>{
  const history=[{role:'user',content:'Previous metadata',source_references:refs,source_reference_scope:scope}];
  const f=environment({files:[],history});await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.deepEqual(JSON.parse(f.state.requests[0].options.body).source_references,refs);
  const foreign=environment({files:[],history:[{...history[0],source_reference_scope:{...scope,owner:'different-owner'}}],provider:'openai'});
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,foreign.sandbox)();
  assert.deepEqual(JSON.parse(JSON.stringify(foreign.state.providerCalls[0].sourceReferences)),[]);
 });
 test(`${part}: late attachment updates remain in their original scope bin`,()=>{
  let bins={};const sandbox={attachmentScopeKey:'owner-A/conversation-A/backend-A',setAttachmentBins:update=>{bins=update(bins);}};
  const setter=vm.runInNewContext(`(${actual.code(actual.declaration('setAttachments').init)})`,sandbox);
  const original={name:'pending.pdf'};setter([original]);sandbox.attachmentScopeKey='owner-B/conversation-B/backend-A';
  // Real renders have separate lexical bindings; the previous setter remains A-bound.
  const oldScope={attachmentScopeKey:'owner-A/conversation-A/backend-A',setAttachmentBins:sandbox.setAttachmentBins};
  const oldSetter=vm.runInNewContext(`(${actual.code(actual.declaration('setAttachments').init)})`,oldScope);oldSetter(previous=>[...previous,{name:'late.pdf'}]);
  assert.equal(bins['owner-A/conversation-A/backend-A'].length,2);assert.equal(bins['owner-B/conversation-B/backend-A'],undefined);
 });
 test(`${part}: every hybrid/fallback body carries explicit references and cancellation`,async()=>{
  const calls=actual.nodes.filter(n=>n.type==='CallExpression'&&n.callee.name==='fetch'&&n.arguments[0]?.type==='TemplateLiteral'&&actual.code(n.arguments[0]).includes('/api/v1/hybrid-chat/stream'));
  const send=actual.declaration('handleSendMessage').init;const selected=calls.filter(n=>n.start>send.start&&n.end<send.end);assert.equal(selected.length,2);
  for(const call of selected){let captured;const controller=new AbortController();const sandbox={reqHeaders:{Authorization:'synthetic'},targetBase:scope.backend_url,formattedPrompt:'metadata',rawText:'query',sourceReferences:refs,recentHistory:[],selectedProvider:'local',selectedModel:'fixture',controller,fallbackTimeout:1000,AbortSignal,fetch:async(url,options)=>{captured={url,options};}};
   await vm.runInNewContext(actual.code(call),sandbox);assert.deepEqual(JSON.parse(captured.options.body).source_references,refs);assert.ok(captured.options.signal);}
 });
}
