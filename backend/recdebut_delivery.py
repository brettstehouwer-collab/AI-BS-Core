"""Bounded, explicit RecDebut delivery. No background sender or roster enrollment.

Preparation and unsubscribe intake work while the independent review hold stays
closed. Provider acceptance never means delivery. Interrupted/ambiguous attempts
remain reserved for manual reconciliation instead of being automatically retried.
"""
import hashlib
import base64
import json
import os
import re
import secrets
import smtplib
import ssl
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from core.outbound_messaging_policy import outbound_messaging_enabled
from security.recdebut_privacy import load_personal_contacts, normalize_phone, PrivacyCheckUnavailable
import recdebut_campaign_links as campaign_links

router = APIRouter()
_sms_release = ContextVar('recdebut_exact_sms_release', default=None)


def workflow():
    # Imported lazily because the workflow router includes these routes.
    import recdebut_workflow
    return recdebut_workflow


def schema(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS recdebut_send_plans (
            id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL,
            state TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_send_attempts (
            dedup_key TEXT PRIMARY KEY, plan_id TEXT NOT NULL, person_id TEXT NOT NULL,
            state TEXT NOT NULL, receipt_id TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_unsubscribe_tokens (
            token_sha256 TEXT PRIMARY KEY, destination TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_send_provider_receipts (
            dedup_key TEXT PRIMARY KEY, plan_id TEXT NOT NULL, http_status INTEGER NOT NULL,
            response_body_base64 TEXT NOT NULL, response_sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_email_staff_copies (
            dedup_key TEXT PRIMARY KEY, plan_id TEXT NOT NULL, state TEXT NOT NULL,
            receipt_id TEXT NOT NULL, updated_at TEXT NOT NULL);
    ''')
    campaign_links.schema(db)


def email_address(value):
    # Lazy import preserves the workflow/router import order.
    from recdebut_email_unsubscribe import normalize_email
    return normalize_email(value)


def email_reply_recipients(profile):
    """Address athlete replies to the sender and staff copy recipient once each."""
    return list(dict.fromkeys(address for value in (profile.get('reply_to'), profile.get('copy_to'))
                              if (address := email_address(value))))


def sender_profile(channel):
    """Configuration comes only from the private host environment, never a request."""
    env = os.environ
    p = {'channel': channel, 'provider': 'smtp' if channel == 'email' else 'textbee', 'blockers': []}
    if channel == 'email':
        p.update(sender=email_address(env.get('RECDEBUT_EMAIL_FROM')),
                 reply_to=email_address(env.get('RECDEBUT_EMAIL_REPLY_TO')),
                 copy_to=email_address(env.get('RECDEBUT_EMAIL_COPY_TO')),
                 track_links=env.get('RECDEBUT_EMAIL_TRACK_LINKS', '').casefold() == 'true',
                 postal_address=env.get('RECDEBUT_MAILING_ADDRESS', '').strip(),
                 unsubscribe_base=env.get('RECDEBUT_UNSUBSCRIBE_BASE_URL', '').rstrip('/'),
                 smtp_host=env.get('RECDEBUT_SMTP_HOST', ''),
                 smtp_user=env.get('RECDEBUT_SMTP_USER', ''),
                 smtp_password=env.get('RECDEBUT_SMTP_PASSWORD', ''),
                 smtp_mode=env.get('RECDEBUT_SMTP_MODE', ''),
                 smtp_port=env.get('RECDEBUT_SMTP_PORT', ''))
        p['reply_recipients'] = email_reply_recipients(p)
        if not p['postal_address'] or p['postal_address'].casefold() == 'recreational debut' or any(c in p['postal_address'] for c in '[]{}\r\n'):
            p['blockers'].append('MAILING_ADDRESS_MISSING')
        if not env.get('RECDEBUT_MAILING_ADDRESS_VERIFIED_AT'):
            p['blockers'].append('MAILING_ADDRESS_UNVERIFIED')
        if not p['sender'] or not p['reply_to'] or not env.get('RECDEBUT_EMAIL_IDENTITY_VERIFIED_AT'):
            p['blockers'].append('EMAIL_IDENTITY_UNVERIFIED')
        if not p['copy_to']:
            p['blockers'].append('EMAIL_COPY_DESTINATION_UNCONFIGURED')
        if (not all(p[k] for k in ('smtp_host', 'smtp_user', 'smtp_password'))
                or p['smtp_mode'] not in ('ssl', 'starttls') or not p['smtp_port'].isdigit()
                or not 1 <= int(p['smtp_port'] or 0) <= 65535):
            p['blockers'].append('AUTHENTICATED_SMTP_NOT_CONFIGURED')
        try:
            base = urlsplit(p['unsubscribe_base'])
            valid_base = (base.scheme == 'https' and base.netloc in ('recdebut-recruit.org', 'api.brettstehouwer.live')
                          and not (base.path or base.query or base.fragment))
        except ValueError:
            valid_base = False
        if not valid_base:
            p['blockers'].append('PUBLIC_UNSUBSCRIBE_NOT_CONFIGURED')
    else:
        raw_sim = env.get('RECDEBUT_TEXTBEE_SIM_SUBSCRIPTION_ID', '')
        p.update(sender=normalize_phone(env.get('RECDEBUT_SMS_SENDER')),
                 device_id=env.get('TEXTBEE_DEVICE_ID', ''), api_key=env.get('TEXTBEE_API_KEY', ''),
                 sim_subscription_id=int(raw_sim) if raw_sim.isdigit() else None,
                 identity_verified_at=env.get('RECDEBUT_SMS_IDENTITY_VERIFIED_AT', ''))
        # Provider SIM metadata has no guaranteed phone-number mapping. Require
        # a private host attestation after an independently observed sender test.
        # It binds the exact tuple, expires after 24 hours, and grants no sending
        # authority by itself. Never manufacture this from device membership.
        binding = workflow().digest({k: p[k] for k in ('device_id', 'sim_subscription_id', 'sender')})
        try:
            verified = datetime.fromisoformat(p['identity_verified_at'])
            recent = (verified.utcoffset() == timedelta(0)
                      and timedelta(0) <= datetime.now(timezone.utc) - verified < timedelta(hours=24))
        except (ValueError, TypeError):
            recent = False
        if not all((p['sender'], p['device_id'], p['api_key'], raw_sim.isdigit(),
                    recent, env.get('RECDEBUT_SMS_IDENTITY_BINDING') == binding)):
            p['blockers'].append('SMS_DEVICE_SIM_SENDER_UNVERIFIED')
    # Bind credentials by digest without returning them to the portal or ledger.
    p['configuration_digest'] = workflow().digest(p)
    return p


def public_profile(p):
    return {k: p.get(k) for k in ('channel', 'provider', 'sender', 'reply_to', 'postal_address',
                                'copy_to', 'reply_recipients', 'track_links',
                                'unsubscribe_base', 'device_id', 'sim_subscription_id', 'identity_verified_at',
                                'configuration_digest', 'blockers')}


def normalized_name(value):
    return ' '.join(str(value or '').casefold().split())


def identity_rows(db):
    """Existing local records only. Missing legacy tables mean no legacy records."""
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, role, n, e, p in (
        ('rec_debut_athletes', 'athlete', 'name', 'email', 'phone'),
        ('rec_debut_registrations', 'unknown', 'parent_name', 'email', 'phone'),
        ('rec_debut_coaches', 'coach', 'coach_name', 'coach_email', 'coach_phone'),
        ('rec_debut_excluded_coaches', 'coach', 'name', None, 'phone')):
        if table not in names: continue
        for row in db.execute('SELECT * FROM ' + table):
            r = dict(row)
            yield {'name': r.get(n, ''), 'email': r.get(e, '') if e else '', 'phone': r.get(p, ''),
                   'role': role, 'email_status': r.get('email_status', ''),
                   'notes': str(r.get('notes', '')) + ' ' + str(r.get('status', ''))}
    for row in db.execute("SELECT payload FROM recdebut_workflow WHERE kind='person'"):
        yield json.loads(row[0])


def audience_checks(db, preview):
    phones, emails = load_personal_contacts()  # Unavailable exclusions fail closed.
    phones |= {'6164023628', '6166003837', '6164067993'}
    rows = list(identity_rows(db))
    prior_opt_outs = set()
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='rec_debut_athlete_replies'").fetchone():
        for row in db.execute('SELECT sender_email,sender_phone,subject,reply_body FROM rec_debut_athlete_replies'):
            r = dict(row)
            if re.search(r'\b(stop|stopall|unsubscribe|opt[ -]?out|do not contact|do not text|remove me|revoke)\b',
                         str(r.get('subject') or '') + ' ' + str(r.get('reply_body') or ''), re.I):
                prior_opt_outs.update(v for v in (normalize_phone(r.get('sender_phone')), email_address(r.get('sender_email'))) if v)
    checks = []
    for a in preview['audience']:
        person = db.execute('SELECT payload FROM recdebut_workflow WHERE id=?', (a['person_id'],)).fetchone()
        p = json.loads(person[0]) if person else {}
        phone, email, name = normalize_phone(p.get('phone')), email_address(p.get('email')), normalized_name(p.get('name'))
        reasons = list(a['reasons'])
        address = p.get('email' if preview['draft']['channel'] == 'email' else 'phone', '')
        canonical = email if preview['draft']['channel'] == 'email' else phone
        if not canonical or address != canonical: reasons.append('Destination normalization invalid')
        if (phone and phone in phones) or (email and email in emails): reasons.append('Personal / diagnostic identity excluded')
        if (phone and phone in prior_opt_outs) or (email and email in prior_opt_outs):
            reasons.append('Possible prior reply opt-out requires review')
        for r in rows:
            rp, re_, rn = normalize_phone(r.get('phone')), email_address(r.get('email')), normalized_name(r.get('name'))
            same_destination = bool((phone and phone == rp) or (email and email == re_))
            same_identity = same_destination or bool(name and name == rn)
            if r.get('role') == 'coach' and same_identity: reasons.append('Coach identity excluded')
            if same_identity and ((rp and rp in phones) or (re_ and re_ in emails)):
                reasons.append('Personal / diagnostic identity excluded')
            if not same_destination: continue
            if (rp and rp in prior_opt_outs) or (re_ and re_ in prior_opt_outs):
                reasons.append('Possible prior reply opt-out requires review')
            if preview['draft']['channel'] == 'email' and str(r.get('email_status', '')).upper() in ('BOUNCED', 'INVALID', 'UNDELIVERABLE', 'NO_EMAIL'):
                reasons.append('Undeliverable email requires review')
            if name and rn and name != rn: reasons.append('Shared destination has conflicting names')
            text = ' '.join(str(r.get(k, '')) for k in ('name', 'notes', 'source'))
            if re.search(r'\b(test|synthetic|fictional)\b', text, re.I): reasons.append('Test-only contact excluded')
            if re.search(r'\b(stop|stopall|unsubscribe|opt[ -]?out|do not contact|do not text|remove me|revoke)\b', str(r.get('notes', '')), re.I):
                reasons.append('Possible prior opt-out requires review')
            if r.get(preview['draft']['channel'] + '_permission') == 'denied': reasons.append('Permission denied in matching record')
        checks.append({'person_id': a['person_id'], 'reasons': sorted(set(reasons))})
    return checks


def current_snapshot(db, draft_id):
    row = db.execute("SELECT * FROM recdebut_workflow WHERE id=? AND kind='draft'", (draft_id,)).fetchone()
    if not row: raise HTTPException(404, 'Draft not found.')
    p = workflow().draft_preview(db, row)
    try:
        checks = audience_checks(db, p)
    except (PrivacyCheckUnavailable, OSError, ValueError, json.JSONDecodeError):
        raise HTTPException(503, 'Recipient privacy checks unavailable; delivery is blocked.')
    profile = sender_profile(p['draft'].get('channel'))
    return p, checks, profile


class Prepare(BaseModel):
    draft_id: str = Field(min_length=1, max_length=160)
    expected_preview_digest: str = Field(pattern='^[a-f0-9]{64}$')
    actor: str = Field(min_length=1, max_length=100)


class ExactAction(BaseModel):
    expected_digest: str = Field(pattern='^[a-f0-9]{64}$')
    actor: str = Field(min_length=1, max_length=100)


@router.get('/sending/readiness')
def readiness(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with workflow().connect() as db:
        drafts = []
        for row in db.execute("SELECT id FROM recdebut_workflow WHERE kind='draft'").fetchall():
            p, checks, profile = current_snapshot(db, row['id'])
            drafts.append({'draft_id': row['id'], 'revision': p['revision'], 'preview_digest': p['digest'],
                           'recipients': len(checks), 'eligible': sum(not c['reasons'] for c in checks),
                           'audience_blockers': sorted({r for c in checks for r in c['reasons']})})
    return {'sending_enabled': outbound_messaging_enabled('recdebut'), 'drafts': drafts,
            'channels': {channel: public_profile(sender_profile(channel)) for channel in ('sms', 'email')}}


@router.post('/sending/plans')
def prepare(data: Prepare, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    w = workflow()
    with w.connect() as db:
        schema(db); db.execute('BEGIN IMMEDIATE')
        p, checks, profile = current_snapshot(db, data.draft_id)
        if p['digest'] != data.expected_preview_digest: raise HTTPException(409, 'Preview changed. Review it again.')
        if profile['blockers'] or not p['reviewable'] or any(c['reasons'] for c in checks):
            raise HTTPException(422, {'code': 'PREREQUISITES_UNRESOLVED', 'sender': profile['blockers'], 'audience': checks})
        if not db.execute("SELECT 1 FROM recdebut_workflow_events WHERE record_id=? AND action='review_recorded_not_send_authorization' AND digest=?",
                          (data.draft_id, w.digest(p))).fetchone():
            raise HTTPException(409, 'Record an exact current draft review before preparing delivery.')
        plan_id = secrets.token_hex(16)
        recipients = []
        for a in p['audience']:
            item = {k: a[k] for k in ('person_id', 'person_revision', 'destination', 'message')}
            if profile['channel'] == 'email':
                token = secrets.token_urlsafe(32)
                url = profile['unsubscribe_base'] + '/api/v1/recdebut/workflow/unsubscribe/' + token
                db.execute('INSERT INTO recdebut_unsubscribe_tokens VALUES(?,?,?)',
                           (hashlib.sha256(token.encode()).hexdigest(), item['destination'], w.now()))
                # Replace the known staging placeholder only after a verified address exists.
                item['message'] = item['message'].replace('[Confirmed mailing address]', profile['postal_address'])
                item['staff_copy_message'] = item['message']
                item['message'] += '\n\nPromotional information from Recreational Debut\n' + profile['postal_address'] + '\nUnsubscribe: ' + url
                item['unsubscribe_url'] = url
                if profile.get('track_links'):
                    campaign_links.render(db, plan_id, profile, item)
            recipients.append(item)
        payload = {'id': plan_id, 'draft_id': data.draft_id, 'preview_digest': p['digest'],
                   'channel': profile['channel'], 'subject': p['draft']['title'], 'sender': public_profile(profile),
                   'recipients': recipients, 'audience_checks': checks}
        if p.get('review_exception'): payload['review_exception'] = p['review_exception']
        plan_digest = w.digest(payload)
        db.execute('INSERT INTO recdebut_send_plans VALUES(?,?,?,?,?)', (plan_id, w.encode(payload), plan_digest, 'PREPARED', w.now()))
        w.event(db, plan_id, 1, 'send_plan_prepared_not_dispatched', data.actor, {'digest': plan_digest, 'count': len(recipients)})
    return {'sending_enabled': outbound_messaging_enabled('recdebut'), 'plan': {**payload, 'digest': plan_digest}}


def load_plan(db, plan_id, expected=None):
    row = db.execute('SELECT * FROM recdebut_send_plans WHERE id=?', (plan_id,)).fetchone()
    if not row: raise HTTPException(404, 'Delivery plan not found.')
    p = json.loads(row['payload'])
    if workflow().digest(p) != row['digest'] or (expected and expected != row['digest']):
        raise HTTPException(409, 'Delivery plan digest changed.')
    return row, p


def recheck(db, p):
    preview, checks, profile = current_snapshot(db, p['draft_id'])
    if (preview['digest'] != p['preview_digest'] or checks != p['audience_checks']
            or any(c['reasons'] for c in checks) or profile['blockers']
            or public_profile(profile) != p['sender']):
        raise HTTPException(409, 'Draft, recipients, exclusions or sender changed. Prepare a new reviewed plan.')
    return profile


def dispatch_enabled(plan_id, expected_digest):
    """A host-only grant cannot enable a different plan or any legacy sender."""
    return (outbound_messaging_enabled('recdebut')
            or _sms_release.get() == (plan_id, expected_digest))


@contextmanager
def bounded_sms_release(plan_id, expected_digest):
    """Single reviewed SMS plan; authority exists only in this caller's context."""
    if _sms_release.get() is not None:
        raise HTTPException(409, 'A bounded release is already active in this context.')
    with workflow().connect() as db:
        schema(db)
        row, p = load_plan(db, plan_id, expected_digest)
        if (row['state'] != 'PREPARED' or p['channel'] != 'sms'
                or not 1 <= len(p['recipients']) <= 25 or not p.get('review_exception')):
            raise HTTPException(409, 'Only a new bounded SMS exception plan can be released.')
        recheck(db, p)
    token = _sms_release.set((plan_id, expected_digest))
    try:
        yield
    finally:
        _sms_release.reset(token)
        # Keep an unstarted plan inspectable after a local caller failure. Any
        # started plan is spent, including interrupted or uncertain attempts.
        with workflow().connect() as db:
            row, p = load_plan(db, plan_id, expected_digest)
            if row['state'] != 'PREPARED':
                db.execute("UPDATE recdebut_sms_review_exceptions SET state='COMPLETED' WHERE id=? AND digest=?",
                           (p['review_exception']['id'], p['review_exception']['digest']))


def plan_status(db, row, p):
    attempts = [dict(r) for r in db.execute('SELECT person_id,state,receipt_id,updated_at FROM recdebut_send_attempts WHERE plan_id=?', (p['id'],))]
    copies = [dict(r) for r in db.execute('''SELECT a.person_id,c.state,c.receipt_id,c.updated_at
        FROM recdebut_email_staff_copies c JOIN recdebut_send_attempts a USING(dedup_key)
        WHERE c.plan_id=?''', (p['id'],))]
    return {'id': p['id'], 'digest': row['digest'], 'state': row['state'], 'recipients': attempts,
            'staff_copies': copies,
            'sending_enabled': outbound_messaging_enabled('recdebut')}


@router.get('/sending/plans/{plan_id}')
def status(plan_id: str, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with workflow().connect() as db:
        schema(db); row, p = load_plan(db, plan_id)
        return plan_status(db, row, p)


@router.post('/sending/plans/{plan_id}/cancel')
def cancel(plan_id: str, data: ExactAction):
    with workflow().connect() as db:
        schema(db); db.execute('BEGIN IMMEDIATE'); row, p = load_plan(db, plan_id, data.expected_digest)
        if row['state'] not in ('PREPARED', 'RUNNING'): raise HTTPException(409, 'Plan has already finished.')
        db.execute("UPDATE recdebut_send_plans SET state='CANCELLED' WHERE id=?", (plan_id,))
        workflow().event(db, plan_id, 1, 'send_plan_cancelled', data.actor, {'digest': row['digest']})
    return {'state': 'CANCELLED', 'sending_enabled': outbound_messaging_enabled('recdebut')}


class DeliveryBlocked(RuntimeError):
    pass


def record_provider_response(item, response):
    """Durably retain the HTTP response before interpreting provider acceptance."""
    if not item.get('dedup_key') or not item.get('plan_id'):
        return
    raw = response.content
    if len(raw) > 65536:
        raise RuntimeError('Provider response exceeds the receipt limit.')
    w = workflow()
    with w.connect() as db:
        active = db.execute("SELECT 1 FROM recdebut_send_attempts WHERE dedup_key=? AND plan_id=? AND state='ATTEMPTING'",
                            (item['dedup_key'], item['plan_id'])).fetchone()
        if not active: raise RuntimeError('Provider response has no reserved attempt.')
        db.execute('INSERT INTO recdebut_send_provider_receipts VALUES(?,?,?,?,?,?)',
                   (item['dedup_key'], item['plan_id'], response.status_code,
                    base64.b64encode(raw).decode('ascii'), hashlib.sha256(raw).hexdigest(), w.now()))


def send_one(profile, item, before_submit):
    """Single provider attempt; caller has durably reserved it. No fallback/retry."""
    if not callable(before_submit): raise TypeError('Final submission check is required.')
    if profile['provider'] == 'textbee':
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            headers = {'x-api-key': profile['api_key']}
            device = client.get('https://api.textbee.dev/api/v1/gateway/devices/' + profile['device_id'], headers=headers)
            device.raise_for_status(); device = device.json().get('data', {})
            sim = profile['sim_subscription_id']
            if (device.get('_id') != profile['device_id'] or device.get('enabled') is not True
                    or not isinstance(sim, int) or isinstance(sim, bool)
                    or sim not in [s.get('subscriptionId') for s in device.get('simInfo', {}).get('sims', [])]):
                raise DeliveryBlocked('Current device/SIM identity unavailable.')
            dest = normalize_phone(item['destination'])
            if not dest: raise DeliveryBlocked('Invalid recipient.')
            before_submit()
            result = client.post('https://api.textbee.dev/api/v1/gateway/send-sms', headers=headers,
                                 json={'deviceId': profile['device_id'], 'simSubscriptionId': sim,
                                       'recipients': [dest if dest.startswith('+') else '+1' + dest], 'message': item['message']})
            record_provider_response(item, result)
            result.raise_for_status(); data = result.json().get('data', {})
            if data.get('success') is not True or not isinstance(data.get('smsBatchId'), str) or not data['smsBatchId']:
                raise RuntimeError('Unconfirmed provider acceptance.')
            return {'state': 'ACCEPTED', 'receipt_id': data['smsBatchId'][:200]}
    if profile['provider'] != 'smtp': raise DeliveryBlocked('Unsupported provider.')
    message = EmailMessage()
    message['From'] = 'Recreational Debut <' + profile['sender'] + '>'
    message['To'] = item['destination']; message['Reply-To'] = ', '.join(email_reply_recipients(profile))
    message['Subject'] = item['subject']; message['Message-ID'] = make_msgid(domain=profile['sender'].split('@')[1])
    message['List-Unsubscribe'] = '<' + item['unsubscribe_url'] + '>'
    message.set_content(item['message'])
    if item.get('html_message'):
        message.add_alternative(item['html_message'], subtype='html')
    return submit_smtp(profile, message, item['destination'], before_submit)


def submit_smtp(profile, message, destination, before_submit):
    ctx = ssl.create_default_context()
    factory = smtplib.SMTP_SSL if profile['smtp_mode'] == 'ssl' else smtplib.SMTP
    args = {'timeout': 20}
    if profile['smtp_mode'] == 'ssl': args['context'] = ctx
    with factory(profile['smtp_host'], int(profile['smtp_port']), **args) as smtp:
        if profile['smtp_mode'] == 'starttls': smtp.ehlo(); smtp.starttls(context=ctx); smtp.ehlo()
        smtp.login(profile['smtp_user'], profile['smtp_password'])
        before_submit()
        refused = smtp.send_message(message, from_addr=profile['sender'], to_addrs=[destination])
        if refused: raise RuntimeError('Recipient not accepted.')
    return {'state': 'ACCEPTED', 'receipt_id': message['Message-ID']}


def send_staff_copy(profile, item, subject, before_submit):
    """A separate, untracked staff record with no athlete unsubscribe capability."""
    message = EmailMessage()
    message['From'] = 'Recreational Debut <' + profile['sender'] + '>'
    message['To'] = profile['copy_to']; message['Reply-To'] = profile['reply_to']
    message['Subject'] = 'RecDebut sent copy: ' + subject
    message['Message-ID'] = make_msgid(domain=profile['sender'].split('@')[1])
    message.set_content('Staff copy of outreach to: ' + item['destination']
                        + '\nSMTP accepted the athlete message; delivery is unconfirmed.\n'
                        + 'Athlete tracking and unsubscribe links are omitted from this staff copy.\n\n'
                        + item['staff_copy_message'])
    return submit_smtp(profile, message, profile['copy_to'], before_submit)


def dispatch_staff_copy(plan, item, key, expected_digest):
    """Reserve separately after durable athlete acceptance. Never retry copies."""
    w = workflow()
    with w.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        accepted = db.execute("SELECT 1 FROM recdebut_send_attempts WHERE dedup_key=? AND plan_id=? AND state='ACCEPTED'",
                              (key, plan['id'])).fetchone()
        if not accepted: return
        inserted = db.execute('INSERT INTO recdebut_email_staff_copies VALUES(?,?,?,?,?) ON CONFLICT(dedup_key) DO NOTHING',
                              (key, plan['id'], 'ATTEMPTING', '', w.now()))
        if not inserted.rowcount: return
    state, receipt = 'UNCERTAIN', ''
    try:
        def before_submit():
            with w.connect() as db:
                row, _ = load_plan(db, plan['id'], expected_digest)
                profile = sender_profile('email')
                if (row['state'] != 'RUNNING' or not dispatch_enabled(plan['id'], expected_digest)
                        or profile['blockers'] or public_profile(profile) != plan['sender']):
                    raise DeliveryBlocked('Staff copy held or sender changed.')
                return profile
        profile = before_submit()
        result = send_staff_copy(profile, item, plan['subject'], before_submit)
        state = 'ACCEPTED' if result.get('state') == 'ACCEPTED' else 'UNCERTAIN'
        receipt = str(result.get('receipt_id', ''))[:200]
    except DeliveryBlocked:
        state = 'BLOCKED'
    except Exception:
        pass
    with w.connect() as db:
        db.execute('UPDATE recdebut_email_staff_copies SET state=?,receipt_id=?,updated_at=? WHERE dedup_key=?',
                   (state, receipt, w.now(), key))


@router.post('/sending/plans/{plan_id}/dispatch')
def dispatch(plan_id: str, data: ExactAction):
    if not dispatch_enabled(plan_id, data.expected_digest):
        raise HTTPException(423, {'code': 'SENDING_DISABLED', 'reason': 'Independent review hold is closed.'})
    w = workflow()
    with w.connect() as db:
        schema(db); db.execute('BEGIN IMMEDIATE'); row, p = load_plan(db, plan_id, data.expected_digest)
        if row['state'] != 'PREPARED': raise HTTPException(409, 'Plan already started, cancelled or finished; no replay.')
        recheck(db, p)
        reservations = []
        for item in p['recipients']:
            # Revisions, newly generated unsubscribe tokens, and a second plan
            # cannot bypass a recipient reservation for this campaign draft.
            key = w.digest({'draft_id': p['draft_id'], 'channel': p['channel'], 'destination': item['destination']})
            if db.execute('SELECT 1 FROM recdebut_send_attempts WHERE dedup_key=?', (key,)).fetchone():
                raise HTTPException(409, 'Recipient attempt already reserved; reconcile it instead of retrying.')
            reservations.append((key, item))
        for key, item in reservations:
            db.execute('INSERT INTO recdebut_send_attempts VALUES(?,?,?,?,?,?)', (key, plan_id, item['person_id'], 'RESERVED', '', w.now()))
        db.execute("UPDATE recdebut_send_plans SET state='RUNNING' WHERE id=?", (plan_id,))
        w.event(db, plan_id, 1, 'explicit_dispatch_reserved', data.actor, {'digest': row['digest']})
    # Persisted claim precedes ALL network I/O, including device inspection.
    for key, item in reservations:
        with w.connect() as db:
            db.execute('BEGIN IMMEDIATE'); row, fresh = load_plan(db, plan_id, data.expected_digest)
            if row['state'] != 'RUNNING': break
            if not dispatch_enabled(plan_id, data.expected_digest): outcome = 'BLOCKED'
            else:
                try: profile = recheck(db, p); outcome = 'ATTEMPTING'
                except HTTPException: outcome = 'BLOCKED'
            db.execute('UPDATE recdebut_send_attempts SET state=?,updated_at=? WHERE dedup_key=?', (outcome, w.now(), key))
        receipt = ''
        if outcome == 'ATTEMPTING':
            try:
                def before_submit():
                    with w.connect() as gate_db:
                        gate_row, _ = load_plan(gate_db, plan_id, data.expected_digest)
                        if gate_row['state'] != 'RUNNING' or not dispatch_enabled(plan_id, data.expected_digest):
                            raise DeliveryBlocked('Delivery cancelled or held before submission.')
                        try: recheck(gate_db, p)
                        except HTTPException: raise DeliveryBlocked('Recipient or sender changed before submission.')
                result = send_one(profile, {**item, 'subject': p['subject'], 'plan_id': plan_id, 'dedup_key': key}, before_submit)
                outcome = result['state'] if result['state'] == 'ACCEPTED' else 'UNCERTAIN'
                receipt = str(result.get('receipt_id', ''))[:200]
            except DeliveryBlocked: outcome = 'BLOCKED'
            except Exception: outcome = 'UNCERTAIN'  # Never expose message/credential/provider exceptions.
        with w.connect() as db:
            db.execute('UPDATE recdebut_send_attempts SET state=?,receipt_id=?,updated_at=? WHERE dedup_key=?', (outcome, receipt, w.now(), key))
            if p.get('review_exception') and outcome != 'ACCEPTED':
                db.execute("UPDATE recdebut_send_plans SET state='HALTED' WHERE id=? AND state='RUNNING'", (plan_id,))
                break
        if outcome == 'ACCEPTED' and p['channel'] == 'email' and p['sender'].get('copy_to'):
            dispatch_staff_copy(p, item, key, data.expected_digest)
    with w.connect() as db:
        db.execute("UPDATE recdebut_send_plans SET state='COMPLETED' WHERE id=? AND state='RUNNING'", (plan_id,))
        row, p = load_plan(db, plan_id)
        return plan_status(db, row, p)


router.include_router(campaign_links.router)


@router.api_route('/unsubscribe/{token}', methods=['GET', 'POST'], response_class=HTMLResponse)
async def unsubscribe(token: str, request: Request):
    headers = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
               'Content-Security-Policy': "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token): raise HTTPException(404, 'Link not found.')
    if request.method == 'POST':
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 2048: raise HTTPException(413, 'Request too large.')
    with workflow().connect() as db:
        schema(db)
        if request.method == 'POST': db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT destination FROM recdebut_unsubscribe_tokens WHERE token_sha256=?', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row: raise HTTPException(404, 'Link not found.')
        if request.method == 'POST':
            cursor = db.execute('INSERT INTO recdebut_suppressions VALUES(?,?,?,?) ON CONFLICT(destination) DO NOTHING',
                                (row['destination'], 'Email unsubscribe link', 'recipient-link', workflow().now()))
            if cursor.rowcount:
                workflow().event(db, row['destination'], 1, 'email_unsubscribed', 'recipient-link', {'channel': 'email'})
            body = '<h1>Unsubscribed</h1><p>This email address is excluded from Recreational Debut outreach.</p>'
        else:
            body = '<h1>Recreational Debut email preferences</h1><form method="post"><button type="submit">Unsubscribe from email</button></form>'
    return HTMLResponse('<!doctype html><html lang="en"><meta charset="utf-8"><title>Recreational Debut</title><body>' + body + '</body></html>', headers=headers)
