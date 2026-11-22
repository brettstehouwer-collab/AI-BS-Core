"""Durable TextBee intake. This module cannot dispatch, forward or enable polling.

Known recruiting replies use the existing inbox. Unknown/personal ordinary text
is excluded from that inbox; only its event digest/disposition is retained.
Opt-outs always enter the existing common suppression store, even when roster or
personal-contact checks cannot classify a sender. START never restores consent.
"""
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

import recdebut_workflow as workflow
from security.recdebut_privacy import normalize_phone, load_personal_contacts, PrivacyCheckUnavailable
from security.recdebut_access import textbee_body

STOP_WORDS = frozenset({'STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT', 'REVOKE', 'OPT OUT'})
IDENTITY = re.compile(r'[A-Za-z0-9_.:-]{1,160}')


def configured_device():
    value = os.environ.get('TEXTBEE_DEVICE_ID')
    if value is None:
        value = dotenv_values(Path(__file__).resolve().parents[1] / '.env').get('TEXTBEE_DEVICE_ID', '')
    if not value or not value.strip():
        raise HTTPException(503, 'SMS intake device is not configured.')
    return value.strip()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def validate(payload):
    if not isinstance(payload, dict):
        raise HTTPException(422, 'An SMS event object is required.')
    for field in ('smsId', 'deviceId', 'webhookSubscriptionId', 'idempotencyKey'):
        value = payload.get(field)
        if not isinstance(value, str) or not IDENTITY.fullmatch(value):
            raise HTTPException(422, 'SMS event identity is missing or invalid.')
    if payload.get('webhookEvent') != 'MESSAGE_RECEIVED':
        raise HTTPException(422, 'Only MESSAGE_RECEIVED events are accepted here.')
    if payload['deviceId'] != configured_device():
        raise HTTPException(403, 'SMS event device does not match this intake.')
    phone = payload.get('sender')
    if not isinstance(phone, str) or len(phone) > 80 or not normalize_phone(phone):
        raise HTTPException(422, 'A valid SMS sender is required.')
    message = payload.get('message')
    if not isinstance(message, str) or not message.strip() or len(message) > 16000 or '\x00' in message:
        raise HTTPException(422, 'SMS message is empty, invalid or exceeds 16000 characters.')
    try:
        received = datetime.fromisoformat(payload['receivedAt'].replace('Z', '+00:00'))
        if received.tzinfo is None or received.utcoffset() is None:
            raise ValueError('Timezone required')
        received = received.astimezone(timezone.utc)
    except (KeyError, AttributeError, TypeError, ValueError, OverflowError):
        raise HTTPException(422, 'A timezone-aware receivedAt timestamp is required.')
    # Equivalent formatting and retries across subscriptions identify the same SMS.
    content = {k: v for k, v in payload.items() if k not in ('idempotencyKey', 'webhookSubscriptionId')}
    content.update(sender=normalize_phone(phone), receivedAt=received.isoformat())
    return content, received


def matching_contacts(db, phone):
    db.create_function('recdebut_phone', 1, normalize_phone, deterministic=True)
    athletes = db.execute('SELECT id,name FROM rec_debut_athletes WHERE recdebut_phone(phone)=?', (phone,)).fetchmany(2)
    athlete = dict(athletes[0]) if len(athletes) == 1 else None
    people = []
    for row in db.execute("SELECT id,payload FROM recdebut_workflow WHERE kind='person'"):
        data = json.loads(row['payload'])
        if normalize_phone(data.get('phone')) == phone:
            people.append(data)
    families = sorted({p['family_id'] for p in people if p.get('family_id')})
    return athlete, people, families


def store_reply(payload, raw_digest):
    content, received = validate(payload)
    content_digest = workflow.digest(content)
    phone, message = content['sender'], content['message']
    keyword = re.sub(r'\s+', ' ', message.strip().rstrip('.!').strip()).upper()
    is_stop = keyword in STOP_WORDS
    with workflow.connect() as db:
        # Serialize replay checks and all effects, including STOP and receipt.
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT * FROM recdebut_textbee_receipts WHERE idempotency_key=?', (payload['idempotencyKey'],)).fetchone()
        if previous:
            if (previous['digest'] != content_digest or previous['subscription_id'] != payload['webhookSubscriptionId']):
                raise HTTPException(409, 'SMS delivery identity was reused with changed inputs.')
            return result(previous['outcome'], True)
        previous_sms = db.execute('SELECT * FROM recdebut_textbee_receipts WHERE device_id=? AND sms_id=? LIMIT 1',
                                  (content['deviceId'], content['smsId'])).fetchone()
        if previous_sms and previous_sms['digest'] != content_digest:
            raise HTTPException(409, 'SMS identity was reused with changed inputs.')
        if previous_sms:
            outcome = previous_sms['outcome']
        else:
            outcome = persist_message(db, content, received, is_stop, keyword)
        db.execute('''INSERT INTO recdebut_textbee_receipts
            (idempotency_key,device_id,sms_id,subscription_id,digest,raw_sha256,outcome,received_at)
            VALUES(?,?,?,?,?,?,?,?)''', (payload['idempotencyKey'], content['deviceId'], content['smsId'],
            payload['webhookSubscriptionId'], content_digest, raw_digest, outcome, workflow.now()))
    # No success is returned until the context manager has committed.
    return result(outcome, bool(previous_sms))


def persist_message(db, content, received, is_stop, keyword):
    phone = content['sender']
    if is_stop:
        db.execute('INSERT INTO recdebut_suppressions VALUES(?,?,?,?) ON CONFLICT(destination) DO NOTHING',
                   (phone, 'TextBee inbound opt-out: ' + keyword, 'textbee:signed_inbound', workflow.now()))
        workflow.event(db, phone, 1, 'sms_opt_out_received', 'textbee:signed_inbound',
                       {'destination': phone, 'sms_id': content['smsId'], 'keyword': keyword})
        # CRM enrichment must not undo a valid opt-out. Core suppression and
        # receipt failures still roll back the entire transaction and return 503.
        db.execute('SAVEPOINT optional_crm')
        try:
            outcome = persist_classified_reply(db, content, received, is_stop)
        except (sqlite3.Error, PrivacyCheckUnavailable, ValueError, TypeError, AttributeError) as exc:
            db.execute('ROLLBACK TO optional_crm')
            db.execute('RELEASE optional_crm')
            workflow.event(db, phone, 1, 'sms_opt_out_classification_deferred', 'textbee:signed_inbound',
                           {'sms_id': content['smsId'], 'error_type': type(exc).__name__})
            return 'suppressed'
        db.execute('RELEASE optional_crm')
        return outcome
    return persist_classified_reply(db, content, received, is_stop)


def persist_classified_reply(db, content, received, is_stop):
    phone = content['sender']
    excluded, _ = load_personal_contacts()
    if phone in excluded:
        return 'suppressed' if is_stop else 'ignored_personal'
    athlete, people, families = matching_contacts(db, phone)
    if not athlete and not people:
        return 'suppressed' if is_stop else 'ignored_unmatched'
    message_key = 'textbee_' + content['smsId']
    existing = db.execute('SELECT sender_phone,reply_body FROM rec_debut_athlete_replies WHERE message_id_hash=?', (message_key,)).fetchone()
    if existing:
        if normalize_phone(existing['sender_phone']) != phone or existing['reply_body'] != content['message']:
            raise HTTPException(409, 'Retained legacy SMS has conflicting content.')
    else:
        db.execute('''INSERT INTO rec_debut_athlete_replies
            (athlete_id,athlete_name,sender_phone,sender_email,recipient_email,subject,reply_body,received_at,is_read,created_at,message_id_hash)
            VALUES(?,?,?,?,?,?,?,?,0,?,?)''', (athlete['id'] if athlete else None,
            athlete['name'] if athlete else people[0].get('name', 'Family contact'), phone, '', '',
            'TextBee incoming reply', content['message'], received.timestamp(), datetime.now(timezone.utc).timestamp(), message_key))
        if athlete and not is_stop:
            db.execute("UPDATE rec_debut_athletes SET status='Replied' WHERE id=?", (athlete['id'],))
    for family in families:
        workflow.history(db, family, message_key, 'sms_opt_out_received' if is_stop else 'sms_reply_received',
                         'textbee:signed_inbound', {'sms_id': content['smsId'], 'reply_key': message_key, 'suppressed': is_stop})
    return 'suppressed' if is_stop else 'stored'


def result(outcome, duplicate):
    return {'success': True, 'status': outcome, 'duplicate': duplicate, 'sending_enabled': False, 'forwarded': False}


async def receive_textbee_webhook(request: Request):
    raw = await textbee_body(request)
    try:
        payload = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Invalid JSON number')))
    except (UnicodeError, ValueError, RecursionError):
        raise HTTPException(400, 'Invalid SMS event JSON.')
    try:
        return await run_in_threadpool(store_reply, payload, hashlib.sha256(raw).hexdigest())
    except (sqlite3.Error, OSError, PrivacyCheckUnavailable, ValueError, TypeError, AttributeError):
        raise HTTPException(503, 'SMS intake could not commit; retry delivery.', headers={'Retry-After': '30'})
