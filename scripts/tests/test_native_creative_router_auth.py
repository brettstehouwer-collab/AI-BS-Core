"""Mounted real router dependencies; synthetic auth and adapter, no live service."""
import ast,asyncio,json,sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi import APIRouter,Depends,FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from security.screenwriting_access import require_screenwriting_access

class MountedRouterAuth(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        adapter=SimpleNamespace(redeem=lambda scope,grant:(self.calls.append(grant) or dict(lease='synthetic')))
        ns=dict(asyncio=asyncio,json=json,Request=Request,HTTPException=HTTPException,JSONResponse=JSONResponse,_NATIVE_CREATIVE_ADAPTER=adapter)
        tree=ast.parse(Path('backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
        names={'_native_creative_owner','_screenwriting_owner_scope'}
        helpers=[x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name in names]
        exec(compile(ast.Module(body=helpers,type_ignores=[]),'<actual-owner>','exec'),ns)
        ns['router']=APIRouter(dependencies=[Depends(require_screenwriting_access),Depends(ns['_screenwriting_owner_scope'])])
        endpoint=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='redeem_native_creative')
        exec(compile(ast.Module(body=[endpoint],type_ignores=[]),'<actual-route>','exec'),ns)
        app=FastAPI();app.include_router(ns['router']);self.client=TestClient(app)
        self.addCleanup(self.client.close)
        auth=patch('security.screenwriting_access.verify_admin_credentials',side_effect=lambda key,bearer:key=='synthetic-allowed');auth.start();self.addCleanup(auth.stop)
        owner=patch('security.firebase_auth.get_admin_principal',return_value='local_admin');owner.start();self.addCleanup(owner.stop)
        self.body={'grant':'nch_g_'+'a'*43}

    def test_anonymous_denied_before_redemption_and_valid_channel_allowed(self):
        url='/api/screenwriting/native/redeem'
        self.assertEqual(self.client.post(url,json=self.body).status_code,403)
        self.assertEqual(self.calls,[])
        result=self.client.post(url,json=self.body,headers={'X-API-Key':'synthetic-allowed'})
        self.assertEqual(result.status_code,200);self.assertEqual(result.headers['cache-control'],'no-store')
        self.assertEqual(self.calls,[self.body['grant']])

    def test_lease_header_cannot_bypass_owner_dependency_on_redemption(self):
        result=self.client.post('/api/screenwriting/native/redeem',json=self.body,headers={'X-API-Key':'synthetic-allowed','X-AI-BS-Creative-Lease':'forged'})
        self.assertEqual(result.status_code,403);self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
