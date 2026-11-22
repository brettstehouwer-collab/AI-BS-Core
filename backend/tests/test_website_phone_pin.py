"""Trusted infrastructure tests; no candidate or VM execution."""
import hashlib
import json
import sys
from pathlib import Path
import pytest
from fastapi import FastAPI, APIRouter, Depends
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security import website_phone_access as access
from security import fe_express_access as fe
from security.firebase_auth import get_admin_principal, verify_admin_credentials


@pytest.fixture
def store(tmp_path):
    salt = bytes(range(32))
    config = tmp_path/'website.json'
    config.write_text(json.dumps({'salt':salt.hex(), 'iterations':600000,
        'digest':hashlib.pbkdf2_hmac('sha256', b'+12025550123\x006789', salt, 600000).hex()}))
    clock = [100.0]
    return access.WebsiteSessions(config, lambda:clock[0]), clock


@pytest.mark.parametrize('phone', ['2025550123','(202) 555-0123','+1 202-555-0123','12025550123'])
def test_equivalent_phone_formats(store, phone):
    s, _ = store
    assert s.login(phone,'6789')['scope']=='website_pages'


@pytest.mark.parametrize('phone,pin', [('2025550124','6789'),('2025550123','1111'),('', '6789'),('+442025550123','6789'),('2025550123ext1','6789')])
def test_both_credentials_required(store, phone, pin):
    s, _ = store
    with pytest.raises(access.HTTPException) as exc:s.login(phone,pin)
    assert exc.value.status_code == 401


def test_scope_expiry_revocation_and_admin_denial(store, monkeypatch):
    s, clock = store
    monkeypatch.setenv('AI_BS_ADMIN_KEY','synthetic-test-admin-key')
    token = s.login('2025550123','6789')['access_token']
    auth = 'Bearer '+token
    assert s.valid(auth) and not s.valid(auth+'changed')
    assert not fe.PinSessions(s.config_path).valid(auth)
    assert not verify_admin_credentials('',auth)
    assert get_admin_principal('',auth) is None
    s.revoke(auth);assert not s.valid(auth)
    auth='Bearer '+s.login('2025550123','6789')['access_token']
    clock[0]+=s.ttl
    assert not s.valid(auth)


def test_http_contract_and_fe_scope(store, monkeypatch):
    s, _ = store
    monkeypatch.setattr(access,'sessions',s)
    app=FastAPI();app.include_router(access.router)
    router=APIRouter(prefix=fe.PREFIX,dependencies=[Depends(fe.require_fe_express_access)])
    @router.get('/test-read')
    def read():return {'ok':True}
    app.include_router(router)
    client=TestClient(app)
    assert client.get('/api/website-access/session').status_code==401
    assert client.post('/api/website-access/login',json={'pin':'6789'}).status_code==422
    response=client.post('/api/website-access/login',json={'phone':'2025550123','pin':'6789'})
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    headers={'Authorization':'Bearer '+response.json()['access_token']}
    assert client.get('/api/website-access/session',headers=headers).status_code==200
    assert client.get(fe.PREFIX+'/test-read',headers=headers).status_code==200
    assert client.post('/api/website-access/logout',headers=headers).status_code==200
    assert client.get('/api/website-access/session',headers=headers).status_code==401
    assert client.get(fe.PREFIX+'/test-read',headers=headers).status_code==401


def test_brute_force_and_missing_config(store,tmp_path):
    s,clock=store
    for _ in range(10):
        with pytest.raises(access.HTTPException):s.login('2025550123','0000')
    with pytest.raises(access.HTTPException) as exc:s.login('2025550123','6789')
    assert exc.value.status_code==429
    clock[0]+=300
    assert s.login('2025550123','6789')['scope']=='website_pages'
    with pytest.raises(access.HTTPException) as exc:access.WebsiteSessions(tmp_path/'missing').login('2025550123','6789')
    assert exc.value.status_code==503
