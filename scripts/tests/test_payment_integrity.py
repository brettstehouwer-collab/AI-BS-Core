"""Offline payment admission fixtures; never provider/account acceptance evidence."""
import asyncio
from contextlib import closing
import hashlib
import hmac
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from fastapi import FastAPI
from fastapi.testclient import TestClient

class FakeSession:
    """In-memory provider response script: no socket or real SDK."""
    def __init__(self,*responses):self.responses=list(responses);self.calls=[]
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def post(self,url,**options):
        self.calls.append((url,options))
        result=self.responses.pop(0)
        if isinstance(result,Exception):raise result
        class Reply:
            status=200
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def json(self):return result
        return Reply()
from core.payment_receipts import ReceiptStore, PaymentConflict
from commercial_gateway import billing_provisioner as billing


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aibs-offline-payment-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'receipts.sqlite'
        self.store = ReceiptStore(self.path)
        self.intent = self.store.prepare_intent('owner-a', 'pass_1day', 499, 'stripe', 'acct_fixture', 'test', 'request-1')
        self.store.bind_reference(self.intent['id'], 'cs_fixture')

    def receipt(self, **overrides):
        record = dict(provider='stripe', account='acct_fixture', mode='test', event_id='evt_fixture',
                      digest='a'*64, kind='capture', payment_id='pi_fixture', reference='cs_fixture',
                      intent_id=self.intent['id'], currency='USD', gross_minor=499, fee_minor=19, net_minor=480)
        record.update(overrides)
        return record

    def test_exact_durable_receipt_and_event_and_capture_deduplication(self):
        first = self.store.ingest(**self.receipt())
        self.assertEqual(first['status'], 'recorded')
        self.assertEqual(self.store.ingest(**self.receipt())['status'], 'duplicate')
        self.assertEqual(self.store.ingest(**self.receipt(event_id='evt_second', digest='b'*64))['status'], 'duplicate_payment')
        rows = ReceiptStore(self.path).receipts('owner-a')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['gross'], '4.99')
        self.assertEqual(rows[0]['net'], '4.80')
        self.assertEqual(self.store.receipts('owner-b'), [])

    def test_signed_wrong_price_currency_or_reference_cannot_be_owned(self):
        for field, value in [('gross_minor', 1), ('currency', 'EUR'), ('reference', 'cs_other'), ('intent_id', 'unknown')]:
            with self.subTest(field=field):
                r = self.receipt(event_id='evt_'+field, payment_id='pi_'+field, fee_minor=None, net_minor=None)
                r[field] = value
                self.store.ingest(**r)
        self.assertEqual(self.store.receipts('owner-a'), [])

    def test_unknown_fee_stays_unreconciled(self):
        self.store.ingest(**self.receipt(fee_minor=None, net_minor=None))
        r = self.store.receipts('owner-a')[0]
        self.assertIsNone(r['fee'])
        self.assertEqual(r['status'], 'fee_evidence_missing')

    def test_conflict_is_durable_and_blocks_reconciliation(self):
        self.store.ingest(**self.receipt())
        self.assertEqual(self.store.ingest(**self.receipt(digest='c'*64))['status'], 'conflict')
        self.assertEqual(ReceiptStore(self.path).receipts('owner-a')[0]['status'], 'review_required')

    def test_reversal_before_capture_and_after_restart_stays_held(self):
        self.store.ingest(**self.receipt(kind='reversal', event_id='evt_refund', gross_minor=100, fee_minor=None, net_minor=None))
        ReceiptStore(self.path).ingest(**self.receipt())
        self.assertEqual(self.store.receipts('owner-a')[0]['status'], 'review_required')

    def test_concurrent_replay_has_one_capture(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: ReceiptStore(self.path).ingest(**self.receipt()), range(8)))
        self.assertEqual(len(self.store.receipts('owner-a')), 1)

    def test_immutable_provider_facts(self):
        self.store.ingest(**self.receipt())
        with closing(sqlite3.connect(self.path)) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute('UPDATE payment_receipts_v1 SET gross_minor=1')

    def test_checkout_retry_is_stable_and_changed_request_conflicts(self):
        same = self.store.prepare_intent('owner-a', 'pass_1day', 499, 'stripe', 'acct_fixture', 'test', 'request-1')
        self.assertEqual(same['id'], self.intent['id'])
        with self.assertRaises(PaymentConflict):
            self.store.prepare_intent('owner-a', 'pass_1day', 999, 'stripe', 'acct_fixture', 'test', 'request-1')
        with self.assertRaises(PaymentConflict):
            self.store.bind_reference(self.intent['id'], 'cs_other')

    def test_bad_fee_math_and_boolean_or_float_minor_units_rejected(self):
        for edits in [dict(fee_minor=20), dict(gross_minor=True), dict(gross_minor=499.0), dict(gross_minor=-1)]:
            with self.assertRaises(ValueError):
                self.store.ingest(**self.receipt(**edits))


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aibs-offline-hooks-')
        self.addCleanup(self.tmp.cleanup)
        self.store = ReceiptStore(Path(self.tmp.name)/'test.sqlite')
        self.intent = self.store.prepare_intent('owner-a','pass_1day',499,'stripe','acct_fixture','test','req')
        self.store.bind_reference(self.intent['id'],'cs_fixture')
        self.env = patch.dict(os.environ, {'AIBS_PAYMENT_MODE':'test','STRIPE_WEBHOOK_SECRET':'whsec_fixture_only_secret',
                                         'STRIPE_ACCOUNT_ID':'acct_fixture'}, clear=False)
        self.env.start(); self.addCleanup(self.env.stop)
        self.sp = patch.object(billing,'get_receipt_store',return_value=self.store)
        self.sp.start(); self.addCleanup(self.sp.stop)
        app=FastAPI(); app.include_router(billing.billing_provisioner_router)
        self.client=TestClient(app); self.addCleanup(self.client.close)

    def event(self, **edits):
        session={'id':'cs_fixture','payment_status':'paid','mode':'payment','payment_intent':'pi_fixture',
                 'amount_total':499,'currency':'usd','metadata':{'intent_id':self.intent['id']}}
        session.update(edits)
        return {'id':'evt_fixture','type':'checkout.session.completed','livemode':False,'data':{'object':session}}

    def post(self, body=None, age=0, signed=True):
        raw=json.dumps(body or self.event(),separators=(',',':')).encode()
        stamp=str(int(time.time())-age)
        sig=hmac.new(b'whsec_fixture_only_secret',stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        return self.client.post('/api/v1/billing/stripe-webhook',content=raw,
            headers={'stripe-signature':f't={stamp},v1={sig}' if signed else 'invalid'})

    def test_unsigned_stale_and_future_never_write(self):
        for kwargs in [dict(signed=False),dict(age=301),dict(age=-301)]:
            self.assertEqual(self.post(**kwargs).status_code,400)
        self.assertEqual(self.store.receipts('owner-a'),[])

    def test_raw_payload_tampering_and_ambiguous_json_are_rejected(self):
        stamp=str(int(time.time()));raw=json.dumps(self.event(),separators=(',',':')).encode()
        signature=hmac.new(b'whsec_fixture_only_secret',stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
        self.assertEqual(self.client.post('/api/v1/billing/stripe-webhook',content=raw+b' ',headers={'stripe-signature':f't={stamp},v1={signature}'}).status_code,400)
        for raw in [b'{"id":"first","id":"second"}',b'{"amount":NaN}']:
            signature=hmac.new(b'whsec_fixture_only_secret',stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
            self.assertEqual(self.client.post('/api/v1/billing/stripe-webhook',content=raw,headers={'stripe-signature':f't={stamp},v1={signature}'}).status_code,400)
        self.assertEqual(self.store.receipts('owner-a'),[])

    def test_valid_paid_event_durable_no_key_and_unknown_fees(self):
        result=self.post()
        self.assertEqual(result.status_code,200,result.text)
        self.assertNotIn('key',result.text)
        self.assertEqual(self.store.receipts('owner-a')[0]['status'],'fee_evidence_missing')
        self.assertEqual(self.post().json()['status'],'duplicate')

    def test_unpaid_mode_currency_amount_and_account_are_not_receipts(self):
        for edits in [dict(payment_status='unpaid'),dict(mode='subscription'),dict(amount_total=True),dict(currency='eur')]:
            self.assertIn(self.post(self.event(**edits)).status_code,(200,400))
        live=self.event(); live['livemode']=True
        self.assertEqual(self.post(live).status_code,400)
        account=self.event(); account['account']='acct_other'
        self.assertEqual(self.post(account).status_code,400)
        self.assertEqual(self.store.receipts('owner-a'),[])

    def test_disabled_configuration_and_simulation_do_not_issue_access(self):
        with patch.dict(os.environ,{'AIBS_PAYMENT_MODE':'disabled'}):
            self.assertEqual(self.post().status_code,503)
        r=self.client.post('/api/v1/billing/simulate-checkout',json={'client_name':'fixture','email':'fixture@example.invalid','tier':'enterprise'})
        self.assertIn(r.status_code,(403,410))

    def test_storage_failure_is_retryable_not_false_ack(self):
        with patch.object(self.store,'ingest',side_effect=sqlite3.OperationalError('offline fixture')):
            self.assertEqual(self.post().status_code,503)

    def test_paypal_unverified_and_order_approved_cannot_issue_receipts(self):
        r=self.client.post('/api/v1/billing/paypal-webhook',json={'event_type':'CHECKOUT.ORDER.APPROVED'})
        self.assertIn(r.status_code,(400,503))
        self.assertEqual(self.store.receipts('owner-a'),[])

    def test_checkout_price_recovery_and_timeout_never_duplicate_bound_or_old_intent(self):
        app=FastAPI();app.include_router(billing.billing_provisioner_router)
        app.dependency_overrides[billing.require_financial_owner]=lambda:'owner-a'
        with TestClient(app) as client, patch.dict(os.environ,{'STRIPE_API_KEY':'sk_test_fixture_only'}):
            headers={'Idempotency-Key':'checkout-offline'}
            payload={'tier_id':'pass_1day','amount_usd':'4.99'}
            fake=FakeSession(asyncio.TimeoutError(),{'id':'cs_recovered','url':'https://checkout.stripe.com/c/pay_fixture'})
            with patch.object(billing.aiohttp,'ClientSession',return_value=fake) as factory:
                self.assertEqual(client.post('/api/v1/billing/create-stripe-session',headers=headers,json=dict(payload,amount_usd='0.01')).status_code,422)
                self.assertEqual(fake.calls,[])
                self.assertEqual(client.post('/api/v1/billing/create-stripe-session',headers=headers,json=payload).status_code,503)
                self.assertEqual(client.post('/api/v1/billing/create-stripe-session',headers=headers,json=payload).status_code,200)
                recovered=client.post('/api/v1/billing/create-stripe-session',headers=headers,json=payload)
                self.assertEqual(recovered.json()['session_id'],'cs_recovered')
                self.assertEqual(len(fake.calls),2)
                self.assertEqual(fake.calls[0][1]['headers']['Idempotency-Key'],fake.calls[1][1]['headers']['Idempotency-Key'])
                self.assertEqual(fake.calls[0][1]['data']['line_items[0][price_data][unit_amount]'],'499')
                self.assertFalse(fake.calls[0][1]['allow_redirects']);self.assertFalse(factory.call_args.kwargs['trust_env'])
            old=self.store.prepare_intent('owner-a','pass_1day',499,'stripe','acct_fixture','test','old-key')
            with closing(sqlite3.connect(self.store.path)) as conn:
                conn.execute('UPDATE payment_intents_v1 SET created_at=? WHERE id=?',(int(time.time())-86401,old['id']));conn.commit()
            with patch.object(billing.aiohttp,'ClientSession',side_effect=AssertionError('must not dispatch')):
                self.assertEqual(client.post('/api/v1/billing/create-stripe-session',headers={'Idempotency-Key':'old-key'},json=payload).status_code,409)

    def test_paypal_verified_capture_exact_fees_and_reversal(self):
        intent=self.store.prepare_intent('owner-a','pass_1day',499,'paypal','merchant_fixture','test','paypal-offline')
        self.store.bind_reference(intent['id'],'order_fixture')
        env={'PAYPAL_MERCHANT_ID':'merchant_fixture','PAYPAL_CLIENT_ID':'client_fixture','PAYPAL_CLIENT_SECRET':'secret_fixture','PAYPAL_WEBHOOK_ID':'hook_fixture'}
        headers={'paypal-auth-algo':'SHA256withRSA','paypal-cert-url':'https://api.sandbox.paypal.com/v1/notifications/certs/fixture',
                 'paypal-transmission-id':'transmission_fixture','paypal-transmission-sig':'signature_fixture','paypal-transmission-time':'2026-10-30T00:00:00Z'}
        usd=lambda amount:{'value':amount,'currency_code':'USD'}
        capture={'id':'evt_paypal','event_type':'PAYMENT.CAPTURE.COMPLETED','resource':{
            'id':'capture_fixture','status':'COMPLETED','payee':{'merchant_id':'merchant_fixture'},'amount':usd('4.99'),
            'custom_id':intent['id'],'supplementary_data':{'related_ids':{'order_id':'order_fixture'}},
            'seller_receivable_breakdown':{'gross_amount':usd('4.99'),'paypal_fee':usd('0.19'),'net_amount':usd('4.80')}}}
        with patch.dict(os.environ,env):
            fake=FakeSession({'access_token':'fixture_token'},{'verification_status':'FAILURE'})
            with patch.object(billing.aiohttp,'ClientSession',return_value=fake):
                self.assertEqual(self.client.post('/api/v1/billing/paypal-webhook',headers=headers,json=capture).status_code,400)
            self.assertEqual(self.store.receipts('owner-a'),[])
            fake=FakeSession({'access_token':'fixture_token'},{'verification_status':'SUCCESS'})
            with patch.object(billing.aiohttp,'ClientSession',return_value=fake):
                result=self.client.post('/api/v1/billing/paypal-webhook',headers=headers,json=capture)
                self.assertEqual(result.status_code,200,result.text)
            self.assertTrue(all(url.startswith('https://api-m.sandbox.paypal.com/') and not options['allow_redirects'] for url,options in fake.calls))
            receipt=self.store.receipts('owner-a')[0];self.assertEqual((receipt['gross'],receipt['fee'],receipt['net']),('4.99','0.19','4.80'))
            reverse={'id':'evt_refund','event_type':'PAYMENT.CAPTURE.REFUNDED','resource':{
                'amount':usd('1.00'),'supplementary_data':{'related_ids':{'capture_id':'capture_fixture'}}}}
            fake=FakeSession({'access_token':'fixture_token'},{'verification_status':'SUCCESS'})
            with patch.object(billing.aiohttp,'ClientSession',return_value=fake):
                self.assertEqual(self.client.post('/api/v1/billing/paypal-webhook',headers=headers,json=reverse).status_code,200)
            self.assertEqual(self.store.receipts('owner-a')[0]['status'],'review_required')

    def test_paypal_verification_timeout_has_no_receipt_and_bad_certificate_has_no_network(self):
        env={'PAYPAL_MERCHANT_ID':'merchant_fixture','PAYPAL_CLIENT_ID':'client_fixture','PAYPAL_CLIENT_SECRET':'secret_fixture','PAYPAL_WEBHOOK_ID':'hook_fixture'}
        headers={key:'fixture' for key in ['paypal-auth-algo','paypal-transmission-id','paypal-transmission-sig','paypal-transmission-time']}
        with patch.dict(os.environ,env):
            with patch.object(billing.aiohttp,'ClientSession',side_effect=AssertionError('must not dispatch')):
                self.assertEqual(self.client.post('/api/v1/billing/paypal-webhook',headers=dict(headers,**{'paypal-cert-url':'https://example.invalid/cert'}),json={}).status_code,400)
            headers['paypal-cert-url']='https://api.sandbox.paypal.com/v1/notifications/certs/fixture'
            with patch.object(billing.aiohttp,'ClientSession',return_value=FakeSession(asyncio.TimeoutError())):
                self.assertEqual(self.client.post('/api/v1/billing/paypal-webhook',headers=headers,json={}).status_code,503)
            self.assertEqual(self.store.receipts('owner-a'),[])


if __name__=='__main__': unittest.main()
