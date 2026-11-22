"""Visual design system for AI-BS Native Studio (Qt Style Sheets + palette)."""

from __future__ import annotations

import ctypes
import sys

PALETTE = {
    "bg": "#0b061c",
    "bg_dark": "#060210",
    "panel": "#12092e",
    "panel_alt": "#1c0f45",
    "border": "#2e1c59",
    "border_glow": "rgba(0, 240, 255, 0.45)",
    "border_pink": "rgba(255, 46, 147, 0.45)",
    "border_violet": "rgba(168, 85, 247, 0.45)",
    "text": "#f4e8ff",
    "muted": "#a793c9",
    "cyan": "#00f0ff",
    "cyan_neon": "#00f0ff",
    "violet": "#a855f7",
    "purple": "#8b5cf6",
    "magenta": "#ff2e93",
    "pink": "#ec4899",
    "emerald": "#10b981",
    "green": "#34d399",
    "amber": "#ff8a00",
    "yellow": "#fbbf24",
    "rose": "#f43f5e",
    "red": "#ef4444",
}

_QSS = """
QWidget {
    color: %(text)s;
    font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}
QMainWindow, QWidget#Root, QStackedWidget {
    background-color: %(bg)s;
}
QDialog, QMessageBox {
    background-color: %(panel)s;
    border: 1px solid %(violet)s;
    border-radius: 12px;
}
QLabel {
    background: transparent;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

QWidget#Sidebar {
    background-color: %(panel)s;
    border-right: 1px solid %(border)s;
}
QLabel#Brand {
    font-size: 22pt;
    font-weight: 800;
    color: %(cyan)s;
    letter-spacing: 0.5px;
}
QLabel#BrandSub {
    color: %(magenta)s;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#SidebarFooter {
    color: %(emerald)s;
    font-size: 8pt;
    font-weight: 600;
}
QListWidget#Nav {
    background: transparent;
    border: none;
    outline: 0;
}
QListWidget#Nav::item {
    padding: 12px 14px;
    border-radius: 10px;
    margin: 2px 0;
    color: %(muted)s;
}
QListWidget#Nav::item:hover {
    background: %(panel_alt)s;
    color: #ffffff;
    border: 1px solid rgba(0, 240, 255, 0.3);
}
QListWidget#Nav::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0,240,255,0.28), stop:0.5 rgba(168,85,247,0.20), stop:1 rgba(255,46,147,0.12));
    color: #ffffff;
    border-left: 3px solid %(cyan)s;
    border-top: 1px solid rgba(0, 240, 255, 0.3);
    border-bottom: 1px solid rgba(0, 240, 255, 0.3);
}

QLabel#PanelTitle {
    font-size: 20pt;
    font-weight: 750;
    color: #ffffff;
    letter-spacing: -0.5px;
}
QLabel#PanelSubtitle {
    color: %(muted)s;
    font-size: 10pt;
}
QFrame#Card {
    background-color: rgba(18, 9, 46, 0.88);
    border: 1px solid rgba(0, 240, 255, 0.22);
    border-radius: 14px;
}
QFrame#Card:hover {
    border-color: rgba(0, 240, 255, 0.45);
}
QLabel#CardTitle {
    color: %(muted)s;
    font-size: 9pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QLabel#Metric {
    font-size: 12pt;
    font-weight: 700;
    color: #ffffff;
}
QLabel#Summary {
    color: %(cyan)s;
    font-weight: 700;
}

QPushButton {
    background: %(panel_alt)s;
    border: 1px solid %(border)s;
    border-radius: 9px;
    padding: 8px 16px;
    color: %(text)s;
    font-weight: 600;
}
QPushButton:hover {
    border-color: %(cyan)s;
    color: #ffffff;
    background: rgba(0, 240, 255, 0.12);
}
QPushButton:pressed {
    background: %(border)s;
}
QPushButton:disabled {
    color: %(muted)s;
    border-color: %(border)s;
}
QPushButton#Accent {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 %(magenta)s, stop:0.5 %(violet)s, stop:1 %(cyan)s);
    color: #ffffff;
    font-weight: 800;
    border: none;
    border-radius: 9px;
    padding: 8px 18px;
}
QPushButton#Accent:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4db0, stop:0.5 #b872f8, stop:1 #33f3ff);
}
QPushButton#Accent:disabled {
    background: %(border)s;
    color: %(muted)s;
}
QPushButton#Danger {
    background: rgba(244, 63, 94, 0.15);
    border: 1px solid %(rose)s;
    color: %(rose)s;
    font-weight: 700;
}
QPushButton#Danger:hover {
    background: rgba(244, 63, 94, 0.3);
}

QTableView, QTableWidget {
    background: rgba(18, 9, 46, 0.90);
    alternate-background-color: rgba(28, 15, 69, 0.75);
    gridline-color: rgba(46, 28, 89, 0.6);
    border: 1px solid rgba(0, 240, 255, 0.25);
    border-radius: 10px;
    selection-background-color: rgba(0, 240, 255, 0.28);
    selection-color: #ffffff;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a0f3d, stop:1 #12092e);
    color: %(cyan)s;
    border: none;
    border-bottom: 1px solid rgba(0, 240, 255, 0.3);
    padding: 7px 10px;
    font-weight: 700;
    font-size: 8.5pt;
    text-transform: uppercase;
}
QTableCornerButton::section {
    background: #1a0f3d;
    border: none;
}

QLineEdit, QComboBox {
    background: #0d0724;
    border: 1px solid #3b226e;
    border-radius: 8px;
    padding: 7px 12px;
    color: #ffffff;
}
QLineEdit:focus, QComboBox:focus {
    border-color: %(cyan)s;
    background: #120a32;
}
QComboBox QAbstractItemView {
    background: #140c33;
    border: 1px solid %(cyan)s;
    selection-background-color: rgba(0, 240, 255, 0.25);
    selection-color: #ffffff;
}

QProgressBar {
    background: #0a051d;
    border: 1px solid #2e1c59;
    border-radius: 6px;
    max-height: 12px;
    color: transparent;
}
QProgressBar::chunk {
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 %(magenta)s, stop:0.5 %(violet)s, stop:1 %(cyan)s);
}

QPlainTextEdit#Console, QTextEdit#Console {
    background: #050212;
    border: 1px solid #3b226e;
    border-radius: 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 9.5pt;
    color: #00f0ff;
    padding: 8px;
}

QStatusBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #090418, stop:0.5 #12082b, stop:1 #090418);
    border-top: 1px solid rgba(168, 85, 247, 0.3);
    color: %(muted)s;
}
QStatusBar QLabel {
    padding: 0 10px;
}

QScrollBar:vertical {
    background: rgba(10, 5, 25, 0.5);
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 %(violet)s, stop:1 %(cyan)s);
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar:horizontal {
    background: rgba(10, 5, 25, 0.5);
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 %(magenta)s, stop:1 %(cyan)s);
    border-radius: 4px;
    min-width: 32px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QSplitter::handle {
    background: %(border)s;
}
QSplitter::handle:hover {
    background: %(cyan)s;
}
QToolTip {
    background: #1c0f45;
    color: #ffffff;
    border: 1px solid %(cyan)s;
    border-radius: 6px;
    padding: 5px;
    font-size: 9pt;
}

/* Trippy Cyber TopNavbar, SubTabBar & MomBanner */
QFrame#TopNavbar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b051e, stop:0.3 #160a36, stop:0.7 #120930, stop:1 #070d24);
    border-bottom: 1px solid rgba(0, 240, 255, 0.35);
}
QFrame#SubTabBar {
    background: rgba(9, 4, 24, 0.94);
    border-bottom: 1px solid rgba(168, 85, 247, 0.30);
}
QFrame#MomBanner {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #be185d, stop:0.5 #ec4899, stop:1 #d92bb8);
    border-bottom: 1px solid #ff4db0;
}
QFrame#MomBanner QLabel {
    color: #ffffff;
    font-weight: 800;
    font-size: 10pt;
    letter-spacing: 1px;
}
"""

STYLESHEET = _QSS % PALETTE


def severity_color(value: float | None, warn: float | None, crit: float | None, base: str = "cyan") -> str:
    if value is None:
        return PALETTE["muted"]
    if crit is not None and value >= crit:
        return PALETTE["rose"]
    if warn is not None and value >= warn:
        return PALETTE["amber"]
    return PALETTE[base]


def apply_dark_titlebar(widget) -> None:
    """Ask DWM for an immersive dark title bar on the native HWND."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new / pre-20H1)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:  # noqa: BLE001
        pass
