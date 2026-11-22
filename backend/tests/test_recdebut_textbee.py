"""Signed synthetic intake only; never load the production application or send SMS."""
import ast
import hashlib
import hmac
import json
import sqlite3
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from test_recdebut_workflow import BASE, save
import recdebut_workflow as w
from core import outbound_messaging_policy as policy
from security import recdebut_access as access
import recdebut_textbee as intake

SECRET = 'synthetic-only-signing-secret'
PATHS = ('/api/v1/recdebut/webhooks/textbee', '/api/recdebut/webhooks/textbee', '/api/v1/recdebut/sms/inbound')


def payload(**changes):
    return dict(smsId='sms-1', deviceId='synthetic-device', webhookSubscriptionId='subscription-1',
                webhookEvent='MESSAGE_RECEIVED', idempotencyKey='delivery-1', sender='+16165550101',
                message='Please send the registration details.', receivedAt='2026-10-27T17:00:00Z', **{}) | changes


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'DB_PATH', tmp_path / 'inbound.db')
    monkeypatch.setenv('TEXTBEE_WEBHOOK_SECRET', SECRET)
    monkeypatch.setenv('TEXTBEE_DEVICE_ID', 'synthetic-device')
    monkeypatch.setenv('AI_BS_RECDEBUT_OUTBOUND_ENABLED', 'true')
    monkeypatch.setattr(access, 'verify_admin_credentials', lambda *args: False)
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: (set(), set()))
    with w.connect() as db:
        db.executescript('''CREATE TABLE rec_debut_athletes(id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, status TEXT);
            INSERT INTO rec_debut_athletes VALUES(1,'Synthetic Athlete','6165550101','','Pending');
            CREATE TABLE rec_debut_athlete_replies(id INTEGER PRIMARY KEY, athlete_id INTEGER, athlete_name TEXT,
                sender_phone TEXT, sender_email TEXT, recipient_email TEXT, subject TEXT, reply_body TEXT,
                received_at REAL, is_read INTEGER DEFAULT 0, created_at REAL, message_id_hash TEXT UNIQUE);''')
    app = FastAPI()
    # Exercise the actual decorated production handler without importing startup/seeding.
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'routers/rec_debut_router.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'handle_textbee_inbound_webhook')
    node.decorator_list = []
    namespace = dict(vars(intake))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), '<production webhook handler>', 'exec'), namespace)
    for path in PATHS:
        app.add_api_route(path, namespace[node.name], methods=['POST'], dependencies=[__import__('fastapi').Depends(access.require_recdebut_access)])
    app.include_router(w.router, prefix='/api/v1/recdebut')
    @app.middleware('http')
    async def production_auth_pattern(request, call_next):
        if request.url.path in PATHS:
            try:
                await access.require_recdebut_access(request)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
        return await call_next(request)
    with TestClient(app) as c:
        yield c


def post(client, data=None, path=PATHS[0], raw=None, signature=None):
    body = raw if raw is not None else json.dumps(data or payload()).encode()
    sig = signature if signature is not None else hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post(path, content=body, headers={'content-type': 'application/json', 'x-signature': sig})


def rows(table):
    with w.connect() as db:
        return [dict(r) for r in db.execute('SELECT * FROM ' + table)]


@pytest.mark.parametrize('path', PATHS)
def test_signed_reply_is_durable_while_hold_enabled(client, path):
    result = post(client, path=path)
    assert result.status_code == 200
    assert result.json()['status'] == 'stored'
    assert result.json()['sending_enabled'] is False and result.json()['forwarded'] is False
    assert policy.RECDEBUT_REVIEW_HOLD and not policy.outbound_messaging_enabled('recdebut')
    assert rows('rec_debut_athlete_replies')[0]['reply_body'] == payload()['message']
    assert len(rows('recdebut_textbee_receipts')) == 1


@pytest.mark.parametrize('keyword', ['STOP', ' stop \n', 'STOPALL', 'Unsubscribe', 'CANCEL', 'END', 'QUIT', 'REVOKE', 'OPT OUT', 'stop!'])
def test_unknown_stop_suppresses_without_roster_or_exclusion_service(client, monkeypatch, keyword):
    def unavailable():
        raise intake.PrivacyCheckUnavailable('Unavailable')
    monkeypatch.setattr(intake, 'load_personal_contacts', unavailable)
    result = post(client, payload(sender='+16165550199', message=keyword))
    assert result.status_code == 200 and result.json()['status'] == 'suppressed'
    assert rows('recdebut_suppressions')[0]['destination'] == '6165550199'
    assert rows('rec_debut_athlete_replies') == []


@pytest.mark.parametrize('message', ['Do not stop helping', 'unstoppable', 'STOP by tomorrow', 'START'])
def test_ordinary_text_does_not_suppress(client, message):
    assert post(client, payload(message=message)).status_code == 200
    assert rows('recdebut_suppressions') == []


def test_replays_conflicts_and_second_subscription(client):
    assert post(client).status_code == 200
    assert post(client).json()['duplicate'] is True
    assert post(client, payload(message='changed')).status_code == 409
    assert post(client, payload(idempotencyKey='delivery-2', message='changed')).status_code == 409
    result = post(client, payload(idempotencyKey='delivery-2', webhookSubscriptionId='subscription-2'))
    assert result.status_code == 200 and result.json()['duplicate'] is True
    assert len(rows('rec_debut_athlete_replies')) == 1
    assert len(rows('recdebut_textbee_receipts')) == 2


def test_stop_cannot_be_undone_by_start_or_replay(client):
    assert post(client, payload(message='STOP')).status_code == 200
    assert post(client, payload(message='STOP')).json()['duplicate'] is True
    assert post(client, payload(message='START', smsId='sms-2', idempotencyKey='delivery-2')).status_code == 200
    assert len(rows('recdebut_suppressions')) == 1


@pytest.mark.parametrize('changes', [dict(webhookEvent='MESSAGE_SENT'), dict(deviceId='wrong-device'), dict(sender='short'),
    dict(message=''), dict(message=123), dict(smsId=''), dict(idempotencyKey=''), dict(receivedAt='yesterday'),
    dict(receivedAt='2026-10-27T17:00:00'), dict(webhookSubscriptionId='')])
def test_invalid_payloads_have_no_writes(client, changes):
    assert post(client, payload(**changes)).status_code in (403, 422)
    assert rows('rec_debut_athlete_replies') == [] and rows('recdebut_suppressions') == []
    assert rows('recdebut_textbee_receipts') == []


@pytest.mark.parametrize('body', [b'not json', b'[]', b'{"sender":"a","sender":"b"}', b'x' * 65537],
                         ids=['malformed', 'array', 'duplicate-keys', 'oversized'])
def test_invalid_json_and_size(client, body):
    assert post(client, raw=body).status_code in (400, 413, 422)
    assert rows('recdebut_textbee_receipts') == []


def test_authentication_precedes_storage(client):
    assert post(client, signature='0' * 64).status_code == 401
    assert post(client, signature='').status_code == 401
    assert rows('recdebut_textbee_receipts') == []


@pytest.mark.parametrize('path', PATHS)
@pytest.mark.parametrize('signature', ['', '0' * 64], ids=['unsigned', 'invalid-signature'])
def test_admin_authority_does_not_forge_signed_provider_events(client, monkeypatch, path, signature):
    monkeypatch.setattr(access, 'verify_admin_credentials', lambda *args: True)
    assert post(client, path=path, signature=signature).status_code == 401
    assert rows('recdebut_textbee_receipts') == []


def test_storage_failure_rolls_back_and_retry_recovers(client):
    with w.connect() as db:
        db.execute("CREATE TRIGGER reject_receipt BEFORE INSERT ON recdebut_textbee_receipts BEGIN SELECT RAISE(ABORT,'synthetic storage failure'); END")
    result = post(client, payload(message='STOP'))
    assert result.status_code == 503
    assert 'synthetic storage failure' not in result.text
    assert rows('recdebut_suppressions') == [] and rows('rec_debut_athlete_replies') == []
    with w.connect() as db:
        db.execute('DROP TRIGGER reject_receipt')
    assert post(client, payload(message='STOP')).status_code == 200
    assert len(rows('recdebut_suppressions')) == 1


def test_concurrent_duplicate_has_one_commit(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: post(client), range(2)))
    assert [r.status_code for r in results] == [200, 200]
    assert sum(not r.json()['duplicate'] for r in results) == 1
    assert len(rows('rec_debut_athlete_replies')) == len(rows('recdebut_textbee_receipts')) == 1


def test_unknown_or_personal_content_is_not_added_to_dennis_feed(client, monkeypatch):
    assert post(client, payload(sender='+16165550199')).json()['status'] == 'ignored_unmatched'
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: ({'6165550101'}, set()))
    assert post(client, payload(smsId='sms-2', idempotencyKey='delivery-2')).json()['status'] == 'ignored_personal'
    assert rows('rec_debut_athlete_replies') == []
    assert all('reply_body' not in r and 'sender_phone' not in r for r in rows('recdebut_textbee_receipts'))


def test_privacy_service_failure_is_retryable_for_ordinary_reply(client, monkeypatch):
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: (_ for _ in ()).throw(intake.PrivacyCheckUnavailable('private failure')))
    assert post(client).status_code == 503
    assert rows('recdebut_textbee_receipts') == []


@pytest.mark.parametrize('damage', ['missing-roster', 'invalid-person-json', 'missing-reply-table'])
def test_stop_survives_optional_crm_failure(client, damage):
    with w.connect() as db:
        if damage == 'missing-roster':
            db.execute('DROP TABLE rec_debut_athletes')
        elif damage == 'invalid-person-json':
            db.execute("INSERT INTO recdebut_workflow VALUES('bad','person',1,'{','now')")
        else:
            db.execute('DROP TABLE rec_debut_athlete_replies')
    response = post(client, payload(message='STOP'))
    assert response.status_code == 200 and response.json()['status'] == 'suppressed'
    assert len(rows('recdebut_suppressions')) == len(rows('recdebut_textbee_receipts')) == 1


def test_commit_failure_is_not_acknowledged(client, monkeypatch):
    real_connect = w.connect
    @contextmanager
    def failing_commit():
        with real_connect() as db:
            yield db
            raise sqlite3.OperationalError('synthetic commit failure')
    monkeypatch.setattr(w, 'connect', failing_commit)
    response = post(client, payload(message='STOP'))
    assert response.status_code == 503 and response.headers['retry-after'] == '30'
    monkeypatch.setattr(w, 'connect', real_connect)
    assert rows('recdebut_suppressions') == rows('recdebut_textbee_receipts') == []
    assert post(client, payload(message='STOP')).status_code == 200


def test_family_timeline_and_common_preview_suppression(client, monkeypatch):
    client.app.dependency_overrides[access.require_recdebut_access] = lambda: None
    save(client, 'family', 'family1', {'name': 'Synthetic Family'})
    save(client, 'person', 'person1', {'name': 'Synthetic Parent', 'family_id': 'family1', 'role': 'parent', 'phone': '6165550101',
        'relationship': 'verified', 'sms_permission': 'granted', 'permission_evidence': 'Synthetic evidence'})
    save(client, 'draft', 'draft1', {'title': 'Synthetic', 'channel': 'sms', 'body': 'Draft only', 'person_ids': ['person1']})
    before = client.get(BASE + '/drafts/draft1/preview').json()['preview']
    assert post(client, payload(message='STOP')).status_code == 200
    after = client.get(BASE + '/drafts/draft1/preview').json()['preview']
    assert before['digest'] != after['digest'] and not after['reviewable']
    entries = client.get(BASE + '/families/family1/timeline').json()['entries']
    assert entries[0]['action'] == 'sms_opt_out_received'
    assert post(client, payload(message='STOP')).json()['duplicate'] is True
    assert len(client.get(BASE + '/families/family1/timeline').json()['entries']) == len(entries)
