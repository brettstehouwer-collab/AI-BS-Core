"""Qt preview lifecycle with synthetic pixmaps; never grabs a real screen."""
from __future__ import annotations

import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication
from native_studio import omni_broadcast_studio as studio


class NativeBroadcastPreview205Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def canvas(self):
        canvas = studio.LiveBroadcastCanvas()
        self.addCleanup(canvas.deleteLater)
        self.addCleanup(canvas.shutdown)
        return canvas

    def fake_capture(self, pixmap=None):
        if pixmap is None:
            pixmap = QPixmap(32, 24)
            pixmap.fill(Qt.GlobalColor.black)
        grabbed_threads = []
        def grab(hwnd):
            grabbed_threads.append(QThread.currentThread())
            return pixmap
        screen = SimpleNamespace(grabWindow=Mock(side_effect=grab))
        user32 = SimpleNamespace(IsWindow=Mock(return_value=True), IsWindowVisible=Mock(return_value=True),
                                 IsIconic=Mock(return_value=False),
                                 GetForegroundWindow=Mock(side_effect=AssertionError('Implicit foreground capture forbidden')))
        return screen, user32, grabbed_threads

    def test_canvas_never_constructs_or_starts_qscreen_worker(self):
        with patch.object(studio, 'NativeScreenCaptureThread', side_effect=AssertionError('QScreen worker forbidden')):
            self.canvas()

    def test_preview_timer_is_gui_owned_bounded_and_inactive_offscreen(self):
        canvas = self.canvas()
        timer = getattr(canvas, '_capture_timer', None)
        self.assertIsNotNone(timer)
        self.assertEqual(timer.thread(), self.app.thread())
        self.assertGreaterEqual(timer.interval(), 100)
        self.assertFalse(timer.isActive())
        canvas.set_target_window(2468, 'FixtureWindow')
        self.assertFalse(timer.isActive())

    def test_selected_window_grab_runs_on_gui_timer_signal(self):
        canvas = self.canvas()
        screen, user32, grabbed_threads = self.fake_capture()
        with patch.object(studio.QGuiApplication, 'primaryScreen', return_value=screen), \
                patch.object(studio, 'ctypes', SimpleNamespace(windll=SimpleNamespace(user32=user32))):
            canvas.set_target_window(2468, 'FixtureWindow')
            timer = getattr(canvas, '_capture_timer', None)
            self.assertIsNotNone(timer)
            timer.timeout.emit()
        screen.grabWindow.assert_called_once_with(2468)
        self.assertEqual(grabbed_threads, [self.app.thread()])
        self.assertIsNotNone(canvas._current_frame)
        self.assertFalse(canvas._current_frame.isNull())

    def test_no_selection_does_not_capture_foreground_or_desktop(self):
        canvas = self.canvas()
        screen, user32, _ = self.fake_capture()
        with patch.object(studio.QGuiApplication, 'primaryScreen', return_value=screen), \
                patch.object(studio, 'ctypes', SimpleNamespace(windll=SimpleNamespace(user32=user32))):
            canvas._capture_preview_frame()
        screen.grabWindow.assert_not_called()
        user32.GetForegroundWindow.assert_not_called()
        self.assertIsNone(canvas._current_frame)

    def test_unavailable_capture_clears_stale_frame_without_inventing_one(self):
        canvas = self.canvas()
        canvas._current_frame = QPixmap(32, 24)
        screen, user32, _ = self.fake_capture(QPixmap())
        with patch.object(studio.QGuiApplication, 'primaryScreen', return_value=screen), \
                patch.object(studio, 'ctypes', SimpleNamespace(windll=SimpleNamespace(user32=user32))):
            canvas.set_target_window(2468, 'FixtureWindow')
            canvas._capture_preview_frame()
        self.assertIsNone(canvas._current_frame)
        self.assertIsNone(canvas._cached_scaled_frame)

    def test_desktop_capture_requires_separate_explicit_opt_in(self):
        canvas = self.canvas()
        screen, user32, _ = self.fake_capture()
        with patch.object(studio.QGuiApplication, 'primaryScreen', return_value=screen), \
                patch.object(studio, 'ctypes', SimpleNamespace(windll=SimpleNamespace(user32=user32))):
            canvas.set_desktop_capture_enabled(True)
            canvas._capture_preview_frame()
        screen.grabWindow.assert_called_once_with(0)
        self.assertFalse(canvas._capture_timer.isActive())

    def test_shutdown_stops_capture_timer_and_clears_retained_pixels(self):
        canvas = self.canvas()
        timer = getattr(canvas, '_capture_timer', None)
        self.assertIsNotNone(timer)
        canvas._current_frame = QPixmap(32, 24)
        timer.start()
        canvas.shutdown()
        self.assertFalse(timer.isActive())
        self.assertIsNone(canvas._current_frame)


if __name__ == '__main__':
    unittest.main()
