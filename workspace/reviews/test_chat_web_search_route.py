import ast,asyncio,json,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI,APIRouter
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel,StrictBool
from typing import Optional
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from core import optional_web_search as web
class RouteTests(unittest.TestCase):
 def exercise(self,**options):
  tree=ast.parse((ROOT/'backend/core/hybrid_reasoning_engine.py').read_text(encoding='utf-8'))
  nodes=[n for n in tree.body if getattr(n,'name','') in ['ChatRequest','chat_hybrid_endpoint']]
  calls=[]
  def search(query):calls.append((query,True));return [{'href':'https://example.com/source','body':'ROUTE_EVIDENCE_TOKEN'}]
  async def answer(payload):
   self.assertIn('ROUTE_EVIDENCE_TOKEN',payload['prompt'])
   self.assertNotIn('PRIVATE-ATTACHMENT',payload['prompt'])
   yield 'Evidence-backed fixture answer'
  async def engine(prompt,messages=None):yield json.dumps({'prompt':prompt,'messages':messages})
  ns=dict(BaseModel=BaseModel,StrictBool=StrictBool,Optional=Optional,StreamingResponse=StreamingResponse,APIRouter=APIRouter,router=APIRouter(),asyncio=asyncio,json=json,stream_stehouwer_hybrid_response=engine)
  code=types.ModuleType('core.coding_chat');code.is_coding_request=lambda body:False;code.coding_request=lambda body:None
  with patch.dict(sys.modules,{'core.coding_chat':code}),patch.object(web,'_search',search),patch.object(web,'_answer_from_sources',answer):
   exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-hybrid-router>','exec'),ns)
   app=FastAPI();app.include_router(ns['router'])
   with TestClient(app) as client:r=client.post('/stream',json={'prompt':'Describe this attached private document','messages':[{'role':'user','content':'PRIVATE-ATTACHMENT'}],**options})
  return r,calls
 def test_explicit_search_reaches_actual_route_without_sending_history(self):
  response,calls=self.exercise(use_web_search=True,web_search_query='public query')
  self.assertEqual(response.status_code,200);self.assertEqual(calls,[('public query',True)]);self.assertIn('Web search completed',response.text);self.assertNotIn('Searching the web',response.text);self.assertIn('https://example.com/source',response.text)
 def test_disabled_and_deferred_routes_never_search(self):
  for flags in [{},{'use_web_search':False},{'use_web_search':True,'plan_only':True},{'use_web_search':True,'execution_backend':'windows_vm'}]:
   response,calls=self.exercise(**flags);self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
