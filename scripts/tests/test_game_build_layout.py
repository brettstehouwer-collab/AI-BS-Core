"""Offscreen geometry and action checks; no real project, service or game launch."""
from copy import deepcopy
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QStyle, QStyleOptionButton
import native_studio.game_build_monitor as monitor
import native_studio.game_build_view as game
from native_studio.theme import STYLESHEET


class _SyntheticBus:
    def __init__(self, data):
        self.data = data
        self.submissions = 0

    def submit(self, function, root, *, on_result, on_error):
        self.submissions += 1
        on_result(deepcopy(self.data))


class BuildProgressLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.original_font = cls.app.font()
        cls.original_stylesheet = cls.app.styleSheet()
        # The offscreen Windows plugin may not discover system fonts. Register
        # the existing theme fonts explicitly rather than measure missing-glyph
        # boxes and accidentally claim readable text from those metrics.
        cls.font_ids = []
        for filename in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):
            path = Path("C:/Windows/Fonts") / filename
            if path.is_file():
                font_id = QFontDatabase.addApplicationFont(str(path))
                if font_id >= 0:
                    cls.font_ids.append(font_id)

    @classmethod
    def tearDownClass(cls):
        cls.app.setStyleSheet(cls.original_stylesheet)
        cls.app.setFont(cls.original_font)
        for font_id in cls.font_ids:
            QFontDatabase.removeApplicationFont(font_id)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # The monitor reads only this empty disposable root. Even drive-space
        # metadata is synthetic, so this test never scans saved user data.
        disk = type("Disk", (), {"free": 100 * 1024**3, "total": 200 * 1024**3})()
        with patch.object(monitor.shutil, "disk_usage", return_value=disk):
            self.data = monitor.read_build_progress(self.root)
        self.data.update(status="running", configuration="Synthetic Release",
                         stage="Checking a long readable synthetic build status " * 8)
        self.data["log"] = "\n".join(f"Synthetic detail line {n}" for n in range(80))
        self.bus = _SyntheticBus(self.data)
        self.views = []
        self.launch = patch.object(game.QProcess, "startDetached",
                                   side_effect=AssertionError("No native process allowed"))
        self.launch.start()
        self.addCleanup(self.launch.stop)
        self.browser = patch.object(game.QDesktopServices, "openUrl", return_value=True)
        self.browser_mock = self.browser.start()
        self.addCleanup(self.browser.stop)
        self.bundle = patch.object(game, "_bundle_root", return_value=None)
        self.bundle.start()
        self.addCleanup(self.bundle.stop)
        self.addCleanup(self._close_views)

    def _close_views(self):
        for view in self.views:
            view.timer.stop()
            view.close()
            view.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def _pump(self):
        for _ in range(6):
            QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
            self.app.processEvents()

    def _scale(self, factor):
        # The real Studio theme declares point sizes; scaling QApplication.font
        # alone would leave those QSS sizes unchanged and give false coverage.
        stylesheet = re.sub(r"(\d+(?:\.\d+)?)pt",
                            lambda match: f"{float(match.group(1)) * factor:g}pt",
                            STYLESHEET)
        self.app.setFont(QFont("Segoe UI", round(10 * factor)))
        self.app.setStyleSheet(stylesheet)

    def _view(self, factor=1, size=(960, 540)):
        self._scale(factor)
        view = game.GameBuildNativeView(self.bus, root=self.root)
        self.views.append(view)
        view.resize(*size)
        view.show()
        self._pump()
        view.timer.stop()
        return view

    def _assert_readable(self, view):
        content = view._progress_content
        previous_bottom = -1
        for index in range(content.layout().count()):
            widget = content.layout().itemAt(index).widget()
            if widget.isHidden():
                continue
            self.assertGreaterEqual(widget.geometry().top(), previous_bottom)
            previous_bottom = widget.geometry().bottom()
            if isinstance(widget, QPushButton):
                self.assertTrue(widget.fontMetrics().inFont("W"), "Real readable glyph font required")
                option = QStyleOptionButton()
                widget.initStyleOption(option)
                text_rect = widget.style().subElementRect(
                    QStyle.SubElement.SE_PushButtonContents, option, widget)
                self.assertGreaterEqual(text_rect.height(), widget.fontMetrics().height(), widget.text())
                self.assertGreaterEqual(text_rect.width(), widget.fontMetrics().horizontalAdvance(widget.text()),
                                        widget.text())
                self.assertGreaterEqual(widget.height(), widget.sizeHint().height(), widget.text())
            elif isinstance(widget, QLabel) and widget.text():
                self.assertTrue(widget.wordWrap())
                self.assertGreaterEqual(widget.height(), widget.heightForWidth(widget.width()), widget.text()[:80])
        self.assertGreaterEqual(view.details.viewport().height(),
                                8 * view.details.fontMetrics().lineSpacing())

    def test_controls_and_multiline_status_keep_readable_geometry_at_three_font_scales(self):
        for factor in (1, 1.5, 2):
            for size in ((1280, 720), (960, 540), (640, 400)):
                with self.subTest(font_scale=factor, viewport=size):
                    view = self._view(factor, size)
                    self._assert_readable(view)
                    self.assertEqual(view.size().width(), size[0])
                    self.assertEqual(view.size().height(), size[1])
                    self.assertGreater(view.progress_scroll.verticalScrollBar().maximum(), 0)
                    self.assertEqual(len(view._progress_content.findChildren(QPushButton)), 8)

    def test_every_action_and_details_are_reachable_by_scroll_without_launching(self):
        for factor in (1, 1.5, 2):
            with self.subTest(font_scale=factor):
                view = self._view(factor, (640, 400))
                scroll = view.progress_scroll
                for widget in [*view._progress_content.findChildren(QPushButton), view.details]:
                    # An editor's ensureWidgetVisible target can be its cursor,
                    # rather than the widget center. Check that an actual point
                    # in every control is reachable by the page scroll range.
                    target = widget.mapTo(view._progress_content, widget.rect().center())
                    scroll.ensureVisible(target.x(), target.y(), 8, 8)
                    self._pump()
                    center = widget.mapTo(scroll.viewport(), widget.rect().center())
                    self.assertTrue(scroll.viewport().rect().contains(center), widget.objectName())
                view.details.verticalScrollBar().setValue(view.details.verticalScrollBar().maximum())
                self.assertGreater(view.details.verticalScrollBar().value(), 0)
                self.assertIn("Synthetic detail line 79", view.details.toPlainText())
                self.assertFalse(self.browser_mock.called)

    def test_refresh_and_live_font_change_reflow_long_text_without_collapsing_details(self):
        view = self._view(1, (960, 540))
        initial_detail_minimum = view.details.minimumSizeHint().height()
        self.bus.data["stage"] = "New long status with readable words " * 40
        view.refresh()
        view.launch_status.setText("Synthetic launch status, no process was started. " * 30)
        self._pump()
        self._assert_readable(view)
        self._scale(2)
        self._pump()
        self.assertGreater(view.details.minimumSizeHint().height(), initial_detail_minimum)
        self._assert_readable(view)
        view.resize(1280, 720)
        self._pump()
        self._assert_readable(view)
        view._error("Synthetic error " * 30)
        self._pump()
        self._assert_readable(view)
        self.assertFalse(view.pending)

    def test_layout_keeps_all_launch_action_arguments_and_resource_targets(self):
        view = self._view()
        with patch.object(view, "_update_launch_targets"), patch.object(view, "_start_native_player") as start:
            for button, arguments, label, extra in (
                (view.native_player_button, [], "Native motherboard world", {}),
                (view.obstacle_course_button, ["--obstacle-course"], "Native obstacle course", {}),
                (view.durable_world_button, ["--durable-world"], "Native durable First Boot world", {}),
                (view.chapter_button, ["--durable-world", "--chapter"], "First Boot chapter", {"chapter": True}),
            ):
                button.setEnabled(True)
                button.click()
                start.assert_called_with(arguments, label, **extra)
        buttons = {button.text(): button for button in view._progress_content.findChildren(QPushButton)}
        submissions = self.bus.submissions
        buttons["Refresh progress"].click()
        self.assertEqual(self.bus.submissions, submissions + 1)
        buttons["Open architectural builder ledger"].click()
        self.assertEqual(Path(self.browser_mock.call_args.args[0].toLocalFile()),
                         self.root / "docs/game_engine/AI_BS_GAME_ARCHITECTURAL_BUILDER_LEDGER.md")
        view.playground_button.setEnabled(True)
        view.playground_button.click()
        self.assertEqual(Path(self.browser_mock.call_args.args[0].toLocalFile()), view.playground_path)
        with patch.object(view, "_workspace_changed") as changed:
            view.warm_opening_button.setEnabled(True)
            view.warm_opening_button.click()
            changed.assert_called_once_with(2)
        self.assertEqual(view.workspace_tabs.currentIndex(), 2)

    def test_other_tabs_stay_lazy_and_missing_launch_resources_stay_disabled(self):
        view = self._view()
        self.assertEqual([view.workspace_tabs.tabText(n) for n in range(4)],
                         ["Build progress", "Creator", "Chapter creator", "Assets"])
        self.assertEqual(view.workspace_tabs.currentIndex(), 0)
        for name in ("creator_view", "content_view", "asset_view"):
            self.assertIsNone(getattr(view, name))
        for button in (view.playground_button, view.native_player_button, view.obstacle_course_button,
                       view.durable_world_button, view.chapter_button, view.warm_opening_button):
            self.assertFalse(button.isEnabled())


if __name__ == "__main__":
    unittest.main(verbosity=2)
