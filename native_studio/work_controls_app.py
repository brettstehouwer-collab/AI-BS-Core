"""Standalone source entry for native work controls; starts no jobs or services."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for location in (ROOT, ROOT / 'backend'):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from PyQt6 import sip
from native_studio.engine import EngineBus
from native_studio.process_batch_view import create_work_control_pages
from native_studio.theme import STYLESHEET
from native_studio.window_geometry import fit_startup_geometry
from native_studio.responsive_layout import workspace_scroll


class WorkControlsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AI-BS — Native work controls (source)')
        self.bus = EngineBus()
        self._ready = self._closing = False
        host = QWidget(self)
        layout = QVBoxLayout(host)
        note = QLabel('Standalone source instance: controls its own queues. '
            'BS-Chat and System Health use these same controls within Studio.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.pages = create_work_control_pages(self.bus, host)
        scroll = workspace_scroll(self.pages, host)
        scroll.setAccessibleName('Scrollable native work controls')
        layout.addWidget(scroll)
        self.setCentralWidget(host)
        self._close_timer = QTimer(self)
        self._close_timer.setInterval(20)
        self._close_timer.timeout.connect(self._poll_close)
        available = QApplication.primaryScreen().availableGeometry()
        self.winId()
        margins = self.windowHandle().frameMargins()
        geometry = fit_startup_geometry((available.x(), available.y(), available.width(), available.height()),
            preferred=(940, 600), minimum=(640, 480),
            frame=(max(16, margins.left()+margins.right()), max(40, margins.top()+margins.bottom())))
        self.setMinimumSize(geometry.minimum_width, geometry.minimum_height)
        self.resize(geometry.width, geometry.height)
        self.move(geometry.x, geometry.y)

    def closeEvent(self, event):
        if self._ready:
            event.accept()
            return
        event.ignore()
        if not self._closing:
            self._closing = True
            self.centralWidget().setEnabled(False)
            self.bus._process_batch_controller.shutdown()
            self.bus._native_terminal.shutdown()
            self.bus.shutdown(0)
            self._close_timer.start()
            self._poll_close()

    def _poll_close(self):
        batch = self.bus._process_batch_controller
        terminal = self.bus._native_terminal
        if batch.snapshot().get('drain_failed') or terminal.snapshot().get('cleanup_failed'):
            self._close_timer.stop()
            self.statusBar().showMessage('Owned-process cleanup needs attention; this session is retained.')
            return
        if batch.is_drained and terminal.is_drained and self.bus.is_drained:
            self._close_timer.stop()
            self._ready = True
            QTimer.singleShot(0, self.close)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = WorkControlsWindow()
    window.show()
    code = app.exec()
    app.processEvents()
    bus = window.bus
    sip.delete(window)
    sip.delete(bus)
    sip.delete(app)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
