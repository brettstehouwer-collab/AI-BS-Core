"""Owner isolation and receipt reconciliation, exclusively temporary offline stores."""
from pathlib import Path
from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from security import financial_auth
from core.payment_receipts import ReceiptStore
from modules import accounting_router as accounting

class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='aibs-offline-accounting-'); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'accounting.sqlite'
        self.store=ReceiptStore(Path(self.tmp.name)/'receipts.sqlite')
        for p in [patch.object(accounting,'DB_PATH',str(self.path)),
                  patch.object(accounting,'get_receipt_store',return_value=self.store),
                  patch.object(financial_auth,'get_admin_principal',side_effect=lambda key='',authorization='': {'Bearer a':'owner-a','Bearer b':'owner-b'}.get(authorization))]:
            p.start(); self.addCleanup(p.stop)
        app=FastAPI();app.include_router(accounting.router);self.client=TestClient(app);self.addCleanup(self.client.close)
        self.a={'Authorization':'Bearer a'}; self.b={'Authorization':'Bearer b'}

    def entry(self,amount='4.99',**kw):
        value=dict(date='2026-10-30',category='manual',description='offline fixture',entry_type='income',amount=amount)
        value.update(kw)
        return self.client.post('/api/accounting/entry',headers=self.a,json=value)

    def test_every_route_requires_verified_identity_before_store_access(self):
        routes=[('GET','/entries'),('POST','/entry'),('DELETE','/entry/1'),('GET','/tax-summary'),
                ('POST','/chat-assistant'),('GET','/crypto-transfers'),('POST','/crypto-transfers'),
                ('DELETE','/crypto-transfers/1'),('GET','/crypto-transfers/export-csv'),('GET','/receipts')]
        for method,path in routes:
            for headers in [{},{'x-client-id':'owner-a'}]:
                response=self.client.request(method,'/api/accounting'+path,headers=headers,json={})
                self.assertEqual(response.status_code,403,(path,response.text))
        self.assertFalse(self.path.exists())

    def test_owner_isolation_and_guessed_ids_are_404(self):
        result=self.entry();self.assertEqual(result.status_code,200,result.text); entry_id=result.json()['id']
        self.assertEqual(self.client.get('/api/accounting/entries',headers=self.b).json()['entries'],[])
        self.assertEqual(self.client.delete(f'/api/accounting/entry/{entry_id}',headers=self.b).status_code,404)
        payload=dict(id=entry_id,date='2026-10-30',category='x',description='x',entry_type='income',amount='1.00')
        self.assertEqual(self.client.post('/api/accounting/entry',headers=self.b,json=payload).status_code,404)
        response=self.client.get('/api/accounting/entries',headers=self.a)
        self.assertEqual(response.json()['entries'][0]['amount'],'4.99')
        self.assertIn('no-store',response.headers['cache-control'])

    def test_legacy_unowned_rows_are_preserved_and_excluded(self):
        with closing(sqlite3.connect(self.path)) as c:
            c.execute('CREATE TABLE accounting_entries(id INTEGER, description TEXT, amount REAL)')
            c.execute("INSERT INTO accounting_entries VALUES(1,'legacy private fixture',12.34)")
            c.commit()
        self.assertEqual(self.client.get('/api/accounting/entries',headers=self.a).json()['entries'],[])
        self.assertEqual(self.client.delete('/api/accounting/entry/1',headers=self.a).status_code,404)
        with closing(sqlite3.connect(self.path)) as c:self.assertEqual(c.execute('SELECT description FROM accounting_entries').fetchone()[0],'legacy private fixture')

    def test_exact_amounts_reject_floats_negative_nonfinite_and_fractional_cent(self):
        for amount in [0.1,'NaN','Infinity','-1.00','1.001','1e2',True]:
            self.assertEqual(self.entry(amount).status_code,422,repr(amount))
        self.assertEqual(self.entry('90071992547409.91').status_code,200)

    def test_tax_summary_and_chat_do_not_manufacture_tax_evidence(self):
        summary=self.client.get('/api/accounting/tax-summary',headers=self.a).json()
        self.assertEqual(summary['status'],'unavailable')

        r=self.client.post('/api/accounting/chat-assistant',headers=self.a,json={'message':'log expense $0.10 hardware'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertNotIn('4.25%',r.text)
        rows=self.client.get('/api/accounting/entries',headers=self.a).json()['entries']
        self.assertEqual(rows[0]['amount'],'0.10')
        self.assertEqual(self.client.get('/api/accounting/entries',headers=self.b).json()['entries'],[])


    def test_mutation_retry_is_durable_and_owner_scoped(self):
        body=dict(date='2026-10-30',category='manual',description='retry fixture',entry_type='income',amount='0.10')
        headers=dict(self.a, **{'Idempotency-Key':'offline-retry'})
        first=self.client.post('/api/accounting/entry',headers=headers,json=body)
        second=self.client.post('/api/accounting/entry',headers=headers,json=body)
        self.assertEqual(first.json(),second.json())
        self.assertEqual(len(self.client.get('/api/accounting/entries',headers=self.a).json()['entries']),1)
        self.assertEqual(self.client.post('/api/accounting/entry',headers=headers,json=dict(body,amount='0.20')).status_code,409)
        other=self.client.post('/api/accounting/entry',headers=dict(self.b, **{'Idempotency-Key':'offline-retry'}),json=body)
        self.assertNotEqual(first.json()['id'],other.json()['id'])

    def test_restored_receipt_id_does_not_reuse_old_match(self):
        intent=self.store.prepare_intent('owner-a','day_pass',499,'stripe','acct_fixture','test','restore-key')
        self.store.bind_reference(intent['id'],'cs_fixture')
        facts=dict(provider='stripe',account='acct_fixture',mode='test',event_id='evt',digest='a'*64,kind='capture',
            payment_id='pi_old',reference='cs_fixture',intent_id=intent['id'],currency='USD',gross_minor=499,fee_minor=0,net_minor=499)
        self.store.ingest(**facts)
        ident=self.entry().json()['id']; url='/api/accounting/receipts/1/reconcile'
        self.assertEqual(self.client.post(url,headers=self.a,json={'entry_id':ident}).status_code,200)
        replacement=ReceiptStore(Path(self.tmp.name)/'replaced.sqlite')
        new_intent=replacement.prepare_intent('owner-a','day_pass',499,'stripe','acct_fixture','test','new-restore-key')
        replacement.bind_reference(new_intent['id'],'cs_new')
        replacement.ingest(**dict(facts,event_id='evt_new',payment_id='pi_new',reference='cs_new',intent_id=new_intent['id']))
        with patch.object(accounting,'get_receipt_store',return_value=replacement):
            row=self.client.get('/api/accounting/receipts',headers=self.a).json()['receipts'][0]
            self.assertEqual(row['status'],'review_required')
            self.assertEqual(self.client.post(url,headers=self.a,json={'entry_id':ident}).status_code,409)

    def test_concurrent_reversal_during_match_retry_remains_held(self):
        intent=self.store.prepare_intent('owner-a','day_pass',499,'stripe','acct_fixture','test','race-key')
        self.store.bind_reference(intent['id'],'cs_race')
        facts=dict(provider='stripe',account='acct_fixture',mode='test',event_id='evt_race',digest='a'*64,kind='capture',
            payment_id='pi_race',reference='cs_race',intent_id=intent['id'],currency='USD',gross_minor=499,fee_minor=0,net_minor=499)
        self.store.ingest(**facts)
        ident=self.entry().json()['id'];url='/api/accounting/receipts/1/reconcile'
        self.assertEqual(self.client.post(url,headers=self.a,json={'entry_id':ident}).status_code,200)
        real=self.store.receipts;calls=0
        def receipts(owner):
            nonlocal calls
            snapshot=real(owner);calls+=1
            if calls==1:self.store.ingest(**dict(facts,event_id='evt_reversal',digest='b'*64,kind='reversal',fee_minor=None,net_minor=None))
            return snapshot
        with patch.object(self.store,'receipts',side_effect=receipts):
            self.assertEqual(self.client.post(url,headers=self.a,json={'entry_id':ident}).status_code,409)
        self.assertEqual(real('owner-a')[0]['status'],'review_required')

    def test_two_receipts_cannot_reuse_manual_rows_and_restart_preserves_lock(self):
        for count in [1,2]:
            intent=self.store.prepare_intent('owner-a','day_pass',499,'stripe','acct_fixture','test',f'shared-{count}')
            self.store.bind_reference(intent['id'],f'cs_shared_{count}')
            self.store.ingest(provider='stripe',account='acct_fixture',mode='test',event_id=f'evt_{count}',digest=str(count)*64,kind='capture',
                payment_id=f'pi_{count}',reference=f'cs_shared_{count}',intent_id=intent['id'],currency='USD',gross_minor=499,fee_minor=0,net_minor=499)
        ident=self.entry().json()['id']
        self.assertEqual(self.client.post('/api/accounting/receipts/1/reconcile',headers=self.a,json={'entry_id':ident}).status_code,200)
        self.assertEqual(self.client.post('/api/accounting/receipts/2/reconcile',headers=self.a,json={'entry_id':ident}).status_code,409)
        with patch.object(accounting,'get_receipt_store',return_value=ReceiptStore(self.store.path)):
            rows=self.client.get('/api/accounting/receipts',headers=self.a).json()['receipts']
            self.assertEqual([r['status'] for r in rows],['ready_to_match','matched_test_only'])
            self.assertEqual(self.client.delete(f'/api/accounting/entry/{ident}',headers=self.a).status_code,409)

    def test_failed_match_commit_rolls_back_and_does_not_lock_manual_record(self):
        intent=self.store.prepare_intent('owner-a','day_pass',499,'stripe','acct_fixture','test','rollback-key')
        self.store.bind_reference(intent['id'],'cs_rollback')
        self.store.ingest(provider='stripe',account='acct_fixture',mode='test',event_id='evt_rollback',digest='a'*64,kind='capture',
            payment_id='pi_rollback',reference='cs_rollback',intent_id=intent['id'],currency='USD',gross_minor=499,fee_minor=0,net_minor=499)
        ident=self.entry().json()['id']; real_get_db=accounting.get_db
        class BrokenCommit:
            def __init__(self,conn):self.conn=conn
            def __getattr__(self,name):return getattr(self.conn,name)
            def commit(self):raise sqlite3.OperationalError('offline commit failure')
        def db(write=False):
            conn=real_get_db(write)
            return BrokenCommit(conn) if write else conn
        with patch.object(accounting,'get_db',side_effect=db):
            with self.assertRaises(sqlite3.OperationalError):
                self.client.post('/api/accounting/receipts/1/reconcile',headers=self.a,json={'entry_id':ident})
        self.assertEqual(self.client.get('/api/accounting/receipts',headers=self.a).json()['receipts'][0]['status'],'ready_to_match')
        self.assertEqual(self.client.delete(f'/api/accounting/entry/{ident}',headers=self.a).status_code,200)

    def test_receipt_match_requires_owner_amount_fee_entries_and_locks_history(self):
        i=self.store.prepare_intent('owner-a','pass_1day',499,'stripe','acct_fixture','test','req')
        self.store.bind_reference(i['id'],'cs_fixture')
        self.store.ingest(provider='stripe',account='acct_fixture',mode='test',event_id='evt',digest='a'*64,kind='capture',
            payment_id='pi',reference='cs_fixture',intent_id=i['id'],currency='USD',gross_minor=499,fee_minor=19,net_minor=480)
        receipt=self.store.receipts('owner-a')[0]
        income=self.entry().json()['id'];fee=self.entry('0.19',entry_type='expense').json()['id']
        url='/api/accounting/receipts/'+str(receipt['id'])+'/reconcile'
        self.assertEqual(self.client.post(url,headers=self.b,json={'entry_id':income,'fee_entry_id':fee}).status_code,404)
        self.assertEqual(self.client.post(url,headers=self.a,json={'entry_id':income}).status_code,409)
        r=self.client.post(url,headers=self.a,json={'entry_id':income,'fee_entry_id':fee})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.post(url,headers=self.a,json={'entry_id':income,'fee_entry_id':fee}).status_code,200)
        self.assertEqual(self.client.delete('/api/accounting/entry/'+str(income),headers=self.a).status_code,409)
        self.store.ingest(provider='stripe',account='acct_fixture',mode='test',event_id='refund',digest='b'*64,kind='reversal',
            payment_id='pi',reference='',intent_id='',currency='USD',gross_minor=100,fee_minor=None,net_minor=None)
        r=self.client.get('/api/accounting/receipts',headers=self.a).json()['receipts'][0]
        self.assertEqual(r['status'],'review_required')

if __name__=='__main__':unittest.main()
