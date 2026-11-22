"""Durable provider facts, separate from legacy REAL ledgers and key provisioning.

Construction and reads never create a database. Only authenticated ingestion or
server checkout preparation initializes additive tables in the commercial store.
No exchange, entitlement, notification or order-dispatch capability is present.
"""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

MAX_MINOR = 9_000_000_000_000_000_000


class PaymentConflict(ValueError):
    pass


def minor(value):
    if type(value) is not int or not 0 <= value <= MAX_MINOR:
        raise ValueError('Invalid integer minor units')
    return value


def usd_minor(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d{0,16})\.\d{2}', value):
        raise ValueError('Use an exact nonnegative USD decimal string with two places')
    whole, cents = value.split('.')
    return minor(int(whole) * 100 + int(cents))


def money(value):
    if value is None:
        return None
    minor(value)
    return f'{value // 100}.{value % 100:02d}'


class ReceiptStore:
    def __init__(self, path):
        self.path = Path(path)

    def _open(self, write=False):
        if not write and not self.path.is_file():
            return None
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path) if write else self.path.resolve().as_uri()+'?mode=ro',
                               uri=not write, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA busy_timeout=5000')
        if write:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=FULL')
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS payment_intents_v1(
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, tier TEXT NOT NULL,
                    gross_minor INTEGER NOT NULL, provider TEXT NOT NULL, account TEXT NOT NULL,
                    mode TEXT NOT NULL, request_key TEXT NOT NULL, reference TEXT,
                    created_at INTEGER NOT NULL, UNIQUE(owner,provider,account,mode,request_key),
                    UNIQUE(provider,account,mode,reference));
                CREATE TABLE IF NOT EXISTS payment_events_v1(
                    provider TEXT,account TEXT,mode TEXT,event_id TEXT,digest TEXT NOT NULL,
                    payment_id TEXT NOT NULL,kind TEXT NOT NULL,received_at INTEGER NOT NULL,
                    PRIMARY KEY(provider,account,mode,event_id));
                CREATE TABLE IF NOT EXISTS payment_receipts_v1(
                    id INTEGER PRIMARY KEY,provider TEXT,account TEXT,mode TEXT,event_id TEXT,
                    payment_id TEXT,reference TEXT,intent_id TEXT,currency TEXT,
                    gross_minor INTEGER,fee_minor INTEGER,net_minor INTEGER,received_at INTEGER,
                    UNIQUE(provider,account,mode,payment_id));
                CREATE TABLE IF NOT EXISTS payment_holds_v1(
                    provider TEXT,account TEXT,mode TEXT,payment_id TEXT,reason TEXT,event_id TEXT,
                    UNIQUE(provider,account,mode,payment_id,reason,event_id));
                CREATE TRIGGER IF NOT EXISTS receipt_no_update BEFORE UPDATE ON payment_receipts_v1
                    BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
                CREATE TRIGGER IF NOT EXISTS receipt_no_delete BEFORE DELETE ON payment_receipts_v1
                    BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
                CREATE TRIGGER IF NOT EXISTS event_no_update BEFORE UPDATE ON payment_events_v1
                    BEGIN SELECT RAISE(ABORT,'immutable event'); END;
                CREATE TRIGGER IF NOT EXISTS event_no_delete BEFORE DELETE ON payment_events_v1
                    BEGIN SELECT RAISE(ABORT,'immutable event'); END;
            ''')
        return conn

    def prepare_intent(self, owner, tier, gross_minor, provider, account, mode, request_key):
        minor(gross_minor)
        if not owner or not account or provider not in ('stripe','paypal') or mode not in ('live','test'):
            raise ValueError('Invalid checkout scope')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',request_key):
            raise ValueError('Invalid idempotency key')
        scope = (owner,provider,account,mode,request_key)
        ident = hashlib.sha256(json.dumps(scope,separators=(',',':')).encode()).hexdigest()
        conn=self._open(True)
        try:
            conn.execute('BEGIN IMMEDIATE')
            old=conn.execute('SELECT * FROM payment_intents_v1 WHERE id=?',(ident,)).fetchone()
            if old and (old['tier'] != tier or old['gross_minor'] != gross_minor):
                raise PaymentConflict('Idempotency key reused with a changed checkout')
            if not old:
                conn.execute('INSERT INTO payment_intents_v1 VALUES(?,?,?,?,?,?,?,?,NULL,?)',
                             (ident,owner,tier,gross_minor,provider,account,mode,request_key,int(time.time())))
            conn.commit()
            return dict(conn.execute('SELECT * FROM payment_intents_v1 WHERE id=?',(ident,)).fetchone())
        finally:
            conn.close()

    def bind_reference(self, intent_id, reference):
        if not isinstance(reference,str) or not 1 <= len(reference) <= 255:
            raise ValueError('Invalid provider reference')
        conn=self._open(True)
        try:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute('SELECT reference FROM payment_intents_v1 WHERE id=?',(intent_id,)).fetchone()
            if not row or (row['reference'] and row['reference'] != reference):
                raise PaymentConflict('Provider reference is immutable')
            conn.execute('UPDATE payment_intents_v1 SET reference=? WHERE id=?',(reference,intent_id))
            conn.commit()
        finally:
            conn.close()

    def ingest(self, *, provider,account,mode,event_id,digest,kind,payment_id,reference,intent_id,
               currency,gross_minor,fee_minor=None,net_minor=None):
        if provider not in ('stripe','paypal') or mode not in ('live','test') or kind not in ('capture','reversal'):
            raise ValueError('Invalid provider fact')
        for text in (account,event_id,payment_id):
            if not isinstance(text,str) or not 1 <= len(text) <= 255:
                raise ValueError('Missing provider identity')
        for text in (reference,intent_id):
            if not isinstance(text,str) or len(text)>255:raise ValueError('Invalid checkout reference')
        if not re.fullmatch('[a-f0-9]{64}',digest) or not re.fullmatch('[A-Z]{3}',currency):
            raise ValueError('Invalid receipt digest or currency')
        minor(gross_minor)
        if (fee_minor is None) != (net_minor is None):
            raise ValueError('Incomplete fee evidence')
        if fee_minor is not None and minor(fee_minor)+minor(net_minor) != gross_minor:
            raise ValueError('Gross does not reconcile to fee plus net')
        scope=(provider,account,mode)
        conn=self._open(True)
        try:
            conn.execute('BEGIN IMMEDIATE')
            prior=conn.execute('SELECT * FROM payment_events_v1 WHERE provider=? AND account=? AND mode=? AND event_id=?',(*scope,event_id)).fetchone()
            if prior:
                result='duplicate' if prior['digest']==digest else 'conflict'
                if result=='conflict':
                    # Hold both identities when a previously seen event changes payload.
                    for pid in {prior['payment_id'],payment_id}:
                        conn.execute('INSERT OR IGNORE INTO payment_holds_v1 VALUES(?,?,?,?,?,?)',(*scope,pid,'event_conflict',event_id))
            else:
                conn.execute('INSERT INTO payment_events_v1 VALUES(?,?,?,?,?,?,?,?)',(*scope,event_id,digest,payment_id,kind,int(time.time())))
                result='recorded'
                if kind=='reversal':
                    conn.execute('INSERT OR IGNORE INTO payment_holds_v1 VALUES(?,?,?,?,?,?)',(*scope,payment_id,'provider_reversal',event_id))
                else:
                    old=conn.execute('SELECT * FROM payment_receipts_v1 WHERE provider=? AND account=? AND mode=? AND payment_id=?',(*scope,payment_id)).fetchone()
                    facts=(reference,intent_id,currency,gross_minor,fee_minor,net_minor)
                    if old:
                        same=tuple(old[k] for k in ('reference','intent_id','currency','gross_minor','fee_minor','net_minor'))==facts
                        result='duplicate_payment' if same else 'conflict'
                        if not same:
                            conn.execute('INSERT OR IGNORE INTO payment_holds_v1 VALUES(?,?,?,?,?,?)',(*scope,payment_id,'payment_conflict',event_id))
                    else:
                        conn.execute('INSERT INTO payment_receipts_v1(provider,account,mode,event_id,payment_id,reference,intent_id,currency,gross_minor,fee_minor,net_minor,received_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                                     (*scope,event_id,payment_id,*facts,int(time.time())))
            conn.commit()
            return {'status':result,'fulfillment':'held_pending_reconciliation'}
        finally:
            conn.close()

    def receipts(self, owner):
        conn=self._open()
        if conn is None:
            return []
        try:
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'payment_receipts_v1','payment_intents_v1','payment_holds_v1'} <= tables:
                return []
            rows=conn.execute('''SELECT r.*,EXISTS(SELECT 1 FROM payment_holds_v1 h WHERE
                h.provider=r.provider AND h.account=r.account AND h.mode=r.mode AND h.payment_id=r.payment_id) AS held
                FROM payment_receipts_v1 r JOIN payment_intents_v1 i ON r.intent_id=i.id
                AND r.provider=i.provider AND r.account=i.account AND r.mode=i.mode
                AND r.reference=i.reference AND r.gross_minor=i.gross_minor AND r.currency='USD'
                WHERE i.owner=? ORDER BY r.id DESC''',(owner,)).fetchall()
            return [dict(id=r['id'], provider=r['provider'], mode=r['mode'],currency=r['currency'],
                         payment_id=r['payment_id'], gross=money(r['gross_minor']),fee=money(r['fee_minor']),net=money(r['net_minor']),
                         evidence_digest=hashlib.sha256(json.dumps(dict(r),sort_keys=True).encode()).hexdigest(),
                         status='review_required' if r['held'] else ('fee_evidence_missing' if r['fee_minor'] is None else 'ready_to_match')) for r in rows]
        finally:
            conn.close()


def get_receipt_store():
    return ReceiptStore(Path(__file__).resolve().parents[1]/'commercial_gateway'/'commercial_usage.db')
