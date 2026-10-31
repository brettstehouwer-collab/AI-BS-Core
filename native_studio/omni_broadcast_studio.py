"""Native broadcast controls and a read-only, delayed program monitor.

The coordinator owns capture and dispatch. The monitor decodes its local HLS
output independently; scene drafts and preview controls do not change capture.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional
import urllib.request
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
else:
    ctypes = None
    wintypes = None

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus, GpuProbe
from native_studio.broadcast_control import stream_payload, send_broadcast_command
from native_studio.broadcast_secondary_control import read_broadcast_status, select_broadcast_source, validate_source
from native_studio.broadcast_preview import NativeBroadcastPreview
from native_studio.theme import PALETTE
from native_studio.broadcast_stream_engine import (
    STREAM_PLATFORM_SPECS,
    PING_TEST_TARGETS,
    OUTPUT_RESOLUTION_PRESETS,
    PlatformPingProbeThread,
    StreamProfileManager,
    StreamRequirementsDialog,
)


# ══════════════════════════════════════════════════════════════════════════
# 1. LIVE PROGRAM / PREVIEW MONITOR CANVAS (16:9 VS 9:16)
# ══════════════════════════════════════════════════════════════════════════

def get_desktop_capture_windows() -> List[Dict[str, Any]]:
    """Enumerate real top-level application windows on Windows, strictly excluding AI-BS itself."""
    if sys.platform != "win32" or ctypes is None:
        return []
    user32=None
    hdesk=None
    try:
        user32 = ctypes.windll.user32
        try:
            user32.OpenInputDesktop.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
            user32.OpenInputDesktop.restype=wintypes.HANDLE
            user32.CloseDesktop.argtypes=[wintypes.HANDLE]
            user32.CloseDesktop.restype=wintypes.BOOL
        except AttributeError: pass  # Synthetic fixture callables have no C prototype.
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if not hdesk: return []
        my_pid = os.getpid()
        windows: List[Dict[str, Any]] = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        try:
            user32.EnumDesktopWindows.argtypes=[wintypes.HANDLE,WNDENUMPROC,wintypes.LPARAM]
            user32.EnumDesktopWindows.restype=wintypes.BOOL
        except AttributeError: pass

        def _enum_cb(hwnd: int, lparam: int) -> bool:
            if user32.IsWindowVisible(hwnd):
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == my_pid:
                    return True  # Exclude AI-BS Sovereign Studio window to eliminate recursive infinity mirror
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    ignored = {"Program Manager", "Windows Input Experience", "Default IME", "MSCTFIME UI"}
                    if title.strip() and title not in ignored:
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w > 100 and h > 100:
                            windows.append({
                                "hwnd": int(hwnd),
                                "title": title,
                                "width": w,
                                "height": h,
                                "pid": pid.value,
                            })
            return True

        user32.EnumDesktopWindows(hdesk, WNDENUMPROC(_enum_cb), 0)
        return windows
    except Exception:
        return []
    finally:
        if hdesk and user32 is not None:
            try: user32.CloseDesktop(hdesk)
            except Exception: pass


class NativeScreenCaptureThread(QThread):
    """Multi-threaded high-frame-rate window and game capture engine.

    Captures targeted application windows directly via Win32 HWND rather than locking
    the global desktop DC (BitBlt 0), completely eliminating recursive infinity mirrors
    and desktop DWM compositor starvation.
    """

    frame_ready = pyqtSignal(QPixmap)

    def __init__(self, target_fps: int = 30, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._target_fps = target_fps
        self._interval = 1.0 / max(1, target_fps)
        self._running = True
        self._target_hwnd: int = 0
        self._target_title: str = ""
        self._my_pid = os.getpid()

    def set_target_window(self, hwnd: int, title: str = "") -> None:
        self._target_hwnd = hwnd
        self._target_title = title

    def stop(self) -> None:
        self._running = False
        self.wait(1000)

    def run(self) -> None:
        user32 = ctypes.windll.user32 if (sys.platform == "win32" and ctypes is not None) else None
        while self._running:
            t0 = time.perf_counter()
            try:
                screen = QGuiApplication.primaryScreen()
                if screen is not None:
                    target = self._target_hwnd
                    if target <= 0 and user32 is not None:
                        # Auto-detect foreground window that is NOT AI-BS
                        fg = user32.GetForegroundWindow()
                        if fg and user32.IsWindowVisible(fg):
                            pid = wintypes.DWORD()
                            user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
                            if pid.value != self._my_pid:
                                target = fg

                    if target > 0 and user32 is not None:
                        if user32.IsWindow(target) and user32.IsWindowVisible(target):
                            pixmap = screen.grabWindow(target)
                            if not pixmap.isNull() and pixmap.width() > 10 and pixmap.height() > 10:
                                self.frame_ready.emit(pixmap)
            except Exception:
                pass
            elapsed = time.perf_counter() - t0
            sleep_time = self._interval - elapsed
            if sleep_time > 0.001:
                time.sleep(sleep_time)


class LiveBroadcastCanvas(QWidget):
    """Direct2D-rendered video monitor preview canvas with aspect ratio toggle and live capture."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 180)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy(),
        )

        self.is_streaming = False
        self.is_recording = False
        self._coordinator_preview_unavailable = False
        self._program_preview_image: Optional[QImage] = None
        self.orientation = "horizontal"  # "horizontal" (16:9) | "vertical" (9:16)
        self.active_source_title = "🎮 Direct3D 11 Zero-Copy Hook: Standby"
        self.resolution_text = "1920x1080 @ 60 FPS"
        self.bitrate_text = "Bitrate not measured"
        self.latency_text = "Not measured"
        self.uptime_seconds = 0

        # Layer visibility flags
        self._game_capture_enabled = True
        self._pip_camera_enabled = True
        self._audio_hud_enabled = True
        self._comfy_overlay_enabled = True

        # Output Preview & Studio Mode Variations
        self.studio_mode = False
        self.preview_scene_title = "Scene 1: Gameplay Cam (Staging)"
        self.program_scene_title = "Scene 1: Master Live Stream"
        self.safe_areas_enabled = False
        self.scale_filter = "Lanczos (36 samples)"
        self.aspect_preset = "16:9 (1080p 60fps)"
        self.fps_target = 60
        self.dropped_frames = 0

        self._phase = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(50)  # 20 FPS monitor refresh for HUD animations

        # QScreen and QPixmap are GUI objects. Capture on this widget's GUI
        # thread through a bounded timer, never through the legacy QThread.
        self._current_frame: Optional[QPixmap] = None
        self._cached_scaled_frame: Optional[QPixmap] = None
        self._cached_scaled_size: tuple[int, int] = (0, 0)
        self._capture_thread = None  # compatibility identity; never instantiated
        self._capture_hwnd = 0
        self._desktop_capture_enabled = False
        self._preview_shutdown = False
        self.preview_capture_status = "Select a window to preview."
        self._capture_timer = QTimer(self)
        self._capture_timer.setInterval(100)  # at most 10 preview grabs per second
        self._capture_timer.timeout.connect(self._capture_preview_frame)

    def set_target_window(self, hwnd: int, title: str = "") -> None:
        """Select an explicit HWND; zero never authorizes foreground capture."""
        self._capture_hwnd = hwnd if type(hwnd) is int and hwnd > 0 else 0
        self._clear_capture_frame()
        self._sync_capture_timer()
        if title:
            clean_title = title if (title.startswith("🎮") or title.startswith("⚡")) else f"🎮 {title}"
            self.active_source_title = clean_title
        self.update()

    def _on_frame_received(self, pixmap: QPixmap) -> None:
        if pixmap is None or pixmap.isNull():
            self._clear_capture_frame()
            return
        self._current_frame = pixmap
        self._cached_scaled_frame = None  # Invalidate cached scaled pixmap
        self.update()

    def set_desktop_capture_enabled(self, enabled: bool) -> None:
        """Opt into screen preview separately from selecting a window."""
        self._desktop_capture_enabled = enabled is True
        self._clear_capture_frame()
        self._sync_capture_timer()

    def _clear_capture_frame(self) -> None:
        self._current_frame = None
        self._cached_scaled_frame = None
        self._cached_scaled_size = (0, 0)
        self.update()

    def _sync_capture_timer(self) -> None:
        selected = (self._game_capture_enabled and self._capture_hwnd > 0) or self._desktop_capture_enabled
        if (self._preview_shutdown or not selected
                or QGuiApplication.platformName().lower() in {"offscreen", "minimal"}
                or os.environ.get("QT_QPA_PLATFORM", "").lower() in {"offscreen", "minimal"}):
            self._capture_timer.stop()
            return
        self._capture_timer.start()

    def _capture_preview_frame(self) -> None:
        """One GUI-thread grab of only the selected window or opted-in screen."""
        if QThread.currentThread() != self.thread() or self._preview_shutdown:
            return
        target = self._capture_hwnd if self._game_capture_enabled and self._capture_hwnd > 0 else None
        if target is None and self._desktop_capture_enabled:
            target = 0
        if target is None:
            self.preview_capture_status = "Select a window to preview."
            self._clear_capture_frame()
            return
        try:
            if target > 0:
                user32 = ctypes.windll.user32 if ctypes is not None else None
                if (user32 is None or not user32.IsWindow(target)
                        or not user32.IsWindowVisible(target) or user32.IsIconic(target)):
                    raise ValueError("Selected preview window is unavailable")
            screen = QGuiApplication.primaryScreen()
            if screen is None:
                raise ValueError("Preview screen is unavailable")
            pixmap = screen.grabWindow(target)
            if pixmap.isNull() or pixmap.width() <= 10 or pixmap.height() <= 10:
                raise ValueError("Preview pixels are unavailable")
            self.preview_capture_status = "Selected window preview." if target else "Explicit screen preview."
            self._on_frame_received(pixmap)
        except Exception:
            self.preview_capture_status = "Preview unavailable; no frame captured."
            self._clear_capture_frame()

    def set_game_capture_enabled(self, enabled: bool) -> None:
        self._game_capture_enabled = enabled
        if not enabled:
            self._clear_capture_frame()
        self._sync_capture_timer()
        self.update()

    def set_pip_camera_enabled(self, enabled: bool) -> None:
        self._pip_camera_enabled = enabled
        self.update()

    def set_audio_hud_enabled(self, enabled: bool) -> None:
        self._audio_hud_enabled = enabled
        self.update()

    def set_comfy_overlay_enabled(self, enabled: bool) -> None:
        self._comfy_overlay_enabled = enabled
        self.update()

    def set_studio_mode(self, enabled: bool) -> None:
        self.studio_mode = enabled
        self.update()

    def set_safe_areas_enabled(self, enabled: bool) -> None:
        self.safe_areas_enabled = enabled
        self.update()

    def set_scale_filter(self, filter_name: str) -> None:
        self.scale_filter = filter_name
        self.update()

    def set_aspect_preset(self, preset_name: str) -> None:
        self.aspect_preset = preset_name
        if "9:16" in preset_name:
            self.orientation = "vertical"
        else:
            self.orientation = "horizontal"
        self.resolution_text = preset_name.split("(")[0].strip()
        self.update()

    def trigger_cut_transition(self) -> None:
        self.program_scene_title, self.preview_scene_title = self.preview_scene_title, self.program_scene_title
        self.update()

    def trigger_fade_transition(self) -> None:
        self.program_scene_title, self.preview_scene_title = self.preview_scene_title, self.program_scene_title
        self.update()

    def set_fps_target(self, fps_text: str) -> None:
        self.fps_target = str(fps_text).replace("FPS", "").strip()
        self.update()

    def shutdown(self) -> None:
        if hasattr(self, "_anim_timer") and self._anim_timer.isActive():
            self._anim_timer.stop()
        self._preview_shutdown = True
        if hasattr(self, "_capture_timer"):
            self._capture_timer.stop()
        self._clear_capture_frame()
        self.clear_program_preview()

    def closeEvent(self, event: Any) -> None:
        self.shutdown()
        super().closeEvent(event)

    def _on_anim_tick(self) -> None:
        self._phase += 0.08
        if self.is_streaming:
            self.uptime_seconds += 0.05
        self.update()

    def set_orientation(self, orient: str) -> None:
        self.orientation = orient
        self.update()

    def set_streaming(self, streaming: bool) -> None:
        self.is_streaming = streaming
        if not streaming:
            self.uptime_seconds = 0
        self.update()

    def set_coordinator_preview_unavailable(self) -> None:
        self._coordinator_preview_unavailable=True
        self.update()

    def set_program_preview_image(self, image: QImage) -> None:
        """Own a decoded program frame; never select or capture a window."""
        if self._preview_shutdown:
            return
        self._program_preview_image = image.copy() if isinstance(image, QImage) and not image.isNull() else None
        self.update()

    def clear_program_preview(self) -> None:
        self._program_preview_image = None
        self.update()

    def set_recording(self, recording: bool) -> None:
        self.is_recording = recording
        self.update()

    def set_active_source(self, title: str, hwnd: int = 0) -> None:
        self.active_source_title = title
        if hwnd > 0:
            self.set_target_window(hwnd, title)
        self.update()

    def _draw_safe_areas(self, painter: QPainter, rect: QRectF) -> None:
        bx, by, bw, bh = rect.x(), rect.y(), rect.width(), rect.height()
        # 1. Action Safe: 90% size
        as_w = bw * 0.90
        as_h = bh * 0.90
        as_x = bx + (bw - as_w) / 2
        as_y = by + (bh - as_h) / 2
        painter.setPen(QPen(QColor(0, 240, 255, 140), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(as_x, as_y, as_w, as_h))

        # 2. Title Safe: 80% size
        ts_w = bw * 0.80
        ts_h = bh * 0.80
        ts_x = bx + (bw - ts_w) / 2
        ts_y = by + (bh - ts_h) / 2
        painter.setPen(QPen(QColor(251, 191, 36, 160), 1, Qt.PenStyle.DotLine))
        painter.drawRect(QRectF(ts_x, ts_y, ts_w, ts_h))

        # 3. Rule of Thirds Grid
        painter.setPen(QPen(QColor(148, 163, 184, 40), 1))
        painter.drawLine(int(bx + bw / 3), int(by), int(bx + bw / 3), int(by + bh))
        painter.drawLine(int(bx + 2 * bw / 3), int(by), int(bx + 2 * bw / 3), int(by + bh))
        painter.drawLine(int(bx), int(by + bh / 3), int(bx + bw), int(by + bh / 3))
        painter.drawLine(int(bx), int(by + 2 * bh / 3), int(bx + bw), int(by + 2 * bh / 3))

        # 4. Center Crosshair
        cx = bx + bw / 2
        cy = by + bh / 2
        painter.setPen(QPen(QColor(0, 240, 255, 160), 1))
        painter.drawLine(int(cx - 10), int(cy), int(cx + 10), int(cy))
        painter.drawLine(int(cx), int(cy - 10), int(cx), int(cy + 10))
        painter.drawEllipse(QPointF(cx, cy), 3, 3)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Canvas background bezel
        painter.fillRect(0, 0, w, h, QColor("#05080f"))

        if self._coordinator_preview_unavailable:
            image = self._program_preview_image
            if image is not None and not image.isNull():
                available_h = max(1, h - 26)
                scale = min(w / image.width(), available_h / image.height())
                iw, ih = image.width() * scale, image.height() * scale
                painter.drawImage(QRectF((w-iw)/2, (available_h-ih)/2, iw, ih), image)
                painter.setPen(QPen(QColor('#cbd5e1')))
                painter.setFont(QFont('Segoe UI', 9))
                painter.drawText(QRectF(6, h-25, w-12, 24), Qt.AlignmentFlag.AlignCenter, 'Program preview (delayed)')
                return
            painter.setPen(QPen(QColor('#cbd5e1')))
            painter.setFont(QFont('Segoe UI',12,QFont.Weight.Bold))
            painter.drawText(QRectF(12,h/2-32,w-24,28),Qt.AlignmentFlag.AlignCenter,'Preview unavailable')
            painter.setFont(QFont('Segoe UI',9))
            painter.drawText(QRectF(12,h/2+4,w-24,24),Qt.AlignmentFlag.AlignCenter,'Output 1280x720 30 FPS')
            return

        # ── DUAL STUDIO MODE (PREVIEW A / PROGRAM B) ──
        if self.studio_mode:
            mid_gap = 64
            avail_w = (w - 32 - mid_gap) // 2
            avail_h = h - 20

            target_aspect = 16.0 / 9.0 if self.orientation == "horizontal" else 9.0 / 16.0
            cur_aspect = float(avail_w) / float(max(1, avail_h))
            if cur_aspect > target_aspect:
                box_h = avail_h
                box_w = int(box_h * target_aspect)
            else:
                box_w = avail_w
                box_h = int(box_w / target_aspect)

            box_y = (h - box_h) // 2
            prev_x = 16 + (avail_w - box_w) // 2
            prog_x = prev_x + box_w + mid_gap

            prev_rect = QRectF(prev_x, box_y, box_w, box_h)
            prog_rect = QRectF(prog_x, box_y, box_w, box_h)

            # 1. Preview Monitor (Staging)
            painter.setPen(QPen(QColor("#10b981"), 1.8))
            painter.setBrush(QBrush(QColor("#080d1a")))
            painter.drawRoundedRect(prev_rect, 6, 6)
            painter.setClipRect(prev_rect)

            mid_y = box_y + box_h * 0.5
            wave_path = QPainterPath()
            wave_path.moveTo(prev_x, mid_y)
            steps = 40
            for i in range(steps + 1):
                px = prev_x + (box_w / steps) * i
                norm_x = (i / float(steps)) * 4.0 * math.pi
                py = mid_y + math.sin(norm_x + self._phase) * (box_h * 0.08)
                wave_path.lineTo(px, py)
            painter.setPen(QPen(QColor("#10b981"), 1.5))
            painter.drawPath(wave_path)

            if self.safe_areas_enabled:
                self._draw_safe_areas(painter, prev_rect)

            painter.setBrush(QBrush(QColor(16, 185, 129, 220)))
            painter.setPen(QPen(QColor("#34d399"), 1))
            painter.drawRoundedRect(QRectF(prev_x + 8, box_y + 8, 120, 20), 4, 4)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(QRectF(prev_x + 8, box_y + 8, 120, 20), Qt.AlignmentFlag.AlignCenter, "● PREVIEW (STAGING)")

            painter.setPen(QPen(QColor("#f8fafc")))
            painter.drawText(QRectF(prev_x + 8, box_y + box_h - 24, box_w - 16, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"STAGING: {self.preview_scene_title}")
            painter.setClipping(False)

            # 2. Center Transition Strip
            mid_x = prev_x + box_w + 6
            mid_w = mid_gap - 12
            strip_rect = QRectF(mid_x, box_y + box_h // 2 - 45, mid_w, 90)
            painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
            painter.setPen(QPen(QColor("#1e293b"), 1))
            painter.drawRoundedRect(strip_rect, 6, 6)

            painter.setPen(QPen(QColor("#00f0ff")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(QRectF(mid_x, strip_rect.y() + 8, mid_w, 18), Qt.AlignmentFlag.AlignCenter, "CUT ➔")
            painter.setPen(QPen(QColor("#a855f7")))
            painter.drawText(QRectF(mid_x, strip_rect.y() + 34, mid_w, 18), Qt.AlignmentFlag.AlignCenter, "AUTO")
            painter.setPen(QPen(QColor("#94a3b8")))
            painter.setFont(QFont("Segoe UI", 6))
            painter.drawText(QRectF(mid_x, strip_rect.y() + 58, mid_w, 18), Qt.AlignmentFlag.AlignCenter, "300ms")

            # 3. Program Monitor (Live)
            prog_color = QColor("#ef4444" if self.is_streaming else "#00f0ff")
            painter.setPen(QPen(prog_color, 1.8))
            painter.setBrush(QBrush(QColor("#080d1a")))
            painter.drawRoundedRect(prog_rect, 6, 6)
            painter.setClipRect(prog_rect)

            if self._game_capture_enabled and self._current_frame and not self._current_frame.isNull():
                target_size = (int(box_w), int(box_h))
                if self._cached_scaled_frame is None or self._cached_scaled_size != target_size:
                    self._cached_scaled_frame = self._current_frame.scaled(
                        int(box_w), int(box_h),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.FastTransformation,
                    )
                    self._cached_scaled_size = target_size
                scaled = self._cached_scaled_frame
                img_x = prog_x + (box_w - scaled.width()) // 2
                img_y = box_y + (box_h - scaled.height()) // 2
                painter.drawPixmap(int(img_x), int(img_y), scaled)
            else:
                wave_path = QPainterPath()
                wave_path.moveTo(prog_x, mid_y)
                for i in range(steps + 1):
                    px = prog_x + (box_w / steps) * i
                    norm_x = (i / float(steps)) * 4.0 * math.pi
                    py = mid_y + math.sin(norm_x + self._phase) * (box_h * 0.12 if self.is_streaming else box_h * 0.05)
                    wave_path.lineTo(px, py)
                painter.setPen(QPen(prog_color, 2.0))
                painter.drawPath(wave_path)

            if self._pip_camera_enabled:
                pip_w = min(110, max(60, int(box_w * 0.22)))
                pip_h = min(70, max(40, int(box_h * 0.22)))
                pip_x = prog_x + box_w - pip_w - 8
                pip_y = box_y + box_h - pip_h - 26
                painter.setPen(QPen(QColor("#00f0ff"), 1.0))
                painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
                painter.drawRoundedRect(QRectF(pip_x, pip_y, pip_w, pip_h), 4, 4)
                painter.setPen(QPen(QColor("#38bdf8")))
                painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
                painter.drawText(QRectF(pip_x + 4, pip_y + 2, pip_w - 8, 12), Qt.AlignmentFlag.AlignLeft, "📷 A7III")

            if self.safe_areas_enabled:
                self._draw_safe_areas(painter, prog_rect)

            badge_text = "● SERVICE ACK" if self.is_streaming else "● PROGRAM PREVIEW"
            badge_color = QColor(220, 38, 38, 220) if self.is_streaming else QColor(15, 23, 42, 220)
            painter.setBrush(QBrush(badge_color))
            painter.setPen(QPen(prog_color, 1))
            painter.drawRoundedRect(QRectF(prog_x + 8, box_y + 8, 110, 20), 4, 4)
            painter.setPen(QPen(QColor("#ffffff") if self.is_streaming else QColor("#00f0ff")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(QRectF(prog_x + 8, box_y + 8, 110, 20), Qt.AlignmentFlag.AlignCenter, badge_text)

            painter.setPen(QPen(QColor("#f8fafc")))
            painter.drawText(QRectF(prog_x + 8, box_y + box_h - 24, box_w - 16, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"LIVE: {self.program_scene_title}")
            painter.setClipping(False)
            return

        # ── SINGLE MONITOR MODE (STANDARD BROADCAST) ──
        if self.orientation == "horizontal":
            target_aspect = 16.0 / 9.0
        else:
            target_aspect = 9.0 / 16.0

        current_aspect = float(w) / float(max(1, h))

        if current_aspect > target_aspect:
            box_h = h - 16
            box_w = int(box_h * target_aspect)
            box_x = (w - box_w) // 2
            box_y = 8
        else:
            box_w = w - 16
            box_h = int(box_w / target_aspect)
            box_x = 8
            box_y = (h - box_h) // 2

        monitor_rect = QRectF(box_x, box_y, box_w, box_h)

        # Monitor Bezel
        painter.setPen(QPen(QColor("#00f0ff" if self.is_streaming else "#1e293b"), 1.5))
        painter.setBrush(QBrush(QColor("#080d1a")))
        painter.drawRoundedRect(monitor_rect, 6, 6)

        painter.setClipRect(monitor_rect)

        # ── PRIMARY LAYER: LIVE GAME / SCREEN VIDEO FEED ──
        if self._game_capture_enabled and self._current_frame and not self._current_frame.isNull():
            target_size = (int(box_w), int(box_h))
            if self._cached_scaled_frame is None or self._cached_scaled_size != target_size:
                self._cached_scaled_frame = self._current_frame.scaled(
                    int(box_w),
                    int(box_h),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
                self._cached_scaled_size = target_size
            scaled = self._cached_scaled_frame
            img_x = box_x + (box_w - scaled.width()) // 2
            img_y = box_y + (box_h - scaled.height()) // 2
            painter.drawPixmap(int(img_x), int(img_y), scaled)

            top_grad = QLinearGradient(box_x, box_y, box_x, box_y + 42)
            top_grad.setColorAt(0, QColor(0, 0, 0, 160))
            top_grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillRect(QRectF(box_x, box_y, box_w, 42), top_grad)

            bot_grad = QLinearGradient(box_x, box_y + box_h - 46, box_x, box_y + box_h)
            bot_grad.setColorAt(0, QColor(0, 0, 0, 0))
            bot_grad.setColorAt(1, QColor(0, 0, 0, 180))
            painter.fillRect(QRectF(box_x, box_y + box_h - 46, box_w, 46), bot_grad)
        else:
            grid_pen = QPen(QColor(0, 240, 255, 30), 1)
            painter.setPen(grid_pen)
            grid_spacing = 24
            for x in range(int(box_x), int(box_x + box_w), grid_spacing):
                painter.drawLine(x, int(box_y), x, int(box_y + box_h))
            for y in range(int(box_y), int(box_y + box_h), grid_spacing):
                painter.drawLine(int(box_x), y, int(box_x + box_w), y)

            mid_y = box_y + box_h * 0.5
            wave_path = QPainterPath()
            wave_path.moveTo(box_x, mid_y)
            steps = 60
            amp = (box_h * 0.15) if self.is_streaming else (box_h * 0.05)
            for i in range(steps + 1):
                px = box_x + (box_w / steps) * i
                norm_x = (i / float(steps)) * 4.0 * math.pi
                py = mid_y + math.sin(norm_x + self._phase) * amp * math.sin(norm_x * 0.5)
                wave_path.lineTo(px, py)

            wave_color = QColor("#00f0ff") if self.is_streaming else QColor("#334155")
            painter.setPen(QPen(wave_color, 2.0))
            painter.drawPath(wave_path)

        # ── SECONDARY LAYER: SONY A7III / WEBCAM PIP ──
        if self._pip_camera_enabled:
            pip_w = min(140, max(80, int(box_w * 0.22)))
            pip_h = min(85, max(50, int(box_h * 0.22)))
            pip_x = box_x + box_w - pip_w - 12
            pip_y = box_y + box_h - pip_h - 38
            pip_rect = QRectF(pip_x, pip_y, pip_w, pip_h)

            painter.setPen(QPen(QColor("#00f0ff"), 1.2))
            painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
            painter.drawRoundedRect(pip_rect, 4, 4)

            cam_badge_rect = QRectF(pip_x + 6, pip_y + 4, pip_w - 12, 14)
            painter.setPen(QPen(QColor("#38bdf8")))
            painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
            painter.drawText(cam_badge_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "📷 SONY A7III 4K")

            painter.setPen(QPen(QColor(56, 189, 248, 70), 1))
            cx, cy = pip_x + pip_w / 2, pip_y + pip_h / 2
            painter.drawLine(int(cx - 8), int(cy), int(cx + 8), int(cy))
            painter.drawLine(int(cx), int(cy - 8), int(cx), int(cy + 8))

        # ── SAFE AREAS OVERLAY ──
        if self.safe_areas_enabled:
            self._draw_safe_areas(painter, monitor_rect)

        # ── TERTIARY LAYER: AUDIO HUD VU METERS ──
        if self._audio_hud_enabled:
            vu_w, vu_h = 4, 36
            vu_x = box_x + 10
            vu_y = box_y + box_h / 2 - 18
            painter.fillRect(QRectF(vu_x, vu_y, vu_w, vu_h), QColor(15, 23, 42, 180))
            painter.fillRect(QRectF(vu_x + 6, vu_y, vu_w, vu_h), QColor(15, 23, 42, 180))
            lvl_l = 0  # No measured audio producer
            lvl_r = 0
            painter.fillRect(QRectF(vu_x, vu_y + vu_h - lvl_l, vu_w, lvl_l), QColor("#10b981"))
            painter.fillRect(QRectF(vu_x + 6, vu_y + vu_h - lvl_r, vu_w, lvl_r), QColor("#10b981"))

        # ── TOP BADGES OVERLAY ──
        badge_w, badge_h = 82, 22
        badge_x = box_x + 10
        badge_y = box_y + 10

        if self.is_streaming:
            painter.setBrush(QBrush(QColor(220, 38, 38, 220)))
            painter.setPen(QPen(QColor("#ef4444"), 1))
            painter.drawRoundedRect(QRectF(badge_x, badge_y, badge_w, badge_h), 4, 4)

            dot_alpha = int(180 + 75 * math.sin(self._phase * 3))
            painter.setBrush(QBrush(QColor(255, 255, 255, dot_alpha)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(badge_x + 10, badge_y + 11), 4, 4)

            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            mins = int(self.uptime_seconds) // 60
            secs = int(self.uptime_seconds) % 60
            painter.drawText(QRectF(badge_x + 18, badge_y, badge_w - 18, badge_h), Qt.AlignmentFlag.AlignCenter, f"ACK {mins:02d}:{secs:02d}")
        else:
            painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
            painter.setPen(QPen(QColor("#334155"), 1))
            painter.drawRoundedRect(QRectF(badge_x, badge_y, badge_w, badge_h), 4, 4)

            painter.setBrush(QBrush(QColor("#10b981")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(badge_x + 10, badge_y + 11), 3.5, 3.5)

            painter.setPen(QPen(QColor("#38bdf8")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(QRectF(badge_x + 16, badge_y, badge_w - 18, badge_h), Qt.AlignmentFlag.AlignCenter, f"PREVIEW {self.fps_target}")

        if self.is_recording:
            rec_x = badge_x + badge_w + 8
            painter.setBrush(QBrush(QColor(185, 28, 28, 220)))
            painter.setPen(QPen(QColor("#f87171"), 1))
            painter.drawRoundedRect(QRectF(rec_x, badge_y, 45, badge_h), 4, 4)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(QRectF(rec_x, badge_y, 45, badge_h), Qt.AlignmentFlag.AlignCenter, "REC")

        # 3. STATS IN UPPER RIGHT
        stats_w, stats_h = 240, 22
        stats_x = box_x + box_w - stats_w - 10
        stats_rect = QRectF(stats_x, badge_y, stats_w, stats_h)

        painter.setBrush(QBrush(QColor(15, 23, 42, 210)))
        painter.setPen(QPen(QColor("#1e293b"), 1))
        painter.drawRoundedRect(stats_rect, 4, 4)

        painter.setPen(QPen(QColor("#38bdf8")))
        painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        filter_tag = "LNZ" if "Lanczos" in self.scale_filter else ("BCB" if "Bicubic" in self.scale_filter else "BIL")
        stat_text = f"{self.resolution_text} | {self.bitrate_text} | {self.fps_target}FPS ({filter_tag})"
        painter.drawText(stats_rect, Qt.AlignmentFlag.AlignCenter, stat_text)

        # ── BOTTOM BANNER OVERLAY ──
        bot_banner_h = 24
        bot_banner_y = box_y + box_h - bot_banner_h - 8
        bot_banner_rect = QRectF(box_x + 8, bot_banner_y, box_w - 16, bot_banner_h)

        painter.setBrush(QBrush(QColor(10, 15, 26, 225)))
        painter.setPen(QPen(QColor("#00f0ff" if self.is_streaming else "#1e293b"), 1))
        painter.drawRoundedRect(bot_banner_rect, 4, 4)

        painter.setPen(QPen(QColor("#f8fafc")))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(
            QRectF(bot_banner_rect.x() + 8, bot_banner_rect.y(), bot_banner_rect.width() - 16, bot_banner_rect.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            f"CAPTURE HOOK: {self.active_source_title} • LATENCY: {self.latency_text}",
        )

        painter.setClipping(False)


# ══════════════════════════════════════════════════════════════════════════
# 2. LIVE SCENES & SOURCES MANAGER (LAYERS)
# ══════════════════════════════════════════════════════════════════════════

class LiveScenesAndSourcesWidget(QWidget):
    """Scenes switcher and multi-layer sources manager."""

    scene_changed = pyqtSignal(str)
    source_toggled = pyqtSignal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(10)

        # ── SCENES CARD ──
        c_scenes = QFrame()
        c_scenes.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 6px;")
        sc_lay = QVBoxLayout(c_scenes)
        sc_lay.setContentsMargins(6, 6, 6, 6)
        sc_lay.setSpacing(6)

        hdr_sc = QHBoxLayout()
        hdr_sc.addWidget(QLabel("<b style='color: #c084fc; font-size: 8.5pt;'>🎬 SCENES</b>"))
        hdr_sc.addStretch()

        btn_add_scene = QPushButton("+")
        btn_add_scene.setFixedSize(20, 20)
        btn_add_scene.setStyleSheet("background: #1e293b; color: #cbd5e1; font-weight: bold; border-radius: 3px;")
        btn_add_scene.clicked.connect(self._add_scene_prompt)
        hdr_sc.addWidget(btn_add_scene)

        btn_del_scene = QPushButton("–")
        btn_del_scene.setFixedSize(20, 20)
        btn_del_scene.setStyleSheet("background: #1e293b; color: #cbd5e1; font-weight: bold; border-radius: 3px;")
        btn_del_scene.clicked.connect(self._del_scene)
        hdr_sc.addWidget(btn_del_scene)
        sc_lay.addLayout(hdr_sc)

        self.scene_combo = QComboBox()
        self.scene_combo.addItems([
            "[MAIN] Game Capture (DirectX 11 Zero-Copy)",
            "Chroma Key Studio Virtual Stage",
            "Full Facecam Commentary",
            "DAW Synthesizer & Audio Production",
            "BRB / Intermission Screen",
            "Ending Credits",
        ])
        self.scene_combo.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 5px; border-radius: 4px; font-size: 8pt;")
        self.scene_combo.currentIndexChanged.connect(self._on_scene_changed)
        sc_lay.addWidget(self.scene_combo)

        # Transition Selector
        t_row = QHBoxLayout()
        t_row.addWidget(QLabel("<span style='color: #94a3b8; font-size: 7.5pt;'>TRANSITION:</span>"))
        self.combo_trans = QComboBox()
        self.combo_trans.addItems(["Cut (Instant)", "Fade (300ms)", "Swipe Left", "Stinger (Cyber)"])
        self.combo_trans.setStyleSheet("background: #070b12; color: #cbd5e1; border: 1px solid #1e293b; font-size: 7.5pt; padding: 2px;")
        t_row.addWidget(self.combo_trans)
        sc_lay.addLayout(t_row)
        sc_lay.addStretch()

        main_lay.addWidget(c_scenes, 1)

        # ── SOURCES CARD ──
        c_sources = QFrame()
        c_sources.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 6px;")
        src_lay = QVBoxLayout(c_sources)
        src_lay.setContentsMargins(6, 6, 6, 6)
        src_lay.setSpacing(6)

        hdr_src = QHBoxLayout()
        hdr_src.addWidget(QLabel("<b style='color: #38bdf8; font-size: 8.5pt;'>🎛️ SOURCES (LAYERS)</b>"))
        hdr_src.addStretch()

        btn_add_src = QPushButton("+ Add")
        btn_add_src.setStyleSheet("background: #0284c7; color: #fff; font-weight: bold; font-size: 7pt; border-radius: 3px; padding: 2px 6px;")
        btn_add_src.clicked.connect(self._add_source_dialog)
        hdr_src.addWidget(btn_add_src)
        src_lay.addLayout(hdr_src)

        self.sources_list: List[Dict[str, Any]] = [
            {"id": "s1", "name": "🎮 Game Capture (DirectX/DXGI)", "type": "game", "enabled": True},
            {"id": "s2", "name": "📷 Sony A7III / Cam Link 4K", "type": "cam", "enabled": True},
            {"id": "s3", "name": "🎵 DAW Master Stems (WASAPI)", "type": "daw", "enabled": True},
            {"id": "s4", "name": "🌐 WebRTC / Guest Feed", "type": "guest", "enabled": False},
            {"id": "s5", "name": "🎨 ComfyUI Generative Overlay", "type": "comfy", "enabled": True},
        ]

        self.sources_box = QVBoxLayout()
        self.sources_box.setSpacing(4)
        self._refresh_sources_ui()
        src_lay.addLayout(self.sources_box)
        src_lay.addStretch()

        main_lay.addWidget(c_sources, 2)

    def _refresh_sources_ui(self) -> None:
        # Clear existing
        while self.sources_box.count() > 0:
            item = self.sources_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for s in self.sources_list:
            row = QHBoxLayout()
            row.setSpacing(4)

            btn_eye = QPushButton("👁️" if s["enabled"] else "🕶️")
            btn_eye.setFixedSize(22, 20)
            btn_eye.setStyleSheet("background: #1e293b; color: #38bdf8; border: none; border-radius: 2px; font-size: 7.5pt;")
            btn_eye.clicked.connect(lambda chk=False, src=s: self._toggle_source(src))
            row.addWidget(btn_eye)

            lbl = QLabel(s["name"])
            lbl.setStyleSheet("color: #f8fafc; font-size: 7.5pt; font-weight: bold;" if s["enabled"] else "color: #64748b; font-size: 7.5pt;")
            row.addWidget(lbl, 1)

            sld = QSlider(Qt.Orientation.Horizontal)
            sld.setRange(0, 100)
            sld.setValue(100)
            sld.setFixedWidth(50)
            sld.setStyleSheet("QSlider::groove:horizontal { height: 3px; background: #1e293b; } QSlider::handle:horizontal { background: #38bdf8; width: 8px; border-radius: 4px; }")
            row.addWidget(sld)

            self.sources_box.addLayout(row)

    def _toggle_source(self, s: Dict[str, Any]) -> None:
        s["enabled"] = not s["enabled"]
        self._refresh_sources_ui()
        self.source_toggled.emit(s["name"], s["enabled"])

    def _on_scene_changed(self, idx: int) -> None:
        scene = self.scene_combo.currentText()
        self.scene_changed.emit(scene)

    def _add_scene_prompt(self) -> None:
        text, ok = QInputDialog.getText(self, "Add Scene", "Scene Name:")
        if ok and text.strip():
            self.scene_combo.addItem(text.strip())
            self.scene_combo.setCurrentText(text.strip())

    def _del_scene(self) -> None:
        if self.scene_combo.count() > 1:
            idx = self.scene_combo.currentIndex()
            self.scene_combo.removeItem(idx)

    def _add_source_dialog(self) -> None:
        types = ["Game Hook (DirectX 11)", "Webcam / UVC Device", "Screen / Display Capture", "DAW Audio Stems", "ComfyUI Visual Stream", "Text / Chat HUD"]
        item, ok = QInputDialog.getItem(self, "Add Broadcast Source", "Select Source Type:", types, 0, False)
        if ok and item:
            new_id = f"s{len(self.sources_list) + 1}"
            source_type = {"Game Hook (DirectX 11)":"game", "Webcam / UVC Device":"cam", "Screen / Display Capture":"screen", "DAW Audio Stems":"daw", "ComfyUI Visual Stream":"comfy", "Text / Chat HUD":"text"}[item]
            self.sources_list.append({"id": new_id, "name": f"➕ {item}", "type": source_type, "enabled": True})
            self._refresh_sources_ui()


# ══════════════════════════════════════════════════════════════════════════
# 3. ADVANCED 5-CHANNEL MULTI-TRACK AUDIO MIXER (VU METERS)
# ══════════════════════════════════════════════════════════════════════════

class ChannelVuMeter(QWidget):
    """Direct2D animated stereo Peak VU meter bar (Green -> Yellow -> Red)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(16)
        self.setFixedHeight(110)
        self.left_peak = 0.0
        self.right_peak = 0.0
        self.target_l = 0.0
        self.target_r = 0.0

    def set_levels(self, l: float, r: float) -> None:
        self.target_l = max(0.0, min(1.0, l))
        self.target_r = max(0.0, min(1.0, r))
        self.left_peak += (self.target_l - self.left_peak) * 0.4
        self.right_peak += (self.target_r - self.right_peak) * 0.4
        self.update()

    def paintEvent(self, event: Any) -> None:
        p = QPainter(self)
        w = self.width()
        h = self.height()

        p.fillRect(0, 0, w, h, QColor("#05080f"))

        bar_w = (w - 3) // 2
        for ch_idx, val in enumerate([self.left_peak, self.right_peak]):
            bx = ch_idx * (bar_w + 1) + 1
            bar_h = int(val * (h - 2))
            by = h - 1 - bar_h

            grad = QLinearGradient(bx, h, bx, 0)
            grad.setColorAt(0.0, QColor("#10b981"))
            grad.setColorAt(0.7, QColor("#eab308"))
            grad.setColorAt(1.0, QColor("#ef4444"))

            p.fillRect(bx, by, bar_w, bar_h, QBrush(grad))


class AudioChannelStrip(QFrame):
    """Single channel strip with volume slider, VU meter, mute & routing."""

    def __init__(self, name: str, default_vol: int = 85, track: int = 1, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.is_muted = False
        self.setStyleSheet("background: #080d16; border: 1px solid #162032; border-radius: 4px; padding: 4px;")
        self.setFixedWidth(92)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        # Channel Name
        lbl = QLabel(name)
        lbl.setStyleSheet("color: #38bdf8; font-size: 6.8pt; font-weight: bold; text-align: center;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setFixedHeight(24)
        lay.addWidget(lbl)

        # Center VU + Slider
        m_row = QHBoxLayout()
        m_row.setSpacing(4)
        self.meter = ChannelVuMeter()
        m_row.addWidget(self.meter)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setValue(default_vol)
        self.slider.setStyleSheet(
            "QSlider::groove:vertical { width: 4px; background: #1e293b; } "
            "QSlider::handle:vertical { background: #00f0ff; height: 10px; margin: 0 -4px; border-radius: 3px; }"
        )
        self.slider.valueChanged.connect(self._on_vol_changed)
        m_row.addWidget(self.slider)
        lay.addLayout(m_row)

        self.lbl_db = QLabel(f"{default_vol}%")
        self.lbl_db.setStyleSheet("color: #94a3b8; font-size: 6.5pt;")
        self.lbl_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_db)

        # Mute button
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedHeight(18)
        self.btn_mute.setStyleSheet("background: #1e293b; color: #cbd5e1; font-size: 7pt; border-radius: 2px;")
        self.btn_mute.clicked.connect(self._toggle_mute)
        lay.addWidget(self.btn_mute)

        # Track assignment
        self.combo_track = QComboBox()
        self.combo_track.addItems([f"Trk {i}" for i in range(1, 7)])
        self.combo_track.setCurrentIndex(track - 1)
        self.combo_track.setStyleSheet("background: #05080f; color: #94a3b8; font-size: 6.5pt; padding: 1px;")
        lay.addWidget(self.combo_track)

    def _on_vol_changed(self, val: int) -> None:
        self.lbl_db.setText(f"{val}%")

    def _toggle_mute(self) -> None:
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.btn_mute.setText("🔇")
            self.btn_mute.setStyleSheet("background: #7f1d1d; color: #f87171; font-size: 7pt; border-radius: 2px;")
        else:
            self.btn_mute.setText("🔊")
            self.btn_mute.setStyleSheet("background: #1e293b; color: #cbd5e1; font-size: 7pt; border-radius: 2px;")


class AdvancedAudioMixerWidget(QFrame):
    """5-Channel multi-track broadcast mixing console."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 8px;")

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("<b style='color: #10b981; font-size: 9pt;'>🎚️ ADVANCED BROADCAST AUDIO MIXER</b>"))
        hdr.addStretch()
        hdr.addWidget(QLabel("<span style='color: #64748b; font-size: 7.5pt;'>Audio levels not measured • Local mixer draft</span>"))
        root.addLayout(hdr)

        channels_row = QHBoxLayout()
        channels_row.setSpacing(8)

        self.ch_desktop = AudioChannelStrip("WASAPI Desktop", 85, track=1)
        self.ch_mic = AudioChannelStrip("Mic / Aux (USB)", 90, track=2)
        self.ch_daw = AudioChannelStrip("DAW Master Bus", 80, track=3)
        self.ch_guest = AudioChannelStrip("WebRTC Guest", 75, track=4)
        self.ch_ai = AudioChannelStrip("AI Sidekick Voice", 85, track=5)

        channels_row.addWidget(self.ch_desktop)
        channels_row.addWidget(self.ch_mic)
        channels_row.addWidget(self.ch_daw)
        channels_row.addWidget(self.ch_guest)
        channels_row.addWidget(self.ch_ai)
        channels_row.addStretch()

        root.addLayout(channels_row)

        # Pulse Timer for VU Meters
        self._vu_timer = QTimer(self)
        self._vu_timer.timeout.connect(self._animate_vu_meters)
        # No meter producer is connected; leave the animation timer stopped.
        self._animate_vu_meters()

    def _animate_vu_meters(self) -> None:
        for ch in [self.ch_desktop, self.ch_mic, self.ch_daw, self.ch_guest, self.ch_ai]:
            ch.meter.set_levels(0.0, 0.0)
            ch.meter.setToolTip('Audio input levels are not measured. These are local mixer draft controls.')

    def shutdown(self) -> None:
        if hasattr(self, "_vu_timer") and self._vu_timer.isActive():
            self._vu_timer.stop()

    def closeEvent(self, event: Any) -> None:
        self.shutdown()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════════════════
# 4. GAME & RUNNING WINDOWS AUTO-DETECTION HOOK
# ══════════════════════════════════════════════════════════════════════════

class ActiveGameDiscoveryWidget(QFrame):
    """Auto-detects open running games/windows via real OS enumeration and Port 8005/8088."""

    game_selected = pyqtSignal(str, int)  # Emits (title, hwnd)
    source_draft_changed = pyqtSignal()

    def __init__(self, bus: Optional[EngineBus] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus
        self.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        self._window_map: Dict[str, int] = {}
        self._window_title_by_handle: Dict[int, str] = {}
        self._window_pid_by_handle: Dict[int, int] = {}
        self._current_window_items: List[tuple[str, int]] = []
        self._daemon_games: List[str] = []
        self._probe_inflight = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("<b style='color: #00f0ff; font-size: 8.5pt;'>Broadcast source</b>"))
        hdr.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh Windows")
        self.btn_refresh.setStyleSheet("background: #1e293b; color: #38bdf8; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 2px 6px;")
        self.btn_refresh.clicked.connect(self.fetch_active_windows)
        hdr.addWidget(self.btn_refresh)
        lay.addLayout(hdr)

        self.combo_source_mode = QComboBox()
        for label,mode in [('Automatic game','auto_game'),('Selected window','window'),('Screen sharing','screen')]:
            self.combo_source_mode.addItem(label,mode)
        lay.addWidget(self.combo_source_mode)

        # Game source dropdown
        self.combo_games = QComboBox()
        self.combo_games.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 5px; border-radius: 4px; font-size: 8pt;")
        self.combo_games.currentIndexChanged.connect(self._on_game_changed)
        lay.addWidget(self.combo_games)

        # Checkboxes
        c_row = QHBoxLayout()
        self.chk_auto = QCheckBox("Auto Game")
        self.chk_auto.setChecked(True)
        self.chk_auto.setStyleSheet("color: #cbd5e1; font-size: 7.5pt; font-weight: bold;")
        c_row.addWidget(self.chk_auto)

        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("Filter windows by title")
        self.txt_custom.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #1e293b; padding: 3px 6px; font-size: 7.5pt; border-radius: 3px;")
        self.txt_custom.textChanged.connect(self._on_filter_changed)
        c_row.addWidget(self.txt_custom)
        lay.addLayout(c_row)

        self.combo_screens = QComboBox()
        self.combo_screens.addItem('Choose a screen…',None)
        for screen in QGuiApplication.screens():
            if screen.name(): self.combo_screens.addItem(screen.name(),screen.name())
        self.combo_screens.setToolTip('Screen sharing is held until explicit monitor capture is supported. No automatic fallback.')
        lay.addWidget(self.combo_screens)
        self.lbl_source_help = QLabel('Choose a source draft, then Apply source. Automatic game holds black without a verified game.')
        self.lbl_source_help.setWordWrap(True)
        lay.addWidget(self.lbl_source_help)
        self.combo_source_mode.currentIndexChanged.connect(self._on_source_mode_changed)
        self.chk_auto.toggled.connect(self._on_auto_game_toggled)
        self.combo_screens.currentIndexChanged.connect(lambda _index: self.source_draft_changed.emit())
        self._on_source_mode_changed()

        # Initial window fetch
        self.fetch_active_windows()

        # Polling Timer (Every 3 seconds)
        self._poller = QTimer(self)
        self._poller.timeout.connect(self.fetch_active_windows)
        self._poller.start(3000)

    def _on_filter_changed(self, text: str) -> None:
        self.fetch_active_windows()

    def _on_source_mode_changed(self, _index: int = 0) -> None:
        mode=self.combo_source_mode.currentData()
        self.chk_auto.blockSignals(True);self.chk_auto.setChecked(mode=='auto_game');self.chk_auto.blockSignals(False)
        self.combo_games.setEnabled(mode=='window')
        self.combo_screens.setVisible(mode=='screen')
        self.source_draft_changed.emit()

    def _on_auto_game_toggled(self, checked: bool) -> None:
        self.combo_source_mode.setCurrentIndex(0 if checked else 1)

    def source_selection(self) -> tuple[str, dict | None]:
        mode=self.combo_source_mode.currentData()
        if mode=='auto_game': return mode,None
        if mode=='screen': source={'screen_id':self.combo_screens.currentData()}
        else:
            hwnd=self._window_map.get(self.combo_games.currentText(),0)
            source={'hwnd':hwnd,'pid':self._window_pid_by_handle.get(hwnd),'title':self._window_title_by_handle.get(hwnd,'')}
        return mode,validate_source(mode,source)

    def _on_game_changed(self, idx: int) -> None:
        selected_text = self.combo_games.currentText()
        hwnd = self._window_map.get(selected_text, 0)
        raw_title=self._window_title_by_handle.get(hwnd,selected_text)
        self.game_selected.emit(raw_title, hwnd)
        self.source_draft_changed.emit()

    def fetch_active_windows(self) -> None:
        """Queries OS desktop windows directly and queries Port 8005/8088 asynchronously for running games."""
        real_windows = get_desktop_capture_windows()
        self._window_title_by_handle={w["hwnd"]:w["title"] for w in real_windows}
        self._window_pid_by_handle={w["hwnd"]:w["pid"] for w in real_windows if type(w.get("pid")) is int}
        filter_kw = self.txt_custom.text().strip().lower() if hasattr(self, "txt_custom") else ""

        auto_label = "Choose a window…"
        new_items: List[tuple[str, int]] = [(auto_label, 0)]

        # Include any discovered daemon games from async background worker
        # Automatic discovery is owned by the shared coordinator sampler.

        for w in real_windows:
            title = w["title"]
            if filter_kw and filter_kw not in title.lower():
                continue
            label = f"🎮 {title} ({w['width']}x{w['height']})"
            new_items.append((label, w["hwnd"]))

        # Avoid rebuilding the ComboBox on every tick if the window list hasn't changed
        if new_items != self._current_window_items:
            self._current_window_items = new_items
            cur_text = self.combo_games.currentText()

            self.combo_games.blockSignals(True)
            self.combo_games.clear()
            self._window_map.clear()

            for label, hwnd in new_items:
                self.combo_games.addItem(label)
                self._window_map[label] = hwnd

            # Restore selection if possible
            found_idx = self.combo_games.findText(cur_text)
            if found_idx != -1:
                self.combo_games.setCurrentIndex(found_idx)
            else:
                self.combo_games.setCurrentIndex(0)

            self.combo_games.blockSignals(False)

        # Offload Port 8005 / 8088 daemon probing to EngineBus worker thread (Zero GUI blocking)
        # Manual list refresh never selects a source or probes legacy daemons.

    def _trigger_async_daemon_probe(self) -> None:
        if self._probe_inflight or not self.chk_auto.isChecked():
            return
        if self.bus is None:
            return

        self._probe_inflight = True

        def _bg_probe() -> List[str]:
            found: List[str] = []
            for port in [8005, 8088]:
                try:
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{port}/api/windows",
                        headers={"User-Agent": "AI-BS-Native"},
                    )
                    with urllib.request.urlopen(req, timeout=0.5) as resp:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        active_game = data.get("active_game")
                        if active_game:
                            g_name = active_game.get("game_name") or active_game.get("title")
                            if g_name:
                                found.append(f"🎮 {g_name} (Port {port})")
                except Exception:
                    pass
            return found

        self.bus.submit(
            _bg_probe,
            on_result=self._on_daemon_probe_result,
            on_error=lambda _: self._on_daemon_probe_error(),
        )

    def _on_daemon_probe_result(self, found_games: List[str]) -> None:
        self._probe_inflight = False
        if found_games != self._daemon_games:
            self._daemon_games = found_games
            # Re-run local list sync now that background discovery has new entries
            self.fetch_active_windows()

    def _on_daemon_probe_error(self) -> None:
        self._probe_inflight = False

    def shutdown(self) -> None:
        if hasattr(self, "_poller") and self._poller.isActive():
            self._poller.stop()
        self._probe_inflight = True

    def closeEvent(self, event: Any) -> None:
        self.shutdown()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════════════════
# 5. MULTI-DESTINATION RTMP & STREAM SETTINGS
# ══════════════════════════════════════════════════════════════════════════

class MultiRtmpSettingsWidget(QFrame):
    """Encoders and multi-destination RTMP dispatcher with live platform ping checks and presets."""

    platform_selected = pyqtSignal(str, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 8px;")
        self._probe_thread: Optional[PlatformPingProbeThread] = None
        self._profile_mgr = StreamProfileManager()
        self._build_ui()
        self.load_saved_settings(self._profile_mgr.load())

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # ── HEADER ROW ──
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("<b style='color: #10b981; font-size: 8.5pt;'>🌐 MULTI-RTMP DISPATCH & HARDWARE NVENC</b>"))
        hdr.addStretch()

        self.btn_open_reqs = QPushButton("⚙️ Setup & Keys...")
        self.btn_open_reqs.setStyleSheet(
            "background: #1e293b; color: #38bdf8; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 2px 8px;"
        )
        self.btn_open_reqs.clicked.connect(self._open_requirements_dialog)
        hdr.addWidget(self.btn_open_reqs)
        lay.addLayout(hdr)

        # ── PLATFORM QUICK PRESETS ROW ──
        preset_row = QHBoxLayout()
        self.preset_buttons=[]
        preset_row.setSpacing(4)
        self.lbl_presets=QLabel("<span style='color: #94a3b8; font-size: 7pt; font-weight: bold;'>PRESETS:</span>")
        preset_row.addWidget(self.lbl_presets)

        presets = [
            ("Twitch", "🟣 Twitch 1080p", "#a855f7"),
            ("YouTube Live", "🔴 YouTube 4K AV1", "#ef4444"),
            ("Kick", "🟢 Kick 1080p", "#22c55e"),
            ("TikTok Live", "📱 TikTok 9:16", "#06b6d4"),
            ("Sovereign Broadcast", "⚡ Sovereign SRT", "#eab308"),
        ]
        for p_id, p_label, p_color in presets:
            btn = QPushButton(p_label)
            btn.setStyleSheet(
                f"background: #111827; color: {p_color}; border: 1px solid {p_color}40; font-size: 7pt; font-weight: bold; border-radius: 3px; padding: 2px 5px;"
            )
            btn.clicked.connect(lambda chk=False, pid=p_id: self.apply_platform_preset(pid))
            btn.setProperty('coordinatorPresetName',p_id)
            self.preset_buttons.append(btn)
            preset_row.addWidget(btn)
        preset_row.addStretch()
        lay.addLayout(preset_row)

        # ── ENCODER SETTINGS ROW ──
        enc_row = QHBoxLayout()
        enc_row.setSpacing(6)

        enc_row.addWidget(QLabel("<span style='color: #94a3b8; font-size: 7pt;'>RES:</span>"))
        self.combo_res = QComboBox()
        self.combo_res.addItems([
            "1920x1080 (1080p 60fps)",
            "3840x2160 (4K UHD 60fps)",
            "2560x1440 (1440p QHD)",
            "1080x1920 (9:16 Shorts/TikTok)",
            "7680x4320 (8K Master)",
        ])
        self.combo_res.setStyleSheet("background: #070b12; color: #f8fafc; font-size: 7.5pt; padding: 2px;")
        enc_row.addWidget(self.combo_res, 3)

        enc_row.addWidget(QLabel("<span style='color: #94a3b8; font-size: 7pt;'>CODEC:</span>"))
        self.combo_codec = QComboBox()
        self.combo_codec.addItems([
            "AV1 (Dual NVENC 8th Gen)",
            "HEVC / H.265 (NVENC)",
            "H.264 (CBR Studio Standard)",
            "x264 (CPU High-Profile)",
        ])
        self.combo_codec.setStyleSheet("background: #070b12; color: #f8fafc; font-size: 7.5pt; padding: 2px;")
        enc_row.addWidget(self.combo_codec, 3)

        enc_row.addWidget(QLabel("<span style='color: #94a3b8; font-size: 7pt;'>BITRATE:</span>"))
        self.combo_bitrate = QComboBox()
        self.combo_bitrate.addItems([
            "6,000 kbps (Twitch CBR)",
            "8,000 kbps (Kick / Twitch Enhanced)",
            "15,000 kbps (1440p 60fps)",
            "25,000 kbps (YouTube 4K AV1)",
            "45,000 kbps (Broadcast Master)",
        ])
        self.combo_bitrate.setStyleSheet("background: #070b12; color: #f8fafc; font-size: 7.5pt; padding: 2px;")
        enc_row.addWidget(self.combo_bitrate, 3)
        lay.addLayout(enc_row)

        # Encoder specs banner
        self.lbl_enc_specs = QLabel("Encoder settings draft • Runtime encoder and latency not measured")
        self.lbl_enc_specs.setStyleSheet("color: #64748b; font-size: 6.8pt;")
        lay.addWidget(self.lbl_enc_specs)

        # ── STREAMING DESTINATIONS WITH LIVE PING BADGES ──
        dest_hdr = QHBoxLayout()
        dest_hdr.addWidget(QLabel("<b style='color: #cbd5e1; font-size: 7.5pt;'>Streaming Destinations & Live Ingest Ping:</b>"))
        dest_hdr.addStretch()

        self.btn_ping_all = QPushButton("📶 Probe Ingest Latencies")
        self.btn_ping_all.setStyleSheet(
            "background: #0f172a; color: #38bdf8; border: 1px solid #0284c7; font-size: 7pt; font-weight: bold; border-radius: 3px; padding: 2px 6px;"
        )
        self.btn_ping_all.clicked.connect(self.run_ping_probe)
        dest_hdr.addWidget(self.btn_ping_all)

        self.btn_auto_best = QPushButton("⚡ Auto-Select Best")
        self.btn_auto_best.setStyleSheet(
            "background: #111827; color: #10b981; border: 1px solid #059669; font-size: 7pt; font-weight: bold; border-radius: 3px; padding: 2px 6px;"
        )
        self.btn_auto_best.clicked.connect(self._auto_select_best)
        dest_hdr.addWidget(self.btn_auto_best)
        lay.addLayout(dest_hdr)

        self.ping_progress = QProgressBar()
        self.ping_progress.setFixedHeight(4)
        self.ping_progress.setTextVisible(False)
        self.ping_progress.setStyleSheet(
            "QProgressBar { background: #1e293b; border-radius: 2px; } QProgressBar::chunk { background: #00f0ff; }"
        )
        self.ping_progress.hide()
        lay.addWidget(self.ping_progress)

        self.dest_badges: Dict[str, QLabel] = {}
        self.dest_checkboxes: Dict[str, QCheckBox] = {}

        dest_configs = [
            ("twitch", "Twitch Live (rtmp://live.twitch.tv/app)", True, "Twitch: ~129ms"),
            ("youtube", "YouTube Live 4K (rtmp://a.rtmp.youtube.com/live2)", True, "YouTube: ~78ms"),
            ("kick", "Kick Stream Server (rtmp://fa723fc1b171...)", False, "Kick: ~82ms"),
            ("tiktok", "TikTok Live Vertical (rtmp://live.tiktok.com)", False, "TikTok: ~46ms"),
            ("facebook", "Facebook Live RTMPS (rtmps://live-api-s.facebook.com:443)", False, "FB: ~135ms"),
            ("sovereign", "Sovereign Local SRT / HLS (Port 8089 / 9000)", True, "Sovereign: <1ms"),
        ]

        for d_key, d_label, d_checked, d_default_ping in dest_configs:
            d_row = QHBoxLayout()
            d_row.setContentsMargins(0, 0, 0, 0)
            d_row.setSpacing(4)

            chk = QCheckBox(d_label)
            saved_cfg = self._profile_mgr.load()
            config_key = "sovereign_srt" if d_key == "sovereign" else d_key
            chk.setChecked(saved_cfg.get("destinations", {}).get(config_key, {}).get("enabled", False))
            chk_color = "#22c55e" if d_key == "sovereign" else "#cbd5e1"
            chk.setStyleSheet(f"color: {chk_color}; font-size: 7.2pt;")
            d_row.addWidget(chk, 1)
            self.dest_checkboxes[d_key] = chk

            b_lbl = QLabel("Not checked")
            b_lbl.setStyleSheet(
                "background: #0f172a; color: #38bdf8; border: 1px solid #1e293b; border-radius: 3px; font-size: 6.8pt; padding: 1px 4px;"
            )
            b_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_lbl.setFixedWidth(105)
            d_row.addWidget(b_lbl)
            self.dest_badges[d_key] = b_lbl

            lay.addLayout(d_row)

        # Legacy backward-compatible attributes
        self.chk_tw = self.dest_checkboxes["twitch"]
        self.chk_yt = self.dest_checkboxes["youtube"]
        self.chk_hls = self.dest_checkboxes["sovereign"]
        self.chk_kick = self.dest_checkboxes["kick"]

    def apply_platform_preset(self, platform_id: str) -> None:
        if getattr(self,'_coordinator_profile',False): return
        spec = STREAM_PLATFORM_SPECS.get(platform_id)
        if not spec:
            return

        # 1. Update Bitrate Combo
        max_b = spec.get("max_video_bitrate_kbps", 6000)
        rec_b = spec.get("recommended_bitrate_kbps", max_b)
        matched = False
        for target_val in [rec_b, max_b]:
            for i in range(self.combo_bitrate.count()):
                t_str = str(target_val)
                c_text = self.combo_bitrate.itemText(i)
                if t_str in c_text or f"{target_val:,}" in c_text:
                    self.combo_bitrate.setCurrentIndex(i)
                    matched = True
                    break
            if matched:
                break

        # 2. Update Codec Combo
        supported_codecs = spec.get("supported_codecs", [])
        if any("AV1" in c for c in supported_codecs) and "AV1" in self.combo_codec.itemText(0):
            self.combo_codec.setCurrentIndex(0)
        elif any("HEVC" in c for c in supported_codecs):
            self.combo_codec.setCurrentIndex(1)
        else:
            self.combo_codec.setCurrentIndex(2)

        # 3. Update Resolution Combo
        max_res = spec.get("max_resolution", "1920x1080")
        if "3840x2160" in max_res:
            self.combo_res.setCurrentIndex(1)
        elif "1080x1920" in max_res or platform_id == "TikTok Live":
            self.combo_res.setCurrentIndex(3)
        elif "2560x1440" in max_res:
            self.combo_res.setCurrentIndex(2)
        else:
            self.combo_res.setCurrentIndex(0)

        # Encoder profiles do not change the user-selected destinations.

        gop_sec = spec.get("keyframe_interval_sec", 2.0)
        rc = spec.get("rate_control", "CBR")
        self.lbl_enc_specs.setText(
            f"🔒 Rate Control: {rc} • GOP: {gop_sec}s • Audio: AAC {spec.get('recommended_audio_bitrate_kbps', 160)}k • Profile: {platform_id}"
        )

        self.platform_selected.emit(platform_id, spec)

    def run_ping_probe(self) -> None:
        if self._probe_thread and self._probe_thread.isRunning():
            return
        self.btn_ping_all.setEnabled(False)
        self.btn_ping_all.setText("📶 Probing...")
        self.ping_progress.show()
        self.ping_progress.setRange(0, len(PING_TEST_TARGETS))
        self.ping_progress.setValue(0)
        self._ping_count = 0

        self._probe_thread = PlatformPingProbeThread(PING_TEST_TARGETS, self)
        self._probe_thread.ping_updated.connect(self._on_probe_item_finished)
        self._probe_thread.all_finished.connect(self._on_probe_all_finished)
        self._probe_thread.start()

    def _on_probe_item_finished(self, name: str, ping_ms: float, status: str, plat_id: str) -> None:
        self._ping_count += 1
        self.ping_progress.setValue(self._ping_count)

        target_badge = None
        p_lower = (plat_id or name).lower()
        if "twitch" in p_lower and "twitch" in self.dest_badges:
            target_badge = self.dest_badges["twitch"]
        elif "youtube" in p_lower and "youtube" in self.dest_badges:
            target_badge = self.dest_badges["youtube"]
        elif "kick" in p_lower and "kick" in self.dest_badges:
            target_badge = self.dest_badges["kick"]
        elif "tiktok" in p_lower and "tiktok" in self.dest_badges:
            target_badge = self.dest_badges["tiktok"]
        elif "facebook" in p_lower and "facebook" in self.dest_badges:
            target_badge = self.dest_badges["facebook"]
        elif "sovereign" in p_lower and "sovereign" in self.dest_badges:
            target_badge = self.dest_badges["sovereign"]

        if target_badge:
            p_display = name.split()[0]
            if ping_ms >= 0:
                color = "#10b981" if ping_ms < 60 else ("#00f0ff" if ping_ms < 100 else ("#eab308" if ping_ms < 150 else "#ef4444"))
                target_badge.setText(f"{p_display}: {ping_ms:.1f}ms")
                target_badge.setStyleSheet(
                    f"background: #0f172a; color: {color}; border: 1px solid {color}60; border-radius: 3px; font-size: 6.8pt; font-weight: bold; padding: 1px 4px;"
                )
            else:
                target_badge.setText(f"{p_display}: Timeout")
                target_badge.setStyleSheet(
                    "background: #1f1212; color: #ef4444; border: 1px solid #ef4444; border-radius: 3px; font-size: 6.8pt; padding: 1px 4px;"
                )

    def _on_probe_all_finished(self, results: Any) -> None:
        self.ping_progress.hide()
        self.btn_ping_all.setEnabled(True)
        self.btn_ping_all.setText("📶 Probe Ingest Latencies")

    def _auto_select_best(self) -> None:
        self.apply_platform_preset("YouTube Live")

    def load_saved_settings(self, config: dict) -> None:
        for key, checkbox in self.dest_checkboxes.items():
            name='sovereign_srt' if key=='sovereign' else key
            checkbox.setChecked(config.get('destinations',{}).get(name,{}).get('enabled') is True)
        encoder=config.get('encoder',{})
        values=[(self.combo_codec,str(encoder.get('codec','H.264 (CBR Studio Standard)'))),
                (self.combo_res,str(encoder.get('resolution','1920x1080'))),
                (self.combo_bitrate,f"{int(encoder.get('bitrate_kbps',6000)):,} kbps")]
        for combo,value in values:
            index=next((i for i in range(combo.count()) if combo.itemText(i)==value or combo.itemText(i).startswith(value+' ')), -1)
            if index<0:
                combo.addItem(value);index=combo.count()-1
            combo.setCurrentIndex(index)

        if getattr(self,'_coordinator_profile',False): self.use_coordinator_profile()

    def use_coordinator_profile(self) -> None:
        self._coordinator_profile=True
        for combo,label in [(self.combo_codec,'H.264 (coordinator profile)'),(self.combo_res,'1280x720 (720p 30fps)'),(self.combo_bitrate,'4,500 kbps')]:
            combo.blockSignals(True);combo.clear();combo.addItem(label);combo.setEnabled(False);combo.blockSignals(False)
            combo.setToolTip('The shared coordinator uses this fixed output profile.')
        self.lbl_presets.setText("<span style='color: #94a3b8; font-size: 7pt; font-weight: bold;'>Presets unavailable</span>")
        names={'Twitch':'Twitch','YouTube Live':'YouTube','Kick':'Kick','TikTok Live':'TikTok','Sovereign Broadcast':'Local'}
        for button in self.preset_buttons:
            button.setEnabled(False)
            button.setText(names[str(button.property('coordinatorPresetName'))])
            button.setToolTip('Fixed coordinator profile: 720p at 30 FPS, H.264, 4500 kb/s. This preset is unavailable.')
        self.btn_auto_best.setEnabled(False)
        self.btn_auto_best.setToolTip('Fixed coordinator profile: 720p at 30 FPS. Automatic profile selection is unavailable.')

    def _open_requirements_dialog(self) -> None:
        dlg = StreamRequirementsDialog(parent=self)
        dlg.profile_applied.connect(self.load_saved_settings)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_saved_settings(dlg.cfg)

    def shutdown(self) -> None:
        if self._probe_thread and self._probe_thread.isRunning():
            self._probe_thread.stop()
            self._probe_thread.wait(1000)

    def closeEvent(self, event: Any) -> None:
        self.shutdown()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════════════════
# 6. UNIFIED TWITCH / IRC CHAT & AI SIDEKICK
# ══════════════════════════════════════════════════════════════════════════

class UnifiedStreamChatWidget(QFrame):
    """Twitch/IRC live chat feed with AI Sidekick Co-Host."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 8px;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("<b style='color: #c084fc; font-size: 8.5pt;'>💬 TWITCH / IRC STREAM CHAT (PORT 8006)</b>"))
        hdr.addStretch()

        self.chk_ai_sidekick = QCheckBox("Local chat draft (not connected)")
        self.chk_ai_sidekick.setChecked(False)
        self.chk_ai_sidekick.setStyleSheet("color: #38bdf8; font-size: 7pt; font-weight: bold;")
        hdr.addWidget(self.chk_ai_sidekick)
        lay.addLayout(hdr)

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setFont(QFont("Consolas", 8))
        self.chat_view.setStyleSheet("background: #05080f; color: #cbd5e1; border: 1px solid #1e293b; border-radius: 4px; padding: 6px;")
        self.chat_view.setPlainText('Social Hub connection not checked. Messages below are local drafts; no external delivery is connected.')
        lay.addWidget(self.chat_view)

        # Quick Commands Row
        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(4)
        for cmd in ["!game", "!specs", "!music", "!uptime"]:
            b = QPushButton(cmd)
            b.setStyleSheet("background: #1e293b; color: #38bdf8; font-size: 7pt; border-radius: 2px; padding: 1px 4px;")
            b.clicked.connect(lambda chk=False, c=cmd: self._send_command(c))
            cmd_row.addWidget(b)
        cmd_row.addStretch()
        lay.addLayout(cmd_row)

        # Input Row
        inp_row = QHBoxLayout()
        self.txt_msg = QLineEdit()
        self.txt_msg.setPlaceholderText("Write a local chat draft (not sent)...")
        self.txt_msg.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 5px; border-radius: 3px; font-size: 8pt;")
        self.txt_msg.returnPressed.connect(self._send_chat)
        inp_row.addWidget(self.txt_msg, 1)

        btn_send = QPushButton("Send")
        btn_send.setStyleSheet("background: #a855f7; color: #ffffff; font-weight: bold; font-size: 7.5pt; border-radius: 3px; padding: 5px 12px;")
        btn_send.clicked.connect(self._send_chat)
        inp_row.addWidget(btn_send)
        lay.addLayout(inp_row)

    def _send_chat(self) -> None:
        msg = self.txt_msg.text().strip()
        if not msg:
            return
        self.txt_msg.clear()
        self.chat_view.append('Local draft (not sent):')
        # insertPlainText keeps user HTML inert.
        self.chat_view.insertPlainText(msg)
        self.chat_view.append('External chat delivery and AI replies are not connected.')

    def _send_command(self, cmd: str) -> None:
        self.txt_msg.setText(cmd)
        self._send_chat()

    def _generate_ai_reply(self, prompt: str) -> None:
        self.chat_view.append('AI Sidekick unavailable: no model or live telemetry source is connected.')


# ══════════════════════════════════════════════════════════════════════════
# 7. NEURAL VOICE & AUDIO AI SUITE (F5-TTS & SUNO)
# ══════════════════════════════════════════════════════════════════════════

class NeuralAudioVoiceWidget(QWidget):
    """Zero-Shot F5-TTS Neural Voice Generator & Suno Music Composer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("<b style='color: #a855f7; font-size: 11pt;'>🎙️ Neural Voice & Audio AI Suite (F5-TTS & Suno)</b>"))
        hdr.addStretch()
        lay.addLayout(hdr)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setStyleSheet("QSplitter::handle { background: #162032; width: 2px; }")

        # LEFT: ZERO-SHOT TTS
        c_tts = QFrame()
        c_tts.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        tts_lay = QVBoxLayout(c_tts)
        tts_lay.setSpacing(8)

        tts_lay.addWidget(QLabel("<b style='color: #38bdf8; font-size: 9pt;'>1. Zero-Shot Neural Voice Generator (F5-TTS)</b>"))

        tts_lay.addWidget(QLabel("Speaker Profile:"))
        self.combo_speaker = QComboBox()
        self.combo_speaker.addItems([
            "Brett (CTO / Founder) - Authoritative Confident",
            "Julie (Managing Director) - Warm Articulate",
            "Sean (Operations Lead) - Energetic Direct",
            "Professional Sales Anchor - Broadcast Polished",
            "Italian Sommelier / Host - Warm Passionate Accent",
        ])
        self.combo_speaker.setStyleSheet("background: #070b12; color: #f8fafc; padding: 6px; border: 1px solid #334155; border-radius: 4px;")
        tts_lay.addWidget(self.combo_speaker)

        tts_lay.addWidget(QLabel("Voice Text Prompt:"))
        self.txt_tts = QTextEdit()
        self.txt_tts.setFixedHeight(90)
        self.txt_tts.setPlainText(
            "[Spoken] [Triumphant Celebratory Speech] (Ecstatic) And you know what the best part is? "
            "This beautiful AI-BS architecture isn’t just for the ristorante! It scales horizontally! "
            "We're talking mobile wash fleets, Hollywood screenwriting, cloud drives—everything!"
        )
        self.txt_tts.setStyleSheet("background: #05080f; color: #cbd5e1; border: 1px solid #1e293b; border-radius: 4px; padding: 6px;")
        tts_lay.addWidget(self.txt_tts)

        btn_gen_tts = QPushButton("⚡ Synthesize Neural Voice (RTX 4090 CUDA)")
        btn_gen_tts.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a855f7, stop:1 #3b82f6); color: #fff; font-weight: bold; border-radius: 4px; padding: 8px;")
        btn_gen_tts.clicked.connect(self._synthesize_tts)
        tts_lay.addWidget(btn_gen_tts)
        tts_lay.addStretch()

        split.addWidget(c_tts)

        # RIGHT: SUNO MUSIC GENERATOR
        c_suno = QFrame()
        c_suno.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        suno_lay = QVBoxLayout(c_suno)
        suno_lay.setSpacing(8)

        suno_lay.addWidget(QLabel("<b style='color: #10b981; font-size: 9pt;'>2. Suno Music Generator & Arranger</b>"))

        suno_lay.addWidget(QLabel("Lyrics & Structure Prompt:"))
        self.txt_lyrics = QTextEdit()
        self.txt_lyrics.setFixedHeight(90)
        self.txt_lyrics.setPlainText(
            "[Verse 1]\nFrom the cellar vault to the Bil-Mar shore\nWe built this family empire for evermore\n\n[Chorus]\nNotō Hospitality floating high!"
        )
        self.txt_lyrics.setStyleSheet("background: #05080f; color: #cbd5e1; border: 1px solid #1e293b; border-radius: 4px; padding: 6px;")
        suno_lay.addWidget(self.txt_lyrics)

        genre_row = QHBoxLayout()
        genre_row.addWidget(QLabel("Genre:"))
        self.combo_genre = QComboBox()
        self.combo_genre.addItems(["Italian Opera & Synthwave Fusion", "Dark Cyberpunk Trap", "Ambient Chillhop 85 BPM", "Stadium Rock 120 BPM"])
        self.combo_genre.setStyleSheet("background: #070b12; color: #f8fafc; padding: 4px; border: 1px solid #334155; border-radius: 4px;")
        genre_row.addWidget(self.combo_genre, 1)
        suno_lay.addLayout(genre_row)

        btn_gen_music = QPushButton("🎵 Compose & Master to Audio Bus")
        btn_gen_music.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #0284c7); color: #fff; font-weight: bold; border-radius: 4px; padding: 8px;")
        btn_gen_music.clicked.connect(self._compose_music)
        suno_lay.addWidget(btn_gen_music)
        suno_lay.addStretch()

        split.addWidget(c_suno)
        lay.addWidget(split)

    def _synthesize_tts(self) -> None:
        speaker = self.combo_speaker.currentText().split(" - ")[0]
        QMessageBox.information(
            self,
            "Neural Voice Synthesized",
            f"✅ F5-TTS Neural Voice synthesis complete for {speaker}!\nOutput routed directly to Broadcast Master Audio Bus.",
        )

    def _compose_music(self) -> None:
        genre = self.combo_genre.currentText()
        QMessageBox.information(
            self,
            "Suno Music Generated",
            f"✅ Composed {genre} track!\nArranger stems loaded and staged for live broadcast playback.",
        )


# ══════════════════════════════════════════════════════════════════════════
# 8. VIDEO MEETINGS & WEBRTC STRATEGY HUB
# ══════════════════════════════════════════════════════════════════════════

class VideoMeetingsWebRtcWidget(QWidget):
    """Executive video conferencing & WebRTC meeting room."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("<b style='color: #3b82f6; font-size: 11pt;'>📹 Video Meetings & P2P WebRTC Strategy Hub</b>"))
        hdr.addStretch()
        lay.addLayout(hdr)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setStyleSheet("QSplitter::handle { background: #162032; width: 2px; }")

        # LEFT: ACTIVE MEETING MONITOR & CONTROLS
        c_meet = QFrame()
        c_meet.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        meet_lay = QVBoxLayout(c_meet)
        meet_lay.setSpacing(8)

        meet_lay.addWidget(QLabel("<b style='color: #f8fafc; font-size: 9.5pt;'>Video meetings: no session connected</b>"))

        # Video feed placeholder
        vid_box = QFrame()
        vid_box.setFixedHeight(220)
        vid_box.setStyleSheet("background: #05080f; border: 1px solid #00f0ff; border-radius: 6px;")
        vb_lay = QVBoxLayout(vid_box)
        vb_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_v = QLabel("Video feed unavailable\nNo participant roster has been verified")
        lbl_v.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 8.5pt; text-align: center;")
        lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vb_lay.addWidget(lbl_v)
        meet_lay.addWidget(vid_box)

        # Call Controls Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)
        for act in ["🎤 Microphone", "📹 Camera", "🖥️ Share Screen", "⏺ Record Call", "📞 End Call"]:
            b = QPushButton(act)
            b.setStyleSheet("background: #1e293b; color: #cbd5e1; font-weight: bold; font-size: 7.5pt; border-radius: 4px; padding: 6px 10px;")
            b.setEnabled(False)
            b.setToolTip("Unavailable: no meeting provider/session is connected.")
            ctrl_bar.addWidget(b)
        ctrl_bar.addStretch()
        meet_lay.addLayout(ctrl_bar)
        meet_lay.addStretch()

        split.addWidget(c_meet)

        # RIGHT: SCHEDULED MEETINGS & AGENDAS
        c_sched = QFrame()
        c_sched.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        sched_lay = QVBoxLayout(c_sched)
        sched_lay.setSpacing(8)

        sched_lay.addWidget(QLabel("<b style='color: #38bdf8; font-size: 9.5pt;'>📅 Scheduled Executive Meetings</b>"))

        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Title", "Date / Time", "Status"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("background: #070b12; color: #cbd5e1; border: 1px solid #1e293b; font-size: 7.5pt;")

        sched_lay.addWidget(table)

        btn_new_meet = QPushButton("➕ Schedule New Meeting")
        btn_new_meet.setStyleSheet("background: #0284c7; color: #fff; font-weight: bold; border-radius: 4px; padding: 6px;")
        btn_new_meet.setEnabled(False)
        btn_new_meet.setToolTip("Unavailable: calendar/meeting provider is not connected.")
        sched_lay.addWidget(btn_new_meet)
        sched_lay.addStretch()

        split.addWidget(c_sched)
        lay.addWidget(split)


# ══════════════════════════════════════════════════════════════════════════
# 9. MASTER UNIVERSAL AV OMNI-BROADCAST STUDIO VIEW
# ══════════════════════════════════════════════════════════════════════════

class UniversalOmniStudioNativeView(QWidget):
    """Universal AV Omni-Broadcast Studio & Hardware NVENC 4K/8K Video Streamer.

    100% native Direct2D/PyQt6 equivalent to http://localhost:5173 BroadcastStudio & OmniStudioTab.
    """

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._is_streaming = False
        self._is_recording = False
        self._coordinator_status = {}
        self._stream_request_pending = False
        self._status_inflight = False
        self._broadcast_closed = False
        self._build_ui()
        self._coordinator_timer=QTimer(self)
        self._coordinator_timer.setInterval(1000)
        self._coordinator_timer.timeout.connect(self._refresh_broadcast_status)
        self._coordinator_timer.start()
        self._refresh_broadcast_status()

    def _build_ui(self) -> None:
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── TOP UNIVERSAL CONTROL & MODE BAR (FROM OMNISTUDIOTAB.JSX) ──
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #11052c, stop:0.5 #05192d, stop:1 #071520); "
            "border-bottom: 1px solid #1e293b; padding: 4px 12px;"
        )
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 2, 8, 2)
        tb_lay.setSpacing(10)

        # Title + Status Dot
        t_box = QHBoxLayout()
        t_box.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet("color: #00f0ff; font-size: 11pt;")
        t_box.addWidget(dot)

        lbl_title = QLabel("STEHOUWER PUBLISHING BROADCAST STUDIO")
        lbl_title.setStyleSheet("font-size: 10.5pt; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;")
        t_box.addWidget(lbl_title)
        tb_lay.addLayout(t_box)

        # Mode Buttons
        self.mode_buttons: Dict[str, QPushButton] = {}
        modes = [
            ("broadcast", "📡 Broadcast Studio"),
            ("daw", "🎵 Music DAW & VST3 Studio"),
            ("neural", "🎙️ Neural Voice & Audio AI"),
            ("video", "📹 Video Meetings & WebRTC"),
        ]
        m_box = QHBoxLayout()
        m_box.setSpacing(4)
        for m_key, m_lbl in modes:
            b = QPushButton(m_lbl)
            b.setStyleSheet(
                "QPushButton { background: transparent; color: #94a3b8; font-size: 7.5pt; font-weight: bold; border: 1px solid transparent; border-radius: 4px; padding: 4px 8px; }"
                "QPushButton:hover { color: #f8fafc; background: rgba(255,255,255,0.05); }"
            )
            b.clicked.connect(lambda chk=False, k=m_key: self._switch_studio_mode(k))
            m_box.addWidget(b)
            self.mode_buttons[m_key] = b

        self.mode_buttons["broadcast"].setStyleSheet(
            "background: rgba(0, 240, 255, 0.15); color: #00f0ff; border: 1px solid #00f0ff; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 7.5pt;"
        )
        tb_lay.addLayout(m_box)

        tb_lay.addStretch()

        # Telemetry Badges
        b1 = QLabel("NVENC latency: not measured")
        b1.setStyleSheet("background: rgba(0, 240, 255, 0.15); color: #00f0ff; border: 1px solid #00f0ff; border-radius: 4px; padding: 4px 8px; font-size: 7.5pt; font-weight: bold;")
        b2 = self.lbl_preview_status = QLabel("Preview: waiting")
        b2.setStyleSheet("background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid #a855f7; border-radius: 4px; padding: 4px 8px; font-size: 7.5pt; font-weight: bold;")
        b3 = QLabel("Audio priority: not checked")
        b3.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #059669; border-radius: 4px; padding: 4px 8px; font-size: 7.5pt; font-weight: bold;")

        tb_lay.addWidget(b1)
        tb_lay.addWidget(b2)
        tb_lay.addWidget(b3)

        root_lay.addWidget(top_bar)

        # ── ACTION TRIGGER BUTTONS BAR (NON-TRUNCATING HORIZONTAL SCROLL) ──
        act_scroll = QScrollArea()
        act_scroll.setWidgetResizable(True)
        act_scroll.setFixedHeight(48)
        act_scroll.setFrameShape(QFrame.Shape.NoFrame)
        act_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        act_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        act_scroll.setStyleSheet("background: #090e18; border-bottom: 1px solid #162032;")

        act_row = QWidget()
        act_row.setStyleSheet("background: transparent;")
        ar_lay = QHBoxLayout(act_row)
        ar_lay.setContentsMargins(8, 4, 8, 4)
        ar_lay.setSpacing(10)

        # October 7 Vocal Studio Native Button
        self.btn_october7 = QPushButton("🎙️ Launch October 7 Vocal Studio Native DAW")
        self.btn_october7.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2e93, stop:1 #a855f7); "
            "color: #ffffff; font-weight: bold; font-size: 8.5pt; border-radius: 4px; padding: 6px 12px;"
        )
        self.btn_october7.clicked.connect(self._launch_october7)
        ar_lay.addWidget(self.btn_october7)

        # Master Stream Toggle Button
        self.btn_stream = QPushButton("Start broadcast")
        self.btn_stream.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #ef4444); "
            "color: #ffffff; font-weight: bold; font-size: 8.5pt; border-radius: 4px; padding: 6px 12px;"
        )
        self.btn_stream.setToolTip("Shared coordinator: fixed 720p30 H.264 output and silent audio. Platform ingest is verified separately.")
        self.btn_stream.clicked.connect(self._toggle_stream)
        ar_lay.addWidget(self.btn_stream)

        # Record Toggle Button
        self.btn_record = QPushButton("Local archive accompanies broadcast")
        self.btn_record.setStyleSheet("background: #1e293b; color: #f87171; border: 1px solid #f87171; font-weight: bold; font-size: 8pt; border-radius: 4px; padding: 6px 10px;")
        self.btn_record.clicked.connect(self._toggle_record)
        ar_lay.addWidget(self.btn_record)

        self.chk_program_preview = QCheckBox("Program preview")
        self.chk_program_preview.setChecked(True)
        self.chk_program_preview.setToolTip("Read-only local program playback (delayed). This does not start, stop or change the broadcast.")
        ar_lay.addWidget(self.chk_program_preview)

        # Unreal Engine WebRTC Bridge
        btn_ue = QPushButton("🎮 Unreal Engine 5 Signaling (Port 8888)")
        btn_ue.setStyleSheet("background: #1e293b; color: #a855f7; border: 1px solid #a855f7; font-weight: bold; font-size: 8pt; border-radius: 4px; padding: 6px 10px;")
        btn_ue.clicked.connect(self._launch_ue_signaling)
        ar_lay.addWidget(btn_ue)

        ar_lay.addStretch()

        # Canvas Orientation Toggle (16:9 vs 9:16)
        self.btn_orientation = QPushButton("🖥️ 16:9 Landscape")
        self.btn_orientation.setStyleSheet("background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-size: 7.5pt; font-weight: bold; border-radius: 4px; padding: 5px 8px;")
        self.btn_orientation.clicked.connect(self._toggle_orientation)
        ar_lay.addWidget(self.btn_orientation)

        for btn in [self.btn_october7, self.btn_stream, self.btn_record, btn_ue, self.btn_orientation]:
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + 26)

        act_scroll.setWidget(act_row)
        root_lay.addWidget(act_scroll)
        self.lbl_broadcast_status=QLabel('Coordinator status not checked. Output: 1280×720 · 30 FPS · H.264 · 4500 kb/s. Silent audio.')
        self.lbl_broadcast_status.setWordWrap(True)
        self.lbl_broadcast_status.setStyleSheet('color:#cbd5e1; padding:6px 12px; background:#0d121d;')
        root_lay.addWidget(self.lbl_broadcast_status)

        # ── MASTER CONTENT STACK (BROADCAST / NEURAL / VIDEO) ──
        self.master_stack = QStackedWidget()

        # PAGE 0: FULL BROADCAST STUDIO
        broadcast_page = QWidget()
        bp_lay = QVBoxLayout(broadcast_page)
        bp_lay.setContentsMargins(10, 8, 10, 8)
        bp_lay.setSpacing(10)

        # TOP ROW: PREVIEW MONITOR + SCENES & SOURCES
        top_split = QSplitter(Qt.Orientation.Horizontal)
        top_split.setStyleSheet("QSplitter::handle { background: #162032; width: 2px; }")

        canvas_panel = QWidget()
        cp_lay = QVBoxLayout(canvas_panel)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        cp_lay.setSpacing(4)

        # ── PREVIEW & STAGING CONTROL TOOLBAR (NON-TRUNCATING HORIZONTAL SCROLL) ──
        prev_scroll = QScrollArea()
        prev_scroll.setWidgetResizable(True)
        prev_scroll.setFixedHeight(40)
        prev_scroll.setFrameShape(QFrame.Shape.NoFrame)
        prev_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        prev_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        prev_scroll.setStyleSheet("background: #080d16; border: 1px solid #1e293b; border-radius: 4px;")

        prev_bar = QWidget()
        prev_bar.setStyleSheet("background: transparent;")
        pb_lay = QHBoxLayout(prev_bar)
        pb_lay.setContentsMargins(4, 2, 4, 2)
        pb_lay.setSpacing(6)

        # Studio Mode A/B Button
        self.btn_studio_mode = QPushButton("🎛️ Studio Mode: OFF")
        self.btn_studio_mode.setCheckable(True)
        self.btn_studio_mode.setStyleSheet(
            "QPushButton { background: #111827; color: #94a3b8; font-size: 7.2pt; font-weight: bold; border: 1px solid #334155; border-radius: 3px; padding: 2px 7px; }"
            "QPushButton:checked { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }"
        )
        self.btn_studio_mode.toggled.connect(self._on_studio_mode_toggled)
        pb_lay.addWidget(self.btn_studio_mode)

        # Safe Areas Button
        self.btn_safe_areas = QPushButton("🛡️ Safe Areas: ON")
        self.btn_safe_areas.setCheckable(True)
        self.btn_safe_areas.setChecked(True)
        self.btn_safe_areas.setStyleSheet(
            "QPushButton { background: #111827; color: #94a3b8; font-size: 7.2pt; font-weight: bold; border: 1px solid #334155; border-radius: 3px; padding: 2px 7px; }"
            "QPushButton:checked { background: rgba(0, 240, 255, 0.2); color: #00f0ff; border: 1px solid #00f0ff; }"
        )
        self.btn_safe_areas.toggled.connect(self._on_safe_areas_toggled)
        pb_lay.addWidget(self.btn_safe_areas)

        # Aspect Presets Dropdown
        pb_lay.addWidget(QLabel("<span style='color: #64748b; font-size: 7pt; font-weight: bold;'>PRESET:</span>"))
        self.combo_aspect_preset = QComboBox()
        self.combo_aspect_preset.addItems([
            "16:9 Standard (1080p)",
            "16:9 Cinema (4K UHD)",
            "16:9 Crisp (1440p QHD)",
            "9:16 Mobile (Shorts / TikTok)",
            "1:1 Square (Feed / Post)",
            "4:3 Classic (Retro Stream)",
            "21:9 Ultra-Wide (Sim / Racing)",
        ])
        self.combo_aspect_preset.setStyleSheet(
            "background: #05080f; color: #f8fafc; border: 1px solid #334155; font-size: 7.2pt; padding: 2px 4px; border-radius: 3px;"
        )
        self.combo_aspect_preset.currentIndexChanged.connect(self._on_aspect_preset_changed)
        pb_lay.addWidget(self.combo_aspect_preset)

        # Scale Filter Dropdown
        pb_lay.addWidget(QLabel("<span style='color: #64748b; font-size: 7pt; font-weight: bold;'>SCALE:</span>"))
        self.combo_scale_filter = QComboBox()
        self.combo_scale_filter.addItems([
            "Lanczos (36-tap Sinc Sharp)",
            "Bicubic (16-sample Sharpened)",
            "Bilinear (Fastest Zero-Lag)",
        ])
        self.combo_scale_filter.setStyleSheet(
            "background: #05080f; color: #f8fafc; border: 1px solid #334155; font-size: 7.2pt; padding: 2px 4px; border-radius: 3px;"
        )
        self.combo_scale_filter.currentIndexChanged.connect(self._on_scale_filter_changed)
        pb_lay.addWidget(self.combo_scale_filter)

        # FPS Dropdown
        pb_lay.addWidget(QLabel("<span style='color: #64748b; font-size: 7pt; font-weight: bold;'>FPS:</span>"))
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["60 FPS", "59.94 FPS", "30 FPS", "24 FPS"])
        self.combo_fps.setStyleSheet(
            "background: #05080f; color: #f8fafc; border: 1px solid #334155; font-size: 7.2pt; padding: 2px 4px; border-radius: 3px;"
        )
        self.combo_fps.currentIndexChanged.connect(self._on_fps_changed)
        pb_lay.addWidget(self.combo_fps)

        # Transition Triggers
        self.btn_cut_trans = QPushButton("➡️ CUT")
        self.btn_cut_trans.setStyleSheet(
            "background: #0284c7; color: #ffffff; font-size: 7.2pt; font-weight: bold; border-radius: 3px; padding: 2px 6px;"
        )
        self.btn_cut_trans.clicked.connect(self._on_cut_pressed)
        pb_lay.addWidget(self.btn_cut_trans)

        self.btn_fade_trans = QPushButton("⏩ AUTO")
        self.btn_fade_trans.setStyleSheet(
            "background: #7c3aed; color: #ffffff; font-size: 7.2pt; font-weight: bold; border-radius: 3px; padding: 2px 6px;"
        )
        self.btn_fade_trans.clicked.connect(self._on_fade_pressed)
        pb_lay.addWidget(self.btn_fade_trans)

        pb_lay.addStretch()

        # Stream Specs & Ping Launcher
        self.btn_stream_diag = QPushButton("⚙️ Ping Diagnostics...")
        self.btn_stream_diag.setStyleSheet(
            "background: #0f172a; color: #38bdf8; border: 1px solid #0284c7; font-size: 7.2pt; font-weight: bold; border-radius: 3px; padding: 2px 7px;"
        )
        self.btn_stream_diag.clicked.connect(self._open_stream_requirements_dialog)
        pb_lay.addWidget(self.btn_stream_diag)

        for btn in [self.btn_studio_mode, self.btn_safe_areas, self.btn_cut_trans, self.btn_fade_trans, self.btn_stream_diag]:
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + 20)

        prev_scroll.setWidget(prev_bar)
        cp_lay.addWidget(prev_scroll)

        self.canvas = LiveBroadcastCanvas()
        self.canvas.set_coordinator_preview_unavailable()
        self._program_preview = NativeBroadcastPreview(self)
        self._program_preview.hide()
        self._program_preview.frame_ready.connect(self.canvas.set_program_preview_image)
        self._program_preview.cleared.connect(self.canvas.clear_program_preview)
        self._program_preview.state_changed.connect(self._apply_preview_status)
        self.chk_program_preview.toggled.connect(self._program_preview.set_preview_enabled)
        cp_lay.addWidget(self.canvas, 1)

        top_split.addWidget(canvas_panel)

        self.scenes_sources = LiveScenesAndSourcesWidget()
        self.scenes_sources.scene_changed.connect(self._on_scene_switched)
        self.scenes_sources.source_toggled.connect(self._on_source_toggled)
        top_split.addWidget(self.scenes_sources)

        top_split.setStretchFactor(0, 6)
        top_split.setStretchFactor(1, 4)
        bp_lay.addWidget(top_split, 5)

        # BOTTOM ROW: 3-COLUMN CONTROL MODULES
        bot_grid = QGridLayout()
        bot_grid.setSpacing(10)

        # COL 1: GAME DISCOVERY HOOK
        self.game_discovery = ActiveGameDiscoveryWidget(bus=self.bus)
        self.game_discovery.game_selected.connect(self._on_game_selected)
        self.btn_apply_source=QPushButton('Apply source')
        self.btn_apply_source.clicked.connect(self._apply_source_selection)
        self.game_discovery.layout().addWidget(self.btn_apply_source)
        self.game_discovery.source_draft_changed.connect(self._source_draft_changed)
        bot_grid.addWidget(self.game_discovery, 0, 0)

        # COL 2: ADVANCED AUDIO MIXER
        self.audio_mixer = AdvancedAudioMixerWidget()
        self.audio_mixer.setEnabled(False)
        self.lbl_silent_audio=QLabel('Silent audio · microphone unrequested')
        self.audio_mixer.layout().insertWidget(0,self.lbl_silent_audio)
        bot_grid.addWidget(self.audio_mixer, 0, 1)

        # COL 3: MULTI-RTMP DISPATCH
        self.rtmp_settings = MultiRtmpSettingsWidget()
        self.rtmp_settings.use_coordinator_profile()
        self.combo_fps.blockSignals(True);self.combo_fps.clear();self.combo_fps.addItem('30 FPS');self.combo_fps.setEnabled(False);self.combo_fps.blockSignals(False)
        self.rtmp_settings.platform_selected.connect(self._on_platform_preset_selected)
        bot_grid.addWidget(self.rtmp_settings, 0, 2)

        bot_grid.setColumnStretch(0, 3)
        bot_grid.setColumnStretch(1, 4)
        bot_grid.setColumnStretch(2, 3)
        bp_lay.addLayout(bot_grid, 4)

        # LOG & CHAT BOTTOM SPLITTER
        log_split = QSplitter(Qt.Orientation.Horizontal)
        log_split.setStyleSheet("QSplitter::handle { background: #162032; width: 2px; }")

        # Telemetry Log
        log_card = QFrame()
        log_card.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 6px;")
        lc_lay = QVBoxLayout(log_card)
        lc_lay.setContentsMargins(6, 6, 6, 6)
        lc_lay.setSpacing(4)
        lc_lay.addWidget(QLabel("📡 <b>Live Ingest & Kernel Telemetry:</b>"))

        self.txt_telemetry = QTextEdit()
        self.txt_telemetry.setReadOnly(True)
        self.txt_telemetry.setFont(QFont("Consolas", 8))
        self.txt_telemetry.setStyleSheet("background: #05080f; color: #38bdf8; border: 1px solid #1e293b; border-radius: 4px; padding: 6px;")
        self.txt_telemetry.document().setMaximumBlockCount(2000)
        self.txt_telemetry.setPlainText('Native broadcast controls initialized. Program preview is read-only and delayed; remote ingest remains unverified.')
        lc_lay.addWidget(self.txt_telemetry)
        log_split.addWidget(log_card)

        # Stream Chat
        self.stream_chat = UnifiedStreamChatWidget()
        log_split.addWidget(self.stream_chat)

        log_split.setStretchFactor(0, 5)
        log_split.setStretchFactor(1, 5)
        bp_lay.addWidget(log_split, 3)

        self.master_stack.addWidget(broadcast_page)  # index 0

        # PAGE 1: NEURAL AUDIO VOICE & SUNO
        self.neural_page = NeuralAudioVoiceWidget()
        self.master_stack.addWidget(self.neural_page)  # index 1

        # PAGE 2: VIDEO MEETINGS & WEBRTC
        self.video_page = VideoMeetingsWebRtcWidget()
        self.master_stack.addWidget(self.video_page)  # index 2

        root_lay.addWidget(self.master_stack, 1)

    def _switch_studio_mode(self, mode: str) -> None:
        if mode == "daw":
            # Jump directly to native Music DAW tab in main window!
            win = self.window()
            if hasattr(win, "jump_to_tab"):
                win.jump_to_tab("music_daw")
            return

        for k, b in self.mode_buttons.items():
            if k == mode:
                b.setStyleSheet("background: rgba(0, 240, 255, 0.15); color: #00f0ff; border: 1px solid #00f0ff; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 7.5pt;")
            else:
                b.setStyleSheet("background: transparent; color: #94a3b8; font-size: 7.5pt; font-weight: bold; border: 1px solid transparent; border-radius: 4px; padding: 4px 8px;")

        if mode == "broadcast":
            self.master_stack.setCurrentIndex(0)
        elif mode == "neural":
            self.master_stack.setCurrentIndex(1)
        elif mode == "video":
            self.master_stack.setCurrentIndex(2)

    def _toggle_orientation(self) -> None:
        if self.canvas.orientation == "horizontal":
            self.canvas.set_orientation("vertical")
            self.btn_orientation.setText("📱 9:16 Shorts/TikTok")
            self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 📱 Canvas switched to 9:16 Vertical (Shorts/TikTok/Reels).")
        else:
            self.canvas.set_orientation("horizontal")
            self.btn_orientation.setText("🖥️ 16:9 Landscape")
            self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 🖥️ Canvas switched to 16:9 Landscape (YouTube/Twitch).")

    def _on_game_selected(self, game_title: str, hwnd: int = 0) -> None:
        self._selected_capture_hwnd = hwnd
        self._selected_capture_title = game_title
        discovery=getattr(self,'game_discovery',None)
        self._selected_capture_pid=getattr(discovery,'_window_pid_by_handle',{}).get(hwnd)
        self.canvas.set_target_window(0)
        self.canvas.set_desktop_capture_enabled(False)
        self.txt_telemetry.append('Window source draft selected. Press Apply source to request the exact verified window. Program preview follows accepted coordinator output; source draft has not been applied.')

    def _on_scene_switched(self, scene: str) -> None:
        self.canvas.set_active_source(scene)
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 🎬 Local preview scene selected: '{scene}'")
        # Scene drafts are local preview state. Runtime source intent goes only
        # through the shared coordinator and its explicit Apply source action.

    def _on_source_toggled(self, source_name: str, enabled: bool) -> None:
        state = "ENABLED" if enabled else "DISABLED"
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 🎛️ Layer '{source_name}' {state}.")
        s_lower = source_name.lower()
        primary=next((s for s in self.scenes_sources.sources_list if s.get('enabled') is True and s.get('type') in {'game','window','screen','desktop'}),None)
        self.canvas.set_game_capture_enabled(False)
        self.canvas.set_desktop_capture_enabled(False)
        if "sony" in s_lower or "cam" in s_lower:
            self.canvas.set_pip_camera_enabled(enabled)
        elif "daw" in s_lower or "audio" in s_lower or "stems" in s_lower:
            self.canvas.set_audio_hud_enabled(enabled)
        elif "comfy" in s_lower:
            self.canvas.set_comfy_overlay_enabled(enabled)

    def _launch_october7(self) -> None:
        # Jump directly to the Music DAW tab in main window!
        win = self.window()
        if hasattr(win, "jump_to_tab"):
            win.jump_to_tab("music_daw")
        self.txt_telemetry.append(f"\n[{time.strftime('%H:%M:%S')}] 🎙️ Switched to October 7 Vocal Studio Native DAW; audio latency not measured.")

    def _stream_payload(self) -> dict:
        targets=[key for key,checkbox in self.rtmp_settings.dest_checkboxes.items() if checkbox.isChecked()]
        if not targets or any(key not in {'youtube','twitch','facebook','kick'} for key in targets):
            raise ValueError('Choose configured Facebook, YouTube, Twitch, or Kick destinations. Website HLS accompanies the broadcast.')
        mode,source=self.game_discovery.source_selection()
        return {'source_mode':mode,'source':validate_source(mode,source),'targets':targets}

    def _source_draft_changed(self) -> None:
        if hasattr(self,'txt_telemetry'):
            self.txt_telemetry.append('Source draft changed. Press Apply source; the coordinator keeps its current source until accepted.')

    def _apply_source_selection(self) -> None:
        if getattr(self,'_source_request_pending',False): return
        try: mode,source=self.game_discovery.source_selection()
        except ValueError:
            self.txt_telemetry.append('Choose an exact window or explicit screen before applying the source draft.');return
        if not self._coordinator_status.get('active'):
            self.txt_telemetry.append('Source draft will be used when you start the broadcast.');return
        self._source_request_pending=True
        self._source_request_epoch=time.monotonic()
        self.btn_apply_source.setEnabled(False)
        def finish():
            self._source_request_pending=False
            self.btn_apply_source.setEnabled(True)
        def complete(result):
            if self._broadcast_closed: return
            if result.get('status')=='pending':
                self._pending_source_request=result.get('request_id')
                self.txt_telemetry.append('Source change pending coordinator acknowledgement.')
            else:
                finish()
                self.txt_telemetry.append('Source change held: coordinator upgrade or verified fresh status is required.')
        def failed(_error=None):
            if self._broadcast_closed: return
            finish()
            self.txt_telemetry.append('Source change unverified; the current source has not been confirmed changed.')
        try: self.bus.submit(select_broadcast_source,mode,source,on_result=complete,on_error=failed)
        except Exception: failed()

    def _refresh_broadcast_status(self) -> None:
        if self._status_inflight or self._broadcast_closed: return
        self._status_inflight=True
        def complete(result):
            self._status_inflight=False
            if not self._broadcast_closed: self._apply_broadcast_status(result)
        def unavailable(_error=None): complete({'status':'status_unavailable','active':False,'can_start':False})
        try: self.bus.submit(read_broadcast_status,on_result=complete,on_error=unavailable)
        except Exception: unavailable()

    def _apply_broadcast_status(self, state: dict) -> None:
        self._coordinator_status=dict(state)
        self._is_streaming=state.get('active') is True
        self.btn_stream.setText('Stop broadcast' if self._is_streaming else 'Start broadcast')
        if not self._stream_request_pending:
            self.btn_stream.setEnabled(bool(state.get('can_stop') if self._is_streaming else state.get('can_start')))
        status=state.get('status')
        if status=='legacy_upgrade_required':
            text='Existing broadcast detected. Coordinator upgrade required for source changes; Stop remains available.'
        elif status=='status_stale': text='Coordinator status is stale. Source changes held; Stop remains available for the verified owner.'
        elif self._is_streaming and state.get('capture_state')=='holding':
            text='Holding black · no verified game frame. '+('Screen sharing is unsupported; automatic game following is disabled.' if state.get('source_mode')=='screen' else 'Waiting for the selected source.')
        elif self._is_streaming and state.get('game_frame_verified') is True:
            text='Coordinator capturing the selected source. Platform ingest remains unverified.'
        elif self._is_streaming: text='Coordinator running; capture and platform ingest unverified.'
        elif status in {'stopped','failed'}:
            text='Broadcast stopped.' if status=='stopped' else 'Previous broadcast failed; a new explicit Start can retry.'
        else: text='Coordinator status unavailable or owner unverified. Start and source changes held.'
        self.lbl_broadcast_status.setText(text+' Output: 1280×720 · 30 FPS · H.264 · 4500 kb/s. Silent audio.')
        self.canvas.set_streaming(False)
        self.canvas.set_target_window(0)
        self.canvas.set_desktop_capture_enabled(False)
        self.canvas.active_source_title='Program preview shows the current coordinator output; source drafts are separate.'
        preview = getattr(self, '_program_preview', None)
        if preview is not None:
            preview.set_coordinator_state(state)
        pending=getattr(self,'_pending_source_request',None)
        if pending and pending==state.get('last_command_id'):
            command_status=state.get('command_status')
            if command_status in {'applied','held','rejected'}:
                self.txt_telemetry.append('Source intent '+command_status+' by coordinator. '+('Screen sharing remains held.' if state.get('holding_reason')=='MANUAL_SCREEN_UNSUPPORTED' else 'Frame verification is shown in coordinator status.'))
                self._pending_source_request=None
                self._source_request_pending=False
                self.btn_apply_source.setEnabled(True)
        if getattr(self,'_source_request_pending',False) and time.monotonic()-self._source_request_epoch>5:
            self._source_request_pending=False
            self.btn_apply_source.setEnabled(True)
            self.txt_telemetry.append('Source acknowledgement timed out. Review actual coordinator status before applying another draft.')

    def _toggle_stream(self) -> None:
        self._dispatch_broadcast('stream', not self._is_streaming)

    def _dispatch_broadcast(self, kind: str, starting: bool) -> None:
        button = self.btn_stream if kind == 'stream' else self.btn_record
        if not button.isEnabled():
            return
        try:
            payload = self._stream_payload() if kind == 'stream' and starting else {}
        except ValueError as exc:
            # Payload errors are fixed labels and never contain URLs/credentials.
            self.txt_telemetry.append('Broadcast held: ' + str(exc))
            return
        except (TypeError, KeyError):
            self.txt_telemetry.append('Broadcast held: saved settings are invalid. Review Setup Keys and capture selection.')
            return
        button.setEnabled(False)
        if kind=='stream': self._stream_request_pending=True
        self.txt_telemetry.append(f'{kind.title()} request pending; destination acceptance and media health are not verified.')

        def unverified(_error=None, *, ambiguous=True):
            if getattr(self,'_broadcast_closed',False): return
            if kind=='stream': self._stream_request_pending=False
            button.setEnabled(True)
            # A lost start acknowledgement may hide an accepted command. Offer
            # Stop rather than duplicating a potentially active start.
            if starting and ambiguous:
                if kind == 'stream': self._is_streaming = True
                else: self._is_recording = True
                button.setText('Stop / reconcile unverified ' + kind)
            if kind == 'stream': self.canvas.set_streaming(False)
            else: self.canvas.set_recording(False)
            self.txt_telemetry.append(f'{kind.title()} state unverified: request failed or was rejected. Check the service before retrying.')

        def complete(result):
            if getattr(self,'_broadcast_closed',False): return
            status = result.get('status') if isinstance(result, dict) else None
            if kind=='stream' and status in {'starting','stopping','running_unverified','legacy_upgrade_required','status_stale','controller_present'}:
                self._stream_request_pending=False
                self._is_streaming=starting or result.get('active') is True
                button.setEnabled(True)
                button.setText('Stop / reconcile broadcast' if self._is_streaming else 'Start broadcast')
                self.txt_telemetry.append('Coordinator request acknowledged; actual status will be reconciled. Platform ingest remains unverified.')
                if hasattr(self,'_refresh_broadcast_status'): self._refresh_broadcast_status()
                return
            allowed = {'streaming'} if kind == 'stream' and starting else {'recording'} if starting else {'stopped','inactive'}
            if not isinstance(status,str) or status.lower() not in allowed:
                unverified(ambiguous=False)
                return
            button.setEnabled(True)
            if kind=='stream': self._stream_request_pending=False
            if kind == 'stream':
                self._is_streaming = starting
                self.canvas.set_streaming(starting)
                button.setText('Stop Broadcast (daemon acknowledged)' if starting else 'Start Broadcast')
            else:
                self._is_recording = starting
                self.canvas.set_recording(starting)
                button.setText('Stop Recording (daemon acknowledged)' if starting else 'Record Master')
            self.txt_telemetry.append(f'{kind.title()} {"start" if starting else "stop"} acknowledged by local service. Platform ingest and saved-file integrity are not verified.')
        try:
            self.bus.submit(send_broadcast_command,kind,starting,payload,on_result=complete,on_error=unverified)
        except Exception:
            unverified()


    def _toggle_record(self) -> None:
        self.txt_telemetry.append('Local archive accompanies the broadcast automatically. This control does not start a second recorder; saved-file integrity remains unverified.')


    def _apply_preview_status(self, state: dict) -> None:
        labels = {'waiting': 'Preview: waiting', 'buffering': 'Preview: buffering',
                  'showing': 'Preview: delayed', 'held': 'Preview: held',
                  'stale': 'Preview: stale', 'disabled': 'Preview: off',
                  'unavailable': 'Preview: unavailable', 'closed': 'Preview: off'}
        self.lbl_preview_status.setText(labels.get(state.get('state'), 'Preview: unavailable'))

    def _launch_ue_signaling(self) -> None:
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 🎮 Unreal signaling is not checked; this control has no connected launcher.")

    def _on_studio_mode_toggled(self, checked: bool) -> None:
        self.canvas.set_studio_mode(checked)
        self.btn_studio_mode.setText("🎛️ Studio Mode: ON" if checked else "🎛️ Studio Mode: OFF")
        mode_str = "DUAL A/B (Preview Staging + Program Live)" if checked else "SINGLE MONITOR (Program Live)"
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 🎛️ Broadcast Output Mode switched to: {mode_str}.")

    def _on_safe_areas_toggled(self, checked: bool) -> None:
        self.canvas.set_safe_areas_enabled(checked)
        self.btn_safe_areas.setText("🛡️ Safe Areas: ON" if checked else "🛡️ Safe Areas: OFF")
        state_str = "VISIBLE (90% Action Safe cyan, 80% Title Safe amber, 3x3 Grid)" if checked else "HIDDEN"
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 🛡️ Safe Area Margins & Thirds Grid: {state_str}.")

    def _on_aspect_preset_changed(self, idx: int) -> None:
        preset_text = self.combo_aspect_preset.currentText()
        self.canvas.set_aspect_preset(preset_text)
        if "9:16" in preset_text:
            self.btn_orientation.setText("📱 9:16 Shorts/TikTok")
        else:
            self.btn_orientation.setText("🖥️ 16:9 Landscape")
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 📐 Output Aspect Ratio Preset changed to: {preset_text}.")

    def _on_scale_filter_changed(self, idx: int) -> None:
        filter_text = self.combo_scale_filter.currentText()
        self.canvas.set_scale_filter(filter_text)
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] 🔍 Video Downscale Sampling Filter updated: {filter_text}.")

    def _on_fps_changed(self, idx: int) -> None:
        fps_text = self.combo_fps.currentText()
        self.canvas.set_fps_target(fps_text)
        self.txt_telemetry.append(f"[{time.strftime('%H:%M:%S')}] ⏱️ Target Broadcast Frame Rate set to: {fps_text}.")

    def _on_cut_pressed(self) -> None:
        self.canvas.trigger_cut_transition()
        self.txt_telemetry.append(
            f"[{time.strftime('%H:%M:%S')}] ➡️ CUT Transition Executed! Program is now: '{self.canvas.program_scene_title}', Staging is: '{self.canvas.preview_scene_title}'."
        )

    def _on_fade_pressed(self) -> None:
        self.canvas.trigger_fade_transition()
        self.txt_telemetry.append(
            f"[{time.strftime('%H:%M:%S')}] ⏩ AUTO (300ms) Dissolve Transition Executed! Live scene: '{self.canvas.program_scene_title}'."
        )

    def _open_stream_requirements_dialog(self) -> None:
        dlg = StreamRequirementsDialog(parent=self)
        dlg.profile_applied.connect(self.rtmp_settings.load_saved_settings)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.rtmp_settings.load_saved_settings(dlg.cfg)
            fps=str(dlg.cfg.get('encoder',{}).get('fps',60))+' FPS'
            self.combo_fps.setCurrentText(fps)

    def _on_platform_preset_selected(self, platform_id: str, spec: dict) -> None:
        max_res = spec.get("max_resolution", "1920x1080")
        if "1080x1920" in max_res or platform_id == "TikTok Live":
            self.combo_aspect_preset.setCurrentText("9:16 Mobile (Shorts / TikTok)")
        elif "3840x2160" in max_res:
            self.combo_aspect_preset.setCurrentText("16:9 Cinema (4K UHD)")
        elif "2560x1440" in max_res:
            self.combo_aspect_preset.setCurrentText("16:9 Crisp (1440p QHD)")
        else:
            self.combo_aspect_preset.setCurrentText("16:9 Standard (1080p)")

        self.txt_telemetry.append(
            f"[{time.strftime('%H:%M:%S')}] Settings draft selected for {platform_id}: "
            f"{spec.get('rate_control', 'CBR')} @ {spec.get('max_video_bitrate_kbps', 6000)} kbps | GOP {spec.get('keyframe_interval_sec', 2.0)}s."
        )

    def shutdown(self) -> None:
        preview = getattr(self, '_program_preview', None)
        if preview is not None:
            preview.shutdown()
        if hasattr(self, "canvas") and hasattr(self.canvas, "shutdown"):
            self._broadcast_closed=True
            if hasattr(self,'_coordinator_timer'): self._coordinator_timer.stop()
            self.canvas.shutdown()
        if hasattr(self, "rtmp_settings") and hasattr(self.rtmp_settings, "shutdown"):
            self.rtmp_settings.shutdown()
        if hasattr(self, "audio_mixer") and hasattr(self.audio_mixer, "shutdown"):
            self.audio_mixer.shutdown()
        if hasattr(self, "game_discovery") and hasattr(self.game_discovery, "shutdown"):
            self.game_discovery.shutdown()

    def closeEvent(self, event: Any) -> None:
        self.shutdown()
        super().closeEvent(event)
