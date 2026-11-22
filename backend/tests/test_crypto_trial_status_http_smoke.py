"""Fifteen metadata-only trial-status HTTP cases using owned ASGI app."""
import threading
import unittest
from unittest.mock import Mock,patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.trading_router import router
from core.personal_memory_scope import current_memory_principal
from tools.bs_chat_tool_bridge import BSChatToolBridge


def reply(status='not_registered'):
    registered=status in ('qualification','held')
    return dict(status=status,registered=registered,stored_state_verified=registered,
        account_metadata_bound=registered,exchange_account_identity_verified=False,
        local_entry_cutoff_enforced=registered,entry_held=status=='held',
        production_store_admitted=False,native_protection_qualified=False,
        live_dispatch_enabled=False,ready_for_live=False,orders_sent=0,account_accessed=False)


class TrialStatusHttpSmoke(unittest.TestCase):
    def setUp(self):
        app=FastAPI();self.after=[]
        @app.middleware('http')
        async def observe_reset(request,call_next):
            result=await call_next(request)
            self.after.append(current_memory_principal())
            return result
        app.include_router(router)
        self.client=TestClient(app);self.addCleanup(self.client.close)
        self.auth=patch('security.host_control_access.get_admin_principal',
            side_effect=lambda key,authorization:'local_admin' if key=='fixture-admin' else None)
        self.auth.start();self.addCleanup(self.auth.stop)
        self.bridge=Mock();self.bridge.execute_tool.return_value=reply()
        self.binding=patch('tools.bs_chat_tool_bridge.bs_chat_bridge',self.bridge)
        self.binding.start();self.addCleanup(self.binding.stop)
        self.headers={'x-admin-key':'fixture-admin'}

    def get(self,query=''):
        return self.client.get('/api/trading/trial-status'+query,headers=self.headers)

    def test_01_not_registered_metadata_only(self):
        response=self.get();self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),reply())
        self.bridge.execute_tool.assert_called_once_with('get_crypto_trial_status',{})

    def test_02_qualification_is_explicitly_unqualified(self):
        self.bridge.execute_tool.return_value=reply('qualification')
        response=self.get();self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),reply('qualification'))
        self.assertFalse(response.json()['production_store_admitted'])

    def test_03_entry_held_metadata_is_visible(self):
        self.bridge.execute_tool.return_value=reply('held')
        response=self.get();self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()['entry_held'])
        self.assertFalse(response.json()['live_dispatch_enabled'])

    def test_04_anonymous_refused_before_bridge(self):
        self.assertEqual(self.client.get('/api/trading/trial-status').status_code,403)
        self.bridge.execute_tool.assert_not_called()

    def test_05_invalid_admin_refused_before_bridge(self):
        response=self.client.get('/api/trading/trial-status',headers={'x-admin-key':'invalid'})
        self.assertEqual(response.status_code,403);self.bridge.execute_tool.assert_not_called()

    def test_06_any_query_selector_refused(self):
        for query in ('?root=C:/private','?store_uuid=abc','?qualification=true','?send_order=false'):
            self.assertEqual(self.get(query).status_code,422)
        self.bridge.execute_tool.assert_not_called()

    def test_07_duplicate_query_fields_refused(self):
        self.assertEqual(self.get('?owner=a&owner=a').status_code,422)
        self.bridge.execute_tool.assert_not_called()

    def test_08_principal_propagates_into_thread_and_resets(self):
        seen=[]
        def tool(*args):
            seen.append((current_memory_principal(),threading.current_thread().name));return reply()
        self.bridge.execute_tool.side_effect=tool
        self.assertEqual(self.get().status_code,200)
        self.assertEqual(seen[0][0],'local_admin');self.assertIn('asyncio',seen[0][1])
        self.assertEqual(self.after,[None]);self.assertIsNone(current_memory_principal())

    def test_09_exception_is_generic_and_context_resets(self):
        self.bridge.execute_tool.side_effect=RuntimeError('PRIVATE_ROOT_ACCOUNT_SECRET')
        response=self.get();self.assertEqual(response.status_code,503)
        self.assertNotIn('PRIVATE_ROOT_ACCOUNT_SECRET',response.text)
        self.assertEqual(self.after,[None])

    def test_10_bridge_denied_maps_to_403(self):
        self.bridge.execute_tool.return_value={'status':'denied'}
        self.assertEqual(self.get().status_code,403)

    def test_11_unavailable_and_error_map_to_generic_503(self):
        for status in ('unavailable','error'):
            self.bridge.execute_tool.return_value={'status':status,'error':'PRIVATE_PATH'}
            response=self.get();self.assertEqual(response.status_code,503)
            self.assertNotIn('PRIVATE_PATH',response.text)

    def test_12_malformed_or_unsafe_flags_refused(self):
        cases=[None,[],{},dict(reply(),orders_sent=1),dict(reply(),orders_sent=False),
            dict(reply(),live_dispatch_enabled=True),dict(reply(),ready_for_live=True),
            dict(reply(),exchange_account_identity_verified=True),dict(reply(),account_accessed=True),
            dict(reply(),registered='false')]
        for data in cases:
            self.bridge.execute_tool.return_value=data
            self.assertEqual(self.get().status_code,503)

    def test_13_extra_private_fields_cannot_escape(self):
        self.bridge.execute_tool.return_value=dict(reply(),account='PRIVATE_ACCOUNT',root='PRIVATE_ROOT',balance='100')
        response=self.get();self.assertEqual(response.status_code,503)
        self.assertNotIn('PRIVATE_ACCOUNT',response.text);self.assertNotIn('PRIVATE_ROOT',response.text)

    def test_14_private_no_store_headers(self):
        response=self.get();self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertIn('Authorization',response.headers['vary'])

    def test_15_existing_public_preview_keeps_public_only_capture(self):
        market=Mock(return_value=dict(bid='0.1000',ask='0.1001',quantity_step='0.1',
            price_tick='0.0001',observed_at_utc='2026-11-15T19:00:00+00:00'))
        bridge=BSChatToolBridge(crypto_market_provider=market)
        with patch('tools.bs_chat_tool_bridge.bs_chat_bridge',bridge):
            response=self.client.get('/api/trading/public-preview?budget_usdt=2',headers=self.headers)
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['status'],'preview')
        self.assertFalse(response.json()['account_accessed']);self.assertEqual(response.json()['orders_sent'],0)
        market.assert_called_once_with();self.bridge.execute_tool.assert_not_called()


if __name__=='__main__':unittest.main()
