"""Native program monitor fixtures; decoder and all broadcast effects are fake."""
from pathlib import Path
import unittest
from unittest.mock import patch

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton


class FakeNativePreview(QWidget):
    frame_ready = pyqtSignal(QImage)
    cleared = pyqtSignal()
    state_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.states = []
        self.enabled = []
        self.closed = False

    def set_coordinator_state(self, state):
        self.states.append(dict(state))

    def set_preview_enabled(self, enabled):
        self.enabled.append(enabled)
        if not enabled:
            self.cleared.emit()
            self.state_changed.emit({'state': 'disabled'})

    def preview_status(self):
        return {'state': 'waiting', 'delayed': True, 'audio_enabled': False}

    def shutdown(self):
        self.closed = True
        self.cleared.emit()


class NativeProgramPreviewUi209Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.tests.test_native_broadcast_coordinator207 import NativeCoordinatorOffscreen207Tests
        NativeCoordinatorOffscreen207Tests.setUpClass()
        cls.app = NativeCoordinatorOffscreen207Tests.app

    def view(self):
        from native_studio import omni_broadcast_studio as studio
        from scripts.tests.test_native_broadcast_coordinator207 import NativeCoordinatorOffscreen207Tests
        with patch.object(studio, 'NativeBroadcastPreview', FakeNativePreview, create=True):
            return NativeCoordinatorOffscreen207Tests.view(self)

    def test_active_native_ui_has_no_obs_launch_or_status_controls(self):
        view, bus, studio = self.view()
        texts = [child.text() for kind in (QLabel, QPushButton) for child in view.findChildren(kind)]
        self.assertFalse(any('obs' in text.casefold() for text in texts))
        self.assertFalse(hasattr(view, 'btn_obs'))
        self.assertFalse(hasattr(type(view), '_launch_obs'))
        self.assertNotIn('obs', Path(studio.__file__).read_text(encoding='utf-8').casefold())

    def test_real_program_image_survives_status_poll_without_desktop_capture(self):
        view, bus, studio = self.view()
        self.assertIsInstance(view._program_preview, FakeNativePreview)
        image = QImage(160, 90, QImage.Format.Format_RGB32)
        image.fill(QColor('#d32941'))
        view._program_preview.frame_ready.emit(image)
        image.fill(QColor('#121212'))  # Canvas must own its copy.
        state = {'status': 'running_unverified', 'active': True, 'can_stop': True,
                 'can_select': True, 'capture_state': 'capturing', 'source_mode': 'window'}
        view._apply_broadcast_status(state)
        self.assertEqual(view._program_preview.states, [state])
        self.assertEqual(view.canvas._program_preview_image.pixelColor(20, 20).name(), '#d32941')
        self.assertFalse(view.canvas._capture_timer.isActive())
        self.assertEqual(view.canvas._capture_hwnd, 0)
        view.canvas.resize(640, 360)
        rendered = view.canvas.grab().toImage()
        self.assertEqual(rendered.pixelColor(rendered.width()//2, rendered.height()//2).name(), '#d32941',
                         f'Actual layout canvas {rendered.width()}x{rendered.height()}')
        self.assertEqual(len(bus.jobs), 1)

    def test_preview_toggle_and_close_never_dispatch_broadcast_commands(self):
        view, bus, studio = self.view()
        with patch.object(studio, 'send_broadcast_command') as dispatch, \
             patch.object(studio, 'select_broadcast_source') as select:
            view.chk_program_preview.setChecked(False)
            self.assertEqual(view._program_preview.enabled, [False])
            self.assertIn('off', view.lbl_preview_status.text().casefold())
            view.shutdown()
            self.assertTrue(view._program_preview.closed)
            dispatch.assert_not_called()
            select.assert_not_called()
            self.assertEqual(len(bus.jobs), 1)

    def test_stale_or_cleared_preview_discards_pixels_and_uses_fixed_labels(self):
        view, bus, studio = self.view()
        image = QImage(160, 90, QImage.Format.Format_RGB32)
        image.fill(QColor('#d32941'))
        view._program_preview.frame_ready.emit(image)
        view._program_preview.cleared.emit()
        view._program_preview.state_changed.emit({'state': 'stale', 'error_code': 'SECRET_MUST_NOT_ECHO'})
        self.assertIsNone(view.canvas._program_preview_image)
        self.assertIn('stale', view.lbl_preview_status.text().casefold())
        self.assertNotIn('SECRET', view.lbl_preview_status.text())
        self.assertIn('delayed', view.chk_program_preview.toolTip().casefold())

