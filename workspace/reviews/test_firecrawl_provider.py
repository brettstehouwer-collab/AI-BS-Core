import asyncio
import importlib.util
import json
import os
import sys
import types
from pathlib import Path
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[2]/'backend/core/optional_web_search.py'
spec=importlib.util.spec_from_file_location('firecrawl_adapter_under_test',PATH)
web=importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


class FirecrawlTests(unittest.TestCase):
    def setUp(self):
        # A missing provider implementation must fail without contacting DDGS.
        dummy=types.ModuleType('ddgs')
        def forbidden(*args,**kwargs): raise AssertionError('unexpected DDGS fallback')
        dummy.DDGS=forbidden
        patcher=patch.dict(sys.modules,{'ddgs':dummy})
        patcher.start()
        self.addCleanup(patcher.stop)

    def client(self, document, status=200):
        calls=[]
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def raise_for_status(self):
                if status!=200: raise RuntimeError('PRIVATE_PROVIDER_DETAIL')
            def iter_bytes(self):
                if isinstance(document,bytes): yield document
                else: yield json.dumps(document).encode()
        class Client:
            def __init__(self,**kwargs): calls.append(kwargs)
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def stream(self,method,url,**kwargs):
                calls.append((method,url,kwargs))
                return Response()
        return Client,calls

    def test_default_remains_ddgs(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(web.search_provider_status(),{'provider':'ddgs','configured':True})

    def test_missing_key_makes_no_request(self):
        import httpx
        with patch.dict(os.environ,{'AIBS_WEB_SEARCH_PROVIDER':'firecrawl'},clear=True),patch.object(httpx,'Client',side_effect=AssertionError('network used')):
            self.assertEqual(web.search_provider_status(),{'provider':'firecrawl','configured':False})
            with self.assertRaisesRegex(ValueError,'not configured'): web._search('public query')

    def test_fixed_api_origin_auth_limits_and_page_text(self):
        import httpx
        client,calls=self.client({'success':True,'data':{'web':[{'url':'https://example.com/docs','title':'Docs','description':'snippet','markdown':'Retrieved page text'}]}})
        with patch.dict(os.environ,{'AIBS_WEB_SEARCH_PROVIDER':'firecrawl','FIRECRAWL_API_KEY':'fixture-secret'},clear=True),patch.object(httpx,'Client',client):
            rows=web._search('Public question')
        self.assertEqual(rows[0]['body'],'Retrieved page text')
        self.assertEqual(rows[0]['href'],'https://example.com/docs')
        self.assertEqual(calls[1][1],'https://api.firecrawl.dev/v2/search')
        self.assertFalse(calls[0]['follow_redirects'])
        self.assertFalse(calls[0]['trust_env'])
        request=calls[1][2]
        self.assertEqual(request['headers']['Authorization'],'Bearer fixture-secret')
        self.assertEqual(request['json']['query'],'Public question')
        self.assertEqual(request['json']['limit'],3)
        self.assertEqual(request['json']['sources'],['web'])
        self.assertEqual(request['json']['scrapeOptions']['formats'],['markdown'])
        self.assertNotIn('fixture-secret',json.dumps(rows))

    def test_provider_errors_are_not_exposed_or_silently_fallback(self):
        import httpx
        for status,doc in [(401,{}),(429,{}),(200,{'success':False,'error':'fixture-secret'}),(200,{'success':True,'data':{}})]:
            client,calls=self.client(doc,status)
            with patch.dict(os.environ,{'AIBS_WEB_SEARCH_PROVIDER':'firecrawl','FIRECRAWL_API_KEY':'fixture-secret'},clear=True),patch.object(httpx,'Client',client):
                result=asyncio.run(web.retrieve_web_sources('public query'))
            self.assertEqual(result['status'],'unavailable')
            self.assertNotIn('fixture-secret',json.dumps(result))
            self.assertEqual(len(calls),2)

    def test_oversized_response_is_rejected(self):
        import httpx
        client,_=self.client(b'x'*(2*1024*1024+1))
        with patch.dict(os.environ,{'AIBS_WEB_SEARCH_PROVIDER':'firecrawl','FIRECRAWL_API_KEY':'fixture-secret'},clear=True),patch.object(httpx,'Client',client):
            with self.assertRaisesRegex(ValueError,'too large'):web._search('public')

    def test_unsupported_provider_never_sends_query(self):
        with patch.dict(os.environ,{'AIBS_WEB_SEARCH_PROVIDER':'unknown'},clear=True):
            result=asyncio.run(web.retrieve_web_sources('public'))
            self.assertEqual(result['status'],'unavailable')

    def test_bad_rows_do_not_remove_valid_results(self):
        import httpx
        client,_=self.client({'success':True,'data':{'web':[None,{'url':'javascript:bad','markdown':'bad'},{'url':'https://example.com','description':'Useful snippet'}]}})
        with patch.dict(os.environ,{'AIBS_WEB_SEARCH_PROVIDER':'firecrawl','FIRECRAWL_API_KEY':'fixture-secret'},clear=True),patch.object(httpx,'Client',client):
            result=asyncio.run(web.retrieve_web_sources('public'))
        self.assertEqual(result['status'],'ok')
        self.assertEqual(len(result['sources']),1)
        self.assertEqual(result['sources'][0]['excerpt'],'Useful snippet')


if __name__=='__main__': unittest.main()
