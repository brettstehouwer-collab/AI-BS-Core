"""IONOS campaign replies to the fixed staff address; never sends to athletes.

Independent of campaign activation. Only a recorded ACCEPTED email Message-ID
and its exact athlete sender can authorize a copy. Ambiguous submissions are
reserved permanently for manual reconciliation. Mailbox reads never mark seen.
"""
import asyncio
import email
import hashlib
import imaplib
import json
import os
import re
import sqlite3
import ssl
import time
import uuid
import threading
from email import policy
from email.message import EmailMessage
from email.utils import getaddresses, make_msgid

from fastapi import APIRouter, Response
import recdebut_delivery as delivery
from security.recdebut_privacy import load_personal_contacts, normalize_phone, PrivacyCheckUnavailable

router = APIRouter()
STAFF = 'dbell002@sbcglobal.net'
ACCOUNT = 'brett@stehouwerproductions.com'
MARKER = 'recdebut-reply-copy-v1'
IDS = re.compile(r'<[^<>\s]{1,196}@[^<>\s]{1,196}>')
MAX_BODY = 262144


def intake():
    import recdebut_email_unsubscribe
    return recdebut_email_unsubscribe


def schema(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS recdebut_reply_progress (
            mailbox TEXT PRIMARY KEY,validity TEXT NOT NULL,last_uid INTEGER NOT NULL,
            lease_owner TEXT NOT NULL,lease_until REAL NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_reply_copies (
            key TEXT PRIMARY KEY,plan_id TEXT NOT NULL,state TEXT NOT NULL,
            receipt_id TEXT NOT NULL,code TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recdebut_reply_connector (
            id INTEGER PRIMARY KEY CHECK(id=1),attempted_at TEXT NOT NULL,
            succeeded_at TEXT NOT NULL,status TEXT NOT NULL,details TEXT NOT NULL);
    ''')


def profile():
    sender = delivery.sender_profile('email')
    p = {'enabled': os.environ.get('RECDEBUT_REPLY_FORWARDING_ENABLED', '').lower() == 'true',
         'host': os.environ.get('RECDEBUT_IMAP_HOST', ''),
         'port': os.environ.get('RECDEBUT_IMAP_PORT', ''),
         'user': os.environ.get('RECDEBUT_IMAP_USER', ''),
         'password': os.environ.get('RECDEBUT_IMAP_PASSWORD', ''),
         'folder': os.environ.get('RECDEBUT_IMAP_FOLDER', 'INBOX'), 'smtp': sender}
    p['configured'] = (p['host'] == 'imap.ionos.com' and p['port'] == '993'
                       and p['user'] == ACCOUNT and bool(p['password']) and p['folder'] == 'INBOX'
                       and sender.get('sender') == ACCOUNT and sender.get('copy_to') == STAFF
                       and sender.get('smtp_user') == ACCOUNT and sender.get('smtp_host') == 'smtp.ionos.com'
                       and sender.get('smtp_mode') == 'starttls' and sender.get('smtp_port') == '587'
                       and bool(sender.get('smtp_password')))
    p['digest'] = delivery.workflow().digest(p)
    return p


def allowed_sender(db, sender):
    phones, emails = load_personal_contacts()
    if not sender or sender in (ACCOUNT, STAFF) or sender in emails:
        return False
    rows = list(delivery.identity_rows(db))
    matches = [r for r in rows if intake().normalize_email(r.get('email')) == sender]
    if not matches or not any(r.get('role') == 'athlete' for r in matches):
        return False
    linked_phones = {normalize_phone(r.get('phone')) for r in matches} - {''}
    linked_names = {delivery.normalized_name(r.get('name')) for r in matches} - {''}
    for row in rows:
        if (intake().normalize_email(row.get('email')) != sender
                and normalize_phone(row.get('phone')) not in linked_phones
                and delivery.normalized_name(row.get('name')) not in linked_names): continue
        if (row.get('role') == 'coach' or intake().normalize_email(row.get('email')) in emails
                or normalize_phone(row.get('phone')) in phones
                or normalize_phone(row.get('phone')) in {'6164023628','6166003837','6164067993'}
                or re.search(r'\b(test|synthetic|fictional)\b', ' '.join(str(row.get(k, '')) for k in ('name','notes','source')), re.I)):
            return False
    return True


def correlate(db, headers, sender):
    refs = set(IDS.findall(' '.join(headers.get_all('In-Reply-To', []) + headers.get_all('References', []))))
    if not refs or len(refs) > 100:
        return None
    matches = {}
    for ref in refs:
        for row in db.execute("SELECT * FROM recdebut_send_attempts WHERE state='ACCEPTED' AND receipt_id=?", (ref,)):
            try:
                _, plan = delivery.load_plan(db, row['plan_id'])
                person = next(r for r in plan['recipients'] if r['person_id'] == row['person_id'])
                if plan['channel'] == 'email' and intake().normalize_email(person['destination']) == sender:
                    matches[row['dedup_key']] = row['plan_id']
            except (ValueError, KeyError, TypeError, StopIteration, delivery.HTTPException):
                continue
    return next(iter(matches.values())) if len(matches) == 1 else None


def safe_body(raw):
    message = email.message_from_bytes(raw, policy=policy.default)
    def visible_parts(part):
        if part.get_content_disposition() == 'attachment' or part.get_content_maintype() == 'message':
            return
        if part.is_multipart():
            for child in part.iter_parts(): yield from visible_parts(child)
        else: yield part
    parts = list(visible_parts(message))
    text = ''
    for part in parts:
        if part.get_content_type() == 'text/plain':
            text = str(part.get_content())[:65536]; break
    if not text:
        # HTML-only replies are common. Render inert text; never load remote content.
        from html.parser import HTMLParser
        class Text(HTMLParser):
            def __init__(self):
                super().__init__(); self.chunks = []; self.hidden = 0
            def handle_starttag(self, tag, attrs):
                if tag in ('script','style'): self.hidden += 1
                if tag in ('p','br','div','blockquote'): self.chunks.append('\n')
            def handle_endtag(self, tag):
                if tag in ('script','style'): self.hidden = max(0,self.hidden-1)
                if tag in ('p','div','blockquote'): self.chunks.append('\n')
            def handle_data(self, data):
                if not self.hidden: self.chunks.append(data)
        for part in parts:
            if part.get_content_type() == 'text/html' and part.get_content_disposition() != 'attachment':
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    parser = Text(); parser.feed(payload.decode(part.get_content_charset() or 'utf-8', errors='replace'))
                    text = ''.join(parser.chunks)[:65536]; break
    # Remove opaque recipient capabilities, including quoted versions.
    text = re.sub(r'https?://[^\s<>\"]*/(?:api/v1/recdebut/workflow/)?(?:unsubscribe|links)/[^\s<>\"]+',
                  '[recipient link omitted]', text, flags=re.I)
    return text[:65536]


def copy_reply(p, key, plan_id, sender, subject, body, scope_check):
    with delivery.workflow().connect() as db:
        schema(db); db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM recdebut_reply_copies WHERE key=?', (key,)).fetchone():
            return 'duplicate'
        db.execute('INSERT INTO recdebut_reply_copies VALUES(?,?,?,?,?,?)',
                   (key, plan_id, 'ATTEMPTING', '', '', delivery.workflow().now()))
    message = EmailMessage()
    message['From'] = 'Recreational Debut <' + ACCOUNT + '>'
    message['To'] = STAFF; message['Reply-To'] = sender
    message['Subject'] = 'RecDebut athlete reply: ' + subject[:180].replace('\r',' ').replace('\n',' ')
    message['Message-ID'] = make_msgid(domain=ACCOUNT.split('@')[1])
    message['Auto-Submitted'] = 'auto-generated'; message['X-RecDebut-Forwarded'] = MARKER
    message.set_content('Athlete reply from: ' + sender + '\n\n' + body +
                        '\n\n[Staff copy. Attachments omitted; original remains in the IONOS inbox.]')
    def before_submit():
        scope_check()
        fresh = profile()
        with delivery.workflow().connect() as db:
            if (not fresh['enabled'] or not fresh['configured'] or fresh['digest'] != p['digest']
                    or not allowed_sender(db, sender)):
                raise delivery.DeliveryBlocked('Reply forwarding configuration or privacy changed.')
    receipt, code = '', ''
    try:
        before_submit()
        result = delivery.submit_smtp(p['smtp'], message, STAFF, before_submit)
        state = 'ACCEPTED' if result.get('state') == 'ACCEPTED' else 'UNCERTAIN'
        receipt = str(result.get('receipt_id', ''))[:200]
    except delivery.DeliveryBlocked:
        state, code = 'BLOCKED', 'configuration_or_privacy_changed'
    except Exception:
        state, code = 'UNCERTAIN', 'smtp_outcome_unconfirmed'
    with delivery.workflow().connect() as db:
        db.execute('UPDATE recdebut_reply_copies SET state=?,receipt_id=?,code=?,updated_at=? WHERE key=?',
                   (state, receipt, code, delivery.workflow().now(), key))
    return state.lower()


def sync_mailbox(mail, p, max_messages=50, stop=None):
    result = {'status': 'not_started','scanned': 0,'matched': 0,'accepted': 0,'duplicate': 0,
              'blocked': 0,'uncertain': 0,'oversize': 0,'last_uid': 0,'highest_uid': 0}
    if not p['enabled'] or not p['configured'] or not 1 <= max_messages <= 50:
        return result | {'status': 'disabled_or_unconfigured'}
    mailbox = delivery.workflow().digest([p['host'],p['user'],p['folder']])
    owner, acquired = uuid.uuid4().hex, False
    try:
        load_personal_contacts()
        validity = str(intake()._response_number(mail, 'UIDVALIDITY'))
        highest = intake()._response_number(mail, 'UIDNEXT') - 1
        result['highest_uid'] = highest
        with delivery.workflow().connect() as db:
            schema(db); delivery.schema(db); db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM recdebut_reply_progress WHERE mailbox=?', (mailbox,)).fetchone()
            if old and old['lease_until'] > time.time():
                return result | {'status': 'mailbox_busy'}
            cursor = old['last_uid'] if old and old['validity'] == validity else 0
            db.execute('INSERT INTO recdebut_reply_progress VALUES(?,?,?,?,?,?) ON CONFLICT(mailbox) DO UPDATE SET '
                       'validity=excluded.validity,last_uid=excluded.last_uid,lease_owner=excluded.lease_owner,'
                       'lease_until=excluded.lease_until,updated_at=excluded.updated_at',
                       (mailbox,validity,cursor,owner,time.time()+180,delivery.workflow().now()))
        acquired = True
        def still_active():
            if stop is not None and stop.is_set():
                raise delivery.DeliveryBlocked('Reply worker stopped.')
            fresh = profile()
            if not fresh['enabled'] or not fresh['configured'] or fresh['digest'] != p['digest']:
                raise delivery.DeliveryBlocked('Reply configuration changed.')
        def advance(uid):
            still_active()
            with delivery.workflow().connect() as db:
                changed = db.execute('UPDATE recdebut_reply_progress SET last_uid=?,lease_until=?,updated_at=? '
                                     'WHERE mailbox=? AND validity=? AND lease_owner=? AND lease_until>?',
                                     (uid,time.time()+180,delivery.workflow().now(),mailbox,validity,owner,time.time())).rowcount
                if changed != 1: raise intake()._MailboxReadError('mailbox_lease_lost')
            result['last_uid'] = uid
        advance(cursor)
        upper = min(highest,cursor+1000)
        if upper > cursor:
            status, values = mail.uid('search', None, f'UID {cursor+1}:{upper}')
            if (status != 'OK' or len(values) != 1 or not isinstance(values[0],bytes) or len(values[0]) > 12000
                    or not re.fullmatch(rb'(?:[1-9][0-9]*(?: [1-9][0-9]*)*)?',values[0])):
                raise intake()._MailboxReadError('uid_search_failed')
            uids = [int(v) for v in values[0].split()]
            if len(uids)>1000 or len(set(uids)) != len(uids) or any(v<=cursor or v>upper for v in uids):
                raise intake()._MailboxReadError('invalid_uid_response')
            for uid in sorted(uids)[:max_messages]:
                advance(result['last_uid'])
                headers_raw, size = intake()._bounded_fetch(mail,uid,
                    'BODY.PEEK[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID IN-REPLY-TO REFERENCES AUTO-SUBMITTED X-RECDEBUT-FORWARDED PRECEDENCE)]',16384)
                if len(headers_raw) == 16384: raise intake()._MailboxReadError('header_read_limit')
                headers = email.message_from_bytes(headers_raw)
                mailboxes = getaddresses(headers.get_all('From', []))
                sender = intake().normalize_email(mailboxes[0][1]) if len(headers.get_all('From',[]))==1 and len(mailboxes)==1 else ''
                message_ids = headers.get_all('Message-ID',[])
                message_id = message_ids[0].strip() if len(message_ids)==1 else ''
                with delivery.workflow().connect() as db:
                    permitted = allowed_sender(db,sender)
                    plan = correlate(db,headers,sender) if permitted else None
                automatic = (headers.get('Auto-Submitted','no').lower() != 'no' or headers.get('X-RecDebut-Forwarded')
                             or headers.get('Precedence','').lower() in ('bulk','list','junk'))
                if permitted and plan and not automatic and IDS.fullmatch(message_id):
                    result['matched'] += 1
                    key = delivery.workflow().digest([mailbox,message_id])
                    with delivery.workflow().connect() as db:
                        exists = db.execute('SELECT 1 FROM recdebut_reply_copies WHERE key=?',(key,)).fetchone()
                    if exists:
                        result['duplicate'] += 1
                    elif size > MAX_BODY:
                        # Retain a visible manual-review condition without blocking newer mail.
                        with delivery.workflow().connect() as db:
                            db.execute('INSERT OR IGNORE INTO recdebut_reply_copies VALUES(?,?,?,?,?,?)',
                                       (key,plan,'BLOCKED','','reply_exceeds_read_limit',delivery.workflow().now()))
                        result['oversize'] += 1
                    else:
                        with delivery.workflow().connect() as db:
                            if not allowed_sender(db,sender): raise PrivacyCheckUnavailable()
                        raw, total = intake()._bounded_fetch(mail,uid,'BODY.PEEK[]',MAX_BODY)
                        if total != len(raw): raise intake()._MailboxReadError('incomplete_message')
                        body = safe_body(raw)
                        subject = intake()._header_text(headers.get('Subject',''))
                        optout = intake().process_email_opt_out(sender,subject,body)
                        if optout['handled'] and not optout['success']:
                            raise intake()._MailboxReadError('suppression_unavailable')
                        def final_scope_check():
                            advance(result['last_uid'])
                            with delivery.workflow().connect() as db:
                                if correlate(db,headers,sender) != plan:
                                    raise delivery.DeliveryBlocked('Recorded campaign ancestor changed.')
                        result[copy_reply(p,key,plan,sender,subject,body,final_scope_check)] += 1
                advance(uid); result['scanned'] += 1
            if len(uids) <= max_messages: advance(upper)
        result['status'] = 'scanned'
    except PrivacyCheckUnavailable:
        result['status'] = 'privacy_unavailable'
    except delivery.DeliveryBlocked:
        result['status'] = 'configuration_changed_or_stopped'
    except intake()._MailboxReadError as exc:
        result['status'] = str(exc)
    except Exception:
        result['status'] = 'mailbox_read_failed'
    finally:
        if acquired:
            with delivery.workflow().connect() as db:
                db.execute('UPDATE recdebut_reply_progress SET lease_owner=?,lease_until=0 WHERE mailbox=? AND lease_owner=?',('',mailbox,owner))
    return result


def run_once(stop=None):
    p = profile()
    if not p['enabled'] or not p['configured'] or (stop is not None and stop.is_set()):
        return {'status': 'disabled_or_unconfigured'}
    attempted = delivery.workflow().now()
    with delivery.workflow().connect() as db:
        schema(db)
        db.execute("INSERT INTO recdebut_reply_connector VALUES(1,?,'','connecting','{}') ON CONFLICT(id) DO UPDATE SET attempted_at=excluded.attempted_at,status='connecting'",(attempted,))
    result = {'status': 'imap_connection_failed'}
    try:
        load_personal_contacts()
        with imaplib.IMAP4_SSL(p['host'],int(p['port']),ssl_context=ssl.create_default_context(),timeout=20) as mail:
            mail.login(p['user'],p['password'])
            status, _ = mail.select(p['folder'],readonly=True)
            if status != 'OK': raise intake()._MailboxReadError('mailbox_selection_failed')
            if stop is not None and stop.is_set(): raise delivery.DeliveryBlocked('Worker stopped.')
            optouts = intake().sync_receive_only_mailbox(mail, '\n'.join((p['host'],p['user'],p['folder'])))
            if not optouts['success'] and optouts['status'] != 'body_prefix_incomplete':
                result = {'status': 'opt_out_intake_' + optouts['status']}
            else:
                # imaplib.response() consumes SELECT response codes. Refresh them
                # for the independent reply cursor after the opt-out reader.
                status, _ = mail.select(p['folder'],readonly=True)
                if status != 'OK': raise intake()._MailboxReadError('mailbox_selection_failed')
                result = sync_mailbox(mail,p,stop=stop)
                result['opt_outs_processed'] = optouts['email_opt_outs_processed']
                if not optouts['success']: result['opt_out_warning'] = optouts['status']
    except PrivacyCheckUnavailable:
        result = {'status': 'privacy_unavailable'}
    except imaplib.IMAP4.error:
        result = {'status': 'imap_auth_or_protocol_failed'}
    except Exception:
        result = {'status': 'imap_connection_failed'}
    with delivery.workflow().connect() as db:
        db.execute('UPDATE recdebut_reply_connector SET succeeded_at=CASE WHEN ? THEN ? ELSE succeeded_at END,status=?,details=? WHERE id=1',
                   (result['status']=='scanned',delivery.workflow().now(),result['status'],json.dumps(result)))
    return result


async def poll_loop():
    """Owned by lifespan; explicit reply-only flag, 60-second bounded polls."""
    stop = threading.Event()
    task = None
    failures, binding = 0, ''
    try:
        while True:
            p = profile()
            if p['digest'] != binding: failures, binding = 0, p['digest']
            if p['enabled'] and failures < 2:
                task = asyncio.create_task(asyncio.to_thread(run_once, stop))
                try:
                    result = await asyncio.shield(task)
                except Exception:
                    result = {'status':'worker_failed'}
                    try:
                        with delivery.workflow().connect() as db:
                            schema(db)
                            db.execute("INSERT INTO recdebut_reply_connector VALUES(1,?,'','worker_failed','{}') ON CONFLICT(id) DO UPDATE SET attempted_at=excluded.attempted_at,status='worker_failed'",(delivery.workflow().now(),))
                    except sqlite3.Error:
                        pass  # Dashboard detects a stale connector if its ledger is unavailable.
                failures = 0 if result['status'] in ('scanned','mailbox_busy') else failures + 1
                if failures == 2:
                    try:
                        with delivery.workflow().connect() as db:
                            schema(db)
                            db.execute("UPDATE recdebut_reply_connector SET status='paused_after_repeated_errors' WHERE id=1")
                    except sqlite3.Error:
                        pass
            await asyncio.sleep(60)
    finally:
        stop.set()
        if task is not None and not task.done():
            await asyncio.shield(task)  # Revoke submission, then join the bounded worker.


@router.get('/email/live')
def live(response: Response):
    """Authenticated local ledger snapshot. No network calls or schema changes."""
    response.headers['Cache-Control'] = 'no-store'
    p = profile()
    with delivery.workflow().connect() as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def counts(table,where='',args=()):
            return {r[0]:r[1] for r in db.execute('SELECT state,COUNT(*) FROM '+table+where+' GROUP BY state',args)} if table in tables else {}
        primary = counts('recdebut_send_attempts'," WHERE plan_id IN (SELECT id FROM recdebut_send_plans WHERE json_extract(payload,'$.channel')='email')")
        copies = counts('recdebut_email_staff_copies')
        replies = counts('recdebut_reply_copies')
        connector = dict(db.execute('SELECT * FROM recdebut_reply_connector WHERE id=1').fetchone() or {}) if 'recdebut_reply_connector' in tables else {}
        if connector: connector['details'] = json.loads(connector['details'])
        missing = db.execute("SELECT COUNT(*) FROM recdebut_send_attempts a JOIN recdebut_send_plans p ON p.id=a.plan_id LEFT JOIN recdebut_email_staff_copies c ON c.dedup_key=a.dedup_key WHERE a.state='ACCEPTED' AND json_extract(p.payload,'$.channel')='email' AND c.dedup_key IS NULL").fetchone()[0] if 'recdebut_send_attempts' in tables else 0
        events = []
        for table,category in [('recdebut_reply_copies','reply copy'),('recdebut_email_staff_copies','outgoing copy'),('recdebut_send_attempts','campaign attempt')]:
            if table not in tables: continue
            where = " WHERE plan_id IN (SELECT id FROM recdebut_send_plans WHERE json_extract(payload,'$.channel')='email')" if table=='recdebut_send_attempts' else ''
            events += [{'category':category,'state':r['state'],'updated_at':r['updated_at'], 'code':r['code'] if 'code' in r.keys() else ''}
                       for r in db.execute('SELECT * FROM '+table+where+' ORDER BY updated_at DESC LIMIT 30')]
        traffic = db.execute('SELECT COALESCE(SUM(request_count),0) FROM recdebut_campaign_link_counts').fetchone()[0] if 'recdebut_campaign_link_counts' in tables else 0
        suppressed = db.execute('SELECT COUNT(*) FROM recdebut_suppressions WHERE destination LIKE ?',('%@%',)).fetchone()[0]
        legacy_columns = {r[1] for r in db.execute('PRAGMA table_info(rec_debut_athletes)')}
        legacy = {str(r[0] or 'UNRECORDED'):r[1] for r in db.execute('SELECT email_status,COUNT(*) FROM rec_debut_athletes GROUP BY email_status')} if 'email_status' in legacy_columns else {}
        drafts = []
        for row in db.execute("SELECT * FROM recdebut_workflow WHERE kind='draft' AND json_extract(payload,'$.channel')='email'"):
            preview = delivery.workflow().draft_preview(db,row)
            drafts.append({'id':row['id'],'audience':len(preview['audience']),
                           'eligible':sum(not a['reasons'] for a in preview['audience']),
                           'blockers':sorted({r for a in preview['audience'] for r in a['reasons']})})
    events.sort(key=lambda e:e['updated_at'],reverse=True)
    return {'observed_at':delivery.workflow().now(),'sending_enabled':delivery.outbound_messaging_enabled('recdebut'),
            'sender':ACCOUNT,'copy_to':STAFF,'sender_blockers':p['smtp']['blockers'],
            'primary':primary,'outgoing_copies':copies,'outgoing_copies_missing':missing,
            'reply_copies':replies,'reply_forwarding':{'enabled':p['enabled'],'configured':p['configured'],**connector},
            'events':events[:30],'drafts':drafts,'tracked_link_requests':traffic,'email_suppressions':suppressed,
            'legacy_email_status':legacy,
            'delivery_confirmation':None,'open_tracking':None,
            'notice':'SMTP accepted is not delivery confirmation. Link requests can include security scanners. Earlier mail without recorded campaign Message-IDs is not automatically forwarded.'}
