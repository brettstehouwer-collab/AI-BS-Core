/** Actual mobile handlers in an isolated VM. Synthetic responses only; no browser/model calls. */
import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import {attachmentSourceReferences} from '../../frontend/src/utils/attachedSources.js';
import {attachmentPromptContent} from '../../frontend/src/utils/screenplayHandoff.js';
import {readChatHttpResponse} from '../../frontend/src/utils/chatHttpResponse.js';
import {ChatStreamParser,frameTextFor,stripMetadataFrames} from '../../frontend/src/utils/chatStream.js';

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
function environment({files=[pdf()],history=[],provider='local',model='fixture',current=true,ready=true}={}){
 const state={files,messages:history,input:'Find the relevant passage',loading:false,current,ready,requests:[],providerCalls:[],authCalls:[],bins:{},inputValue:'selected',clears:0};
 const update=(field,value)=>{state[field]=typeof value==='function'?value(state[field]):value;};
 const signal={current:null};
 const sandbox={AbortController,AbortSignal,Date,Response,TextDecoder,TextEncoder,console:{log(){},warn(){},error(){}},
  BACKEND_URL:scope.backend_url,currentUser:{uid:'fixture-owner'},attachments:files,chatMessages:history,footerInput:state.input,isLoading:false,
  selectedProvider:provider,selectedModel:model,isMobileClient:false,autoSpeak:false,
  conversationMemory:{get viewReady(){return state.ready;},owner:scope.owner,conversationId:scope.conversation_id,isCurrent:()=>state.current},
  useAppStore:{getState:()=>({chatMessages:state.messages,footerInput:state.input})},
  attachmentSourceReferences,attachmentPromptContent,ChatStreamParser,frameTextFor,stripMetadataFrames,isComfyStatusQuery:()=>false,errorMessage:error=>error?.message||String(error),
  setChatMessages:value=>update('messages',value),setFooterInput:value=>update('input',value),setAttachments:value=>{state.clears++;update('files',value);},
  setIsLoading:value=>update('loading',value),setIsUploadingFile:value=>update('uploading',value),setActionSheetOpen(){},
  abortControllerRef:signal,chatRequestEpochRef:{current:0},fileInputRef:{current:{get value(){return state.inputValue;},set value(value){state.inputValue=value;}}},
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
  assert.equal(f.state.messages.length,0);assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);assert.equal(f.state.clears,0);
 });
 for(const condition of ['history-not-ready','stale-owner'])test(`${part}: ${condition} cannot admit or clear a send`,async()=>{
  const f=environment({ready:condition!=='history-not-ready',current:condition!=='stale-owner'});
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.authCalls.length,0);assert.equal(f.state.requests.length,0);assert.equal(f.state.messages.length,0);
  assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);assert.equal(f.state.clears,0);assert.equal(f.state.loading,false);
 });
 for(const condition of ['ready','stale-owner','history-not-ready','cancelled'])test(`${part}: authentication wait preserves draft and sources before ${condition}`,async()=>{
  const f=environment({provider:'openai'});let finishAuth;
  f.sandbox.chatAuthHeaders=()=>new Promise(resolve=>{finishAuth=resolve;});
  const pending=vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.messages.length,0);assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);assert.equal(f.state.clears,0);
  if(condition==='stale-owner')f.state.current=false;
  if(condition==='history-not-ready')f.state.ready=false;
  if(condition==='cancelled')f.sandbox.abortControllerRef.current.abort();
  finishAuth({Authorization:'synthetic'});await pending;
  if(condition==='ready')assert.equal(f.state.providerCalls.length,1);
  else {assert.equal(f.state.providerCalls.length,0);assert.equal(f.state.messages.length,0);assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);assert.equal(f.state.clears,0);}
 });
 test(`${part}: failed fresh authentication does not clear staged input`,async()=>{
  const f=environment();f.sandbox.chatAuthHeaders=async()=>{throw Error('Synthetic authentication denial');};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,0);assert.ok(!f.state.messages.some(m=>m.role==='user'));assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);assert.equal(f.state.clears,0);
 });
 test(`${part}: old authentication cannot clear a newer request controller`,async()=>{
  const f=environment();let finishAuth;f.sandbox.chatAuthHeaders=()=>new Promise(resolve=>{finishAuth=resolve;});
  const pending=vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  const newer=new AbortController();f.sandbox.abortControllerRef.current=newer;finishAuth({Authorization:'synthetic'});await pending;
  assert.equal(f.sandbox.abortControllerRef.current,newer);assert.equal(f.state.loading,true);assert.equal(f.state.requests.length,0);assert.equal(f.state.messages.length,0);assert.equal(f.state.clears,0);
 });
 test(`${part}: a second click cannot duplicate pending authentication or dispatch`,async()=>{
  const f=environment();let finishAuth,calls=0;f.sandbox.chatAuthHeaders=()=>{calls++;return new Promise(resolve=>{finishAuth=resolve;});};
  const send=vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox);const pending=send();await send();
  assert.equal(calls,1);assert.equal(f.state.messages.length,0);assert.equal(f.state.clears,0);finishAuth({Authorization:'synthetic'});await pending;
  assert.equal(f.state.requests.length,1);assert.equal(f.state.messages.filter(m=>m.role==='user').length,1);
 });
 for(const replacement of ['active','completed'])test(`${part}: late old failure preserves ${replacement} newer request state`,async()=>{
  const f=environment({model:'stehouwer_llm'});let rejectRead;
  f.sandbox.fetch=async()=>({ok:true,body:{getReader:()=>({read:()=>new Promise((resolve,reject)=>{rejectRead=reject;}),cancel(){},releaseLock(){}})}});
  const pending=vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  while(!rejectRead)await Promise.resolve();
  const newer=new AbortController(),newFile={name:'newer.txt'};const newerReply={role:'assistant',content:replacement==='active'?'':'Newer completed answer'};
  f.sandbox.abortControllerRef.current=replacement==='active'?newer:null;f.sandbox.chatRequestEpochRef.current++;
  f.state.input='';f.state.files=[newFile];f.state.messages=[...f.state.messages,{role:'user',content:'Newer request'},newerReply];f.state.loading=replacement==='active';
  rejectRead(Error('Synthetic late old failure'));await pending;
  assert.equal(f.state.messages.at(-1),newerReply);assert.equal(f.state.input,'');assert.deepEqual(f.state.files,[newFile]);
  assert.equal(f.state.loading,replacement==='active');assert.equal(f.sandbox.abortControllerRef.current,replacement==='active'?newer:null);
 });
 for(const endpoint of ['chat','secondary-fallback'])test(`${part}: cancellation during ${endpoint} body read cannot publish or speak`,async()=>{
  const f=environment();let spoken=0;f.sandbox.autoSpeak=true;f.sandbox.speakText=()=>{spoken++;};
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return endpoint==='secondary-fallback'&&!url.endsWith('/stream')?new Response('Unsupported',{status:404}):Response.json({response:'Late cancelled answer'});};
  f.sandbox.readChatHttpResponse=async()=>{f.sandbox.abortControllerRef.current.abort();return {response:'Late cancelled answer'};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,endpoint==='chat'?1:3);assert.equal(spoken,0);assert.ok(!f.state.messages.some(m=>m.content==='Late cancelled answer'));
  assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);
 });
 for(const phase of ['onText','completion'])test(`${part}: late OpenAI ${phase} cannot publish or speak after scope change`,async()=>{
  const f=environment({provider:'openai'});let spoken=0;f.sandbox.autoSpeak=true;f.sandbox.speakText=()=>{spoken++;};
  f.sandbox.streamBSChatProvider=async options=>{f.state.providerCalls.push(options);f.state.current=false;if(phase==='onText')options.onText('Late foreign answer','Fixture');return {content:'Late foreign answer'};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.providerCalls.length,1);assert.equal(spoken,0);assert.ok(!f.state.messages.some(m=>m.content==='Late foreign answer'));
  assert.equal(f.state.input,'Find the relevant passage');assert.equal(f.state.files.length,1);
 });
 for(const failure of [false,true])test(`${part}: later draft and attachment survive authentication${failure?' and request failure':''}`,async()=>{
  const f=environment();const later={name:'later.txt',type:'text/plain',ext:'.txt',content:'Synthetic later text'};
  f.sandbox.chatAuthHeaders=async()=>{f.state.input='Newer draft';f.state.files=[...f.state.files,later];return {Authorization:'synthetic'};};
  if(failure)f.sandbox.fetch=async()=>{throw Error('Synthetic uncertain dispatch');};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.input,'Newer draft');assert.ok(f.state.files.includes(later));assert.equal(f.state.files.length,failure?2:1);
  assert.deepEqual(JSON.parse(JSON.stringify(f.state.messages.find(m=>m.role==='user').source_references)),refs);
 });
 test(`${part}: OpenAI path receives references outside the prose`,async()=>{
  const f=environment({provider:'openai'});await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.providerCalls.length,1);assert.deepEqual(JSON.parse(JSON.stringify(f.state.providerCalls[0].sourceReferences)),refs);
  assert.equal(f.state.requests.length,0);assert.match(f.state.providerCalls[0].prompt,/Preserved PDF reference/);
 });
 for(const behavior of ['eof','disconnect','disconnect-release-error'])test(`${part}: hybrid reader released once after ${behavior}`,async()=>{
  const f=environment({model:'stehouwer_llm'});let reads=0,releases=0,cancels=0;
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return {ok:true,body:{getReader:()=>({
   read:async()=>{if(!reads++)return {done:false,value:new TextEncoder().encode('Synthetic partial answer')};if(behavior==='eof')return {done:true};throw Error('Original synthetic read failure');},
   releaseLock:()=>{releases++;if(behavior==='disconnect-release-error')throw Error('Synthetic cleanup failure');},
   cancel:()=>{cancels++;if(behavior==='disconnect-release-error')return Promise.reject(Error('Synthetic cancel failure'));}
  })}};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(releases,1);assert.equal(cancels,behavior==='eof'?0:1);assert.equal(f.state.requests.length,1);assert.ok(f.state.messages.some(m=>m.content==='Synthetic partial answer'));
  if(behavior!=='eof'){assert.match(f.state.messages.at(-1).content,/Original synthetic read failure/);assert.doesNotMatch(f.state.messages.at(-1).content,/Synthetic cleanup failure/);assert.equal(f.state.files.length,1);}
 });
 for(const tail of ['<','<!--AI-', '\ufffd'])test(`${part}: EOF publishes the complete decoded parser tail ${JSON.stringify(tail)}`,async()=>{
  const f=environment({model:'stehouwer_llm'});const bytes=tail==='\ufffd'?new Uint8Array([65,110,115,119,101,114,32,0xe2]):new TextEncoder().encode('Answer '+tail);
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return new Response(bytes);};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,1);assert.equal(f.state.messages.at(-1).content,'Answer '+tail);
 });
 for(const hasSource of [true,false])test(`${part}: cancellation releases and cancels once without fallback${hasSource?' with source':''}`,async()=>{
  const f=environment({files:hasSource?[pdf()]:[],model:'stehouwer_llm'});let reads=0,releases=0,cancels=0;
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return {ok:true,body:{getReader:()=>({
   read:async()=>{if(!reads++)return {done:false,value:new TextEncoder().encode('Synthetic partial answer')};f.sandbox.abortControllerRef.current.abort();return {done:true};},
   cancel:()=>{cancels++;},releaseLock:()=>{releases++;}
  })}};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,1);assert.equal(releases,1);assert.equal(cancels,1);assert.equal(f.state.input,'Find the relevant passage');
  assert.ok(f.state.messages.some(m=>m.content==='Synthetic partial answer'));assert.equal(f.state.files.length,hasSource?1:0);
 });
 for(const behavior of ['cancel-empty','owner-switch-partial','disconnect-no-source'])test(`${part}: ${behavior} retains the request without replay`,async()=>{
  const f=environment({files:behavior==='owner-switch-partial'?[pdf()]:[],model:'stehouwer_llm'});let reads=0,releases=0,cancels=0;
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});return {ok:true,body:{getReader:()=>({
   read:async()=>{if(behavior==='cancel-empty'){f.sandbox.abortControllerRef.current.abort();return {done:true};}
    if(!reads++)return {done:false,value:new TextEncoder().encode('Synthetic partial answer')};
    if(behavior==='owner-switch-partial'){f.state.current=false;return {done:true};}throw Error('Synthetic uncertain partial disconnect');},
   cancel:()=>{cancels++;},releaseLock:()=>{releases++;}
  })}};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  assert.equal(f.state.requests.length,1);assert.equal(releases,1);assert.equal(cancels,1);assert.equal(f.state.input,'Find the relevant passage');
  if(behavior!=='cancel-empty')assert.ok(f.state.messages.some(m=>m.content==='Synthetic partial answer'));
  if(behavior==='owner-switch-partial'){assert.equal(f.state.files.length,1);assert.deepEqual(JSON.parse(JSON.stringify(f.state.messages.find(m=>m.role==='user').source_references)),refs);}
 });
 test(`${part}: split metadata stays separate and prior history stays bounded`,async()=>{
  const history=Array.from({length:35},(_,index)=>({role:index%2?'assistant':'user',content:`Earlier ${index}<!--AI-BS-METADATA:{"hidden":true}-->`}));
  const f=environment({history,model:'stehouwer_llm'});const frame='<!--AI-BS-METADATA:{"display_name":"Fixture stream","source_retrieval":{"hits":1}}-->';
  f.sandbox.fetch=async(url,options)=>{f.state.requests.push({url,options});let index=0;const chunks=['Synthetic ',frame.slice(0,10),frame.slice(10,42),frame.slice(42),'answer'];return {ok:true,body:{getReader:()=>({read:async()=>index<chunks.length?{done:false,value:new TextEncoder().encode(chunks[index++])}:{done:true},releaseLock(){}})}};};
  await vm.runInNewContext(`(${actual.handler('handleSendMessage')})`,f.sandbox)();
  const sent=JSON.parse(f.state.requests[0].options.body);assert.equal(sent.messages.length,32);assert.equal(sent.messages[0].content,'Earlier 3');assert.equal(sent.messages.at(-1).content,'Earlier 34');
  const reply=f.state.messages.at(-1);assert.equal(reply.content,'Synthetic answer');assert.equal(reply.model,'Fixture stream');assert.equal(reply.source_retrieval.hits,1);assert.doesNotMatch(reply.content,/METADATA|hidden/);
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
  for(const call of selected)for(const signalApi of [AbortSignal,{}]){let captured;const controller=new AbortController();const sandbox={reqHeaders:{Authorization:'synthetic'},targetBase:scope.backend_url,formattedPrompt:'metadata',rawText:'query',sourceReferences:refs,recentHistory:[],selectedProvider:'local',selectedModel:'fixture',controller,fallbackTimeout:1000,AbortSignal:signalApi,fetch:async(url,options)=>{captured={url,options};}};
   await vm.runInNewContext(actual.code(call),sandbox);assert.deepEqual(JSON.parse(captured.options.body).source_references,refs);assert.ok(captured.options.signal);controller.abort();assert.equal(captured.options.signal.aborted,true);}
 });
}
