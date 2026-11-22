"""Offline native writer regressions: synthetic transport, routes and documents only.

No app startup, production listener, credential store or personal document access.
Run with Python -B. AIBS_TEST_ROOT optionally selects a retained source checkout.
"""
import ast
import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

ROOT = Path(os.environ.get('AIBS_TEST_ROOT', r'C:\AI-BS'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts' / 'tests'))
from native_studio.screenplay_client import DraftSession, ScreenplayClient, ScreenplayError


def metadata(epoch=4, branch='main', initialized=True, **changes):
    value = dict(initialized=initialized, workflow_revision=epoch,
                 active_branch=branch, pending_operation=None)
    value.update(changes)
    return value


def snapshot(content='original', revision='r1', **workflow):
    return dict(project='Fixture', content=content, revision=revision, **workflow)


def acknowledgment(revision='r2', epoch=5, **changes):
    value = dict(status='success', project='Fixture', revision=revision,
                 **metadata(epoch))
    value.update(changes)
    return value


class NativeWorkflowTests(unittest.TestCase):
    def test_invalid_workflow_read_is_rejected_before_gui_delivery(self):
        client = ScreenplayClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=snapshot(initialized=True))))
        with self.assertRaises(ScreenplayError):
            client.read('Fixture')

    def setUp(self):
        self.headers = patch('native_studio.screenplay_client.local_service_headers',
                             return_value={'X-Admin-Key': 'offline-fixture-only'})
        self.headers.start()
        self.addCleanup(self.headers.stop)

    def session(self, workflow=None):
        value = DraftSession()
        value.load(snapshot(**(metadata() if workflow is None else workflow)))
        return value

    def test_loaded_workflow_state_survives_in_native_session(self):
        value = self.session()
        self.assertEqual(value.workflow_revision, 4)
        self.assertEqual(value.active_branch, 'main')
        self.assertIs(value.initialized, True)

    def test_save_sends_loaded_workflow_epoch_including_zero(self):
        calls = []
        def handler(request):
            sent = json.loads(request.content)
            calls.append(sent)
            epoch = sent['expected_workflow_revision']
            return httpx.Response(200, json=acknowledgment(
                epoch=epoch + 1 if epoch else 0, initialized=bool(epoch)))
        client = ScreenplayClient(transport=httpx.MockTransport(handler))
        for epoch in (4, 0):
            client.save('Fixture', 'new', 'r1', expected_workflow_revision=epoch)
        self.assertEqual([entry['expected_workflow_revision'] for entry in calls], [4, 0])
        self.assertEqual([entry['expected_revision'] for entry in calls], ['r1', 'r1'])

    def test_partial_or_malformed_workflow_never_replaces_loaded_baseline(self):
        invalid = [
            {'initialized': True}, {'workflow_revision': 4},
            metadata(initialized='yes'), metadata(epoch=True), metadata(epoch=-1),
            metadata(epoch=1.5), metadata(branch=''),
            metadata(epoch=3, initialized=False), metadata(pending_operation={'id': 'pending'}),
        ]
        for workflow in invalid:
            with self.subTest(workflow=workflow):
                value = self.session()
                with self.assertRaises(ScreenplayError):
                    value.load(snapshot('replacement', 'r9', **workflow))
                self.assertEqual((value.content, value.baseline, value.revision),
                                 ('original', 'original', 'r1'))

    def test_confirmed_initialized_save_advances_epoch_once(self):
        value = self.session()
        value.content = 'newer edits'
        value.saved('submitted snapshot', acknowledgment())
        self.assertEqual(value.workflow_revision, 5)
        self.assertEqual(value.revision, 'r2')
        self.assertEqual(value.baseline, 'submitted snapshot')
        self.assertEqual(value.content, 'newer edits')
        self.assertTrue(value.dirty)

    def test_invalid_acknowledgments_never_advance_baseline(self):
        invalid = [
            {'status': 'success', 'project': 'Fixture', 'revision': 'r2'},
            acknowledgment(epoch=4), acknowledgment(epoch=6),
            acknowledgment(active_branch='other'), acknowledgment(project='Other'),
            acknowledgment(initialized=False), acknowledgment(workflow_revision=True),
            acknowledgment(pending_operation={'id': 'pending'}),
        ]
        for response in invalid:
            with self.subTest(response=response):
                value = self.session()
                value.content = 'new'
                with self.assertRaises(ScreenplayError):
                    value.saved('new', response)
                self.assertEqual((value.revision, value.baseline), ('r1', 'original'))
                self.assertTrue(value.dirty)

    def test_unchanged_acknowledgment_keeps_revision_and_epoch(self):
        value = self.session()
        value.load(snapshot('original\r\n', **metadata()))
        value.content = 'original\n'
        value.saved('original\n', acknowledgment('r1', 4, unchanged=True))
        self.assertEqual((value.revision, value.workflow_revision), ('r1', 4))
        self.assertFalse(value.dirty)
        invalid = self.session()
        with self.assertRaises(ScreenplayError):
            invalid.saved('original', acknowledgment('r2', 4, unchanged=True))
        self.assertEqual(invalid.revision, 'r1')

    def test_uninitialized_save_keeps_epoch_zero(self):
        value = self.session(metadata(0, initialized=False))
        value.content = 'new'
        value.saved('new', acknowledgment(epoch=0, initialized=False))
        self.assertEqual(value.workflow_revision, 0)
        self.assertIs(value.initialized, False)
        self.assertEqual(value.baseline, 'new')

    def test_legacy_reads_and_confirmed_legacy_saves_remain_supported(self):
        value = self.session({})
        self.assertIsNone(value.workflow_revision)
        value.content = 'new'
        value.saved('new', dict(status='success', project='Fixture', revision='r2'))
        self.assertIsNone(value.workflow_revision)
        self.assertEqual(value.baseline, 'new')

    def _view(self, response):
        """Execute the actual save controller with in-memory callback/editor fakes."""
        tree = ast.parse((ROOT / 'native_studio' / 'screenwriting_view.py').read_text(encoding='utf-8'))
        view_class = next(node for node in tree.body
                          if isinstance(node, ast.ClassDef) and node.name == 'ScreenwritingNativeView')
        method = next(node for node in view_class.body
                      if isinstance(node, ast.FunctionDef) and node.name == '_save_script')
        method.decorator_list = []
        imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)
                   and node.module == 'native_studio.screenplay_client']
        scope = {}
        exec(compile(ast.Module(body=[*imports, method], type_ignores=[]), '<actual-native-save>', 'exec'), scope)
        calls = []
        def transport(request):
            calls.append(request)
            return response
        value = self.session()
        state = SimpleNamespace(_writer_busy=False, _draft=value, _adapt_job=None,
                                editor=SimpleNamespace(toPlainText=lambda: 'new'),
                                _writer_client=ScreenplayClient(transport=httpx.MockTransport(transport)),
                                _preserve_native_draft=lambda: True,
                                _sync_native_project_selection=lambda: None,
                                errors=[], statuses=[])
        state._writer_error = state.errors.append
        state._writer_status = state.statuses.append
        def native_io(work, success, failure):
            try:
                result = work()
            except Exception as error:
                failure(str(error))
            else:
                # Result callbacks are outside the transport exception boundary.
                success(result)
        state._native_io = native_io
        return state, calls, scope['_save_script']

    def test_http500_keeps_draft_and_blocks_second_dispatch(self):
        state, calls, save = self._view(httpx.Response(500))
        save(state)
        save(state)
        self.assertEqual(len(calls), 1)
        self.assertIs(state._draft.uncertain, True)
        self.assertEqual((state._draft.content, state._draft.baseline), ('new', 'original'))
        self.assertTrue(state.errors)

    def test_invalid_success_ack_is_retained_through_actual_view_callback(self):
        bad = acknowledgment(active_branch='wrong-branch')
        state, calls, save = self._view(httpx.Response(200, json=bad))
        save(state)
        self.assertEqual(len(calls), 1)
        self.assertIs(state._draft.uncertain, True)
        self.assertEqual((state._draft.content, state._draft.baseline), ('new', 'original'))
        self.assertTrue(state.errors)


class NativeExportInteropTests(unittest.TestCase):
    def setUp(self):
        headers = patch('native_studio.screenplay_client.local_service_headers',
                        return_value={'X-Admin-Key': 'offline-fixture-only'})
        headers.start();self.addCleanup(headers.stop)

    def test_pdf_and_fdx_exports_send_loaded_revision_without_writing_or_rebasing(self):
        for fmt, payload in [('pdf', b'%PDF-1.4 synthetic'), ('fdx', b'<FinalDraft/>')]:
            with self.subTest(fmt=fmt):
                calls=[]
                def handler(request):
                    calls.append(request)
                    self.assertEqual(request.method, 'GET')
                    self.assertEqual(request.headers['X-Admin-Key'], 'offline-fixture-only')
                    if request.url.path.endswith('/read'):
                        return httpx.Response(200, json=snapshot())
                    self.assertEqual(request.url.params['project_name'], 'Fixture')
                    if request.url.params.get('expected_revision') != 'r1':
                        return httpx.Response(428, json={'detail':'A current export revision is required.'})
                    return httpx.Response(200, content=payload)
                client=ScreenplayClient(transport=httpx.MockTransport(handler))
                self.assertEqual(client.export('Fixture',fmt,'r1'),payload)
                self.assertEqual(len(calls),3)
                self.assertEqual(calls[1].url.params['expected_revision'],'r1')

    def test_stale_or_foreign_initial_read_never_dispatches_export(self):
        for value in (snapshot(revision='r2'), {**snapshot(),'project':'Other'}):
            calls=[]
            def handler(request):
                calls.append(request)
                return httpx.Response(200,json=value)
            client=ScreenplayClient(transport=httpx.MockTransport(handler))
            with self.assertRaises(ScreenplayError):client.export('Fixture','pdf','r1')
            self.assertEqual(len(calls),1)
            self.assertTrue(calls[0].url.path.endswith('/read'))

    def test_foreign_owner_export_denial_is_not_retried_or_returned_as_bytes(self):
        calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(200,json=snapshot()) if request.url.path.endswith('/read') else httpx.Response(403)
        client=ScreenplayClient(transport=httpx.MockTransport(handler))
        with self.assertRaises(ScreenplayError):client.export('Fixture','fdx','r1')
        self.assertEqual(len(calls),2)
        self.assertTrue(all(request.method=='GET' for request in calls))

    def test_revision_change_during_export_still_refuses_returned_payload(self):
        reads=0;calls=[]
        def handler(request):
            nonlocal reads
            calls.append(request)
            if request.url.path.endswith('/read'):
                reads+=1;return httpx.Response(200,json=snapshot(revision='r1' if reads==1 else 'r2'))
            return httpx.Response(200,content=b'%PDF-1.4 synthetic')
        client=ScreenplayClient(transport=httpx.MockTransport(handler))
        with self.assertRaisesRegex(ScreenplayError,'changed during export'):client.export('Fixture','pdf','r1')
        self.assertEqual(len(calls),3)


class ActualRouteWorkflowTests(unittest.TestCase):
    def setUp(self):
        # Import a fixture, not the production FastAPI app or router module.
        from test_creation_project_lifecycle import ProjectLifecycleTests
        self.fixture = ProjectLifecycleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.scope = self.fixture.scope
        self.name = self.fixture.project.name
        initial = self.scope['read_screenplay'](self.name)
        self.scope['_workflow_call'](self.fixture.project, 'create_branch',
                                     'alternate', initial['revision'], 0)
        self.database = self.fixture.project / '.writing-workflows.sqlite3'
        self._integrity()
        self.addCleanup(self._integrity)
        self.headers = patch('native_studio.screenplay_client.local_service_headers',
                             return_value={'X-Admin-Key': 'offline-fixture-only'})
        self.headers.start()
        self.addCleanup(self.headers.stop)
        self.payloads = []
        def handler(request):
            from fastapi import HTTPException
            try:
                if request.method == 'GET':
                    result = self.scope['read_screenplay'](request.url.params['project_name'])
                else:
                    payload = json.loads(request.content)
                    self.payloads.append(payload)
                    result = self.scope['write_screenplay'](SimpleNamespace(
                        preserve_unchanged_bytes=True, **payload))
                return httpx.Response(200, json=result)
            except HTTPException as error:
                return httpx.Response(error.status_code, json={'detail': error.detail})
        self.client = ScreenplayClient(transport=httpx.MockTransport(handler))

    def _integrity(self):
        with sqlite3.connect(f'{self.database.as_uri()}?mode=ro', uri=True) as connection:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchall(), [('ok',)])

    def test_two_native_saves_use_acknowledged_epoch_with_actual_routes(self):
        value = DraftSession()
        value.load(self.client.read(self.name))
        for text in ('INT. LAB - DAY\nFirst synthetic edit.\n', 'INT. LAB - DAY\nSecond synthetic edit.\n'):
            value.content = text
            result = self.client.save(self.name, text, value.revision,
                                      expected_workflow_revision=value.workflow_revision)
            value.saved(text, result)
        self.assertEqual([p['expected_workflow_revision'] for p in self.payloads], [1, 2])
        self.assertEqual(value.workflow_revision, 3)
        self.assertEqual(self.fixture.script.read_bytes(), text.encode('utf-8'))

    def test_stale_workflow_refusal_preserves_exact_manuscript_bytes(self):
        value = self.client.read(self.name)
        before = self.fixture.script.read_bytes()
        with self.assertRaises(ScreenplayError):
            self.client.save(self.name, 'REPLACEMENT', value['revision'], expected_workflow_revision=0)
        self.assertEqual(self.fixture.script.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
