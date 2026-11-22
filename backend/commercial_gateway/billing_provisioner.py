"""Verified payment admission. Receipt recording never issues commercial keys.

Snapshot webhook configuration is explicit and has no sandbox credential defaults.
See https://docs.stripe.com/webhooks and
https://developer.paypal.com/api/rest/webhooks/rest/ .
"""
import asyncio
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from urllib.parse import urlparse

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from core.payment_receipts import PaymentConflict, get_receipt_store, minor, usd_minor
from security.financial_auth import require_financial_owner

billing_provisioner_router=APIRouter(prefix='/api/v1/billing',tags=['Commercial Billing & Payouts'])
CATALOG={'day_pass':499,'pass_1day':499,'pass_3day':1199,'pass_5day':1799,'pass_7day':2299,'pass_12day':3499,'pass_15day':3999,'pass_30day':6999}
MAX_BODY=262144


def config(provider):
    mode=os.environ.get('AIBS_PAYMENT_MODE','disabled')
    account=os.environ.get('STRIPE_ACCOUNT_ID' if provider=='stripe' else 'PAYPAL_MERCHANT_ID','')
    if mode not in ('test','live') or not account:
        raise HTTPException(503,'Payment verification is not configured')
    return mode,account


async def raw_body(request):
    chunks=[]; length=0
    async for chunk in request.stream():
        length+=len(chunk)
        if length>MAX_BODY:
            raise HTTPException(413,'Payment event too large')
        chunks.append(chunk)
    return b''.join(chunks)


def parse_event(raw):
    def unique_pairs(pairs):
        result={}
        for k,v in pairs:
            if k in result: raise ValueError('Duplicate JSON key')
            result[k]=v
        return result
    result=json.loads(raw,object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if not isinstance(result,dict): raise ValueError('Invalid event')
    return result


def verify_stripe(raw,signature):
    secret=os.environ.get('STRIPE_WEBHOOK_SECRET','')
    if not secret.startswith('whsec_') or len(secret)<20 or 'sandbox_test_2026' in secret:
        raise HTTPException(503,'Stripe signing secret is not configured')
    parts=[part.strip().split('=',1) for part in signature.split(',')]
    stamps=[p[1] for p in parts if len(p)==2 and p[0]=='t']
    signatures=[p[1] for p in parts if len(p)==2 and p[0]=='v1']
    if len(stamps)!=1 or not re.fullmatch(r'\d{1,12}',stamps[0]): raise ValueError('Invalid signature')
    if abs(time.time()-int(stamps[0]))>300: raise ValueError('Expired signature')
    expected=hmac.new(secret.encode(),stamps[0].encode()+b'.'+raw,hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected,s) for s in signatures): raise ValueError('Invalid signature')


async def verify_paypal(payload,headers,mode):
    client_id=os.environ.get('PAYPAL_CLIENT_ID',''); secret=os.environ.get('PAYPAL_CLIENT_SECRET','')
    webhook_id=os.environ.get('PAYPAL_WEBHOOK_ID','')
    if not all((client_id,secret,webhook_id)) or any('sandbox_' in v for v in (client_id,webhook_id)):
        raise HTTPException(503,'PayPal verification credentials are not configured')
    names={'auth_algo':'paypal-auth-algo','cert_url':'paypal-cert-url','transmission_id':'paypal-transmission-id',
           'transmission_sig':'paypal-transmission-sig','transmission_time':'paypal-transmission-time'}
    data={k:headers.get(v,'') for k,v in names.items()}
    if not all(data.values()) or any(len(v)>4096 for v in data.values()): raise ValueError('Missing verification headers')
    host='api-m.paypal.com' if mode=='live' else 'api-m.sandbox.paypal.com'
    cert=urlparse(data['cert_url'])
    allowed={'api.paypal.com','api-m.paypal.com'} if mode=='live' else {'api.sandbox.paypal.com','api-m.sandbox.paypal.com'}
    if cert.scheme!='https' or cert.hostname not in allowed or cert.port not in (None,443) or cert.username or cert.password or not cert.path.startswith('/v1/notifications/certs/') or cert.query or cert.fragment:
        raise ValueError('Invalid PayPal certificate URL')
    data.update(webhook_id=webhook_id,webhook_event=payload)
    # Fixed provider host; no certificate fetch or client-controlled redirect.
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8),trust_env=False) as session:
        async with session.post('https://'+host+'/v1/oauth2/token',auth=aiohttp.BasicAuth(client_id,secret),
                                data={'grant_type':'client_credentials'},allow_redirects=False) as response:
            if response.status!=200: raise HTTPException(503,'PayPal verification unavailable')
            token=(await response.json()).get('access_token')
            if not isinstance(token,str) or not token: raise HTTPException(503,'PayPal verification unavailable')
        async with session.post('https://'+host+'/v1/notifications/verify-webhook-signature',
            headers={'Authorization':'Bearer '+token},json=data,allow_redirects=False) as response:
            if response.status!=200: raise HTTPException(503,'PayPal verification unavailable')
            if (await response.json()).get('verification_status')!='SUCCESS': raise ValueError('Invalid signature')


async def persist(facts):
    try:
        result=await asyncio.to_thread(get_receipt_store().ingest,**facts)
    except (sqlite3.Error,OSError):
        raise HTTPException(503,'Receipt storage unavailable; retry event delivery') from None
    if result['status']=='conflict': raise HTTPException(409,'Conflicting payment evidence is held for review')
    return result


@billing_provisioner_router.post('/simulate-checkout',status_code=410)
async def simulate_checkout():
    raise HTTPException(410,'Payment simulation cannot grant commercial access; use isolated offline fixtures')


@billing_provisioner_router.post('/stripe-webhook')
async def stripe_webhook(request:Request):
    mode,account=config('stripe'); raw=await raw_body(request)
    try:
        verify_stripe(raw,request.headers.get('stripe-signature',''))
        payload=parse_event(raw)
        if type(payload.get('livemode')) is not bool or payload['livemode']!=(mode=='live'):
            raise ValueError('Payment mode mismatch')
        if payload.get('account',account)!=account: raise ValueError('Provider account mismatch')
        event=payload['type']; obj=payload['data']['object']
        base=dict(provider='stripe',account=account,mode=mode,event_id=payload['id'],digest=hashlib.sha256(raw).hexdigest(),fee_minor=None,net_minor=None)
        if event in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
            if obj.get('payment_status')!='paid' or obj.get('mode')!='payment':
                return {'status':'ignored_unsettled','fulfillment':'held_pending_reconciliation'}
            if obj.get('currency')!='usd': raise ValueError('Unsupported currency')
            facts=dict(base,kind='capture',payment_id=obj['payment_intent'],reference=obj['id'],
                       intent_id=obj.get('metadata',{}).get('intent_id',''),currency='USD',gross_minor=minor(obj['amount_total']))
        elif event in ('charge.refunded','charge.dispute.created','charge.dispute.closed'):
            # Reversals never clear automatically, including out-of-order delivery.
            if obj.get('currency')!='usd': raise ValueError('Unsupported currency')
            payment_id=obj.get('payment_intent')
            if not payment_id:
                raise HTTPException(503,'Reversal requires provider payment lookup before acknowledgement')
            amount=obj.get('amount_refunded') if event=='charge.refunded' else obj.get('amount')
            facts=dict(base,kind='reversal',payment_id=payment_id,reference='',intent_id='',currency='USD',gross_minor=minor(amount))
        else:
            return {'status':'ignored','fulfillment':'held_pending_reconciliation'}
        return await persist(facts)
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
        raise HTTPException(400,'Invalid or unverified payment event') from None


@billing_provisioner_router.post('/paypal-webhook')
async def paypal_webhook(request:Request):
    mode,account=config('paypal'); raw=await raw_body(request)
    try:
        payload=parse_event(raw)
        await verify_paypal(payload,request.headers,mode)
        event=payload['event_type']; obj=payload['resource']
        base=dict(provider='paypal',account=account,mode=mode,event_id=payload['id'],digest=hashlib.sha256(raw).hexdigest())
        if event=='PAYMENT.CAPTURE.COMPLETED' and obj.get('status')=='COMPLETED':
            if obj.get('payee',{}).get('merchant_id')!=account or obj.get('amount',{}).get('currency_code')!='USD': raise ValueError('Merchant or currency mismatch')
            gross=usd_minor(obj['amount']['value']); breakdown=obj.get('seller_receivable_breakdown',{})
            fee=net=None
            if breakdown:
                for key in ('gross_amount','paypal_fee','net_amount'):
                    if breakdown[key]['currency_code']!='USD': raise ValueError('Fee currency mismatch')
                if usd_minor(breakdown['gross_amount']['value'])!=gross: raise ValueError('Gross mismatch')
                fee=usd_minor(breakdown['paypal_fee']['value']); net=usd_minor(breakdown['net_amount']['value'])
            facts=dict(base,kind='capture',payment_id=obj['id'],reference=obj['supplementary_data']['related_ids']['order_id'],
                intent_id=obj.get('custom_id',''),currency='USD',gross_minor=gross,fee_minor=fee,net_minor=net)
        elif event in ('PAYMENT.CAPTURE.REFUNDED','PAYMENT.CAPTURE.REVERSED'):
            capture=obj.get('supplementary_data',{}).get('related_ids',{}).get('capture_id')
            if not capture: raise HTTPException(503,'Reversal requires provider capture lookup before acknowledgement')
            if obj['amount']['currency_code']!='USD': raise ValueError('Currency mismatch')
            facts=dict(base,kind='reversal',payment_id=capture,reference='',intent_id='',currency='USD',gross_minor=usd_minor(obj['amount']['value']))
        else: return {'status':'ignored_unsettled','fulfillment':'held_pending_reconciliation'}
        return await persist(facts)
    except (aiohttp.ClientError,asyncio.TimeoutError):
        raise HTTPException(503,'PayPal verification unavailable; retry delivery') from None
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
        raise HTTPException(400,'Invalid or unverified payment event') from None


class StripeSessionPayload(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tier_id:str
    client_name:str=''
    # Retained for old clients only as a price assertion, never as pricing authority.
    amount_usd:str | None=None


@billing_provisioner_router.post('/create-stripe-session')
async def create_stripe_session(payload:StripeSessionPayload,request:Request,owner=Depends(require_financial_owner)):
    mode,account=config('stripe'); key=os.environ.get('STRIPE_API_KEY','')
    if not key.startswith('sk_live_' if mode=='live' else 'sk_test_'):
        raise HTTPException(503,'Stripe checkout credentials are not configured for this mode')
    price=CATALOG.get(payload.tier_id)
    if price is None: raise HTTPException(422,'Unsupported catalog tier')
    try:
        if payload.amount_usd is not None and usd_minor(payload.amount_usd)!=price: raise ValueError('Price mismatch')
        request_key=request.headers.get('idempotency-key','')
        store=get_receipt_store()
        intent=await asyncio.to_thread(store.prepare_intent,owner,payload.tier_id,price,'stripe',account,mode,request_key)
    except PaymentConflict: raise HTTPException(409,'Checkout request conflicts with its durable intent') from None
    except ValueError: raise HTTPException(422,'Use a server catalog price and stable Idempotency-Key') from None
    except (sqlite3.Error,OSError): raise HTTPException(503,'Checkout intent storage unavailable') from None
    if intent['reference']:
        return {'session_id':intent['reference'],'status':'existing_checkout_requires_lookup','fulfillment':'held_pending_reconciliation'}
    # Local intent durability exceeds the provider's idempotency retention. Never
    # dispatch another create for an old ambiguous outcome.
    if time.time()-intent['created_at'] > 23*60*60:
        raise HTTPException(409,'Unresolved checkout requires provider reconciliation; no new session created')
    data={'success_url':'https://ai-bs-dashboard.web.app/?checkout=pending_verification',
          'cancel_url':'https://ai-bs-dashboard.web.app/?checkout=cancelled','mode':'payment',
          'line_items[0][price_data][currency]':'usd','line_items[0][price_data][product_data][name]':'AI-BS '+payload.tier_id,
          'line_items[0][price_data][unit_amount]':str(price),'line_items[0][quantity]':'1','metadata[intent_id]':intent['id']}
    # No automatic POST retry: callers may retry the SAME durable idempotency key.
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8),trust_env=False) as session:
            async with session.post('https://api.stripe.com/v1/checkout/sessions',data=data,
                headers={'Authorization':'Bearer '+key,'Idempotency-Key':intent['id']},allow_redirects=False) as resp:
                if resp.status!=200: raise HTTPException(503,'Checkout not confirmed; retry with the same Idempotency-Key')
                result=await resp.json(); ref=result['id']; url=result['url']
                if not isinstance(ref,str) or not ref.startswith('cs_') or urlparse(url).scheme!='https' or urlparse(url).hostname!='checkout.stripe.com':
                    raise ValueError('Invalid checkout response')
        await asyncio.to_thread(store.bind_reference,intent['id'],ref)
    except PaymentConflict: raise HTTPException(409,'Conflicting checkout reference is held') from None
    except (aiohttp.ClientError,asyncio.TimeoutError,sqlite3.Error,OSError,ValueError,KeyError,TypeError):
        raise HTTPException(503,'Checkout outcome unknown; retain and retry the same Idempotency-Key') from None
    return {'url':url,'session_id':ref,'status':'pending_payment','fulfillment':'held_pending_reconciliation'}
