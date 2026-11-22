"""Offline campaign link security, honest aggregation and SMTP copy coverage."""
import hashlib
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_recdebut_delivery import client, seed, plan, dispatch, BASE, w, d


def tracked_plan(client, monkeypatch):
    profile = d.sender_profile
    monkeypatch.setattr(d, 'sender_profile', lambda channel: {
        **profile(channel), 'track_links': channel == 'email', 'copy_to': 'dennis@example.org'})
    seed()
    return plan(client)


def link_path(p, target='website'):
    return p['recipients'][0]['campaign_links'][target].split('recdebut-recruit.org')[1]


def attempt(p, state, wrong_plan=False):
    item = p['recipients'][0]
    key = w.digest({'draft_id': p['draft_id'], 'channel': 'email', 'destination': item['destination']})
    with w.connect() as db:
        db.execute('INSERT INTO recdebut_send_attempts VALUES(?,?,?,?,?,?)',
                   (key, 'different-plan' if wrong_plan else p['id'], item['person_id'], state, 'synthetic', w.now()))


def test_email_link_rendering_preserves_visible_script_and_hides_identity(client, monkeypatch):
    p = tracked_plan(client, monkeypatch); item = p['recipients'][0]
    assert set(item['campaign_links']) == {'website', 'video'}
    assert len(set(item['campaign_links'].values())) == 2
    assert 'Hi Alex,' in item['message']
    assert 'https://recdebut.com/' in item['message']
    assert 'https://youtu.be/YJoPHIWmvnQ' in item['message']
    for url in item['campaign_links'].values():
        token = url.rsplit('/', 1)[1]
        assert len(token) == 43 and 'alex' not in url and '@' not in url
        assert url in item['html_message']
        with w.connect() as db:
            row = dict(db.execute('SELECT * FROM recdebut_campaign_links WHERE token_sha256=?',
                                 (hashlib.sha256(token.encode()).hexdigest(),)).fetchone())
        assert token not in json.dumps(row)
        assert row['plan_id'] == p['id'] and row['person_id'] == item['person_id']
    assert 'alex@example.org' not in item['html_message']


@pytest.mark.parametrize('state', [None, 'RESERVED', 'ATTEMPTING', 'BLOCKED', 'UNCERTAIN'])
def test_unaccepted_links_never_record_or_promote_attempt(client, monkeypatch, state):
    p = tracked_plan(client, monkeypatch)
    if state: attempt(p, state)
    assert client.get(link_path(p), follow_redirects=False).status_code == 404
    summary = client.get(BASE + '/traffic').json()
    assert summary['total_requests'] == 0
    if state:
        with w.connect() as db:
            assert db.execute('SELECT state FROM recdebut_send_attempts').fetchone()[0] == state


def test_wrong_plan_or_changed_immutable_payload_cannot_record(client, monkeypatch):
    p = tracked_plan(client, monkeypatch); attempt(p, 'ACCEPTED', wrong_plan=True)
    assert client.get(link_path(p), follow_redirects=False).status_code == 404
    with w.connect() as db:
        db.execute('UPDATE recdebut_send_attempts SET plan_id=?', (p['id'],))
        db.execute("UPDATE recdebut_send_plans SET payload=replace(payload,'Recruiting information','Tampered')")
    assert client.get(link_path(p), follow_redirects=False).status_code == 404
    assert client.get(BASE + '/traffic').json()['total_requests'] == 0


def test_allowlist_changes_cannot_silently_retarget_accepted_links(client, monkeypatch):
    p = tracked_plan(client, monkeypatch); attempt(p, 'ACCEPTED')
    monkeypatch.setitem(d.campaign_links.TARGETS, 'website', 'https://recdebut.com/changed')
    assert client.get(link_path(p), follow_redirects=False).status_code == 404
    assert client.get(BASE + '/traffic').json()['total_requests'] == 0


def test_accepted_links_record_aggregate_requests_with_fixed_destinations(client, monkeypatch):
    p = tracked_plan(client, monkeypatch); attempt(p, 'ACCEPTED')
    with w.connect() as db:
        db.execute("UPDATE recdebut_send_plans SET state='CANCELLED'")
    for _ in range(2):
        r = client.get(link_path(p) + '?url=https://evil.example/', follow_redirects=False,
                       headers={'user-agent': 'synthetic scanner', 'x-forwarded-for': '192.0.2.77'})
        assert r.status_code == 302 and r.headers['location'] == 'https://recdebut.com/'
        assert r.headers['cache-control'] == 'no-store' and r.headers['referrer-policy'] == 'no-referrer'
    r = client.get(link_path(p, 'video'), follow_redirects=False)
    assert r.headers['location'] == 'https://youtu.be/YJoPHIWmvnQ'
    summary = client.get(BASE + '/traffic').json()
    assert summary['total_requests'] == 3
    website = next(row for row in summary['campaigns'] if row['target'] == 'website')
    assert website['requests'] == 2 and website['distinct_links'] == 1
    serialized = json.dumps(summary)
    for private in ['alex@example.org', 'synthetic scanner', '192.0.2.77', link_path(p).rsplit('/', 1)[1]]:
        assert private not in serialized
    with w.connect() as db:
        columns = {r[1] for r in db.execute('PRAGMA table_info(recdebut_campaign_link_counts)')}
    assert columns == {'token_sha256', 'request_count', 'first_requested_at', 'last_requested_at'}


def test_tracking_public_exception_does_not_expose_summary_or_writes(client, monkeypatch):
    p = tracked_plan(client, monkeypatch); attempt(p, 'ACCEPTED')
    app = FastAPI(); app.include_router(w.router, prefix='/api/v1/recdebut')
    with TestClient(app) as public:
        assert public.get(link_path(p), follow_redirects=False).status_code == 302
        assert public.get(BASE + '/traffic').status_code == 403
        assert public.post(link_path(p)).status_code in (403, 405)
        assert public.get(BASE + '/links/' + 'x' * 43).status_code == 404
        assert public.get(link_path(p) + '/extra').status_code == 404
        assert public.get(BASE + '/links/short').status_code in (403, 404)
    assert client.get(BASE + '/traffic').json()['total_requests'] == 1


def test_rendered_html_escapes_script_text(client, monkeypatch):
    p = tracked_plan(client, monkeypatch)
    with w.connect() as db:
        row = db.execute("SELECT payload FROM recdebut_workflow WHERE id='draft'").fetchone()
        payload = json.loads(row[0]); payload['body'] += '\n<script>alert("unsafe")</script>'
        db.execute("UPDATE recdebut_workflow SET payload=?, revision=2 WHERE id='draft'", (w.encode(payload),))
    preview = client.get(BASE + '/drafts/draft/preview').json()['preview']
    assert client.post(BASE + '/drafts/draft/review', json={'actor':'Reviewer', 'revision':2,
                       'expected_digest':preview['digest']}).status_code == 200
    r = client.post(BASE + '/sending/plans', json={'draft_id':'draft', 'actor':'Reviewer',
                    'expected_preview_digest':preview['digest']})
    html = r.json()['plan']['recipients'][0]['html_message']
    assert '<script>' not in html and '&lt;script&gt;' in html


@pytest.mark.parametrize('copy_to,reply_recipients', [
    ('dennis@example.org', ['staff@example.org', 'dennis@example.org']),
    ('staff@example.org', ['staff@example.org'])])
def test_staff_copy_has_separate_envelope_and_no_athlete_optout_or_tracking(monkeypatch, copy_to, reply_recipients):
    from email.utils import getaddresses
    captured = []
    class SMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): pass
        def starttls(self, **kwargs): pass
        def login(self, *args): pass
        def send_message(self, message, **kwargs): captured.append((message, kwargs)); return {}
    monkeypatch.setattr(d.smtplib, 'SMTP', SMTP)
    profile = {'provider':'smtp','sender':'staff@example.org','reply_to':'staff@example.org',
               'smtp_mode':'starttls','smtp_host':'smtp.example.org','smtp_port':'587',
               'smtp_user':'staff@example.org','smtp_password':'synthetic','copy_to':copy_to}
    item = {'destination':'alex@example.org','subject':'Review','message':'Hi Alex, exact copy',
            'html_message':'<p>Hi Alex, exact copy</p>', 'staff_copy_message':'Hi Alex, https://recdebut.com/',
            'unsubscribe_url':'https://recdebut-recruit.org/opaque'}
    assert d.send_one(profile, item, lambda: None)['state'] == 'ACCEPTED'
    message, envelope = captured[0]
    assert envelope['to_addrs'] == ['alex@example.org']
    assert message['To'] == 'alex@example.org' and message['Bcc'] is None
    assert [address for _, address in getaddresses(message.get_all('Reply-To'))] == reply_recipients
    assert message.get_body(('html',)).get_content().strip() == item['html_message']
    assert d.send_staff_copy(profile, item, 'Review', lambda: None)['state'] == 'ACCEPTED'
    copy, envelope = captured[1]
    assert envelope['to_addrs'] == [copy_to]
    assert copy['To'] == copy_to and copy['List-Unsubscribe'] is None
    assert [address for _, address in getaddresses(copy.get_all('Reply-To'))] == ['staff@example.org']
    assert item['unsubscribe_url'] not in copy.as_string() and '/workflow/links/' not in copy.as_string()
    assert 'https://recdebut.com/' in copy.get_content()
    monkeypatch.setattr(SMTP, 'send_message', lambda *args, **kwargs: {copy_to:(550,b'refused')})
    with pytest.raises(RuntimeError): d.send_staff_copy(profile, item, 'Review', lambda: None)


@pytest.mark.parametrize('copy_to', ['', 'invalid', 'dennis@example.org'])
def test_sender_profile_requires_valid_staff_copy_destination(monkeypatch, copy_to):
    monkeypatch.setenv('RECDEBUT_EMAIL_COPY_TO', copy_to)
    profile = d.sender_profile('email')
    assert ('EMAIL_COPY_DESTINATION_UNCONFIGURED' in profile['blockers']) == (copy_to != 'dennis@example.org')
    assert profile['copy_to'] == ('dennis@example.org' if copy_to == 'dennis@example.org' else '')


@pytest.mark.parametrize('copy_outcome', ['accepted', 'uncertain', 'held'])
def test_staff_copy_failure_never_retries_athlete_or_fabricates_copy_success(client, monkeypatch, copy_outcome):
    p = tracked_plan(client, monkeypatch); calls = []
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    def primary(*args):
        if copy_outcome == 'held': monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: False)
        return {'state':'ACCEPTED','receipt_id':'primary-receipt'}
    def staff(*args):
        calls.append(args)
        if copy_outcome == 'uncertain': raise TimeoutError('synthetic timeout')
        return {'state':'ACCEPTED','receipt_id':'copy-receipt'}
    monkeypatch.setattr(d, 'send_one', primary); monkeypatch.setattr(d, 'send_staff_copy', staff)
    r = dispatch(client, p); assert r.status_code == 200
    assert r.json()['recipients'][0]['state'] == 'ACCEPTED'
    expected = {'accepted':'ACCEPTED','uncertain':'UNCERTAIN','held':'BLOCKED'}[copy_outcome]
    assert r.json()['staff_copies'][0]['state'] == expected
    assert len(calls) == (0 if copy_outcome == 'held' else 1)
    assert client.get(link_path(p), follow_redirects=False).status_code == 302
    monkeypatch.setattr(d, 'outbound_messaging_enabled', lambda _: True)
    assert dispatch(client, p).status_code == 409
