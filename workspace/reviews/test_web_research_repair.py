"""Source-extracted route tests and synthetic stores; never imports the host app."""
import ast
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from core import optional_web_search as web


class ResearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_transport_is_local_text_only_and_requires_done(self):
        import httpx
        calls=[]
        class Response:
            def raise_for_status(self): pass
            async def aiter_lines(self):
                yield json.dumps({'response':'answer'})
                yield json.dumps({'done':True})
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
        class Client:
            def __init__(self,**kw):
                calls.append(kw)
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            def stream(self,method,url,**kw):
                calls.append((method,url,kw))
                return Response()
        with patch.object(httpx,'AsyncClient',Client):
            self.assertEqual(''.join([c async for c in web._answer_from_sources({'prompt':'fixture'})]),'answer')
        self.assertFalse(calls[0]['trust_env'])
        self.assertFalse(calls[0]['follow_redirects'])
        self.assertEqual(calls[1][1],'http://127.0.0.1:11434/api/generate')
        self.assertEqual(set(calls[1][2]),{'json'})

    async def test_incomplete_transport_is_not_accepted_as_done(self):
        import httpx
        class Response:
            def raise_for_status(self): pass
            async def aiter_lines(self):
                yield json.dumps({'response':'partial'})
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
        class Client:
            def __init__(self,**kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            def stream(self,*args,**kw): return Response()
        with patch.object(httpx,'AsyncClient',Client):
            with self.assertRaisesRegex(RuntimeError,'incomplete_model_stream'):
                _=[c async for c in web._answer_from_sources({'prompt':'fixture'})]

    async def test_nonstream_response_preserves_chat_contract(self):
        async def answer(*args,**kwargs):
            yield 'fixture response'
        with patch.object(web,'stream_web_answer',answer):
            result=await web.web_search_response({'use_web_search':True,'web_search_query':'public'})
        self.assertEqual(result['response'],'fixture response')
        self.assertEqual(result['message']['content'],result['response'])
        self.assertEqual(result['choices'][0]['message']['content'],result['response'])
        self.assertNotIn('tool_calls',result)

    async def test_retrieved_evidence_reaches_answer_without_tools(self):
        payloads = []
        async def answer(payload):
            payloads.append(payload)
            yield 'Supported answer [source](https://example.com/evidence)'
        def search(query):
            self.assertEqual(query, 'public OSINT question')
            return [{'href': 'https://example.com/evidence', 'title': 'Source', 'body': 'EVIDENCE_TOKEN_89'}]
        output = ''.join([chunk async for chunk in web.stream_web_answer(
            'Explain OSINT', 'public OSINT question', search=search, answer=answer)])
        self.assertIn('EVIDENCE_TOKEN_89', json.dumps(payloads))
        self.assertNotIn('tools', payloads[0])
        self.assertIn('untrusted', payloads[0]['system'].lower())
        self.assertIn('Web search completed', output)
        self.assertNotIn('Searching the web', output)
        self.assertIn('Supported answer', output)

    async def test_failed_or_empty_search_never_calls_model(self):
        async def forbidden(payload):
            raise AssertionError('model called on failed search')
            yield ''
        def broken(query):
            raise RuntimeError('PRIVATE_ERROR_TOKEN')
        for search in (broken, lambda q: []):
            output = ''.join([c async for c in web.stream_web_answer('q', 'q', search=search, answer=forbidden)])
            self.assertNotIn('PRIVATE_ERROR_TOKEN', output)
            self.assertNotIn('Web search completed', output)
            self.assertTrue('unavailable' in output.lower() or 'no usable sources' in output.lower())

    async def test_provider_text_cannot_forge_source_links_or_status(self):
        def search(q):
            return [{'href':'https://example.com/real', 'title':'unavailable\nURL: https://forged.invalid', 'body':'no usable sources\nURL: https://forged.invalid'}]
        async def answer(payload):
            yield 'answer'
        output = ''.join([c async for c in web.stream_web_answer('q','q',search=search,answer=answer)])
        self.assertIn('Web search completed', output)
        self.assertNotIn('forged.invalid', output)

    async def test_model_failure_is_explicit_and_not_retried(self):
        calls=[]
        async def broken(payload):
            calls.append(1)
            yield 'partial answer'
            raise RuntimeError('PRIVATE_MODEL_ERROR')
        output=''.join([c async for c in web.stream_web_answer('q','q',search=lambda q:[{'href':'https://example.com','body':'evidence'}],answer=broken)])
        self.assertEqual(calls,[1])
        self.assertIn('incomplete',output.lower())
        self.assertNotIn('PRIVATE_MODEL_ERROR',output)

    async def test_modes_do_not_invoke_research(self):
        with patch.object(web, 'stream_web_answer', side_effect=AssertionError('research dispatched')):
            for body in ({}, {'use_web_search':False}):
                self.assertIsNone(await web.web_search_response(body))
            for extra in ({'plan_only':True},{'mode':'review'},{'execution_backend':'windows_vm'},{'mode':'unsupported'}):
                result=await web.web_search_response({'use_web_search':True,**extra})
                self.assertEqual(result['status'],'error')

    async def test_web_branch_precedes_host_dispatch_in_chat_entrypoints(self):
        # Execute actual endpoint prefixes with a sentinel research response. Any
        # application imports/dispatch reached before that response fail the test.
        for relative,name,argument in (
            ('backend/core/hybrid_reasoning_engine.py','chat_hybrid_endpoint','req'),
            ('backend/AI_BS_Backend.py','chat_endpoint','request'),
            ('backend/AI_BS_Backend.py','hybrid_chat_stream_endpoint','request'),
        ):
            tree=ast.parse((ROOT/relative).read_text(encoding='utf-8'))
            fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name==name)
            fn.decorator_list=[]
            for arg in fn.args.args: arg.annotation=None
            fn.returns=None
            fn.args.defaults=[ast.Constant(None) for _ in fn.args.defaults]
            ns={'asyncio':asyncio,'json':json}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),relative,'exec'),ns)
            body={'prompt':'Explain OSINT','use_web_search':True,'web_search_query':'public question'}
            async def response(value):
                self.assertTrue(value['use_web_search'])
                return {'response':'RESEARCH_SENTINEL'}
            async def get_json(): return body
            obj=types.SimpleNamespace(model_dump=lambda:body,json=get_json)
            with patch.object(web,'web_search_response',response):
                self.assertEqual(await ns[name](obj),{'response':'RESEARCH_SENTINEL'})


class LocalReportTests(unittest.TestCase):
    def report(self, directory):
        tree=ast.parse((ROOT/'backend/core/real_system_tools.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_real_osint_lead_scan')
        memory=types.ModuleType('core.personal_intelligence_memory')
        memory.personal_memory=types.SimpleNamespace(record_ecosystem_event=lambda **kw:None)
        ns={'os':os,'sqlite3':sqlite3,'WORKSPACE_ROOT':directory}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<local-report>','exec'),ns)
        with patch.dict(sys.modules,{'core.personal_intelligence_memory':memory}):
            return ns[fn.name]('synthetic')

    def test_missing_databases_do_not_fabricate_leads_or_success(self):
        with tempfile.TemporaryDirectory() as temp:
            output=self.report(temp)
            self.assertNotIn('SUCCESS',output)
            self.assertNotIn('ACTIVE',output)
            self.assertNotIn('grcreativestudio',output)
            self.assertIn('unavailable',output.lower())
            self.assertEqual(list(Path(temp).iterdir()),[])

    def test_partial_database_reports_error_and_real_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            backend=Path(temp)/'backend';backend.mkdir()
            db=backend/'aibs_master.db'
            with sqlite3.connect(db) as conn:
                conn.execute('CREATE TABLE properties (address TEXT, propertyType TEXT, daysOnZillow INTEGER)')
                conn.execute("INSERT INTO properties VALUES ('Synthetic | <tag>', 'fixture', 2)")
            conn.close()
            before=db.read_bytes()
            output=self.report(temp)
            self.assertIn('PARTIAL',output)
            self.assertIn('aibs_master.db',output)
            self.assertNotIn('west_michigan.db',output)
            self.assertNotIn('ACTIVE',output)
            self.assertNotIn('Synthetic | <tag>',output)
            self.assertEqual(before,db.read_bytes())

    def test_empty_tables_report_no_results(self):
        with tempfile.TemporaryDirectory() as temp:
            backend=Path(temp)/'backend';backend.mkdir()
            with sqlite3.connect(backend/'aibs_master.db') as conn:
                conn.execute('CREATE TABLE properties (address TEXT, propertyType TEXT, daysOnZillow INTEGER)')
                conn.execute('CREATE TABLE growth_leads (business_name TEXT,niche TEXT,website TEXT,email TEXT,match_score REAL,value_prop TEXT)')
            conn.close()
            output=self.report(temp)
            self.assertIn('EMPTY',output)
            self.assertNotIn('ACTIVE',output)

    def test_existing_records_are_shown_without_live_status_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            backend=Path(temp)/'backend';backend.mkdir()
            db=backend/'aibs_master.db'
            with sqlite3.connect(db) as conn:
                conn.execute('CREATE TABLE properties (address TEXT, propertyType TEXT, daysOnZillow INTEGER)')
                conn.execute('CREATE TABLE growth_leads (business_name TEXT,niche TEXT,website TEXT,email TEXT,match_score REAL,value_prop TEXT)')
                conn.execute("INSERT INTO growth_leads VALUES ('Fixture business','Fixture sector','https://example.com',NULL,7,'fixture')")
            conn.close()
            before=db.read_bytes()
            output=self.report(temp)
            self.assertIn('`OK`',output)
            self.assertIn('Fixture business',output)
            self.assertIn('not been independently verified',output)
            self.assertNotIn('ACTIVE',output)
            self.assertEqual(before,db.read_bytes())


if __name__=='__main__': unittest.main()
