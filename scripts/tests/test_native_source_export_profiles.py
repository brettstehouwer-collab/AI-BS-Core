"""Native client against actual PDF-source route bodies and disposable files."""
import hashlib,json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs
import httpx
from fastapi import HTTPException
from scripts.tests.test_chat_pdf_workflow import PdfWorkflowFixture,OWNER
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from native_studio.screenplay_client import ScreenplayClient,ScreenplayError

class NativeSourceExports(unittest.TestCase):
    def setUp(self):
        self.fixture=PdfWorkflowFixture()
        self.fixture._setupAsyncioRunner()
        self.addCleanup(self.fixture._tearDownAsyncioRunner)
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        source=self.fixture.stage();self.imported=self.fixture.import_source(source)
        self.name=self.imported['project'];self.directory=self.fixture.projects/self.name
        self.routes=self.fixture.router_scope();self.calls=[]
        self.principal=bind_memory_principal(OWNER);self.addCleanup(reset_memory_principal,self.principal)
        def handle(request):
            query=dict(request.url.params);self.calls.append((request.url.path,query))
            try:
                if request.url.path.endswith('/read'):
                    return httpx.Response(200,json=self.routes['read_screenplay'](query['project_name']))
                fmt=request.url.path.rsplit('/',1)[-1]
                response=self.routes['export_'+fmt](**query)
                return httpx.Response(response.status_code,content=response.body,headers=dict(response.headers))
            except HTTPException as error:return httpx.Response(error.status_code,json={'detail':str(error.detail)})
        self.client=ScreenplayClient(transport=httpx.MockTransport(handle))
        auth=patch('native_studio.screenplay_client.local_service_headers',return_value={'X-API-Key':'synthetic'})
        auth.start();self.addCleanup(auth.stop)

    def test_edited_source_requires_explicit_reflow_and_preserves_original_artifacts(self):
        paths=('original.pdf','source_packet.json','source_exports/layout.fdx','source_exports/layout.pdf')
        original={n:(self.directory/n).read_bytes() for n in paths}
        before=self.client.read(self.name)
        changed=before['content']+'\nINT. FIXTURE - DAY\nAn edited native export line.\n'
        saved=self.routes['write_screenplay'](SimpleNamespace(project_name=self.name,content=changed,
            expected_revision=before['revision'],expected_workflow_revision=0,preserve_unchanged_bytes=True))
        for fmt in ('fdx','pdf'):
            with self.assertRaises(ScreenplayError):self.client.export(self.name,fmt,saved['revision'])
            self.assertIsNone(self.calls[-1][1].get('layout'))
        fdx=self.client.export(self.name,'fdx',saved['revision'],layout='reflow')
        self.assertIn(b'An edited native export line.',fdx)
        pdf=self.client.export(self.name,'pdf',saved['revision'],layout='reflow')
        import fitz
        with fitz.open(stream=pdf,filetype='pdf') as document:
            self.assertGreater(len(document),0)
            self.assertIn('An edited native export line.',' '.join(p.get_text() for p in document))
        self.assertEqual(original,{n:(self.directory/n).read_bytes() for n in paths})

    def test_invalid_profile_fails_before_any_request(self):
        for fmt,layout in [('pdf','unknown'),('fountain','reflow'),('other',None)]:
            with self.assertRaises(ScreenplayError):self.client.export(self.name,fmt,'r',layout=layout)
        self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
