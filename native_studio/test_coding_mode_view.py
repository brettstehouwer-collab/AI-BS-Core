"""Offscreen native coding workflow checks using synthetic API responses."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import time
from PyQt6.QtWidgets import QApplication
from native_studio.coding_mode_view import CodingModeView


class Bus:
    def submit(self, fn, *args, on_result=None, on_error=None):
        try: value = fn(*args)
        except Exception as exc:
            if on_error: on_error(str(exc))
        else:
            if on_result: on_result(value)


class Service:
    def __init__(self): self.calls = []
    def request(self, method, path, payload):
        self.calls.append((method, path, payload))
        if path == '/mode/capabilities':
            return {'enabled': True, 'owner': 'synthetic', 'execution_available': False, 'blocked_reason': 'Qualified worker unavailable',
                    'trusted_local_available': True, 'supported_execution_backends': ['isolated', 'trusted_host']}
        if path.endswith('/preview'): return {'state': 'PREVIEW', 'review_digest': 'f'*64}
        return {'state': 'BLOCKED', 'verification_status': 'not_run'}


class CodingModeViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.service = Service(); self.view = CodingModeView(Bus(), service=self.service)
        self.addCleanup(self.view.close)

    def scope(self):
        self.view.objective.setText('Fix synthetic component')
        self.view.file_fields['editable'].setPlainText('frontend/x.jsx')
        self.view.file_fields['verification'].setPlainText('tests/x.mjs')
        self.view.check_fields['node_test'].setPlainText('tests/x.mjs')

    def test_initial_history_only_and_apply_disabled(self):
        self.assertEqual(self.service.calls, [('GET', '/mode/capabilities', None), ('GET', '/preparations', None)])
        self.assertIn('Qualified worker unavailable', self.view.capabilities.text())
        self.assertFalse(self.view.apply_button.isEnabled())

    def test_preview_then_prepare_requires_same_visible_scope(self):
        self.scope(); self.view.preview()
        self.assertEqual(self.service.calls[-1][1], '/preparations/preview')
        count = len(self.service.calls)
        self.view.objective.setText('changed objective'); self.view.prepare()
        self.assertEqual(len(self.service.calls), count)
        self.scope(); self.view.preview(); self.view.prepare()
        self.assertEqual(self.service.calls[-1][2]['review_digest'], 'f'*64)

    def test_proposal_requires_review_and_check_keeps_blocked(self):
        self.view.request_id.setText('a'*32); self.view.plan_id.setText('b'*32)
        count = len(self.service.calls); self.view.implement()
        self.assertEqual(len(self.service.calls), count)
        self.view.proposal_id.setText('c'*32); self.view.check_candidate()
        self.assertEqual(self.service.calls[-1][1], '/mode/executions')
        self.assertIn('BLOCKED', self.view.status.text())
        self.assertFalse(self.view.apply_button.isEnabled())

    def test_cancel_uses_selected_ids_and_no_replay_on_close(self):
        self.view.request_id.setText('a'*32); self.view.plan_id.setText('b'*32)
        self.view._busy = True; self.view.cancel()
        self.assertTrue(self.service.calls[-1][1].endswith('/plans/'+'b'*32+'/cancel'))
        count = len(self.service.calls); self.view.close()
        self.assertEqual(len(self.service.calls), count)

    def test_human_summary_and_optional_evidence(self):
        value = {'state': 'BLOCKED', 'blocked_reason': 'VM unavailable', 'verification_status': 'not_run',
                 'diff': '-old\n+new'}
        self.view._record = value; self.view._render(value)
        self.assertIn('VM unavailable', self.view.output.toPlainText())
        self.assertIn('-old\n+new', self.view.output.toPlainText())
        self.view._render({'review_diff': '-candidate old\n+candidate new',
                           'static_checks': [{'path': 'app.py', 'status': 'passed'}]})
        self.assertIn('+candidate new', self.view.output.toPlainText())
        self.assertIn('Syntax: app.py', self.view.output.toPlainText())
        self.assertNotIn('"state"', self.view.output.toPlainText())
        self.view.evidence_button.setChecked(True)
        self.assertIn('"state"', self.view.output.toPlainText())

    def test_real_engine_bus_drains_after_panel_close(self):
        from native_studio.engine import EngineBus
        bus = EngineBus(max_threads=1)
        view = CodingModeView(bus, service=Service())
        view.close()
        deadline = time.monotonic() + 3
        while bus.active_count and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(0.005)
        self.assertEqual(bus.active_count, 0)
        self.assertTrue(bus.shutdown())

    def test_saved_check_selection_reopens_without_replay(self):
        value = {'items': [{'execution_id': 'd'*32, 'request_id': 'a'*32, 'plan_id': 'b'*32,
                           'proposal_id': 'c'*32, 'state': 'BLOCKED'}], 'next_cursor': 'e'*32}
        self.view.history_kind.setCurrentText('Checks')
        self.view._history_loaded(value, 'Checks', False)
        self.view._select_history(self.view.history_rows.topLevelItem(0), 0)
        self.assertEqual(self.view.execution_id.text(), 'd'*32)
        self.assertEqual(self.view.request_id.text(), 'a'*32)
        self.assertEqual(self.service.calls[-1][:2], ('GET', '/mode/executions/'+'d'*32))
        self.assertTrue(self.view.history_more.isEnabled())
        self.view.history(more=True)
        self.assertEqual(self.service.calls[-1][1], '/mode/executions?limit=20&cursor='+'e'*32)

    def test_saved_preparation_plan_proposal_navigation(self):
        self.view._history_loaded({'items': [{'request_id': 'a'*32, 'objective': 'Synthetic'}]}, 'Preparations', False)
        self.view._select_history(self.view.history_rows.topLevelItem(0), 0)
        self.assertEqual(self.service.calls[-1][:2], ('GET', '/preparations/'+'a'*32))
        self.view.history_kind.setCurrentText('Plans'); self.view.history()
        self.assertEqual(self.service.calls[-1][1], '/preparations/'+'a'*32+'/plans')

    def test_disabled_or_unknown_capabilities_prevent_all_posts(self):
        for capabilities in ({'enabled': False, 'owner': 'synthetic'}, {}, {'enabled': True}, {'enabled': True, 'owner': ''}):
            self.view._capabilities_loaded(capabilities)
            count = len(self.service.calls)
            for path in ['/preparations', '/mode/executions', '/mode/executions/'+'a'*32+'/cancel']:
                self.view._call('POST', path, {}, concurrent=True)
            self.assertEqual(len(self.service.calls), count)
        self.view.check_service()
        self.assertTrue(self.view._coding_enabled)

    def test_closed_dialog_ignores_stale_delivery(self):
        class DeferredBus:
            def submit(self, fn, *args, on_result=None, on_error=None):
                self.result = on_result; self.error = on_error
        bus = DeferredBus(); view = CodingModeView(bus, service=Service())
        before = view.output.toPlainText(); view.close()
        bus.result({'enabled': True, 'owner': 'synthetic', 'state': 'STALE'})
        bus.error('stale error')
        self.assertEqual(view.output.toPlainText(), before)
        self.assertFalse(view._coding_enabled)

    def selected_proposal(self):
        self.view.request_id.setText('a'*32)
        self.view.plan_id.setText('b'*32)
        self.view.proposal_id.setText('c'*32)

    def test_trusted_local_requires_acknowledgement_for_each_task(self):
        self.selected_proposal()
        self.assertEqual(self.view.execution_mode.currentData(), 'isolated')
        self.view.execution_mode.setCurrentIndex(1)
        count = len(self.service.calls); self.view.check_candidate()
        self.assertEqual(len(self.service.calls), count)
        self.view.trusted_ack.setChecked(True); self.view.check_candidate()
        payload = self.service.calls[-1][2]
        self.assertEqual(payload['execution_backend'], 'trusted_host')
        self.assertTrue(payload['trusted_local_ack'])
        self.assertFalse(self.view.trusted_ack.isChecked())
        count = len(self.service.calls); self.view.check_candidate()
        self.assertEqual(len(self.service.calls), count)

    def test_isolated_never_inherits_local_ack(self):
        self.selected_proposal()
        self.view.execution_mode.setCurrentIndex(1); self.view.trusted_ack.setChecked(True)
        self.view.execution_mode.setCurrentIndex(0); self.view.check_candidate()
        self.assertEqual(self.service.calls[-1][2]['execution_backend'], 'isolated')
        self.assertFalse(self.service.calls[-1][2]['trusted_local_ack'])

    def test_trusted_local_requires_service_capability(self):
        self.selected_proposal()
        self.view._capabilities_loaded({'enabled': True, 'owner': 'synthetic', 'trusted_local_available': False})
        self.view.execution_mode.setCurrentIndex(1); self.view.trusted_ack.setChecked(True)
        count = len(self.service.calls); self.view.check_candidate()
        self.assertEqual(len(self.service.calls), count)

    def test_explicit_review_then_apply_and_no_auto_apply(self):
        class ReviewService(Service):
            def request(self, method, path, payload):
                result = super().request(method, path, payload)
                if path.endswith('/review'):
                    return {'owner': 'synthetic', 'execution_id': 'd'*32, 'can_apply': True,
                            'review_token': 'sealed-synthetic-token', 'state': 'VERIFIED'}
                return result
        service = ReviewService(); self.view.service = service
        self.view.execution_id.setText('d'*32); self.view.review_changes()
        self.assertTrue(self.view.apply_button.isEnabled())
        self.assertEqual(len(service.calls), 1)
        self.assertTrue(service.calls[-1][1].endswith('/review'))
        self.view.apply_changes()
        self.assertTrue(service.calls[-1][1].endswith('/apply'))
        self.assertEqual(service.calls[-1][2], {'review_token': 'sealed-synthetic-token'})
        self.assertFalse(self.view.apply_button.isEnabled())

    def test_mismatched_review_and_changed_selection_cannot_apply(self):
        class ReviewService(Service):
            def request(self, method, path, payload):
                super().request(method, path, payload)
                return {'owner': 'other', 'execution_id': 'd'*32, 'can_apply': True, 'review_token': 'token'}
        service = ReviewService(); self.view.service = service
        self.view.execution_id.setText('d'*32); self.view.review_changes()
        self.assertFalse(self.view.apply_button.isEnabled())
        count = len(service.calls); self.view.apply_changes()
        self.assertEqual(len(service.calls), count)
        self.view._apply_review = {'owner': 'synthetic', 'execution_id': 'd'*32, 'review_token': 'old'}
        self.view.execution_id.setText('e'*32)
        self.assertIsNone(self.view._apply_review)

    def test_running_checks_poll_selected_record_without_reexecution(self):
        self.view.execution_id.setText('d'*32); self.view._record = {'state': 'RUNNING'}
        self.view._poll()
        self.assertEqual(self.service.calls[-1][:2], ('GET', '/mode/executions/'+'d'*32))


if __name__ == '__main__': unittest.main()
