"""Fifteen controlled HTTP checks for metadata-only protective review."""
import threading
import unittest
from unittest.mock import Mock,patch
from tests.test_crypto_trial_status_http_smoke import TrialStatusHttpSmoke as Fixture
from core.personal_memory_scope import current_memory_principal
from tools.bs_chat_tool_bridge import BSChatToolBridge


def reply(status='not_registered'):
    return dict(status=status,draft_count=0,pending_evidence_count=0,observed_state='NOT_PREPARED',quarantined=False,
        native_order_accepted=False,child_mapping_verified=False,full_position_protection_verified=False,
        live_dispatch_enabled=False,ready_for_live=False,account_accessed=False,orders_sent=0)


class ProtectiveReviewHttpSmoke(unittest.TestCase):
    def setUp(self):
        Fixture.setUp(self);self.bridge.execute_tool.return_value=reply()

    def get(self,query=''):
        return self.client.get('/api/trading/protective-review'+query,headers=self.headers)

    def test_01_not_registered_returns_metadata_only(self):
        response=self.get();self.assertEqual(response.status_code,200);self.assertEqual(response.json(),reply())
        self.bridge.execute_tool.assert_called_once_with('get_crypto_protective_review',{})

    def test_02_not_prepared_is_visible_without_creation(self):
        self.bridge.execute_tool.return_value=reply('not_prepared')
        response=self.get();self.assertEqual(response.status_code,200);self.assertEqual(response.json(),reply('not_prepared'))

    def test_03_qualification_keeps_acceptance_false(self):
        data=dict(reply('qualification'),draft_count=1,observed_state='UNSIGNED_DRAFT')
        self.bridge.execute_tool.return_value=data
        response=self.get();self.assertEqual(response.status_code,200);self.assertEqual(response.json(),data)

    def test_04_quarantined_held_is_visible(self):
        data=dict(reply('held'),draft_count=1,observed_state='ACTIVE',quarantined=True)
        self.bridge.execute_tool.return_value=data
        response=self.get();self.assertEqual(response.status_code,200);self.assertEqual(response.json(),data)

    def test_05_anonymous_denied_before_bridge(self):
        self.assertEqual(self.client.get('/api/trading/protective-review').status_code,403)
        self.bridge.execute_tool.assert_not_called()

    def test_06_invalid_admin_denied_before_bridge(self):
        response=self.client.get('/api/trading/protective-review',headers={'x-admin-key':'invalid'})
        self.assertEqual(response.status_code,403);self.bridge.execute_tool.assert_not_called()

    def test_07_any_query_and_duplicates_refused(self):
        for query in ('?root=C:/private','?stop_id=abc','?prepare=true','?owner=a&owner=a'):
            self.assertEqual(self.get(query).status_code,422)
        self.bridge.execute_tool.assert_not_called()

    def test_08_verified_principal_reaches_thread_and_resets(self):
        seen=[]
        def tool(*args):
            seen.append((current_memory_principal(),threading.current_thread().name));return reply()
        self.bridge.execute_tool.side_effect=tool
        self.assertEqual(self.get().status_code,200);self.assertEqual(seen[0][0],'local_admin')
        self.assertIn('asyncio',seen[0][1]);self.assertEqual(self.after,[None])

    def test_09_exception_is_generic_and_context_resets(self):
        self.bridge.execute_tool.side_effect=RuntimeError('PRIVATE_ROOT_AND_ACCOUNT')
        response=self.get();self.assertEqual(response.status_code,503)
        self.assertNotIn('PRIVATE_ROOT_AND_ACCOUNT',response.text);self.assertEqual(self.after,[None])

    def test_10_denied_maps_to_403(self):
        self.bridge.execute_tool.return_value={'status':'denied'}
        self.assertEqual(self.get().status_code,403)

    def test_11_unavailable_error_and_malformed_are_private_503(self):
        for data in (None,[],{},dict(reply(),status='unavailable'),{'status':'error','error':'PRIVATE_ERROR'}):
            self.bridge.execute_tool.return_value=data;response=self.get()
            self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE_ERROR',response.text)

    def test_12_unsafe_flags_and_noninteger_counts_refused(self):
        for key,value in [('native_order_accepted',True),('child_mapping_verified',True),
                ('full_position_protection_verified',True),('live_dispatch_enabled',True),
                ('ready_for_live',True),('account_accessed',True),('orders_sent',1),('orders_sent',False),
                ('draft_count',False),('pending_evidence_count',-1)]:
            self.bridge.execute_tool.return_value=dict(reply(),**{key:value})
            self.assertEqual(self.get().status_code,503)

    def test_13_private_extras_and_unbounded_state_refused(self):
        for data in (dict(reply(),root='PRIVATE_ROOT',account='PRIVATE_ACCOUNT'),
                dict(reply('qualification'),draft_count=1,observed_state='PRIVATE_SECRET'*100)):
            self.bridge.execute_tool.return_value=data;response=self.get()
            self.assertEqual(response.status_code,503)
            self.assertNotIn('PRIVATE_',response.text)

    def test_14_response_has_private_no_store_headers(self):
        response=self.get();self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertIn('Authorization',response.headers['vary'])

    def test_15_public_preview_is_still_readonly(self):
        market=Mock(return_value=dict(bid='0.1000',ask='0.1001',quantity_step='0.1',price_tick='0.0001',
            observed_at_utc='2026-11-15T19:00:00+00:00'))
        bridge=BSChatToolBridge(crypto_market_provider=market)
        with patch('tools.bs_chat_tool_bridge.bs_chat_bridge',bridge):
            response=self.client.get('/api/trading/public-preview?budget_usdt=2',headers=self.headers)
        self.assertEqual(response.status_code,200);self.assertFalse(response.json()['account_accessed'])
        self.assertEqual(response.json()['orders_sent'],0);market.assert_called_once_with()
        self.bridge.execute_tool.assert_not_called()


if __name__=='__main__':unittest.main()

