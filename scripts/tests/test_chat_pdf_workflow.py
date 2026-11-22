"""Actual intake and source-project contracts using synthetic PDFs/stores only."""
import ast
import asyncio
from contextlib import closing
import hashlib
import importlib
import inspect
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime
from typing import Optional
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch, Mock
import uuid
import xml.etree.ElementTree as ET

from fastapi import Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.tests.test_screenplay_pdf import make_fixture
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal

OWNER = 'firebase:pdf-workflow-fixture:owner'
OTHER = 'firebase:pdf-workflow-fixture:other'


class PdfWorkflowFixture(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='pdf-workflow-', dir=ROOT / 't')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.uploads, self.projects = self.root / 'uploads', self.root / 'projects'
        self.uploads.mkdir()
        self.projects.mkdir()
        self.db = self.root / 'vault.sqlite'
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute('CREATE TABLE vault_items(id INTEGER PRIMARY KEY AUTOINCREMENT,'
                'title TEXT,content TEXT,collection TEXT,tags TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,item_hash TEXT)')
        try:
            self.bridge = importlib.import_module('core.chat_pdf_sources')
        except ModuleNotFoundError:
            self.bridge = None
        if self.bridge is not None:
            for name, value in (('CACHE_ROOT', self.root / 'pdf-cache'), ('VAULT_DB_PATH', self.db)):
                setting = patch.object(self.bridge, name, value)
                setting.start()
                self.addCleanup(setting.stop)
        source = ROOT / 'backend/AI_BS_Backend.py'
        function = next(node for node in ast.parse(source.read_text(encoding='utf-8-sig')).body
                        if getattr(node, 'name', '') == 'chat_attach_file')
        function.decorator_list = []
        namespace = dict(Request=Request, UploadFile=UploadFile, File=File, HTTPException=HTTPException,
            JSONResponse=JSONResponse, os=os, asyncio=asyncio, re=re, UPLOAD_ATTACHMENTS_DIR=str(self.uploads))
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        self.attach = namespace['chat_attach_file']

    async def upload(self, filename, raw, owner=OWNER):
        from routers import conversation_router
        async def authenticated(request):
            if owner is None:
                raise HTTPException(403, 'Synthetic denied account')
            return owner
        upload = UploadFile(filename=filename, file=io.BytesIO(raw))
        with patch.object(conversation_router, 'require_conversation_owner', authenticated):
            arguments = dict(file=upload)
            if 'request' in inspect.signature(self.attach).parameters:
                arguments['request'] = SimpleNamespace(headers={})
            return await self.attach(**arguments)

    async def test_pdf_intake_returns_verified_source_reference_not_entire_text(self):
        raw = make_fixture()
        result = await self.upload('fixture.pdf', raw)
        self.assertIsInstance(result, dict)
        item = result['file']
        self.assertIn('source_id', item)
        self.assertEqual(item['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(item['page_count'], 3)
        self.assertEqual(item['indexing_status'], 'lexical_chunks_indexed')
        self.assertEqual(item['retrieval_status'], 'source_passage_readback_verified')
        self.assertNotIn('First wrapped dialogue line', item['content'])
        self.assertLess(len(item['content']), 500)

    async def test_pdf_extraction_failure_is_not_success(self):
        result = await self.upload('broken.pdf', b'%PDF-invalid synthetic fixture')
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 422)
        body = json.loads(result.body)
        self.assertTrue(body['original_retained'])

    async def test_same_name_non_pdf_uploads_never_overwrite(self):
        first = await self.upload('same.txt', b'first original')
        second = await self.upload('same.txt', b'second original')
        self.assertNotEqual(first['file']['path'], second['file']['path'])
        self.assertEqual(Path(first['file']['path']).read_bytes(), b'first original')
        self.assertEqual(Path(second['file']['path']).read_bytes(), b'second original')

    def stage(self, owner=OWNER):
        return self.bridge.stage_pdf(make_fixture(), owner, 'synthetic.pdf')

    def router_scope(self):
        from routers.conversation_router import require_conversation_owner
        source = ROOT / 'backend/routers/screenwriting_router.py'
        names = {'_project_directory', '_existing_project_directory', '_atomic_project_text',
            '_read_project_metadata', '_write_project_metadata', '_screenplay_snapshot',
            '_workflow_call', '_workflow_project', '_require_screenplay_revision', '_require_idle_adaptation',
            '_write_screenplay', 'read_screenplay', 'write_screenplay', 'list_projects',
            '_archive_entry', 'delete_project', 'list_project_archives', 'restore_project',
            'switch_project', 'do_import_project', '_screenplay_export_source', 'export_fdx', 'export_pdf',
            'import_pdf_source_project', '_screenwriting_owner_scope'}
        selected = [node for node in ast.parse(source.read_text(encoding='utf-8-sig')).body
                    if getattr(node, 'name', '') in names]
        for node in selected:
            if hasattr(node, 'decorator_list'):
                node.decorator_list = []
        namespace = dict(Path=Path, HTTPException=HTTPException, Response=Response,
            hashlib=hashlib, json=json, os=os, tempfile=tempfile, datetime=datetime,
            Optional=Optional, uuid=uuid, SCREENPLAY_ROOT=self.projects,
            _PROJECT_STORE_LOCK=threading.RLock(), _current_project='Default Project', ADAPTATION_TASKS={},
            Request=Request, Depends=Depends, require_conversation_owner=require_conversation_owner, asyncio=asyncio)
        for model in ('WriteScreenplayPayload', 'SwitchProjectPayload', 'RestoreProjectPayload',
                      'ImportProjectPayload', 'ImportPdfSourcePayload'):
            namespace[model] = object
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        return namespace

    def import_source(self, receipt, name='Private PDF', request_id=None):
        return self.bridge.import_project(self.projects / name, OWNER, receipt['source_id'],
                                         receipt['source_sha256'], request_id or uuid.uuid4().hex)

    def test_create_only_import_idempotent_and_request_conflicts_preserve_projects(self):
        source = self.stage()
        request = uuid.uuid4().hex
        first = self.import_source(source, request_id=request)
        retry = self.import_source(source, request_id=request)
        self.assertEqual(first['revision'], retry['revision'])
        self.assertTrue(retry['idempotent'])
        original = (self.projects / 'Private PDF/original.pdf').read_bytes()
        with self.assertRaises(self.bridge.PDFSourceError):
            self.import_source(source, name='Other Name', request_id=request)
        self.assertFalse((self.projects / 'Other Name').exists())
        self.assertEqual((self.projects / 'Private PDF/original.pdf').read_bytes(), original)
        with self.assertRaises(self.bridge.PDFSourceError):
            self.import_source(source, request_id=uuid.uuid4().hex)

    def test_failed_publication_retains_stage_and_same_request_can_retry(self):
        source = self.stage()
        request = uuid.uuid4().hex
        with patch.object(self.bridge.os, 'rename', side_effect=PermissionError('synthetic publication interruption')):
            with self.assertRaises(PermissionError):
                self.import_source(source, request_id=request)
        self.assertFalse((self.projects / 'Private PDF').exists())
        result = self.import_source(source, request_id=request)
        self.assertEqual(result['status'], 'success')
        self.assertEqual((self.projects / 'Private PDF/original.pdf').read_bytes(), make_fixture())

    def test_partial_file_publish_preserves_temp_and_retry_publishes_complete_target(self):
        directory = self.root / 'atomic'
        directory.mkdir()
        target = directory / 'complete.bin'
        with patch.object(self.bridge.os, 'fsync', side_effect=OSError('synthetic flush interruption')):
            with self.assertRaises(OSError):
                self.bridge._write_once(target, b'complete fixture bytes')
        self.assertFalse(target.exists())
        retained = list(directory.glob('.pdf-publish-*.tmp'))
        self.assertTrue(retained)
        self.bridge._write_once(target, b'complete fixture bytes')
        self.assertEqual(target.read_bytes(), b'complete fixture bytes')
        self.assertTrue(all(path.exists() for path in retained))

    def test_linked_write_ancestor_is_rejected_before_outside_mutation(self):
        outside = self.root / 'outside'
        outside.mkdir()
        linked = self.root / 'linked'
        # Patch only classification, not writes: this models the Windows
        # junction predicate without requiring symbolic-link privilege.
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda path: path == linked or original(path)):
            with self.assertRaises(self.bridge.PDFSourceError):
                self.bridge._write_once(linked / 'source_exports/file.bin', b'new')
        self.assertFalse(linked.exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_pdf_cache_and_project_owner_tamper_guards(self):
        source = self.stage()
        with self.assertRaises(self.bridge.PDFSourceError) as foreign:
            self.bridge.read_source(OTHER, source['source_id'], source['source_sha256'])
        self.assertEqual(foreign.exception.status, 404)
        result = self.import_source(source)
        directory = self.projects / result['project']
        with self.assertRaises(self.bridge.PDFSourceError) as denied:
            self.bridge.source_project_view(directory, result['revision'], owner=OTHER)
        self.assertEqual(denied.exception.status, 403)
        (directory / 'original.pdf').write_bytes(b'synthetic changed source')
        with self.assertRaises(self.bridge.PDFSourceError):
            self.bridge.source_project_view(directory, result['revision'], owner=OWNER)

    def test_export_cas_edited_mode_and_immutable_original_exports(self):
        source = self.stage()
        result = self.import_source(source)
        directory = self.projects / result['project']
        preserved = self.bridge.source_export(directory, result['revision'], 'pdf', 'source',
            owner=OWNER, expected_revision=result['revision'])
        self.assertTrue(preserved.startswith(b'%PDF-'))
        for expected, code in ((None, 428), ('stale', 409)):
            with self.assertRaises(self.bridge.PDFSourceError) as caught:
                self.bridge.source_export(directory, result['revision'], 'pdf', 'source',
                    owner=OWNER, expected_revision=expected)
            self.assertEqual(caught.exception.status, code)
        canonical = directory / 'screenplay.fountain'
        canonical.write_bytes(canonical.read_bytes() + b'\nA deliberate edit.\n')
        changed = hashlib.sha256(canonical.read_bytes()).hexdigest()
        with self.assertRaises(self.bridge.PDFSourceError) as caught:
            self.bridge.source_export(directory, changed, 'pdf', 'source', owner=OWNER, expected_revision=changed)
        self.assertEqual(caught.exception.status, 409)
        self.assertIsNone(self.bridge.source_export(directory, changed, 'pdf', 'reflow', owner=OWNER, expected_revision=changed))
        view = self.bridge.source_project_view(directory, changed, owner=OWNER)
        self.assertFalse(view['source_layout_preserved'])
        self.assertNotIn('body_ast', view)
        self.assertEqual((directory / 'source_exports/layout.pdf').read_bytes(), preserved)

    def professional_engine(self):
        engine=ModuleType('core.screenplay_professional')
        engine.to_professional_fdx=Mock(return_value=b'<?xml version="1.0"?><FinalDraft><Content/></FinalDraft>')
        engine.to_professional_pdf=Mock(return_value=b'%PDF-1.4 synthetic professional')
        engine.professional_profile_receipt=Mock(return_value={
            'profile_id':'us-spec-courier12-v1','renderer_id':'synthetic-professional-v1',
            'natural_pagination':True,'source_page_count_is_target':False})
        return engine

    def test_explicit_professional_route_returns_profile_sha_without_writing_source(self):
        source=self.stage();result=self.import_source(source);directory=self.projects/result['project']
        before={path.relative_to(directory).as_posix():path.read_bytes() for path in directory.rglob('*') if path.is_file()}
        engine=self.professional_engine()
        with patch.dict(sys.modules,{'core.screenplay_professional':engine}):
            value=self.bridge.source_export(directory,result['revision'],'fdx','professional',owner=OWNER,expected_revision=result['revision'])
            self.assertEqual(value,engine.to_professional_fdx.return_value)
            engine.to_professional_fdx.assert_called_once()
            packet=engine.to_professional_fdx.call_args.args[0]
            self.assertEqual(packet['source_sha256'],source['source_sha256'])
            token=bind_memory_principal(OWNER)
            try: response=self.router_scope()['export_fdx'](directory.name,'professional',result['revision'])
            finally: reset_memory_principal(token)
            self.assertEqual(response.headers['X-AI-BS-Layout'],'professional')
            self.assertEqual(response.headers['X-AI-BS-Profile'],'us-spec-courier12-v1')
            self.assertEqual(response.headers['X-AI-BS-Renderer'],'synthetic-professional-v1')
            self.assertEqual(response.headers['X-AI-BS-Artifact-SHA256'],hashlib.sha256(response.body).hexdigest())
            self.assertIn('.professional-us-spec-courier12-v1.fdx',response.headers['Content-Disposition'])
        self.assertEqual(before,{path.relative_to(directory).as_posix():path.read_bytes() for path in directory.rglob('*') if path.is_file()})

    def test_professional_never_uses_packet_for_edited_stale_foreign_or_tampered_source(self):
        source=self.stage();result=self.import_source(source);directory=self.projects/result['project'];engine=self.professional_engine()
        before={path.relative_to(directory).as_posix():path.read_bytes() for path in directory.rglob('*') if path.is_file()}
        with patch.dict(sys.modules,{'core.screenplay_professional':engine}):
            for owner,expected,revision,status in [(OTHER,result['revision'],result['revision'],403),(OWNER,'stale',result['revision'],409),(OWNER,None,result['revision'],428),(OWNER,'edited','edited',409)]:
                with self.assertRaises(self.bridge.PDFSourceError) as caught:
                    self.bridge.source_export(directory,revision,'pdf','professional',owner=owner,expected_revision=expected)
                self.assertEqual(caught.exception.status,status)
            self.assertEqual(before,{path.relative_to(directory).as_posix():path.read_bytes() for path in directory.rglob('*') if path.is_file()})
            canonical=directory/'screenplay.fountain';canonical.write_bytes(canonical.read_bytes()+b'\nEDIT\n')
            with self.assertRaises(self.bridge.PDFSourceError):
                self.bridge.source_export(directory,result['revision'],'fdx','professional',owner=OWNER,expected_revision=result['revision'])
            canonical.write_bytes(before['screenplay.fountain'])
            (directory/'original.pdf').write_bytes(b'changed original')
            with self.assertRaises(self.bridge.PDFSourceError):
                self.bridge.source_export(directory,result['revision'],'pdf','professional',owner=OWNER,expected_revision=result['revision'])
        engine.to_professional_fdx.assert_not_called();engine.to_professional_pdf.assert_not_called()

    def test_archival_default_and_explicit_legacy_reflow_do_not_enter_professional_engine(self):
        source=self.stage();result=self.import_source(source);directory=self.projects/result['project'];engine=self.professional_engine()
        with patch.dict(sys.modules,{'core.screenplay_professional':engine}):
            self.assertTrue(self.bridge.source_export(directory,result['revision'],'pdf',None,owner=OWNER,expected_revision=result['revision']).startswith(b'%PDF-'))
            self.assertIsNone(self.bridge.source_export(directory,result['revision'],'pdf','reflow',owner=OWNER,expected_revision=result['revision']))
            with self.assertRaises(self.bridge.PDFSourceError) as caught:
                self.bridge.source_export(directory,result['revision'],'pdf','professional',owner=OWNER,expected_revision=result['revision'],watermark='Requested watermark')
            self.assertEqual(caught.exception.status,422)
        engine.to_professional_fdx.assert_not_called();engine.to_professional_pdf.assert_not_called()

    def test_professional_rejects_unfenced_projects_and_unknown_layout_without_legacy_fallback(self):
        directory=self.projects/'Plain Existing Project';directory.mkdir()
        (directory/'screenplay.fountain').write_text('INT. LAB - DAY\nPlain text.\n',encoding='utf-8')
        with self.assertRaises(self.bridge.PDFSourceError) as caught:
            self.bridge.source_export(directory,'current','fdx','professional',owner=OWNER,expected_revision='current')
        self.assertEqual(caught.exception.status,422)
        scope=self.router_scope();token=bind_memory_principal(OWNER)
        try:
            with self.assertRaises(HTTPException) as invalid:
                scope['export_fdx'](directory.name,'unreviewed-preset','current')
            self.assertEqual(invalid.exception.status_code,422)
        finally:reset_memory_principal(token)

    def test_current_fdx_renderer_upgrades_legacy_cache_without_rewriting_evidence(self):
        from core import screenplay_pdf
        source = self.stage()
        current_renderer = screenplay_pdf.to_fdx

        def legacy_renderer(packet):
            xml = ET.fromstring(current_renderer(packet))
            for spec in xml.findall('./ElementSettings/ParagraphSpec'):
                spec.set('FirstIndent', spec.get('LeftIndent'))
            return ET.tostring(xml, encoding='utf-8', xml_declaration=True)

        with patch.object(screenplay_pdf, 'to_fdx', legacy_renderer):
            result = self.import_source(source)
        directory = self.projects / result['project']
        before = {path.relative_to(directory).as_posix(): path.read_bytes()
                  for path in directory.rglob('*') if path.is_file()}
        packet = json.loads((directory / 'source_packet.json').read_text(encoding='utf-8'))
        expected = ET.fromstring(current_renderer(packet))
        for spec in expected.findall('./ElementSettings/ParagraphSpec'):
            spec.set('FirstIndent', '0')
        corrected = ET.tostring(expected, encoding='utf-8', xml_declaration=True)
        self.assertNotEqual(corrected, before['source_exports/layout.fdx'])
        with patch.object(screenplay_pdf, 'to_fdx', return_value=corrected) as renderer:
            exported = self.bridge.source_export(directory, result['revision'], 'fdx', 'source',
                owner=OWNER, expected_revision=result['revision'])
            self.assertEqual(exported, corrected)
            renderer.assert_called_once_with(packet)
        self.assertEqual(before, {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()})

        token = bind_memory_principal(OWNER)
        try:
            with patch.object(screenplay_pdf, 'to_fdx', return_value=corrected):
                response = self.router_scope()['export_fdx'](directory.name, 'source', result['revision'])
            self.assertEqual(response.body, corrected)
            self.assertEqual(response.headers['X-AI-BS-FDX-Renderer'], 'screenplay_fdx_relative_indent_v2')
            self.assertEqual(response.headers['X-AI-BS-Artifact-SHA256'], hashlib.sha256(corrected).hexdigest())
        finally:
            reset_memory_principal(token)

        canonical = directory / 'screenplay.fountain'
        canonical.write_bytes(canonical.read_bytes() + b'\nchanged after snapshot\n')
        with self.assertRaises(self.bridge.PDFSourceError) as changed:
            self.bridge.source_export(directory, result['revision'], 'fdx', 'source',
                owner=OWNER, expected_revision=result['revision'])
        self.assertEqual(changed.exception.status, 409)

    def test_legacy_route_owner_fences_cover_read_write_export_delete_import_and_lists(self):
        source = self.stage()
        result = self.import_source(source)
        scope = self.router_scope()
        directory = self.projects / result['project']
        before = {str(path.relative_to(directory)): path.read_bytes() for path in directory.rglob('*') if path.is_file()}
        token = bind_memory_principal(OTHER)
        try:
            operations = [
                lambda: scope['read_screenplay'](directory.name),
                lambda: scope['write_screenplay'](SimpleNamespace(project_name=directory.name,
                    content='foreign replacement', expected_revision=result['revision'], preserve_unchanged_bytes=True)),
                lambda: scope['export_pdf'](directory.name, expected_revision=result['revision']),
                lambda: scope['delete_project'](SimpleNamespace(project_name=directory.name)),
                lambda: scope['switch_project'](SimpleNamespace(project_name=directory.name)),
                lambda: scope['do_import_project'](SimpleNamespace(project_name=directory.name, content='foreign replacement')),
            ]
            for operation in operations:
                with self.subTest(operation=operation), self.assertRaises(HTTPException) as caught:
                    operation()
                self.assertEqual(caught.exception.status_code, 403)
            self.assertNotIn(directory.name, scope['list_projects']()['projects'])
        finally:
            reset_memory_principal(token)
        self.assertEqual(before, {str(path.relative_to(directory)): path.read_bytes() for path in directory.rglob('*') if path.is_file()})
        token = bind_memory_principal(OWNER)
        try:
            archived = scope['delete_project'](SimpleNamespace(project_name=directory.name))
        finally:
            reset_memory_principal(token)
        token = bind_memory_principal(OTHER)
        try:
            self.assertEqual(scope['list_project_archives']()['archives'], [])
            with self.assertRaises(HTTPException) as caught:
                scope['restore_project'](SimpleNamespace(archive_id=archived['archive_id']))
            self.assertEqual(caught.exception.status_code, 403)
        finally:
            reset_memory_principal(token)

    async def test_upload_authentication_precedes_any_file_read_or_write(self):
        with self.assertRaises(HTTPException) as caught:
            await self.upload('unauthorized.pdf', make_fixture(), owner=None)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(list(self.uploads.iterdir()), [])
        self.assertFalse((self.root / 'pdf-cache').exists())

    def test_index_failure_keeps_original_and_packet_without_false_manifest(self):
        with patch.object(self.bridge, 'ingest_source', side_effect=RuntimeError('synthetic unavailable vault')):
            with self.assertRaises(self.bridge.PDFSourceError) as caught:
                self.stage()
        error = caught.exception
        directory = self.bridge._source_directory(OWNER, error.source_id)
        self.assertEqual((directory / 'original.pdf').read_bytes(), make_fixture())
        self.assertTrue((directory / 'packet.json').is_file())
        self.assertTrue((directory / 'failure.json').is_file())
        self.assertFalse((directory / 'manifest.json').exists())

    def test_foreign_fenced_default_project_is_not_exposed_by_empty_list_fallback(self):
        source = self.stage()
        self.import_source(source, name='Default Project')
        scope = self.router_scope()
        token = bind_memory_principal(OTHER)
        try:
            result = scope['list_projects']()
        finally:
            reset_memory_principal(token)
        self.assertEqual(result['projects'], [])
        self.assertIsNone(result['current'])

    def test_actual_http_owner_binding_reaches_sync_read_and_export_handlers(self):
        from fastapi import APIRouter, FastAPI
        from fastapi.testclient import TestClient
        from security import firebase_auth
        source = self.stage()
        imported = self.import_source(source)
        scope = self.router_scope()
        router = APIRouter(dependencies=[Depends(scope['_screenwriting_owner_scope'])])
        router.add_api_route('/read', scope['read_screenplay'], methods=['GET'])
        router.add_api_route('/pdf', scope['export_pdf'], methods=['GET'])
        app = FastAPI()
        app.include_router(router)
        def verified(key, authorization):
            return OWNER if authorization == 'Bearer synthetic-owner' else OTHER if authorization == 'Bearer synthetic-other' else None
        with patch.object(firebase_auth, 'get_admin_principal', verified), TestClient(app) as client:
            query = dict(project_name=imported['project'])
            own = client.get('/read', params=query, headers={'Authorization':'Bearer synthetic-owner'})
            self.assertEqual(own.status_code, 200)
            self.assertTrue(own.json()['source_layout_preserved'])
            self.assertEqual(own.json()['metadata']['source_pdf']['sha256'], source['source_sha256'])
            self.assertTrue(own.json()['body_ast'])
            other = client.get('/read', params=query, headers={'Authorization':'Bearer synthetic-other'})
            self.assertEqual(other.status_code, 403)
            self.assertNotIn('First wrapped dialogue line', other.text)
            anonymous = client.get('/read', params=query)
            self.assertEqual(anonymous.status_code, 403)
            pdf = client.get('/pdf', params={**query, 'expected_revision':imported['revision']},
                             headers={'Authorization':'Bearer synthetic-owner'})
            self.assertEqual(pdf.status_code, 200)
            self.assertEqual(pdf.headers['X-AI-BS-Layout'], 'preserved-source')
            self.assertTrue(pdf.content.startswith(b'%PDF-'))
            self.assertEqual(client.get('/pdf', params={**query, 'expected_revision':'stale'},
                headers={'Authorization':'Bearer synthetic-owner'}).status_code, 409)

    def test_actual_professional_http_pipeline_validates_outputs_and_retains_project(self):
        from fastapi import APIRouter, FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.testclient import TestClient
        from security import firebase_auth
        import fitz
        source=self.stage();imported=self.import_source(source);directory=self.projects/imported['project']
        before={path.relative_to(directory).as_posix():path.read_bytes() for path in directory.rglob('*') if path.is_file()}
        scope=self.router_scope();router=APIRouter(dependencies=[Depends(scope['_screenwriting_owner_scope'])])
        router.add_api_route('/fdx',scope['export_fdx'],methods=['GET']);router.add_api_route('/pdf',scope['export_pdf'],methods=['GET'])
        app=FastAPI();app.include_router(router)
        app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173'],allow_methods=['GET'],allow_headers=['Authorization'])
        def verified(key,authorization):
            return OWNER if authorization=='Bearer synthetic-owner' else OTHER if authorization=='Bearer synthetic-other' else None
        query={'project_name':imported['project'],'expected_revision':imported['revision'],'layout':'professional'}
        with patch.object(firebase_auth,'get_admin_principal',verified),TestClient(app) as client:
            for kind in ('fdx','pdf'):
                response=client.get('/'+kind,params=query,headers={'Authorization':'Bearer synthetic-owner','Origin':'http://localhost:5173'})
                self.assertEqual(response.status_code,200,response.text[:100] if kind=='fdx' else '')
                self.assertEqual(response.headers['X-AI-BS-Layout'],'professional')
                self.assertEqual(response.headers['X-AI-BS-Profile'],'us-spec-courier12-v1')
                self.assertEqual(response.headers['X-AI-BS-Artifact-SHA256'],hashlib.sha256(response.content).hexdigest())
                self.assertIn('X-AI-BS-Artifact-SHA256',response.headers['Access-Control-Expose-Headers'])
                self.assertIn('.professional-us-spec-courier12-v1.'+kind,response.headers['Content-Disposition'])
                self.assertEqual(response.headers['Access-Control-Allow-Origin'],'http://localhost:5173')
                if kind=='fdx':
                    self.assertEqual(ET.fromstring(response.content).tag,'FinalDraft')
                    self.assertEqual(response.headers['X-AI-BS-Renderer'],'aibs_professional_fdx_v1')
                    self.assertNotIn('X-AI-BS-PDF-Page-Count',response.headers)
                else:
                    with fitz.open(stream=response.content,filetype='pdf') as document:
                        self.assertEqual(int(response.headers['X-AI-BS-PDF-Page-Count']),document.page_count)
                        self.assertGreater(document.page_count,0)
                    self.assertEqual(response.headers['X-AI-BS-Renderer'],'aibs_reportlab_professional_pdf_v1')
                self.assertEqual(client.get('/'+kind,params=query,headers={'Authorization':'Bearer synthetic-other'}).status_code,403)
                self.assertEqual(client.get('/'+kind,params={**query,'expected_revision':'stale'},headers={'Authorization':'Bearer synthetic-owner'}).status_code,409)
        self.assertEqual(before,{path.relative_to(directory).as_posix():path.read_bytes() for path in directory.rglob('*') if path.is_file()})

    async def test_generic_text_pdf_keeps_rag_intake_without_screenplay_fidelity_claim(self):
        raw = make_fixture(font='Times-Roman')
        result = await self.upload('ordinary.pdf', raw)
        self.assertIsInstance(result, dict)
        item = result['file']
        self.assertFalse(item['source_layout_available'])
        self.assertEqual(item['profile'], 'generic_pdf_text')
        self.assertEqual(item['indexing_status'], 'lexical_chunks_indexed')
        self.assertEqual(item['page_count'], 3)
        with self.assertRaises(self.bridge.PDFSourceError) as caught:
            self.bridge.import_project(self.projects / 'Not A Qualified Screenplay', OWNER,
                item['source_id'], item['source_sha256'], uuid.uuid4().hex)
        self.assertEqual(caught.exception.status, 422)
        self.assertEqual(list(self.projects.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
