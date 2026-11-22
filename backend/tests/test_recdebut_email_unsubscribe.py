"""Synthetic receive-only email opt-outs; no live inbox or sender is imported."""
import ast
import email
import json
import re
import time
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

import recdebut_workflow as workflow
import recdebut_email_unsubscribe as intake


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, 'DB_PATH', tmp_path / 'email-opt-outs.db')
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: (set(), set()))
    with workflow.connect() as db:
        db.execute('CREATE TABLE rec_debut_athletes(id INTEGER PRIMARY KEY,name TEXT,email TEXT,phone TEXT)')
        db.execute('INSERT INTO rec_debut_athletes VALUES(1,?,?,?)',
                   ('Synthetic Athlete', 'Athlete+Recruit@example.org', '6165550101'))
        db.execute('INSERT INTO recdebut_workflow VALUES(?,?,?,?,?)',
                   ('parent-1', 'person', 1, json.dumps({'name': 'Synthetic Parent',
                    'email': 'parent@example.org', 'phone': '6165550102', 'role': 'parent'}), workflow.now()))
    return workflow.DB_PATH


def rows(table):
    with workflow.connect() as db:
        return [dict(row) for row in db.execute('SELECT * FROM ' + table)]


@pytest.mark.parametrize('subject,body', [
    ('unsubscribe', ''), (' Re: UNSUBSCRIBE ', 'Old campaign follows'),
    ('', 'STOP'), ('', '\n unsubscribe!\n\n> Old campaign'),
    ('', 'Unsubscribe\n\nOn Tuesday someone wrote:\n> Old campaign'),
])
def test_exact_intent_from_subject_or_leading_reply(database, subject, body):
    result = intake.process_email_opt_out(' Parent@Example.org ', subject, body)
    assert result['handled'] and result['success'] and result['status'] == 'suppressed'
    assert result['channel'] == 'email' and result['forwarded'] is False
    assert result['sending_enabled'] is False
    assert rows('recdebut_suppressions')[0]['destination'] == 'parent@example.org'
    assert len(rows('recdebut_workflow_events')) == 1


@pytest.mark.parametrize('subject,body', [
    ('unsubscribe', 'x' * 100000), ('Re: STOP', 'x' * 100000),
    ('Question', 'STOP\n\n> ' + 'old content ' * 10000),
], ids=['subject-unsubscribe-long-body', 'subject-stop-long-body', 'leading-stop-long-quote'])
def test_exact_intent_not_disabled_by_long_quoted_body(database, subject, body):
    assert intake.process_email_opt_out('parent@example.org', subject, body)['success']


@pytest.mark.parametrize('subject,body', [
    ('Question about unsubscribe links', 'Please send details'),
    ('', '> unsubscribe'), ('', 'On Tuesday someone wrote:\nUNSUBSCRIBE'),
    ('', 'Please send details\n\n> STOP'), ('Re: Campaign', 'Thanks\nUNSUBSCRIBE'),
    ('', 'Do not unsubscribe'), ('', 'STOP by tomorrow'), ('', 'unstoppable'),
    ('', '<blockquote>UNSUBSCRIBE</blockquote>'),
])
def test_quoted_or_nonexact_old_text_does_not_opt_out(database, subject, body):
    assert intake.process_email_opt_out('parent@example.org', subject, body)['handled'] is False
    assert rows('recdebut_suppressions') == []
    assert rows('recdebut_workflow_events') == []


@pytest.mark.parametrize('sender', [
    '', 'invalid', 'a@@example.org', 'parent@example.org\r\nBcc: other@example.org',
    'Name <parent@example.org>', 'parent@example.org,other@example.org',
    'parent@-example.org', 'parent@example..org', 'parent@example.org.',
])
def test_malformed_email_is_denied_without_storage(database, sender):
    result = intake.process_email_opt_out(sender, 'unsubscribe', 'private content')
    assert result['handled'] and not result['success']
    assert result['status'] == 'invalid_sender'
    assert rows('recdebut_suppressions') == []


def test_known_legacy_athlete_normalizes_and_idempotent_common_suppression(database):
    first = intake.process_email_opt_out('ATHLETE+RECRUIT@EXAMPLE.ORG', '', 'STOP')
    second = intake.process_email_opt_out('athlete+recruit@example.org', 'unsubscribe', 'private reply')
    assert first['status'] == second['status'] == 'suppressed'
    assert first['already_suppressed'] is False and second['already_suppressed'] is True
    assert len(rows('recdebut_suppressions')) == len(rows('recdebut_workflow_events')) == 1
    assert 'private reply' not in database.read_bytes().decode('utf-8', errors='ignore')


def test_existing_suppression_preserved(database):
    with workflow.connect() as db:
        db.execute('INSERT INTO recdebut_suppressions VALUES(?,?,?,?)',
                   ('parent@example.org', 'Earlier request', 'staff', workflow.now()))
    result = intake.process_email_opt_out('parent@example.org', 'unsubscribe', '')
    assert result['already_suppressed']
    assert rows('recdebut_suppressions')[0]['reason'] == 'Earlier request'
    assert rows('recdebut_workflow_events') == []


def test_concurrent_duplicate_opt_out_creates_one_common_suppression_and_event(database):
    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(lambda _: intake.process_email_opt_out('parent@example.org', 'unsubscribe', ''), range(8)))
    assert all(result['success'] for result in results)
    assert sum(not result['already_suppressed'] for result in results) == 1
    assert len(rows('recdebut_suppressions')) == len(rows('recdebut_workflow_events')) == 1


def test_unknown_or_personal_email_does_not_store_private_content(database, monkeypatch):
    unknown = intake.process_email_opt_out('unknown@example.org', '', 'STOP')
    assert unknown['status'] == 'unknown_contact' and not unknown['success']
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: (set(), {'parent@example.org'}))
    personal = intake.process_email_opt_out('parent@example.org', 'unsubscribe', 'private content')
    assert personal['status'] == 'personal_contact' and not personal['success']
    assert rows('recdebut_suppressions') == []
    assert rows('recdebut_workflow_events') == []


def test_personal_phone_overlap_and_unavailable_exclusions_fail_closed(database, monkeypatch):
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: ({'6165550102'}, set()))
    assert intake.process_email_opt_out('parent@example.org', '', 'STOP')['status'] == 'personal_contact'
    def unavailable():
        raise intake.PrivacyCheckUnavailable('Synthetic unavailable exclusions')
    monkeypatch.setattr(intake, 'load_personal_contacts', unavailable)
    assert intake.process_email_opt_out('parent@example.org', '', 'STOP')['status'] == 'privacy_unavailable'
    assert rows('recdebut_suppressions') == []


def load_router_function(name, namespace):
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'routers/rec_debut_router.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    scope = {'Dict': Dict, 'Any': Any, 'Optional': Optional} | namespace
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), '<production router function>', 'exec'), scope)
    return scope[name]


def test_actual_router_processes_unsubscribe_before_disabled_forwarding_gate(database):
    def blocked():
        raise RuntimeError('Outbound disabled')
    handler = load_router_function('process_inbound_reply', {'_require_recdebut_outbound': blocked})
    result = handler('', 'parent@example.org', 'Old campaign', source='imap_mms', raw_meta={'subject': 'unsubscribe'})
    assert result['status'] == 'suppressed' and result['forwarded'] is False
    assert len(rows('recdebut_suppressions')) == 1
    with pytest.raises(RuntimeError, match='Outbound disabled'):
        handler('', 'parent@example.org', 'A normal reply', source='imap_mms')


@pytest.mark.parametrize('receive_only', [True, False])
def test_actual_imap_opt_out_never_calls_forwarding(database, receive_only):
    message = EmailMessage()
    message['From'] = 'Synthetic Parent <parent@example.org>'
    message['To'] = 'receiving@example.org'
    message['Subject'] = 'unsubscribe'
    message.set_content('private material must not be retained')
    calls = []
    class FakeIMAP:
        def __init__(self, *args, **kwargs): calls.append('connect')
        def login(self, *args): return 'OK', []
        def select(self, *args, **kwargs):
            assert kwargs == {'readonly': True}
            return 'OK', []
        def search(self, *args):
            assert not receive_only, 'Receive-only must use durable UID progression'
            return 'OK', [b'1']
        def fetch(self, *args):
            assert not receive_only, 'Receive-only must use bounded UID partial reads'
            return 'OK', [(b'', message.as_bytes())]
        def response(self, key):
            return key, [b'7' if key == 'UIDVALIDITY' else b'2']
        def uid(self, operation, *args):
            mailbox = UIDMailbox({1: message.as_bytes()})
            return mailbox.uid(operation, *args)
        def logout(self): calls.append('logout')
    def forbidden(*args, **kwargs):
        raise AssertionError('Receive-only ingestion must not enter outbound or forwarding')
    inbound = load_router_function('process_inbound_reply', {'_require_recdebut_outbound': forbidden})
    handler = load_router_function('sync_imap_inbound_messages', {
        '_require_recdebut_outbound': forbidden if receive_only else lambda: None,
        'process_inbound_reply': forbidden if receive_only else inbound,
        'load_credentials': lambda: {'IMAP_USER': 'synthetic', 'IMAP_APP_PASSWORD': 'synthetic'},
        'imaplib': SimpleNamespace(IMAP4_SSL=FakeIMAP), 'email': email, 're': re, 'time': time,
        'decode_mime_words': lambda text: text,
        'extract_email_body': lambda msg: msg.get_payload(decode=True).decode(),
    })
    result = handler(receive_only=receive_only)
    assert result['success'] and result['new_replies_forwarded'] == 0
    assert result['email_opt_outs_processed'] == 1 and result['receive_only'] is receive_only
    assert calls == ['connect', 'logout']
    assert rows('recdebut_suppressions')[0]['destination'] == 'parent@example.org'
    assert 'private material' not in database.read_bytes().decode('utf-8', errors='ignore')
    replay = handler(receive_only=receive_only)
    assert replay['success'] and replay['email_opt_outs_processed'] == 0
    assert replay['email_opt_outs_already_suppressed'] == (0 if receive_only else 1)
    assert replay['items'] == []


def synthetic_mail(sender='parent@example.org', subject='A question', body='STOP', uid=1):
    message = EmailMessage()
    message['From'] = sender
    message['To'] = 'receiving@example.org'
    message['Subject'] = subject
    message['Date'] = 'Mon, 01 Jan 1990 00:00:00 +0000'
    message.set_content(body)
    return message.as_bytes()


class UIDMailbox:
    def __init__(self, messages, validity=7, next_uid=None):
        self.messages = messages
        self.validity = validity
        self.next_uid = next_uid if next_uid is not None else max(messages, default=0) + 1
        self.calls = []
        self.fail_uid = None
    def response(self, key):
        return key, [str(self.validity if key == 'UIDVALIDITY' else self.next_uid).encode()]
    def uid(self, operation, *args):
        self.calls.append((operation, args))
        if operation == 'search':
            lower, upper = (int(value) for value in args[-1].removeprefix('UID ').split(':'))
            return 'OK', [' '.join(str(uid) for uid in self.messages if lower <= uid <= upper).encode()]
        uid = int(args[0])
        if uid == self.fail_uid:
            return 'NO', [b'synthetic failure']
        request = args[-1]
        size = int(re.search(r'<0\.(\d+)>', request).group(1))
        raw = self.messages[uid]
        if 'HEADER.FIELDS' in request:
            message = email.message_from_bytes(raw)
            raw = ('From: ' + message.get('From', '') + '\r\nSubject: ' + message.get('Subject', '') + '\r\n\r\n').encode()
        literal = raw[:size]
        return 'OK', [(f'1 (UID {uid} RFC822.SIZE {len(self.messages[uid])} BODY[] {{{len(literal)}}}'.encode(), literal), b')']


def test_uid_scan_finds_body_only_stop_and_never_stores_body_or_sender_date(database):
    mailbox = UIDMailbox({12: synthetic_mail(body='STOP\n\nprivate quoted content')})
    result = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert result['success'] and result['email_opt_outs_processed'] == 1
    assert result['new_replies_forwarded'] == 0 and result['receive_only']
    assert result['last_uid'] == 12 and result['messages_scanned'] == 1
    assert all('BODY.PEEK' in call[1][-1] for call in mailbox.calls if call[0] == 'fetch')
    assert 'private quoted content' not in database.read_bytes().decode(errors='ignore')
    assert rows('recdebut_suppressions')[0]['created_at'][:4] != '1990'


def test_uid_cursor_ascending_bounded_and_replay_counters(database):
    messages = {uid: synthetic_mail() for uid in reversed(range(1, 62))}
    mailbox = UIDMailbox(messages)
    first = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox', max_messages=50)
    assert first['last_uid'] == 50 and first['messages_scanned'] == 50
    assert first['email_opt_outs_processed'] == 1
    assert first['email_opt_outs_already_suppressed'] == 49
    second = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox', max_messages=50)
    assert second['last_uid'] == 61 and second['messages_scanned'] == 11
    assert second['email_opt_outs_processed'] == 0 and second['email_opt_outs_already_suppressed'] == 11
    third = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert third['messages_scanned'] == third['email_opt_outs_processed'] == 0
    assert len(rows('recdebut_workflow_events')) == 1


def test_unknown_personal_excluded_before_body_fetch(database, monkeypatch):
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: (set(), {'parent@example.org'}))
    mailbox = UIDMailbox({1: synthetic_mail('unknown@example.org', body='private unknown'),
                          2: synthetic_mail('parent@example.org', body='private personal')})
    result = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert result['success'] and result['messages_scanned'] == 2
    assert all('HEADER.FIELDS' in args[-1] for op, args in mailbox.calls if op == 'fetch')
    assert rows('recdebut_suppressions') == []
    assert rows('recdebut_workflow_events') == []
    raw_db = database.read_bytes().decode(errors='ignore')
    assert 'private unknown' not in raw_db and 'private personal' not in raw_db
    assert 'synthetic-mailbox' not in raw_db


def test_unavailable_personal_exclusions_prevent_mailbox_access(database, monkeypatch):
    def unavailable():
        raise intake.PrivacyCheckUnavailable('synthetic')
    monkeypatch.setattr(intake, 'load_personal_contacts', unavailable)
    mailbox = UIDMailbox({1: synthetic_mail()})
    result = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert not result['success'] and result['status'] == 'privacy_unavailable'
    assert mailbox.calls == [] and rows('recdebut_suppressions') == []


def test_subject_opt_out_skips_body_and_ignores_duplicate_counters(database):
    mailbox = UIDMailbox({1: synthetic_mail(subject='unsubscribe', body='x' * 200000)})
    first = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert first['email_opt_outs_processed'] == 1
    assert all('HEADER.FIELDS' in args[-1] for op, args in mailbox.calls if op == 'fetch')
    # A new UID containing the same request must not report another new opt-out.
    mailbox.messages[2] = mailbox.messages[1]
    mailbox.next_uid = 3
    second = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert second['email_opt_outs_processed'] == 0 and second['email_opt_outs_already_suppressed'] == 1


def test_fetch_failure_retains_prior_progress_and_releases_lease(database):
    mailbox = UIDMailbox({1: synthetic_mail(), 2: synthetic_mail('athlete+recruit@example.org')})
    mailbox.fail_uid = 2
    failed = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert not failed['success'] and failed['last_uid'] == 1
    mailbox.fail_uid = None
    retried = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert retried['success'] and retried['last_uid'] == 2
    assert retried['email_opt_outs_processed'] == 1 and len(rows('recdebut_suppressions')) == 2


def test_empty_uid_windows_are_bounded_and_uidvalidity_change_restarts_scan(database):
    mailbox = UIDMailbox({1001: synthetic_mail()})
    first = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert first['last_uid'] == 1000 and first['messages_scanned'] == 0
    second = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert second['last_uid'] == 1001 and second['email_opt_outs_processed'] == 1
    replacement = UIDMailbox({1: synthetic_mail('athlete+recruit@example.org')}, validity=8)
    reset = intake.sync_receive_only_mailbox(replacement, 'synthetic-mailbox')
    assert reset['last_uid'] == 1 and reset['email_opt_outs_processed'] == 1


def test_busy_mailbox_lease_and_expired_recovery(database):
    mailbox = UIDMailbox({1: synthetic_mail()})
    assert intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')['success']
    with workflow.connect() as db:
        db.execute('UPDATE recdebut_email_inbox_progress SET lease_owner=?,lease_until=?', ('other-run', time.time() + 300))
    mailbox.calls.clear()
    busy = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert not busy['success'] and busy['status'] == 'mailbox_busy' and mailbox.calls == []
    with workflow.connect() as db:
        db.execute('UPDATE recdebut_email_inbox_progress SET lease_until=0')
    assert intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')['success']


def test_malformed_uid_response_does_not_advance_cursor(database):
    mailbox = UIDMailbox({1: synthetic_mail()})
    original = mailbox.uid
    mailbox.uid = lambda operation, *args: ('OK', [b'1 1']) if operation == 'search' else original(operation, *args)
    result = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert not result['success'] and result['last_uid'] == 0
    assert rows('recdebut_suppressions') == []


def test_privacy_exclusion_change_during_headers_prevents_body_fetch(database, monkeypatch):
    private = False
    monkeypatch.setattr(intake, 'load_personal_contacts', lambda: (set(), {'parent@example.org'} if private else set()))
    mailbox = UIDMailbox({1: synthetic_mail()})
    original = mailbox.uid
    def changing_mailbox(operation, *args):
        nonlocal private
        response = original(operation, *args)
        if operation == 'fetch' and 'HEADER.FIELDS' in args[-1]:
            private = True
        return response
    mailbox.uid = changing_mailbox
    result = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert result['success'] and result['email_opt_outs_processed'] == 0
    assert all('HEADER.FIELDS' in args[-1] for op, args in mailbox.calls if op == 'fetch')
    assert rows('recdebut_suppressions') == []


def test_oversized_body_without_intent_retains_uid_for_review(database):
    mailbox = UIDMailbox({1: synthetic_mail(body='Not an unsubscribe\n' + 'x' * 100000)})
    result = intake.sync_receive_only_mailbox(mailbox, 'synthetic-mailbox')
    assert not result['success'] and result['status'] == 'body_prefix_incomplete'
    assert result['last_uid'] == 0 and rows('recdebut_suppressions') == []


@pytest.mark.parametrize('receive_only', [True, False])
@pytest.mark.parametrize('config', [
    {}, {'IMAP_USER': 'synthetic'}, {'IMAP_APP_PASSWORD': 'synthetic'},
    {'IMAP_USER': '', 'IMAP_APP_PASSWORD': 'synthetic'},
    {'IMAP_USER': 'synthetic', 'IMAP_APP_PASSWORD': '   '},
    {'IMAP_USER': None, 'IMAP_APP_PASSWORD': 'synthetic'},
    {'IMAP_USER': 'synthetic', 'IMAP_APP_PASSWORD': False},
    None,
], ids=['absent', 'missing-password', 'missing-user', 'empty-user', 'blank-password', 'null-user', 'non-string-password', 'invalid-config'])
def test_actual_imap_requires_explicit_private_credentials_without_connecting(config, receive_only):
    calls = []
    class ForbiddenIMAP:
        def __init__(self, *args, **kwargs):
            calls.append('connect')
            raise AssertionError('No connection without explicit private IMAP credentials')
    handler = load_router_function('sync_imap_inbound_messages', {
        '_require_recdebut_outbound': lambda: None,
        'load_credentials': lambda: config,
        'imaplib': SimpleNamespace(IMAP4_SSL=ForbiddenIMAP),
    })
    result = handler(receive_only=receive_only)
    assert result == {'success': False, 'status': 'imap_unconfigured', 'provider': 'imap',
                      'receive_only': receive_only, 'new_replies_forwarded': 0,
                      'email_opt_outs_processed': 0, 'email_opt_outs_already_suppressed': 0,
                      'items': []}
    assert calls == []
