"""Disposable real driver API; only Firebase SDK verification is synthetic."""
import ast
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    output = Path(sys.argv[1]).resolve(strict=True)
    phase = ROOT / 'backups' / 'fe_api_composition_20261114_v01'
    if output != phase and not (output.parent == phase and output.name.startswith('attempt')):
        raise RuntimeError('Owned composition output required')
    database = output / 'fixture.sqlite3'
    if database.exists():
        raise FileExistsError('Never reuse fixture data')
    os.environ['AI_BS_ENABLE_DRIVER_PORTAL'] = '1'
    os.environ['AI_BS_ADMIN_KEY'] = 'composition-fixture-local-key'
    os.environ['AI_BS_ADMIN_EMAILS'] = 'owner-a@example.test,owner-b@example.test'
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    import fe_express_owned_records as records
    from routers.fe_driver_registration import register_driver_portal
    from security import firebase_auth as auth

    def verify(token, request, audience):
        if token not in ('synthetic:owner-a', 'synthetic:owner-b'):
            raise ValueError('Invalid fixture token')
        uid = token.split(':', 1)[1]
        return {'sub': uid, 'email': uid + '@example.test',
                'email_verified': True, 'exp': time.time() + 600}

    auth.id_token = SimpleNamespace(verify_firebase_token=verify)
    auth._request = object()
    auth._token_cache.clear()
    app = FastAPI()
    assert register_driver_portal(app)
    app.dependency_overrides[records.database_path] = lambda: database
    production = ROOT / 'backend' / 'AI_BS_Backend.py'
    cors_calls = [node for node in ast.walk(ast.parse(production.read_text(encoding='utf-8-sig')))
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == 'add_middleware' and node.args
                  and isinstance(node.args[0], ast.Name) and node.args[0].id == 'CORSMiddleware']
    if len(cors_calls) != 1:
        raise RuntimeError('Exactly one literal production CORS policy required')
    cors = {item.arg: ast.literal_eval(item.value) for item in cors_calls[0].keywords}
    app.add_middleware(CORSMiddleware, **cors)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))

    def stop():
        if sys.stdin.readline().strip() == 'STOP':
            server.should_exit = True

    threading.Thread(target=stop, daemon=True).start()
    with (output / 'server-ready.json').open('x') as stream:
        json.dump({'pid': os.getpid(), 'port': sock.getsockname()[1],
                   'host': '127.0.0.1', 'database': str(database),
                   'mock_boundary': 'Firebase SDK verifier only',
                   'real_principal_contract': True,
                   'cors_policy': cors,
                   'cors_source_sha256': hashlib.sha256(production.read_bytes()).hexdigest()}, stream, indent=2)
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()
        auth._token_cache.clear()


if __name__ == '__main__':
    main()
