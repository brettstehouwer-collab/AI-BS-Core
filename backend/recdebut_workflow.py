"""Private recruiting casework. Saving/reviewing records never dispatches messages.

Additive tables preserve the legacy roster and provider evidence. Recorded staff
names are attribution supplied by an authenticated administrator, not proof of
another person's approval. No provider/network calls belong in this module.
"""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from security.recdebut_access import require_recdebut_access
from security.recdebut_privacy import normalize_phone

DB_PATH = Path(__file__).resolve().parents[1] / 'saved_data' / 'rec_debut.db'
router = APIRouter(prefix='/workflow', dependencies=[Depends(require_recdebut_access)])
KINDS = ('family', 'person', 'followup', 'draft', 'service', 'delivery', 'worklog')
FIELDS = {
    'family': {'name', 'athlete_name', 'grad_year', 'sport', 'school', 'source', 'notes'},
    'person': {'name', 'family_id', 'role', 'phone', 'email', 'source', 'relationship', 'sms_permission', 'email_permission', 'permission_evidence', 'notes'},
    'followup': {'family_id', 'title', 'owner', 'due', 'status', 'kind', 'notes'},
    'draft': {'title', 'body', 'channel', 'person_ids', 'notes'},
    'service': {'family_id', 'title', 'stage', 'package', 'price_cents', 'payment', 'deliverables', 'notes'},
    'delivery': {'family_id', 'title', 'owner', 'due', 'status', 'reference', 'notes'},
    'worklog': {'family_id', 'title', 'owner', 'minutes', 'expense_cents', 'notes'},
}


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    db = sqlite3.connect(str(DB_PATH), timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS recdebut_workflow (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, revision INTEGER NOT NULL,
            payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_workflow_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL,
            revision INTEGER NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL,
            digest TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_suppressions (
            destination TEXT PRIMARY KEY, reason TEXT NOT NULL, actor TEXT NOT NULL,
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_textbee_receipts (
            idempotency_key TEXT PRIMARY KEY, device_id TEXT NOT NULL, sms_id TEXT NOT NULL,
            subscription_id TEXT NOT NULL, digest TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
            outcome TEXT NOT NULL, received_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS recdebut_textbee_sms_lookup ON recdebut_textbee_receipts(device_id,sms_id);
        CREATE TABLE IF NOT EXISTS recdebut_registration_receipts (
            event_id TEXT PRIMARY KEY, digest TEXT NOT NULL, family_id TEXT NOT NULL, received_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_registration_reviews (
            event_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, status TEXT NOT NULL,
            target_family_id TEXT NOT NULL, notes TEXT NOT NULL, actor TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_family_history (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, family_id TEXT NOT NULL,
            record_id TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL,
            details TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS recdebut_family_history_lookup ON recdebut_family_history(family_id,sequence);
        CREATE TABLE IF NOT EXISTS recdebut_sms_review_exceptions (
            id TEXT PRIMARY KEY, draft_id TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
            digest TEXT NOT NULL, state TEXT NOT NULL);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


def encode(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(data):
    return hashlib.sha256(encode(data).encode()).hexdigest()


def unpack(row):
    return {**dict(row), 'payload': json.loads(row['payload'])}


class SaveRecord(BaseModel):
    revision: int = Field(ge=0)
    actor: str = Field(min_length=1, max_length=100)
    payload: dict


class ReviewRecord(BaseModel):
    revision: int = Field(ge=1)
    actor: str = Field(min_length=1, max_length=100)
    expected_digest: str = Field(pattern=r'^[a-f0-9]{64}$')


class Suppression(BaseModel):
    destination: str = Field(min_length=3, max_length=254)
    reason: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=100)


def destination(value):
    value = value.strip()
    if '@' in value:
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise HTTPException(422, 'Enter a valid email destination.')
        return value.casefold()
    phone = normalize_phone(value)
    if not phone:
        raise HTTPException(422, 'Enter a valid phone destination.')
    return phone


def validate_payload(db, kind, payload):
    if kind not in KINDS or set(payload) - FIELDS[kind]:
        raise HTTPException(422, 'Unknown record type or field.')
    if len(encode(payload).encode()) > 24000:
        raise HTTPException(422, 'Record exceeds 24 KB.')
    for key, value in payload.items():
        if key == 'person_ids':
            if not isinstance(value, list) or len(value) > 100 or any(not isinstance(v, str) for v in value) or len(set(value)) != len(value):
                raise HTTPException(422, 'Audience requires at most 100 unique contact IDs.')
        elif key in ('price_cents', 'expense_cents', 'minutes'):
            if type(value) is not int or not 0 <= value <= 100000000:
                raise HTTPException(422, 'Amounts and minutes must be nonnegative whole numbers.')
        elif not isinstance(value, str) or len(value) > (12000 if key in ('body', 'notes', 'deliverables') else 1000):
            raise HTTPException(422, 'Invalid field length or type.')
    title = payload.get('name' if kind in ('family', 'person') else 'title', '').strip()
    if not title:
        raise HTTPException(422, 'A name or title is required.')
    family_id = payload.get('family_id')
    if family_id and not db.execute("SELECT 1 FROM recdebut_workflow WHERE id=? AND kind='family'", (family_id,)).fetchone():
        raise HTTPException(422, 'Select an existing family.')
    if kind == 'person':
        enums = {'role': ('unknown', 'parent', 'guardian', 'athlete', 'coach', 'organization'),
                 'relationship': ('unknown', 'verified'), 'sms_permission': ('unknown', 'granted', 'denied'),
                 'email_permission': ('unknown', 'granted', 'denied')}
        for key, choices in enums.items():
            if payload.get(key, 'unknown') not in choices:
                raise HTTPException(422, 'Invalid contact classification.')
        for key in ('phone', 'email'):
            if payload.get(key):
                payload[key] = destination(payload[key])
                if (key == 'email') != ('@' in payload[key]):
                    raise HTTPException(422, 'Phone and email must be in the correct fields.')
        if any(payload.get(key) == 'granted' for key in ('sms_permission', 'email_permission')) and not payload.get('permission_evidence', '').strip():
            raise HTTPException(422, 'Record the source/date of channel permission first.')
    if kind == 'draft' and payload.get('channel') not in ('sms', 'email'):
        raise HTTPException(422, 'Choose SMS or email.')
    if payload.get('due'):
        try:
            datetime.strptime(payload['due'], '%Y-%m-%d')
        except ValueError:
            raise HTTPException(422, 'Due dates must be YYYY-MM-DD.')
    return payload


def event(db, row_id, revision, action, actor, data):
    if not actor.strip():
        raise HTTPException(422, 'Recorded by is required.')
    db.execute('INSERT INTO recdebut_workflow_events(record_id,revision,action,actor,digest,created_at) VALUES(?,?,?,?,?,?)',
               (row_id, revision, action, actor.strip(), digest(data), now()))
    row = db.execute('SELECT kind FROM recdebut_workflow WHERE id=?', (row_id,)).fetchone()
    family_id = row_id if row and row['kind'] == 'family' else data.get('family_id')
    if family_id:
        history(db, family_id, row_id, action, actor, {'revision': revision, 'record': data})
    if row and row['kind'] == 'draft':
        linked = set()
        for person_id in data.get('person_ids', data.get('draft', {}).get('person_ids', [])):
            person = db.execute("SELECT payload FROM recdebut_workflow WHERE id=? AND kind='person'", (person_id,)).fetchone()
            if person:
                linked.add(json.loads(person['payload']).get('family_id'))
        for linked_id in linked - {None, ''}:
            history(db, linked_id, row_id, action, actor, {'revision': revision, 'record': data})


def history(db, family_id, record_id, action, actor, details):
    if not actor.strip():
        raise HTTPException(422, 'Recorded by is required.')
    db.execute('INSERT INTO recdebut_family_history(family_id,record_id,action,actor,details,created_at) VALUES(?,?,?,?,?,?)',
               (family_id, record_id, action, actor.strip(), encode(details), now()))


class RegistrationReview(BaseModel):
    revision: int = Field(ge=0)
    status: Literal['pending', 'accepted', 'needs_information', 'duplicate']
    target_family_id: str = Field(default='', max_length=80)
    notes: str = Field(default='', max_length=4000)
    actor: str = Field(min_length=1, max_length=100)


class TimelineNote(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    actor: str = Field(min_length=1, max_length=100)


@router.get('/registrations')
def registrations(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with connect() as db:
        rows = [dict(r) for r in db.execute('''SELECT p.*, COALESCE(r.revision,0) AS revision,
            COALESCE(r.status,'pending') AS status, COALESCE(r.target_family_id,'') AS target_family_id,
            COALESCE(r.notes,'') AS notes, COALESCE(r.actor,'') AS actor
            FROM recdebut_registration_receipts p LEFT JOIN recdebut_registration_reviews r USING(event_id)
            ORDER BY p.received_at DESC,p.event_id DESC''')]
    return {'registrations': rows, 'sending_enabled': False}


@router.put('/registrations/{event_id}/review')
def review_registration(event_id: str, data: RegistrationReview, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        receipt = db.execute('SELECT * FROM recdebut_registration_receipts WHERE event_id=?', (event_id,)).fetchone()
        if not receipt:
            raise HTTPException(404, 'Registration receipt not found.')
        prior = db.execute('SELECT * FROM recdebut_registration_reviews WHERE event_id=?', (event_id,)).fetchone()
        if data.revision != (prior['revision'] if prior else 0):
            raise HTTPException(409, 'Review changed in another session. Reload the inbox before saving; your edits were not applied.')
        target = data.target_family_id
        if data.status == 'duplicate':
            if target == receipt['family_id'] or not db.execute("SELECT 1 FROM recdebut_workflow WHERE id=? AND kind='family'", (target,)).fetchone():
                raise HTTPException(422, 'Select a different existing family for the duplicate link.')
            if db.execute("SELECT 1 FROM recdebut_registration_reviews r JOIN recdebut_registration_receipts p USING(event_id) WHERE r.status='duplicate' AND (p.family_id=? OR r.target_family_id=?)", (target, receipt['family_id'])).fetchone():
                raise HTTPException(409, 'Duplicate chains are not supported. Link directly to an independent family.')
        elif target:
            raise HTTPException(422, 'A duplicate target is only valid for a duplicate review.')
        revision = data.revision + 1
        stamp = now()
        details = {'status': data.status, 'notes': data.notes, 'target_family_id': target, 'revision': revision}
        history(db, receipt['family_id'], event_id, 'registration_review', data.actor, details)
        if target:
            history(db, target, event_id, 'duplicate_registration_linked', data.actor, {**details, 'original_family_id': receipt['family_id']})
        db.execute('INSERT INTO recdebut_registration_reviews VALUES(?,?,?,?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET revision=excluded.revision,status=excluded.status,target_family_id=excluded.target_family_id,notes=excluded.notes,actor=excluded.actor,updated_at=excluded.updated_at',
                   (event_id, revision, data.status, target, data.notes, data.actor.strip(), stamp))
    return {'success': True, 'revision': revision, 'sending_enabled': False}


@router.get('/families/{family_id}/timeline')
def family_timeline(family_id: str, response: Response, before: int = 0, limit: int = 50):
    response.headers['Cache-Control'] = 'no-store'
    if before < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid timeline page.')
    with connect() as db:
        if not db.execute("SELECT 1 FROM recdebut_workflow WHERE id=? AND kind='family'", (family_id,)).fetchone():
            raise HTTPException(404, 'Family not found.')
        rows = db.execute('SELECT * FROM recdebut_family_history WHERE family_id=? AND (?=0 OR sequence<?) ORDER BY sequence DESC LIMIT ?', (family_id, before, before, limit + 1)).fetchall()
        entries = [{**dict(r), 'details': json.loads(r['details'])} for r in rows[:limit]]
    return {'entries': entries, 'next_before': entries[-1]['sequence'] if len(rows) > limit else None,
            'history_notice': 'Detailed history starts with this feature. Earlier records remain in the workspace.', 'sending_enabled': False}


@router.post('/families/{family_id}/timeline')
def add_family_note(family_id: str, data: TimelineNote):
    if not data.text.strip():
        raise HTTPException(422, 'Enter an internal note.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute("SELECT 1 FROM recdebut_workflow WHERE id=? AND kind='family'", (family_id,)).fetchone():
            raise HTTPException(404, 'Family not found.')
        history(db, family_id, family_id, 'internal_note', data.actor, {'text': data.text.strip()})
    return {'success': True, 'sending_enabled': False}


@router.get('')
def snapshot(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with connect() as db:
        records = [unpack(r) for r in db.execute('SELECT * FROM recdebut_workflow ORDER BY updated_at DESC,id')]
        events = [dict(r) for r in db.execute('SELECT * FROM recdebut_workflow_events ORDER BY sequence DESC LIMIT 200')]
        suppressions = [dict(r) for r in db.execute('SELECT * FROM recdebut_suppressions ORDER BY created_at DESC')]
    return {'success': True, 'tenant': 'recdebut', 'records': records, 'events': events, 'suppressions': suppressions,
            'sending_enabled': False, 'hold_reason': 'Campaign preparation does not send messages. See sending/readiness and email/live for current connector status.',
            'offers_confirmed': False}


@router.put('/records/{kind}/{record_id}')
def save_record(kind: str, record_id: str, data: SaveRecord, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', record_id):
        raise HTTPException(422, 'Invalid record ID.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        prior = db.execute('SELECT * FROM recdebut_workflow WHERE id=?', (record_id,)).fetchone()
        if (prior and (prior['revision'] != data.revision or prior['kind'] != kind)) or (not prior and data.revision != 0):
            raise HTTPException(409, 'This record changed in another session. Reload before saving; your edits have not been applied.')
        payload = validate_payload(db, kind, dict(data.payload))
        old_family = json.loads(prior['payload']).get('family_id') if prior else None
        if old_family and old_family != payload.get('family_id'):
            history(db, old_family, record_id, 'record_relinked', data.actor, {'previous_record': json.loads(prior['payload']), 'new_family_id': payload.get('family_id', '')})
        # A refusal follows the destination, including other contacts sharing it.
        if kind == 'person':
            for channel, field in (('sms', 'phone'), ('email', 'email')):
                if payload.get(channel + '_permission') == 'denied' and payload.get(field):
                    db.execute('INSERT INTO recdebut_suppressions VALUES(?,?,?,?) ON CONFLICT(destination) DO NOTHING',
                               (payload[field], 'Contact permission denied', data.actor, now()))
        revision = data.revision + 1
        stamp = now()
        db.execute('INSERT INTO recdebut_workflow VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at',
                   (record_id, kind, revision, encode(payload), stamp))
        event(db, record_id, revision, 'saved', data.actor, payload)
    return {'success': True, 'record': {'id': record_id, 'kind': kind, 'revision': revision, 'payload': payload, 'updated_at': stamp}}


def personalize_message(template, name):
    """Render literal name tokens from this recipient only; never evaluate templates."""
    parts = name.split()
    first = parts[0] if parts else ''
    if (first.casefold().strip('.') in ('unknown', 'n/a', 'na', 'none', 'null', 'missing', 'parent', 'guardian', 'athlete')
            or not first or not first[0].isalpha()
            or any(not (c.isalpha() or c in "-'’") for c in first)):
        first = ''
    token = r'(?:\{first_name\}|\[(?:parent\s+)?first\s+name\])'
    body = template
    if not first:
        # Replace the entire salutation, avoiding "Hi Hello" for unnamed contacts.
        body = re.sub(r'\b(?:hi|hello|dear)\s+' + token + r'\s*[,!:.]?',
                      'Hello,', body, flags=re.IGNORECASE)
    body = re.sub(token, lambda _: first or 'Hello', body, flags=re.IGNORECASE)
    return {'message': body, 'first_name': first or None, 'greeting_fallback': not bool(first)}


def sms_review_exception(db, row):
    """Host-recorded release scope, bound to at most 25 unchanged SMS contacts.

    This scope never waives contact eligibility, consent or family checks.
    There is deliberately no HTTP endpoint that creates or expands this grant.
    """
    grant = db.execute('SELECT * FROM recdebut_sms_review_exceptions WHERE draft_id=?', (row['id'],)).fetchone()
    if not grant or grant['state'] not in ('PREPARED', 'RUNNING'):
        return None
    try:
        draft, authority = json.loads(row['payload']), json.loads(grant['payload'])
        ids = draft.get('person_ids', [])
        expires = datetime.fromisoformat(authority['expires_at'])
        if (draft.get('channel') != 'sms' or not 1 <= len(ids) <= 25
                or len(set(ids)) != len(ids) or set(ids) != set(authority['recipients'])
                or digest(authority) != grant['digest'] or not authority['actor'].strip()
                or authority['draft_id'] != row['id'] or authority['draft_revision'] != row['revision']
                or authority['draft_sha256'] != digest(draft)
                or expires.utcoffset() != timezone.utc.utcoffset(expires)
                or expires <= datetime.now(timezone.utc)):
            return None
        for pid in ids:
            person = db.execute("SELECT revision,payload FROM recdebut_workflow WHERE id=? AND kind='person'", (pid,)).fetchone()
            expected = authority['recipients'][pid]
            if (not person or person['revision'] != expected['revision']
                    or digest(json.loads(person['payload'])) != expected['payload_sha256']):
                return None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    return {'id': grant['id'], 'digest': grant['digest']}


def draft_preview(db, row):
    payload = json.loads(row['payload'])
    exception = sms_review_exception(db, row)
    audience = []
    seen = set()
    for person_id in payload.get('person_ids', []):
        person = db.execute("SELECT * FROM recdebut_workflow WHERE id=? AND kind='person'", (person_id,)).fetchone()
        p = json.loads(person['payload']) if person else {}
        channel = payload.get('channel')
        address = p.get('phone' if channel == 'sms' else 'email', '')
        reasons = []
        if not person: reasons.append('Contact missing')
        allowed_roles = ('parent', 'guardian', 'athlete') if channel == 'email' else ('parent', 'guardian')
        if p.get('role') == 'coach':
            reasons.append('Coach identity excluded')
        elif p.get('role') not in allowed_roles:
            reasons.append('Athlete/parent/guardian role required; coaches excluded' if channel == 'email'
                           else 'Parent/guardian role required')
        # Direct athlete email uses the athlete's sourced contact permission.
        # A parent/guardian destination still requires verified family linkage.
        if not (channel == 'email' and p.get('role') == 'athlete'):
            if not p.get('family_id') or p.get('relationship') != 'verified': reasons.append('Family relationship unverified')
        if p.get(channel + '_permission') != 'granted' or not p.get('permission_evidence'): reasons.append('Channel permission unconfirmed')
        if p.get(channel + '_permission') == 'denied': reasons.append('Channel permission denied')
        if not p.get('source'): reasons.append('Contact source missing')
        if not address: reasons.append('Destination missing')
        if address and db.execute('SELECT 1 FROM recdebut_suppressions WHERE destination=?', (address,)).fetchone(): reasons.append('Suppressed / opted out')
        if address in seen: reasons.append('Shared destination: review relationship')
        if address: seen.add(address)
        # Template rendering is intentionally limited and cannot execute expressions.
        # A historical athlete name does not identify the parent who owns a phone.
        greeting = '' if exception and (p.get('role') not in ('parent', 'guardian')
                                        or p.get('relationship') != 'verified') else p.get('name', '')
        rendered = personalize_message(payload.get('body', ''), greeting)
        body = rendered['message']
        if not body.strip() or any(c in body for c in '{}[]'): reasons.append('Message personalization needs review')
        audience.append({'person_id': person_id, 'person_revision': person['revision'] if person else None,
                         'name': p.get('name', 'Missing contact'), 'destination': address,
                         **rendered, 'reasons': reasons, 'eligible_for_review': not reasons})
    # Bind actual contact content and opt-out state through the preview, plus draft revision.
    bound = {'draft_id': row['id'], 'revision': row['revision'], 'draft': payload, 'audience': audience}
    if exception: bound['review_exception'] = exception
    return {**bound, 'digest': digest(bound), 'sending_enabled': False,
            'reviewable': bool(audience) and all(not a['reasons'] for a in audience)}


@router.get('/drafts/{record_id}/preview')
def preview(record_id: str, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with connect() as db:
        row = db.execute("SELECT * FROM recdebut_workflow WHERE id=? AND kind='draft'", (record_id,)).fetchone()
        if not row: raise HTTPException(404, 'Draft not found.')
        return {'success': True, 'preview': draft_preview(db, row)}


@router.post('/drafts/{record_id}/review')
def record_review(record_id: str, data: ReviewRecord):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT * FROM recdebut_workflow WHERE id=? AND kind='draft'", (record_id,)).fetchone()
        if not row: raise HTTPException(404, 'Draft not found.')
        current = draft_preview(db, row)
        if row['revision'] != data.revision or current['digest'] != data.expected_digest:
            raise HTTPException(409, 'Draft, contact or suppression changed. Review the current preview.')
        if not current['reviewable']: raise HTTPException(422, 'Resolve the audience and message warnings first.')
        event(db, record_id, row['revision'], 'review_recorded_not_send_authorization', data.actor, current)
    return {'success': True, 'sending_enabled': False, 'digest': current['digest']}


@router.post('/suppressions')
def suppress(data: Suppression):
    address = destination(data.destination)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT INTO recdebut_suppressions VALUES(?,?,?,?) ON CONFLICT(destination) DO NOTHING',
                   (address, data.reason, data.actor, now()))
        event(db, address, 1, 'suppressed', data.actor, {'destination': address, 'reason': data.reason})
    return {'success': True, 'sending_enabled': False}


# Explicit plans and public opt-out intake; no scheduler or automatic dispatch.
from recdebut_delivery import router as delivery_router
router.include_router(delivery_router)
from recdebut_reply_forwarding import router as reply_forwarding_router
router.include_router(reply_forwarding_router)
