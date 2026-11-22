"""Synthetic receiver checks: no production app, database, website or provider."""
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recdebut_registration as intake
from security.recdebut_access import require_recdebut_access

SECRET = 'synthetic-only-secret-32-characters-long'
PATH = '/api/v1/recdebut/webhooks/registration'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(intake.workflow, 'DB_PATH', tmp_path / 'synthetic.db')
    monkeypatch.setenv('RECDEBUT_REGISTRATION_SECRET', SECRET)
    monkeypatch.setenv('RECDEBUT_REGISTRATION_FORMS', 'reviewed-form')
    app = FastAPI()
    @app.middleware('http')
    async def production_access_pattern(request, call_next):
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse
        try:
            await require_recdebut_access(request)
        except HTTPException as exc:
            return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
        return await call_next(request)
    from fastapi import Depends
    app.include_router(intake.router, prefix='/api/v1/recdebut', dependencies=[Depends(require_recdebut_access)])
    with TestClient(app) as c:
        yield c


def data():
    return dict(schema_version=1, event_id='11111111-1111-4111-8111-111111111111',
                source='https://recdebut.com', form_reference='reviewed-form', athlete_name='Synthetic Athlete',
                guardian_name='Synthetic Parent', guardian_email='parent@example.test')


def post(client, payload=None, offset=0, tamper=False):
    raw=json.dumps(data() if payload is None else payload).encode()
    stamp=str(int(time.time()) + offset)
    signature=hmac.new(SECRET.encode(), stamp.encode()+b'.'+raw, hashlib.sha256).hexdigest()
    return client.post(PATH, content=raw+(b' ' if tamper else b''), headers={
        'content-type':'application/json','x-recdebut-timestamp':stamp,'x-recdebut-signature':signature})


def test_atomic_casework_and_retry(client):
    assert post(client).json()['duplicate'] is False
    assert post(client).json()['duplicate'] is True
    with intake.workflow.connect() as db:
        assert db.execute('SELECT count(*) FROM recdebut_registration_receipts').fetchone()[0] == 1
        rows=list(db.execute('SELECT kind,payload FROM recdebut_workflow'))
        assert len(rows)==4
        for row in rows:
            if row['kind']=='person':
                p=json.loads(row['payload'])
                assert p['sms_permission']==p['email_permission']==p['relationship']=='unknown'
        assert db.execute('SELECT count(*) FROM recdebut_workflow_events').fetchone()[0]==4


def test_changed_retry_conflicts(client):
    assert post(client).status_code==200
    assert post(client,{**data(),'athlete_name':'Changed'}).status_code==409


@pytest.mark.parametrize('offset',[-301,301])
def test_expired_or_future(client,offset):
    assert post(client,offset=offset).status_code==401


def test_tampering(client):
    assert post(client,tamper=True).status_code==401


def test_dormant_without_secret(client,monkeypatch):
    monkeypatch.delenv('RECDEBUT_REGISTRATION_SECRET')
    assert post(client).status_code==503


@pytest.mark.parametrize('change',[{'source':'https://other.test'}, {'consent':True},
                                 {'guardian_email':'invalid'}, {'athlete_name':' '}])
def test_invalid_submission_rolls_back(client,change):
    assert post(client,{**data(),**change}).status_code==422
    with intake.workflow.connect() as db:
        assert db.execute('SELECT count(*) FROM recdebut_workflow').fetchone()[0]==0


def test_oversized_body(client):
    assert post(client,{**data(),'athlete_name':'A'*17000}).status_code==413


def test_unsigned_rejected(client):
    assert client.post(PATH,json=data()).status_code==401


def test_form_scope(client,monkeypatch):
    assert post(client,{**data(),'form_reference':'newsletter'}).status_code==403
    monkeypatch.delenv('RECDEBUT_REGISTRATION_FORMS')
    assert post(client).status_code==503


def test_distinct_events_do_not_merge_shared_guardian(client):
    assert post(client).status_code==200
    assert post(client,{**data(),'event_id':'22222222-2222-4222-8222-222222222222'}).status_code==200
    with intake.workflow.connect() as db:
        assert db.execute("SELECT count(*) FROM recdebut_workflow WHERE kind='family'").fetchone()[0]==2
