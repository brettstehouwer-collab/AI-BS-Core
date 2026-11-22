"""Synthetic chat arithmetic qualification; no account, market or model calls."""
import asyncio
from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import Mock, patch

from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from tools.bs_chat_tool_bridge import BSChatToolBridge
from tools.tool_registry import ToolRegistry, _BS_CHAT_DIAGNOSTIC_NAMES


class CryptoPreviewChatSmoke(unittest.TestCase):
    def setUp(self):
        self.market = Mock(side_effect=lambda: {
            'bid': '0.1000', 'ask': '0.1001', 'quantity_step': '0.1',
            'price_tick': '0.0001', 'observed_at_utc': datetime.now(timezone.utc).isoformat(),
            'private_extra': 'SYNTHETIC_DO_NOT_EXPOSE'})
        self.bridge = BSChatToolBridge(crypto_market_provider=self.market)
        self.binding = patch('tools.bs_chat_tool_bridge.bs_chat_bridge', self.bridge)
        self.binding.start()
        self.addCleanup(self.binding.stop)
        self.token = bind_memory_principal('local_admin')
        self.addCleanup(reset_memory_principal, self.token)

    def invoke(self, arguments=None):
        return ToolRegistry.execute_tool('preview_crypto_spot', arguments or {})

    def reply(self, text=None, **body):
        from core.crypto_preview_chat import crypto_preview_reply
        if text is not None:
            body['user_prompt'] = text
        return asyncio.run(crypto_preview_reply(body))

    def test_01_defaults_are_arithmetic_only(self):
        result = self.invoke()
        self.assertEqual(result['status'], 'preview')
        preview = result['preview']
        self.assertEqual(preview['entry']['budget_all_in_usdt'], '2')
        self.assertFalse(preview['ready_for_live'])
        self.assertFalse(preview['live_dispatch_enabled'])
        self.assertEqual(preview['orders_sent'], 0)
        self.assertEqual(result['fee_rate_source'], 'SCENARIO_INPUTS_NOT_AUTHENTICATED_ACCOUNT_RATES')

    def test_02_missing_principal_denied_before_market(self):
        with patch('tools.bs_chat_tool_bridge.current_memory_principal', return_value=None):
            self.assertEqual(self.invoke(), {'status': 'denied'})
        self.market.assert_not_called()

    def test_03_unknown_and_numeric_arguments_rejected_before_market(self):
        for arguments in ({'budget_usdt': 2.0}, {'budget_usdt': 2},
                          {'budget_usdt': True}, {'account_id': 'synthetic'},
                          {'execute': True}):
            with self.subTest(arguments=arguments):
                result = self.invoke(arguments)
                self.assertNotEqual(result.get('status'), 'preview')
        self.market.assert_not_called()

    def test_04_preview_declared_with_diagnostics_disabled(self):
        with patch.dict(os.environ, {'AI_BS_ENABLE_CHAT_TOOL_BRIDGE': '0'}):
            declarations = ToolRegistry.get_tool_declarations()
            names = {item['name'] for item in declarations}
            self.assertIn('preview_crypto_spot', names)
            self.assertTrue(names.isdisjoint(_BS_CHAT_DIAGNOSTIC_NAMES))
            declaration = next(item for item in declarations if item['name'] == 'preview_crypto_spot')
            self.assertFalse(declaration['parameters']['additionalProperties'])
            self.assertEqual(self.invoke()['status'], 'preview')

    def test_05_market_metadata_whitelisted(self):
        result = self.invoke()
        self.assertNotIn('SYNTHETIC_DO_NOT_EXPOSE', json.dumps(result))
        self.assertTrue({'bid', 'ask', 'quantity_step', 'price_tick', 'observed_at_utc'} <= set(result['market']))

    def test_06_market_failure_sanitized(self):
        self.market.side_effect = RuntimeError('SYNTHETIC_PRIVATE_FAILURE_DETAIL')
        result = self.invoke()
        self.assertNotEqual(result.get('status'), 'preview')
        self.assertNotIn('SYNTHETIC_PRIVATE_FAILURE_DETAIL', json.dumps(result))

    def test_07_command_default(self):
        result = self.reply('/crypto-preview')
        self.assertEqual(result['provider'], 'local')
        self.assertEqual(result['model'], 'crypto-arithmetic-preview')
        self.assertIsInstance(result['response'], str)
        self.assertTrue(result['response'])
        self.market.assert_called_once()

    def test_08_command_budget(self):
        result = self.reply('/crypto-preview 3')
        self.assertEqual(result['model'], 'crypto-arithmetic-preview')
        self.assertIn('3', result['response'])
        self.market.assert_called_once()

    def test_09_command_json_arguments(self):
        result = self.reply('/crypto-preview {"budget_usdt":"2","stop_percent":"2","target_percent":"3"}')
        self.assertEqual(result['model'], 'crypto-arithmetic-preview')
        self.market.assert_called_once()

    def test_10_bad_command_json_never_fetches(self):
        for suffix in ('{"budget_usdt":"2","budget_usdt":"3"}',
                       '{"budget_usdt":NaN}', '{"budget_usdt":2.0}',
                       '{"execute":true}', '{', '2 extra'):
            with self.subTest(suffix=suffix):
                result = self.reply('/crypto-preview ' + suffix)
                self.assertIsInstance(result, dict)
                self.assertIn('crypto-preview', result['response'].lower())
        self.market.assert_not_called()

    def test_11_history_and_attached_text_never_authorize(self):
        for body in ({'messages': [{'role': 'user', 'content': '/crypto-preview 2'}]},
                     {'user_prompt': 'Explain this report', 'prompt': '/crypto-preview 2'},
                     {'user_prompt': 'Unrelated current text', 'messages': [{'role': 'user', 'content': '/crypto-preview'}]}):
            self.assertIsNone(self.reply(**body))
        self.market.assert_not_called()

    def test_12_unrelated_current_text_returns_none(self):
        for text in ('Hello', 'Discuss crypto risk', 'The report says /crypto-preview 2'):
            self.assertIsNone(self.reply(text))
        self.market.assert_not_called()

    def test_13_normal_provider_route_intercepts_before_provider_io(self):
        from core.bs_chat_provider import bs_chat_reply
        with patch('core.bs_chat_provider.openai_completion', side_effect=AssertionError('model forbidden')):
            result = asyncio.run(bs_chat_reply({'user_prompt': '/crypto-preview 2',
                'prompt': '/crypto-preview 2', 'provider': 'local', 'mode': 'execute'}))
        self.assertEqual(result['model'], 'crypto-arithmetic-preview')
        self.market.assert_called_once()

    def test_14_normal_mode_and_backend_guards_precede_preview(self):
        from core.bs_chat_provider import bs_chat_reply
        for extra in ({'plan_only': True}, {'mode': 'review'}, {'mode': 'unsupported'},
                      {'execution_backend': 'windows_vm'}):
            result = asyncio.run(bs_chat_reply(dict(user_prompt='/crypto-preview 2',
                prompt='/crypto-preview 2', **extra)))
            self.assertNotEqual(result.get('model'), 'crypto-arithmetic-preview')
        self.market.assert_not_called()

    def test_15_hybrid_current_turn_preview_without_model(self):
        from core.hybrid_reasoning_engine import stream_stehouwer_hybrid_response
        async def collect():
            return ''.join([part async for part in stream_stehouwer_hybrid_response(
                '/crypto-preview 2', intent_prompt='/crypto-preview 2')])
        result = asyncio.run(collect())
        self.assertTrue(result)
        self.assertNotIn('SYNTHETIC_DO_NOT_EXPOSE', result)
        self.market.assert_called_once()


if __name__ == '__main__':
    unittest.main()
