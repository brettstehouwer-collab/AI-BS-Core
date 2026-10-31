"""Isolated source tests: no application imports, SDKs, or production stores."""
import ast
import asyncio
import builtins
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]

def extracted(path, name, namespace=None, method=None):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    node = next(n for n in tree.body if getattr(n, 'name', None) == name)
    if method:
        node = next(n for n in node.body if getattr(n, 'name', None) == method)
    node.decorator_list = []
    safe = dict(vars(builtins))
    def forbidden(*args, **kwargs):
        raise AssertionError('Import or side effect forbidden')
    safe['__import__'] = forbidden
    safe['open'] = forbidden
    ns = {'__builtins__': safe, 'Dict': Dict, 'Any': Any, 'Optional': Optional, 'List': List}
    ns.update(namespace or {})
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), 'exec'), ns)
    return ns[name if not method else method]

class Response:
    def __init__(self, content, status_code=200):
        self.content, self.status_code = content, status_code
class HTTPError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
class Upload:
    def __init__(self, data): self.data = data
    async def read(self, size):
        data, self.data = self.data[:size], self.data[size:]
        return data

class IntegrityTests(unittest.TestCase):
    def test_pipeline_held_without_imports_or_checkpoints(self):
        run = extracted('backend/core/media_render_engine.py', 'MediaRenderEngine', method='execute_media_pipeline_recipe')
        result = run({'stages': [{'domain': 1, 'action': 'invented'}]}, 'old-job')
        self.assertEqual(result['status'], 'held')
        self.assertEqual(result['stages_completed'], 0)
        self.assertFalse(result['checkpoints_saved'])

    def test_vault_inert_writer_and_readonly_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.db'
            observed_connections = []
            class ReadOnlySQLite:
                @staticmethod
                def connect(database, **kwargs):
                    observed_connections.append(database)
                    self.assertTrue(database.startswith(path.resolve().as_uri() + '?mode=ro'))
                    self.assertTrue(kwargs.get('uri'))
                    return sqlite3.connect(database, **kwargs)
            cls = extracted('backend/core/media_chromadb_vault.py', 'MediaChromaDBVault', {
                'sqlite3': ReadOnlySQLite, 'Path': Path, 'json': __import__('json'),
                'SQLITE_VAULT_PATH': str(path), 'COLLECTION_NAME': 'test'})
            vault = cls()
            self.assertFalse(path.exists())
            self.assertIsNone(vault.get_stats()['count'])
            self.assertEqual(vault.search_media_memory('x')['status'], 'unavailable')
            self.assertNotIn('persist_dir', vault.get_stats())
            self.assertEqual(vault.add_media_asset('x','image','t','d','p')['status'], 'held')
            self.assertFalse(path.exists())
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('CREATE TABLE media_memory_vault (media_id, media_type, title, description, file_path, metadata_json)')
                conn.execute("INSERT INTO media_memory_vault VALUES ('1','image','needle','description','private','{}')")
                conn.commit()
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            before = path.read_bytes()
            stats = vault.get_stats()
            self.assertEqual(stats['count'], 1, repr(observed_connections))
            self.assertEqual(vault.search_media_memory('needle', media_type='video')['count'], 0)
            self.assertEqual(vault.search_media_memory('needle')['count'], 1)
            self.assertEqual(before, path.read_bytes())
            with closing(sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)) as conn:
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_signing_and_tampering_held(self):
        for name, args in [('generate_signed_nda', (None,)), ('embed_anti_tamper_seal', (b'x','x','x')), ('generate_signed_nda_pdf_bytes', (None,'x','x')), ('simulate_tamper_attack', (None,))]:
            fn = extracted('backend/routers/nda_signer_router.py', name, {'HTTPException': HTTPError, 'NdaSignRequest': object, 'UploadFile': object, 'File': lambda *a: None})
            with self.assertRaises(HTTPError) as raised:
                result = fn(*args)
                if hasattr(result, '__await__'): asyncio.run(result)
            self.assertEqual(raised.exception.status_code, 503)

    def test_router_is_admin_and_pdf_engines_not_imported(self):
        tree = ast.parse((ROOT / 'backend/routers/nda_signer_router.py').read_text(encoding='utf-8-sig'))
        imports = [n.module for n in tree.body if isinstance(n, ast.ImportFrom)]
        self.assertIn('security.host_control_access', imports)
        self.assertFalse(any((name or '').startswith('reportlab') for name in imports))
        router = next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'router' for t in n.targets))
        self.assertTrue(any(k.arg == 'route_class' and isinstance(k.value, ast.Name) and k.value.id == 'AdminHostControlRoute' for k in router.keywords))

    def test_verification_is_bounded_observation(self):
        fn = extracted('backend/routers/nda_signer_router.py', 'verify_pdf_integrity', {'JSONResponse': Response, 'HTTPException': HTTPError, 'UploadFile': object, 'File': lambda *a: None, 'hashlib': hashlib})
        result = asyncio.run(fn(Upload(b'changed image bytes')))
        self.assertIsNone(result.content['valid'])
        self.assertIsNone(result.content['tamper_detected'])
        self.assertEqual(result.content['current_sha256'], hashlib.sha256(b'changed image bytes').hexdigest())
        result = asyncio.run(fn(Upload(b'x' * (8 * 1024 * 1024 + 1))))
        self.assertEqual(result.status_code, 413)
        self.assertIsNone(result.content['tamper_detected'])
        class BrokenUpload:
            async def read(self, size): raise OSError('backend unavailable')
        result = asyncio.run(fn(BrokenUpload()))
        self.assertEqual(result.status_code, 503)
        self.assertIsNone(result.content['tamper_detected'])

if __name__ == '__main__': unittest.main()
