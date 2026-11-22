"""Actual Qt close-filter lifetime; synthetic widgets/storage only."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton, QLabel
from native_studio.chat_recovery import ChatRecoveryController


class RecoveryLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        class View(QWidget):
            def __init__(self):
                super().__init__()
                self.accesses = self.captures = 0
                self.forbid_access = False
                self._is_streaming = False
                self.state = {'transcript': 'synthetic', 'draft': '', 'scratchpad': '', 'history': [], 'model': ''}
                self.input_edit = QLineEdit(self)
                self.send_btn = QPushButton(self)
                self.recovery_retry = QPushButton(self)
                self.recovery_status = QLabel(self)

            def window(self):
                self.accesses += 1
                if self.forbid_access:
                    raise AssertionError('View accessed after controller shutdown')
                return super().window()

            def capture_recovery_state(self):
                self.captures += 1
                if self.forbid_access:
                    raise AssertionError('Capture after controller shutdown')
                return dict(self.state)

        class Store:
            def __init__(self):
                self.saved = []
                self.fail = False

            def save(self, state):
                if self.fail:
                    raise OSError('synthetic save failure')
                self.saved.append(dict(state))
                return object()

        self.view, self.store = View(), Store()
        self.controller = ChatRecoveryController(self.view, object(), store=self.store)
        self.controller.ready = True
        self.controller._confirmed = self.controller.capture()

    def tearDown(self):
        # Explicitly clean up even the old failing implementation before Qt dies.
        self.app.removeEventFilter(self.controller)
        self.controller.timer.stop()
        self.view.forbid_access = False
        self.view.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_global_close_event_does_not_access_view_after_shutdown(self):
        self.controller.shutdown()
        before = self.view.accesses, self.view.captures
        event = QCloseEvent()
        QCoreApplication.sendEvent(self.view, event)
        self.assertEqual((self.view.accesses, self.view.captures), before)
        self.assertEqual(self.store.saved, [])
        self.assertTrue(event.isAccepted())

    def test_late_direct_filter_call_short_circuits_before_any_view_access(self):
        self.controller.shutdown()
        self.view.forbid_access = True
        self.assertFalse(self.controller.eventFilter(self.view, QCloseEvent()))

    def test_shutdown_removes_filter_once_from_its_original_application(self):
        with patch.object(self.app, 'removeEventFilter', wraps=self.app.removeEventFilter) as remove:
            with patch.object(QApplication, 'instance', side_effect=AssertionError('Must use original filter owner')):
                self.controller.shutdown()
                self.controller.shutdown()
            remove.assert_called_once_with(self.controller)
        self.assertFalse(self.controller.timer.isActive())

    def test_active_filter_saves_current_draft_before_accepting_close(self):
        self.view.state['draft'] = 'synthetic final draft'
        event = QCloseEvent()
        QCoreApplication.sendEvent(self.view, event)
        self.assertTrue(event.isAccepted())
        self.assertEqual(self.store.saved[-1]['draft'], 'synthetic final draft')
        self.assertFalse(self.controller._closed)

    def test_save_failure_veto_keeps_filter_live_and_retry_preserves_newest_draft(self):
        self.view.state['draft'] = 'first draft'
        self.store.fail = True
        event = QCloseEvent()
        QCoreApplication.sendEvent(self.view, event)
        self.assertFalse(event.isAccepted())
        self.assertFalse(self.controller._closed)
        self.assertEqual(self.store.saved, [])
        self.view.state['draft'] = 'newest draft'
        self.store.fail = False
        retry = QCloseEvent()
        QCoreApplication.sendEvent(self.view, retry)
        self.assertTrue(retry.isAccepted())
        self.assertEqual(self.store.saved[-1]['draft'], 'newest draft')

    def test_streaming_close_veto_does_not_save_partial_response(self):
        self.view._is_streaming = True
        self.view.state['draft'] = 'synthetic partial response'
        event = QCloseEvent()
        QCoreApplication.sendEvent(self.view, event)
        self.assertFalse(event.isAccepted())
        self.assertFalse(self.controller._closed)
        self.assertEqual(self.store.saved, [])

    def test_second_shutdown_does_not_touch_a_released_native_timer(self):
        self.controller.shutdown()
        with patch.object(self.controller.timer, 'stop', side_effect=RuntimeError('synthetic released timer')):
            self.controller.shutdown()

    def test_closed_entry_points_do_not_read_view_or_admit_more_work(self):
        from unittest.mock import Mock
        self.controller.bus = Mock()
        self.controller.shutdown()
        self.view.forbid_access = True
        self.controller.begin()
        self.controller.retry()
        self.controller.tick()
        self.controller._loaded(None)
        self.controller._load_error('synthetic')
        self.assertFalse(self.controller.flush_for_close())
        self.controller.bus.submit.assert_not_called()

    def test_late_save_ack_cannot_replace_confirmed_final_snapshot_after_shutdown(self):
        from types import SimpleNamespace
        jobs = []
        self.controller.bus = SimpleNamespace(submit=lambda work, **callbacks: jobs.append(callbacks))
        self.view.state['draft'] = 'old autosave'
        self.controller.tick()
        self.assertEqual(len(jobs), 1)
        final = {'synthetic': 'newer final snapshot'}
        self.controller._confirmed = final
        self.controller.shutdown()
        self.view.forbid_access = True
        jobs[0]['on_result'](object())
        self.assertIs(self.controller._confirmed, final)


if __name__ == '__main__':
    unittest.main(verbosity=2)
