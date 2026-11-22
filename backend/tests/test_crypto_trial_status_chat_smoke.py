"""Fifteen source status-chat cases; no model/account/order I/O."""
import asyncio
import json
import os
import unittest
from unittest.mock import Mock, patch

from core.crypto_trial_status_chat import crypto_trial_status_declarations, crypto_trial_status_reply
from tools.tool_registry import ToolRegistry, _BS_CHAT_DIAGNOSTIC_NAMES


class CryptoTrialStatusChatSmoke(unittest.TestCase):
    def status(self,status,**changes):
        from core.crypto_trial_status_contract import trial_status
        return dict(trial_status(status),**changes)

    def reply(self,text=None,**body):
        if text is not None:body['user_prompt']=text
        return asyncio.run(crypto_trial_status_reply(body))

    def test_01_closed_empty_declaration(self):
        row=crypto_trial_status_declarations()[0]
        self.assertEqual(row['name'],'get_crypto_trial_status')
        self.assertEqual(row['parameters'],{'type':'object','properties':{},'required':[], 'additionalProperties':False})

    def test_02_exact_current_commands(self):
        with patch.object(ToolRegistry,'execute_tool',return_value={'status':'not_registered'}) as run:
            for text in ('/crypto-trial',' /CRYPTO-TRIAL STATUS  '):
                self.assertEqual(self.reply(text)['model'],'crypto-trial-status')
            self.assertEqual(run.call_count,2);run.assert_called_with('get_crypto_trial_status',{})

    def test_03_bad_tails_usage_without_tools(self):
        with patch.object(ToolRegistry,'execute_tool') as run:
            for text in ('/crypto-trial activate','/crypto-trial {}','/crypto-trial status extra','/crypto-trial 2'):
                self.assertIn('/crypto-trial status',self.reply(text)['response'])
            run.assert_not_called()

    def test_04_boundary_and_embedded_text_no_authority(self):
        with patch.object(ToolRegistry,'execute_tool') as run:
            for text in ('/crypto-trialevil','Explain /crypto-trial','hello'):
                self.assertIsNone(self.reply(text))
            run.assert_not_called()

    def test_05_attachments_history_never_authorize(self):
        with patch.object(ToolRegistry,'execute_tool') as run:
            for body in ({'messages':[{'role':'user','content':'/crypto-trial'}]},
                {'user_prompt':'hello','prompt':'/crypto-trial'},
                {'attachments':[{'text':'/crypto-trial'}]}):self.assertIsNone(self.reply(**body))
            run.assert_not_called()

    def test_06_not_registered_sanitized(self):
        with patch.object(ToolRegistry,'execute_tool',return_value=self.status('not_registered')):
            text=self.reply('/crypto-trial')['response']
        self.assertIn('not registered',text.lower());self.assertNotIn('PRIVATE_SENTINEL',text)
        with patch.object(ToolRegistry,'execute_tool',return_value=self.status('not_registered',root='PRIVATE_SENTINEL')):
            self.assertNotIn('PRIVATE_SENTINEL',self.reply('/crypto-trial')['response'])

    def test_07_qualification_is_simulation(self):
        with patch.object(ToolRegistry,'execute_tool',return_value=self.status('qualification')):
            text=self.reply('/crypto-trial')['response']
        self.assertIn('simulation',text.lower());self.assertIn('Live trading remains held',text)

    def test_08_held_unavailable_denied_known_only(self):
        for status in ('held','unavailable','denied','PRIVATE_SENTINEL'):
            result=self.status(status) if status!='PRIVATE_SENTINEL' else {'status':status,'message':'PRIVATE_SENTINEL'}
            with self.subTest(status=status),patch.object(ToolRegistry,'execute_tool',return_value=result):
                text=self.reply('/crypto-trial')['response']
                self.assertNotIn('PRIVATE_SENTINEL',text);self.assertIn('Live trading remains held',text)

    def test_09_exceptions_sanitized(self):
        with patch.object(ToolRegistry,'execute_tool',side_effect=RuntimeError('PRIVATE_SENTINEL')):
            self.assertNotIn('PRIVATE_SENTINEL',self.reply('/crypto-trial')['response'])

    def test_10_unsafe_output_never_promotes_live(self):
        with patch.object(ToolRegistry,'execute_tool',return_value={'status':'qualification','live_dispatch_enabled':True,
            'ready_for_live':True,'native_protection_qualified':True,'orders_sent':99,'account':'PRIVATE_SENTINEL'}):
            text=self.reply('/crypto-trial')['response']
        self.assertIn('Live trading remains held',text);self.assertNotIn('PRIVATE_SENTINEL',text)

    def test_11_normal_provider_route_before_model(self):
        from core.bs_chat_provider import bs_chat_reply
        with (patch.object(ToolRegistry,'execute_tool',return_value={'status':'not_registered'}) as run,
            patch('core.bs_chat_provider.openai_completion',side_effect=AssertionError('model forbidden'))):
            result=asyncio.run(bs_chat_reply({'user_prompt':'/crypto-trial','provider':'local','mode':'execute'}))
        self.assertEqual(result['model'],'crypto-trial-status');run.assert_called_once()

    def test_12_normal_guards_precede_status(self):
        from core.bs_chat_provider import bs_chat_reply
        with patch.object(ToolRegistry,'execute_tool') as run:
            for extra in ({'plan_only':True},{'mode':'review'},{'mode':'unsupported'}, {'execution_backend':'windows_vm'}):
                result=asyncio.run(bs_chat_reply(dict(user_prompt='/crypto-trial',**extra)))
                self.assertNotEqual(result['model'],'crypto-trial-status')
            run.assert_not_called()

    def test_13_hybrid_safety_then_current_turn_status(self):
        from core.hybrid_reasoning_engine import stream_stehouwer_hybrid_response
        async def collect():return ''.join([part async for part in stream_stehouwer_hybrid_response(
            'attached /crypto-trial',intent_prompt='/crypto-trial')])
        with patch.object(ToolRegistry,'execute_tool',return_value=self.status('not_registered')) as run:
            result=asyncio.run(collect());self.assertIn('not registered',result.lower());run.assert_called_once()
        with (patch('core.hybrid_reasoning_engine.audit_prompt_safety',return_value=(False,'fixture refusal')),
            patch.object(ToolRegistry,'execute_tool') as run):
            self.assertIn('Refusal',asyncio.run(collect()));run.assert_not_called()

    def test_14_registry_preserves_preview_diagnostic_flags_and_bad_args(self):
        with patch.dict(os.environ,{'AI_BS_ENABLE_CHAT_TOOL_BRIDGE':'0'}):
            names={row['name'] for row in ToolRegistry.get_tool_declarations()}
            self.assertIn('get_crypto_trial_status',names);self.assertIn('preview_crypto_spot',names)
            self.assertTrue(names.isdisjoint(_BS_CHAT_DIAGNOSTIC_NAMES))
        with patch('tools.bs_chat_tool_bridge.bs_chat_bridge.execute_tool') as run:
            for args in ({'path':'PRIVATE_SENTINEL'},{'account':'x'},[],None):
                self.assertNotEqual(ToolRegistry.execute_tool('get_crypto_trial_status',args).get('status'),'qualification')
            run.assert_not_called()

    def test_15_registry_anonymous_denied(self):
        with patch('tools.bs_chat_tool_bridge.current_memory_principal',return_value=None):
            result=ToolRegistry.execute_tool('get_crypto_trial_status',{})
            self.assertEqual(result['status'],'denied')
            self.assertNotIn('account',result);self.assertNotIn('path',result)


if __name__=='__main__':unittest.main()
