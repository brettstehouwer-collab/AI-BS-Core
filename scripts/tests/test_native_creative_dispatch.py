"""Actual screenplay services, synthetic PDF/vault and controlled process identity."""
import ast
import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import BaseModel, StrictInt
from scripts.tests import test_chat_pdf_workflow as pdf
from scripts.tests import test_native_creative_adapter as identities
from security.native_creative_dispatch import CreativeDispatch
from security.native_creative_handoff import CreativeScope, HandoffDenied
from core.personal_memory_scope import current_memory_principal, bind_memory_principal, reset_memory_principal


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = pdf.PdfWorkflowFixture()
        self.fixture._setupAsyncioRunner()
        self.addCleanup(self.fixture._tearDownAsyncioRunner)
        self.addCleanup(self.fixture.doCleanups)
        self.fixture._callSetUp()
        self.identity = identities.AdapterTests()
        self.identity.setUp()
        self.addCleanup(self.identity.doCleanups)
        self.invocation = self.identity._invocation()
        self.adapter = self.identity.adapter
        self.adapter.register(self.invocation)
        self.source = self.fixture.stage()
        self.opening = self.fixture.import_source(self.source, name='Pipe Project')
        self.project = self.fixture.projects / 'Pipe Project'
        self.originals = {name: (self.project/name).read_bytes() for name in
                          ('original.pdf', 'source_packet.json', 'source_exports/layout.fdx', 'source_exports/layout.pdf')}
        ns = self.fixture.router_scope()
        ns.update(BaseModel=BaseModel, StrictInt=StrictInt)
        source = pdf.ROOT/'backend/routers/screenwriting_router.py'
        model = next(n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body
                     if isinstance(n, ast.ClassDef) and n.name == 'WriteScreenplayPayload')
        exec(compile(ast.Module(body=[model], type_ignores=[]), '<actual screenplay model>', 'exec'), ns)
        self.router = SimpleNamespace(**ns)
        self.dispatcher = self.new_dispatcher()
        self.sequence = 0

    def new_dispatcher(self, *, owner=pdf.OWNER, source_sha=None):
        self.scope = CreativeScope(owner, 'Pipe Project', self.opening['revision'],
            source_sha or self.source['source_sha256'], self.invocation.candidate_sha256)
        self.grant = self.identity.grants.issue(self.scope, self.invocation, auth_deadline=1000)
        return CreativeDispatch(self.adapter, self.invocation, self.router)

    def rpc(self, operation, payload):
        self.sequence += 1
        return self.dispatcher.dispatch({'version':1,'id':self.sequence,
            'operation':operation,'payload':payload})

    def redeem(self):
        value = self.rpc('redeem', {'grant':self.grant})
        self.assertEqual(value['status'], 200)
        self.identity.lookup.assert_not_called()

    def test_recovery_scope_is_server_bound_not_lease_or_candidate_bound(self):
        value=self.rpc('redeem', {'grant':self.grant})
        self.assertEqual(value['status'],200)
        expected=hashlib.sha256(json.dumps({'version':1,'owner':self.scope.owner,
            'project':self.scope.project,'source_sha256':self.scope.source_sha256},
            sort_keys=True,separators=(',',':')).encode('utf8')).hexdigest()
        self.assertEqual(value['body']['recovery_scope'],expected)
        self.assertNotIn(self.scope.owner,value['body']['recovery_scope'])
        self.assertEqual(len(value['body']['recovery_scope']),64)

    def test_actual_read_save_reopen_and_original_artifacts_preserved(self):
        self.redeem()
        view = self.rpc('read', {'project_name':'Pipe Project'})['body']
        before = view['revision']
        saved = self.rpc('save', {'project_name':'Pipe Project','content':view['content']+'\nSynthetic pipe edit.\n',
            'expected_revision':before})
        self.assertEqual(saved['status'],200)
        self.assertNotEqual(saved['body']['revision'], before)
        reopened = self.rpc('read', {'project_name':'Pipe Project'})['body']
        self.assertIn('Synthetic pipe edit.', reopened['content'])
        self.assertEqual(reopened['revision'], saved['body']['revision'])
        self.assertIsNone(current_memory_principal())
        for name, content in self.originals.items():
            self.assertEqual((self.project/name).read_bytes(),content)

    def test_actual_fdx_pdf_exports_have_verified_binary_hash_and_no_fallback(self):
        self.redeem()
        for operation, signature in (('export_fdx',b'<?xml'),('export_pdf',b'%PDF')):
            response = self.rpc(operation, {'project_name':'Pipe Project','layout':'source',
                'expected_revision':self.opening['revision']})
            self.assertEqual(response['status'],200)
            content = base64.b64decode(response['body_base64'],validate=True)
            self.assertTrue(content.startswith(signature))
            self.assertEqual(hashlib.sha256(content).hexdigest(),
                             response['headers']['x-ai-bs-artifact-sha256'])
        self.assertIsNone(current_memory_principal())

    def test_wrong_owner_and_substituted_source_are_terminal(self):
        for owner, digest in ((pdf.OTHER,None),(pdf.OWNER,'c'*64)):
            with self.subTest(owner=owner):
                # A fresh exact registered invocation for each independent denial.
                self.adapter.register(self.invocation)
                self.identity.now += 1
                self.dispatcher = self.new_dispatcher(owner=owner,source_sha=digest)
                self.sequence = 0
                self.redeem()
                with self.assertRaises(HandoffDenied): self.rpc('read',{'project_name':'Pipe Project'})
                self.assertNotIn(self.invocation,self.adapter._invocations)
                self.assertIsNone(current_memory_principal())

    def test_missing_and_stale_revisions_refused_without_saving(self):
        self.redeem()
        before = (self.project/'screenplay.fountain').read_bytes()
        for revision, expected in ((None,428),('stale',409)):
            response = self.rpc('save', {'project_name':'Pipe Project','content':'must not save',
                'expected_revision':revision})
            self.assertEqual(response['status'],expected)
        self.assertEqual((self.project/'screenplay.fountain').read_bytes(),before)
        self.assertIsNone(current_memory_principal())

    def test_expiry_is_checked_after_store_lock_acquisition(self):
        self.redeem()
        lock = self.router._PROJECT_STORE_LOCK
        identity = self.identity
        class ExpiresWhileWaiting:
            def __enter__(self):
                lock.acquire()
                identity.now += 301
            def __exit__(self,*args): lock.release()
        self.router._PROJECT_STORE_LOCK = ExpiresWhileWaiting()
        with self.assertRaises(HandoffDenied): self.rpc('read', {'project_name':'Pipe Project'})
        self.assertNotIn(self.invocation,self.adapter._invocations)

    def test_protocol_replay_and_extra_authority_fields_revoke(self):
        self.redeem()
        with self.assertRaises(HandoffDenied):
            self.rpc('read', {'project_name':'Pipe Project','owner':pdf.OWNER})
        self.assertNotIn(self.invocation,self.adapter._invocations)
        with self.assertRaises(HandoffDenied):
            self.dispatcher.dispatch({'version':1,'id':1,'operation':'redeem','payload':{'grant':self.grant}})

    def test_principal_is_restored_and_export_refusal_does_not_change_profile(self):
        self.redeem()
        token = bind_memory_principal('local_admin')
        try:
            response = self.rpc('export_pdf', {'project_name':'Pipe Project','layout':'invalid',
                'expected_revision':self.opening['revision']})
            self.assertEqual(response['status'],422)
            self.assertEqual(current_memory_principal(),'local_admin')
        finally:
            reset_memory_principal(token)

    def test_oversized_export_is_refused_without_truncation_or_alternate_export(self):
        from fastapi.responses import Response
        self.redeem()
        oversized = Response(content=b'x' * (7*1024*1024), media_type='application/pdf')
        with patch.object(self.router, 'export_pdf', return_value=oversized) as export, \
                patch.object(self.router, 'export_fdx', side_effect=AssertionError('No fallback')):
            response = self.rpc('export_pdf', {'project_name':'Pipe Project','layout':'source',
                'expected_revision':self.opening['revision']})
            self.assertEqual(response['status'],413)
            self.assertNotIn('body_base64', response)
            export.assert_called_once()
        self.assertIsNone(current_memory_principal())

    def test_same_request_identifier_cannot_be_replayed(self):
        self.redeem()
        with self.assertRaises(HandoffDenied):
            self.dispatcher.dispatch({'version':1,'id':1,'operation':'read',
                'payload':{'project_name':'Pipe Project'}})
        self.assertNotIn(self.invocation,self.adapter._invocations)

    def test_changed_project_is_refused_before_reading(self):
        self.redeem()
        with patch.object(self.router,'read_screenplay',side_effect=AssertionError('Do not read')):
            with self.assertRaises(HandoffDenied): self.rpc('read',{'project_name':'Other Project'})
        self.assertIsNone(current_memory_principal())


if __name__ == '__main__':
    unittest.main(verbosity=2)
