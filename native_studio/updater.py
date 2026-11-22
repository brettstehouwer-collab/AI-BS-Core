"""Update information for packaged clients and explicit source-development sync."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE, apply_dark_titlebar

AI_BS_ROOT = Path(r"C:\AI-BS")
PACKAGED_UPDATE_MESSAGE = "A new Windows installer is required. No automatic update service is configured."
PACKAGED_UPDATE_DETAILS = "Install a newer Windows package from a trusted source. No update availability check has been performed."


def get_local_version() -> str:
    """Read packaged build authority, or the source version in development mode."""
    is_frozen = getattr(sys, "frozen", False)
    try:
        if is_frozen:
            bundle_root = getattr(sys, "_MEIPASS", None)
            if not bundle_root:
                return "unknown"
            v_file = Path(bundle_root) / "version.txt"
        else:
            v_file = AI_BS_ROOT / "version.txt"
        if v_file.exists():
            version = v_file.read_text(encoding="utf-8").strip()
            return (version or "unknown") if is_frozen else version
    except Exception:
        pass
    return "unknown" if is_frozen else "v5.327.0"


def check_for_updates_worker() -> Dict[str, Any]:
    """Background worker to probe remote Git repository for updates without blocking GUI."""
    version = get_local_version()
    is_frozen = getattr(sys, "frozen", False)
    payload: Dict[str, Any] = {
        "version": version,
        "is_frozen": is_frozen,
        "branch": "main",
        "commit": "",
        "tracking": "",
        "commits_behind": 0,
        "incoming_commits": [],
        "has_local_changes": False,
        "has_updates": False,
        "status_message": "Checking repository...",
        "error": None,
    }
    if is_frozen:
        payload.update({
            "branch": "",
            "installer_required": True,
            "update_check_performed": False,
            "update_mode": "installer",
            "status_message": PACKAGED_UPDATE_MESSAGE,
        })
        return payload

    try:
        def _git(cmd: List[str], timeout: int = 8) -> str:
            res = subprocess.run(
                ["git"] + cmd,
                cwd=str(AI_BS_ROOT),
                capture_output=True,
                text=True,
                errors="ignore",
                timeout=timeout,
            )
            return res.stdout.strip()

        payload["commit"] = _git(["rev-parse", "--short", "HEAD"])
        payload["branch"] = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "main"
        payload["tracking"] = _git(["rev-parse", "--abbrev-ref", "@{u}"])

        # Fetch remote silently
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=str(AI_BS_ROOT),
            capture_output=True,
            timeout=10,
        )

        tracking = payload["tracking"] or "origin/main"
        behind_str = _git(["rev-list", f"HEAD..{tracking}", "--count"])
        try:
            behind_count = int(behind_str)
        except ValueError:
            behind_count = 0

        payload["commits_behind"] = behind_count
        if behind_count > 0:
            payload["has_updates"] = True
            log_str = _git(["log", f"HEAD..{tracking}", "--oneline", "-n", "10"])
            payload["incoming_commits"] = [line.strip() for line in log_str.splitlines() if line.strip()]
            payload["status_message"] = f"🚀 {behind_count} new update(s) available from {tracking}!"
        else:
            payload["has_updates"] = False
            payload["status_message"] = f"✅ Studio is 100% up to date with {tracking}."

        # Check local uncommitted edits
        status_str = _git(["status", "--porcelain"])
        payload["has_local_changes"] = bool(status_str)

    except Exception as exc:
        payload["error"] = str(exc)
        payload["status_message"] = f"⚠️ Could not check updates: {exc}"

    return payload


def apply_update_worker() -> Dict[str, Any]:
    """Background worker to pull latest git commits into the live codebase."""
    res = {"success": False, "message": "", "output": ""}
    if getattr(sys, "frozen", False):
        res.update({"message": PACKAGED_UPDATE_MESSAGE, "installer_required": True, "is_frozen": True})
        return res
    try:
        p = subprocess.run(
            ["git", "pull", "--autostash", "origin", "main"],
            cwd=str(AI_BS_ROOT),
            capture_output=True,
            text=True,
            errors="ignore",
            timeout=30,
        )
        res["output"] = p.stdout.strip() + ("\n" + p.stderr.strip() if p.stderr.strip() else "")
        if p.returncode == 0:
            res["success"] = True
            new_v = get_local_version()
            res["message"] = f"Successfully updated to {new_v}! Restart Studio to apply changes immediately."
        else:
            res["message"] = f"Git pull returned non-zero code {p.returncode}: {p.stderr.strip()}"
    except Exception as exc:
        res["message"] = f"Error during git pull: {exc}"
    return res


def restart_studio() -> None:
    """Seamlessly reboots the AI-BS Sovereign Studio process in <1 second (zero rebuild)."""
    try:
        if getattr(sys, "frozen", False):
            cmd = [sys.executable]
            working_directory = Path(sys.executable).parent
        else:
            app_script = str(AI_BS_ROOT / "native_studio" / "app.py")
            cmd = [sys.executable, app_script]
            working_directory = AI_BS_ROOT

        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        subprocess.Popen(cmd, cwd=str(working_directory), creationflags=flags)
        QApplication.quit()
    except Exception as exc:
        print(f"[RESTART ERROR] {exc}")


class UpdateDialog(QDialog):
    """High-fidelity Cyber UI modal to check for updates and hot-reload code in-place."""

    def __init__(self, bus: Optional[EngineBus] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus or EngineBus()
        self.setWindowTitle("AI-BS Update Information" if getattr(sys, "frozen", False) else "AI-BS Sovereign Update & Live Sync Hub")
        self.setFixedSize(640, 520)
        self.setStyleSheet(
            f"background-color: {PALETTE['panel']}; color: {PALETTE['text']}; "
            f"border: 1px solid #00f0ff; border-radius: 10px;"
        )
        apply_dark_titlebar(self)

        self._build_ui()
        self.start_check()

    def _build_ui(self) -> None:
        is_frozen = getattr(sys, "frozen", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # ── 1. HEADER ──
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        icon_lbl = QLabel("🔄")
        icon_lbl.setStyleSheet("font-size: 18pt;")
        hdr.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("AI-BS WINDOWS UPDATE INFORMATION" if is_frozen else "AI-BS SOVEREIGN LIVE UPDATE ENGINE")
        lbl_title.setStyleSheet("font-size: 11pt; font-weight: 800; color: #00f0ff; letter-spacing: 0.5px;")
        lbl_sub = QLabel("Updates require a new Windows installer." if is_frozen else "Direct In-Place Sync & Hot-Reload • Zero PyInstaller / Vite Rebuild Required")
        lbl_sub.setStyleSheet("font-size: 7.5pt; color: #a78bfa;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        hdr.addLayout(title_box)
        hdr.addStretch()

        self.badge_version = QLabel(f"Version: {get_local_version()}")
        self.badge_version.setStyleSheet(
            "background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #a855f7; "
            "border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 8pt;"
        )
        hdr.addWidget(self.badge_version)
        layout.addLayout(hdr)

        # ── 2. STATUS CARD ──
        self.status_card = QFrame()
        self.status_card.setStyleSheet(
            "background: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;"
        )
        sc_lay = QVBoxLayout(self.status_card)
        sc_lay.setContentsMargins(10, 8, 10, 8)
        sc_lay.setSpacing(6)

        self.lbl_status = QLabel("Reading packaged version..." if is_frozen else "Checking repository and remote refs...")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 9pt; font-weight: bold;")
        sc_lay.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate spinner
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: #05080f; border: 1px solid #1e293b; border-radius: 3px; } "
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f0ff, stop:1 #a855f7); }"
        )
        sc_lay.addWidget(self.progress_bar)

        self.lbl_details = QLabel(PACKAGED_UPDATE_DETAILS if is_frozen else "Probing origin/main for incoming commits...")
        self.lbl_details.setStyleSheet("color: #94a3b8; font-size: 7.5pt;")
        sc_lay.addWidget(self.lbl_details)
        layout.addWidget(self.status_card)

        # ── 3. CHANGELOG / INCOMING COMMITS DISPLAY ──
        layout.addWidget(QLabel("<b>Windows Installer Updates:</b>" if is_frozen else "📋 <b>Incoming Changes & Commit Log:</b>"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 8))
        self.txt_log.setStyleSheet(
            "background: #040810; color: #cbd5e1; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;"
        )
        self.txt_log.setPlaceholderText(PACKAGED_UPDATE_DETAILS if is_frozen else "No incoming commits pending.")
        layout.addWidget(self.txt_log, 1)

        # ── 4. ACTION BUTTONS ──
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_check = QPushButton("Refresh Version Information" if is_frozen else "🔍 Re-Check Updates")
        self.btn_check.setStyleSheet(
            "QPushButton { background: #0f172a; color: #38bdf8; border: 1px solid #0284c7; border-radius: 6px; padding: 7px 14px; font-weight: bold; font-size: 8pt; }"
            "QPushButton:hover { background: #1e293b; }"
        )
        self.btn_check.clicked.connect(self.start_check)
        btn_bar.addWidget(self.btn_check)

        self.btn_update = QPushButton("New Windows Installer Required" if is_frozen else "⚡ Update & Live Reload (No Rebuild)")
        self.btn_update.setEnabled(False)
        self.btn_update.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981); color: #ffffff; border-radius: 6px; padding: 7px 14px; font-weight: bold; font-size: 8.5pt; }"
            "QPushButton:hover { background: #10b981; }"
            "QPushButton:disabled { background: #1e293b; color: #64748b; border: 1px solid #334155; }"
        )
        self.btn_update.clicked.connect(self.start_update)
        btn_bar.addWidget(self.btn_update)

        self.btn_restart = QPushButton("Restart Studio" if is_frozen else "🔄 Hot-Restart Studio (1s)")
        self.btn_restart.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #a855f7); color: #ffffff; border-radius: 6px; padding: 7px 14px; font-weight: bold; font-size: 8.5pt; }"
            "QPushButton:hover { background: #9333ea; }"
        )
        self.btn_restart.clicked.connect(restart_studio)
        btn_bar.addWidget(self.btn_restart)

        btn_bar.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.setStyleSheet(
            "QPushButton { background: #111827; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 7px 14px; font-weight: bold; font-size: 8pt; }"
            "QPushButton:hover { background: #1f2937; color: #ffffff; }"
        )
        self.btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(self.btn_close)

        layout.addLayout(btn_bar)

    def start_check(self) -> None:
        if getattr(sys, "frozen", False):
            self._on_check_result(check_for_updates_worker())
            return
        self.progress_bar.show()
        self.btn_check.setEnabled(False)
        self.btn_update.setEnabled(False)
        self.lbl_status.setText("Checking remote repository...")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 9pt; font-weight: bold;")
        self.lbl_details.setText("Running silent git fetch against origin...")
        self.bus.submit(check_for_updates_worker, on_result=self._on_check_result, on_error=self._on_check_error)

    def _on_check_result(self, data: Dict[str, Any]) -> None:
        if getattr(sys, "frozen", False) or data.get("installer_required"):
            self.progress_bar.hide()
            self.btn_check.setEnabled(True)
            self.btn_update.setEnabled(False)
            self.badge_version.setText(f"Version: {get_local_version()} (packaged)")
            self.lbl_status.setText(PACKAGED_UPDATE_MESSAGE)
            self.lbl_status.setStyleSheet("color: #fbbf24; font-size: 9pt; font-weight: bold;")
            self.lbl_details.setText(PACKAGED_UPDATE_DETAILS)
            self.txt_log.setPlainText(PACKAGED_UPDATE_DETAILS)
            return
        self.progress_bar.hide()
        self.btn_check.setEnabled(True)

        v = data.get("version", get_local_version())
        c = data.get("commit", "unknown")
        b = data.get("branch", "main")
        self.badge_version.setText(f"Version: {v} ({c} @ {b})")

        has_updates = data.get("has_updates", False)
        behind = data.get("commits_behind", 0)
        commits = data.get("incoming_commits", [])

        if has_updates:
            self.lbl_status.setText(f"🚀 Update Available ({behind} new commit(s))")
            self.lbl_status.setStyleSheet("color: #fbbf24; font-size: 9pt; font-weight: bold;")
            self.lbl_details.setText(
                "Click 'Update & Live Reload' below to pull changes directly without rebuilding any binary."
            )
            self.btn_update.setEnabled(True)
            log_text = "\n".join(f"• {c}" for c in commits)
            self.txt_log.setPlainText(log_text)
        else:
            self.lbl_status.setText(data.get("status_message", "Studio is up to date."))
            self.lbl_status.setStyleSheet("color: #34d399; font-size: 9pt; font-weight: bold;")
            details = f"Branch '{b}' is fully synced. Running live native code."
            if data.get("has_local_changes"):
                details += " (Active local source edits detected — live hot-reloading active)."
            self.lbl_details.setText(details)
            self.btn_update.setEnabled(False)
            self.txt_log.setPlainText("✅ All files are up to date.\nNo rebuild is required to run latest changes.")

    def _on_check_error(self, err_msg: str) -> None:
        self.progress_bar.hide()
        self.btn_check.setEnabled(True)
        self.lbl_status.setText("⚠️ Failed to check for updates")
        self.lbl_status.setStyleSheet("color: #f87171; font-size: 9pt; font-weight: bold;")
        self.lbl_details.setText(str(err_msg))

    def start_update(self) -> None:
        if getattr(sys, "frozen", False):
            self._on_update_result(apply_update_worker())
            return
        self.progress_bar.show()
        self.btn_update.setEnabled(False)
        self.btn_check.setEnabled(False)
        self.lbl_status.setText("Pulling latest code...")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 9pt; font-weight: bold;")
        self.lbl_details.setText("Applying git pull with auto-stash to preserve any local configurations...")
        self.bus.submit(apply_update_worker, on_result=self._on_update_result, on_error=self._on_check_error)

    def _on_update_result(self, res: Dict[str, Any]) -> None:
        if getattr(sys, "frozen", False) or res.get("installer_required"):
            self.progress_bar.hide()
            self.btn_check.setEnabled(True)
            self.btn_update.setEnabled(False)
            self.badge_version.setText(f"Version: {get_local_version()} (packaged)")
            self.lbl_status.setText(PACKAGED_UPDATE_MESSAGE)
            self.lbl_status.setStyleSheet("color: #fbbf24; font-size: 9pt; font-weight: bold;")
            self.lbl_details.setText(PACKAGED_UPDATE_DETAILS)
            self.txt_log.setPlainText(PACKAGED_UPDATE_DETAILS)
            return
        self.progress_bar.hide()
        self.btn_check.setEnabled(True)
        if res.get("success"):
            self.lbl_status.setText("🎉 Update Successfully Applied!")
            self.lbl_status.setStyleSheet("color: #34d399; font-size: 9.5pt; font-weight: 800;")
            self.lbl_details.setText(
                "Files updated in-place without rebuilding! Click 'Hot-Restart Studio' to reload immediately."
            )
            self.txt_log.setPlainText(res.get("output", "") + "\n\n" + res.get("message", ""))
            self.badge_version.setText(f"Version: {get_local_version()}")
        else:
            self.lbl_status.setText("⚠️ Update Failed")
            self.lbl_status.setStyleSheet("color: #f87171; font-size: 9pt; font-weight: bold;")
            self.lbl_details.setText(res.get("message", "Error during update"))
            self.txt_log.setPlainText(res.get("output", ""))
