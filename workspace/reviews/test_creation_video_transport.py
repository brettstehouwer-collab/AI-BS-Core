"""Actual video handlers in a synthetic FastAPI app; no backend startup or real files."""
import ast
import mimetypes
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit, quote

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]


class VideoTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'fixture clip.webm'
        self.file.write_bytes(bytes(range(128)))
        def require_document_access(request: Request):
            if request.headers.get('authorization') != 'Bearer fixture-only':
                raise HTTPException(403, 'Fixture authorization required')
        scope = dict(APIRouter=APIRouter, Depends=Depends, HTTPException=HTTPException,
                     Query=Query, Request=Request, BaseModel=BaseModel, Path=Path,
                     SCREEN_RECORDINGS_DIR=self.root, mimetypes=mimetypes, quote=quote,
                     require_document_access=require_document_access, require_video_access=require_document_access)
        tree = ast.parse((ROOT/'backend/routers/video_router.py').read_text(encoding='utf-8'))
        selected = [n for n in tree.body if (isinstance(n, ast.ImportFrom) and n.module == 'fastapi.responses')
                    or (isinstance(n, ast.ClassDef) and n.name == 'StreamRequest')
                    or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'VIDEO_MIME_TYPES' for t in n.targets))]
        scope['router'] = APIRouter(prefix='/api/video')
        selected += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('resolve_video_path', 'start_video_stream', 'stream_video_file')]
        exec(compile(ast.Module(body=selected, type_ignores=[]), '<actual-video-handlers>', 'exec'), scope)
        app = FastAPI(); app.include_router(scope['router'])
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.headers = {'Authorization': 'Bearer fixture-only'}

    def test_actual_stream_serves_range_with_correct_mime(self):
        r = self.client.get('/api/video/stream', params={'path': str(self.file)},
                            headers={**self.headers, 'Range': 'bytes=16-31'})
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.content, bytes(range(16, 32)))
        self.assertEqual(r.headers['content-type'], 'video/webm')
        self.assertEqual(r.headers['content-range'], 'bytes 16-31/128')

    def test_anonymous_file_requests_are_denied(self):
        r = self.client.get('/api/video/stream', params={'path': str(self.file)})
        self.assertEqual(r.status_code, 403)

    def test_start_preserves_full_file_identity(self):
        r = self.client.post('/api/video/start_stream', json={'video_path': str(self.file)}, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(parse_qs(urlsplit(r.json()['stream_url']).query)['path'][0], str(self.file.resolve()))

    def test_missing_file_stays_404(self):
        r = self.client.get('/api/video/stream', params={'path': str(self.root/'missing.mp4')}, headers=self.headers)
        self.assertEqual(r.status_code, 404)


if __name__ == '__main__': unittest.main()
