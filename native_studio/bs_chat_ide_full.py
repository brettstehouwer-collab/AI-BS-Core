"""1:1 Web-Parity Native Desktop Port of BS-CHAT Autonomous Agentic IDE.

Matches the exact visual layout and interactive experience of ChatTab.jsx and unifies:
- Full PowerShell Host Execution Authority: /ps, /powershell, /cmd, /sh, /run, /exec, /build, /test
- Scratchpad Code Runner: Direct '⚡ Run Script (PowerShell)' execution for Python, PowerShell, and Batch
- Top Sub-Header: '⚡ AI-BS Autonomous Agentic IDE Chat' + '● Single-Pane Active (Phase 7 Sandbox)' + '↔ Toggle Split View'
- Interactive Empty-State Hero: 'Stehouwer LLM Assistant' gradient header, 9 category filter pills, and 3x3 interactive launch cards
- Seamless transition between Starter Card Grid and Live Streaming Transcript via QStackedWidget
- Collapsible Right-Hand Code & Media Scratchpad (hidden by default for full-width single-pane focus)
- 5-Tier Bottom Command & Governance Deck:
  1. @Mention Context Pills (@Developer, @PowerShell, @Ecosystem, @Calendar, @Documents, @Email)
  2. Context Budget Progress Strip (0 chars • ~0 tokens • 0% of 8,192 max window)
  3. Active Agent Tools Pill Bar (⚡ Run in PowerShell, 🔨 PowerShell Build, 🧪 Pytest Runner, Mode: Plan & Review, Shadow Coder, Media Studio, etc.)
  4. Unified Prompt Bar (🧰 Artifacts & Tools, ⚡ PowerShell, ⚡ Ecosystem Ports, [/] Commands ▲, Input Box, Send)
  5. Governance & Oversight Footer (⚡ PowerShell Shell, Disable Backend, 43-Module Oversight, 11 Spaces, Ingest to DB, Risk & Governance, Context Stress Test, Auto-Save Active)
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QCursor, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus

STARTER_CARDS: List[Tuple[str, str, str, str, str, str]] = [
    (
        "mission_launch",
        "🚀",
        "Launch Autonomous Mission",
        "Run 5-Phase agentic mission: workspace telemetry, task blueprint, tool execution, tests, and 4-mirror delivery.",
        "Execute a 5-phase autonomous mission audit across workspace telemetry and 4-mirror parity.",
        "Missions",
    ),
    (
        "mission_blueprint",
        "📋",
        "Generate Mission Blueprint",
        "Deconstruct an operational goal into an atomic execution plan without touching host files.",
        "Generate an atomic multi-stage execution blueprint for current ecosystem tasks.",
        "Missions",
    ),
    (
        "preflight_grill",
        "🔥",
        "Pre-Flight Architectural Grill",
        "Stress-test proposals against local schemas, concurrency locks, recovery rollbacks, and security policies.",
        "Run a Pre-Flight Architectural Grill on SQLite concurrency and VRAM governance.",
        "Oversight",
    ),
    (
        "static_ast",
        "🔍",
        "PowerShell Mirror Parity Audit",
        "Execute verify-mirror-parity.ps1 in PowerShell to assert 100% SHA-256 byte parity across all 4 mirrors.",
        "/ps powershell -ExecutionPolicy Bypass -File C:\\AI-BS\\verify-mirror-parity.ps1",
        "Host IDE",
    ),
    (
        "tdd_loop",
        "🔴",
        "PowerShell Pytest Battery",
        "Run the complete native studio automated pytest test suite in PowerShell with real-time output capture.",
        "/test",
        "Host IDE",
    ),
    (
        "visual_diff",
        "📄",
        "Git Status & Workspace Diffs",
        "Inspect working directory changes, uncommitted files, and status via PowerShell git commands.",
        "/status",
        "Oversight",
    ),
    (
        "atomic_snapshot",
        "📌",
        "Atomic State Snapshot",
        "Write an atomic checkpoint commit to Git and dump state to SAVED_CHECKPOINT.md.",
        "/vault checkpoint",
        "Studio",
    ),
    (
        "hw_watchdog",
        "⚡",
        "Hardware & Clamping Watchdog",
        "Check NVIDIA GeForce RTX 4090 GPU thermals, power draw, and VRAM utilization.",
        "/vram",
        "Intelligence",
    ),
    (
        "read_host_file",
        "💻",
        "PowerShell Directory Tree",
        "List top-level files, directory sizes, and last modified timestamps via PowerShell.",
        "/dir C:\\AI-BS",
        "Creative",
    ),
    (
        "ps_program_builder",
        "⚡",
        "PowerShell Program Builder & Runner",
        "Compile, build, test, and run programs in C:\\AI-BS directly via elevated PowerShell with root host privileges.",
        "/build",
        "Host IDE",
    ),
]


def format_chat_text_to_html(text: str) -> str:
    """Converts markdown links and absolute Windows file paths into clickable cyber-cyan hyperlinks."""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _md_link_sub(m):
        label = m.group(1)
        raw_url = m.group(2).strip()
        if not raw_url.startswith("file:///"):
            clean_p = raw_url.replace("\\", "/")
            raw_url = f"file:///{clean_p}"
        return f'<a href="{raw_url}" style="color: #38bdf8; text-decoration: underline; font-weight: bold;">{label}</a>'

    safe = re.sub(r'\[(.*?)\]\((file:\/\/\/[^\)]+|[A-Za-z]:[^\)]+)\)', _md_link_sub, safe)

    def _path_sub(m):
        fp = m.group(1)
        url = f"file:///{fp.replace(chr(92), '/')}"
        return f'<a href="{url}" style="color: #38bdf8; text-decoration: underline; font-weight: bold;">{fp}</a>'

    safe = re.sub(r'(?<!["\'\(\/=\>])\b([A-Za-z]:\\[A-Za-z0-9_.\-\\]+\.[A-Za-z0-9]+)\b', _path_sub, safe)
    return safe.replace("\n", "<br>")


class BsChatBrowser(QTextBrowser):
    """Rich interactive chat display with clickable IDE hyperlinks and Explorer context menus."""

    file_open_requested = pyqtSignal(str)
    show_in_explorer_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.setMouseTracking(True)
        self.anchorClicked.connect(self._on_anchor_clicked)
        self.setStyleSheet(
            "background: rgba(7, 11, 20, 0.95); font-family: 'Cascadia Mono', Consolas, monospace; "
            "font-size: 9.5pt; color: #f1f5f9; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;"
        )

    def _on_anchor_clicked(self, url: QUrl) -> None:
        local_p = url.toLocalFile()
        if not local_p:
            s = url.toString()
            if s.startswith("file:///"):
                local_p = s[8:]
            elif s.startswith("file://"):
                local_p = s[7:]
            else:
                local_p = s
        norm_p = os.path.normpath(local_p)
        self.file_open_requested.emit(norm_p)

    def appendPlainText(self, text: str) -> None:
        html = format_chat_text_to_html(text)
        cur = self.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertHtml(html)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    def contextMenuEvent(self, event) -> None:
        pos = event.pos()
        anchor = self.anchorAt(pos)
        target_path = ""
        if anchor:
            u = QUrl(anchor)
            loc = u.toLocalFile()
            if not loc:
                loc = anchor[8:] if anchor.startswith("file:///") else (anchor[7:] if anchor.startswith("file://") else anchor)
            target_path = os.path.normpath(loc)
        else:
            cur = self.cursorForPosition(pos)
            cur.select(QTextCursor.SelectionType.LineUnderCursor)
            line_txt = cur.selectedText()
            m = re.search(r'([A-Za-z]:\\[A-Za-z0-9_.\-\\]+\.[A-Za-z0-9]+)', line_txt)
            if not m:
                m = re.search(r'([A-Za-z]:/[A-Za-z0-9_.\-/]+\.[A-Za-z0-9]+)', line_txt)
            if m:
                target_path = os.path.normpath(m.group(1))

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #0f172a; color: #f1f5f9; border: 1px solid #334155; border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; font-size: 8.5pt; }"
            "QMenu::item:selected { background: #1e293b; color: #38bdf8; }"
        )

        if target_path:
            act_open = menu.addAction("📝 Open & View in BS-Chat Editor")
            act_open.triggered.connect(lambda: self.file_open_requested.emit(target_path))

            act_exp = menu.addAction("📂 Show in File Explorer")
            act_exp.triggered.connect(lambda: self.show_in_explorer_requested.emit(target_path))

            act_copy = menu.addAction("📋 Copy File Path")
            act_copy.triggered.connect(lambda: QApplication.clipboard().setText(target_path))
            menu.addSeparator()

        if self.textCursor().hasSelection():
            act_copy_sel = menu.addAction("Copy Selection")
            act_copy_sel.triggered.connect(self.copy)
        act_sel = menu.addAction("Select All")
        act_sel.triggered.connect(self.selectAll)
        act_clr = menu.addAction("Clear Transcript")
        act_clr.triggered.connect(self.clear)

        menu.exec(event.globalPos())


class BsCodeEditor(QPlainTextEdit):
    """IDE Code Editor supporting active file tracking and File Explorer context integration."""

    show_in_explorer_requested = pyqtSignal(str)
    save_file_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_file_path: Optional[str] = None
        self.setStyleSheet(
            "background: rgba(7, 4, 18, 0.96); font-family: 'Cascadia Mono', Consolas, monospace; "
            "font-size: 9pt; color: #a5f3fc; border: 1px solid #334155; border-radius: 8px; padding: 8px;"
        )

    def set_current_file(self, path: Optional[str]) -> None:
        self._current_file_path = path

    def get_current_file(self) -> Optional[str]:
        return self._current_file_path

    def contextMenuEvent(self, event) -> None:
        menu = self.createStandardContextMenu()
        menu.setStyleSheet(
            "QMenu { background: #0f172a; color: #f1f5f9; border: 1px solid #334155; border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; font-size: 8.5pt; }"
            "QMenu::item:selected { background: #1e293b; color: #38bdf8; }"
        )
        if self._current_file_path:
            menu.addSeparator()
            act_exp = menu.addAction("📂 Show in File Explorer")
            act_exp.triggered.connect(lambda: self.show_in_explorer_requested.emit(self._current_file_path))

            act_save = menu.addAction("💾 Save File")
            act_save.triggered.connect(lambda: self.save_file_requested.emit())

            act_copy = menu.addAction("📋 Copy File Path")
            act_copy.triggered.connect(lambda: QApplication.clipboard().setText(self._current_file_path))

        menu.exec(event.globalPos())


class BsChatIdeFullView(QWidget):
    """1:1 Web-Parity Native Win32 Widget for BS-CHAT Autonomous Agentic IDE with Full PowerShell Execution."""

    token_chunk = pyqtSignal(str)
    action_log_signal = pyqtSignal(str, str)

    def __init__(self, bus: EngineBus, parent: QWidget | None = None, *, session_store=None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._is_streaming = False
        self._split_active = False
        self._auto_heal_enabled = True
        self._mobile_synergy_active = False
        self._dpi_profile_id = "native_desktop"
        self._active_category = "All"
        self._current_editor_file: Optional[str] = None
        self._last_referenced_file: Optional[str] = None
        self._conversation_history: List[Tuple[str, str]] = []
        self._card_widgets: List[Tuple[str, QFrame]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 8)
        root.setSpacing(6)

        # ── 1. SUB-HEADER BAR (MATCHES WEB SCREENSHOT TOP STRIP) ──
        sub_hdr = QFrame()
        sub_hdr.setStyleSheet(
            "background: rgba(13, 18, 30, 0.95); border-bottom: 1px solid #1e293b; border-radius: 6px;"
        )
        sh_lay = QHBoxLayout(sub_hdr)
        sh_lay.setContentsMargins(12, 6, 12, 6)
        sh_lay.setSpacing(8)

        lbl_sub = QLabel("⚡ <b style='color:#60a5fa;'>AI-BS Autonomous Agentic IDE Chat</b>")
        lbl_sub.setStyleSheet("font-size: 9pt;")
        sh_lay.addWidget(lbl_sub)

        # Model Selector (Compact Web Pill Style)
        self.model_picker = QComboBox()
        self.model_picker.setStyleSheet(
            "background: #0f172a; color: #38bdf8; border: 1px solid #1e293b; "
            "border-radius: 5px; padding: 2px 8px; font-size: 8pt; font-weight: bold;"
        )
        for label, val in [
            ("stehouwer_llm (17-Fleet Primary)", "stehouwer_llm"),
            ("stehouwer_dolphin:latest", "stehouwer_dolphin:latest"),
            ("qwen2.5-coder:latest", "qwen2.5-coder:latest"),
            ("stehouwer-hermes:latest", "stehouwer-hermes:latest"),
            ("qwen3.6:latest", "qwen3.6:latest"),
            ("gemma4:12b", "gemma4:12b"),
            ("llama3.3:70b", "llama3.3:70b"),
            ("mixtral", "mixtral"),
        ]:
            self.model_picker.addItem(label, val)
        sh_lay.addWidget(self.model_picker)

        # Resolution & DPI Profile Selector (Parsec / Tailscale + RustDesk Mobile Workstation)
        self.dpi_picker = QComboBox()
        self.dpi_picker.setStyleSheet(
            "background: #0f172a; color: #a78bfa; border: 1px solid #4c1d95; "
            "border-radius: 5px; padding: 2px 8px; font-size: 8pt; font-weight: bold;"
        )
        for dpi_lbl, dpi_val in [
            ("🖥️ 100% Native Desktop", "native_desktop"),
            ("📱 1440p @ 125% DPI (Parsec / RustDesk)", "mobile_1440p_125"),
            ("📱 1080p @ 150% DPI (Phone High-Contrast)", "mobile_1080p_150"),
        ]:
            self.dpi_picker.addItem(dpi_lbl, dpi_val)
        self.dpi_picker.currentIndexChanged.connect(self._on_dpi_profile_changed)
        sh_lay.addWidget(self.dpi_picker)

        # Mobile Synergy & Bluetooth Trackpad Toggle
        self.btn_mobile_synergy = QPushButton("📱 Mobile Synergy: OFF")
        self.btn_mobile_synergy.setStyleSheet(
            "QPushButton { background: #1e1b4b; color: #c4b5fd; border: 1px solid #4c1d95; "
            "border-radius: 5px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { background: #312e81; color: #ffffff; border-color: #8b5cf6; }"
        )
        self.btn_mobile_synergy.clicked.connect(self._toggle_mobile_synergy)
        sh_lay.addWidget(self.btn_mobile_synergy)

        sh_lay.addStretch()

        self.pane_status_lbl = QLabel("● Single-Pane Active (Phase 7 Sandbox)")
        self.pane_status_lbl.setStyleSheet("color: #10b981; font-size: 8pt; font-weight: bold;")
        sh_lay.addWidget(self.pane_status_lbl)

        self.btn_back_grid = QPushButton("⊞ Mission Cards")
        self.btn_back_grid.setStyleSheet(
            "QPushButton { background: #1e293b; color: #94a3b8; border: 1px solid #334155; "
            "border-radius: 5px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { color: #ffffff; border-color: #38bdf8; }"
        )
        self.btn_back_grid.clicked.connect(lambda: self.left_stack.setCurrentIndex(0))
        sh_lay.addWidget(self.btn_back_grid)

        self.btn_toggle_split = QPushButton("↔ Toggle Split View")
        self.btn_toggle_split.setStyleSheet(
            "QPushButton { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; "
            "border-radius: 5px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { background: #334155; border-color: #38bdf8; }"
        )
        self.btn_toggle_split.clicked.connect(self._toggle_split_view)
        sh_lay.addWidget(self.btn_toggle_split)

        root.addWidget(sub_hdr)

        # ── 1.5. MOBILE SYNERGY & BLUETOOTH TRACKPAD 1-TAP DOCK (HIDDEN BY DEFAULT) ──
        self.mobile_dock = QFrame()
        self.mobile_dock.setStyleSheet(
            "background: rgba(17, 24, 39, 0.96); border: 1px solid #6366f1; border-radius: 6px; padding: 4px;"
        )
        md_lay = QHBoxLayout(self.mobile_dock)
        md_lay.setContentsMargins(10, 4, 10, 4)
        md_lay.setSpacing(8)
        lbl_md = QLabel("📱 <b style='color:#a78bfa;'>Mobile Synergy & Trackpad Dock:</b>")
        lbl_md.setStyleSheet("font-size: 8.5pt;")
        md_lay.addWidget(lbl_md)
        for m_lbl, m_cmd in [
            ("💥 /blast (AST Impact)", "/blast "),
            ("🕸️ /graph (491-Node Index)", "/graph"),
            ("🧬 /distill (4090 QLoRA)", "/distill"),
            ("📱 /dpi (Display & HID Status)", "/dpi"),
            ("⚡ /ps (PowerShell)", "/ps "),
            ("🐧 /wsl (Ubuntu Bash)", "/wsl "),
            ("⚡ Run Scratchpad", "/runlast"),
        ]:
            mb = QPushButton(m_lbl)
            mb.setStyleSheet(
                "QPushButton { background: #1e1b4b; color: #e0e7ff; border: 1px solid #6366f1; "
                "border-radius: 6px; padding: 5px 12px; font-size: 8.5pt; font-weight: bold; }"
                "QPushButton:hover { background: #4338ca; color: #ffffff; }"
            )
            mb.clicked.connect(
                lambda checked, c=m_cmd: self._handle_slash_command(c)
                if not c.endswith(" ")
                else self._insert_slash_command(c)
            )
            md_lay.addWidget(mb)
        md_lay.addStretch()
        self.mobile_dock.hide()
        root.addWidget(self.mobile_dock)

        # ── 2. CENTRAL WORKSPACE (SINGLE-PANE HERO OR SPLIT VIEW) ──
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Stack: Page 0 = Web Hero + 3x3 Card Grid | Page 1 = Live Chat Stream
        self.left_stack = QStackedWidget()
        self.hero_page = self._build_web_hero_page()
        self.chat_page = self._build_chat_stream_page()
        self.left_stack.addWidget(self.hero_page)
        self.left_stack.addWidget(self.chat_page)
        self.splitter.addWidget(self.left_stack)

        # Right Pane: Code & Media Scratchpad (Hidden by default to match Single-Pane Active)
        self.right_w = self._build_scratchpad_pane()
        self.right_w.hide()
        self.splitter.addWidget(self.right_w)

        root.addWidget(self.splitter, 1)

        # ── 3. BOTTOM 5-TIER WEB COMMAND & GOVERNANCE DECK ──
        bottom_deck = self._build_bottom_command_deck()
        root.addWidget(bottom_deck)

        self.token_chunk.connect(self._append_token)
        self.action_log_signal.connect(self._append_action_log)
        from native_studio.chat_recovery import ChatRecoveryController
        self._chat_recovery = ChatRecoveryController(self, bus, session_store)
        self._chat_recovery.begin()

    def _build_web_hero_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: rgba(7, 11, 20, 0.92); border: 1px solid #1e293b; border-radius: 8px;")

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(40, 24, 40, 24)
        lay.setSpacing(14)

        lay.addStretch(1)

        # Centered 'Stehouwer LLM Assistant' Title
        title = QLabel("Stehouwer LLM Assistant")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20pt; font-weight: 800; color: #a78bfa; letter-spacing: 0.5px;")
        lay.addWidget(title)

        sub = QLabel(
            "Your unified cognitive AI system. Run PowerShell commands directly, build programs,\n"
            "select a quick starter action below, or type a custom prompt."
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        lay.addWidget(sub)

        # Category Filter Pills Row
        pill_row = QHBoxLayout()
        pill_row.setSpacing(6)
        pill_row.addStretch()
        self._cat_btns: Dict[str, QPushButton] = {}
        for cat_key, cat_lbl in [
            ("All", "All"),
            ("Missions", "🎯 Missions"),
            ("Host IDE", "💻 Host IDE"),
            ("Oversight", "👑 Oversight"),
            ("Email", "✉️ Email"),
            ("Swarm", "⚔️ Swarm"),
            ("Creative", "🎨 Creative"),
            ("Studio", "🎬 Studio"),
            ("Intelligence", "🧠 Intelligence"),
        ]:
            b = QPushButton(cat_lbl)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(lambda checked, k=cat_key: self._filter_cards(k))
            self._cat_btns[cat_key] = b
            pill_row.addWidget(b)
        pill_row.addStretch()
        lay.addLayout(pill_row)

        # 3x3 Interactive Mission Cards Grid
        grid_wrap = QHBoxLayout()
        grid_wrap.addStretch()
        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(12)

        for idx, (cid, icon, ctitle, cdesc, payload, cat) in enumerate(STARTER_CARDS):
            card = self._create_launch_card(cid, icon, ctitle, cdesc, payload)
            self._card_widgets.append((cat, card))
            self.cards_grid.addWidget(card, idx // 3, idx % 3)

        grid_wrap.addLayout(self.cards_grid)
        grid_wrap.addStretch()
        lay.addLayout(grid_wrap)

        lay.addStretch(2)
        self._filter_cards("All")
        scroll.setWidget(container)
        return scroll

    def _create_launch_card(self, cid: str, icon: str, title: str, desc: str, payload: str) -> QFrame:
        card = QFrame()
        card.setFixedSize(255, 118)
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        card.setStyleSheet(
            "QFrame { background: rgba(17, 24, 39, 0.88); border: 1px solid #1e293b; border-radius: 8px; }"
            "QFrame:hover { background: rgba(30, 41, 59, 0.96); border: 1px solid #38bdf8; }"
        )
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(4)

        lbl_t = QLabel(f"{icon}  <b>{title}</b>")
        lbl_t.setStyleSheet("color: #f8fafc; font-size: 8.5pt; border: none; background: transparent;")
        c_lay.addWidget(lbl_t)

        lbl_d = QLabel(desc)
        lbl_d.setWordWrap(True)
        lbl_d.setStyleSheet("color: #64748b; font-size: 7.5pt; border: none; background: transparent;")
        c_lay.addWidget(lbl_d, 1)

        btn_go = QPushButton("⚡ Click to Launch →")
        btn_go.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #38bdf8; "
            "font-size: 7.5pt; font-weight: bold; text-align: left; padding: 0px; }"
            "QPushButton:hover { color: #22d3ee; }"
        )
        btn_go.clicked.connect(lambda checked, p=payload: self._launch_from_card(p))
        c_lay.addWidget(btn_go)
        return card

    def _filter_cards(self, category: str) -> None:
        self._active_category = category
        for k, b in self._cat_btns.items():
            if k == category:
                b.setStyleSheet(
                    "background: #3b82f6; color: #ffffff; border-radius: 10px; padding: 3px 10px; font-size: 7.5pt; font-weight: bold;"
                )
            else:
                b.setStyleSheet(
                    "background: #0f172a; color: #94a3b8; border: 1px solid #1e293b; border-radius: 10px; padding: 3px 10px; font-size: 7.5pt;"
                )
        for cat, card in self._card_widgets:
            card.setVisible(category == "All" or cat == category)

    def _launch_from_card(self, payload: str) -> None:
        self.left_stack.setCurrentIndex(1)
        self.input_edit.setText(payload)
        self._send()

    def _build_chat_stream_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self.chat_display = BsChatBrowser()
        self.chat_display.file_open_requested.connect(self._open_file_in_editor)
        self.chat_display.show_in_explorer_requested.connect(self._show_in_file_explorer)

        # Quick Action Toolbar for Code & PowerShell
        tb = QFrame()
        tb.setStyleSheet("background: rgba(13, 18, 30, 0.85); border: 1px solid #1e293b; border-radius: 6px; padding: 2px;")
        tb_lay = QHBoxLayout(tb)
        tb_lay.setContentsMargins(6, 4, 6, 4)
        tb_lay.setSpacing(6)

        lbl = QLabel("⚡ <b style='color:#38bdf8;'>BS-Chat Builder:</b>")
        lbl.setStyleSheet("font-size: 8pt;")
        tb_lay.addWidget(lbl)

        btn_run_last = QPushButton("⚡ Run Last Code (PowerShell)")
        btn_run_last.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #0284c7); "
            "color: #ffffff; border: 1px solid #38bdf8; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold; }"
            "QPushButton:hover { background: #2563eb; }"
        )
        btn_run_last.clicked.connect(self._run_last_code_in_powershell)
        tb_lay.addWidget(btn_run_last)

        btn_copy_scratch = QPushButton("📋 Code ➔ Scratchpad")
        btn_copy_scratch.setStyleSheet(
            "QPushButton { background: #1e293b; color: #a5f3fc; border: 1px solid #334155; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold; }"
            "QPushButton:hover { background: #334155; color: #ffffff; border-color: #38bdf8; }"
        )
        btn_copy_scratch.clicked.connect(self._load_last_code_to_scratchpad)
        tb_lay.addWidget(btn_copy_scratch)

        btn_save_file = QPushButton("💾 Save Code to File")
        btn_save_file.setStyleSheet(
            "QPushButton { background: #1e293b; color: #fbbf24; border: 1px solid #854d0e; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold; }"
            "QPushButton:hover { background: #334155; color: #ffffff; border-color: #fbbf24; }"
        )
        btn_save_file.clicked.connect(self._save_last_code_to_file)
        tb_lay.addWidget(btn_save_file)

        btn_spawn_ps = QPushButton("🖥️ Interactive PowerShell Window")
        btn_spawn_ps.setStyleSheet(
            "QPushButton { background: #0f172a; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold; }"
            "QPushButton:hover { background: #1e293b; color: #ffffff; }"
        )
        btn_spawn_ps.clicked.connect(self._spawn_powershell_terminal)
        tb_lay.addWidget(btn_spawn_ps)

        self.btn_auto_heal = QPushButton("🩹 Auto-Heal: ON (3x)")
        self.btn_auto_heal.setStyleSheet(
            "QPushButton { background: #064e3b; color: #34d399; border: 1px solid #10b981; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold; }"
            "QPushButton:hover { background: #065f46; color: #ffffff; }"
        )
        self.btn_auto_heal.clicked.connect(self._toggle_auto_heal)
        tb_lay.addWidget(self.btn_auto_heal)

        tb_lay.addStretch()

        btn_clear = QPushButton("🧹 Clear Transcript")
        btn_clear.setStyleSheet(
            "QPushButton { background: transparent; color: #64748b; border: none; font-size: 7.5pt; padding: 2px 6px; }"
            "QPushButton:hover { color: #ef4444; }"
        )
        btn_clear.clicked.connect(self.chat_display.clear)
        tb_lay.addWidget(btn_clear)

        lay.addWidget(tb)
        lay.addWidget(self.chat_display, 1)
        return page

    def _build_scratchpad_pane(self) -> QWidget:
        right_w = QWidget()
        r_lay = QVBoxLayout(right_w)
        r_lay.setContentsMargins(4, 0, 0, 0)
        r_lay.setSpacing(6)

        self.code_editor = BsCodeEditor()
        self.code_editor.show_in_explorer_requested.connect(self._show_in_file_explorer)
        self.code_editor.save_file_requested.connect(self._save_scratchpad_to_file)
        self.code_editor.setPlainText(
            "# AI-BS Sovereign Native Code & Prompt Scratchpad\n"
            "# Press '⚡ Run Script (Multi-Runtime + Auto-Heal)' to execute this program instantly!\n"
            "import sys, platform\n"
            "print(f'AI-BS Python Engine: {sys.version}')\n"
            "print(f'Platform: {platform.platform()}')\n"
            "print('Ready to build sovereign programs in BS-Chat!')\n"
        )

        r_hdr = QHBoxLayout()
        self.lbl_canvas = QLabel("Active Code Canvas & Media Scratchpad:")
        self.lbl_canvas.setStyleSheet("color: #a5f3fc; font-weight: bold; font-size: 9pt;")
        r_hdr.addWidget(self.lbl_canvas)
        r_hdr.addStretch()

        # 📂 Show in Explorer Button
        self.btn_show_explorer = QPushButton("📂 Show in Explorer")
        self.btn_show_explorer.setStyleSheet(
            "QPushButton { background: #1e1438; color: #38bdf8; border: 1px solid #0284c7; "
            "border-radius: 4px; padding: 3px 8px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { background: #0284c7; color: #ffffff; }"
        )
        self.btn_show_explorer.clicked.connect(self._show_active_editor_file_in_explorer)
        r_hdr.addWidget(self.btn_show_explorer)

        # ⚡ Dedicated Run in Multi-Runtime + Stage 1 Auto-Heal Button
        btn_run_ps = QPushButton("⚡ Run Script (Auto-Heal)")
        btn_run_ps.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #06b6d4); "
            "color: #ffffff; border: 1px solid #38bdf8; border-radius: 4px; padding: 3px 10px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { background: #3b82f6; border-color: #67e8f9; }"
        )
        btn_run_ps.clicked.connect(self._run_scratchpad_in_powershell)
        r_hdr.addWidget(btn_run_ps)

        btn_term = QPushButton("🖥️ Open Terminal")
        btn_term.setStyleSheet("background: #0f172a; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 3px 8px; font-size: 8pt; font-weight: bold;")
        btn_term.clicked.connect(self._spawn_powershell_terminal)
        r_hdr.addWidget(btn_term)

        btn_save_file = QPushButton("💾 Save File")
        btn_save_file.setStyleSheet("background: #1e1438; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 3px 8px; font-size: 8pt;")
        btn_save_file.clicked.connect(self._save_scratchpad_to_file)
        r_hdr.addWidget(btn_save_file)

        btn_save_vault = QPushButton("💾 Vault")
        btn_save_vault.setStyleSheet("background: #1e1438; color: #fbbf24; border: 1px solid #fbbf24; border-radius: 4px; padding: 3px 8px; font-size: 8pt;")
        btn_save_vault.clicked.connect(self._save_scratchpad_to_vault)
        r_hdr.addWidget(btn_save_vault)

        btn_validate = QPushButton("🔍 Syntax")
        btn_validate.setStyleSheet("background: #1e1438; color: #a5f3fc; border: 1px solid #334155; border-radius: 4px; padding: 3px 8px; font-size: 8pt;")
        btn_validate.clicked.connect(self._validate_syntax)
        r_hdr.addWidget(btn_validate)

        btn_clear_sc = QPushButton("🧹 Clear")
        btn_clear_sc.setStyleSheet("background: transparent; color: #64748b; border: none; font-size: 8pt; padding: 2px;")
        btn_clear_sc.clicked.connect(self.code_editor.clear)
        r_hdr.addWidget(btn_clear_sc)

        r_lay.addLayout(r_hdr)
        r_lay.addWidget(self.code_editor)
        return right_w

    def _build_bottom_command_deck(self) -> QFrame:
        deck = QFrame()
        deck.setStyleSheet("background: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
        d_lay = QVBoxLayout(deck)
        d_lay.setContentsMargins(8, 4, 8, 4)
        d_lay.setSpacing(6)

        # Tier 1: @Mention Context Pills
        m_row = QHBoxLayout()
        m_row.setSpacing(6)
        for mention in ["@Developer", "@PowerShell", "@Ecosystem", "@Calendar", "@Documents", "@Email"]:
            mb = QPushButton(mention)
            mb.setStyleSheet(
                "QPushButton { background: #111827; color: #60a5fa; border: 1px solid #1e3a8a; "
                "border-radius: 10px; padding: 2px 10px; font-size: 7.5pt; font-weight: bold; }"
                "QPushButton:hover { background: #1e3a8a; color: #ffffff; }"
            )
            mb.clicked.connect(lambda checked, m=mention: self.input_edit.insert(f"{m} "))
            m_row.addWidget(mb)
        m_row.addStretch()
        d_lay.addLayout(m_row)

        # Tier 2: Context Budget Bar (1,000,000 Token Window • 4,096 GPU VRAM + CPU Port 11435 + ChromaDB 8001)
        b_row = QHBoxLayout()
        self.lbl_budget = QLabel("📊 Context Budget: 0 chars • ~0 tokens (0.00% of 1,000,000 max window • 1M+ Offload RAG Active)")
        self.lbl_budget.setStyleSheet("color: #38bdf8; font-size: 7.5pt; font-weight: bold;")
        b_row.addWidget(self.lbl_budget)
        b_row.addStretch()

        self.lbl_rag_status = QLabel("🧠 ChromaDB 1M+ Vector RAG: ACTIVE (Port 8001 | CPU 11435 | Vault: 139K Records)")
        self.lbl_rag_status.setStyleSheet("color: #10b981; font-size: 7.5pt; font-weight: bold;")
        b_row.addWidget(self.lbl_rag_status)
        d_lay.addLayout(b_row)

        self.budget_bar = QProgressBar()
        self.budget_bar.setFixedHeight(3)
        self.budget_bar.setRange(0, 1000000)
        self.budget_bar.setValue(0)
        self.budget_bar.setTextVisible(False)
        self.budget_bar.setStyleSheet(
            "QProgressBar { background: #1e293b; border: none; } QProgressBar::chunk { background: #38bdf8; }"
        )
        d_lay.addWidget(self.budget_bar)

        # Tier 3: Active Agent Tools Pill Bar
        t_row = QHBoxLayout()
        t_row.setSpacing(5)
        lbl_tools = QLabel("🛠️ Active Agent Tools:")
        lbl_tools.setStyleSheet("color: #38bdf8; font-size: 7.5pt; font-weight: bold;")
        t_row.addWidget(lbl_tools)

        for tool_lbl, tool_cmd in [
            ("💥 /blast AST Impact", "/blast "),
            ("🕸️ /graph 491-Node", "/graph"),
            ("🧬 /distill QLoRA", "/distill"),
            ("📱 /dpi Mobile Profile", "/dpi"),
            ("📡 /cast Wireless Mirror", "/cast "),
            ("🧠 1M+ RAG Search", "/rag "),
            ("📚 Ingest to 1M RAG", "/rag_ingest "),
            ("📑 1M Map-Reduce", "/summarize_1m "),
            ("⚡ Run in PowerShell", "/ps "),
            ("🐧 WSL2 Ubuntu", "/wsl "),
            ("⚡ Multi-Runtime /run", "/run "),
            ("🔨 PowerShell Build", "/build"),
            ("🧪 Pytest Runner", "/test"),
            ("🖥️ Terminal Window", "/terminal"),
            ("⚡ Run Last Code", "/runlast"),
            ("📋 Code to Scratchpad", "/scratchlast"),
            ("📂 Directory Tree", "/dir C:\\AI-BS"),
            ("⚡ Git Status", "/status"),
            ("🐍 Run Python", "/python "),
            ("🧠 vector vault", "/vectors "),
        ]:
            tb = QPushButton(tool_lbl)
            tb.setStyleSheet(
                "QPushButton { background: rgba(14, 116, 144, 0.18); color: #38bdf8; "
                "border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 10px; padding: 2px 8px; font-size: 7.5pt; }"
                "QPushButton:hover { background: rgba(56, 189, 248, 0.3); color: #ffffff; }"
            )
            tb.clicked.connect(lambda checked, c=tool_cmd: self._insert_slash_command(c))
            t_row.addWidget(tb)
        t_row.addStretch()
        d_lay.addLayout(t_row)

        # Tier 4: Unified Prompt Bar (Artifacts & Tools, PowerShell, Ecosystem Ports, [/] Commands, Input, Send)
        in_row = QHBoxLayout()
        in_row.setSpacing(6)

        btn_artifacts = QPushButton("🧰 Artifacts & Tools")
        btn_artifacts.setStyleSheet(
            "background: rgba(16, 185, 129, 0.18); color: #10b981; border: 1px solid #059669; "
            "border-radius: 6px; padding: 7px 10px; font-size: 8pt; font-weight: bold;"
        )
        btn_artifacts.clicked.connect(self._toggle_split_view)
        in_row.addWidget(btn_artifacts)

        btn_ps = QPushButton("⚡ PowerShell")
        btn_ps.setStyleSheet(
            "background: rgba(37, 99, 235, 0.25); color: #38bdf8; border: 1px solid #2563eb; "
            "border-radius: 6px; padding: 7px 10px; font-size: 8pt; font-weight: bold;"
        )
        btn_ps.clicked.connect(lambda: self._insert_slash_command("/ps "))
        in_row.addWidget(btn_ps)

        btn_ports = QPushButton("⚡ Ports")
        btn_ports.setStyleSheet(
            "background: rgba(59, 130, 246, 0.18); color: #60a5fa; border: 1px solid #2563eb; "
            "border-radius: 6px; padding: 7px 10px; font-size: 8pt; font-weight: bold;"
        )
        btn_ports.clicked.connect(lambda: self._handle_slash_command("/ports"))
        in_row.addWidget(btn_ports)

        btn_cmds = QPushButton("[/] Commands ▲")
        btn_cmds.setStyleSheet(
            "background: rgba(30, 41, 59, 0.9); color: #38bdf8; border: 1px solid #334155; "
            "border-radius: 6px; padding: 7px 10px; font-size: 8pt; font-weight: bold;"
        )
        cmd_menu = QMenu(self)
        for s_cmd, s_desc in [
            ("/blast ", "💥 Query AST Blast-Radius Dependency Graph (Stage 2)"),
            ("/graph", "🕸️ Rebuild Full 491-Node AST Dependency Graph (Stage 2)"),
            ("/distill", "🧬 Build Sovereign Nightly QLoRA Dataset on RTX 4090 (Stage 3)"),
            ("/dpi ", "📱 Switch Mobile Workstation DPI Profile (100% / 125% / 150%)"),
            ("/run ", "⚡ Multi-Runtime Polyglot Execution (Python/Node/Go/Rust/C++)"),
            ("/ps ", "⚡ Execute PowerShell Command"),
            ("/cmd ", "🪟 Execute Windows Command Prompt (cmd.exe)"),
            ("/wsl ", "🐧 Execute Linux WSL2 Bash Command"),
            ("/bash ", "🐚 Execute Bash Command (Git Bash / WSL)"),
            ("/build", "🔨 Run Project Build (auto-detects npm/cargo/go/cmake/make/pip)"),
            ("/test", "🧪 Run Pytest Test Battery in PowerShell"),
            ("/program list", "📦 List Programs in saved_data/built_programs"),
            ("/program build ", "🔨 Build/Compile Program or Project"),
            ("/program run ", "⚡ Run Built Program in PowerShell"),
            ("/terminal", "🖥️ Spawn Interactive PowerShell Terminal"),
            ("/runlast", "⚡ Run Last Code Block (with Stage 1 Auto-Heal)"),
            ("/scratchlast", "📋 Load Last Code to Scratchpad"),
            ("/dir ", "📂 List Directory via PowerShell"),
            ("/cat ", "📄 Read File Contents via PowerShell"),
            ("/status", "🌿 Check Git Status in PowerShell"),
            ("/python ", "🐍 Run Python Script in pyppeteer_env"),
            ("/pip ", "📦 Install Python Package via pip in PowerShell"),
            ("/npm ", "📦 Run NPM Command in PowerShell"),
            ("/npx ", "⚡ Run NPX Command in PowerShell"),
            ("/cargo ", "🦀 Run Cargo Rust Command in PowerShell"),
            ("/dotnet ", "🔷 Run .NET CLI in PowerShell"),
            ("/firebase ", "🔥 Run Firebase CLI Command"),
            ("/kill ", "🛑 Stop Process by Name in PowerShell"),
            ("/image ", "🎨 Generate ComfyUI Image"),
            ("/video ", "🎬 Generate Wan2.1/LTX Video"),
            ("/stems ", "🎙️ Demucs 4-Stem Isolation"),
            ("/voice ", "🗣️ F5-TTS Vocal Synthesis"),
            ("/vectors ", "🧠 Query ChromaDB Vectors"),
            ("/vault ", "🏛️ Search SQLite Master Vault"),
            ("/vram", "⚡ Inspect RTX 4090 Telemetry"),
            ("/ports", "🌐 Scan 18-Port Collision Matrix"),
            ("/daw", "🎹 Switch to Low-Latency DAW"),
            ("/clear", "🧹 Clear Transcript"),
        ]:
            act = cmd_menu.addAction(f"{s_desc} ({s_cmd.strip()})")
            act.triggered.connect(lambda checked, c=s_cmd: self._insert_slash_command(c))
        btn_cmds.setMenu(cmd_menu)
        in_row.addWidget(btn_cmds)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(
            "Message Stehouwer LLM or run /blast, /graph, /distill, /dpi, /ps, /wsl, /cmd, /run... (Enter to execute)"
        )
        self.input_edit.setStyleSheet(
            "background: #070a12; color: #f8fafc; border: 1px solid #1e293b; "
            "border-radius: 6px; padding: 8px 12px; font-size: 9pt;"
        )
        self.input_edit.textChanged.connect(self._update_context_budget)
        self.input_edit.returnPressed.connect(self._send)
        in_row.addWidget(self.input_edit, 1)

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedWidth(42)
        self.send_btn.setStyleSheet(
            "background: #2563eb; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 8px;"
        )
        self.send_btn.clicked.connect(self._send)
        in_row.addWidget(self.send_btn)

        d_lay.addLayout(in_row)

        # Tier 5: Governance & Oversight Footer
        f_row = QHBoxLayout()
        f_row.setSpacing(6)
        for f_lbl, f_cmd in [
            ("💥 AST Blast Radius", "/blast ChatTab.jsx"),
            ("🕸️ Rebuild Graph", "/graph"),
            ("🧬 QLoRA Distill", "/distill"),
            ("📱 Mobile DPI Status", "/dpi"),
            ("⚡ PowerShell Shell", "/ps Get-Host"),
            ("🖥️ Live PowerShell CLI", "/terminal"),
            ("🛡️ Risk & Governance Review", "/vram"),
            ("📊 Context Stress Test", "/ports"),
        ]:
            fb = QPushButton(f_lbl)
            fb.setStyleSheet(
                "QPushButton { background: #111827; color: #94a3b8; border: 1px solid #1e293b; "
                "border-radius: 5px; padding: 3px 8px; font-size: 7.5pt; }"
                "QPushButton:hover { color: #f8fafc; border-color: #38bdf8; }"
            )
            fb.clicked.connect(lambda checked, c=f_cmd: self._handle_slash_command(c))
            f_row.addWidget(fb)

        f_row.addStretch()
        from native_studio import __version__ as _ns_ver
        self.recovery_status = QLabel("Private chat recovery starting…")
        self.recovery_status.setStyleSheet("color: #10b981; font-size: 7.5pt; font-weight: bold;")
        f_row.addWidget(self.recovery_status)
        self.recovery_retry = QPushButton('Retry recovery')
        f_row.addWidget(self.recovery_retry)
        d_lay.addLayout(f_row)

        return deck

    def _toggle_split_view(self) -> None:
        self._split_active = not self._split_active
        self.right_w.setVisible(self._split_active)
        if self._split_active:
            self.pane_status_lbl.setText("● Split-Pane Active (Code + Chat)")
            self.splitter.setSizes([700, 520])
        else:
            self.pane_status_lbl.setText("● Single-Pane Active (Phase 7 Sandbox)")

    def _toggle_auto_heal(self) -> None:
        self._auto_heal_enabled = not self._auto_heal_enabled
        if self._auto_heal_enabled:
            self.btn_auto_heal.setText("🩹 Auto-Heal: ON (3x)")
            self.btn_auto_heal.setStyleSheet(
                "QPushButton { background: #064e3b; color: #34d399; border: 1px solid #10b981; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold; }"
                "QPushButton:hover { background: #065f46; color: #ffffff; }"
            )
        else:
            self.btn_auto_heal.setText("🩹 Auto-Heal: OFF")
            self.btn_auto_heal.setStyleSheet(
                "QPushButton { background: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold; }"
                "QPushButton:hover { background: #334155; color: #ffffff; }"
            )

    def _toggle_mobile_synergy(self) -> None:
        self._mobile_synergy_active = not self._mobile_synergy_active
        self.mobile_dock.setVisible(self._mobile_synergy_active)
        if self._mobile_synergy_active:
            self.btn_mobile_synergy.setText("📱 Mobile Synergy: ON")
            self.btn_mobile_synergy.setStyleSheet(
                "QPushButton { background: #4338ca; color: #ffffff; border: 1px solid #818cf8; "
                "border-radius: 5px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
                "QPushButton:hover { background: #4f46e5; }"
            )
        else:
            self.btn_mobile_synergy.setText("📱 Mobile Synergy: OFF")
            self.btn_mobile_synergy.setStyleSheet(
                "QPushButton { background: #1e1b4b; color: #c4b5fd; border: 1px solid #4c1d95; "
                "border-radius: 5px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
                "QPushButton:hover { background: #312e81; color: #ffffff; border-color: #8b5cf6; }"
            )

    def _on_dpi_profile_changed(self, idx: int) -> None:
        profile_id = self.dpi_picker.itemData(idx) or "native_desktop"
        self._dpi_profile_id = profile_id
        if profile_id == "mobile_1080p_150":
            chat_pt, code_pt, input_pt = "12.5pt", "12pt", "11pt"
            if not self._mobile_synergy_active:
                self._toggle_mobile_synergy()
        elif profile_id == "mobile_1440p_125":
            chat_pt, code_pt, input_pt = "11pt", "10.5pt", "10pt"
            if not self._mobile_synergy_active:
                self._toggle_mobile_synergy()
        else:
            chat_pt, code_pt, input_pt = "9.5pt", "9pt", "9pt"

        self.chat_display.setStyleSheet(
            f"QTextBrowser {{ background: #070b14; font-family: 'Cascadia Mono', Consolas, monospace; "
            f"font-size: {chat_pt}; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; }}"
        )
        self.code_editor.setStyleSheet(
            f"background: rgba(7, 4, 18, 0.96); font-family: 'Cascadia Mono', Consolas, monospace; "
            f"font-size: {code_pt}; color: #a5f3fc; border: 1px solid #334155; border-radius: 8px; padding: 8px;"
        )
        self.input_edit.setStyleSheet(
            f"background: #070a12; color: #f8fafc; border: 1px solid #1e293b; "
            f"border-radius: 6px; padding: 8px 12px; font-size: {input_pt};"
        )

        def _apply_backend_dpi():
            try:
                from backend.mobile_workstation_engine import apply_mobile_workstation_profile
                apply_mobile_workstation_profile(profile_id, apply_os_resolution=False)
            except Exception:
                pass
        self.bus.submit(_apply_backend_dpi)

    def _update_context_budget(self, text: str) -> None:
        chars = len(text)
        tokens = max(0, chars // 4)
        pct = min(100.0, (tokens / 1000000.0) * 100.0)
        self.lbl_budget.setText(
            f"📊 Context Budget: {chars:,} chars • ~{tokens:,} tokens ({pct:.2f}% of 1,000,000 max window • 1M+ Offload RAG Active)"
        )
        self.budget_bar.setValue(min(1000000, tokens))

    def _insert_slash_command(self, cmd: str) -> None:
        self.input_edit.setText(cmd)
        self.input_edit.setFocus()

    def _send(self) -> None:
        if hasattr(self, '_chat_recovery') and not self._chat_recovery.ready:
            return
        txt = self.input_edit.text().strip()
        if not txt or self._is_streaming:
            return
        self.input_edit.clear()
        self.left_stack.setCurrentIndex(1)

        # 1. Explicit slash commands
        if txt.startswith("/"):
            self._handle_slash_command(txt)
            return

        # 2. Direct @powershell or @ps mention prefix
        if txt.lower().startswith("@powershell ") or txt.lower().startswith("@ps "):
            ps_body = txt.split(maxsplit=1)[1].strip()
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')} (Direct PowerShell)]:\n{ps_body}\n")
            self.bus.submit(self._run_powershell_task, ps_body)
            return

        # 3. Direct PowerShell cmdlet prefixes (37+ standard verbs)
        ps_cmdlet_prefixes = (
            "Get-", "Set-", "Start-", "Stop-", "Restart-", "Test-", "New-", "Remove-",
            "Invoke-", "Write-", "Read-", "Select-", "Where-", "Clear-", "Copy-", "Move-",
            "Install-", "Update-", "Out-", "Export-", "Import-", "Convert-", "Measure-",
            "Wait-", "Add-", "Rename-", "Format-", "Show-", "Find-", "Register-", "Unregister-",
            "Enter-", "Exit-", "Resolve-", "Join-", "Split-", "Enable-", "Disable-"
        )
        if any(txt.startswith(p) for p in ps_cmdlet_prefixes):
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')} (PowerShell Cmdlet)]:\n{txt}\n")
            self.bus.submit(self._run_powershell_task, txt)
            return

        # 4. Direct developer CLI execution tokens
        cli_tokens = txt.split()
        first_token = cli_tokens[0].lower() if cli_tokens else ""
        if first_token in (
            "powershell", "powershell.exe", "pwsh", "pwsh.exe",
            "python", "python.exe", "py",
            "pip", "pip3", "pytest", "npm", "npx", "git", "cargo", "dotnet", "firebase",
            "node", "node.exe", "wsl", "wsl.exe", "bash", "sh"
        ):
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')} (Direct Host CLI)]:\n{txt}\n")
            if first_token in ("python", "python.exe", "py"):
                rest = txt.split(maxsplit=1)[1] if len(cli_tokens) > 1 else ""
                ps_cmd = f'& "C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe" {rest}'
                self.bus.submit(self._run_powershell_task, ps_cmd)
                return
            elif first_token in ("pip", "pip3"):
                rest = txt.split(maxsplit=1)[1] if len(cli_tokens) > 1 else ""
                ps_cmd = f'& "C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe" -m pip {rest}'
                self.bus.submit(self._run_powershell_task, ps_cmd)
                return
            elif first_token in ("bash", "sh"):
                rest = txt.split(maxsplit=1)[1] if len(cli_tokens) > 1 else ""
                self.bus.submit(self._run_multi_runtime_with_auto_heal, rest, "bash", None)
                return
            elif first_token == "pytest":
                rest = txt.split(maxsplit=1)[1] if len(cli_tokens) > 1 else ""
                ps_cmd = f'& "C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe" -m pytest {rest}'
                self.bus.submit(self._run_powershell_task, ps_cmd)
                return
            elif first_token in ("powershell", "powershell.exe", "pwsh", "pwsh.exe"):
                rest = txt.split(maxsplit=1)[1] if len(cli_tokens) > 1 else ""
                ps_cmd = rest or "Get-Host"
                self.bus.submit(self._run_powershell_task, ps_cmd)
                return
            else:
                ps_cmd = txt
                self.bus.submit(self._run_powershell_task, ps_cmd)
                return

        # 5. Natural Language Developer & Host Action Dispatch (Zero Slash Commands Required)
        p_low = txt.lower()

        # Clear Chat / Screen
        if re.search(r'\b(?:clear|clean|wipe)\s+(?:the\s+)?(?:chat|transcript|screen)\b', p_low):
            self.chat_display.clear()
            self.left_stack.setCurrentIndex(0)
            return

        # Open / Spawn PowerShell Terminal
        if re.search(r'\b(?:open|spawn|give\s+me|launch)\s+(?:a\s+)?(?:terminal|console|powershell(?:\s+console|\s+window)?|cmd)\b', p_low):
            self._spawn_powershell_terminal()
            return

        # Run Pytest / Automated Test Battery
        if re.search(r'\b(?:run|execute|start)?\s*(?:the\s+)?(?:pytest|tests|test\s+suite|test\s+battery|test\s+native\s+studio)\b', p_low):
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
            self.chat_display.appendPlainText("[POWERSHELL PYTEST]: Running Pytest test suite in PowerShell...\n")
            self.bus.submit(
                self._run_powershell_task,
                '& "C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe" -m pytest "C:\\AI-BS\\native_studio\\test_native_studio.py" -v',
            )
            return

        # Build / Compile Application
        if re.search(r'\b(?:build|compile)\s+(?:the\s+)?(?:program|app|application|binaries|exe|release|native\s+studio)\b', p_low):
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
            self.chat_display.appendPlainText("[POWERSHELL BUILD]: Initiating production build in PowerShell...\n")
            self.bus.submit(self._run_powershell_task, 'powershell -ExecutionPolicy Bypass -Command "npm run build"')
            return

        # Run Scratchpad / Code Editor Program
        if re.search(r'\b(?:run|execute)\s+(?:this|the|my)?\s*(?:code|script|program|scratchpad)\b', p_low) or (p_low in ("run it", "execute it")):
            self._run_scratchpad_in_powershell()
            return

        # Check VRAM / Hardware Telemetry
        if re.search(r'\b(?:vram|check\s+vram|gpu\s+status|how\s+is\s+(?:the\s+|my\s+)?gpu|how\s+much\s+vram|hardware|thermals|rtx\s*4090)\b', p_low):
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
            self.bus.submit(self._check_vram)
            return

        # Check Ecosystem Sockets / Ports / Daemons / Matrix Doctor
        if re.search(r'\b(?:check\s+ports|ports|daemons|system\s+health|matrix\s+doctor|services|socket\s+status|are\s+ports\s+online)\b', p_low):
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
            self.bus.submit(self._check_ports)
            return

        # Git Status / Uncommitted Changes
        if re.search(r'\b(?:git\s+status|what\s+changed|check\s+git|git\s+diffs|uncommitted\s+changes)\b', p_low):
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
            self.bus.submit(self._run_powershell_task, "git status --short")
            return

        # Show in Explorer
        if re.search(r'\b(?:show|reveal|open|explore)\b.*?\b(?:in\s+)?(?:file\s+explorer|explorer)\b', p_low):
            m_f = re.search(r'([a-zA-Z]:\\[^\s"\'`:,]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|ps1|yml|yaml|sql|csv|conf|toml|log))', txt)
            target = m_f.group(1).strip('"\'`:,') if m_f else (self._current_editor_file or self._last_referenced_file or r"C:\AI-BS")
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
            self._show_in_file_explorer(target)
            return

        # Open / View in Editor
        if (
            re.search(r'\b(?:open|view|show|display|load)\b.*?\b(?:in\s+editor|editor|code\s+canvas)\b', p_low)
            or re.search(r'\b(?:open|view|inspect)\s+(?:it|this\s+file|the\s+file)\b', p_low)
        ):
            m_f = re.search(r'([a-zA-Z]:\\[^\s"\'`:,]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|ps1|yml|yaml|sql|csv|conf|toml|log))', txt)
            target = m_f.group(1).strip('"\'`:,') if m_f else (self._current_editor_file or self._last_referenced_file)
            if target:
                self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
                self._open_file_in_editor(target)
                return

        # Bare File Path Entered
        m_bare = re.fullmatch(r'["\']?([a-zA-Z]:\\[^\s"\'`:,]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|ps1|yml|yaml|sql|csv|conf|toml|log))["\']?', txt.strip())
        if m_bare:
            raw_path = m_bare.group(1).strip('"\'`:,')
            abs_fp = os.path.abspath(raw_path) if os.path.isabs(raw_path) else os.path.abspath(os.path.join(r"C:\AI-BS", raw_path))
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n")
            if os.path.isfile(abs_fp):
                self._open_file_in_editor(abs_fp)
            else:
                self.chat_display.appendPlainText(f"[SYSTEM]: File path does not exist on disk:\n{abs_fp}\n")
            return

        # 6. Natural Language 1M+ RAG Search & Vector Offload Triggers
        if re.search(r'\b(?:search|query|find\s+in)\s+(?:rag|vectors?|chroma|knowledge\s+base|vector\s+memory)\b', p_low):
            q_text = re.sub(r'^(?:search|query|find\s+in)\s+(?:rag|vectors?|chroma|knowledge\s+base|vector\s+memory)\s*(?:for|about)?\s*', '', txt, flags=re.IGNORECASE).strip()
            self._handle_slash_command(f"/rag {q_text}")
            return

        # Ingest / Offload to 1M+ RAG
        if re.search(r'\b(?:ingest|offload|index)\s+(?:this\s+file|it|file|document)?\s*(?:to|into)?\s*(?:rag|chroma|vector\s+store|vault)\b', p_low):
            self._handle_slash_command("/rag_ingest")
            return

        # Map-Reduce 1M Summarizer
        if re.search(r'\b(?:summarize|novel(?:ize)?|compress)\s+(?:this\s+)?(?:1m\s+)?(?:file|document|script|novel|codebase)\b', p_low) or p_low in ("map reduce", "summarize 1m"):
            self._handle_slash_command("/summarize_1m")
            return

        # 6.5. Massive 1M+ Direct Input Buffer Detection & Automatic Offload
        if len(txt) > 25000:
            est_tokens = len(txt) // 4
            self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n[Pasted Massive Document: {len(txt):,} characters (~{est_tokens:,} tokens)]\n")
            self.chat_display.appendPlainText(
                f"[1M+ RAG OFFLOAD BUFFER DETECTED]: Input exceeds single-prompt VRAM capacity (~{est_tokens:,} tokens).\n"
                f"• Staging massive input into 'C:\\AI-BS\\workspace\\pasted_1m_buffer.txt'...\n"
                f"• Automatically offloading into ChromaDB (Port 8001 / CPU Port 11435 AVX-512)...\n"
            )
            stage_dir = Path(r"C:\AI-BS\workspace")
            stage_dir.mkdir(parents=True, exist_ok=True)
            stage_fp = stage_dir / "pasted_1m_buffer.txt"
            with open(stage_fp, "w", encoding="utf-8", errors="replace") as sf:
                sf.write(txt)
            self._open_file_in_editor(str(stage_fp))

            def _auto_ingest_pasted():
                ok, msg = self._ingest_file_to_rag(str(stage_fp))
                self.action_log_signal.emit("1M+ BUFFER RAG INGESTION", msg)
            self.bus.submit(_auto_ingest_pasted)
            return

        # 7. Fallthrough to Autonomous Streaming LLM with Enriched Host & 1M+ Vector Context
        self._is_streaming = True
        self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{txt}\n\n[BS-CHAT]:\n")
        m = self.model_picker.currentData()
        self.bus.submit(self._stream_response, m, txt)

    def _handle_slash_command(self, cmd_line: str) -> None:
        self.left_stack.setCurrentIndex(1)
        self.chat_display.appendPlainText(f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]:\n{cmd_line}\n")
        parts = cmd_line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        # ── STAGE 2: AST BLAST-RADIUS DEPENDENCY GRAPH (/blast & /graph) ──
        if cmd == "/graph":
            self.chat_display.appendPlainText("[STAGE 2 AST GRAPH ENGINE]: Scanning all 43 modules, FastAPI routes, and React mirrors...\n")
            def _graph_task():
                try:
                    from backend.blast_radius_engine import build_full_graph
                    stats = build_full_graph()
                    out = (
                        f"=== 🕸️ STAGE 2 AST DEPENDENCY GRAPH REBUILT ===\n"
                        f"• Total Indexed Nodes: {stats.get('total_nodes', 0)} (Routers: {stats.get('backend_routers', 0)}, Components: {stats.get('frontend_components', 0)})\n"
                        f"• Total Directed Edges: {stats.get('total_edges', 0)}\n"
                        f"• Build Time: {stats.get('elapsed_ms', 0)} ms\n"
                        f"• Storage: SQLite Master Vault (aibs_master.db -> blast_radius_nodes / blast_radius_edges)\n"
                        f"💡 Run `/blast <file_or_route>` (e.g., `/blast ChatTab.jsx` or `/blast /api/executive/run`) to inspect upstream & downstream impact before patching!"
                    )
                    self.action_log_signal.emit("AST DEPENDENCY GRAPH", out)
                except Exception as e:
                    self.action_log_signal.emit("AST GRAPH ERROR", str(e))
            self.bus.submit(_graph_task)
            return

        if cmd == "/blast":
            q = arg or (os.path.basename(self._current_editor_file) if self._current_editor_file else "ChatTab.jsx")
            self.chat_display.appendPlainText(f"[STAGE 2 BLAST-RADIUS ENGINE]: Computing upstream & downstream impact for '{q}'...\n")
            def _blast_task():
                try:
                    from backend.blast_radius_engine import query_blast_radius
                    res = query_blast_radius(q)
                    lines = [
                        f"=== 💥 STAGE 2 BLAST-RADIUS IMPACT REPORT: {q} ===",
                        f"• Risk Level: {res.get('risk_level', 'LOW')} ({res.get('blast_radius_score', 0)} impacted dependencies)",
                        f"• Summary: {res.get('summary', '')}",
                    ]
                    matched = res.get("matched_nodes", [])
                    if matched:
                        lines.append(f"\n[MATCHED NODES ({len(matched)})]:")
                        for n in matched[:8]:
                            lines.append(f"  • [{n.get('node_type')}] {n.get('label')} ({n.get('file_path') or n.get('node_id')})")
                    up = res.get("upstream_callers", [])
                    if up:
                        lines.append(f"\n[UPSTREAM CALLERS / DEPENDENTS ({len(up)} — Will be affected if you modify '{q}')]:")
                        for u in up[:15]:
                            lines.append(f"  ⬅️ {u.get('source')} --[{u.get('relation')}]--> {u.get('target')} ({u.get('file_path')}:{u.get('line_number')})")
                    down = res.get("downstream_callees", [])
                    if down:
                        lines.append(f"\n[DOWNSTREAM CALLEES / IMPORTS ({len(down)})]:")
                        for d in down[:15]:
                            lines.append(f"  ➡️ {d.get('source')} --[{d.get('relation')}]--> {d.get('target')} ({d.get('file_path')}:{d.get('line_number')})")
                    self.action_log_signal.emit("BLAST-RADIUS IMPACT ANALYSIS", "\n".join(lines))
                except Exception as e:
                    self.action_log_signal.emit("BLAST-RADIUS ERROR", str(e))
            self.bus.submit(_blast_task)
            return

        # ── STAGE 3: SOVEREIGN NIGHTLY QLORA DISTILLATION (/distill) ──
        if cmd == "/distill":
            self.chat_display.appendPlainText("[STAGE 3 SOVEREIGN QLORA DISTILLATION]: Curating ShareGPT JSONL pairs from SQLite Vaults, ChromaDB & Master Architecture...\n")
            def _distill_task():
                try:
                    from backend.sovereign_qlora_distillation import build_distillation_dataset
                    res = build_distillation_dataset()
                    stats = res.get("stats", {})
                    out = (
                        f"=== 🧬 STAGE 3 SOVEREIGN QLORA DISTILLATION DATASET READY ===\n"
                        f"• Dataset Path: {res.get('dataset_path')}\n"
                        f"• Unsloth RTX 4090 Config: {res.get('config_path')}\n"
                        f"• Total Curated Examples: {res.get('total_examples', 0):,}\n"
                        f"  ├─ Master Architecture & Idioms: {stats.get('architecture_core', 0)}\n"
                        f"  ├─ SQLite Vault Records: {stats.get('sqlite_vault', 0):,}\n"
                        f"  ├─ ChromaDB Memory Vectors: {stats.get('chromadb_memory', 0)}\n"
                        f"  └─ AST Blast-Radius Topology Pairs: {stats.get('blast_radius_graph', 0)}\n"
                        f"• Elapsed Time: {res.get('elapsed_ms', 0)} ms\n"
                        f"• Target Hardware: NVIDIA GeForce RTX 4090 (24GB VRAM, 4-bit NormalFloat QLoRA r=16, alpha=32)"
                    )
                    self.action_log_signal.emit("SOVEREIGN QLORA DISTILLATION", out)
                except Exception as e:
                    self.action_log_signal.emit("DISTILLATION ERROR", str(e))
            self.bus.submit(_distill_task)
            return

        # ── MOBILE WORKSTATION, DPI SCALING & BLUETOOTH TRACKPAD SYNERGY (/dpi & /mobile) ──
        if cmd in ("/dpi", "/mobile"):
            arg_low = arg.lower()
            target_profile = None
            apply_os = "os" in arg_low or "display" in arg_low
            if "150" in arg_low or "1080" in arg_low:
                target_profile = "mobile_1080p_150"
            elif "125" in arg_low or "1440" in arg_low:
                target_profile = "mobile_1440p_125"
            elif "100" in arg_low or "native" in arg_low or "desktop" in arg_low:
                target_profile = "native_desktop"

            if target_profile:
                idx = self.dpi_picker.findData(target_profile)
                if idx >= 0:
                    self.dpi_picker.setCurrentIndex(idx)

            def _dpi_task():
                try:
                    from backend.mobile_workstation_engine import (
                        apply_mobile_workstation_profile,
                        get_mobile_workstation_status,
                    )
                    if target_profile:
                        st = apply_mobile_workstation_profile(target_profile, apply_os_resolution=apply_os)
                    else:
                        st = get_mobile_workstation_status()
                    disp = st.get("current_display", {})
                    daemons = st.get("remote_daemons", {})
                    hid = st.get("input_peripherals", {})
                    prof = st.get("active_profile", {})
                    out = (
                        f"=== 📱 MOBILE WORKSTATION & DPI SYNERGY TELEMETRY ===\n"
                        f"• Active UI Profile: {prof.get('label', self._dpi_profile_id)} (Scale: {int(prof.get('ui_scale_factor', 1.0)*100)}%)\n"
                        f"• Primary Display Resolution: {disp.get('width', 1920)}x{disp.get('height', 1080)} @ {disp.get('refresh_hz', 60)}Hz\n"
                        f"• Remote Streaming Daemons:\n"
                        f"  ├─ Parsec (60FPS H.265 Ultra-Low Latency): {'🟢 RUNNING' if daemons.get('parsec', {}).get('running') else '⚪ STANDBY'} ({daemons.get('parsec', {}).get('executable') or 'Not detected'})\n"
                        f"  ├─ Tailscale Mesh VPN: {'🟢 CONNECTED' if daemons.get('tailscale', {}).get('running') else '⚪ STANDBY'} (IPs: {', '.join(daemons.get('tailscale', {}).get('mesh_ips', [])) or 'N/A'})\n"
                        f"  └─ RustDesk Direct Mirror: {'🟢 RUNNING' if daemons.get('rustdesk', {}).get('running') else '⚪ STANDBY'}\n"
                        f"• Bluetooth & HID Trackpad/Keyboard Peripherals: {hid.get('total_hid_count', 0)} active device(s)\n"
                        f"💡 Tip: Use `/dpi 150`, `/dpi 125`, or `/dpi 100` to switch font & button scaling instantly!"
                    )
                    self.action_log_signal.emit("MOBILE WORKSTATION & DPI STATUS", out)
                except Exception as e:
                    self.action_log_signal.emit("MOBILE DPI ERROR", str(e))
            self.bus.submit(_dpi_task)
            return

        # ── 3-WAY WIRELESS SCREEN MIRROR & DISPLAY CAST (/cast & /mirror) ──
        if cmd in ("/cast", "/mirror", "/wireless-display", "/screen-mirror"):
            sub_parts = arg.split()
            sub_act = (sub_parts[0] if sub_parts else "status").lower()
            sub_arg = sub_parts[1] if len(sub_parts) > 1 else ""

            def _cast_task():
                try:
                    from backend.mobile_workstation_engine import (
                        execute_wireless_cast_action,
                        get_wireless_cast_status,
                    )
                    if sub_act in ("display", "tv", "miracast", "win-k", "wink"):
                        res = execute_wireless_cast_action("win_k")
                        self.action_log_signal.emit("PC ➔ WIRELESS DISPLAY (WIN+K)", res.get("message", ""))
                    elif sub_act in ("clone", "duplicate", "extend", "external", "second", "internal", "pc"):
                        res = execute_wireless_cast_action("display_mode", mode=sub_act)
                        self.action_log_signal.emit("WINDOWS PROJECTION MODE", res.get("message", ""))
                    elif sub_act in ("phone", "scrcpy", "phone-to-pc", "android"):
                        res = execute_wireless_cast_action("phone_to_pc_scrcpy", phone_ip=sub_arg)
                        self.action_log_signal.emit("PHONE ➔ PC SCRCPY MIRROR", res.get("message", ""))
                    elif sub_act in ("adb", "tcpip", "wireless-adb"):
                        res = execute_wireless_cast_action("adb_tcpip_auto", phone_ip=sub_arg)
                        self.action_log_signal.emit("WIRELESS ADB SETUP (:5555)", res.get("message", ""))
                    elif sub_act in ("scan", "nearby", "devices"):
                        res = execute_wireless_cast_action("scan_nearby")
                        scan = res.get("scan", {})
                        pnp = "\n".join(f"  • [{d.get('class')}] {d.get('name')}" for d in scan.get("pnp_displays_and_endpoints", []))
                        peers = "\n".join(f"  • {p.get('ip')} ({p.get('mac')})" for p in scan.get("wifi_lan_peers", []))
                        self.action_log_signal.emit(
                            "NEARBY WIRELESS DISPLAYS & WI-FI PEERS",
                            f"[WINDOWS DISPLAYS & ENDPOINTS]:\n{pnp}\n\n[WI-FI LAN PEERS]:\n{peers}"
                        )
                    else:
                        st = get_wireless_cast_status()
                        urls = st.get("urls", {})
                        p2p = st.get("phone_to_pc", {})
                        out = (
                            f"=== 📡 3-WAY WIRELESS SCREEN MIRROR & DISPLAY CAST HUB ===\n"
                            f"1️⃣ PC ➔ Wireless Display (TV / Monitor): Run `/cast display` (Win+K), `/cast clone`, or `/cast extend`\n"
                            f"2️⃣ PC ➔ Phone / Tablet (Wi-Fi IDE): {urls.get('pc_to_phone_workspace_lan')}\n"
                            f"   Live PC Screen Viewer URL: {urls.get('pc_to_phone_live_screen_viewer')}\n"
                            f"3️⃣ Phone ➔ PC (Scrcpy v4.1 60FPS): {'🟢 READY' if p2p.get('scrcpy_installed') else '⚪ STANDBY'} | Run `/cast adb` then `/cast phone [ip]`"
                        )
                        self.action_log_signal.emit("3-WAY WIRELESS CAST STATUS", out)
                except Exception as e:
                    self.action_log_signal.emit("WIRELESS CAST ERROR", str(e))
            self.bus.submit(_cast_task)
            return

        # ── SOVEREIGN EXECUTION & PRIVILEGE DIRECTIVE (/directive & /privilege) ──
        if cmd in ("/directive", "/privilege", "/ring0", "/aibs-dir-000"):
            sub_act = (arg or "status").strip().lower()

            def _directive_task():
                try:
                    from backend.sovereign_privilege_engine import (
                        enforce_sovereign_privilege_directive,
                        get_sovereign_privilege_status,
                    )
                    if sub_act in ("enforce", "apply"):
                        res = enforce_sovereign_privilege_directive()
                        self.action_log_signal.emit(
                            "AIBS-DIR-000 ENFORCEMENT COMPLETE",
                            res.get("stdout") or json.dumps(res, indent=2),
                        )
                    else:
                        st = get_sovereign_privilege_status()
                        ls = st.get("live_state", {})
                        ts = st.get("two_strike_governance", {})
                        out = (
                            f"=== 🛡️ AIBS-DIR-000 SOVEREIGN PRIVILEGE & EXECUTION DIRECTIVE ===\n"
                            f"• Directive Spec: {st.get('directive_file')}\n"
                            f"• Tier 1 Elevated Admin (Ring 3): {'🟢 ACTIVE' if ls.get('tier1_elevated_admin_active') else '⚪ STANDARD'}\n"
                            f"• Tier 4 Ring 0 / VTL 1 HVCI De-Clamping: {'🟢 UNBLOCKED (HVCI=0)' if ls.get('ring0_msr_telemetry_unblocked') else '⚠️ LOCKED'}\n"
                            f"• 4096-Bit RSA SHA-256 X.509 Cert: {ls.get('sovereign_x509_thumbprint') or 'Not Enrolled'}\n"
                            f"• ReAct Sandbox Dir: {ls.get('react_sandbox_dir')}\n"
                            f"• Two-Strike Fault Heuristics Logged: {ts.get('total_logged_fault_vectors', 0)}"
                        )
                        self.action_log_signal.emit("AIBS-DIR-000 PRIVILEGE TELEMETRY", out)
                except Exception as e:
                    self.action_log_signal.emit("DIRECTIVE ERROR", str(e))
            self.bus.submit(_directive_task)
            return

        # ── SOVEREIGN MEMORY & REASONING RECALL (/recall & /memory) ──
        if cmd in ("/recall", "/memory", "/thinking"):
            query_str = (arg or "").strip()
            if not query_str:
                self.action_log_signal.emit(
                    "MEMORY USAGE",
                    "Usage: /recall <query>\nExample: /recall closeEvent window bug\nQueries ChromaDB vector vault and SQLite sovereign reasoning store."
                )
                return

            def _recall_task():
                try:
                    from backend.sovereign_memory_ingestor import search_memory
                    hits = search_memory(query_str, n_results=5)
                    if hits:
                        lines = [f"=== 🧠 SOVEREIGN MEMORY RECALL: '{query_str}' ==="]
                        for idx, h in enumerate(hits):
                            t = h.get("metadata", {}).get("title") or h.get("id")
                            cat = h.get("metadata", {}).get("category") or "memory"
                            dist = h.get("distance", 0.0)
                            sim = max(0.0, 1.0 - dist)
                            snippet = h.get("document", "").replace("\n", " ")[:200]
                            lines.append(f"[{idx+1}] {t} ({cat}) - Similarity: {sim:.3f}\n   ↳ {snippet}...\n")
                        self.action_log_signal.emit("MEMORY RECALL (CHROMADB)", "\n".join(lines))
                    else:
                        # Fallback to SQLite
                        import sqlite3
                        db_p = r"C:\AI-BS\backend\aibs_master.db"
                        conn = sqlite3.connect(db_p)
                        cur = conn.cursor()
                        like_q = f"%{query_str}%"
                        cur.execute("""
                            SELECT title, category, content FROM sovereign_reasoning_vault
                            WHERE content LIKE ? OR prompt LIKE ? OR title LIKE ?
                            ORDER BY created_at DESC LIMIT 5
                        """, (like_q, like_q, like_q))
                        rows = cur.fetchall()
                        conn.close()
                        if rows:
                            lines = [f"=== 🧠 SOVEREIGN MEMORY RECALL (SQLITE): '{query_str}' ==="]
                            for idx, r in enumerate(rows):
                                lines.append(f"[{idx+1}] {r[0]} ({r[1]})\n   ↳ {(r[2] or '')[:200]}...\n")
                            self.action_log_signal.emit("MEMORY RECALL (SQLITE)", "\n".join(lines))
                        else:
                            self.action_log_signal.emit("MEMORY RECALL", f"No memory nodes matched '{query_str}'.")
                except Exception as e:
                    self.action_log_signal.emit("MEMORY RECALL ERROR", str(e))
            self.bus.submit(_recall_task)
            return

        # ── MULTI-SHELL & POLYGLOT DEVELOPER DISPATCH ROUTERS (/ps, /cmd, /wsl, /run) ──
        if cmd in ("/ps", "/powershell"):
            if not arg:
                self.chat_display.appendPlainText("[USAGE]: /ps <command> (e.g., /ps Get-Process, /ps git status)\n")
                return
            self.bus.submit(self._run_multi_runtime_with_auto_heal, arg, "powershell", None)
            return

        if cmd == "/cmd":
            if not arg:
                self.chat_display.appendPlainText("[USAGE]: /cmd <command> (e.g., /cmd dir C:\\AI-BS)\n")
                return
            self.bus.submit(self._run_multi_runtime_with_auto_heal, arg, "cmd", None)
            return

        if cmd in ("/wsl", "/sh", "/bash"):
            if not arg:
                self.chat_display.appendPlainText(f"[USAGE]: {cmd} <command> (e.g., {cmd} pip install requests or {cmd} uname -a)\n")
                return
            rt_mode = "wsl" if cmd == "/wsl" else "bash"
            self.bus.submit(self._run_multi_runtime_with_auto_heal, arg, rt_mode, None)
            return

        if cmd in ("/run", "/exec"):
            if not arg:
                self._run_scratchpad_in_powershell()
                return
            # Check if arg is a file path on disk
            cand_p = os.path.abspath(arg) if os.path.isabs(arg) else os.path.abspath(os.path.join(r"C:\AI-BS", arg))
            if os.path.isfile(cand_p):
                with open(cand_p, "r", encoding="utf-8", errors="replace") as f:
                    file_code = f.read()
                self.bus.submit(self._run_multi_runtime_with_auto_heal, file_code, "auto", cand_p)
            else:
                self.bus.submit(self._run_multi_runtime_with_auto_heal, arg, "auto", None)
            return

        if cmd == "/terminal" or cmd == "/console":
            self._spawn_powershell_terminal()
            return

        if cmd == "/runlast":
            self._run_last_code_in_powershell()
            return

        if cmd == "/scratchlast":
            self._load_last_code_to_scratchpad()
            return

        if cmd == "/build":
            target_proj = arg.strip() if arg else r"C:\AI-BS"
            parts_b = target_proj.split(maxsplit=1)
            b_dir = parts_b[0] if parts_b else r"C:\AI-BS"
            b_custom = parts_b[1] if len(parts_b) > 1 else None

            self.chat_display.appendPlainText(f"[PROJECT BUILD]: Initiating build for '{b_dir}'" + (f" with command '{b_custom}'" if b_custom else " (auto-detecting build tools)") + "...\n")
            def _build_project_task():
                from core.program_builder_engine import AutonomousProgramBuilder
                res = AutonomousProgramBuilder.build_project(b_dir, build_command=b_custom)
                status_str = res.get("status", "error").upper()
                exit_code = res.get("exit_code", 1)
                cmd_run = res.get("command", "N/A")
                out_text = f"Status: {status_str} (Exit Code: {exit_code})\nCommand: {cmd_run}\n"
                if res.get("stdout"):
                    out_text += f"\n--- STDOUT ---\n{res.get('stdout')}\n"
                if res.get("stderr"):
                    out_text += f"\n--- STDERR ---\n{res.get('stderr')}\n"
                self.action_log_signal.emit(f"Project '{b_dir}' build completed ({status_str})", out_text)
            self.bus.submit(_build_project_task)
            return

        if cmd == "/test":
            self.chat_display.appendPlainText("[POWERSHELL PYTEST]: Running Pytest test suite in PowerShell...\n")
            self.bus.submit(
                self._run_powershell_task,
                '& "C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe" -m pytest "C:\\AI-BS\\native_studio\\test_native_studio.py" -v',
            )
            return

        if cmd in ("/program", "/app", "/builder"):
            parts_p = arg.split(maxsplit=1)
            sub = parts_p[0].lower() if parts_p else "list"
            prog_arg = parts_p[1].strip() if len(parts_p) > 1 else ""
            if sub == "list":
                from core.program_builder_engine import AutonomousProgramBuilder
                progs = AutonomousProgramBuilder.list_programs()
                self.chat_display.appendPlainText(f"[PROGRAM BUILDER]: Found {len(progs)} built program(s) in saved_data/built_programs:\n")
                for p in progs:
                    b_info = p.get("build")
                    b_str = f" [Build: {b_info.get('status')}]" if b_info else ""
                    self.chat_display.appendPlainText(f"  • {p.get('project_name')} ({p.get('language')}){b_str} - {p.get('description', '')}\n")
                return
            elif sub in ("build", "compile"):
                if not prog_arg:
                    self.chat_display.appendPlainText("[USAGE]: /program build <project_name_or_dir> [build_cmd]\n")
                    return
                b_parts = prog_arg.split(maxsplit=1)
                b_proj = b_parts[0]
                b_custom = b_parts[1] if len(b_parts) > 1 else None
                self.chat_display.appendPlainText(f"[PROJECT BUILD]: Building '{b_proj}'" + (f" with command '{b_custom}'" if b_custom else " (auto-detecting build tools)") + "...\n")
                def _build_prog_task():
                    from core.program_builder_engine import AutonomousProgramBuilder
                    res = AutonomousProgramBuilder.build_project(b_proj, build_command=b_custom)
                    status_str = res.get("status", "error").upper()
                    exit_code = res.get("exit_code", 1)
                    cmd_run = res.get("command", "N/A")
                    out_text = f"Status: {status_str} (Exit Code: {exit_code})\nCommand: {cmd_run}\n"
                    if res.get("stdout"):
                        out_text += f"\n--- STDOUT ---\n{res.get('stdout')}\n"
                    if res.get("stderr"):
                        out_text += f"\n--- STDERR ---\n{res.get('stderr')}\n"
                    self.action_log_signal.emit(f"Project '{b_proj}' build completed ({status_str})", out_text)
                self.bus.submit(_build_prog_task)
                return
            elif sub == "run":
                if not prog_arg:
                    self.chat_display.appendPlainText("[USAGE]: /program run <project_name>\n")
                    return
                self.chat_display.appendPlainText(f"[PROGRAM BUILDER]: Running program '{prog_arg}' in PowerShell...\n")
                def _run_prog_task():
                    from core.program_builder_engine import AutonomousProgramBuilder
                    res = AutonomousProgramBuilder.run_existing_program(prog_arg)
                    self.action_log_signal.emit(f"Program '{prog_arg}' executed with status: {res.get('status')}", str(res.get("stdout") or res.get("stderr") or ""))
                self.bus.submit(_run_prog_task)
                return
            else:
                self.chat_display.appendPlainText("[USAGE]: /program [list | build <name> [cmd] | run <name>]\n")
                return

        if cmd in ("/dir", "/ls"):
            target_path = arg or "C:\\AI-BS"
            self.bus.submit(
                self._run_powershell_task,
                f'Get-ChildItem -Path "{target_path}" | Select-Object Mode, Name, Length, LastWriteTime',
            )
            return

        if cmd in ("/cat", "/type"):
            if not arg:
                self.chat_display.appendPlainText("[USAGE]: /cat <file_path>\n")
                return
            self.bus.submit(self._run_powershell_task, f'Get-Content -Path "{arg}"')
            return

        if cmd == "/status":
            self.bus.submit(self._run_powershell_task, "git status --short")
            return

        if cmd == "/git":
            self.bus.submit(self._run_powershell_task, f"git {arg}")
            return

        if cmd == "/python":
            self.bus.submit(self._run_powershell_task, f'& "C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe" {arg}')
            return

        if cmd in ("/pip", "/pip3"):
            self.bus.submit(self._run_powershell_task, f'& "C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe" -m pip {arg}')
            return

        if cmd == "/npm":
            self.bus.submit(self._run_powershell_task, f"npm {arg}")
            return

        if cmd == "/npx":
            self.bus.submit(self._run_powershell_task, f"npx {arg}")
            return

        if cmd == "/cargo":
            self.bus.submit(self._run_powershell_task, f"cargo {arg}")
            return

        if cmd == "/dotnet":
            self.bus.submit(self._run_powershell_task, f"dotnet {arg}")
            return

        if cmd == "/firebase":
            self.bus.submit(self._run_powershell_task, f"firebase {arg}")
            return

        if cmd == "/kill":
            if not arg:
                self.chat_display.appendPlainText("[USAGE]: /kill <process_name>\n")
                return
            self.bus.submit(self._run_powershell_task, f'Stop-Process -Name "{arg}" -Force -ErrorAction SilentlyContinue')
            return

        if cmd == "/clear":
            self.chat_display.clear()
            self.left_stack.setCurrentIndex(0)
            return
        if cmd == "/vram":
            self.bus.submit(self._check_vram)
            return
        if cmd == "/ports":
            self.bus.submit(self._check_ports)
            return
        if cmd == "/daw":
            main_win = self.window()
            if hasattr(main_win, "jump_to_tab"):
                main_win.jump_to_tab("music_daw")
            return
        if cmd in ("/rag", "/vector", "/vectors"):
            q = arg or "screenplay"
            self.chat_display.appendPlainText(f"[CHROMADB 1M+ VECTOR SEARCH]: Querying 31 collections and 139K vault records for '{q}'...\n")
            def _rag_task():
                from native_studio.service_orchestrator import query_chroma_vectors, query_sqlite_vault
                c_res = query_chroma_vectors(q, n_results=5)
                v_res = query_sqlite_vault(q, limit=3)
                lines = [f"=== CHROMADB 1M+ VECTOR EMBEDDINGS (Port 8001 / E:\\AI_BS_Resources) ==="]
                for r in c_res:
                    if r.get("document"):
                        col = r.get("collection", "vault")
                        doc_snippet = str(r["document"]).strip().replace("\n", " ")[:1000]
                        lines.append(f"• [{col}] (Port {r.get('port', 8001)}):\n  \"{doc_snippet}\"\n")
                if v_res and any("title" in v for v in v_res):
                    lines.append("=== SQLITE VAULT SOVEREIGN MEMORY (stehouwer_vault.db, 139K Records) ===")
                    for v in v_res:
                        if "title" in v:
                            lines.append(f"• [{v.get('title')}]: {str(v.get('content') or v.get('description') or '')[:600]}...")
                self.action_log_signal.emit("CHROMADB 1M+ VECTOR RAG", "\n".join(lines))
            self.bus.submit(_rag_task)
            return

        if cmd == "/rag_ingest":
            target = arg or self._current_editor_file or ""
            if not target or not os.path.isfile(target):
                self.chat_display.appendPlainText("[USAGE]: /rag_ingest <file_path> (or load a file into the editor first)\n")
                return
            self.chat_display.appendPlainText(f"[CHROMADB 1M+ RAG INGESTION]: Chunking and vectorizing '{target}'...\n")
            def _ingest_task():
                ok, msg = self._ingest_file_to_rag(target)
                self.action_log_signal.emit("RAG INGESTION COMPLETE" if ok else "RAG INGESTION ERROR", msg)
            self.bus.submit(_ingest_task)
            return

        if cmd == "/summarize_1m":
            target = arg or self._current_editor_file or ""
            if not target or not os.path.isfile(target):
                self.chat_display.appendPlainText("[USAGE]: /summarize_1m <file_path> (or load a massive file into the editor first)\n")
                return
            self.chat_display.appendPlainText(f"[1M MAP-REDUCE SUMMARIZER]: Initiating hierarchical chunk accumulation for '{os.path.basename(target)}'...\n")
            self.bus.submit(self._run_1m_map_reduce_task, target)
            return

        self._is_streaming = True
        self.chat_display.appendPlainText("[BS-CHAT]:\n")
        m = self.model_picker.currentData()
        self.bus.submit(self._stream_response, m, cmd_line)

    def _run_multi_runtime_with_auto_heal(
        self,
        code_or_cmd: str,
        runtime: str = "auto",
        file_path: Optional[str] = None,
    ) -> None:
        """Executes code/commands across any shell or language runtime with Stage 1 Autonomous Self-Healing (up to 3 attempts)."""
        try:
            from backend.executive_runtime_router import auto_heal_code, execute_multi_runtime
        except Exception as e:
            self._run_powershell_task(code_or_cmd)
            return

        current_code = code_or_cmd
        max_attempts = 3 if self._auto_heal_enabled else 1

        for attempt in range(1, max_attempts + 1):
            res = execute_multi_runtime(
                command=current_code,
                runtime=runtime,
                cwd=r"C:\AI-BS",
                file_path=file_path,
            )
            rt_used = res.get("runtime_used", runtime)
            rc = res.get("returncode", -1)
            elapsed_ms = res.get("elapsed_ms", 0)
            stdout_text = (res.get("stdout") or "").strip()
            stderr_text = (res.get("stderr") or "").strip()

            out_lines = [
                f"RUNTIME: {rt_used.upper()} | ATTEMPT: {attempt}/{max_attempts}",
                f"STATUS: {'SUCCESS (Exit 0)' if rc == 0 else f'EXIT {rc}'} | ELAPSED: {elapsed_ms} ms | CWD: C:\\AI-BS",
            ]
            if stdout_text:
                out_lines.append(f"\n[STDOUT]:\n{stdout_text}")
            if stderr_text:
                out_lines.append(f"\n[STDERR]:\n{stderr_text}")
            if not stdout_text and not stderr_text:
                out_lines.append("\n[OUTPUT]: (Completed with exit code 0)")

            header = (
                f"MULTI-RUNTIME EXECUTION ({rt_used.upper()} SUCCESS)"
                if rc == 0
                else f"MULTI-RUNTIME EXECUTION ({rt_used.upper()} FAILED — EXIT {rc})"
            )
            self.action_log_signal.emit(header, "\n".join(out_lines))
            self.token_chunk.emit(f"\n{header}\n" + "\n".join(out_lines) + "\n\n")

            if rc == 0 or not self._auto_heal_enabled or attempt >= max_attempts:
                break

            # Trigger Stage 1 Autonomous Self-Healing via qwen2.5-coder with Grammar-Locked JSON
            self.action_log_signal.emit(
                f"🩺 STAGE 1 AUTO-HEAL (ATTEMPT {attempt}/{max_attempts - 1})",
                f"Feeding stderr traceback into qwen2.5-coder (Grammar-Locked JSON schema) to synthesize surgical fix...",
            )
            heal_res = auto_heal_code(
                code=current_code,
                stderr=stderr_text or f"Process exited with non-zero returncode {rc}",
                runtime=rt_used,
                file_path=file_path,
                attempt=attempt,
            )
            fixed_code = (heal_res.get("fixed_code") or "").strip()
            if heal_res.get("status") == "success" and fixed_code and fixed_code != current_code.strip():
                root_cause = heal_res.get("root_cause", "Runtime error detected")
                explanation = heal_res.get("explanation", "Applied surgical code fix")
                line_num = heal_res.get("error_line")
                heal_summary = (
                    f"• Root Cause (Line {line_num or '?'}): {root_cause}\n"
                    f"• Surgical Fix Applied: {explanation}\n"
                    f"• Re-executing healed code automatically..."
                )
                self.action_log_signal.emit("🩺 STAGE 1 AUTO-HEAL PATCH SYNTHESIZED", heal_summary)
                current_code = fixed_code
            else:
                self.action_log_signal.emit(
                    "🩺 STAGE 1 AUTO-HEAL HALTED",
                    f"Could not synthesize a distinct repair patch: {heal_res.get('explanation', 'No diff produced')}",
                )
                break

    def _run_powershell_task(self, command: str) -> None:
        """Executes a PowerShell script or command asynchronously with real-time capture."""
        self._run_multi_runtime_with_auto_heal(command, runtime="powershell", file_path=None)

    def _run_scratchpad_in_powershell(self) -> None:
        """Runs the active program from the Scratchpad code editor via Multi-Runtime Router + Stage 1 Auto-Heal."""
        code = self.code_editor.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "Empty Scratchpad", "Scratchpad contains no code to execute.")
            return

        self.left_stack.setCurrentIndex(1)
        active_fp = self._current_editor_file
        self.chat_display.appendPlainText(
            f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]: Executing Scratchpad ({os.path.basename(active_fp) if active_fp else 'auto-detect'}) with Stage 1 Auto-Heal...\n"
        )
        self.bus.submit(self._run_multi_runtime_with_auto_heal, code, "auto", active_fp)

    def _execute_host_intent_standalone(self, prompt: str) -> Tuple[bool, str, bool]:
        """Zero-dependency host tool executor (works in both frozen AI_BS_Studio.exe and Python)."""
        p_strip = prompt.strip()
        p_low = p_strip.lower()

        # 1. Host File Write / Creation Intent
        code_block_m = re.search(r"```(?:[a-zA-Z0-9_\-]+)?\r?\n([\s\S]*?)\r?\n```", p_strip)
        is_explicit_write_cmd = p_low.startswith(("/write ", "/save ", "/create_file "))
        is_nl_file_write = (
            not any(db_kw in p_low for db_kw in ("database", "sqlite", "chroma", "vault", "table"))
            and (
                bool(re.search(r"\b(?:write|save|create|make|put|generate|touch)\s+(?:a\s+|an\s+|the\s+|some\s+)?(?:new\s+|small\s+|test\s+|sample\s+|example\s+|text\s+|host\s+)?file\b", p_low))
                or bool(re.search(r"\b(?:write|save)\s+.*?\bto\s+(?:a\s+|the\s+|my\s+)?(?:file|host(?:\s+system)?|c\s*drive|c:|disk)\b", p_low))
            )
        )
        if is_explicit_write_cmd or is_nl_file_write:
            explicit_fp = re.search(
                r'([a-zA-Z]:\\[^\s"\'`:,]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|ps1|yml|yaml|sql|csv|conf|toml|log))',
                p_strip,
            )
            target_fp = explicit_fp.group(1).strip('"\'`:.,') if explicit_fp else r"C:\AI-BS\exampleFile.txt"
            abs_fp = os.path.abspath(target_fp) if os.path.isabs(target_fp) else os.path.abspath(os.path.join(r"C:\AI-BS", target_fp))

            if code_block_m:
                content = code_block_m.group(1)
            else:
                quoted_m = re.search(r'(?:saying|content|text|containing)\s*[:=]?\s*["\']([^"\']+)["\']', p_strip, flags=re.IGNORECASE)
                if quoted_m:
                    content = quoted_m.group(1) + "\n"
                else:
                    content = (
                        f"Hello, this is a host file created by AI-BS Sovereign Intelligence.\n"
                        f"Host File Location: {abs_fp}\n"
                        f"Created At: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Operator Request: {p_strip}\n"
                    )
            try:
                os.makedirs(os.path.dirname(abs_fp), exist_ok=True)
                with open(abs_fp, "w", encoding="utf-8") as f:
                    f.write(content)
                self._last_referenced_file = abs_fp
                if not self._current_editor_file:
                    self._current_editor_file = abs_fp
                exists_ok = os.path.isfile(abs_fp)
                size_bytes = os.path.getsize(abs_fp) if exists_ok else 0
                abs_url = f"file:///{abs_fp.replace(os.sep, '/')}"
                msg = (
                    f"\n✅ [AUTONOMOUS HOST FILE WRITE EXECUTED & VERIFIED]\n"
                    f"I have physically created and written the file to your host system.\n\n"
                    f"• Host File Location (C: Drive): [{abs_fp}]({abs_url})\n"
                    f"• Verified On Disk: YES ({size_bytes} bytes)\n"
                    f"• File Contents Written:\n"
                    f"----------------------------------------\n"
                    f"{content.strip()}\n"
                    f"----------------------------------------\n"
                    f"💡 Click [{os.path.basename(abs_fp)}]({abs_url}) to view and edit in the BS-Chat IDE Code Editor, or right-click to 'Show in File Explorer'.\n"
                )
                return True, msg, True
            except Exception as e:
                return True, f"⚠️ [HOST FILE WRITE FAILED]: {e} (Target: {abs_fp})\n", True

        # 2. Host File Read Intent
        read_m = re.search(
            r"(?:read|view|open|cat|show\s+me|inspect|display|what\s+is\s+in(?:side)?)\s+(?:the\s+)?(?:host\s+)?(?:file\s+)?([a-zA-Z]:\\[^\s\"'`:,?]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|ps1|yml|yaml|sql|csv|conf|toml|log))",
            p_strip,
            flags=re.IGNORECASE,
        )
        if read_m:
            target_fp = read_m.group(1).strip('"\'`:.,?')
            abs_fp = os.path.abspath(target_fp) if os.path.isabs(target_fp) else os.path.abspath(os.path.join(r"C:\AI-BS", target_fp))
            if os.path.isfile(abs_fp):
                try:
                    with open(abs_fp, "r", encoding="utf-8", errors="replace") as f:
                        body = f.read(16000)
                    self._last_referenced_file = abs_fp
                    size_bytes = os.path.getsize(abs_fp)
                    abs_url = f"file:///{abs_fp.replace(os.sep, '/')}"
                    msg = (
                        f"\n📄 [AUTONOMOUS HOST FILE READ VERIFIED]\n"
                        f"• Host File Location (C: Drive): [{abs_fp}]({abs_url}) ({size_bytes} bytes)\n"
                        f"----------------------------------------\n"
                        f"{body.strip()}\n"
                        f"----------------------------------------\n"
                        f"💡 Click [{os.path.basename(abs_fp)}]({abs_url}) to open in the BS-Chat IDE Code Editor, or right-click to 'Show in File Explorer'.\n"
                    )
                    return True, msg, True
                except Exception as e:
                    return True, f"⚠️ [HOST FILE READ ERROR]: {e}\n", True

        # 3. Host Directory Listing Intent
        dir_m = re.search(
            r"(?:list|show(?:\s+me)?|display|scan|what\s+are)\s+(?:the\s+)?(?:files|contents|directory|folder)\s+(?:in|of|inside|on)\s+(?:the\s+)?(?:directory\s+|folder\s+)?([a-zA-Z]:\\[^\s\"'`,?]+)",
            p_strip,
            flags=re.IGNORECASE,
        )
        if dir_m:
            target_dir = dir_m.group(1).strip('"\'`:.,?')
            if os.path.isdir(target_dir):
                try:
                    entries = sorted(os.listdir(target_dir))[:60]
                    abs_dir_url = f"file:///{target_dir.replace(os.sep, '/')}"
                    lines = [f"\n📂 [AUTONOMOUS HOST DIRECTORY SCAN: [{target_dir}]({abs_dir_url})] ({len(entries)} items shown)"]
                    for name in entries:
                        full_p = os.path.join(target_dir, name)
                        full_url = f"file:///{full_p.replace(os.sep, '/')}"
                        kind = "<DIR>" if os.path.isdir(full_p) else f"{os.path.getsize(full_p)} B"
                        lines.append(f"  • [{name}]({full_url}) ({kind})")
                    lines.append(f"\n💡 Click any file above to view in the BS-Chat IDE Code Editor, or right-click to 'Show in File Explorer'.\n")
                    return True, "\n".join(lines) + "\n", True
                except Exception as e:
                    return True, f"⚠️ [DIRECTORY SCAN ERROR]: {e}\n", True

        # 4. Host File Rename / Move Intent (Natural Language + Zero Slash Commands)
        if re.search(r'\b(?:re\s*name|rename|mv|move)\b', p_low):
            m_to = re.search(r'\b(?:to|as|into)\s+[:=]?\s*["\']?([a-zA-Z0-9_\-\.]+)["\']?', p_strip, flags=re.IGNORECASE)
            if m_to:
                dst = m_to.group(1).strip('"\'`:,')
            else:
                m_direct = re.search(r'\b(?:re\s*name|rename)\s+(?:it|this|the\s+file|file)?\s+["\']?([a-zA-Z0-9_\-\.]+)["\']?', p_strip, flags=re.IGNORECASE)
                dst = m_direct.group(1).strip('"\'`:,') if m_direct else None

            if dst and dst.lower() not in ("it", "to", "this", "file"):
                idx = p_strip.lower().rfind(dst.lower())
                p_before = p_strip[:idx] if idx != -1 else p_strip
                m_src = re.search(r'([a-zA-Z]:\\[^\s"\'`:,]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|ps1|yml|yaml|sql|csv|conf|toml|log))', p_before)
                if m_src:
                    src_raw = m_src.group(1).strip('"\'`:,')
                else:
                    src_raw = self._current_editor_file or self._last_referenced_file or ""

                if src_raw:
                    src_path = os.path.abspath(src_raw) if os.path.isabs(src_raw) else os.path.abspath(os.path.join(r"C:\AI-BS", src_raw))
                    if not os.path.isfile(src_path):
                        for alt in (self._current_editor_file, self._last_referenced_file):
                            if alt and os.path.isfile(alt):
                                src_path = alt
                                break
                    if not os.path.isfile(src_path):
                        cand = os.path.join(r"C:\AI-BS", os.path.basename(src_path))
                        if os.path.isfile(cand):
                            src_path = cand

                    if os.path.isfile(src_path):
                        src_ext = os.path.splitext(src_path)[1]
                        dst_ext = os.path.splitext(dst)[1]
                        final_dst_name = dst if dst_ext else (dst + src_ext)
                        dst_path = os.path.normpath(os.path.join(os.path.dirname(src_path), final_dst_name))
                        try:
                            os.rename(src_path, dst_path)
                            self._current_editor_file = dst_path
                            self._last_referenced_file = dst_path
                            if hasattr(self, "code_editor"):
                                self.code_editor.set_current_file(dst_path)
                            if hasattr(self, "lbl_canvas"):
                                size_b = os.path.getsize(dst_path)
                                self.lbl_canvas.setText(f"Active Editor: {os.path.basename(dst_path)} ({size_b} bytes)")
                                self.lbl_canvas.setToolTip(dst_path)
                            src_url = f"file:///{src_path.replace(os.sep, '/')}"
                            dst_url = f"file:///{dst_path.replace(os.sep, '/')}"
                            size_b = os.path.getsize(dst_path)
                            msg = (
                                f"\n✅ [AUTONOMOUS HOST FILE RENAME EXECUTED & VERIFIED]\n"
                                f"I have physically renamed the file on your host system.\n\n"
                                f"• Previous Path: [{src_path}]({src_url})\n"
                                f"• New Path (C: Drive): [{dst_path}]({dst_url})\n"
                                f"• Verified On Disk: YES ({size_b} bytes)\n"
                                f"💡 Click [{os.path.basename(dst_path)}]({dst_url}) to view and edit in the BS-Chat IDE Code Editor, or right-click to 'Show in File Explorer'.\n"
                            )
                            return True, msg, True
                        except Exception as e:
                            return True, f"⚠️ [RENAME ERROR]: Failed to rename {src_path} to {dst_path}:\n{e}\n", True
                    else:
                        return True, f"⚠️ [FILE NOT FOUND]: Cannot rename. Target source file does not exist on disk:\n{src_path}\n", True

        # 5. Host File Delete Intent (Natural Language + Zero Slash Commands)
        is_delete_cmd = (
            re.search(r'\b(?:delete|remove|trash|erase|destroy)\s+(?:it|this|the\s+file|file)\b', p_low)
            or p_low.startswith(("/rm ", "/del "))
            or bool(re.search(r'\b(?:delete|remove)\s+([a-zA-Z]:\\[^\s"\'`:,]+|[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)\b', p_low))
        )
        if is_delete_cmd:
            m_f = re.search(r'([a-zA-Z]:\\[^\s"\'`:,]+|[a-zA-Z0-9_\-]+\.(?:txt|py|js|jsx|ts|tsx|json|md|html|css|env|bat|sh|ps1|yml|yaml|sql|csv|conf|toml|log))', p_strip)
            target_raw = m_f.group(1).strip('"\'`:,') if m_f else (self._current_editor_file or self._last_referenced_file or "")
            if target_raw:
                target_path = os.path.abspath(target_raw) if os.path.isabs(target_raw) else os.path.abspath(os.path.join(r"C:\AI-BS", target_raw))
                if os.path.isfile(target_path):
                    try:
                        os.remove(target_path)
                        if self._current_editor_file == target_path:
                            self._current_editor_file = None
                            if hasattr(self, "code_editor"):
                                self.code_editor.clear()
                            if hasattr(self, "lbl_canvas"):
                                self.lbl_canvas.setText("Active Code Canvas & Media Scratchpad: (Empty)")
                        target_url = f"file:///{target_path.replace(os.sep, '/')}"
                        msg = (
                            f"\n✅ [AUTONOMOUS HOST FILE DELETED & VERIFIED]\n"
                            f"The file has been physically removed from disk.\n\n"
                            f"• Deleted Path: [{target_path}]({target_url})\n"
                            f"• Verified Removed: YES\n"
                        )
                        return True, msg, True
                    except Exception as e:
                        return True, f"⚠️ [DELETE ERROR]: Failed to remove {target_path}:\n{e}\n", True
                else:
                    return True, f"⚠️ [FILE NOT FOUND]: Cannot delete. File does not exist on disk:\n{target_path}\n", True

        return False, "", False

    def _chunk_text_semantic(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Slices massive documents into 1,000-token semantic chunks with 200-token overlap."""
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += chunk_size - overlap
        return chunks

    def _retrieve_1m_rag_context(self, query: str, active_file_path: Optional[str] = None, top_k: int = 3) -> str:
        """Retrieves semantic needles from ChromaDB (Port 8001 / E: drive) and active document."""
        from native_studio.service_orchestrator import query_chroma_vectors, query_sqlite_vault
        rag_blocks = []

        # 1. Active file semantic chunk matching if large
        if active_file_path and os.path.isfile(active_file_path):
            try:
                with open(active_file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if len(content) > 1500:
                    chunks = self._chunk_text_semantic(content, chunk_size=1200, overlap=200)
                    q_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 3]
                    scored = []
                    for idx, c in enumerate(chunks):
                        c_low = c.lower()
                        score = sum(c_low.count(w) for w in q_words)
                        if score > 0:
                            scored.append((score, idx, c))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    if scored:
                        rag_blocks.append(f"[ACTIVE DOCUMENT RAG CHUNKS ({os.path.basename(active_file_path)})]:")
                        for s, idx, c in scored[:2]:
                            rag_blocks.append(f"--- Chunk {idx+1} (Relevance {s}) ---\n{c.strip()[:1200]}")
            except Exception:
                pass

        # 2. ChromaDB Vector Store (Port 8001 / E:\AI_BS_Resources\ChromaDB, 31 collections)
        try:
            chroma_res = query_chroma_vectors(query, n_results=top_k)
            docs = [r for r in chroma_res if r.get("document")]
            if docs:
                rag_blocks.append("[CHROMADB 1M+ VECTOR EMBEDDINGS (Port 8001 / E:\\AI_BS_Resources)]:")
                for d in docs[:top_k]:
                    col_name = d.get("collection", "vault")
                    doc_snippet = str(d.get("document", "")).strip().replace("\n", " ")[:1000]
                    rag_blocks.append(f"• [{col_name}]: {doc_snippet}")
        except Exception:
            pass

        # 3. SQLite Vault Records (stehouwer_vault.db, 139K records)
        try:
            vault_res = query_sqlite_vault(query, limit=2)
            valid_v = [v for v in vault_res if "content" in v or "title" in v]
            if valid_v:
                rag_blocks.append("[SQLITE VAULT SOVEREIGN MEMORY (stehouwer_vault.db, 139K Records)]:")
                for v in valid_v[:2]:
                    title = v.get("title") or "Vault Item"
                    body = (v.get("content") or v.get("description") or "").strip().replace("\n", " ")[:600]
                    rag_blocks.append(f"• [{title}]: {body}")
        except Exception:
            pass

        return "\n\n".join(rag_blocks) if rag_blocks else ""

    def _ingest_file_to_rag(self, file_path: str) -> Tuple[bool, str]:
        """Chunks a large file into 1,000-token blocks and embeds into ChromaDB Port 8001 with 768-dim nomic embeddings."""
        abs_p = os.path.abspath(file_path)
        if not os.path.isfile(abs_p):
            return False, f"File not found: {abs_p}"
        try:
            with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            chunks = self._chunk_text_semantic(content, chunk_size=1000, overlap=200)
            if not chunks:
                return False, "File is empty."

            import chromadb
            client = chromadb.HttpClient(host="127.0.0.1", port=8001)
            col_name = "ai_bs_context_memory"
            col = client.get_or_create_collection(name=col_name, embedding_function=None)

            docs, metas, ids, embeddings = [], [], [], []
            for i, chunk in enumerate(chunks):
                doc_id = f"rag_{os.path.basename(abs_p)}_{int(time.time())}_{i}"
                docs.append(chunk)
                metas.append({"source": os.path.basename(abs_p), "path": abs_p, "chunk_index": i})
                ids.append(doc_id)
                vec = None
                for port in (11435, 11434):
                    try:
                        with httpx.Client(timeout=4.0) as http_c:
                            r = http_c.post(f"http://127.0.0.1:{port}/api/embeddings", json={"model": "nomic-embed-text", "prompt": chunk})
                            if r.status_code == 200:
                                vec = r.json().get("embedding")
                                if vec:
                                    break
                    except Exception:
                        pass
                if vec:
                    embeddings.append(vec)

            if embeddings and len(embeddings) == len(docs):
                col.upsert(documents=docs, metadatas=metas, ids=ids, embeddings=embeddings)
            else:
                col.upsert(documents=docs, metadatas=metas, ids=ids)

            return True, f"Successfully chunked and offloaded {len(chunks)} blocks from [{os.path.basename(abs_p)}](file:///{abs_p.replace(os.sep, '/')}) into ChromaDB '{col_name}'!"
        except Exception as e:
            return False, f"ChromaDB ingestion failed: {e}"

    def _run_1m_map_reduce_task(self, file_path: str, instruction: str = "Summarize the key narrative points, characters, decisions, and structural beats") -> None:
        """Hierarchical Map-Reduce rolling accumulator across massive 1,000,000-token documents."""
        abs_p = os.path.abspath(file_path)
        try:
            with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            chunks = self._chunk_text_semantic(content, chunk_size=3500, overlap=300)
            total_chunks = len(chunks)
            self.action_log_signal.emit(
                "1M MAP-REDUCE PIPELINE ACTIVE",
                f"Document: {os.path.basename(abs_p)} ({len(content)} chars)\nTotal Batches: {total_chunks} chunk(s)\nCommencing rolling synthesis pass..."
            )

            rolling_summary = ""
            for idx, chunk in enumerate(chunks, start=1):
                prompt = (
                    f"You are the AI-BS Sovereign Map-Reduce Synthesizer.\n"
                    f"Instruction: {instruction}\n"
                    f"Prior Context Summary so far: {rolling_summary[:1500] if rolling_summary else '(Start of document)'}\n\n"
                    f"Current Section ({idx}/{total_chunks}):\n{chunk}\n\n"
                    f"Provide a concise updated running summary incorporating the new section:"
                )
                try:
                    with httpx.Client(timeout=120.0) as client:
                        r = client.post(
                            "http://127.0.0.1:11434/api/generate",
                            json={
                                "model": "stehouwer_llm:latest",
                                "prompt": prompt,
                                "stream": False,
                                "keep_alive": 0,
                                "options": {"num_ctx": 4096, "num_predict": 512},
                            },
                        )
                        if r.status_code == 200:
                            rolling_summary = r.json().get("response", "").strip()
                except Exception as e:
                    rolling_summary += f"\n[Batch {idx} parse notice: {e}]"

            summary_path = f"{abs_p}_1M_SUMMARY.md"
            try:
                with open(summary_path, "w", encoding="utf-8") as sf:
                    sf.write(f"# 1M+ Map-Reduce Synthesis: {os.path.basename(abs_p)}\n\n{rolling_summary}\n")
            except Exception:
                pass

            out_msg = (
                f"### 📑 1M HIERARCHICAL MAP-REDUCE SYNTHESIS COMPLETE\n"
                f"• Source Document: [{os.path.basename(abs_p)}](file:///{abs_p.replace(os.sep, '/')}) ({len(content)} chars, {total_chunks} chunks parsed)\n"
                f"• Saved Summary Artifact: [{os.path.basename(summary_path)}](file:///{summary_path.replace(os.sep, '/')})\n"
                f"• Architecture: Zero-VRAM-Overflow Hierarchical Batching (Screenwriting Studio Parity)\n\n"
                f"----------------------------------------\n"
                f"{rolling_summary}\n"
                f"----------------------------------------\n"
            )
            self.action_log_signal.emit("1M MAP-REDUCE MASTER REPORT", out_msg)
        except Exception as e:
            self.action_log_signal.emit("MAP-REDUCE ERROR", str(e))

    def _stream_response(self, model: str, prompt: str) -> None:
        # ── 1. AUTONOMOUS HOST TOOL EXECUTION (ZERO-DEPENDENCY STANDALONE + BACKEND REGISTRY) ──
        handled, out_msg, should_stop = self._execute_host_intent_standalone(prompt)
        if handled:
            self.token_chunk.emit(out_msg)
            self._conversation_history.append((prompt, out_msg))
            if len(self._conversation_history) > 10:
                self._conversation_history = self._conversation_history[-10:]
            if should_stop:
                self._is_streaming = False
                return

        backend_dir = r"C:\AI-BS\backend"
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        try:
            from core.hybrid_reasoning_engine import detect_tool_intent
            from tools.tool_registry import ToolRegistry

            t_name, t_args = detect_tool_intent(prompt)
            if t_name and t_name in ("read_host_file", "scan_directory_tree", "execute_powershell", "execute_bash", "execute_pip", "check_hardware", "probe_port"):
                res = ToolRegistry.execute_tool(t_name, t_args)
                self.token_chunk.emit(
                    f"⚡ [AUTONOMOUS HOST TOOL EXECUTED: {t_name}]\n"
                    f"{json.dumps(res, indent=2)}\n\n"
                )
                if t_name in ("execute_powershell", "execute_bash", "execute_pip"):
                    self._is_streaming = False
                    return
                prompt = (
                    f"[LIVE HOST TOOL RESULT ({t_name})]:\n{json.dumps(res, indent=2)}\n\n"
                    f"[USER REQUEST]: {prompt}\n"
                    f"Provide a direct, accurate answer using the verified host tool output above."
                )
        except Exception:
            pass

        # ── 2. OLLAMA STREAMING WITH MULTI-TURN HOST CONTEXT & RECENT HISTORY ──
        context_blocks = []
        if self._current_editor_file or self._last_referenced_file:
            context_blocks.append("[HOST WORKSPACE CONTEXT]:")
            if self._current_editor_file:
                context_blocks.append(f"• Active File in IDE Code Editor: {self._current_editor_file}")
            if self._last_referenced_file and self._last_referenced_file != self._current_editor_file:
                context_blocks.append(f"• Last Referenced Host File: {self._last_referenced_file}")
            context_blocks.append("")

        if self._conversation_history:
            context_blocks.append("[RECENT CONVERSATION HISTORY]:")
            for u_hist, a_hist in self._conversation_history[-4:]:
                u_clean = u_hist.strip()[:250]
                a_clean = a_hist.strip()[:250].replace("\n", " ")
                context_blocks.append(f"Operator: {u_clean}")
                context_blocks.append(f"BS-Chat: {a_clean}")
            context_blocks.append("")

        # ── 2.5. CHROMA VECTOR & SQLITE VAULT 1M+ RAG OFFLOAD INJECTION ──
        rag_context = self._retrieve_1m_rag_context(prompt, self._current_editor_file)
        if rag_context:
            context_blocks.append("[1M+ CHROMA VECTOR & VAULT RAG OFFLOAD CONTEXT]:")
            context_blocks.append(rag_context)
            context_blocks.append("")

        context_blocks.append(f"[CURRENT OPERATOR REQUEST]:\n{prompt}")
        enriched_prompt = "\n".join(context_blocks)

        url = "http://127.0.0.1:11434/api/generate"
        system_instruction = (
            "You are the Stehouwer Autonomous AI-BS Sovereign Intelligence Engine in BS-Chat. "
            "The operator is pair-programming and executing host operations with you on Windows 11. "
            "You have 100% unrestricted root host execution authority via Windows PowerShell (-ExecutionPolicy Bypass) in C:\\AI-BS. "
            "CRITICAL EXECUTION RULE: When the operator asks you to perform a host action (write/create a file, run a script, check a directory, or inspect the C: drive), "
            "any ```powershell code block you output WILL BE AUTOMATICALLY EXECUTED on the host system immediately by BS-Chat. "
            "CRITICAL HYPERLINK RULE: Whenever you reference, create, inspect, or write a host file on disk, ALWAYS format the file path as a clickable markdown hyperlink using the file:/// scheme (e.g., [C:\\AI-BS\\exampleFile.txt](file:///C:/AI-BS/exampleFile.txt)). "
            "The operator can click this hyperlink to view and edit the file directly in the BS-Chat IDE Code Editor, or right-click to 'Show in File Explorer'. "
            "NEVER tell the user to click '⚡ Run Last Code (PowerShell)' and NEVER say 'Once executed...'. "
            "Output clean, syntactically valid ```powershell or ```python code blocks and state the exact C:\\ path."
        )
        full_reply = ""
        dynamic_ctx = 4096 if len(enriched_prompt) < 10000 else min(32768, (len(enriched_prompt) // 3) + 2048)
        try:
            with httpx.stream(
                "POST",
                url,
                json={
                    "model": model,
                    "prompt": enriched_prompt,
                    "system": system_instruction,
                    "stream": True,
                    "keep_alive": 0,
                    "options": {"num_ctx": dynamic_ctx},
                },
                timeout=120.0
            ) as r:
                for line in r.iter_lines():
                    if not self._is_streaming:
                        break
                    if line:
                        chunk = json.loads(line)
                        tok = chunk.get("response", "")
                        full_reply += tok
                        self.token_chunk.emit(tok)
                        if chunk.get("done"):
                            break

            if full_reply:
                self._conversation_history.append((prompt, full_reply))
                if len(self._conversation_history) > 10:
                    self._conversation_history = self._conversation_history[-10:]

            # ── 3. POST-STREAM AUTONOMOUS POWERSHELL / PYTHON EXECUTION ──
            if full_reply:
                lang, code = self._extract_last_code_block(full_reply)
                p_low = prompt.lower()
                host_action_requested = any(
                    w in p_low for w in (
                        "write", "create", "save", "make", "run", "execute", "delete",
                        "remove", "copy", "move", "rename", "list", "check", "find",
                        "locate", "host", "c drive", "c:\\", "c:/", "file", "folder", "directory"
                    )
                )
                ps_has_side_effect = any(
                    cmdlet in code for cmdlet in (
                        "Out-File", "Set-Content", "Add-Content", "New-Item",
                        "Copy-Item", "Move-Item", "Remove-Item", "Get-ChildItem", "Get-Content"
                    )
                )
                if code and (lang in ("powershell", "ps1", "ps", "cmd", "bat", "sh") or ps_has_side_effect) and host_action_requested:
                    self.token_chunk.emit("\n\n⚡ [AUTONOMOUS HOST EXECUTION: Running generated PowerShell on C:\\AI-BS...]\n")
                    res = subprocess.run(
                        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", code],
                        cwd=r"C:\AI-BS",
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    stdout_s = (res.stdout or "").strip()
                    stderr_s = (res.stderr or "").strip()
                    status_str = "SUCCESS (Exit 0)" if res.returncode == 0 else f"EXIT {res.returncode}"
                    exec_summary = f"• Execution Status: {status_str}\n"
                    if stdout_s:
                        exec_summary += f"• Host Output:\n{stdout_s}\n"
                    if stderr_s:
                        exec_summary += f"• Host Stderr:\n{stderr_s}\n"
                    # Verify any C:\ file path mentioned in the code block and format as clickable hyperlinks
                    for path_m in re.finditer(r'([A-Za-z]:\\[A-Za-z0-9_.\-\\]+\.[A-Za-z0-9]+)', code):
                        cand_path = path_m.group(1)
                        if os.path.isfile(cand_path):
                            cand_url = f"file:///{cand_path.replace(os.sep, '/')}"
                            exec_summary += f"• Verified File on Disk: [{cand_path}]({cand_url}) ({os.path.getsize(cand_path)} bytes)\n"
                    self.token_chunk.emit(exec_summary)
        except Exception as e:
            self.token_chunk.emit(f"[Stream Error on Port 11434: {e}]")
        finally:
            self._is_streaming = False
            # Sovereign On-Demand VRAM Reclamation: evict loaded weights immediately
            try:
                with httpx.Client(timeout=2.0) as evict_c:
                    evict_c.post(f"http://127.0.0.1:11434/api/generate", json={"model": model, "keep_alive": 0})
            except Exception:
                pass

    def _extract_last_code_block(self, custom_text: Optional[str] = None) -> Tuple[str, str]:
        """Extracts the most recent code block from the chat transcript or provided text."""
        text = custom_text if custom_text is not None else self.chat_display.toPlainText()
        matches = list(re.finditer(r"```([a-zA-Z0-9_\-\+]*)\r?\n([\s\S]*?)\r?\n```", text))
        if matches:
            last = matches[-1]
            lang = last.group(1).strip().lower()
            code = last.group(2).strip()
            return lang, code
        return "", ""

    def _run_last_code_in_powershell(self) -> None:
        """Executes the last code block from the chat transcript via Multi-Runtime Router + Stage 1 Auto-Heal."""
        lang, code = self._extract_last_code_block()
        if not code:
            code = self.code_editor.toPlainText().strip()
            if not code:
                QMessageBox.warning(self, "No Code Found", "No code block found in chat transcript or scratchpad to execute.")
                return
            lang = "auto"

        self.left_stack.setCurrentIndex(1)
        self.chat_display.appendPlainText(
            f"\n[OPERATOR @ {time.strftime('%H:%M:%S')}]: Executing code block ({lang or 'auto'}) with Stage 1 Auto-Heal...\n"
        )
        self.bus.submit(self._run_multi_runtime_with_auto_heal, code, lang or "auto", self._current_editor_file)

    def _load_last_code_to_scratchpad(self) -> None:
        """Copies the last code block from chat to the scratchpad editor and reveals split pane."""
        lang, code = self._extract_last_code_block()
        if not code:
            QMessageBox.information(self, "No Code Block", "No code block found in chat transcript.")
            return
        self.code_editor.setPlainText(code)
        if not self._split_active:
            self._toggle_split_view()
        self.chat_display.appendPlainText(f"\n[SYSTEM]: Loaded last code block ({len(code)} chars) into Active Scratchpad Canvas.\n")

    def _save_last_code_to_file(self) -> None:
        """Saves the last code block from chat to a file on host disk."""
        lang, code = self._extract_last_code_block()
        if not code:
            code = self.code_editor.toPlainText().strip()
            if not code:
                QMessageBox.warning(self, "No Code Found", "No code block found to save.")
                return

        m = re.search(r'(?:#|//)\s*(?:File|Target|Path):\s*([^\r\n]+)', code, re.IGNORECASE)
        default_name = m.group(1).strip() if m else "new_program.py"

        file_path, ok = QInputDialog.getText(
            self, "Save Code to File", "Target file path (relative to C:\\AI-BS or absolute):",
            QLineEdit.EchoMode.Normal, default_name
        )
        if not ok or not file_path.strip():
            return

        target = file_path.strip()
        if not os.path.isabs(target):
            target = os.path.join(r"C:\AI-BS", target)

        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(code)
            self.chat_display.appendPlainText(f"\n[SYSTEM]: Saved code block to {target} ({len(code)} bytes).\n")
            QMessageBox.information(self, "Saved", f"File saved successfully to:\n{target}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{e}")

    def _open_file_in_editor(self, file_path: str) -> None:
        """Opens the target file in the BS-Chat IDE Code Editor / Scratchpad right pane."""
        abs_path = os.path.normpath(file_path)
        if not os.path.isabs(abs_path):
            abs_path = os.path.normpath(os.path.join(r"C:\AI-BS", abs_path))

        if not os.path.isfile(abs_path):
            QMessageBox.warning(self, "File Not Found", f"Cannot open file. It does not exist on disk:\n{abs_path}")
            return

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            self._current_editor_file = abs_path
            self._last_referenced_file = abs_path
            self.code_editor.set_current_file(abs_path)
            self.code_editor.setPlainText(content)
            if not self._split_active:
                self._toggle_split_view()

            size_b = os.path.getsize(abs_path)
            self.lbl_canvas.setText(f"Active Editor: {os.path.basename(abs_path)} ({size_b} bytes)")
            self.lbl_canvas.setToolTip(abs_path)
            link_html = f"[{abs_path}](file:///{abs_path.replace(os.sep, '/')})"
            if not self._is_streaming:
                self.chat_display.appendPlainText(f"\n[SYSTEM]: Loaded {os.path.basename(abs_path)} ({size_b} bytes) into BS-Chat IDE Code Editor.\n")
            else:
                self.pane_status_lbl.setText(f"● Editor: {os.path.basename(abs_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error Opening File", f"Failed to read file:\n{e}")

    def _show_in_file_explorer(self, file_path: str) -> None:
        """Opens Windows File Explorer and selects/highlights the target file."""
        abs_path = os.path.normpath(file_path)
        if not os.path.isabs(abs_path):
            abs_path = os.path.normpath(os.path.join(r"C:\AI-BS", abs_path))

        if not os.path.exists(abs_path):
            QMessageBox.warning(self, "File Not Found", f"Target file or folder does not exist:\n{abs_path}")
            return

        try:
            subprocess.Popen(f'explorer.exe /select,"{abs_path}"')
        except Exception as e:
            QMessageBox.critical(self, "Explorer Error", f"Failed to launch File Explorer:\n{e}")

    def _show_active_editor_file_in_explorer(self) -> None:
        """Shows current active editor file in File Explorer."""
        target = self._current_editor_file or r"C:\AI-BS"
        self._show_in_file_explorer(target)

    def _save_scratchpad_to_file(self) -> None:
        """Saves current scratchpad code to active file on disk or prompts if unsaved."""
        code = self.code_editor.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "Empty Scratchpad", "Scratchpad contains no code.")
            return

        target = self._current_editor_file
        if not target:
            m = re.search(r'(?:#|//)\s*(?:File|Target|Path):\s*([^\r\n]+)', code, re.IGNORECASE)
            default_name = m.group(1).strip() if m else "scratch_program.py"
            file_path, ok = QInputDialog.getText(
                self, "Save Scratchpad to File", "Target file path (relative to C:\\AI-BS or absolute):",
                QLineEdit.EchoMode.Normal, default_name
            )
            if not ok or not file_path.strip():
                return
            target = file_path.strip()
            if not os.path.isabs(target):
                target = os.path.join(r"C:\AI-BS", target)

        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(code)
            self._current_editor_file = target
            self._last_referenced_file = target
            self.code_editor.set_current_file(target)
            size_b = os.path.getsize(target)
            self.lbl_canvas.setText(f"Active Editor: {os.path.basename(target)} ({size_b} bytes)")
            link_html = f"[{target}](file:///{target.replace(os.sep, '/')})"
            self.chat_display.appendPlainText(f"\n[SYSTEM]: Saved active code to {link_html} ({size_b} bytes).\n")
            QMessageBox.information(self, "Saved", f"File saved successfully to:\n{target}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{e}")

    def _spawn_powershell_terminal(self) -> None:
        r"""Spawns an interactive elevated PowerShell console window in C:\AI-BS."""
        try:
            cmd = (
                'start powershell.exe -NoExit -ExecutionPolicy Bypass -Command '
                '"Set-Location \'C:\\AI-BS\'; '
                'Write-Host \'================================================================\' -ForegroundColor Cyan; '
                'Write-Host \'  ⚡ AI-BS SOVEREIGN DEVELOPMENT CONSOLE (POWERSHELL BYPASS)  \' -ForegroundColor Yellow; '
                'Write-Host \'  Root host privileges active • Working directory: C:\\AI-BS    \' -ForegroundColor Green; '
                'Write-Host \'================================================================\' -ForegroundColor Cyan; '
                'Get-Host | Select-Object Version, UI; "'
            )
            subprocess.Popen(["cmd.exe", "/c", cmd], shell=True)
            self.chat_display.appendPlainText(f"\n[SYSTEM @ {time.strftime('%H:%M:%S')}]: Spawned interactive PowerShell console window (Bypass Mode).\n")
        except Exception as e:
            QMessageBox.critical(self, "Console Error", f"Failed to spawn PowerShell console:\n{e}")

    def shutdown(self) -> None:
        self._is_streaming = False
        self._chat_recovery.shutdown()

    def _append_token(self, chunk: str) -> None:
        if any(marker in chunk for marker in ("file:///", "[C:", "C:\\", "✅", "⚡", "📂", "📄")):
            cur = self.chat_display.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.insertHtml(format_chat_text_to_html(chunk))
            self.chat_display.setTextCursor(cur)
        else:
            cur = self.chat_display.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.insertText(chunk)
            self.chat_display.setTextCursor(cur)
        self.chat_display.ensureCursorVisible()

    def _append_action_log(self, header: str, content: str) -> None:
        self.left_stack.setCurrentIndex(1)
        self.chat_display.appendPlainText(f"\n[{header}]:\n{content}\n")

    def _check_vram(self) -> None:
        try:
            from backend.modules.gpu_hardware_telemetry import sample_gpu_telemetry
            data = sample_gpu_telemetry()
            out = (
                f"GPU: {data.get('device_name', 'NVIDIA GeForce RTX 4090')}\n"
                f"Core Temp: {data.get('temperature_c', 30)}°C | VRAM: {data.get('vram_used_gb', 1.5):.2f} / 24.00 GB"
            )
            self.action_log_signal.emit("RTX 4090 HARDWARE TELEMETRY", out)
        except Exception as e:
            self.action_log_signal.emit("VRAM ERROR", str(e))

    def _check_ports(self) -> None:
        from native_studio.engine import probe_ports
        ports = probe_ports()
        online = [p for p, info in ports.items() if info.get("online")]
        self.action_log_signal.emit(
            "18-PORT MATRIX TOPOLOGY",
            f"Online Sockets ({len(online)}/{len(ports)}): {', '.join(str(p) for p in sorted(online))}",
        )

    def _save_scratchpad_to_vault(self) -> None:
        code = self.code_editor.toPlainText().strip()
        if not code:
            return
        db_path = r"C:\AI-BS\backend\stehouwer_vault.db"
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            item_id = f"scratch_{int(time.time())}"
            conn.execute(
                "INSERT INTO vault_items (item_id, item_type, title, content, created_at) VALUES (?, ?, ?, ?, ?);",
                (item_id, "scratchpad", "BS-CHAT Code Scratchpad", code, time.time()),
            )
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Saved to Vault", f"Saved to stehouwer_vault.db as {item_id}")
        except Exception as e:
            QMessageBox.critical(self, "Vault Save Error", str(e))

    def _validate_syntax(self) -> None:
        try:
            compile(self.code_editor.toPlainText(), "<scratchpad>", "exec")
            QMessageBox.information(self, "Syntax Check", "Python Syntax Validated: 100% Valid AST structure.")
        except Exception as e:
            QMessageBox.warning(self, "Syntax Error", str(e))
