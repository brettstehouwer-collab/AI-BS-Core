# =========================================================================
# AI-BS Sovereign Intelligence Ecosystem - Native Tap-To-Run Test Suite
# File: C:\AI-BS\native_studio\test_tap_to_run_native.py
# Description: Unit test for native PyQt6 Direct2D TapToRunCanvasWidget
# Architecture: Zero Browser Engine / Pure Native Direct2D Scene Graph
# =========================================================================

import os
import sys
import time
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt

# Initialize headless QApplication if not already present
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from native_studio.intelligence_views import InteractiveCanvasScreen, TapToRunCanvasWidget


def test_interactive_canvas_screen():
    screen = InteractiveCanvasScreen()
    assert screen.width() == 420
    assert screen.height() == 420

    clicked_coords = []
    screen.point_clicked.connect(lambda x, y: clicked_coords.append((x, y)))

    # Simulate mouse press event at center (210, 210) -> (400, 400)
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QEvent
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(210.0, 210.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    screen.mousePressEvent(event)
    assert len(clicked_coords) == 1
    assert 390 <= clicked_coords[0][0] <= 410
    assert 390 <= clicked_coords[0][1] <= 410


def test_tap_to_run_canvas_widget_lifecycle():
    widget = TapToRunCanvasWidget()
    assert widget.lbl_status.text() == "STAGED (IDLE)"
    assert not widget.viewport_frame.isVisible()

    # Stage payload
    test_code = "import pygame\npygame.init()\n"
    widget.set_staged_payload("Animated Chess Game", test_code)
    assert widget.lbl_status.text() == "STAGED (READY)"
    assert widget.btn_run.text() == "▶ Run Animated Chess Game"

    # Show widget to enable hierarchical visibility
    widget.show()

    # Toggle run (start)
    widget.start_canvas()
    assert widget.active_proc is not None
    assert widget.lbl_status.text().startswith("LIVE")
    assert not widget.viewport_frame.isHidden()

    # Toggle stop
    widget.stop_canvas()
    assert widget.active_proc is None
    assert widget.lbl_status.text() == "TERMINATED"
    assert widget.viewport_frame.isHidden()
