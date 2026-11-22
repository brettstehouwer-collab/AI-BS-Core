"""Receive-only email opt-outs. Never forwards, acknowledges, or sends mail.

Only existing RecDebut contacts may enter this intake. Message bodies and subjects
are inspected in memory and are never retained here. The shared suppression table
is the authority consumed by reviewed outbound delivery paths.
"""
import json
import re
import sqlite3
import email
import hashlib
import time
import uuid
from email.header import decode_header, make_header

import recdebut_workflow as workflow
from security.recdebut_privacy import PrivacyCheckUnavailable, load_personal_contacts, normalize_phone


def normalize_email(value):
    """Accept one plain ASCII mailbox, excluding headers and display-name input."""
    if not isinstance(value, str) or any(char in value for char in '\r\n'):
        return ''
    value = value.strip()
    if len(value) > 254 or not value.isascii() or value.count('@') != 1:
        return ''
    local, domain = value.rsplit('@', 1)
    if not 1 <= len(local) <= 64 or not re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+", local):
        return ''
    if local.startswith('.') or local.endswith('.') or '..' in local:
        return ''
    labels = domain.split('.')
    if len(labels) < 2 or any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label) for label in labels):
        return ''
    if not re.fullmatch(r'[A-Za-z]{2,63}', labels[-1]):
        return ''
    return value.casefold()


def opt_out_keyword(subject, body):
    """Use an exact subject or the first nonblank reply line, never quoted text."""
    if not isinstance(subject, str) or not isinstance(body, str):
        return ''
    if len(subject) > 1000 or '\r' in subject or '\n' in subject:
        return ''
    subject = re.sub(r'^(?:\s*re:\s*)+', '', subject, flags=re.IGNORECASE).strip()
    first_line = next((line.strip() for line in body[:65536].splitlines() if line.strip()), '')
    for candidate in (subject, first_line):
        match = re.fullmatch(r'(STOP|UNSUBSCRIBE)[.!]?', candidate, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return ''


def _known_contact_phones(db, sender):
    phones = []
    known = False
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='rec_debut_athletes'").fetchone():
        for row in db.execute('SELECT email,phone FROM rec_debut_athletes WHERE LOWER(TRIM(email))=?', (sender,)):
            if normalize_email(row['email']) == sender:
                known = True
                phones.append(normalize_phone(row['phone']))
    for row in db.execute("SELECT payload FROM recdebut_workflow WHERE kind='person'"):
        try:
            person = json.loads(row['payload'])
        except (TypeError, ValueError):
            continue
        if not isinstance(person, dict) or normalize_email(person.get('email')) != sender:
            continue
        known = True
        phones.append(normalize_phone(person.get('phone')))
    return known, phones


def process_email_opt_out(sender_email, subject='', body=''):
    """Persist one known-contact STOP/UNSUBSCRIBE while all sending stays off.

    ``handled`` prevents a recognized opt-out, including rejected intake, from
    falling through to legacy forwarding. ``success`` means suppression exists;
    it never means an email or acknowledgment was sent.
    """
    result = {'handled': False, 'success': False, 'status': 'not_opt_out',
              'channel': 'email', 'forwarded': False, 'sending_enabled': False}
    keyword = opt_out_keyword(subject, body)
    if not keyword:
        return result
    result['handled'] = True
    sender = normalize_email(sender_email)
    if not sender:
        return result | {'status': 'invalid_sender'}
    try:
        personal_phones, personal_emails = load_personal_contacts()
    except PrivacyCheckUnavailable:
        return result | {'status': 'privacy_unavailable'}
    if sender in personal_emails:
        return result | {'status': 'personal_contact'}
    try:
        with workflow.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            known, phones = _known_contact_phones(db, sender)
            if not known:
                return result | {'status': 'unknown_contact'}
            if any(phone and phone in personal_phones for phone in phones):
                return result | {'status': 'personal_contact'}
            inserted = db.execute(
                'INSERT INTO recdebut_suppressions(destination,reason,actor,created_at) VALUES(?,?,?,?) '
                'ON CONFLICT(destination) DO NOTHING',
                (sender, 'Email inbound opt-out: ' + keyword, 'email:receive_only', workflow.now()),
            ).rowcount == 1
            if inserted:
                workflow.event(db, sender, 1, 'email_opt_out_received', 'email:receive_only',
                               {'channel': 'email', 'destination': sender, 'keyword': keyword})
        return result | {'success': True, 'status': 'suppressed', 'already_suppressed': not inserted}
    except sqlite3.Error:
        return result | {'status': 'storage_unavailable'}


class _MailboxReadError(Exception):
    """A fixed diagnostic code, never provider response text or message content."""


def _response_number(mail, name):
    label, values = mail.response(name)
    if label != name or not isinstance(values, list) or len(values) != 1:
        raise _MailboxReadError('invalid_mailbox_identity')
    raw = values[0]
    if not isinstance(raw, bytes) or not re.fullmatch(rb'[1-9][0-9]{0,9}', raw):
        raise _MailboxReadError('invalid_mailbox_identity')
    number = int(raw)
    if number > 4294967295:
        raise _MailboxReadError('invalid_mailbox_identity')
    return number


def _bounded_fetch(mail, uid, fields, limit):
    status, values = mail.uid('fetch', str(uid), f'(UID RFC822.SIZE {fields}<0.{limit}>)')
    if status != 'OK' or not isinstance(values, list):
        raise _MailboxReadError('message_fetch_failed')
    literals = [item for item in values if isinstance(item, tuple)]
    if len(literals) != 1 or len(literals[0]) != 2:
        raise _MailboxReadError('invalid_fetch_response')
    metadata, raw = literals[0]
    if not isinstance(metadata, bytes) or not isinstance(raw, bytes) or len(raw) > limit:
        raise _MailboxReadError('message_read_limit')
    uid_match = re.search(rb'\bUID ([1-9][0-9]*)\b', metadata)
    size_match = re.search(rb'\bRFC822.SIZE ([0-9]+)\b', metadata)
    if not uid_match or int(uid_match[1]) != uid or not size_match:
        raise _MailboxReadError('invalid_fetch_response')
    return raw, int(size_match[1])


def _header_text(value):
    try:
        return str(make_header(decode_header(value or '')))
    except (LookupError, UnicodeError, ValueError):
        return ''


def _leading_plain_body(raw):
    message = email.message_from_bytes(raw)
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_type() != 'text/plain' or part.get_content_disposition() == 'attachment':
            continue
        try:
            payload = part.get_payload(decode=True)
            return payload.decode(part.get_content_charset() or 'utf-8', errors='replace')[:65536] if isinstance(payload, bytes) else ''
        except (LookupError, UnicodeError, ValueError):
            return ''
    return ''


def sync_receive_only_mailbox(mail, mailbox_identity, max_messages=50):
    """Read one bounded UID window in a caller-selected, read-only IMAP mailbox.

    This function neither connects nor schedules polling. The durable cursor is
    advanced only after an inspected UID; an interrupted suppression is replayed
    idempotently. Only mailbox identity hashes/cursors and common suppressions are
    saved. Unknown/personal message bodies are never requested. From is untrusted:
    its only possible effect is suppressing an existing RecDebut email address.
    """
    result = {'success': False, 'status': 'not_started', 'receive_only': True,
              'new_replies_forwarded': 0, 'email_opt_outs_processed': 0,
              'email_opt_outs_already_suppressed': 0, 'messages_scanned': 0,
              'last_uid': 0, 'items': []}
    if (not isinstance(mailbox_identity, str) or not 1 <= len(mailbox_identity) <= 1000
            or type(max_messages) is not int or not 1 <= max_messages <= 50):
        return result | {'status': 'invalid_read_scope'}
    mailbox_hash = hashlib.sha256(mailbox_identity.encode('utf-8')).hexdigest()
    owner = uuid.uuid4().hex
    acquired = False
    try:
        # No mailbox search/header/body reads when personal exclusions are absent.
        load_personal_contacts()
        validity = str(_response_number(mail, 'UIDVALIDITY'))
        highest_uid = _response_number(mail, 'UIDNEXT') - 1
        with workflow.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS recdebut_email_inbox_progress ('
                       'mailbox_sha256 TEXT PRIMARY KEY,uid_validity TEXT NOT NULL,last_uid INTEGER NOT NULL,'
                       'lease_owner TEXT NOT NULL,lease_until REAL NOT NULL,updated_at TEXT NOT NULL,'
                       'last_error TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT * FROM recdebut_email_inbox_progress WHERE mailbox_sha256=?', (mailbox_hash,)).fetchone()
            if previous and previous['lease_owner'] and previous['lease_until'] > time.time():
                return result | {'status': 'mailbox_busy', 'last_uid': previous['last_uid']}
            cursor = previous['last_uid'] if previous and previous['uid_validity'] == validity else 0
            db.execute('INSERT INTO recdebut_email_inbox_progress VALUES(?,?,?,?,?,?,?) '
                       'ON CONFLICT(mailbox_sha256) DO UPDATE SET uid_validity=excluded.uid_validity,'
                       'last_uid=excluded.last_uid,lease_owner=excluded.lease_owner,'
                       'lease_until=excluded.lease_until,updated_at=excluded.updated_at,last_error=excluded.last_error',
                       (mailbox_hash, validity, cursor, owner, time.time() + 180, workflow.now(), ''))
        acquired = True
        result['last_uid'] = cursor

        def advance(new_cursor):
            with workflow.connect() as db:
                changed = db.execute('UPDATE recdebut_email_inbox_progress SET last_uid=?,lease_until=?,updated_at=? '
                                     'WHERE mailbox_sha256=? AND uid_validity=? AND lease_owner=? AND lease_until>?',
                                     (new_cursor, time.time() + 180, workflow.now(), mailbox_hash, validity, owner, time.time())).rowcount
                if changed != 1:
                    raise _MailboxReadError('mailbox_lease_lost')
            result['last_uid'] = new_cursor

        upper = min(highest_uid, cursor + 1000)
        if upper > cursor:
            status, values = mail.uid('search', None, f'UID {cursor + 1}:{upper}')
            if status != 'OK' or not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], bytes):
                raise _MailboxReadError('uid_search_failed')
            if len(values[0]) > 12000 or not re.fullmatch(rb'(?:[1-9][0-9]*(?: [1-9][0-9]*)*)?', values[0]):
                raise _MailboxReadError('invalid_uid_response')
            uids = [int(value) for value in values[0].split()]
            if len(uids) > 1000 or len(set(uids)) != len(uids) or any(uid <= cursor or uid > upper for uid in uids):
                raise _MailboxReadError('invalid_uid_response')
            uids.sort()
            for uid in uids[:max_messages]:
                advance(result['last_uid'])  # Renew and verify exclusion before each fetch.
                personal_phones, personal_emails = load_personal_contacts()
                raw_headers, _ = _bounded_fetch(mail, uid, 'BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)]', 8192)
                if len(raw_headers) == 8192:
                    raise _MailboxReadError('header_read_limit')
                headers = email.message_from_bytes(raw_headers)
                from_headers = headers.get_all('From', [])
                subjects = headers.get_all('Subject', [])
                mailboxes = email.utils.getaddresses(from_headers)
                sender = normalize_email(mailboxes[0][1]) if len(from_headers) == 1 and len(mailboxes) == 1 else ''
                subject = _header_text(subjects[0]) if len(subjects) == 1 else ''
                with workflow.connect() as db:
                    known, phones = _known_contact_phones(db, sender) if sender else (False, [])
                # Exclusions may change while IMAP is returning headers. Reload
                # immediately before deciding whether any body may be requested.
                personal_phones, personal_emails = load_personal_contacts()
                if known and sender not in personal_emails and not any(phone and phone in personal_phones for phone in phones):
                    body = ''
                    if not opt_out_keyword(subject, ''):
                        # Request a bounded prefix, never RFC822 or an unbounded body.
                        raw_message, full_size = _bounded_fetch(mail, uid, 'BODY.PEEK[]', 65536)
                        body = _leading_plain_body(raw_message)
                        if not opt_out_keyword(subject, body) and full_size > len(raw_message):
                            # An unseen MIME text part may contain STOP. Retain UID
                            # for explicit review rather than silently skipping it.
                            raise _MailboxReadError('body_prefix_incomplete')
                    processed = process_email_opt_out(sender, subject, body)
                    if processed['status'] in {'privacy_unavailable', 'storage_unavailable'}:
                        raise _MailboxReadError(processed['status'])
                    if processed.get('success'):
                        if processed.get('already_suppressed'):
                            result['email_opt_outs_already_suppressed'] += 1
                        else:
                            result['email_opt_outs_processed'] += 1
                            result['items'].append(processed)
                advance(uid)
                result['messages_scanned'] += 1
            if len(uids) <= max_messages:
                advance(upper)  # Empty/expunged UID gaps must not stall progression.
        result.update(success=True, status='scanned')
    except PrivacyCheckUnavailable:
        result['status'] = 'privacy_unavailable'
    except sqlite3.Error:
        result['status'] = 'storage_unavailable'
    except _MailboxReadError as exc:
        result['status'] = str(exc)
    except Exception:
        result['status'] = 'mailbox_read_failed'
    finally:
        if acquired:
            try:
                with workflow.connect() as db:
                    db.execute('UPDATE recdebut_email_inbox_progress SET lease_owner=?,lease_until=0,last_error=?,updated_at=? '
                               'WHERE mailbox_sha256=? AND lease_owner=?',
                               ('', '' if result['success'] else result['status'], workflow.now(), mailbox_hash, owner))
            except sqlite3.Error:
                result.update(success=False, status='storage_unavailable')
    return result
