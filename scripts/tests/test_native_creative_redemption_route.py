"""Actual redemption body with synthetic request/adapter; no mounted auth claim."""
import ast,asyncio,json
from pathlib import Path
from types import SimpleNamespace
import unittest
from fastapi import HTTPException,Request
from fastapi.responses import JSONResponse

class RedemptionRoute(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree=ast.parse(Path('backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
        node=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='redeem_native_creative')
        node.decorator_list=[]
        self.calls=[]
        def redeem(scope,grant):self.calls.append(grant);return {'lease':'synthetic'}
        self.ns=dict(asyncio=asyncio,json=json,Request=Request,JSONResponse=JSONResponse,HTTPException=HTTPException,_NATIVE_CREATIVE_ADAPTER=SimpleNamespace(redeem=redeem))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-redemption-route>','exec'),self.ns)

    def request(self,body):
        async def receive():return dict(type='http.request',body=body,more_body=False)
        return Request(dict(type='http',method='POST',path='/api/screenwriting/native/redeem',headers=[]),receive)

    async def test_valid_grant_body_and_no_store_response(self):
        grant='nch_g_'+'a'*43
        response=await self.ns['redeem_native_creative'](self.request(json.dumps({'grant':grant}).encode()))
        self.assertEqual(self.calls,[grant]);self.assertEqual(response.headers['cache-control'],'no-store')

    async def test_invalid_ambiguous_and_oversize_bodies_never_redeem(self):
        for body in (b'x'*4097,b'{"grant":"a","grant":"b"}',b'{}',b'{"grant":true}',b'{"grant":"bad","owner":"forged"}'):
            with self.assertRaises(HTTPException):await self.ns['redeem_native_creative'](self.request(body))
        self.assertEqual(self.calls,[])

    async def test_unconfigured_adapter_denies(self):
        self.ns['_NATIVE_CREATIVE_ADAPTER']=None
        with self.assertRaises(HTTPException):await self.ns['redeem_native_creative'](self.request(b'{}'))

    async def test_oversize_stream_stops_before_consuming_more_input(self):
        consumed=[]
        class Streaming:
            scope={}
            async def stream(self):
                yield b'x'*4097
                consumed.append('beyond-limit')
                yield b'x'
        with self.assertRaises(HTTPException):await self.ns['redeem_native_creative'](Streaming())
        self.assertEqual(consumed,[])
        self.assertEqual(self.calls,[])

    async def test_excessively_nested_body_is_sanitized(self):
        body=b'['*1500+b'0'+b']'*1500
        with self.assertRaises(HTTPException) as error:
            await self.ns['redeem_native_creative'](self.request(body))
        self.assertEqual(error.exception.status_code,403)
        self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
