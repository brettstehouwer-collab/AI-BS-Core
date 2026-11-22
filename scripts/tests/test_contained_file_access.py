"""Offline containment fixtures. Never import the AI-BS application or stores."""
import ast
import asyncio
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI, APIRouter, HTTPException, Request, Query, File, Form, UploadFile, Depends
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi import Path as FPath
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from security import contained_file_access as access
from security import host_control_access as auth
from security import document_access


class Upload:
    def __init__(self, content, filename='fixture.txt'):
        self.filename = filename
        self.content_type = 'text/plain'
        self.file = io.BytesIO(content)
    async def read(self, size=-1):
        return self.file.read(size)


class FileContainmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aibs-file-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'managed'
        self.root.mkdir()

    def test_upload_rejects_paths_devices_ads_and_ambiguous_names(self):
        for value in ('../outside', '..\\outside', 'C:\\private.txt', '/absolute', 'a:b.txt',
                      'NUL.txt', 'CON', 'COM¹.txt', 'LPT² .txt', 'name.', 'name ', 'a\x00.txt', 'x/y.txt', '', 'a'*181):
            with self.subTest(value=value), self.assertRaises(HTTPException):
                access.validate_upload_filename(value)

    def test_unicode_upload_and_exact_bytes(self):
        data = b'fixture\r\n\x00\xff'
        path, size = asyncio.run(access.write_bounded_upload(Upload(data), self.root, '雪.txt', max_bytes=100))
        self.assertEqual(path.read_bytes(), data)
        self.assertEqual(size, len(data))

    def test_collision_never_overwrites(self):
        (self.root/'same.txt').write_bytes(b'preserve')
        with self.assertRaises(HTTPException) as failure:
            asyncio.run(access.write_bounded_upload(Upload(b'new'), self.root, 'same.txt'))
        self.assertEqual(failure.exception.status_code, 409)
        self.assertEqual((self.root/'same.txt').read_bytes(), b'preserve')
        self.assertEqual([p.name for p in self.root.iterdir()], ['same.txt'])

    def test_oversize_upload_leaves_no_partial_file(self):
        with self.assertRaises(HTTPException) as failure:
            asyncio.run(access.write_bounded_upload(Upload(b'x'*21), self.root, 'large.txt', max_bytes=20))
        self.assertEqual(failure.exception.status_code, 413)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_network_failure_leaves_no_partial_file(self):
        upload = Upload(b'fixture')
        upload.read = Mock(side_effect=RuntimeError('private fixture error'))
        with self.assertRaises(Exception):
            asyncio.run(access.write_bounded_upload(upload, self.root, 'fixture.txt'))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_media_only_managed_regular_media_files(self):
        target = self.root/'clip.mp4'; target.write_bytes(b'offline fixture')
        self.assertEqual(access.resolve_media_path(str(target), [self.root]), target.resolve())
        outside = self.root.parent/'private.mp4'; outside.write_bytes(b'fixture private')
        secret = self.root/'secret.env'; secret.write_bytes(b'fixture')
        for value in (str(outside), str(secret), str(self.root), str(self.root/'missing.mp4'), str(self.root/'../private.mp4')):
            with self.subTest(value=value), self.assertRaises(HTTPException):
                access.resolve_media_path(value, [self.root])

    def test_media_symlink_is_rejected(self):
        outside = self.root.parent/'outside.mp4'; outside.write_bytes(b'fixture')
        link = self.root/'link.mp4'
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('Windows symlink privilege unavailable')
        with self.assertRaises(HTTPException):
            access.resolve_media_path(str(link), [self.root])


class RouteContainmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aibs-route-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        admission = patch.object(auth, 'get_admin_principal', side_effect=lambda key='', token='':
                                 'offline-owner' if token == 'Bearer offline-admin' else None)
        admission.start(); self.addCleanup(admission.stop)
        self.auth = {'Authorization': 'Bearer offline-admin'}

    def fixture(self, relative, names, extra=None):
        path = ROOT/relative
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        app = FastAPI()
        ns = dict(__name__='isolated_file_fixture', __file__=str(path), app=app,
                  APIRouter=APIRouter, AdminHostControlRoute=auth.AdminHostControlRoute,
                  require_host_admin=auth.require_host_admin, Request=Request,
                  Depends=Depends, HTTPException=HTTPException, Query=Query, File=File,
                  JSONResponse=JSONResponse, HOST_CONTROL_PRIVATE_HEADERS=auth.HOST_CONTROL_PRIVATE_HEADERS,
                  Form=Form, UploadFile=UploadFile, Path=FPath, os=__import__('os'),
                  json=__import__('json'), asyncio=asyncio, VAULT_DOCS_DIR=str(self.root),
                  write_bounded_upload=access.write_bounded_upload,
                  validate_upload_filename=access.validate_upload_filename,
                  resolve_media_path=access.resolve_media_path, MEDIA_ROOTS=[self.root],
                  stream_media_response=getattr(access,'stream_media_response',None),
                  open_verified_media=getattr(access,'open_verified_media',None),
                  MEDIA_UPLOAD_DIR=self.root, MAX_UPLOAD_BYTES=32*1024*1024)
        ns.update(extra or {})
        selected = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
                selected.append(node)
            elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'router' for t in node.targets):
                selected.append(node)
        exec(compile(ast.Module(selected, []), str(path), 'exec'), ns)
        if 'router' in ns:
            app.include_router(ns['router'])
        client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(client.close)
        return client

    def test_raw_documents_upload_rejects_unverified_before_writing(self):
        client = self.fixture('backend/AI_BS_Backend.py', {'upload_document'})
        for headers in ({}, {'X-Client-ID': 'admin'}, {'Authorization': 'Bearer forged'}):
            response = client.post('/documents/upload', headers=headers, files={'file': ('fixture.txt', b'fixture')})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_raw_documents_upload_rejects_traversal_and_collisions(self):
        client = self.fixture('backend/AI_BS_Backend.py', {'upload_document'})
        for filename in ('../escape.txt', 'nested/escape.txt', 'NUL.txt'):
            response = client.post('/documents/upload', headers=self.auth, files={'file': (filename, b'fixture')})
            self.assertEqual(response.status_code, 400)
        good = client.post('/documents/upload', headers=self.auth, files={'file': ('fixture.txt', b'preserve')})
        self.assertEqual(good.status_code, 200)
        duplicate = client.post('/documents/upload', headers=self.auth, files={'file': ('fixture.txt', b'replace')})
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual((self.root/'fixture.txt').read_bytes(), b'preserve')

    def test_media_anonymous_cannot_stream_upload_or_probe(self):
        client = self.fixture('backend/routers/media_render_router.py', {'stream_media_file', 'upload_media_file', 'inspect_media_file'})
        target = self.root/'clip.mp4'; target.write_bytes(b'fixture')
        for method, path in [('GET', '/api/v1/media/stream'), ('GET', '/api/v1/media/inspect'), ('POST', '/api/v1/media/upload')]:
            response = client.request(method, path, params={'path': str(target)}, content=b'not-a-valid-upload')
            self.assertEqual(response.status_code, 403)
            self.assertIn('no-store', response.headers.get('cache-control', ''))

    def test_media_stream_admin_still_cannot_read_outside_managed_roots(self):
        client = self.fixture('backend/routers/media_render_router.py', {'stream_media_file'})
        outside = self.root.parent/(self.root.name+'-outside.mp4')
        outside.write_bytes(b'fixture-private')
        self.addCleanup(outside.unlink)
        response = client.get('/api/v1/media/stream', headers=self.auth, params={'path': str(outside)})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('fixture-private', response.text)
        self.assertNotIn(str(outside), response.text)
        target = self.root/'clip.mp4'; target.write_bytes(b'fixture-media')
        response = client.get('/api/v1/media/stream', headers=self.auth, params={'path': str(target)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'fixture-media')
        self.assertIn('no-store', response.headers.get('cache-control', ''))

    def test_media_inspect_passes_paths_as_argv_without_shell(self):
        client = self.fixture('backend/routers/media_render_router.py', {'inspect_media_file'})
        target = self.root/'clip & echo fixture.mp4'; target.write_bytes(b'fixture')
        process = Mock(return_value=__import__('types').SimpleNamespace(returncode=0, stdout='{"streams":[{"width":2,"height":2,"duration":"1"}]}'))
        with patch('subprocess.run', process):
            response = client.get('/api/v1/media/inspect', headers=self.auth, params={'path': str(target)})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(process.call_args.args[0], list)
        self.assertEqual(process.call_args.args[0][-1], 'pipe:0')
        self.assertIsNotNone(process.call_args.kwargs.get('stdin'))
        self.assertFalse(process.call_args.kwargs.get('shell', False))

    def test_checked_media_replacement_never_serves_outside_bytes(self):
        target=self.root/'clip.mp4';target.write_bytes(b'allowed-fixture')
        outside=self.root.parent/(self.root.name+'-secret.mp4');outside.write_bytes(b'outside-fixture-secret')
        self.addCleanup(outside.unlink)
        real=access.resolve_media_path
        def replace_after_check(value,roots):
            checked=real(value,roots)
            checked.unlink()
            checked.symlink_to(outside)
            return checked
        client=self.fixture('backend/routers/media_render_router.py',{'stream_media_file'},
                            {'resolve_media_path':replace_after_check})
        with patch.object(access,'resolve_media_path',replace_after_check):
            response=client.get('/api/v1/media/stream',headers=self.auth,params={'path':str(target)})
        self.assertNotIn(b'outside-fixture-secret',response.content)
        self.assertIn(response.status_code,(403,404,409,503))

    def test_stream_supports_bounded_single_range_and_releases_handles(self):
        target=self.root/'clip.mp4';target.write_bytes(b'0123456789')
        client=self.fixture('backend/routers/media_render_router.py',{'stream_media_file'})
        response=client.get('/api/v1/media/stream',headers=dict(self.auth,Range='bytes=2-5'),params={'path':str(target)})
        self.assertEqual(response.status_code,206)
        self.assertEqual(response.content,b'2345')
        self.assertEqual(response.headers['content-range'],'bytes 2-5/10')
        target.rename(self.root/'after.mp4')

    def test_upload_directory_swap_cannot_publish_substituted_payload(self):
        original=access._reject_links
        hits=0
        def swap(path):
            nonlocal hits
            original(path)
            if Path(path)==self.root:
                hits+=1
            if hits==3:
                try:
                    self.root.rename(self.root.with_name('moved'))
                except PermissionError:
                    return
                self.root.mkdir()
                for item in self.root.with_name('moved').glob('.upload-*'):
                    (self.root/item.name).write_bytes(b'substituted-fixture')
        with patch.object(access,'_reject_links',swap):
            try:
                path,_=asyncio.run(access.write_bounded_upload(Upload(b'actual-fixture'),self.root,'file.txt'))
            except (HTTPException,OSError):
                return
        self.assertEqual(path.read_bytes(),b'actual-fixture')

    def test_demucs_routes_share_early_admission_and_confine_stem_files(self):
        effects = Mock(side_effect=AssertionError('Audio worker effect attempted'))
        client = self.fixture('backend/routers/audio_demucs_router.py',
            {'upload_and_separate_endpoint', 'get_audio_hardware_status', 'get_stem_sessions', 'get_stem_audio_file'},
            {'Optional': __import__('typing').Optional, 'STEMS_DIR': str(self.root), 'UPLOAD_DIR': str(self.root),
             'FileResponse': FileResponse, 'DemucsAudioEngine': types.SimpleNamespace(
                separate_stems=effects, get_hardware_status=effects, list_recent_sessions=effects)})
        for method, route in [('POST','/upload_and_separate'), ('GET','/hardware'), ('GET','/sessions'), ('GET','/file/test/clip.wav')]:
            response = client.request(method, '/api/v1/audio/demucs'+route, content=b'bad-body')
            self.assertEqual(response.status_code,403)
        effects.assert_not_called()
        session = self.root/'session'; session.mkdir()
        (session/'clip.wav').write_bytes(b'fixture-wav')
        response = client.get('/api/v1/audio/demucs/file/session/clip.wav', headers=self.auth)
        self.assertEqual(response.content, b'fixture-wav')
        self.assertIn('no-store', response.headers.get('cache-control',''))
        response = client.get('/api/v1/audio/demucs/file/session/missing.wav', headers=self.auth)
        self.assertEqual(response.status_code,404)

    def test_unverified_pipeline_cannot_dispatch_resume_or_certify_checkpoint(self):
        class PipelineRequest(BaseModel):
            recipe: dict
            job_id: str | None = None
        dispatch=Mock(return_value={'status':'success'})
        legacy=Mock(return_value={'domain_id':9,'stage_name':'fixture','status':'COMPLETED'})
        client=self.fixture('backend/routers/media_render_router.py',
            {'execute_media_pipeline','resume_media_pipeline','get_job_checkpoint'},
            {'PipelineExecuteRequest':PipelineRequest,
             'MediaRenderEngine':types.SimpleNamespace(execute_media_pipeline_recipe=dispatch),
             'vram_arbiter':types.SimpleNamespace(get_last_successful_checkpoint=legacy)})
        for method,url in [('POST','/pipeline/execute'),('POST','/pipeline/resume/fixture'),('GET','/checkpoints/fixture')]:
            response=client.request(method,'/api/v1/media'+url,headers=self.auth,json={'recipe':{'stages':[{'domain':9}]}})
            self.assertEqual(response.status_code,503)
            self.assertIn('no-store',response.headers.get('cache-control',''))
        dispatch.assert_not_called();legacy.assert_not_called()

    def test_new_multipart_namespaces_are_bounded_before_parser(self):
        app=FastAPI()
        router=APIRouter(prefix='/api/v1/nda',route_class=auth.AdminHostControlRoute)
        effect=Mock(side_effect=AssertionError('oversize upload reached handler'))
        @router.post('/verify-integrity')
        async def verify(file:UploadFile=File(...)):
            effect()
        app.include_router(router)
        with patch.object(auth,'HOST_UPLOAD_REQUEST_MAX_BYTES',128), patch('starlette.formparsers.MultiPartParser.parse',side_effect=AssertionError('oversize reached multipart parser')) as parser:
            with TestClient(app,raise_server_exceptions=False) as client:
                result=client.post('/api/v1/nda/verify-integrity',headers=self.auth,files={'file':('fixture.pdf',b'%PDF'+b'x'*256)})
        self.assertEqual(result.status_code,413)
        self.assertIn('no-store',result.headers.get('cache-control',''))
        parser.assert_not_called();effect.assert_not_called()

    def test_document_and_host_alias_middleware_denies_before_body_parsing(self):
        tree = ast.parse((ROOT/'backend/AI_BS_Backend.py').read_text(encoding='utf-8-sig'))
        node = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AdminExecutionBoundaryMiddleware')
        namespace = dict(BaseHTTPMiddleware=BaseHTTPMiddleware, Request=Request, HTTPException=HTTPException,
                         JSONResponse=JSONResponse, asyncio=asyncio, get_admin_principal=auth.get_admin_principal,
                         HOST_CONTROL_PRIVATE_HEADERS=auth.HOST_CONTROL_PRIVATE_HEADERS,
                         limit_host_upload=auth.limit_host_upload)
        exec(compile(ast.Module([node],[]),'isolated_boundary','exec'), namespace)
        stubs = {}
        for name, functions in {
            'security.vault_access': {'is_vault_path': lambda path:False, 'require_vault_access':Mock()},
            'security.analytics_access': {'is_analytics_path':lambda path:False,'require_analytics_access':Mock()},
            'security.screenwriting_access': {'is_screenwriting_path':lambda path:False,'screenwriting_request_allowed':Mock()},
            'security.recdebut_access': {'is_recdebut_path':lambda path:False,'require_recdebut_access':Mock()},
            'core.personal_memory_scope': {'bind_memory_principal':lambda principal:object(),'reset_memory_principal':lambda token:None},
        }.items():
            module = types.ModuleType(name)
            module.__dict__.update(functions)
            stubs[name] = module
        with patch.dict(sys.modules, stubs), patch.object(document_access,'verify_admin_credentials',return_value=False):
            app = FastAPI()
            effect = Mock(side_effect=AssertionError('Unauthorized body/handler reached'))
            async def forbidden():
                effect()
            paths = ['/documents/upload','/documents/list','/api/v1/media/upload',
                     '/api/v1/audio/demucs/upload_and_separate','/api/v1/executive/vibe-rollback',
                     '/api/usb-recovery/rebuild-partition', '/api/ai/config',
                     '/api/ai/validate-key', '/api/ai/generate']
            for path in paths:
                app.add_api_route(path,forbidden,methods=['POST'])
            app.add_middleware(namespace['AdminExecutionBoundaryMiddleware'])
            with TestClient(app) as client:
                for path in paths:
                    result=client.post(path,content=b'not-valid-json-or-multipart',headers={'Content-Type':'application/json'})
                    self.assertEqual(result.status_code,403)
                    self.assertIn('no-store',result.headers.get('cache-control',''))
            effect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
