"""Fifteen source HTTP checks, fixed public transport and synthetic admin only."""
import json
import unittest
from unittest.mock import Mock,patch
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.trading_router import router
from tools.bs_chat_tool_bridge import BSChatToolBridge
from core.personal_memory_scope import current_memory_principal


class LivestreamPublicSmoke(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(router)
        self.client=TestClient(app);self.addCleanup(self.client.close)
        self.auth=patch('security.host_control_access.get_admin_principal',return_value='local_admin')
        self.auth.start();self.addCleanup(self.auth.stop)
        self.calls=[]
        self.body={'code':0,'result':{'data':[{'bids':[['0.04310','100','1']],'asks':[['0.04311','200','1']]}]}}
        self.raw=None;self.code=200;self.options=[]
        original=httpx.AsyncClient
        def handler(request):
            self.calls.append(request)
            return httpx.Response(self.code,content=self.raw if self.raw is not None else json.dumps(self.body).encode())
        def client(**kwargs):
            self.options.append(kwargs)
            return original(**kwargs,transport=httpx.MockTransport(handler))
        self.transport=patch('httpx.AsyncClient',side_effect=client)
        self.transport.start();self.addCleanup(self.transport.stop)
        self.market=Mock(return_value={'bid':'0.04310','ask':'0.04311','quantity_step':'1',
            'price_tick':'0.00001','observed_at_utc':'2026-11-15T19:00:00+00:00'})
        self.bridge=BSChatToolBridge(crypto_market_provider=self.market)
        self.binding=patch('tools.bs_chat_tool_bridge.bs_chat_bridge',self.bridge)
        self.binding.start();self.addCleanup(self.binding.stop)

    def test_01_anonymous_book_denied_before_source(self):
        with patch('security.host_control_access.get_admin_principal',return_value=None):
            self.assertEqual(self.client.get('/api/trading/public-book').status_code,403)
        self.assertEqual(self.calls,[])

    def test_02_book_success_is_public_market_only(self):
        response=self.client.get('/api/trading/public-book')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['symbol'],'CRO_USDT')
        self.assertFalse(response.json()['account_data_included'])
        self.assertEqual(response.json()['orders_sent'],0)
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertEqual(response.json()['bids'],[['0.04310','100']])

    def test_03_fixed_get_and_no_proxy_or_redirects(self):
        self.client.get('/api/trading/public-book')
        request=self.calls[0]
        self.assertEqual(request.method,'GET')
        self.assertEqual(request.url.host,'api.crypto.com')
        self.assertEqual(request.url.path,'/exchange/v1/public/get-book')
        self.assertEqual(request.url.params['instrument_name'],'CRO_USDT')
        self.assertNotIn('authorization',request.headers)
        self.assertFalse(self.options[0]['trust_env']);self.assertFalse(self.options[0]['follow_redirects'])

    def test_04_binary_float_depth_refused(self):
        self.body['result']['data'][0]['bids']=[[0.04310,'100']]
        self.assertEqual(self.client.get('/api/trading/public-book').status_code,503)

    def test_05_empty_or_excess_depth_refused(self):
        for levels in ([],[['0.04310','1']]*11):
            self.body['result']['data'][0]['bids']=levels
            self.assertEqual(self.client.get('/api/trading/public-book').status_code,503)

    def test_06_duplicate_or_nonfinite_json_refused(self):
        for raw in (b'{"code":1,"code":0}',b'{"code":NaN}'):
            self.raw=raw
            self.assertEqual(self.client.get('/api/trading/public-book').status_code,503)

    def test_07_http_and_provider_errors_are_not_data(self):
        self.code=403
        self.assertEqual(self.client.get('/api/trading/public-book').status_code,503)
        self.code=200;self.body['code']=10004
        self.assertEqual(self.client.get('/api/trading/public-book').status_code,503)

    def test_08_no_custom_host_or_symbol_arguments(self):
        for query in ('symbol=BTC_USDT','url=https://example.com'):
            self.assertEqual(self.client.get('/api/trading/public-book?'+query).status_code,422)
        self.assertEqual(self.calls,[])

    def test_09_authenticated_public_preview_is_never_ready(self):
        response=self.client.get('/api/trading/public-preview?budget_usdt=2')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['status'],'preview')
        self.assertFalse(response.json()['preview']['ready_for_live'])
        self.assertFalse(response.json()['account_accessed'])
        self.assertEqual(response.headers['cache-control'],'private, no-store')

    def test_10_anonymous_preview_denied_before_market(self):
        with patch('security.host_control_access.get_admin_principal',return_value=None):
            self.assertEqual(self.client.get('/api/trading/public-preview').status_code,403)
        self.market.assert_not_called()

    def test_11_unknown_and_duplicate_query_fields_refused(self):
        for query in ('budget_usdt=2&budget_usdt=25','send_order=true','owner=local_admin'):
            self.assertEqual(self.client.get('/api/trading/public-preview?'+query).status_code,422)
        self.market.assert_not_called()

    def test_12_invalid_decimal_assumption_never_fetches(self):
        self.assertEqual(self.client.get('/api/trading/public-preview?budget_usdt=NaN').status_code,503)
        self.market.assert_not_called()

    def test_13_principal_context_is_bound_and_reset(self):
        seen=[];original=self.market.return_value
        self.market.side_effect=lambda:seen.append(current_memory_principal()) or original
        initial=current_memory_principal()
        self.assertEqual(self.client.get('/api/trading/public-preview').status_code,200)
        self.assertEqual(seen,['local_admin'])
        self.assertEqual(current_memory_principal(),initial)

    def test_14_live_order_hold_remains(self):
        response=self.client.post('/api/trading/order',json={'pair':'CRO/USDT','action':'BUY','amount_usd':2})
        self.assertEqual(response.status_code,503)
        self.assertEqual(self.client.get('/api/trading/balances').status_code,503)
        self.market.assert_not_called()

    def test_15_errors_do_not_expose_callback_details(self):
        self.market.side_effect=ValueError('PRIVATE_TEST_DETAIL')
        response=self.client.get('/api/trading/public-preview')
        self.assertEqual(response.status_code,503)
        self.assertNotIn('PRIVATE_TEST_DETAIL',response.text)
        self.assertEqual(current_memory_principal(),None)


if __name__=='__main__':unittest.main()
