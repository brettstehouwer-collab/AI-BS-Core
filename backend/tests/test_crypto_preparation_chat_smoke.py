"""Fifteen retained-preparation chat/bridge cases; synthetic provider only."""
import asyncio
import copy
import os
import unittest
from unittest.mock import patch

from core.personal_memory_scope import bind_memory_principal,reset_memory_principal,current_memory_principal
from core.crypto_trial_status_chat import crypto_trial_status_reply
from tools.bs_chat_tool_bridge import BSChatToolBridge
from tools.tool_registry import ToolRegistry,_BS_CHAT_DIAGNOSTIC_NAMES


def result(status='held_preparation',**changes):
    from core.crypto_preparation_status import preparation_status
    return dict(preparation_status(status),**changes)


class Reader:
    def __init__(self,value=None):self.value=result() if value is None else value;self.calls=[]
    def status(self):
        self.calls.append(current_memory_principal());return copy.deepcopy(self.value)


class PreparationChatSmoke(unittest.TestCase):
    def setUp(self):
        self.token=bind_memory_principal('local_admin');self.addCleanup(reset_memory_principal,self.token)

    def bridge(self,value=None):
        reader=Reader(value);return BSChatToolBridge(crypto_preparation_reader=reader),reader

    def reply(self,text=None,**body):
        if text is not None:body['user_prompt']=text
        return asyncio.run(crypto_trial_status_reply(body))

    def test_01_anonymous_before_preparation_reader(self):
        bridge,reader=self.bridge()
        with patch('tools.bs_chat_tool_bridge.current_memory_principal',return_value=None):
            self.assertEqual(bridge.execute_tool('get_crypto_preparation_status',{}),{'status':'denied'})
        self.assertEqual(reader.calls,[])

    def test_02_direct_method_authorizes(self):
        bridge,reader=self.bridge()
        with patch('tools.bs_chat_tool_bridge.current_memory_principal',return_value=None):
            with self.assertRaises(PermissionError):bridge.get_crypto_preparation_status()
        self.assertEqual(reader.calls,[])

    def test_03_authorized_principal_and_exact_closed_status(self):
        bridge,reader=self.bridge()
        self.assertEqual(bridge.execute_tool('get_crypto_preparation_status',{}),result())
        self.assertEqual(reader.calls,['local_admin'])

    def test_04_invalid_args_never_read(self):
        bridge,reader=self.bridge()
        for args in ({'path':'PRIVATE_SENTINEL'},{'root':'x'},{'account':'x'},{'force':True},{'initialize':True},[],None):
            with self.subTest(args=args):self.assertEqual(bridge.execute_tool('get_crypto_preparation_status',args)['status'],'error')
        self.assertEqual(reader.calls,[])

    def test_05_private_extra_fields_refused(self):
        for key in ('account','path','snapshot_sha256','seed_usdt','balance'):
            bridge,_=self.bridge(result(**{key:'PRIVATE_SENTINEL'}))
            reply=bridge.execute_tool('get_crypto_preparation_status',{})
            self.assertEqual(reply['status'],'error');self.assertNotIn('PRIVATE_SENTINEL',str(reply))

    def test_06_optimistic_authority_flags_refused(self):
        for key in ('fresh_authority','external_funds_reserved','account_identity_verified',
                'native_order_accepted','live_dispatch_enabled','ready_for_live'):
            bridge,_=self.bridge(result(**{key:True}))
            self.assertEqual(bridge.execute_tool('get_crypto_preparation_status',{})['status'],'error')

    def test_07_malformed_states_types_and_allocation_refused(self):
        for value in (result(status='selected',local_seed_allocated=True),result(orders_sent=False),
                result(test_only=1),dict(result(),status='LIVE'),None,[]):
            bridge,_=self.bridge(value if value is not None else {'status':'unknown'})
            self.assertEqual(bridge.execute_tool('get_crypto_preparation_status',{})['status'],'error')

    def test_08_provider_exception_sanitized(self):
        bridge,reader=self.bridge();reader.status=lambda:(_ for _ in ()).throw(RuntimeError('PRIVATE_SENTINEL'))
        reply=bridge.execute_tool('get_crypto_preparation_status',{})
        self.assertEqual(reply['status'],'error');self.assertNotIn('PRIVATE_SENTINEL',str(reply))

    def test_09_declarations_closed_and_old_tools_preserved(self):
        from core.crypto_trial_status_chat import crypto_preparation_status_declarations
        declaration=crypto_preparation_status_declarations()[0]
        self.assertEqual(declaration['name'],'get_crypto_preparation_status')
        self.assertEqual(declaration['parameters'],{'type':'object','properties':{},'required':[],'additionalProperties':False})
        with patch.dict(os.environ,{'AI_BS_ENABLE_CHAT_TOOL_BRIDGE':'0'}):
            names={row['name'] for row in ToolRegistry.get_tool_declarations()}
        self.assertTrue({'get_crypto_preparation_status','get_crypto_trial_status','get_crypto_protective_review','preview_crypto_spot'}<=names)
        self.assertTrue(names.isdisjoint(_BS_CHAT_DIAGNOSTIC_NAMES))

    def test_10_registry_dispatch_only_closed_args(self):
        from tools.bs_chat_tool_bridge import bs_chat_bridge
        with patch.object(bs_chat_bridge,'execute_tool',return_value=result()) as run:
            self.assertEqual(ToolRegistry.execute_tool('get_crypto_preparation_status',{}),result())
            run.assert_called_once_with('get_crypto_preparation_status',{})
            run.reset_mock()
            for args in ({'path':'PRIVATE_SENTINEL'},[],None):
                self.assertNotEqual(ToolRegistry.execute_tool('get_crypto_preparation_status',args).get('status'),'held_preparation')
            run.assert_not_called()

    def test_11_explicit_command_reports_dated_held_without_leakage(self):
        bridge,reader=self.bridge()
        with patch('tools.bs_chat_tool_bridge.bs_chat_bridge',bridge):
            for command in ('/crypto-preparation',' /CRYPTO-PREPARATION STATUS '):
                reply=self.reply(command);text=reply['response'].lower()
                self.assertEqual(reply['model'],'crypto-preparation-status')
                self.assertTrue('retained' in text or 'dated' in text)
                self.assertIn('external funds',text);self.assertIn('not reserved',text)
                self.assertIn('unverified',text);self.assertIn('live trading remains held',text)
                self.assertNotIn('PRIVATE_SENTINEL',text)
        self.assertEqual(reader.calls,['local_admin','local_admin'])

    def test_12_bad_command_tails_usage_no_provider(self):
        with patch.object(ToolRegistry,'execute_tool') as run:
            for tail in ('initialize','{}','status extra','2','verify --force'):
                reply=self.reply('/crypto-preparation '+tail)
                self.assertIn('/crypto-preparation status',reply['response'])
            run.assert_not_called()

    def test_13_history_attachments_and_prefix_never_authorize(self):
        with patch.object(ToolRegistry,'execute_tool') as run:
            for body in ({'messages':[{'role':'user','content':'/crypto-preparation status'}]},
                    {'user_prompt':'hello','prompt':'/crypto-preparation'},
                    {'attachments':[{'text':'/crypto-preparation status'}]},
                    {'user_prompt':'Discuss /crypto-preparation status'},{'user_prompt':'/crypto-preparationevil'}):
                self.assertIsNone(self.reply(**body))
            run.assert_not_called()

    def test_14_normal_hybrid_and_guards_no_model(self):
        from core.bs_chat_provider import bs_chat_reply
        from core.hybrid_reasoning_engine import stream_stehouwer_hybrid_response
        bridge,reader=self.bridge()
        async def collect():return ''.join([part async for part in stream_stehouwer_hybrid_response(
            '/crypto-preparation status',intent_prompt='/crypto-preparation status')])
        with (patch('tools.bs_chat_tool_bridge.bs_chat_bridge',bridge),
                patch('core.bs_chat_provider.openai_completion',side_effect=AssertionError('model forbidden'))):
            normal=asyncio.run(bs_chat_reply({'user_prompt':'/crypto-preparation status','provider':'local'}))
            self.assertEqual(normal['model'],'crypto-preparation-status')
            self.assertIn('held',asyncio.run(collect()).lower())
            for extra in ({'plan_only':True},{'mode':'review'},{'execution_backend':'windows_vm'}):
                guarded=asyncio.run(bs_chat_reply(dict(user_prompt='/crypto-preparation status',**extra)))
                self.assertNotEqual(guarded['model'],'crypto-preparation-status')
        self.assertEqual(reader.calls,['local_admin','local_admin'])

    def test_15_old_trial_and_protection_commands_unchanged(self):
        from core.crypto_trial_status_contract import trial_status
        from core.crypto_protective_review_contract import protective_review
        with patch.object(ToolRegistry,'execute_tool',return_value=trial_status('not_registered')) as run:
            self.assertEqual(self.reply('/crypto-trial status')['model'],'crypto-trial-status')
            run.assert_called_once_with('get_crypto_trial_status',{})
        with patch.object(ToolRegistry,'execute_tool',return_value=protective_review('not_registered')) as run:
            self.assertEqual(self.reply('/crypto-protection status')['model'],'crypto-protective-review')
            run.assert_called_once_with('get_crypto_protective_review',{})


if __name__=='__main__':unittest.main()
