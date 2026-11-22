"""Native PDF intake uses the same retained source/indexed readback as chat."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from native_studio.screenplay_client import ScreenplayClient,ScreenplayError

class NativePdfHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'fixture.pdf';self.path.write_bytes(b'%PDF-1.4\nfixture-source')
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest();self.calls=[]
        self.receipt=dict(source_id='a'*32,source_sha256=self.digest,source_layout_available=True,
            parsing_status='complete',indexing_status='lexical_chunks_indexed',retrieval_status='source_passage_readback_verified')
        self.headers=patch('native_studio.screenplay_client.local_service_headers',return_value={'X-API-Key':'synthetic'});self.headers.start();self.addCleanup(self.headers.stop)

    def client(self):
        def handler(request):
            self.calls.append(request)
            if request.url.path=='/api/chat/attach':return httpx.Response(200,json={'status':'success','file':self.receipt})
            return httpx.Response(200,json={'status':'success','project':'Fixture','source':{'sha256':self.digest}})
        return ScreenplayClient(transport=httpx.MockTransport(handler))

    def test_pdf_upload_then_import_uses_same_hash_and_source(self):
        self.assertEqual(self.client().import_file('Fixture',self.path),'Fixture')
        self.assertEqual([r.url.path for r in self.calls],['/api/chat/attach','/api/screenwriting/projects/import-pdf-source'])
        self.assertIn(self.path.read_bytes(),self.calls[0].content)
        body=json.loads(self.calls[1].content)
        self.assertEqual((body['source_id'],body['source_sha256']),('a'*32,self.digest))

    def test_failed_or_foreign_hash_receipt_never_creates_project(self):
        self.receipt['source_sha256']='0'*64
        with self.assertRaises(ScreenplayError):self.client().import_file('Fixture',self.path)
        self.assertEqual(len(self.calls),1)

    def test_unverified_indexing_does_not_claim_ready(self):
        self.receipt['retrieval_status']='pending'
        with self.assertRaises(ScreenplayError):self.client().import_file('Fixture',self.path)
        self.assertEqual(len(self.calls),1)

    def test_generic_pdf_requires_explicit_text_working_copy(self):
        self.receipt['source_layout_available']=False
        with self.assertRaisesRegex(ScreenplayError,'working copy'):self.client().import_file('Fixture',self.path)
        self.assertEqual(len(self.calls),1)

    def test_text_working_copy_parses_captured_upload_bytes_after_file_mutation(self):
        captured=self.path.read_bytes();self.receipt['source_layout_available']=False;parsed=[]
        def handler(request):
            self.calls.append(request)
            if request.url.path=='/api/chat/attach':
                self.assertIn(captured,request.content)
                self.path.write_bytes(b'%PDF-1.4\nREPLACED_FILE_TEXT')
                return httpx.Response(200,json={'status':'success','file':self.receipt})
            body=json.loads(request.content);self.assertEqual(body['content'],'Original captured text.')
            return httpx.Response(200,json={'status':'success','project':'Fixture'})
        def reader(stream):
            raw=stream.read() if hasattr(stream,'read') else Path(stream).read_bytes();parsed.append(raw)
            return SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda:'Original captured text.' if raw==captured else 'Wrong replacement text.')])
        with patch('pypdf.PdfReader',side_effect=reader):
            result=ScreenplayClient(transport=httpx.MockTransport(handler)).import_file('Fixture',self.path,pdf_mode='text_working_copy')
        self.assertEqual(result,'Fixture');self.assertEqual(parsed,[captured]);self.assertNotEqual(self.path.read_bytes(),captured)
        self.assertEqual([r.url.path for r in self.calls],['/api/chat/attach','/api/screenwriting/projects/import'])

    def test_generic_text_extraction_failure_preserves_source_and_creates_no_project(self):
        before=self.path.read_bytes();self.receipt['source_layout_available']=False
        for value in (None,''):
            self.calls.clear()
            reader=patch('pypdf.PdfReader',side_effect=ValueError('synthetic PDF failure')) if value is None else patch('pypdf.PdfReader',return_value=SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda:'')]))
            with reader,self.assertRaises(ScreenplayError):self.client().import_file('Fixture',self.path,pdf_mode='text_working_copy')
            self.assertEqual(len(self.calls),1);self.assertEqual(self.path.read_bytes(),before)

if __name__=='__main__':unittest.main()
