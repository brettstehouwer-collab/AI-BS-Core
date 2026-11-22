"""Infrastructure tests: scoped PIN sessions, not guest/candidate execution."""
import hashlib
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI, APIRouter, Depends, Request
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security import fe_express_access as access


@pytest.fixture
def store(tmp_path):
    p = tmp_path / 'pin.json'
    salt = bytes(range(32))
    # Synthetic PIN differs from the configured production PIN.
    p.write_text(json.dumps({'salt': salt.hex(), 'iterations': 600000,
        'digest': hashlib.pbkdf2_hmac('sha256', b'6789', salt, 600000).hex()}))
    clock = [100.0]
    return access.PinSessions(p, lambda: clock[0]), clock


def test_wrong_pin_and_session_expiry(store):
    s, clock = store
    with pytest.raises(access.HTTPException) as e:
        s.login('1111')
    assert e.value.status_code == 401
    result = s.login('6789')
    auth = 'Bearer ' + result['access_token']
    assert result['scope'] == 'fe_express'
    assert s.valid(auth)
    assert not s.valid(auth + 'tampered')
    clock[0] += result['expires_in']
    assert not s.valid(auth)  # Exact expiry boundary is rejected.


def test_attempt_limit_and_cooldown(store):
    s, clock = store
    for _ in range(10):
        with pytest.raises(access.HTTPException) as e:
            s.login('0000')
        assert e.value.status_code == 401
    with pytest.raises(access.HTTPException) as e:
        s.login('6789')
    assert e.value.status_code == 429
    clock[0] += 300
    assert s.login('6789')['scope'] == 'fe_express'


def test_logout_and_restart_revoke(store):
    s, _ = store
    token = 'Bearer ' + s.login('6789')['access_token']
    s.revoke(token)
    assert not s.valid(token)
    token = 'Bearer ' + s.login('6789')['access_token']
    assert not access.PinSessions(s.config_path).valid(token)


def test_missing_configuration_fails_closed(tmp_path):
    with pytest.raises(access.HTTPException) as e:
        access.PinSessions(tmp_path / 'missing').login('6789')
    assert e.value.status_code == 503


def test_scoped_routes_and_no_admin_identity(store, monkeypatch):
    s, _ = store
    monkeypatch.setattr(access, 'sessions', s)
    monkeypatch.setattr(access, 'verify_admin_credentials', lambda key, auth: key == 'test-admin')
    app = FastAPI()
    router = APIRouter(prefix=access.PREFIX, dependencies=[Depends(access.require_fe_express_access)])

    @router.post('/pin/login')
    def login():
        return s.login('6789')

    @router.get('/status')
    def status():
        return {'ok': True}

    app.include_router(router)

    @app.get('/admin')
    def admin(request: Request):
        if not access.verify_admin_credentials('', request.headers.get('authorization', '')):
            raise access.HTTPException(403)
        return {'admin': True}

    client = TestClient(app)
    assert client.get(access.PREFIX + '/status').status_code == 401
    token = client.post(access.PREFIX + '/pin/login').json()['access_token']
    headers = {'Authorization': 'Bearer ' + token}
    assert client.get(access.PREFIX + '/status', headers=headers).status_code == 200
    assert client.get('/admin', headers=headers).status_code == 403
    assert client.get(access.PREFIX + '/status', headers={'X-Admin-Key': 'test-admin'}).status_code == 200
    assert client.get(access.PREFIX + '/pin/login').status_code == 405


def test_concurrent_tokens_unique_and_bounded(store):
    s, _ = store
    with ThreadPoolExecutor(max_workers=3) as pool:
        tokens = list(pool.map(lambda _: s.login('6789')['access_token'], range(3)))
    assert len(set(tokens)) == 3
    s.sessions = {str(i): 100000 for i in range(128)}
    with pytest.raises(access.HTTPException) as e:
        s.login('6789')
    assert e.value.status_code == 429
