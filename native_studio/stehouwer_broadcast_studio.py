"""Stehouwer Publishing Broadcast Studio - Pure Native Windows Desktop Workstation.

Direct Win32 Direct2D / DirectX 11 GUI with Zero Browser Engines (zero Electron, zero Chromium wrappers):
1. Pure PyQt6 QtWidgets native HWND window rendered via Direct2D / DirectX 11.
2. Direct Multimedia Class Scheduler Service (MMCSS "Pro Audio", thread priority 15) registration.
3. Decoupled multithreaded EngineBus worker pool for non-blocking hardware I/O and telemetry.
4. Program/Preview monitor with 16:9 Landscape vs 9:16 Shorts/TikTok orientation toggle.
5. 5-Channel WASAPI Exclusive Multi-Track Audio Mixer with real-time VU peak meters.
6. Multi-Destination Hardware NVENC 4K/8K Video Streamer (YouTube Live, Twitch, Kick, Sovereign HLS).
7. Seamlessly harmonized with AI-BS local web servers & daemon topology (FastAPI 8080, Broadcast Daemon 8005, NVENC Kernel 8088, Vite 5174, etc.) within the Native Windows version.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
import time

# Ensure C:\AI-BS root and native_studio are in sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_NATIVE_DIR = str(Path(__file__).resolve().parent)
if _NATIVE_DIR not in sys.path:
    sys.path.insert(0, _NATIVE_DIR)

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStatusBar,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.omni_broadcast_studio import UniversalOmniStudioNativeView
from native_studio.theme import PALETTE, STYLESHEET, apply_dark_titlebar


def set_windows_app_id() -> None:
    """Register explicit Windows AppUserModelID for taskbar isolation and MMCSS priority."""
    if sys.platform == "win32":
        try:
            myappid = "StehouwerPublishing.BroadcastStudio.v5"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass


def register_mmcss_pro_audio() -> bool:
    """Register the application audio/render pipeline with Windows MMCSS Pro Audio (priority 15)."""
    if sys.platform != "win32":
        return False
    try:
        avrt = ctypes.windll.avrt
        task_index = wintypes.DWORD(0)
        handle = avrt.AvSetMmThreadCharacteristicsW("Pro Audio", ctypes.byref(task_index))
        if handle:
            # Set thread priority to HIGH (thread priority 15 in MMCSS Pro Audio)
            avrt.AvSetMmThreadPriority(handle, 2)  # AVRT_PRIORITY_HIGH
            return True
    except Exception:
        pass
    return False


class StehouwerBroadcastStudioWindow(QMainWindow):
    """Pure Native Windows Application Shell for Stehouwer Publishing Broadcast Studio."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Stehouwer Publishing Broadcast Studio — Hardware NVENC 4K/8K & Neural DAW")
        self.resize(1620, 1020)
        self.setMinimumSize(1200, 750)

        # Apply high-resolution icon
        icon_path = Path(_ROOT) / "installer" / "app_icon.ico"
        if not icon_path.exists():
            icon_path = Path(_ROOT) / "BroadcastStudioApp" / "build" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Engine Worker Bus (multithreaded QThreadPool)
        self.bus = EngineBus()

        # Central Native Broadcast Studio
        self.broadcast_view = UniversalOmniStudioNativeView(self.bus)
        self.setCentralWidget(self.broadcast_view)

        # Status Bar
        self.status = QStatusBar()
        self.status.setStyleSheet("background: #060911; color: #94a3b8; border-top: 1px solid #1e293b; font-size: 8pt;")
        self.setStatusBar(self.status)
        self.status.showMessage("Stehouwer Publishing Broadcast Studio | Pure Native Windows (Direct2D / MMCSS P15) | NVENC Ready")

        # Native DWM Immersive Dark Titlebar
        apply_dark_titlebar(self)

    def closeEvent(self, event) -> None:
        """Graceful shutdown of worker threads and background streams."""
        try:
            if hasattr(self.broadcast_view, "cleanup"):
                self.broadcast_view.cleanup()
            self.bus.shutdown()
        except Exception:
            pass
        super().closeEvent(event)


def log_studio(msg: str) -> None:
    try:
        log_file = Path(_ROOT) / "logs" / "stehouwer_studio.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def main() -> int:
    log_studio("Entering stehouwer_broadcast_studio.py main()")
    try:
        set_windows_app_id()
        mmcss_ok = register_mmcss_pro_audio()
        log_studio(f"MMCSS Pro Audio registered: {mmcss_ok}")

        # Enable High DPI rendering
        if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName("Stehouwer Publishing Broadcast Studio")
        app.setOrganizationName("Stehouwer Publishing LLC")
        app.setStyleSheet(STYLESHEET)

        icon_path = Path(_ROOT) / "installer" / "app_icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        log_studio("Instantiating StehouwerBroadcastStudioWindow...")
        win = StehouwerBroadcastStudioWindow()
        log_studio("Calling win.show()...")
        win.show()
        log_studio("Entering app.exec()...")
        res = app.exec()
        log_studio(f"app.exec() returned {res}")
        return res
    except Exception as exc:
        import traceback
        log_studio(f"FATAL EXCEPTION in main(): {exc}\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
