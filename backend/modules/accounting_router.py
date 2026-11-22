"""Owner-scoped manual records and explicit provider-receipt matching.

Legacy unowned REAL tables are preserved, never adopted or used as evidence.
There are no schema writes on import or read, and no trading/provider dispatch.
"""
import csv
import hashlib
from datetime import date as Date
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import io
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from core.payment_receipts import get_receipt_store, money, usd_minor
from security.financial_auth import require_financial_owner

router=APIRouter(prefix='/api/accounting',tags=['Accounting & Tax Suite'],dependencies=[Depends(require_financial_owner)])
BACKEND=Path(__file__).resolve().parents[1]
DB_PATH=str(BACKEND/'aibs_master.db' if (BACKEND/'aibs_master.db').exists() else BACKEND/'stehouwer_accounting.db')


def get_db(write=False):
    path=Path(DB_PATH)
    if not write and not path.exists(): return None
    conn=sqlite3.connect(str(path) if write else path.resolve().as_uri()+'?mode=ro',uri=not write,timeout=5,isolation_level=None)
    conn.row_factory=sqlite3.Row
    if write:
        conn.execute('PRAGMA journal_mode=WAL');conn.execute('PRAGMA synchronous=FULL')
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS accounting_owned_records_v1(
                id INTEGER PRIMARY KEY AUTOINCREMENT,owner TEXT NOT NULL,kind TEXT NOT NULL,
                payload TEXT NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS accounting_owner_idx_v1 ON accounting_owned_records_v1(owner,kind,id);
            CREATE TABLE IF NOT EXISTS accounting_operations_v1(
                owner TEXT NOT NULL,request_key TEXT NOT NULL,digest TEXT NOT NULL,result TEXT NOT NULL,
                PRIMARY KEY(owner,request_key));
            CREATE TABLE IF NOT EXISTS accounting_receipt_matches_v1(
                receipt_id INTEGER PRIMARY KEY,owner TEXT NOT NULL,entry_id INTEGER UNIQUE NOT NULL,
                fee_entry_id INTEGER UNIQUE,evidence_digest TEXT NOT NULL,matched_at INTEGER NOT NULL);
            CREATE TRIGGER IF NOT EXISTS receipt_match_no_update BEFORE UPDATE ON accounting_receipt_matches_v1
                BEGIN SELECT RAISE(ABORT,'immutable receipt match'); END;
            CREATE TRIGGER IF NOT EXISTS receipt_match_no_delete BEFORE DELETE ON accounting_receipt_matches_v1
                BEGIN SELECT RAISE(ABORT,'immutable receipt match'); END;
        ''')
    return conn


def has_table(conn,name):
    return conn is not None and conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None


def records(owner,kind):
    conn=get_db()
    if conn is None:return []
    try:
        if not has_table(conn,'accounting_owned_records_v1'):return []
        return [dict(json.loads(r['payload']),id=r['id'],verification='manual_unreconciled') for r in
                conn.execute('SELECT id,payload FROM accounting_owned_records_v1 WHERE owner=? AND kind=? ORDER BY id DESC',(owner,kind))]
    finally:conn.close()


class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid')


class EntrySchema(StrictModel):
    id:int | None=Field(default=None,gt=0)
    date:str
    category:str=Field(min_length=1,max_length=120)
    description:str=Field(min_length=1,max_length=2000)
    entry_type:Literal['income','expense']
    amount:str
    currency:Literal['USD']='USD'
    is_tax_deductible:bool=False
    schedule_c_code:str=Field(default='Other',max_length=120)
    receipt_note:str=Field(default='',max_length=2000)

    @field_validator('amount')
    @classmethod
    def amount_exact(cls,value):
        usd_minor(value);return value

    @field_validator('date')
    @classmethod
    def date_valid(cls,value):
        if Date.fromisoformat(value).isoformat()!=value:raise ValueError('Use YYYY-MM-DD')
        return value


class CryptoTransferSchema(StrictModel):
    id:int | None=Field(default=None,gt=0)
    date:str
    source_account:str=Field(min_length=1,max_length=160)
    dest_account:str=Field(min_length=1,max_length=160)
    asset:str=Field(min_length=1,max_length=20)
    amount:str
    usd_price_at_transfer:str
    usd_total_value:str
    fee_amount:str='0'
    fee_asset:str='USD'
    tx_hash:str=Field(default='',max_length=255)
    category:Literal['mining_income','wallet_transfer','exchange_swap','direct_deposit_ach','network_fee']='mining_income'
    notes:str=Field(default='',max_length=2000)

    @field_validator('date')
    @classmethod
    def date_valid(cls,value):return EntrySchema.date_valid(value)

    @field_validator('amount','usd_price_at_transfer','fee_amount')
    @classmethod
    def decimal_exact(cls,value):
        if not re.fullmatch(r'(0|[1-9]\d{0,13})(\.\d{1,18})?',value):raise ValueError('Use a nonnegative exact decimal string')
        return value

    @field_validator('usd_total_value')
    @classmethod
    def total_exact(cls,value):usd_minor(value);return value


def locked(conn,owner,entry_id):
    return conn.execute('SELECT 1 FROM accounting_receipt_matches_v1 WHERE owner=? AND (entry_id=? OR fee_entry_id=?)',(owner,entry_id,entry_id)).fetchone()


def save(owner,kind,entry,request_key=None):
    payload=entry.model_dump(exclude={'id'}); now=int(time.time());conn=get_db(True)
    try:
        conn.execute('BEGIN IMMEDIATE')
        digest=hashlib.sha256(json.dumps([kind,entry.id,payload],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if request_key is not None:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',request_key):raise HTTPException(422,'Invalid Idempotency-Key')
            prior=conn.execute('SELECT digest,result FROM accounting_operations_v1 WHERE owner=? AND request_key=?',(owner,request_key)).fetchone()
            if prior:
                if prior['digest']!=digest:raise HTTPException(409,'Idempotency-Key reused for a different update')
                return json.loads(prior['result'])
        if entry.id:
            if locked(conn,owner,entry.id):raise HTTPException(409,'Matched records are immutable; corrections require new evidence')
            result=conn.execute('UPDATE accounting_owned_records_v1 SET payload=?,updated_at=? WHERE id=? AND owner=? AND kind=?',
                (json.dumps(payload),now,entry.id,owner,kind))
            if not result.rowcount:raise HTTPException(404,'Record not found')
            ident=entry.id
        else:
            ident=conn.execute('INSERT INTO accounting_owned_records_v1(owner,kind,payload,created_at,updated_at) VALUES(?,?,?,?,?)',
                (owner,kind,json.dumps(payload),now,now)).lastrowid
        result={'status':'success','id':ident,'verification':'manual_unreconciled'}
        if request_key is not None:
            conn.execute('INSERT INTO accounting_operations_v1 VALUES(?,?,?,?)',(owner,request_key,digest,json.dumps(result)))
        conn.commit();return result
    finally:conn.close()


def delete(owner,kind,ident):
    conn=get_db()
    if conn is None:raise HTTPException(404,'Record not found')
    exists=has_table(conn,'accounting_owned_records_v1');conn.close()
    if not exists:raise HTTPException(404,'Record not found')
    conn=get_db(True)
    try:
        conn.execute('BEGIN IMMEDIATE')
        if locked(conn,owner,ident):raise HTTPException(409,'Matched records are immutable')
        result=conn.execute('DELETE FROM accounting_owned_records_v1 WHERE owner=? AND kind=? AND id=?',(owner,kind,ident))
        if not result.rowcount:raise HTTPException(404,'Record not found')
        conn.commit();return {'status':'success'}
    finally:conn.close()


@router.get('/entries')
def get_entries(owner=Depends(require_financial_owner)):
    rows=records(owner,'entry')
    return {'status':'success','count':len(rows),'entries':rows,'coverage':'manual_only_legacy_unowned_excluded'}


@router.post('/entry')
def save_entry(entry:EntrySchema,owner=Depends(require_financial_owner),request_key:str | None=Header(default=None,alias='Idempotency-Key')):return save(owner,'entry',entry,request_key)


@router.delete('/entry/{entry_id}')
def delete_entry(entry_id:int,owner=Depends(require_financial_owner)):return delete(owner,'entry',entry_id)


@router.get('/tax-summary')
def get_tax_summary(owner=Depends(require_financial_owner)):
    return {'status':'unavailable','verification':'not_verified','reason':'Reconciled coverage and validated entity, year and jurisdiction rules are unavailable.'}


class ChatPromptSchema(StrictModel):
    message:str=Field(min_length=1,max_length=4000)


@router.post('/chat-assistant')
def chat_assistant(payload:ChatPromptSchema,owner=Depends(require_financial_owner),request_key:str | None=Header(default=None,alias='Idempotency-Key')):
    msg=payload.message; lower=msg.lower();reply='Manual assistant output is unverified. Tax results and payment confirmation are unavailable.'
    if re.search(r'\b(log|add)\b',lower):
        amount=re.search(r'(?<![\w.\-])\$?((?:0|[1-9]\d{0,13})(?:\.\d{1,2})?)(?![\w.])',msg)
        if amount:
            with localcontext() as ctx:
                ctx.prec=40; value=f'{Decimal(amount[1]):.2f}'
            kind='expense' if any(w in lower for w in ('expense','cost','spent')) else 'income'
            saved=save(owner,'entry',EntrySchema(date=Date.today().isoformat(),category='Manual assistant entry',description=msg,entry_type=kind,amount=value,
                       receipt_note='Manual command; no receipt verification'),request_key)
            reply=f'Manual {kind} of ${value} recorded (row {saved["id"]}). '+reply
    return {'status':'success','reply':reply,'verification':'manual_unreconciled'}


@router.get('/crypto-transfers')
def get_crypto_transfers(owner=Depends(require_financial_owner)):
    rows=records(owner,'crypto')
    return {'status':'success','count':len(rows),'transfers':rows,'verification':'manual_unreconciled',
            'metrics':dict.fromkeys(('total_transferred_usd','mined_income_usd','ach_direct_deposits_usd','total_fees_usd'),None),
            'reason':'Manual records do not verify wallet linkage, USD fees, transfers or tax treatment.'}


@router.post('/crypto-transfers')
def save_crypto_transfer(transfer:CryptoTransferSchema,owner=Depends(require_financial_owner),request_key:str | None=Header(default=None,alias='Idempotency-Key')):
    with localcontext() as ctx:
        ctx.prec=80
        total=(Decimal(transfer.amount)*Decimal(transfer.usd_price_at_transfer)).quantize(Decimal('.01'),rounding=ROUND_HALF_EVEN)
    if f'{total:.2f}'!=transfer.usd_total_value:raise HTTPException(422,'Manual USD total must equal quantity times price, rounded half even to cents')
    return save(owner,'crypto',transfer,request_key)


@router.delete('/crypto-transfers/{transfer_id}')
def delete_crypto_transfer(transfer_id:int,owner=Depends(require_financial_owner)):return delete(owner,'crypto',transfer_id)


@router.get('/crypto-transfers/export-csv')
def export_crypto_transfers_csv(owner=Depends(require_financial_owner)):
    output=io.StringIO();writer=csv.writer(output)
    columns=('id','date','source_account','dest_account','asset','amount','usd_price_at_transfer','usd_total_value','fee_amount','fee_asset','category','tx_hash','notes','verification')
    writer.writerow(columns)
    for row in records(owner,'crypto'):
        writer.writerow([("'"+str(row.get(k,''))) if str(row.get(k,'')).startswith(('=','+','-','@','\t','\r','\n')) else row.get(k,'') for k in columns])
    return Response(output.getvalue(),media_type='text/csv',headers={'Cache-Control':'private, no-store','Content-Disposition':'attachment; filename=AI_BS_Manual_Transfers.csv'})


@router.get('/receipts')
def get_receipts(owner=Depends(require_financial_owner)):
    rows=get_receipt_store().receipts(owner);conn=get_db()
    try:
        matches={r['receipt_id']:dict(r) for r in conn.execute('SELECT * FROM accounting_receipt_matches_v1 WHERE owner=?',(owner,))} if has_table(conn,'accounting_receipt_matches_v1') else {}
        for row in rows:
            match=matches.get(row['id'])
            if match:
                if match['evidence_digest']!=row['evidence_digest']:
                    row['status']='review_required'
                    row['reason']='Stored match evidence differs from current provider facts'
                    continue
                row['status']='matched_test_only' if row['status']=='ready_to_match' and row['mode']=='test' else ('matched_receipt' if row['status']=='ready_to_match' else row['status'])
                row['entry_id']=match['entry_id'];row['fee_entry_id']=match['fee_entry_id']
        return {'status':'success','receipts':rows,'coverage':'unconfirmed','economic_summary_eligible':False}
    finally:
        if conn:conn.close()


class ReceiptMatchSchema(StrictModel):
    entry_id:int=Field(gt=0)
    fee_entry_id:int | None=Field(default=None,gt=0)


@router.post('/receipts/{receipt_id}/reconcile')
def reconcile_receipt(receipt_id:int,payload:ReceiptMatchSchema,owner=Depends(require_financial_owner)):
    receipt=next((r for r in get_receipt_store().receipts(owner) if r['id']==receipt_id),None)
    if receipt is None:raise HTTPException(404,'Receipt not found')
    if receipt['status']!='ready_to_match':raise HTTPException(409,'Receipt requires complete fee evidence and no reversal/conflict hold')
    conn=get_db(True)
    try:
        conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT * FROM accounting_receipt_matches_v1 WHERE receipt_id=?',(receipt_id,)).fetchone()
        if old:
            if old['owner']!=owner:raise HTTPException(404,'Receipt not found')
            if old['evidence_digest']!=receipt['evidence_digest']:raise HTTPException(409,'Stored match evidence differs; reconciliation is held')
            if (old['entry_id'],old['fee_entry_id'])!=(payload.entry_id,payload.fee_entry_id):raise HTTPException(409,'Receipt already matched')
            latest=next((r for r in get_receipt_store().receipts(owner) if r['id']==receipt_id),None)
            if not latest or latest['status']!='ready_to_match' or latest['evidence_digest']!=receipt['evidence_digest']:
                raise HTTPException(409,'Receipt changed during matching; historical match remains held for review')
            return {'status':'success','verification':'matched_test_only' if receipt['mode']=='test' else 'matched_receipt','coverage':'unconfirmed'}
        expected=[(payload.entry_id,'income',receipt['gross'])]
        if usd_minor(receipt['fee'])>0:
            if payload.fee_entry_id is None:raise HTTPException(409,'A separate exact fee expense is required')
            expected.append((payload.fee_entry_id,'expense',receipt['fee']))
        elif payload.fee_entry_id is not None:raise HTTPException(409,'Zero fee requires no fee expense')
        for ident,kind,amount in expected:
            row=conn.execute("SELECT payload FROM accounting_owned_records_v1 WHERE owner=? AND kind='entry' AND id=?",(owner,ident)).fetchone()
            if not row:raise HTTPException(404,'Manual record not found')
            record=json.loads(row['payload'])
            if record['entry_type']!=kind or record['amount']!=amount or record['currency']!=receipt['currency'] or locked(conn,owner,ident):
                raise HTTPException(409,'Receipt amount, currency, direction or prior match does not agree')
        conn.execute('INSERT INTO accounting_receipt_matches_v1 VALUES(?,?,?,?,?,?)',(receipt_id,owner,payload.entry_id,payload.fee_entry_id,receipt['evidence_digest'],int(time.time())))
        conn.commit()
        latest=next((r for r in get_receipt_store().receipts(owner) if r['id']==receipt_id),None)
        if not latest or latest['status']!='ready_to_match' or latest['evidence_digest']!=receipt['evidence_digest']:
            raise HTTPException(409,'Receipt changed during matching; reconciliation is held for review')
        return {'status':'success','verification':'matched_test_only' if receipt['mode']=='test' else 'matched_receipt','coverage':'unconfirmed'}
    except sqlite3.IntegrityError:raise HTTPException(409,'Conflicting receipt match') from None
    finally:conn.close()
