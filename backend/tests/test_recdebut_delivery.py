"""Provider-free exact-audience delivery and public opt-out regression tests."""
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recdebut_workflow as w
import recdebut_delivery as d


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'DB_PATH', tmp_path / 'delivery.db')
    monkeypatch.setattr(d, 'load_personal_contacts', lambda: (set(), set()))
    monkeypatch.setattr(d, 'sender_profile', lambda channel: {
        'channel': channel, 'provider': 'smtp' if channel == 'email' else 'textbee',
        'sender': 'staff@example.org' if channel == 'email' else '6165550199',
        'reply_to': 'staff@example.org', 'postal_address': '123 Example St, Example, MI 49000',
        'unsubscribe_base': 'https://recdebut-recruit.org', 'configuration_digest': 'a' * 64,
        'blockers': []})
    app = FastAPI(); app.include_router(w.router, prefix='/api/v1/recdebut')
    app.dependency_overrides[w.require_recdebut_access] = lambda: None
    with TestClient(app) as c:
        yield c


BASE = '/api/v1/recdebut/workflow'


def seed(channel='email'):
    with w.connect() as db:
        rows = [('family', 'family', {'name': 'Example household'}),
                ('person', 'person', {'name': 'Alex Parent', 'role': 'parent', 'family_id': 'family',
                 'relationship': 'verified', 'email': 'alex@example.org', 'phone': '6165550101',
                 'source': 'Registration', 'email_permission': 'granted', 'sms_permission': 'granted',
                 'permission_evidence': 'Verified form consent'}),
                ('draft', 'draft', {'title': 'Recruiting information', 'channel': channel,
                 'body': 'Hi {first_name}, see https://recdebut.com/ and https://youtu.be/YJoPHIWmvnQ. Reply STOP to opt out.',
                 'person_ids': ['person']})]
        for id, kind, payload in rows:
            db.execute('INSERT INTO recdebut_workflow VALUES(?,?,?,?,?)', (id, kind, 1, w.encode(payload), w.now()))


def plan(c):
    p = c.get(BASE + '/drafts/draft/preview').json()['preview']
    assert c.post(BASE + '/drafts/draft/review', json={'actor': 'Reviewer', 'revision': 1,
                    'expected_digest': p['digest']}).status_code == 200
    r = c.post(BASE + '/sending/plans', json={'draft_id': 'draft', 'expected_preview_digest': p['digest'], 'actor': 'Reviewer'})
    assert r.status_code == 200, r.text
    return r.json()['plan']


def dispatch(c, p):
    return c.post(BASE + '/sending/plans/' + p['id'] + '/dispatch',
                  json={'expected_digest': p['digest'], 'actor': 'Operator'})


def test_closed_gate_never_calls_provider(client, monkeypatch):
    seed(); p = plan(client)
    monkeypatch.setattr(d, 'send_one', lambda *args: pytest.fail('Provider reached while held'))
    r = dispatch(client, p)
    assert r.status_code == 423
    assert r.json()['detail']['code'] == 'SENDING_DISABLED'


def test_exact_rendered_email_has_address_and_working_opt_out(client):
    seed(); p = plan(client)
    body = p['recipients'][0]['message']
    assert 'Hi Alex,' in body and '{first_name}' not in body
    assert '123 Example St' in body and 'Promotional information from Recreational Debut' in body
    path = p['recipients'][0]['unsubscribe_url'].split('recdebut-recruit.org')[1]
    assert 'alex@' not in path
    assert client.get(path).status_code == 200
    with w.connect() as db:
        assert db.execute('SELECT count(*) FROM recdebut_suppressions').fetchone()[0] == 0
    for _ in range(2):
        assert client.post(path).status_code == 200
    with w.connect() as db:
        assert db.execute('SELECT count(*) FROM recdebut_suppressions').fetchone()[0] == 1
        assert db.execute('SELECT destination FROM recdebut_suppressions').fetchone()[0] == 'alex@example.org'
    assert client.get(BASE + '/drafts/draft/preview').json()['preview']['reviewable'] is False


def test_missing_address_blocks_plan_without_fabricating_one(client, monkeypatch):
    seed(); profile = d.sender_profile('email'); profile['postal_address'] = ''; profile['blockers'] = ['MAILING_ADDRESS_MISSING']
    monkeypatch.setattr(d, 'sender_profile', lambda _: profile)
    readiness = client.get(BASE + '/sending/readiness').json()
    assert not readiness['sending_enabled']
    assert 'MAILING_ADDRESS_MISSING' in readiness['channels']['email']['blockers']
    p = client.get(BASE + '/drafts/draft/preview').json()['preview']
    r = client.post(BASE + '/sending/plans', json={'draft_id': 'draft', 'expected_preview_digest': p['digest'], 'actor': 'Reviewer'})
    assert r.status_code == 422


@pytest.mark.parametrize('change', ['draft', 'contact', 'suppression', 'coach', 'personal', 'configuration', 'duplicate_name'])
def test_changed_inputs_block_before_provider(client, monkeypatch, change):
    seed(); p = plan(client)
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    monkeypatch.setattr(d, 'send_one', lambda *args: pytest.fail('Stale input reached provider'))
    with w.connect() as db:
        if change in ('draft', 'contact'):
            db.execute('UPDATE recdebut_workflow SET revision=2 WHERE id=?', ('draft' if change == 'draft' else 'person',))
        elif change == 'suppression':
            db.execute('INSERT INTO recdebut_suppressions VALUES(?,?,?,?)', ('alex@example.org', 'STOP', 'test', w.now()))
        elif change == 'coach':
            db.execute('CREATE TABLE rec_debut_coaches(coach_name TEXT,coach_email TEXT,coach_phone TEXT)')
            db.execute('INSERT INTO rec_debut_coaches VALUES(?,?,?)', ('Different Name', 'alex@example.org', ''))
        elif change == 'duplicate_name':
            db.execute('CREATE TABLE rec_debut_athletes(name TEXT,email TEXT,phone TEXT)')
            db.execute('INSERT INTO rec_debut_athletes VALUES(?,?,?)', ('Someone Else', 'alex@example.org', ''))
    if change == 'personal': monkeypatch.setattr(d, 'load_personal_contacts', lambda: (set(), {'alex@example.org'}))
    if change == 'configuration':
        profile = d.sender_profile('email'); profile['configuration_digest'] = 'b' * 64
        monkeypatch.setattr(d, 'sender_profile', lambda _: profile)
    r = dispatch(client, p)
    assert r.status_code == 409


def test_queue_receipt_is_not_delivery_and_replay_cannot_resend(client, monkeypatch):
    seed('sms'); p = plan(client); calls = []
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    monkeypatch.setattr(d, 'send_one', lambda *args: calls.append(args) or {'state': 'ACCEPTED', 'receipt_id': 'batch-123'})
    r = dispatch(client, p)
    assert r.status_code == 200 and r.json()['state'] == 'COMPLETED'
    assert r.json()['recipients'][0]['state'] == 'ACCEPTED'
    assert 'DELIVERED' not in r.text
    assert dispatch(client, p).status_code == 409
    assert len(calls) == 1


def test_uncertain_result_not_retried_or_replanned(client, monkeypatch):
    seed('sms'); p = plan(client); calls = []
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    def uncertain(*args):
        calls.append(args); raise TimeoutError('Do not expose provider details')
    monkeypatch.setattr(d, 'send_one', uncertain)
    r = dispatch(client, p)
    assert r.json()['recipients'][0]['state'] == 'UNCERTAIN'
    assert 'Do not expose' not in r.text
    assert dispatch(client, p).status_code == 409 and len(calls) == 1
    p2 = plan(client)
    assert dispatch(client, p2).status_code == 409 and len(calls) == 1


def test_unsubscribe_public_exception_is_exact_and_private_routes_stay_private(client, tmp_path, monkeypatch):
    seed(); p = plan(client); path = p['recipients'][0]['unsubscribe_url'].split('recdebut-recruit.org')[1]
    app = FastAPI(); app.include_router(w.router, prefix='/api/v1/recdebut')
    with TestClient(app) as public:
        assert public.get(path).status_code == 200
        assert public.post(path).status_code == 200
        assert public.get(BASE + '/sending/readiness').status_code == 403
        assert public.get(BASE + '/sending/plans/' + p['id']).status_code == 403
        assert public.get(path + '/extra').status_code == 404
        assert public.post(BASE + '/unsubscribe/' + 'x' * 43).status_code == 404


def test_textbee_adapter_requires_current_exact_sim_and_reports_only_accepted(monkeypatch):
    calls = []
    class Reply:
        def __init__(self, data): self.data = data
        def raise_for_status(self): pass
        def json(self): return self.data
    class HTTP:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, **kw):
            return Reply({'data': {'_id': 'device1', 'enabled': True, 'simInfo': {'sims': [{'subscriptionId': 8}]}}})
        def post(self, url, **kw):
            calls.append((url, kw)); return Reply({'data': {'success': True, 'smsBatchId': 'batch1'}})
    monkeypatch.setattr(d.httpx, 'Client', HTTP)
    profile = {'provider': 'textbee', 'device_id': 'device1', 'sim_subscription_id': 8, 'api_key': 'synthetic'}
    assert d.send_one(profile, {'destination': '6165550101', 'message': 'Test'}, lambda: None)['state'] == 'ACCEPTED'
    assert calls[0][0] == 'https://api.textbee.dev/api/v1/gateway/send-sms'
    assert calls[0][1]['json']['simSubscriptionId'] == 8
    assert calls[0][1]['json']['deviceId'] == 'device1'
    calls.clear(); profile['sim_subscription_id'] = 9
    with pytest.raises(d.DeliveryBlocked): d.send_one(profile, {'destination': '6165550101', 'message': 'Test'}, lambda: None)
    assert calls == []


def test_cancelled_plan_never_calls_provider(client, monkeypatch):
    seed('sms'); p = plan(client)
    assert client.post(BASE + '/sending/plans/' + p['id'] + '/cancel', json={'expected_digest': p['digest'], 'actor': 'Operator'}).status_code == 200
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    monkeypatch.setattr(d, 'send_one', lambda *args: pytest.fail('Cancelled plan sent'))
    assert dispatch(client, p).status_code == 409


def test_missing_permissions_and_privacy_failure_block_without_provider(client, monkeypatch):
    seed()
    with w.connect() as db:
        row = db.execute("SELECT payload FROM recdebut_workflow WHERE id='person'").fetchone()
        payload = json.loads(row[0]); payload['email_permission'] = 'unknown'
        db.execute("UPDATE recdebut_workflow SET payload=? WHERE id='person'", (w.encode(payload),))
    assert client.get(BASE + '/sending/readiness').json()['drafts'][0]['eligible'] == 0
    def unavailable(): raise d.PrivacyCheckUnavailable('Missing private contact source')
    monkeypatch.setattr(d, 'load_personal_contacts', unavailable)
    r = client.get(BASE + '/sending/readiness')
    assert r.status_code == 503 and 'Missing private' not in r.text


def test_email_uses_only_explicit_tls_sender_and_no_fallback(monkeypatch):
    operations = []
    class SMTP:
        def __init__(self, host, port, **kw): operations.append(('connect', host, port))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): operations.append('ehlo')
        def starttls(self, **kw): operations.append('tls')
        def login(self, user, password): operations.append(('login', user))
        def send_message(self, message, **kw):
            operations.append(('send', message, kw)); return {}
    monkeypatch.setattr(d.smtplib, 'SMTP', SMTP)
    profile = {'provider': 'smtp', 'sender': 'sender@example.org', 'reply_to': 'reply@example.org',
               'smtp_mode': 'starttls', 'smtp_host': 'smtp.example.org', 'smtp_port': '587',
               'smtp_user': 'sender@example.org', 'smtp_password': 'synthetic'}
    result = d.send_one(profile, {'destination': 'alex@example.org', 'subject': 'Review',
                        'message': 'Exact reviewed message', 'unsubscribe_url': 'https://recdebut-recruit.org/opaque'}, lambda: None)
    assert operations[:5] == [('connect', 'smtp.example.org', 587), 'ehlo', 'tls', 'ehlo', ('login', 'sender@example.org')]
    message = operations[5][1]
    assert message['Reply-To'] == 'reply@example.org'
    assert operations[5][2] == {'from_addr': 'sender@example.org', 'to_addrs': ['alex@example.org']}
    assert 'List-Unsubscribe-Post' not in message
    assert result['state'] == 'ACCEPTED'


def test_interrupted_reservation_remains_ambiguous_and_cannot_replay(client, monkeypatch):
    seed('sms'); p = plan(client)
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    def interruption(*args): raise KeyboardInterrupt()
    monkeypatch.setattr(d, 'send_one', interruption)
    with pytest.raises(KeyboardInterrupt): d.dispatch(p['id'], d.ExactAction(expected_digest=p['digest'], actor='Operator'))
    state = client.get(BASE + '/sending/plans/' + p['id']).json()
    assert state['state'] == 'RUNNING' and state['recipients'][0]['state'] == 'ATTEMPTING'
    assert dispatch(client, p).status_code == 409
    p2 = plan(client)
    assert dispatch(client, p2).status_code == 409


def test_new_contact_revision_does_not_bypass_existing_recipient_reservation(client, monkeypatch):
    seed('sms'); p = plan(client)
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    monkeypatch.setattr(d, 'send_one', lambda *args: {'state': 'ACCEPTED', 'receipt_id': 'batch-1'})
    assert dispatch(client, p).status_code == 200
    with w.connect() as db: db.execute("UPDATE recdebut_workflow SET revision=2 WHERE id='person'")
    p2 = plan(client)
    assert dispatch(client, p2).status_code == 409


@pytest.mark.parametrize('signal', ['bounced', 'personal_link', 'historic_stop'])
def test_legacy_audit_exclusions_also_block_dispatch(client, monkeypatch, signal):
    seed(); p = plan(client)
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    monkeypatch.setattr(d, 'send_one', lambda *args: pytest.fail('Excluded recipient reached provider'))
    with w.connect() as db:
        if signal in ('bounced', 'personal_link'):
            db.execute('CREATE TABLE rec_debut_athletes(name TEXT,email TEXT,phone TEXT,email_status TEXT)')
            db.execute('INSERT INTO rec_debut_athletes VALUES(?,?,?,?)',
                       ('Alex Parent', 'alex@example.org', '6164023628' if signal == 'personal_link' else '6165550101',
                        'BOUNCED' if signal == 'bounced' else ''))
        else:
            db.execute('CREATE TABLE rec_debut_athlete_replies(sender_email TEXT,sender_phone TEXT,subject TEXT,reply_body TEXT)')
            db.execute('INSERT INTO rec_debut_athlete_replies VALUES(?,?,?,?)', ('alex@example.org', '', 'Re: Info', 'STOP'))
    assert client.get(BASE + '/sending/readiness').json()['drafts'][0]['eligible'] == 0
    assert dispatch(client, p).status_code == 409


@pytest.mark.parametrize('address', ['a..b@example.org', '.alex@example.org', 'alex@example..org', 'alex@-example.org'])
def test_delivery_uses_strict_canonical_email_validation(address):
    assert d.email_address(address) == ''


def test_cancellation_during_smtp_login_blocks_final_submission(client, monkeypatch):
    seed(); p = plan(client)
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    profile = d.sender_profile('email')
    profile.update(smtp_mode='starttls', smtp_host='smtp.example.org', smtp_port='587',
                   smtp_user='staff@example.org', smtp_password='synthetic')
    monkeypatch.setattr(d, 'sender_profile', lambda _: profile)
    class SMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): pass
        def starttls(self, **kwargs): pass
        def login(self, *args):
            assert client.post(BASE + '/sending/plans/' + p['id'] + '/cancel',
                json={'expected_digest': p['digest'], 'actor': 'Reviewer'}).status_code == 200
        def send_message(self, *args, **kwargs): pytest.fail('Cancelled plan submitted to SMTP')
    monkeypatch.setattr(d.smtplib, 'SMTP', SMTP)
    result = dispatch(client, p)
    assert result.status_code == 200
    assert result.json()['state'] == 'CANCELLED'
    assert result.json()['recipients'][0]['state'] == 'BLOCKED'


@pytest.mark.parametrize('problem', ['unbound', 'changed_sim', 'stale', 'future', 'valid'])
def test_sms_identity_requires_recent_exact_device_sim_number_attestation(monkeypatch, problem):
    from datetime import datetime, timedelta, timezone
    monkeypatch.setenv('TEXTBEE_DEVICE_ID', 'synthetic-device')
    monkeypatch.setenv('TEXTBEE_API_KEY', 'synthetic-credential')
    monkeypatch.setenv('RECDEBUT_SMS_SENDER', '6165550199')
    monkeypatch.setenv('RECDEBUT_TEXTBEE_SIM_SUBSCRIPTION_ID', '7')
    verified = datetime.now(timezone.utc)
    if problem == 'stale': verified -= timedelta(days=2)
    if problem == 'future': verified += timedelta(hours=1)
    monkeypatch.setenv('RECDEBUT_SMS_IDENTITY_VERIFIED_AT', verified.isoformat())
    binding = w.digest({'device_id': 'synthetic-device', 'sim_subscription_id': 8 if problem == 'changed_sim' else 7,
                        'sender': '6165550199'})
    monkeypatch.setenv('RECDEBUT_SMS_IDENTITY_BINDING', '' if problem == 'unbound' else binding)
    assert ('SMS_DEVICE_SIM_SENDER_UNVERIFIED' in d.sender_profile('sms')['blockers']) == (problem != 'valid')
