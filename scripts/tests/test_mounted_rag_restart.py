"""Selected production FastAPI routes, real stores, synthetic SDK claims, fresh processes.

This does not import/activate the whole operational backend or call an AI provider.
The attachment function is mounted from its unchanged source AST; the memory
router is imported normally. SDK token verification alone is a local fixture.
"""
import ast
import asyncio
from contextlib import ExitStack, closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


async def worker(directory, phase):
    import socket
    import httpx
    from fastapi import FastAPI, File, HTTPException, Request, UploadFile
    from fastapi.responses import JSONResponse

    sys.path.insert(0, str(ROOT / 'backend'))
    sys.path.insert(0, str(ROOT))
    # Child-only synthetic configuration. Never load operational .env or keys.
    os.environ.pop('AI_BS_ADMIN_KEY', None)
    os.environ['FIREBASE_PROJECT_ID'] = 'mounted-rag-fixture'
    os.environ['AI_BS_ADMIN_EMAILS'] = 'one@example.invalid,two@example.invalid'
    from security import firebase_auth
    from routers import memory_router
    from core import chat_pdf_sources
    from core.infinite_learning_loop import learning_loop_instance
    from scripts.tests.test_screenplay_pdf import make_fixture

    assert not learning_loop_instance.running
    directory = Path(directory)
    db = directory / 'vault.sqlite'
    memory_router.VAULT_DB_PATH = db
    chat_pdf_sources.VAULT_DB_PATH = db
    chat_pdf_sources.CACHE_ROOT = directory / 'pdf-cache'
    app = FastAPI()
    app.include_router(memory_router.router)
    source = ROOT / 'backend/AI_BS_Backend.py'
    node = next(node for node in ast.parse(source.read_text(encoding='utf-8-sig')).body
                if getattr(node, 'name', '') == 'chat_attach_file')
    namespace = dict(app=app, Request=Request, UploadFile=UploadFile, File=File,
                     HTTPException=HTTPException, JSONResponse=JSONResponse,
                     asyncio=asyncio, os=os, re=re,
                     UPLOAD_ATTACHMENTS_DIR=str(directory / 'uploads'))
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)

    def claims(token, request, audience):
        assert audience == 'mounted-rag-fixture'
        if token not in ('fixture-one', 'fixture-two'):
            raise ValueError('Invalid synthetic credential')
        name = token.removeprefix('fixture-')
        return dict(sub=name, email=name + '@example.invalid', email_verified=True,
                    exp=time.time() + 120)

    network_attempts = []

    def no_network(*args, **kwargs):
        network_attempts.append(True)
        raise AssertionError('This fixture must not contact a network or model')

    headers = {'Authorization': 'Bearer fixture-one'}
    other = {'Authorization': 'Bearer fixture-two'}
    route_results = {}
    with ExitStack() as stack:
        stack.enter_context(patch.object(firebase_auth.id_token, 'verify_firebase_token', claims))
        stack.enter_context(patch.object(socket.socket, 'connect', no_network))
        stack.enter_context(patch.object(socket, 'create_connection', no_network))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url='http://synthetic-fixture') as client:
            raw = make_fixture()
            denied = await client.post('/api/chat/attach', files={'file': ('synthetic.pdf', raw)},
                                       headers={'X-Client-ID': 'fixture-one'})
            assert denied.status_code == 403, denied.text
            route_results['anonymous_attach'] = denied.status_code
            if phase == 'seed':
                one = await client.post('/api/chat/attach', headers=headers,
                                        files={'file': ('synthetic.pdf', raw)})
                two = await client.post('/api/chat/attach', headers=other,
                                        files={'file': ('synthetic.pdf', raw)})
                assert one.status_code == two.status_code == 200, (one.text, two.text)
                original = one.json()['file']
                foreign = two.json()['file']
                assert original['source_id'] != foreign['source_id']
                assert original['source_sha256'] == hashlib.sha256(raw).hexdigest()
                assert original['retrieval_status'] == 'source_passage_readback_verified'
                assert original['parsing_status'] == 'complete'
                (directory / 'reference.json').write_text(json.dumps(original), encoding='utf8')
            else:
                original = json.loads((directory / 'reference.json').read_text(encoding='utf8'))
            query = dict(query='wrapped', collection='bschat_sources_v1', top_k=5)
            result = await client.post('/api/memory/query', headers=headers, json=query)
            assert result.status_code == 200, result.text
            body = result.json()
            assert body['search_type'] == 'lexical_scan' and body['count'] > 0
            manifest, packet, retained_original = chat_pdf_sources.read_source(
                'firebase:mounted-rag-fixture:one', original['source_id'], original['source_sha256'])
            assert retained_original == raw
            expected_id = manifest['rag_receipt']['vault_item_id']
            derived = packet['rag_text'].encode('utf8')
            verified = []
            for hit in body['results']:
                assert hit['id'] == expected_id
                excerpt = derived[hit['byte_start']:hit['byte_end']]
                assert excerpt.decode('utf8') == hit['content']
                assert hashlib.sha256(excerpt).hexdigest() == hit['chunk_sha256']
                verified.append(hit['chunk_sha256'])
            denied = await client.get(f'/api/memory/items/{expected_id}', headers=other)
            assert denied.status_code == 404, denied.text
            route_results['foreign_record'] = denied.status_code
            denied = await client.post('/api/memory/query', json=query)
            assert denied.status_code == 403
            route_results['anonymous_query'] = denied.status_code
            invalid = await client.post('/api/memory/query', headers=headers,
                                        json={**query, 'owner': 'firebase:mounted-rag-fixture:two'})
            assert invalid.status_code == 422
            route_results['forged_owner_field'] = invalid.status_code
            with closing(sqlite3.connect(db)) as connection:
                before_bad_digest = connection.execute('SELECT count(*) FROM vault_items').fetchone()[0]
            invalid = await client.post('/api/memory', headers=headers, json={
                'content': 'Synthetic wrong digest', 'metadata': {'kind': 'bschat_source_v1',
                'source_name': 'wrong.txt', 'source_sha256': '0' * 64}})
            assert invalid.status_code == 422
            route_results['wrong_digest'] = invalid.status_code
            with closing(sqlite3.connect(db)) as connection:
                assert connection.execute('SELECT count(*) FROM vault_items').fetchone()[0] == before_bad_digest
            _, packet_after, retained_after = chat_pdf_sources.read_source(
                'firebase:mounted-rag-fixture:one', original['source_id'], original['source_sha256'])
            assert packet == packet_after and retained_after == raw
    assert not network_attempts
    assert not learning_loop_instance.running
    return dict(phase=phase, pid=os.getpid(), source_sha256=original['source_sha256'],
                source_id=original['source_id'], passage_hashes=verified,
                route_results=route_results, network_attempts=len(network_attempts),
                embeddings_generated=body['embeddings_generated'],
                scope='Selected production routes mounted in isolated FastAPI ASGI; synthetic SDK verification')


class MountedRagRestartTests(unittest.TestCase):
    def test_authenticated_pdf_index_readback_owner_isolation_survives_fresh_process(self):
        with tempfile.TemporaryDirectory(prefix='aibs-mounted-rag-') as folder:
            db = Path(folder) / 'vault.sqlite'
            with closing(sqlite3.connect(db)) as connection, connection:
                connection.execute('CREATE TABLE vault_items(id INTEGER PRIMARY KEY AUTOINCREMENT,'
                    'title TEXT,content TEXT,collection TEXT,tags TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,item_hash TEXT)')
            outputs = []
            child_environment = {key: value for key, value in os.environ.items()
                                 if key.upper() in {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP',
                                                    'APPDATA', 'LOCALAPPDATA', 'USERPROFILE'}}
            child_environment.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
            for phase in ('seed', 'restart'):
                result = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()),
                                         '--worker', folder, phase], cwd=ROOT,
                                        capture_output=True, text=True, encoding='utf8', timeout=60,
                                        env=child_environment,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.assertEqual(result.returncode, 0, result.stderr[-5000:])
                outputs.append(json.loads(result.stdout))
            first, second = outputs
            self.assertNotEqual(first['pid'], second['pid'])
            for key in ('source_id', 'source_sha256', 'passage_hashes', 'route_results'):
                self.assertEqual(first[key], second[key], key)
            self.assertTrue(first['passage_hashes'])
            self.assertFalse(first['embeddings_generated'])
            self.assertEqual(first['network_attempts'] + second['network_attempts'], 0)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        print(json.dumps(asyncio.run(worker(sys.argv[2], sys.argv[3]))))
    else:
        unittest.main()
