"""Fifteen draft stop-selection checks; synthetic public market only."""
import asyncio
import copy
from datetime import datetime, timezone
from decimal import Decimal
import inspect
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from starlette.requests import Request
from fastapi import HTTPException
from core.crypto_execution_controls import ControlError
from core.crypto_spot_preview import preview_cro_spot
from core.crypto_spot_protection import review_cro_protection
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from tools.bs_chat_tool_bridge import BSChatToolBridge
from tools.tool_registry import ToolRegistry


class TrialSelectionSmoke(unittest.TestCase):
    def setUp(self):
        self.preview = preview_cro_spot(budget_usdt='2', bid='0.1000', ask='0.1001',
            quantity_step='0.1', price_tick='0.0001', minimum_notional_usd='1',
            usdt_usd_index='1', entry_fee_bps='25', exit_fee_bps='50',
            stop_price='0.0980', daily_loss_budget_usdt='1')
        self.market = Mock(side_effect=lambda: dict(bid='0.1000', ask='0.1001',
            quantity_step='0.1', price_tick='0.0001', observed_at_utc=datetime.now(timezone.utc).isoformat()))
        self.bridge = BSChatToolBridge(crypto_market_provider=self.market)
        binding = patch('tools.bs_chat_tool_bridge.bs_chat_bridge', self.bridge)
        binding.start(); self.addCleanup(binding.stop)
        token = bind_memory_principal('local_admin')
        self.addCleanup(reset_memory_principal, token)

    def selected(self, **updates):
        args = dict(stop_type='STOP_LOSS', trigger_reference_type='LAST_PRICE', price_tick='0.0001')
        return review_cro_protection(self.preview, **dict(args, **updates))

    def invoke(self, **arguments):
        return ToolRegistry.execute_tool('preview_crypto_spot', arguments)

    def test_01_old_default_review_stays_unselected(self):
        result = review_cro_protection(self.preview)
        self.assertIsNone(result['selected_stop_type'])
        self.assertIsNone(result['trigger_reference_type'])

    def test_02_saved_stop_market_last_price_choice(self):
        result = self.selected()
        self.assertEqual(result['selected_stop_type'], 'STOP_LOSS')
        self.assertEqual(result['trigger_reference_type'], 'LAST_PRICE')
        self.assertNotIn('STOP_TYPE_SELECTION_REQUIRED', result['blocking_checks'])
        self.assertNotIn('TRIGGER_REFERENCE_SELECTION_REQUIRED', result['blocking_checks'])

    def test_03_valid_reference_modes_and_stop_limit(self):
        for reference in ('LAST_PRICE','MARK_PRICE','INDEX_PRICE'):
            result = self.selected(stop_type='STOP_LIMIT', trigger_reference_type=reference, stop_limit_price='0.0970')
            self.assertEqual(result['trigger_reference_type'], reference)
            option = next(o for o in result['stop_options'] if o['type']=='STOP_LIMIT')
            self.assertEqual(Decimal(option['limit_price']), Decimal('0.0970'))

    def test_04_selection_does_not_clear_real_protection_holds(self):
        result = self.selected()
        for blocker in ('CURRENT_TRIAL_OPENING_STATE_UNVERIFIED','PARTIAL_FILL_PROTECTION_UNVERIFIED',
                        'ACTUAL_FILL_QUANTITY_AND_FEES_UNVERIFIED','NATIVE_STOP_ACCEPTANCE_UNVERIFIED','DAILY_CUTOFF_NOT_ENFORCED'):
            self.assertIn(blocker, result['blocking_checks'])
        for field in ('ready_for_live','native_order_accepted','partial_fill_protection_verified','live_dispatch_enabled'):
            self.assertIs(result[field], False)
        self.assertEqual(result['orders_sent'], 0)

    def test_05_missing_limit_remains_blocked(self):
        result = self.selected(stop_type='STOP_LIMIT')
        self.assertTrue(any('LIMIT' in b and ('MISSING' in b or 'REQUIRED' in b) for b in result['blocking_checks']))

    def test_06_limit_must_be_positive_not_above_trigger_and_tick_aligned(self):
        for limit in ('0','-1','0.0990','0.09705'):
            with self.subTest(limit=limit), self.assertRaises(ControlError):
                self.selected(stop_type='STOP_LIMIT', stop_limit_price=limit)
        for tick in (None, '0', '-0.0001'):
            with self.subTest(tick=tick), self.assertRaises(ControlError):
                self.selected(stop_type='STOP_LIMIT', stop_limit_price='0.0970', price_tick=tick)

    def test_07_stop_market_cannot_carry_limit(self):
        with self.assertRaises(ControlError):
            self.selected(stop_limit_price='0.0970')

    def test_08_pure_invalid_enums_and_types_rejected(self):
        for changes in ({'stop_type':'MARKET'}, {'stop_type':True}, {'trigger_reference_type':'LAST'},
                        {'trigger_reference_type':1}):
            with self.subTest(changes=changes), self.assertRaises(ControlError):
                self.selected(**changes)

    def test_09_selected_review_preserves_four_cases_and_input(self):
        before = copy.deepcopy(self.preview)
        default = review_cro_protection(self.preview)
        selected = self.selected()
        self.assertEqual(selected['fee_currency_cases'], default['fee_currency_cases'])
        self.assertEqual(selected['static_quantity_candidate_cro'], default['static_quantity_candidate_cro'])
        self.assertEqual(self.preview, before)

    def test_10_bridge_defaults_saved_choices_without_live_authority(self):
        result = self.invoke()
        self.assertEqual(result['status'], 'preview')
        review = result['protection_review']
        self.assertEqual(review['selected_stop_type'], 'STOP_LOSS')
        self.assertEqual(review['trigger_reference_type'], 'LAST_PRICE')
        self.assertIs(review['ready_for_live'], False)
        self.assertIs(result['account_accessed'], False)
        self.assertEqual(result['orders_sent'], 0)

    def test_11_invalid_bridge_fields_rejected_before_market_io(self):
        for args in ({'stop_type':'MARKET'}, {'stop_type':True}, {'trigger_reference_type':'LAST'},
                     {'trigger_reference_type':1}, {'stop_limit_price':0.097}):
            with self.subTest(args=args):
                self.assertNotEqual(self.invoke(**args).get('status'), 'preview')
        self.market.assert_not_called()

    def test_12_registry_and_chat_declare_three_closed_string_fields(self):
        from core.crypto_preview_chat import FIELDS, crypto_preview_declarations
        for declarations in (ToolRegistry.get_tool_declarations(), crypto_preview_declarations()):
            declaration = next(d for d in declarations if d['name']=='preview_crypto_spot')
            self.assertFalse(declaration['parameters']['additionalProperties'])
            for name in ('stop_type','trigger_reference_type','stop_limit_price'):
                self.assertIn(name, FIELDS)
                self.assertEqual(declaration['parameters']['properties'][name]['type'], 'string')

    def test_13_chat_accepts_selection_and_formats_not_armed(self):
        from core.crypto_preview_chat import crypto_preview_reply, _format
        command = '/crypto-preview ' + json.dumps({'stop_type':'STOP_LIMIT','trigger_reference_type':'MARK_PRICE','stop_limit_price':'0.0970'})
        reply = asyncio.run(crypto_preview_reply({'user_prompt':command}))
        self.assertIn('STOP_LIMIT', reply['response'])
        self.assertIn('MARK_PRICE', reply['response'])
        self.assertIn('not armed', reply['response'].lower())
        result = self.invoke()
        result['protection_review'] = review_cro_protection(result['preview'])
        self.assertIn('unselected', _format(result).lower())

    def test_14_public_preview_signature_forwards_selection(self):
        from routers.trading_router import get_public_spot_preview
        for field in ('stop_type','trigger_reference_type','stop_limit_price'):
            self.assertIn(field, inspect.signature(get_public_spot_preview).parameters)
        query = b'stop_type=STOP_LIMIT&trigger_reference_type=INDEX_PRICE&stop_limit_price=0.0970'
        request = Request({'type':'http','method':'GET','path':'/api/trading/public-preview','query_string':query,'headers':[]})
        with patch('security.host_control_access.require_host_admin', new=AsyncMock(return_value='local_admin')):
            result = asyncio.run(get_public_spot_preview(request, stop_type='STOP_LIMIT',
                trigger_reference_type='INDEX_PRICE', stop_limit_price='0.0970'))
        self.assertEqual(result['protection_review']['selected_stop_type'], 'STOP_LIMIT')
        self.assertEqual(result['protection_review']['trigger_reference_type'], 'INDEX_PRICE')
        self.assertEqual(result['protection_review']['scope'], 'PROTECTION_REVIEW_NOT_AN_ORDER')
        self.assertEqual(result['orders_sent'], 0)

    def test_15_duplicate_unknown_route_keys_refused_before_io(self):
        from routers.trading_router import get_public_spot_preview
        for query in (b'stop_type=STOP_LOSS&stop_type=STOP_LIMIT', b'execute=true'):
            request = Request({'type':'http','method':'GET','path':'/api/trading/public-preview','query_string':query,'headers':[]})
            with self.subTest(query=query), self.assertRaises(HTTPException) as caught:
                asyncio.run(get_public_spot_preview(request))
            self.assertEqual(caught.exception.status_code, 422)
        self.market.assert_not_called()


if __name__ == '__main__':
    unittest.main()
