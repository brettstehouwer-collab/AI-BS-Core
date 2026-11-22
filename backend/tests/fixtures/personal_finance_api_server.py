"""Owned loopback API fixture; only Firebase SDK verification is synthetic."""
import ast
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'backend'))


def main():
    output = Path(sys.argv[1]).resolve(strict=True)
    if output.parent != ROOT/'backups' or not output.name.startswith('personal_phone_20261114_'):
        raise RuntimeError('Owned personal fixture output required')
    database = output/'fixture.sqlite3'
    if database.exists():
        raise FileExistsError('Preserve previous fixture data')
    os.environ.update(AI_BS_ENABLE_PERSONAL_PAYMENTS='1', AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT='1',
                      AI_BS_ADMIN_KEY='', AI_BS_ADMIN_EMAILS='owner-a@example.test,owner-b@example.test')
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    from modules import accounting_router
    from modules.personal_payments import register_personal_payments
    from modules.personal_ledger_export import register_personal_ledger
    from security import firebase_auth as auth
    accounting_router.DB_PATH = str(database)

    def verify(token, request, audience):
        if token not in ('synthetic:owner-a', 'synthetic:owner-b'):
            raise ValueError('Invalid fixture token')
        uid = token.split(':', 1)[1]
        return {'sub': uid, 'email': uid+'@example.test', 'email_verified': True, 'exp': time.time()+600}
    auth.id_token = SimpleNamespace(verify_firebase_token=verify)
    auth._request = object()
    auth._token_cache.clear()
    app = FastAPI()
    assert register_personal_payments(app) and register_personal_ledger(app)
    app.include_router(accounting_router.router)
    source = ast.parse((ROOT/'backend/AI_BS_Backend.py').read_text(encoding='utf-8-sig'))
    calls = [n for n in ast.walk(source) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == 'add_middleware' and n.args and isinstance(n.args[0], ast.Name)
             and n.args[0].id == 'CORSMiddleware']
    assert len(calls) == 1
    cors = {k.arg: ast.literal_eval(k.value) for k in calls[0].keywords}
    app.add_middleware(CORSMiddleware, **cors)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0)); sock.listen(128)
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))
    def stop():
        if sys.stdin.readline().strip() == 'STOP':
            server.should_exit = True
    threading.Thread(target=stop, daemon=True).start()
    with (output/'server-ready.json').open('x') as stream:
        json.dump({'pid': os.getpid(), 'port': sock.getsockname()[1], 'database': str(database),
                   'cors': cors, 'mock_boundary': 'Firebase SDK verifier only'}, stream)
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()


if __name__ == '__main__':
    main()
