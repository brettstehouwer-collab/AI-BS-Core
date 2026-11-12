"""Client -> actual route body -> real registry/store, controlled OS identity.

No production listener/authentication stack, real process or original project.
"""
import ast,asyncio,json,os
from pathlib import Path
import unittest
from fastapi import Request,HTTPException
from fastapi.responses import JSONResponse
import httpx
from scripts.tests.test_native_creative_adapter import AdapterTests
from native_studio.creative_session import CreativeSession,CreativeSessionError,decode_bootstrap
from security.native_creative_handoff import CreativeScope

@unittest.skipUnless(os.name=='nt','Controlled Windows identity fixture')
class RedemptionContract(unittest.TestCase):
    def setUp(self):
        self.fixture=AdapterTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        self.invocation=f._invocation();f.owner_pid=self.invocation._pid;f.adapter.register(self.invocation)
        self.scope=CreativeScope('firebase:fixture:owner-a','project-a','revision-a','a'*64,'b'*64)
        grant=f.grants.issue(self.scope,self.invocation,auth_deadline=145)
        self.packet=decode_bootstrap(json.dumps(dict(version=1,grant=grant,project='project-a',revision='revision-a',source_sha256='a'*64,candidate_sha256='b'*64)).encode())
        tree=ast.parse(Path('backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
        node=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='redeem_native_creative');node.decorator_list=[]
        ns=dict(asyncio=asyncio,json=json,Request=Request,JSONResponse=JSONResponse,HTTPException=HTTPException,_NATIVE_CREATIVE_ADAPTER=f.adapter)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-route>','exec'),ns)
        def transport(request):
            async def receive():return dict(type='http.request',body=request.content,more_body=False)
            req=Request(dict(f.http,method='POST',path='/api/screenwriting/native/redeem',query_string=b''),receive)
            try:
                response=asyncio.run(ns['redeem_native_creative'](req))
                return httpx.Response(response.status_code,content=response.body,headers=dict(response.headers))
            except HTTPException as error:return httpx.Response(error.status_code,json={'detail':error.detail})
        self.session=CreativeSession(headers_provider=lambda:{'X-API-Key':'synthetic'},transport=httpx.MockTransport(transport),clock=lambda:f.now)

    def test_redeem_authorize_and_replay_denial_across_contract(self):
        self.fixture.now=125
        self.session.redeem(self.packet)
        lease=self.session.headers(project='project-a',operation='read')['X-AI-BS-Creative-Lease']
        authorized=self.fixture.adapter.resolve(self.fixture.http,lease,project='project-a',operation='read')
        self.assertEqual(authorized.owner,self.scope.owner)
        self.assertEqual(self.session._deadline,145)
        with self.assertRaises(CreativeSessionError):self.session.redeem(self.packet)
        self.assertIsNone(self.session._lease)

    def test_wrong_peer_cannot_redeem_and_correct_peer_can_still_redeem(self):
        self.fixture.owner_pid+=1
        with self.assertRaises(CreativeSessionError):self.session.redeem(self.packet)
        self.fixture.owner_pid=self.invocation._pid
        self.session.redeem(self.packet)

if __name__=='__main__':unittest.main()
