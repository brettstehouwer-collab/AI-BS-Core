"""Actual owner-dependency definitions; synthetic ASGI requests and adapter only."""
import ast,asyncio,sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi import HTTPException,Request
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))

class OwnerDependency(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree=ast.parse(Path('backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
        nodes=[x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name in ('_native_creative_owner','_screenwriting_owner_scope')]
        self.ns=dict(Request=Request,HTTPException=HTTPException,asyncio=asyncio,_NATIVE_CREATIVE_ADAPTER=None)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-owner-dependency>','exec'),self.ns)

    def request(self,headers,path='/api/screenwriting/read'):
        return Request(dict(type='http',method='GET',path=path,query_string=b'project_name=fixture',headers=headers,server=('127.0.0.1',8080),client=('127.0.0.1',123)))

    async def test_unconfigured_or_invalid_lease_never_falls_back(self):
        for headers in ([ (b'x-ai-bs-creative-lease',b'') ],[(b'x-ai-bs-creative-lease',b'synthetic')]):
            with self.assertRaises(HTTPException):await self.ns['_native_creative_owner'](self.request(headers))

    async def test_resolver_gets_explicit_resource_and_operation(self):
        calls=[]
        def resolve(scope,lease,**kw):calls.append((lease,kw));return SimpleNamespace(owner='firebase:test:owner')
        self.ns['_NATIVE_CREATIVE_ADAPTER']=SimpleNamespace(resolve=resolve)
        owner=await self.ns['_native_creative_owner'](self.request([(b'x-ai-bs-creative-ase',b'ignored'),(b'x-ai-bs-creative-lease',b'synthetic')]))
        self.assertEqual(owner,'firebase:test:owner')
        self.assertEqual(calls,[('synthetic',{'project':'fixture','operation':'read'})])

    async def test_duplicate_lease_and_other_operations_fail(self):
        self.ns['_NATIVE_CREATIVE_ADAPTER']=object()
        for req in (self.request([(b'x-ai-bs-creative-lease',b'a')]*2),self.request([(b'x-ai-bs-creative-lease',b'a')],'/api/screenwriting/projects')):
            with self.assertRaises(HTTPException):await self.ns['_native_creative_owner'](req)

    async def test_verified_lease_owner_is_bound_and_reset_without_admin_fallback(self):
        from core.personal_memory_scope import current_memory_principal
        self.ns['_NATIVE_CREATIVE_ADAPTER']=SimpleNamespace(resolve=lambda *a,**kw:SimpleNamespace(owner='firebase:test:owner'))
        before=current_memory_principal()
        stream=self.ns['_screenwriting_owner_scope'](self.request([(b'x-ai-bs-creative-lease',b'synthetic')]))
        with patch('security.firebase_auth.get_admin_principal',side_effect=AssertionError('No fallback')):
            self.assertEqual(await anext(stream),'firebase:test:owner')
            self.assertEqual(current_memory_principal(),'firebase:test:owner')
            await stream.aclose()
        self.assertEqual(current_memory_principal(),before)

if __name__=='__main__':unittest.main()
