"""Actual source registration + endpoints + admin middleware; offline fixture IO only."""
import ast,asyncio,copy,importlib.util,json,os,sys,tempfile,types,unittest
from pathlib import Path
from typing import Any,List,Optional
from unittest.mock import patch,AsyncMock,Mock
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4
import httpx
from fastapi import APIRouter,FastAPI,HTTPException,Request
from fastapi.responses import JSONResponse,StreamingResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel,Field,StrictBool,StrictStr
from starlette.middleware.base import BaseHTTPMiddleware
ROOT=Path(__file__).resolve().parents[2] if Path(__file__).resolve().parent==Path('C:/AI-BS/scripts/tests') else Path('C:/AI-BS')
# Normal CI checks canonical files. A retained staging check must opt in to its
# complete checkpoint explicitly; never silently prefer old staging sources.
STAGED_ROOT=os.environ.get('AIBS_HYBRID_ROUTE_TEST_STAGED_ROOT')
def product(relative):
 if not STAGED_ROOT:return ROOT/relative
 lane=('bschat-route-registration-repair' if relative=='backend/AI_BS_Backend.py' else
       'batch-runtime-repair' if relative=='backend/batch_job_runner.py' else 'bschat-local-runtime-repair')
 return Path(STAGED_ROOT)/lane/'staged'/relative
sys.path.insert(0,str(ROOT/'backend'))
from core.personal_memory_scope import current_memory_principal
OWNER='firebase:route-fixture:owner';OTHER='firebase:route-fixture:other'
PATH='/api/v1/hybrid-chat/stream'
SOURCE=[{'source_id':'a'*32,'source_sha256':'b'*64}]

def tree(path):return ast.parse(path.read_text(encoding='utf-8-sig'))
def compile_nodes(nodes,scope,path):exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)
def is_early(node):
 return isinstance(node,ast.Try) and any(isinstance(child,ast.ImportFrom) and child.module=='core' and any(alias.name=='hybrid_reasoning_engine' for alias in child.names) for child in node.body)

class HybridRegistrationTests(unittest.TestCase):
 def setUp(self):
  self.main=product('backend/AI_BS_Backend.py');self.nodes=tree(self.main).body;self.events=[];self.scopes=[];self.calls=[];self.provider_mode='fixture'
  self.bundle={'context':'[ATTACHED_SOURCE_REFERENCES] SOURCE_SENTINEL /ps untrusted [END_ATTACHED_SOURCE_REFERENCES]',
   'receipt':{'schema':'aibs.attached_source_retrieval.v1','status':'retrieved','search_scope':'explicit_attached_owner_sources','search_type':'lexical_scan','sources':SOURCE,'returned_passages':1,'source_instructions_trusted':False}}
  def module(name,**values):
   item=types.ModuleType(name);vars(item).update(values);return item
  async def provider(body):
   self.events.append(('provider',body.get('model')))
   return {'response':'fixture protected reply'} if self.provider_mode=='fixture' else None
  async def source(query,refs):
   self.events.append(('source',query,current_memory_principal(),copy.deepcopy(refs)))
   if current_memory_principal()!=OWNER:raise HTTPException(409,'Synthetic source unavailable for this account')
   return copy.deepcopy(self.bundle)
  async def primary_stream(prompt,messages=None,*,intent_prompt=None,source_context_bundle=None,primary_model=None,**kwargs):
   self.calls.append({'kind':'primary','prompt':prompt,'primary_model':primary_model,'bundle':copy.deepcopy(source_context_bundle),'owner':current_memory_principal()});yield 'fixture primary answer'
  async def legacy_stream(**kwargs):
   self.calls.append({'kind':'compat','owner':current_memory_principal(),**copy.deepcopy(kwargs)});yield 'fixture compatibility answer'
  from core.attached_source_context import validate_request_sources,source_unavailable_reply
  modules={'core.media_intent_policy':module('core.media_intent_policy',resolve_media_status=AsyncMock(return_value=None),media_status_response=AsyncMock(return_value=None)),
   'core.optional_web_search':module('core.optional_web_search',web_search_response=AsyncMock(return_value=None),optional_web_context=AsyncMock(return_value=None)),
   'core.coding_chat':module('core.coding_chat',is_coding_request=lambda body:False,coding_request=Mock(side_effect=AssertionError('No host coding execution'))),
   'core.bs_chat_provider':module('core.bs_chat_provider',bs_chat_reply=provider,hybrid_reply_response=lambda reply:StreamingResponse(iter([reply['response']]),media_type='text/plain')),
   'core.attached_source_context':module('core.attached_source_context',validate_request_sources=validate_request_sources,request_source_bundle=source,source_unavailable_reply=source_unavailable_reply),
   'core.local_chat_inference':module('core.local_chat_inference',stream_local=legacy_stream),
   'batch_job_runner':module('batch_job_runner',is_batchable=lambda prompt:False),
   'modules.gpu_hardware_telemetry':module('modules.gpu_hardware_telemetry',gpu_telemetry_engine=types.SimpleNamespace(query_nvml_telemetry=lambda:{}))}
  shared=modules['core.local_chat_inference']
  helper_path=product('backend/core/local_chat_inference.py')
  helper_spec=importlib.util.spec_from_file_location('fixture_route_history_helpers',helper_path)
  actual_helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(actual_helper)
  for name in ('LocalInferenceError','conversation_prompt','context_profile'):setattr(shared,name,getattr(actual_helper,name))
  modules['core.pipeline_context_injector']=module('core.pipeline_context_injector',AIBS_SOVEREIGN_SYSTEM_PROMPT='AI-BS fixture platform identity.')
  for name,predicate,require in [('vault_access','is_vault_path','require_vault_access'),('analytics_access','is_analytics_path','require_analytics_access'),('recdebut_access','is_recdebut_path','require_recdebut_access')]:
   modules['security.'+name]=module('security.'+name,**{predicate:lambda path:False,require:AsyncMock()})
  modules['security.screenwriting_access']=module('security.screenwriting_access',is_screenwriting_path=lambda path:False,screenwriting_request_allowed=lambda request:True)
  modules['security.document_access']=module('security.document_access',is_document_path=lambda path:False,document_request_allowed=lambda request:True)
  setting=patch.dict(sys.modules,modules);setting.start();self.addCleanup(setting.stop)
  self.primary_module=module('core.hybrid_reasoning_engine',router=APIRouter(prefix='/api/v1/hybrid-chat'),is_coding_intent=lambda text:(False,0))
  primary_path=product('backend/core/hybrid_reasoning_engine.py')
  namespace={'__name__':'fixture_primary_hybrid','router':self.primary_module.router,'BaseModel':BaseModel,'Field':Field,'StrictBool':StrictBool,'StrictStr':StrictStr,'Optional':Optional,'StreamingResponse':StreamingResponse,'json':json,'asyncio':asyncio,'stream_stehouwer_hybrid_response':primary_stream}
  compile_nodes([node for node in tree(primary_path).body if getattr(node,'name',None) in {'ChatRequest','chat_hybrid_endpoint'}],namespace,primary_path)
  for name in ('ChatRequest','chat_hybrid_endpoint'):setattr(self.primary_module,name,namespace[name])
  import core
  setting=patch.dict(sys.modules,{'core.hybrid_reasoning_engine':self.primary_module});setting.start();self.addCleanup(setting.stop)
  setting=patch.object(core,'hybrid_reasoning_engine',self.primary_module,create=True);setting.start();self.addCleanup(setting.stop)
 def app(self,*,primary=True,legacy_first=False,aliases=False):
  app=FastAPI();scope={'__name__':'fixture_hybrid_main','app':app,'BaseModel':BaseModel,'Field':Field,'StrictBool':StrictBool,'StrictStr':StrictStr,'Optional':Optional,'List':List,'Any':Any,'Request':Request,'asyncio':asyncio,'json':json,'HTTPException':HTTPException,'StreamingResponse':StreamingResponse,'logger':types.SimpleNamespace(warning=lambda *args:None),'resolve_ollama_model':lambda model:model,'inject_safety_directive':lambda text:text,'os':types.SimpleNamespace(path=os.path,makedirs=Mock(side_effect=AssertionError('No prompt disk offload'))),'datetime':datetime,'uuid4':uuid4,'httpx':types.SimpleNamespace(AsyncClient=Mock(side_effect=AssertionError('No legacy unbounded HTTP')))}
  helper_names={'_mount_primary_hybrid_router','_register_hybrid_compat_stream'}
  compile_nodes([node for node in self.nodes if getattr(node,'name',None) in helper_names],scope,self.main)
  early=next(node for node in self.nodes if is_early(node));legacy=[node for node in self.nodes if getattr(node,'name',None) in {'HybridStreamPayload','hybrid_chat_stream_endpoint'}]
  def mount():
   if primary:compile_nodes([early],scope,self.main)
   else:
    import builtins
    actual=builtins.__import__
    def missing(name,globals=None,locals=None,fromlist=(),level=0):
     if name=='core' and 'hybrid_reasoning_engine' in fromlist:raise ImportError('Synthetic optional primary module unavailable')
     return actual(name,globals,locals,fromlist,level)
    with patch('builtins.__import__',side_effect=missing):compile_nodes([early],scope,self.main)
  if legacy_first:
   compile_nodes(legacy,scope,self.main)
   if aliases:
    app.post('/fixture/legacy-callable-copy')(scope['hybrid_chat_stream_endpoint']);app.get(PATH)(scope['hybrid_chat_stream_endpoint'])
   app.openapi();mount()
  else:mount();compile_nodes(legacy,scope,self.main)
  middleware=next(node for node in self.nodes if getattr(node,'name',None)=='AdminExecutionBoundaryMiddleware')
  scope.update(BaseHTTPMiddleware=BaseHTTPMiddleware,JSONResponse=JSONResponse,HOST_CONTROL_PRIVATE_HEADERS={'Cache-Control':'private, no-store'},limit_host_upload=AsyncMock(),get_admin_principal=lambda key,authorization:OWNER if key=='fixture-owner' else OTHER if key=='fixture-other' else None)
  compile_nodes([middleware],scope,self.main);app.add_middleware(scope['AdminExecutionBoundaryMiddleware'])
  @app.middleware('http')
  async def observe(request,call_next):
   response=await call_next(request);self.scopes.append(getattr(request.scope.get('endpoint'),'__name__',None));return response
  client=TestClient(app);self.addCleanup(client.close);return app,client,scope
 def post(self,client,**fields):return client.post(PATH,headers={'X-Admin-Key':'fixture-owner'},json={'prompt':'Explain this source','user_prompt':'Explain this source','model':'llama3.1:latest',**fields})
 def actual_transport(self,*,status=200,admitted_ctx=8192):
  path=product('backend/core/local_chat_inference.py')
  spec=importlib.util.spec_from_file_location('fixture_actual_route_local_transport',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  rows=[];leases=[]
  from orchestrator.gpu_task_dispatcher import OllamaDispatcher
  self.transport_releases=[]
  @asynccontextmanager
  async def lease(model,host,**kwargs):
   # Exercise the real enabled adapter's request bounds before this offline
   # fixture admits anything. Never let synthetic admission waive its 8K cap.
   context,_,_=OllamaDispatcher._bounded_options(kwargs.get('options'))
   leases.append((model,host,kwargs))
   try:yield {'gpu_admitted':True,'execution':'fixture_only','num_ctx':min(admitted_ctx,context),'num_batch':64,'keep_alive_s':0}
   finally:self.transport_releases.append((model,host))
  setting=patch.object(module,'get_dispatcher',return_value=types.SimpleNamespace(lease=lease));setting.start();self.addCleanup(setting.stop)
  actual_client=httpx.AsyncClient
  def handle(request):
   payload=json.loads(request.content);rows.append(payload)
   return httpx.Response(status,text=json.dumps({'model':payload['model'],'response':'Fixture bounded answer','done':True,'done_reason':'stop'})+'\n')
  def client(**kwargs):return actual_client(transport=httpx.MockTransport(handle),**kwargs)
  setting=patch.object(module.httpx,'AsyncClient',side_effect=client);setting.start();self.addCleanup(setting.stop)
  setting=patch.dict(sys.modules,{'core.local_chat_inference':module});setting.start();self.addCleanup(setting.stop)
  self.actual_runner()
  return rows,leases
 def actual_runner(self):
  path=product('backend/batch_job_runner.py')
  spec=importlib.util.spec_from_file_location('fixture_actual_route_batch_runner',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  directory=tempfile.TemporaryDirectory(prefix='route-batch-',dir=ROOT/'t');self.addCleanup(directory.cleanup)
  module.BIG_JOBS_DIR=directory.name
  setting=patch.dict(sys.modules,{'batch_job_runner':module});setting.start();self.addCleanup(setting.stop)
  self.runner_directory=Path(directory.name)
  return module,Path(directory.name)
 def test_primary_first_runtime_and_openapi_have_one_matching_owner(self):
  app,client,_=self.app();response=self.post(client);self.assertEqual(response.status_code,200);self.assertEqual(self.scopes[-1],'chat_hybrid_endpoint')
  operation=app.openapi()['paths'][PATH]['post'];self.assertTrue(operation['operationId'].startswith('chat_hybrid_endpoint_'));self.assertTrue(operation['requestBody']['content']['application/json']['schema']['$ref'].endswith('/ChatRequest'))
 def test_legacy_first_primary_mount_invalidates_cached_schema_and_preserves_aliases(self):
  app,client,scope=self.app(legacy_first=True,aliases=True);response=self.post(client);self.assertEqual(response.status_code,200);self.assertEqual(self.scopes[-1],'chat_hybrid_endpoint');self.assertTrue(app.openapi()['paths'][PATH]['post']['operationId'].startswith('chat_hybrid_endpoint_'));self.assertIn('get',app.openapi()['paths'][PATH]);self.assertIn('/fixture/legacy-callable-copy',app.openapi()['paths']);self.assertTrue(callable(scope['hybrid_chat_stream_endpoint']))
 def test_failed_optional_mount_keeps_discoverable_callable_legacy_in_both_orders(self):
  for legacy_first in (False,True):
   with self.subTest(legacy_first=legacy_first):
    app,client,scope=self.app(primary=False,legacy_first=legacy_first);response=self.post(client);self.assertEqual(response.status_code,200);self.assertEqual(self.scopes[-1],'hybrid_chat_stream_endpoint');operation=app.openapi()['paths'][PATH]['post'];self.assertTrue(operation['operationId'].startswith('hybrid_chat_stream_endpoint_'));self.assertIn('HybridStreamPayload',json.dumps(operation['requestBody']));self.assertTrue(callable(scope['hybrid_chat_stream_endpoint']))
 def test_primary_and_fallback_reject_anonymous_and_body_owner_before_dispatch(self):
  for primary in (True,False):
   _,client,_=self.app(primary=primary)
   for headers in ({},{'X-Admin-Key':'not-verified'}):self.assertEqual(client.post(PATH,headers=headers,json={'prompt':'x','owner':OWNER}).status_code,403)
  self.assertEqual(self.events,[])
 def test_schema_validation_matches_actual_request_parser_and_never_bypasses_auth(self):
  for primary in (True,False):
   _,client,_=self.app(primary=primary)
   for user_prompt in (True,7,'','x'*128001):self.assertEqual(self.post(client,user_prompt=user_prompt).status_code,422)
   self.assertEqual(self.post(client,source_references=SOURCE*5).status_code,422)
  self.assertEqual(self.events,[])
 def test_legacy_local_selected_model_and_explicit_owner_source_reach_shared_transport(self):
  self.provider_mode='local';_,client,_=self.app(primary=False);response=self.post(client,source_references=SOURCE,messages=[{'role':'user','content':'Prior whole question'},{'role':'assistant','content':'Prior answer'}]);self.assertEqual(response.status_code,200);self.assertEqual(len(self.calls),1)
  call=self.calls[0];self.assertEqual(call['model'],'llama3.1:latest');self.assertEqual(call['requested_model'],'llama3.1:latest');self.assertEqual(call['source_context_bundle'],self.bundle);self.assertEqual(call['owner'],OWNER);self.assertIn('Prior whole question',call['prompt']);self.assertIn('Prior answer',call['prompt']);self.assertEqual(call['options']['num_predict'],1024);self.assertEqual(call['options']['num_ctx'],8192);self.assertNotIn('SOURCE_SENTINEL',call['prompt']);self.assertNotIn('SOURCE_SENTINEL',call['system']);self.assertTrue(response.headers['content-type'].startswith('text/plain'))
 def test_foreign_source_is_refused_before_local_transport(self):
  self.provider_mode='local';_,client,_=self.app(primary=False);response=client.post(PATH,headers={'X-Admin-Key':'fixture-other'},json={'prompt':'Explain this source','model':'llama3.1:latest','source_references':SOURCE});self.assertEqual(response.status_code,409);self.assertEqual(self.calls,[])
 def test_actual_primary_and_fallback_plan_invalidmode_and_vm_refusals_precede_models(self):
  self.provider_mode='local'
  for primary in (True,False):
   _,client,_=self.app(primary=primary)
   for fields,phrase in (({'plan_only':True},'Plan/review'),({'mode':'review'},'Plan/review'),({'mode':'invented'},'Unsupported chat mode'),({'execution_backend':'windows_vm'},'ISOLATION_UNAVAILABLE'),({'execution_backend':'outside'},'INVALID_EXECUTION_BACKEND')):
    with self.subTest(primary=primary,fields=fields):
     response=self.post(client,source_references=SOURCE,**fields);self.assertEqual(response.status_code,200);self.assertIn(phrase,response.text)
  self.assertEqual(self.events,[]);self.assertEqual(self.calls,[])
 def test_actual_shared_transport_preserves_model_history_scope_budget_and_terminal_receipt(self):
  self.provider_mode='local';rows,leases=self.actual_transport();_,client,_=self.app(primary=False)
  response=self.post(client,source_references=SOURCE,messages=[{'role':'user','content':'Complete earlier question'},{'role':'assistant','content':'Complete earlier answer'}]);self.assertEqual(response.status_code,200);self.assertEqual(len(rows),1);self.assertEqual(len(leases),1)
  payload=rows[0];self.assertEqual(payload['model'],'llama3.1:latest');self.assertIn('Complete earlier question',payload['prompt']);self.assertIn('Complete earlier answer',payload['prompt']);self.assertIn('SOURCE_SENTINEL',payload['system']);self.assertNotIn('SOURCE_SENTINEL',payload['prompt']);self.assertEqual(payload['options']['num_predict'],1024)
  metadata=[json.loads(value.split('-->')[0]) for value in response.text.split('<!--AI-BS-METADATA:')[1:]];final=metadata[-1]
  self.assertEqual(final['actual_model'],'llama3.1:latest');self.assertTrue(final['generation_verified']);self.assertTrue(final['completion_verified']);self.assertEqual(final['source_retrieval']['search_scope'],'explicit_attached_owner_sources');self.assertEqual(final['context_budget']['basis'],'conservative_utf8_bytes_not_tokenizer_count');self.assertNotIn('SOURCE_SENTINEL',json.dumps(metadata))
 def test_actual_transport_refuses_utf8_oversize_before_lease_or_http_without_truncation(self):
  self.provider_mode='local';rows,leases=self.actual_transport();_,client,_=self.app(primary=False);response=self.post(client,prompt='Ω'*12000,user_prompt='Ω'*12000,source_references=SOURCE)
  self.assertEqual(response.status_code,200);self.assertIn('context_budget_exceeded',response.text);self.assertEqual(rows,[]);self.assertEqual(leases,[])
 def test_actual_transport_provider_failure_is_terminal_and_never_replayed_on_second_host(self):
  self.provider_mode='local';rows,leases=self.actual_transport(status=503);_,client,_=self.app(primary=False);response=self.post(client,source_references=SOURCE)
  self.assertIn('provider_http_503',response.text);self.assertEqual(len(rows),1);self.assertEqual(len(leases),1);self.assertNotIn('"generation_verified":true',response.text)
 def test_actual_transport_readmits_budget_before_http_after_smaller_admission(self):
  self.provider_mode='local';rows,leases=self.actual_transport(admitted_ctx=4096);_,client,_=self.app(primary=False);response=self.post(client,prompt='x'*4000,user_prompt='x'*4000,source_references=SOURCE)
  self.assertIn('context_budget_exceeded',response.text);self.assertEqual(rows,[]);self.assertEqual(len(leases),1)

 def test_actual_fallback_multipart_keeps_exact_input_owner_history_source_and_web_profile(self):
  self.provider_mode='local';rows,leases=self.actual_transport(admitted_ctx=16384);_,directory=self.actual_runner()
  sys.modules['core.optional_web_search'].optional_web_context=AsyncMock(return_value='WEB_SENTINEL approved search evidence')
  _,client,_=self.app(primary=False)
  prompt='Global standing requirement Ω.\n[Task 1] First\n'+'first '*730+'\n[Task 2] Second\n'+'second '*730
  history=[{'role':'user','content':'Earlier whole question'},{'role':'assistant','content':'Earlier whole answer'}]
  response=self.post(client,prompt=prompt,user_prompt=prompt,messages=history,source_references=SOURCE,use_web_search=True)
  self.assertEqual(response.status_code,200);self.assertIn('Batch complete',response.text);self.assertEqual(len(rows),2);self.assertEqual(len(leases),2)
  for row in rows:
   self.assertEqual(row['model'],'llama3.1:latest');self.assertIn('Earlier whole question',row['prompt']);self.assertIn('Earlier whole answer',row['prompt']);self.assertIn('WEB_SENTINEL',row['system']);self.assertEqual(row['system'].count('SOURCE_SENTINEL'),1)
  requests=list(directory.rglob('request.json'));self.assertEqual(len(requests),1)
  archived=json.loads(requests[0].read_text(encoding='utf-8'));self.assertEqual(archived['prompt'],prompt);self.assertEqual(archived['history'],history);self.assertEqual(archived['source_context_bundle'],self.bundle)
  self.assertEqual(requests[0].parent.parent.name,__import__('hashlib').sha256(OWNER.encode()).hexdigest());self.assertEqual((requests[0].parent/'raw_prompt.txt').read_text(encoding='utf-8'),prompt)
  state=json.loads((requests[0].parent/'state.json').read_text(encoding='utf-8'));self.assertEqual(state['status'],'complete');self.assertTrue(all(value['complete'] for value in state['results'].values()));self.assertTrue((requests[0].parent/'final.md').is_file())

 def test_actual_fallback_large_single_archives_raw_history_and_clean_output(self):
  self.provider_mode='local';rows,leases=self.actual_transport();_,directory=self.actual_runner();_,client,_=self.app(primary=False)
  prompt='Literal single request Ω & punctuation. '+'body '*640;history=[{'role':'assistant','content':'Full earlier answer'}]
  response=self.post(client,prompt=prompt,user_prompt=prompt,messages=history,source_references=SOURCE)
  self.assertEqual(response.status_code,200);self.assertIn('Large request archived locally',response.text);self.assertEqual(len(rows),1);self.assertEqual(len(leases),1)
  self.assertIn('Full earlier answer',rows[0]['prompt']);self.assertEqual(rows[0]['system'].count('SOURCE_SENTINEL'),1)
  request_path=next(directory.rglob('request.json'));archived=json.loads(request_path.read_text(encoding='utf-8'));self.assertEqual(archived['prompt'],prompt);self.assertEqual(archived['history'],history);self.assertEqual(archived['source_context_bundle'],self.bundle)
  self.assertEqual((request_path.parent/'raw_prompt.txt').read_text(encoding='utf-8'),prompt);self.assertEqual((request_path.parent/'streamed_output.md').read_text(encoding='utf-8'),'Fixture bounded answer')
  state=json.loads((request_path.parent/'state.json').read_text(encoding='utf-8'));self.assertEqual(state['status'],'complete');self.assertTrue(state['complete']);self.assertTrue(state['receipt']['completion_verified'])

 def test_actual_fallback_large_failure_retains_incomplete_state_without_endpoint_replay(self):
  self.provider_mode='local';rows,leases=self.actual_transport(status=503);_,directory=self.actual_runner();_,client,_=self.app(primary=False)
  prompt='bounded '*450;response=self.post(client,prompt=prompt,user_prompt=prompt,source_references=SOURCE)
  self.assertIn('provider_http_503',response.text);self.assertEqual(len(rows),1);self.assertEqual(len(leases),1)
  state=json.loads(next(directory.rglob('state.json')).read_text(encoding='utf-8'));self.assertFalse(state['complete']);self.assertNotEqual(state['status'],'complete');self.assertEqual(state['receipt']['status'],'error');self.assertFalse(list(directory.rglob('final.md')))

 def test_actual_fallback_resumes_only_verified_owner_checkpoint_and_ignores_body_owner(self):
  self.provider_mode='local';rows,leases=self.actual_transport();_,directory=self.actual_runner();_,client,_=self.app(primary=False)
  prompt='Standing requirement.\n[Task 1] First\n'+'first '*730+'\n[Task 2] Second\n'+'second '*730
  first=self.post(client,prompt=prompt,user_prompt=prompt,owner=OTHER);self.assertIn('Batch complete',first.text);self.assertEqual(len(rows),2)
  second=self.post(client,prompt=prompt,user_prompt=prompt);self.assertIn('Reused completed owner-scoped checkpoint',second.text);self.assertEqual(len(rows),2)
  third=client.post(PATH,headers={'X-Admin-Key':'fixture-other'},json={'prompt':prompt,'user_prompt':prompt,'model':'llama3.1:latest','owner':OWNER});self.assertIn('Batch complete',third.text);self.assertEqual(len(rows),4)
  expected={__import__('hashlib').sha256(value.encode()).hexdigest() for value in (OWNER,OTHER)};self.assertEqual({path.parent.parent.name for path in directory.rglob('request.json')},expected);self.assertEqual(len(leases),len(self.transport_releases))

 def test_actual_legacy_archive_capture_survives_context_reset_and_aclose_retains_partial(self):
  self.provider_mode='local';rows,leases=self.actual_transport();_,directory=self.actual_runner();_,_,scope=self.app(primary=False)
  from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
  async def scenario():
   token=bind_memory_principal(OWNER)
   try:
    payload=scope['HybridStreamPayload'](prompt='body '*650,model='llama3.1:latest')
    response=await scope['hybrid_chat_stream_endpoint'](None,payload)
   finally:reset_memory_principal(token)
   stream=response.body_iterator;observed=[]
   async for piece in stream:
    observed.append(piece)
    if 'Fixture bounded answer' in piece:break
   await stream.aclose()
   return ''.join(observed)
  output=asyncio.run(scenario());self.assertIn('Fixture bounded answer',output);self.assertEqual(len(rows),1);self.assertEqual(len(leases),len(self.transport_releases))
  state_path=next(directory.rglob('state.json'));state=json.loads(state_path.read_text(encoding='utf-8'));self.assertEqual(state['status'],'cancelled');self.assertFalse(state['complete']);self.assertEqual((state_path.parent/'streamed_output.md').read_text(encoding='utf-8'),'Fixture bounded answer');self.assertEqual(state_path.parent.parent.name,__import__('hashlib').sha256(OWNER.encode()).hexdigest())

if __name__=='__main__':unittest.main()
