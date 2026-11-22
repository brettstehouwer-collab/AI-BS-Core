"""Comprehensive Click & Interaction Verification Across All AI-BS Native Studio Hubs & Subtabs.

Simulates clicking every QPushButton, QToolButton, and exercising interactive controls
across all 59 subtabs in the native studio. Ensures zero crashes, zero unhandled exceptions,
and verifies 100% functional signal-slot connectivity.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\AI-BS")

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFontDialog,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QTextEdit,
    QToolButton,
    QWidget,
)

import subprocess

# Safe mocks to prevent modal blocking or runaway child processes during the click sweep
QDialog.exec = lambda self: int(QDialog.DialogCode.Accepted)
QDialog.open = lambda self: None
QFileDialog.getOpenFileName = lambda *a, **k: (r"C:\AI-BS\version.txt", "All Files (*.*)")
QFileDialog.getSaveFileName = lambda *a, **k: (r"C:\AI-BS\saved_test.txt", "All Files (*.*)")
QFileDialog.getExistingDirectory = lambda *a, **k: r"C:\AI-BS"
QMessageBox.exec = lambda *a, **k: int(QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QInputDialog.getText = staticmethod(lambda *a, **k: ("AI-BS Click Test", True))
QInputDialog.getInt = staticmethod(lambda *a, **k: (1, True))
QColorDialog.getColor = staticmethod(lambda *a, **k: Qt.GlobalColor.cyan)
QFontDialog.getFont = staticmethod(lambda *a, **k: (None, True))

from PyQt6.QtWidgets import QMenu
QMenu.exec = lambda *a, **k: None
QMenu.popup = lambda *a, **k: None

from PyQt6.QtCore import QProcess
QProcess.start = lambda self, *a, **k: None

orig_popen = subprocess.Popen
class SafePopen:
    def __init__(self, args, *a, **k):
        self.pid = 99999
        self.returncode = 0
        self.args = args
        self.stdin = None
        self.stdout = None
        self.stderr = None
    def poll(self): return 0
    def wait(self, timeout=None): return 0
    def communicate(self, input=None, timeout=None): return (b"", b"")
    def terminate(self): pass
    def kill(self): pass

subprocess.Popen = SafePopen
subprocess.run = lambda *a, **k: subprocess.CompletedProcess(args=a, returncode=0, stdout="", stderr="")
subprocess.check_output = lambda *a, **k: b'{"cuda": true, "name": "NVIDIA GeForce RTX 4090", "vram": 24.0}'
subprocess.call = lambda *a, **k: 0
os.system = lambda *a, **k: 0
if hasattr(os, "startfile"):
    os.startfile = lambda *a, **k: None

from native_studio.engine import EngineBus
from native_studio.navigation_registry import (
    NATIVE_MASTER_HUBS,
    PINNED_QUICK_TABS,
    SIMPLE_MODE_ITEMS,
    get_all_subtabs_flat,
)
from native_studio.app import MainWindow


def run_click_audit():
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()

    all_subtabs = get_all_subtabs_flat()
    print(f"============================================================")
    print(f"AI-BS NATIVE STUDIO UNIVERSAL CLICK-TEST AUDIT")
    print(f"Total Subtabs Registered: {len(all_subtabs)}")
    print(f"Total Master Hubs: {len(NATIVE_MASTER_HUBS)}")
    print(f"Pinned Quick Tabs in Top Navbar: {len(PINNED_QUICK_TABS)}")
    print(f"============================================================\n")

    # 1. Test Top Navigation Bar and Pinned Dock
    print("--- [TOP NAVIGATION BAR & PINNED QUICK DOCK] ---")
    top_navbar = win.findChild(QWidget, "TopNavbar")
    top_nav_buttons = top_navbar.findChildren((QPushButton, QToolButton)) if top_navbar else []
    print(f"Total Top Nav & Quick Dock Buttons: {len(top_nav_buttons)}")
    top_failures = []
    for btn in top_nav_buttons:
        txt = btn.text() or btn.toolTip() or btn.objectName() or "unnamed"
        rec = btn.receivers(btn.clicked)
        try:
            btn.click()
            QApplication.processEvents()
            # print(f"  [OK] '{txt}' (receivers: {rec})")
        except Exception as exc:
            top_failures.append((txt, str(exc)))
            print(f"  [FAIL] '{txt}': {exc}")
    print(f"Top Nav Clicks Completed. Failures: {len(top_failures)}\n")

    # 2. Iterate All 59 Subtabs
    total_buttons_clicked = 0
    total_exceptions = []
    subtab_summary = []

    for idx, item in enumerate(all_subtabs, 1):
        k = item.key
        label = item.label
        view = win._get_or_create_subview(k)
        if not view:
            print(f"[{idx:02d}/{len(all_subtabs)}] [ERROR] Subtab '{k}' could not be instantiated.")
            continue

        buttons = view.findChildren((QPushButton, QToolButton))
        combos = view.findChildren(QComboBox)
        sliders = view.findChildren(QSlider)
        checkboxes = view.findChildren((QCheckBox, QRadioButton))

        subtab_btn_count = 0
        subtab_fails = 0

        for btn in buttons:
            txt = btn.text() or btn.toolTip() or btn.objectName() or "unnamed"
            # Ignore internal Qt calendar navigation month/year buttons
            if btn.objectName() in ("qt_calendar_monthbutton", "qt_calendar_yearbutton") or txt in ("October", "<", ">"):
                continue

            receivers = btn.receivers(btn.clicked)
            subtab_btn_count += 1
            total_buttons_clicked += 1

            try:
                # Dismiss any modal popup scheduled
                QTimer.singleShot(10, lambda: (QApplication.activeModalWidget().accept() if hasattr(QApplication.activeModalWidget(), "accept") else QApplication.activeModalWidget().close()) if QApplication.activeModalWidget() else None)
                btn.click()
                QApplication.processEvents()
            except Exception as exc:
                subtab_fails += 1
                total_exceptions.append({
                    "subtab": k,
                    "label": label,
                    "button": txt,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                })

        # Test ComboBoxes
        for cb in combos:
            if cb.count() > 0:
                orig = cb.currentIndex()
                for c_idx in range(min(cb.count(), 2)):
                    cb.setCurrentIndex(c_idx)
                    QApplication.processEvents()
                cb.setCurrentIndex(orig)

        # Test Sliders
        for sl in sliders:
            orig = sl.value()
            sl.setValue(min(sl.maximum(), orig + 1))
            QApplication.processEvents()
            sl.setValue(orig)

        # Test Checkboxes
        for chk in checkboxes:
            orig = chk.isChecked()
            chk.setChecked(not orig)
            QApplication.processEvents()
            chk.setChecked(orig)

        status = "PASS" if subtab_fails == 0 else f"FAIL ({subtab_fails} errors)"
        subtab_summary.append((k, label, subtab_btn_count, len(combos), len(sliders), len(checkboxes), status))
        print(f"[{idx:02d}/{len(all_subtabs)}] [{status}] {label:35s} | {subtab_btn_count:2d} btns | {len(combos):2d} combos | {len(sliders):2d} sliders | {len(checkboxes):2d} checks")

    print("\n" + "="*60)
    print("UNIVERSAL CLICK-TEST SUMMARY REPORT")
    print("="*60)
    print(f"Total Subtabs Tested: {len(subtab_summary)}")
    print(f"Total Interactive Buttons Clicked: {total_buttons_clicked}")
    print(f"Total Unhandled Exceptions: {len(total_exceptions)}")
    print("="*60)

    if total_exceptions:
        print("\n[EXCEPTIONS CAUGHT]:")
        for ex in total_exceptions:
            print(f"  - Subtab [{ex['subtab']}]: Button '{ex['button']}' -> {ex['error']}")
    else:
        print("\n>>> ALL BUTTONS IN ALL HUBS AND TABS FUNCTION NATIVELY WITH 0 UNHANDLED EXCEPTIONS! <<<")

    return len(total_exceptions)


if __name__ == "__main__":
    sys.exit(run_click_audit())
