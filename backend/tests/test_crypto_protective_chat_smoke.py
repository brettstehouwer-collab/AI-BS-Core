"""Read-only protection consumer checks; synthetic registry only."""
import asyncio
import copy
import os
import unittest
from unittest.mock import patch
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal, current_memory_principal
from tools.bs_chat_tool_bridge import BSChatToolBridge
from tools.tool_registry import ToolRegistry
from core.crypto_trial_status_chat import crypto_trial_status_reply


def result(**changes):
    value=dict(status='qualification',draft_count=1,pending_evidence_count=0,
        observed_state='UNSIGNED_DRAFT',quarantined=False,native_order_accepted=False,
        child_mapping_verified=False,full_position_protection_verified=False,
        live_dispatch_enabled=False,ready_for_live=False,account_accessed=False,orders_sent=0)
    value.update(changes);return value


class Registry:
    def __init__(self,value=None):self.value=result() if value is None else value;self.calls=[]
    def protective_review(self):
        self.calls.append(current_memory_principal());return copy.deepcopy(self.value)


class ProtectiveChatSmoke(unittest.TestCase):
    def call(self,value=None,args=None):
        registry=Registry(value);bridge=BSChatToolBridge(crypto_trial_registry=registry)
        token=bind_memory_principal('local_admin')
        try:return bridge.execute_tool('get_crypto_protective_review',{} if args is None else args),registry
        finally:reset_memory_principal(token)

    def reply(self,text=None,**body):
        if text is not None:body['user_prompt']=text
        return asyncio.run(crypto_trial_status_reply(body))

    def test_01_anonymous_before_registry(self):
        registry=Registry();bridge=BSChatToolBridge(crypto_trial_registry=registry)
        self.assertEqual(bridge.execute_tool('get_crypto_protective_review',{}),{'status':'denied'})
        self.assertEqual(registry.calls,[])

    def test_02_direct_method_authorizes(self):
        registry=Registry();bridge=BSChatToolBridge(crypto_trial_registry=registry)
        with self.assertRaises(PermissionError):bridge.get_crypto_protective_review()
        self.assertEqual(registry.calls,[])

    def test_03_authorized_principal_and_exact_result(self):
        reply,registry=self.call();self.assertEqual(reply,result());self.assertEqual(registry.calls,['local_admin'])

    def test_04_arguments_rejected_without_io(self):
        for key in ('path','root','account','recover','stop_id','force'):
            reply,registry=self.call(args={key:'PRIVATE_SENTINEL'})
            self.assertEqual(reply['status'],'error');self.assertEqual(registry.calls,[])

    def test_05_extra_private_fields_refused(self):
        reply,_=self.call(result(path='PRIVATE_SENTINEL'))
        self.assertEqual(reply['status'],'error');self.assertNotIn('PRIVATE_SENTINEL',str(reply))

    def test_06_authority_claims_refused(self):
        for key in ('native_order_accepted','child_mapping_verified','full_position_protection_verified',
                    'live_dispatch_enabled','ready_for_live','account_accessed'):
            reply,_=self.call(result(**{key:True}));self.assertEqual(reply['status'],'error')

    def test_07_bad_counts_and_states_refused(self):
        for change in ({'orders_sent':False},{'draft_count':True},{'pending_evidence_count':-1},
                       {'observed_state':'PRIVATE_SENTINEL'},{'status':'LIVE'}):
            reply,_=self.call(result(**change));self.assertEqual(reply['status'],'error')

    def test_08_provider_exception_sanitized(self):
        registry=Registry();registry.protective_review=lambda:(_ for _ in ()).throw(RuntimeError('PRIVATE_SENTINEL'))
        bridge=BSChatToolBridge(crypto_trial_registry=registry);token=bind_memory_principal('local_admin')
        try:reply=bridge.execute_tool('get_crypto_protective_review',{})
        finally:reset_memory_principal(token)
        self.assertEqual(reply['status'],'error');self.assertNotIn('PRIVATE_SENTINEL',str(reply))

    def test_09_declaration_available_without_diagnostics(self):
        with patch.dict(os.environ,{'AI_BS_CHAT_DIAGNOSTICS_ENABLED':'0'}):
            rows=[x for x in ToolRegistry.get_tool_declarations() if x['name']=='get_crypto_protective_review']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['parameters'],
            {'type':'object','properties':{},'required':[],'additionalProperties':False})

    def test_10_registry_routes_only_empty_args(self):
        from tools.bs_chat_tool_bridge import bs_chat_bridge
        with patch.object(bs_chat_bridge,'execute_tool',return_value=result()) as run:
            self.assertEqual(ToolRegistry.execute_tool('get_crypto_protective_review',{}),result())
            run.assert_called_once_with('get_crypto_protective_review',{})

    def test_11_current_exact_commands_and_pending_disclosure(self):
        with patch.object(ToolRegistry,'execute_tool',return_value=result(status='held',pending_evidence_count=2)) as run:
            for text in ('/crypto-protection',' /CRYPTO-PROTECTION STATUS  '):
                reply=self.reply(text);self.assertIsNotNone(reply)
                self.assertIn('qualification',reply['response'].lower())
                self.assertIn('not automatically replayed',reply['response'])
                self.assertIn('Live trading remains held',reply['response'])
            self.assertEqual(run.call_count,2);run.assert_called_with('get_crypto_protective_review',{})

    def test_12_invalid_tail_usage_no_tools(self):
        with patch.object(ToolRegistry,'execute_tool') as run:
            for text in ('/crypto-protection recover','/crypto-protection status extra','/crypto-protection {}'):
                self.assertIn('/crypto-protection status',self.reply(text)['response'])
            run.assert_not_called()

    def test_13_history_embedded_prefix_never_dispatch(self):
        with patch.object(ToolRegistry,'execute_tool') as run:
            for body in ({'messages':[{'role':'user','content':'/crypto-protection'}]},
                {'user_prompt':'hello','prompt':'/crypto-protection'},
                {'user_prompt':'/crypto-protectionevil'},{'prompt':'explain /crypto-protection'}):
                self.assertIsNone(self.reply(**body))
            run.assert_not_called()

    def test_14_chat_failure_never_echoes_or_claims_protection(self):
        for value in (result(path='PRIVATE_SENTINEL'),result(native_order_accepted=True),None):
            with patch.object(ToolRegistry,'execute_tool',return_value=value):
                reply=self.reply('/crypto-protection');self.assertIsNotNone(reply)
                self.assertIn('unavailable',reply['response'].lower());self.assertNotIn('PRIVATE_SENTINEL',str(reply))
        with patch.object(ToolRegistry,'execute_tool',side_effect=RuntimeError('PRIVATE_SENTINEL')):
            self.assertNotIn('PRIVATE_SENTINEL',str(self.reply('/crypto-protection')))

    def test_15_existing_trial_command_unchanged(self):
        from core.crypto_trial_status_contract import trial_status
        with patch.object(ToolRegistry,'execute_tool',return_value=trial_status('qualification',entry_held=True)) as run:
            reply=self.reply('/crypto-trial status');self.assertEqual(reply['model'],'crypto-trial-status')
            self.assertIn('cutoff is latched',reply['response']);run.assert_called_once_with('get_crypto_trial_status',{})


if __name__=='__main__':unittest.main()
