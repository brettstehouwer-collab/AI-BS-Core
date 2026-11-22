"""Ten integrated synthetic store/bridge/HTTP/chat cases; auth resolver is a fixture."""
import asyncio,json,sqlite3,unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.trading_router import router
from tools.bs_chat_tool_bridge import BSChatToolBridge
from core.crypto_trial_registry import TrialRuntimeRegistry
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from core.crypto_trial_status_chat import crypto_trial_status_reply
from tests.test_crypto_protective_lifecycle_smoke import ProtectiveLifecycleSmoke

class ProtectiveMountedSmoke(unittest.TestCase):
 def setUp(self):
  self.f=ProtectiveLifecycleSmoke();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.principal='local_admin';token=bind_memory_principal(self.principal)
  try:self.registry=TrialRuntimeRegistry.create(self.f.parent,'mounted-registry',runtime=self.f.owner,principal=self.principal)
  finally:reset_memory_principal(token)
  self.bridge=BSChatToolBridge(crypto_trial_registry=self.registry)
  self.addCleanup(patch.stopall)
  patch('tools.bs_chat_tool_bridge.bs_chat_bridge',self.bridge).start()
  patch('security.host_control_access.get_admin_principal',side_effect=lambda key,authorization:self.principal if key=='fixture-admin' else None).start()
  app=FastAPI();app.include_router(router);self.client=TestClient(app);self.addCleanup(self.client.close)
 def get(self,suffix=''):
  return self.client.get('/api/trading/protective-review'+suffix,headers={'x-admin-key':'fixture-admin'})
 def draft(self):self.f.buy();return self.f.prepare()
 def tables(self):
  with sqlite3.connect(self.f.owner.root/'accounting.sqlite3') as db:return db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
 def held(self,value):
  for key in ('native_order_accepted','child_mapping_verified','full_position_protection_verified','live_dispatch_enabled','ready_for_live','account_accessed'):self.assertIs(value[key],False)
  self.assertEqual(value['orders_sent'],0)
 def test_01_missing_registry_remains_absent(self):
  absent=self.f.parent/'missing';self.bridge.crypto_trial_registry=TrialRuntimeRegistry(absent)
  response=self.get();self.assertEqual(response.status_code,200);self.assertEqual(response.json()['status'],'not_registered');self.assertFalse(absent.exists())
 def test_02_no_draft_does_not_change_schema_or_financial_state(self):
  before=self.f.owner.coordinator.snapshot();tables=self.tables();response=self.get()
  self.assertEqual(response.status_code,200);self.assertEqual(response.json()['status'],'not_prepared');self.assertEqual(self.tables(),tables);self.assertEqual(self.f.owner.coordinator.snapshot(),before)
 def test_03_actual_draft_through_http_bridge_registry(self):
  self.draft();before=self.f.owner.coordinator.snapshot();value=self.get().json()
  self.assertEqual(value['status'],'qualification');self.assertEqual(value['draft_count'],1);self.assertEqual(value['observed_state'],'UNSIGNED_DRAFT');self.held(value);self.assertEqual(before,self.f.owner.coordinator.snapshot())
 def test_04_actual_chat_tool_registry_path(self):
  self.draft();token=bind_memory_principal('local_admin')
  try:result=asyncio.run(crypto_trial_status_reply({'user_prompt':'/crypto-protection status'}))
  finally:reset_memory_principal(token)
  self.assertIsInstance(result,dict);self.assertIn('response',result);self.assertIn('UNSIGNED_DRAFT',result['response']);self.assertIn('held',result['response'].lower())
 def test_05_anonymous_before_store_review(self):
  with patch.object(self.registry,'protective_review',wraps=self.registry.protective_review) as call:
   self.assertEqual(self.client.get('/api/trading/protective-review').status_code,403);call.assert_not_called()
 def test_06_query_before_store_review(self):
  with patch.object(self.registry,'protective_review',wraps=self.registry.protective_review) as call:
   self.assertEqual(self.get('?path=C:/private').status_code,422);call.assert_not_called()
 def test_07_wrong_owner_denied_without_closing_owner(self):
  self.principal='firebase:fixture:other';self.assertEqual(self.get().status_code,403);self.assertFalse(self.f.owner._closed)
 def test_08_closed_owner_reopens_without_creating_draft(self):
  self.draft();self.f.owner.close();value=self.get().json();self.assertEqual(value['status'],'qualification');self.assertEqual(value['draft_count'],1);self.held(value)
 def test_09_pending_raw_is_held_without_interpretation(self):
  self.draft()
  with patch.object(self.f.life,'_interpret',side_effect=RuntimeError('interruption')):
   with self.assertRaises(RuntimeError):self.f.capture('ack','pending',self.f.ack())
  value=self.get().json();self.assertEqual(value['status'],'held');self.assertEqual(value['pending_evidence_count'],1);self.assertEqual(value['observed_state'],'UNSIGNED_DRAFT');self.held(value)
 def test_10_corrupt_retained_bytes_are_unavailable_not_leaked(self):
  self.draft();self.f.capture('ack','receipt',self.f.ack())
  with self.f.owner.coordinator._tx() as db:db.execute("UPDATE aibs_protective_inputs SET raw_response=?",(b'PRIVATE_CORRUPT_BODY',))
  response=self.get();self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE_CORRUPT_BODY',response.text)
