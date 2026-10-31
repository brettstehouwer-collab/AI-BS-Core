"""System Health & Audit Logs View for AI-BS Native Studio (Pure PyQt6 Direct2D).

1:1 visual & functional parity with SystemHealthTab.jsx:
- Real-Time Hardware & VRAM Allocation Telemetry (RTX 4090, VRAM bar, Temp, Load, Port Status)
- Live Stream vs. Persistent Archive Dual-Mode Workspace
- Live auto-scrolling terminal console connected to SQLite audit logs
- Persistent Archive table with level filters, full-text keyword search, and pagination
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from html import escape
import math
import time
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus, GpuProbe
from native_studio.theme import PALETTE

_ROOT = Path(os.environ.get("AI_BS_ROOT", r"C:\AI-BS"))
_LOG_DB_PATH = _ROOT / "backend" / "system_logs.db"
QUERY_BUDGET_SECONDS = 0.25
LIVE_PREVIEW_BLOCKS = 2000


def _ensure_log_db() -> sqlite3.Connection:
    """Open an existing producer-owned archive; observing must not create facts."""
    conn = sqlite3.connect(_LOG_DB_PATH.absolute().as_uri() + "?mode=ro", uri=True, timeout=0.25)
    try:
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA trusted_schema = OFF")
        deadline = time.monotonic() + QUERY_BUDGET_SECONDS
        # SQLite checks its VM budget during execution; lock waits use timeout.
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        return conn
    except Exception:
        conn.close()
        raise


def _measured_number(value, *, minimum=0.0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < minimum or maximum is not None and value > maximum:
        return None
    return float(value)


class SystemHealthNativeView(QWidget):
    """System Health & Audit Logs View matching SystemHealthTab.jsx."""

    def __init__(self, bus: EngineBus, gpu_probe: Optional[GpuProbe] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus
        self.gpu_probe = gpu_probe or GpuProbe()
        self._history_page = 0
        self._page_limit = 50
        self._last_log_id = 0

        self._build_ui()

        # Connect live log poller timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_live_updates)
        self.timer.start(2000)

        # Initial data load
        self._poll_live_updates()
        self._load_history()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Top Header with Tab Switcher
        header_bar = QFrame()
        header_bar.setStyleSheet(
            "background: #12161f; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 12px;"
        )
        h_lay = QHBoxLayout(header_bar)
        h_lay.setContentsMargins(8, 6, 8, 6)

        title_lbl = QLabel("🏥  System Health & <span style='color: #38bdf8;'>Audit Logs</span>")
        title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #f8fafc;")
        h_lay.addWidget(title_lbl)

        h_lay.addStretch()

        # Mode buttons (Live Stream vs Persistent Archive)
        btn_box = QFrame()
        btn_box.setStyleSheet(
            "background: #090d14; border: 1px solid #1e293b; border-radius: 6px; padding: 2px;"
        )
        b_lay = QHBoxLayout(btn_box)
        b_lay.setContentsMargins(2, 2, 2, 2)
        b_lay.setSpacing(4)

        self.btn_live = QPushButton(">_ Live Stream")
        self.btn_live.setCheckable(True)
        self.btn_live.setChecked(True)
        self.btn_live.setStyleSheet(
            "QPushButton { background: #1e293b; color: #38bdf8; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 8.5pt; }"
            "QPushButton:hover { background: #334155; }"
        )
        self.btn_live.clicked.connect(lambda: self._set_mode("live"))
        b_lay.addWidget(self.btn_live)

        self.btn_archive = QPushButton("💾 Persistent Archive")
        self.btn_archive.setCheckable(True)
        self.btn_archive.setStyleSheet(
            "QPushButton { background: transparent; color: #94a3b8; border: none; border-radius: 4px; padding: 6px 14px; font-size: 8.5pt; }"
            "QPushButton:hover { background: #1e293b; color: #f8fafc; }"
        )
        self.btn_archive.clicked.connect(lambda: self._set_mode("archive"))
        b_lay.addWidget(self.btn_archive)

        h_lay.addWidget(btn_box)
        main_layout.addWidget(header_bar)

        # GPU & Hardware Telemetry HUD Bar
        self.telemetry_card = QFrame()
        self.telemetry_card.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(15,23,42,0.95), stop:1 rgba(30,41,59,0.85));"
            "border: 1px solid #334155; border-radius: 10px; padding: 10px;"
        )
        t_lay = QVBoxLayout(self.telemetry_card)
        t_lay.setContentsMargins(12, 10, 12, 10)
        t_lay.setSpacing(8)

        # Top chip row
        top_chip_row = QHBoxLayout()
        self.lbl_gpu_device = QLabel("GPU telemetry unavailable")
        self.lbl_gpu_device.setStyleSheet("font-size: 10pt; font-weight: bold; color: #f8fafc;")
        top_chip_row.addWidget(self.lbl_gpu_device)

        self.lbl_gpu_temp = QLabel("Temperature unavailable")
        self.lbl_gpu_temp.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #059669; border-radius: 4px; padding: 2px 8px; font-size: 8pt; font-weight: bold;")
        top_chip_row.addWidget(self.lbl_gpu_temp)

        self.lbl_gpu_load = QLabel("GPU load unavailable")
        self.lbl_gpu_load.setStyleSheet("background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 2px 8px; font-size: 8pt; font-weight: bold;")
        top_chip_row.addWidget(self.lbl_gpu_load)

        top_chip_row.addStretch()

        self.lbl_ollama_status = QLabel("Ollama (11434): not checked")
        self.lbl_ollama_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 8pt;")
        top_chip_row.addWidget(self.lbl_ollama_status)

        self.lbl_comfy_status = QLabel("ComfyUI (8189): not checked")
        self.lbl_comfy_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 8pt;")
        top_chip_row.addWidget(self.lbl_comfy_status)

        t_lay.addLayout(top_chip_row)

        # VRAM Allocation Bar & Legend
        vram_labels_row = QHBoxLayout()
        self.lbl_vram_alloc = QLabel("Allocated VRAM unavailable")
        self.lbl_vram_alloc.setStyleSheet("color: #94a3b8; font-size: 8pt;")
        vram_labels_row.addWidget(self.lbl_vram_alloc)

        vram_labels_row.addStretch()

        self.lbl_vram_free = QLabel("VRAM headroom unavailable")
        self.lbl_vram_free.setStyleSheet("font-size: 8pt;")
        vram_labels_row.addWidget(self.lbl_vram_free)
        t_lay.addLayout(vram_labels_row)

        self.vram_meter = QProgressBar()
        self.vram_meter.setRange(0, 100)
        self.vram_meter.setValue(0)
        self.vram_meter.setEnabled(False)
        self.vram_meter.setTextVisible(False)
        self.vram_meter.setFixedHeight(8)
        self.vram_meter.setStyleSheet(
            "QProgressBar { background: #0f172a; border-radius: 4px; border: none; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:0.7 #00f0ff, stop:1 #10b981); border-radius: 4px; }"
        )
        t_lay.addWidget(self.vram_meter)

        main_layout.addWidget(self.telemetry_card)

        # Stacked area: Live Stream vs Archive
        self.deck = QStackedWidget()

        # Page 0: Live Stream Console
        page_live = QWidget()
        p0_lay = QVBoxLayout(page_live)
        p0_lay.setContentsMargins(0, 0, 0, 0)
        p0_lay.setSpacing(6)

        live_bar = QFrame()
        live_bar.setStyleSheet("background: #0f141f; border: 1px solid #1e293b; border-radius: 6px; padding: 6px 12px;")
        lb_lay = QHBoxLayout(live_bar)
        lb_lay.setContentsMargins(4, 2, 4, 2)
        lb_lay.addWidget(QLabel("● Live Telemetry EventStream (In-Process Direct SQLite + EngineBus)"))
        lb_lay.addStretch()
        self.lbl_event_count = QLabel("Showing live events")
        self.lbl_event_count.setStyleSheet("color: #64748b; font-size: 8pt;")
        lb_lay.addWidget(self.lbl_event_count)
        p0_lay.addWidget(live_bar)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.document().setMaximumBlockCount(LIVE_PREVIEW_BLOCKS)
        self.console.setFont(QFont("Consolas", 9))
        self.console.setStyleSheet(
            "background: #05080f; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;"
        )
        p0_lay.addWidget(self.console, 1)

        # Clear Console & Sweep Zombie Nodes buttons
        c_btn_row = QHBoxLayout()
        c_btn_row.addStretch()

        btn_sweep_zombies = QPushButton("🧹 Audit Zombie Nodes")
        btn_sweep_zombies.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #0284c7); color: #ffffff; border-radius: 4px; padding: 4px 12px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { background: #059669; }"
        )
        btn_sweep_zombies.clicked.connect(self._sweep_zombies)
        c_btn_row.addWidget(btn_sweep_zombies)

        btn_clear = QPushButton("🗑️ Clear Live Stream")
        btn_clear.setStyleSheet("background: #1e293b; color: #94a3b8; border-radius: 4px; padding: 4px 10px; font-size: 8pt;")
        btn_clear.clicked.connect(self.console.clear)
        c_btn_row.addWidget(btn_clear)
        p0_lay.addLayout(c_btn_row)

        self.deck.addWidget(page_live)

        # Page 1: Persistent Archive (Table + Filters + Search + Pagination)
        page_archive = QWidget()
        p1_lay = QVBoxLayout(page_archive)
        p1_lay.setContentsMargins(0, 0, 0, 0)
        p1_lay.setSpacing(8)

        # Filter bar
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background: #0f141f; border: 1px solid #1e293b; border-radius: 6px; padding: 6px 12px;")
        fb_lay = QHBoxLayout(filter_bar)
        fb_lay.setContentsMargins(6, 4, 6, 4)
        fb_lay.setSpacing(8)

        self.cmb_level = QComboBox()
        self.cmb_level.addItems(["ALL", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.cmb_level.setStyleSheet("background: #090d14; color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 4px;")
        self.cmb_level.currentTextChanged.connect(self._on_filter_changed)
        fb_lay.addWidget(self.cmb_level)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search logs by keyword...")
        self.txt_search.setStyleSheet("background: #090d14; color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 4px;")
        self.txt_search.returnPressed.connect(self._on_search)
        fb_lay.addWidget(self.txt_search, 1)

        btn_search = QPushButton("🔍 Search")
        btn_search.setStyleSheet("background: #2563eb; color: #ffffff; border-radius: 4px; padding: 6px 16px; font-weight: bold;")
        btn_search.clicked.connect(self._on_search)
        fb_lay.addWidget(btn_search)

        p1_lay.addWidget(filter_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Level", "Logger", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(
            "QTableWidget { background: #05080f; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 8px; }"
            "QHeaderView::section { background: #0f141f; color: #94a3b8; font-weight: bold; border: 1px solid #1e293b; padding: 6px; }"
        )
        p1_lay.addWidget(self.table, 1)

        # Pagination bar
        page_bar = QHBoxLayout()
        self.lbl_page_info = QLabel("Showing 0 of 0 logs")
        self.lbl_page_info.setStyleSheet("color: #64748b; font-size: 8pt;")
        page_bar.addWidget(self.lbl_page_info)
        page_bar.addStretch()

        self.btn_prev = QPushButton("◀ Previous")
        self.btn_prev.setStyleSheet("background: #1e293b; color: #f8fafc; border-radius: 4px; padding: 4px 12px;")
        self.btn_prev.clicked.connect(self._on_prev_page)
        page_bar.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.setStyleSheet("background: #1e293b; color: #f8fafc; border-radius: 4px; padding: 4px 12px;")
        self.btn_next.clicked.connect(self._on_next_page)
        page_bar.addWidget(self.btn_next)

        p1_lay.addLayout(page_bar)

        self.deck.addWidget(page_archive)
        main_layout.addWidget(self.deck, 1)

    def _set_mode(self, mode: str) -> None:
        if mode == "live":
            self.btn_live.setChecked(True)
            self.btn_archive.setChecked(False)
            self.btn_live.setStyleSheet(
                "QPushButton { background: #1e293b; color: #38bdf8; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 8.5pt; }"
            )
            self.btn_archive.setStyleSheet(
                "QPushButton { background: transparent; color: #94a3b8; border: none; border-radius: 4px; padding: 6px 14px; font-size: 8.5pt; }"
            )
            self.deck.setCurrentIndex(0)
        else:
            self.btn_live.setChecked(False)
            self.btn_archive.setChecked(True)
            self.btn_archive.setStyleSheet(
                "QPushButton { background: #1e293b; color: #38bdf8; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 8.5pt; }"
            )
            self.btn_live.setStyleSheet(
                "QPushButton { background: transparent; color: #94a3b8; border: none; border-radius: 4px; padding: 6px 14px; font-size: 8.5pt; }"
            )
            self.deck.setCurrentIndex(1)
            self._load_history()

    def _poll_live_updates(self) -> None:
        """Pulls latest hardware telemetry and new logs."""
        # 1. Update Hardware & GPU Telemetry
        try:
            snap = self.gpu_probe.sample()
        except Exception:
            snap = {}
        if not isinstance(snap, dict) or snap.get("detected") is not True:
            snap = {}
        name = snap.get("name")
        total_g = _measured_number(snap.get("vram_total_gb"))
        used_g = _measured_number(snap.get("vram_used_gb"))
        temp = _measured_number(snap.get("temp_c"), minimum=-273.15)
        load = _measured_number(snap.get("util_pct"), maximum=100)
        self.lbl_gpu_device.setText(f"⚡ {escape(name)}" if isinstance(name, str) and name else "GPU telemetry unavailable")
        self.lbl_gpu_temp.setText(f"Temp: {temp:g}°C" if temp is not None else "Temperature unavailable")
        self.lbl_gpu_load.setText(f"GPU Load: {load:g}%" if load is not None else "GPU load unavailable")
        valid_memory = total_g is not None and total_g > 0 and used_g is not None and used_g <= total_g
        self.lbl_vram_alloc.setText(f"Allocated VRAM: {used_g:.2f} GB" if valid_memory else "Allocated VRAM unavailable")
        self.lbl_vram_free.setText(f"VRAM headroom: {total_g-used_g:.2f} GB" if valid_memory else "VRAM headroom unavailable")
        self.vram_meter.setEnabled(valid_memory)
        self.vram_meter.setValue(round(used_g/total_g*100) if valid_memory else 0)

        # 2. Append new logs to Live Stream console
        try:
            with closing(_ensure_log_db()) as conn:
                rows = conn.execute(
                    "SELECT id, timestamp, level, name, message FROM logs WHERE id > ? ORDER BY id ASC LIMIT 50",
                    (self._last_log_id,),
                ).fetchall()
            for r in rows:
                log_id, ts, lvl, name, msg = r
                self._last_log_id = log_id
                ts, lvl, name, msg = (str(value) for value in (ts, lvl, name, msg))
                time_str = ts[11:19] if len(ts) >= 19 else ts
                color = "#38bdf8"
                if lvl in ("ERROR", "CRITICAL"):
                    color = "#ef4444"
                elif lvl == "WARNING":
                    color = "#f59e0b"
                elif lvl == "INFO":
                    color = "#38bdf8"

                self.console.append(
                    f"<span style='color: #64748b;'>[{escape(time_str)}]</span> "
                    f"<span style='color: {color}; font-weight: bold;'>[{escape(lvl)}]</span> "
                    f"<span style='color: #a855f7;'>[{escape(name)}]</span> "
                    f"<span style='color: #f1f5f9;'>{escape(msg[:32768])}</span>"
                )
            self.lbl_event_count.setText("Producer log stream available")
        except Exception:
            self.lbl_event_count.setText("Log source unavailable")

    def _load_history(self) -> None:
        """Queries persistent archive SQLite database with pagination and search."""
        lvl = self.cmb_level.currentText()
        query_text = self.txt_search.text().strip()

        try:
            sql = "SELECT timestamp, level, name, message FROM logs WHERE 1=1"
            params: list[str | int] = []
            if lvl != "ALL":
                sql += " AND level = ?"
                params.append(lvl)
            if query_text:
                sql += " AND (message LIKE ? OR name LIKE ?)"
                params.extend([f"%{query_text}%", f"%{query_text}%"])

            # Count total
            count_sql = f"SELECT COUNT(*) FROM ({sql})"
            # Fetch page
            sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
            with closing(_ensure_log_db()) as conn:
                total = conn.execute(count_sql, params).fetchone()[0]
                rows = conn.execute(sql, [*params, self._page_limit, self._history_page * self._page_limit]).fetchall()

            self.table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                ts_item = QTableWidgetItem(str(r[0]))
                lvl_item = QTableWidgetItem(str(r[1]))
                name_item = QTableWidgetItem(str(r[2]))
                msg_item = QTableWidgetItem(str(r[3]))

                lvl_val = str(r[1])
                if lvl_val in ("ERROR", "CRITICAL"):
                    lvl_item.setForeground(QColor("#ef4444"))
                elif lvl_val == "WARNING":
                    lvl_item.setForeground(QColor("#f59e0b"))
                else:
                    lvl_item.setForeground(QColor("#38bdf8"))

                self.table.setItem(i, 0, ts_item)
                self.table.setItem(i, 1, lvl_item)
                self.table.setItem(i, 2, name_item)
                self.table.setItem(i, 3, msg_item)

            self.lbl_page_info.setText(f"Showing {len(rows)} of {total} logs (Page {self._history_page + 1})")
            self.btn_prev.setEnabled(self._history_page > 0)
            self.btn_next.setEnabled((self._history_page + 1) * self._page_limit < total)
        except Exception:
            self.table.setRowCount(0)
            self.lbl_page_info.setText("Archive unavailable: existing producer log source is not readable")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)

    def _on_filter_changed(self) -> None:
        self._history_page = 0
        self._load_history()

    def _on_search(self) -> None:
        self._history_page = 0
        self._load_history()

    def _on_prev_page(self) -> None:
        if self._history_page > 0:
            self._history_page -= 1
            self._load_history()

    def _on_next_page(self) -> None:
        self._history_page += 1
        self._load_history()

    def _sweep_zombies(self) -> None:
        t_str = datetime.utcnow().strftime("%H:%M:%S")
        self.console.append(f"<span style='color: #38bdf8;'>[{t_str}] [PROCESS AUDIT] Inspecting orphan candidates; no process termination.</span>")
        def _do_sweep():
            from native_studio.service_orchestrator import sweep_zombie_nodes_native
            return sweep_zombie_nodes_native(dry_run=True)
        self.bus.submit(_do_sweep, on_result=self._on_zombies_swept,
                        on_error=lambda _: self.console.append("Process audit unavailable; host health was not established."))

    def _on_zombies_swept(self, res: dict) -> None:
        if not isinstance(res, dict) or res.get("error"):
            self.console.append("Process audit unavailable; host health was not established.")
            return
        actions = res.get("actions", [])
        self.console.append(f"Process audit finished; {len(actions) if isinstance(actions, list) else 0} reported actions. No process termination requested.")
        if isinstance(actions, list):
            for action in actions[:200]:
                self.console.append(escape(str(action)[:4096]))

    def shutdown(self) -> None:
        """Stop this view's observer when its containing window closes."""
        self.timer.stop()
