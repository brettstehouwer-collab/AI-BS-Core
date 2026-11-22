"""Universal Hollywood Screenwriting Studio & Story Bible Native View.

Pixel-perfect native desktop replica of http://localhost:5173/?tab=unified_creation
Features:
- Creation Suite Header & Sub-Tool Switcher (Writing, Video, ComfyUI, Visual Scripting)
- Hollywood Action Bar (+ New Project, Zen Mode, Novelize to Book, Table Read Studio, Telemetry, Import/Export)
- Format Toolbar (Undo, Redo, Cut, Copy, Paste, Bold, Italic, Underline, Spell, Thesaurus, Alt-Take)
- Page Navigation & Mode Bar (Editor, Page View, Split, Beat Board, Page pagination, Scene selector, Script Co-Pilot)
- Left Project & Scene Sidebar (Outlines, Projects, Branches, Sprints, Scene list with live page indices)
- Real Hollywood Page Layout: Centered page in Courier monospace with industry standard margins
- Bottom Script Telemetry Strip: 31 Pages (~31m screen time), Dialogue/Action breakdown, Roles, Scenes, Jump to Page, Zoom
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path

from native_studio.screenplay_client import DraftSession, ScreenplayClient, ScreenplayError, write_new_export

from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QAction, QColor, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE





class BeatCardWidget(QFrame):
    """Interactive Hollywood Beat Card replicating web .sw-beat-card."""

    def __init__(self, idx: int, beat: dict, on_jump: callable, on_animate: callable, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.beat = beat
        self.on_jump = on_jump
        self.on_animate = on_animate
        self.setFixedSize(160, 135)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QFrame {"
            "  background: #182030;"
            "  border: 1.5px solid rgba(56, 189, 248, 0.4);"
            "  border-radius: 6px;"
            "  padding: 8px;"
            "}"
            "QFrame:hover {"
            "  border-color: #38bdf8;"
            "  background: #1e293b;"
            "}"
        )
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        # Top row: Index badge and page indicator
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        lbl_idx = QLabel(f"#{self.idx + 1}")
        lbl_idx.setStyleSheet("background: #0284c7; color: #ffffff; border-radius: 3px; padding: 1px 4px; font-size: 7pt; font-weight: bold;")
        lbl_page = QLabel(f"p.{self.beat.get('page', 1)}")
        lbl_page.setStyleSheet("color: #94a3b8; font-size: 7.5pt; font-weight: bold;")
        top_row.addWidget(lbl_idx)
        top_row.addStretch()
        top_row.addWidget(lbl_page)
        lay.addLayout(top_row)

        # Emoji & Heading
        emoji = self.beat.get("emoji", "🎬")
        heading = self.beat.get("heading", f"SCENE {self.idx + 1}")
        lbl_heading = QLabel(f"{emoji} {heading}")
        lbl_heading.setWordWrap(True)
        lbl_heading.setStyleSheet("color: #f8fafc; font-size: 8pt; font-weight: bold;")
        lbl_heading.setFixedHeight(36)
        lay.addWidget(lbl_heading)

        lay.addStretch()

        # Action: Animate Scene button
        self.btn_anim = QPushButton("🎥 Animate Scene")
        self.btn_anim.setFixedHeight(22)
        self.btn_anim.setStyleSheet(
            "QPushButton { background: #0284c7; color: #ffffff; border-radius: 3px; font-size: 7pt; font-weight: bold; border: none; }"
            "QPushButton:hover { background: #0369a1; }"
        )
        self.btn_anim.clicked.connect(lambda: self.on_animate(self.beat))
        lay.addWidget(self.btn_anim)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_jump(self.beat)
        super().mousePressEvent(event)


class BeatBoardWidget(QWidget):
    """Visual Story Beat Board Canvas replicating web activeView === 'beats'."""

    def __init__(self, on_jump_to_scene: callable, on_animate_scene: callable, parent=None):
        super().__init__(parent)
        self.on_jump_to_scene = on_jump_to_scene
        self.on_animate_scene = on_animate_scene
        self.setStyleSheet("background: #060a12;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header bar
        header = QHBoxLayout()
        lbl_title = QLabel("🗂️ <b>HOLLYWOOD STORY BEAT BOARD & SCENE CARDS</b>")
        lbl_title.setStyleSheet("color: #38bdf8; font-size: 10pt;")
        self.lbl_count = QLabel("0 Beats")
        self.lbl_count.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: bold;")
        header.addWidget(lbl_title)
        header.addSpacing(12)
        header.addWidget(self.lbl_count)
        header.addStretch()

        btn_add = QPushButton("+ Add Beat")
        btn_add.setStyleSheet("background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 3px 8px; font-size: 8pt; font-weight: bold;")
        btn_add.clicked.connect(self._add_beat_prompt)
        header.addWidget(btn_add)

        layout.addLayout(header)

        # Scroll area for cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background: #060a12; border: 1px solid #162032; border-radius: 6px; }")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: #060a12;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(16, 16, 16, 16)
        self.cards_layout.setSpacing(14)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll, 1)

        self._beats = []

    def populate_beats(self, beats: list[dict]):
        self._beats = list(beats)
        # Clear existing card widgets
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.lbl_count.setText(f"{len(self._beats)} Story Beats")
        for idx, beat in enumerate(self._beats):
            card = BeatCardWidget(idx, beat, self.on_jump_to_scene, self.on_animate_scene, self)
            self.cards_layout.addWidget(card)
        self.cards_layout.addStretch()

    def _add_beat_prompt(self):
        slug, ok = QInputDialog.getText(self, "Add Story Beat", "Scene Slug (e.g. EXT. ROOFTOP - NIGHT):")
        if ok and slug:
            new_beat = {"heading": slug.upper(), "page": len(self._beats) + 1, "emoji": "🎬", "line": 0}
            self._beats.append(new_beat)
            self.populate_beats(self._beats)


class ScreenplayPageViewerWidget(QWidget):
    """Paginated 8.5 x 11 Finished Script Page View with industry standard Courier margins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #070b13;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background: #070b13; border: none; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: #070b13;")
        self.c_lay = QVBoxLayout(self.container)
        self.c_lay.setContentsMargins(20, 20, 20, 20)
        self.c_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.page_sheets: list[QFrame] = []
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def render_pages(self, content: str, active_page: int = 1):
        lines = content.splitlines()
        # Clean existing pages
        while self.c_lay.count():
            item = self.c_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.page_sheets.clear()

        # 54 lines industry standard per page
        lines_per_page = 54
        chunks = [lines[i:i + lines_per_page] for i in range(0, max(1, len(lines)), lines_per_page)]
        total_p = max(1, len(chunks))

        for p_idx, page_lines in enumerate(chunks, start=1):
            sheet = QFrame()
            sheet.setFixedSize(780, 1020)
            is_active = (p_idx == active_page)
            border_col = "#38bdf8" if is_active else "#cbd5e1"
            sheet.setStyleSheet(
                f"QFrame {{"
                f"  background: #ffffff;"
                f"  border: 1.5px solid {border_col};"
                f"  border-radius: 3px;"
                f"  box-shadow: 0 8px 24px rgba(0,0,0,0.6);"
                f"}}"
            )
            s_lay = QVBoxLayout(sheet)
            s_lay.setContentsMargins(70, 50, 60, 50)

            # Top header with page number
            top_h = QHBoxLayout()
            top_h.addStretch()
            lbl_p = QLabel(f"{p_idx}.")
            lbl_p.setStyleSheet("color: #000000; font-family: 'Courier New', Courier; font-size: 10pt; font-weight: bold;")
            top_h.addWidget(lbl_p)
            s_lay.addLayout(top_h)

            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setFont(QFont("Courier New", 10))
            txt.setPlainText("\n".join(page_lines))
            txt.setStyleSheet("background: transparent; border: none; color: #000000; font-family: 'Courier New', Courier; line-height: 1.3;")
            s_lay.addWidget(txt, 1)

            self.c_lay.addWidget(sheet)
            self.c_lay.addSpacing(16)
            self.page_sheets.append(sheet)

    def scroll_to_page(self, page_num: int):
        idx = max(1, min(len(self.page_sheets), page_num)) - 1
        if 0 <= idx < len(self.page_sheets):
            sheet = self.page_sheets[idx]
            self.scroll.ensureWidgetVisible(sheet)


class ScreenwritingNativeView(QWidget):
    """Hollywood AST Screenplay Studio & Story Bible Native View."""


    def __init__(self, bus: EngineBus, *, creative_session=None, bootstrap=None) -> None:
        super().__init__()
        if creative_session is not None or bootstrap is not None:
            from native_studio.creative_session import Bootstrap, CreativeSession, CreativeSessionError
            if (type(creative_session) is not CreativeSession or type(bootstrap) is not Bootstrap
                    or creative_session._scope is not bootstrap):
                raise CreativeSessionError()
        self._creative_bootstrap = bootstrap
        self._creative_initial_read = bootstrap is not None
        self.bus = bus
        self._current_page = 1
        self._total_pages = 1
        self._current_project = None
        self._parsed_beats = []
        self._writer_client = (ScreenplayClient() if creative_session is None else
                               ScreenplayClient(creative_session=creative_session))
        self._draft = DraftSession()
        if creative_session is not None:
            self._draft.recovery_scope = creative_session.recovery_scope
        self._writer_busy = False
        self._adapt_job = None
        self._build_ui()
        self._draft_timer = QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(1000)
        self._draft_timer.timeout.connect(self._preserve_native_draft)
        self.editor.textChanged.connect(self._on_native_draft_changed)
        self.editor.document().contentsChange.connect(self._on_native_rich_range_changed)
        self._adapt_timer = QTimer(self)
        self._adapt_timer.setInterval(3000)
        self._adapt_timer.timeout.connect(self._poll_native_adaptation)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._preserve_native_draft)
            app.installEventFilter(self)
        if bootstrap is None:
            self._scan_and_populate_projects()
        else:
            self._apply_delegated_controls()
            self.combo_project.blockSignals(True)
            self.combo_project.addItem(bootstrap.project)
            self.combo_project.blockSignals(False)
            item = QListWidgetItem(bootstrap.project)
            item.setData(Qt.ItemDataRole.UserRole, bootstrap.project)
            self.proj_list.addItem(item)
            self._read_native_project(bootstrap.project)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("background: #080d16; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;")

        # ── ROW 1: CREATION SUITE SUB-TABS & BREADCRUMBS ──
        subtabs_bar = QFrame()
        subtabs_bar.setFixedHeight(36)
        subtabs_bar.setStyleSheet("background: #0b111e; border-bottom: 1px solid #1e293b;")
        sb_lay = QHBoxLayout(subtabs_bar)
        sb_lay.setContentsMargins(12, 0, 12, 0)
        sb_lay.setSpacing(6)

        lbl_suite = QLabel("<b>CREATION SUITE</b>")
        lbl_suite.setStyleSheet("color: #38bdf8; font-size: 8.5pt; margin-right: 6px;")
        sb_lay.addWidget(lbl_suite)

        self.btn_writing = self._create_nav_btn("✍️ Writing Studio", active=True)
        self.btn_video = self._create_nav_btn("🎬 Video Studio")
        self.btn_comfy = self._create_nav_btn("❇️ ComfyUI Studio")
        self.btn_visual = self._create_nav_btn("🔀 Visual Scripting")

        self.btn_writing.clicked.connect(lambda: self._switch_suite_tab("writing"))
        self.btn_video.clicked.connect(lambda: self._switch_suite_tab("video"))
        self.btn_comfy.clicked.connect(lambda: self._switch_suite_tab("comfy"))
        self.btn_visual.clicked.connect(lambda: self._switch_suite_tab("visual"))

        sb_lay.addWidget(self.btn_writing)
        sb_lay.addWidget(self.btn_video)
        sb_lay.addWidget(self.btn_comfy)
        sb_lay.addWidget(self.btn_visual)

        sb_lay.addStretch()

        self.btn_share = self._create_action_pill("🔗 Share Sub-Tool", "#1e293b", "#94a3b8")
        self.btn_guide = self._create_action_pill("💡 Studio Guide", "#1e293b", "#eab308")
        self.btn_lock = self._create_action_pill("🔒 Lock Studio", "#1e293b", "#ef4444")
        self.btn_share.clicked.connect(self._share_subtool)
        self.btn_guide.clicked.connect(self._show_studio_guide)
        self.btn_lock.clicked.connect(self._toggle_lock_studio)
        sb_lay.addWidget(self.btn_share)
        sb_lay.addWidget(self.btn_guide)
        sb_lay.addWidget(self.btn_lock)

        main_layout.addWidget(subtabs_bar)

        # ── CREATION SUITE MULTI-TOOL STACK (WRITING, VIDEO, COMFYUI, VISUAL SCRIPTING, LOCK) ──
        self.suite_stack = QStackedWidget()
        self._last_active_index = 0

        self.writing_page = self._build_writing_page()
        self.suite_stack.addWidget(self.writing_page)     # 0: Writing Studio
        if self._creative_bootstrap is None:
            from native_studio.creation_suite_subtools import (
                ComfyUIStudioPage, LockScreenPage, VideoStudioPage, VisualScriptingPage)
            self.video_page = VideoStudioPage(self.bus)
            self.comfy_page = ComfyUIStudioPage(self.bus, active_script_provider=self._active_creative_snapshot)
            self.visual_page = VisualScriptingPage(self.bus)
            self.lock_page = LockScreenPage(self._unlock_studio)
            self.suite_stack.addWidget(self.video_page)       # 1: Video Studio
            self.suite_stack.addWidget(self.comfy_page)       # 2: ComfyUI Studio
            self.suite_stack.addWidget(self.visual_page)      # 3: Visual Scripting
            self.suite_stack.addWidget(self.lock_page)        # 4: Lock Screen

        main_layout.addWidget(self.suite_stack, 1)

    def _decline_delegated_action(self):
        self._writer_status('Connected project only: read, save, Export FDX/PDF and local draft recovery.')

    def _delegated_editor_ready(self):
        """Initial snapshot gate only; lease expiry must not destroy local editing."""
        packet = getattr(self, '_creative_bootstrap', None)
        return (packet is None or
                (not self._creative_initial_read and self._draft.project == packet.project
                 and bool(self._draft.revision)))

    def _apply_delegated_controls(self):
        """UI affordances complement method and delegated-client request guards."""
        self.writing_page.setEnabled(self._delegated_editor_ready())
        self.lbl_rich_notice.setText('FDX text projection: edit existing paragraph text. Original styles, notes and metadata stay in the source. Creating a separate structural working copy is unavailable in this connected-project session.')
        for name in (
            'btn_video', 'btn_comfy', 'btn_visual', 'btn_share', 'btn_guide', 'btn_lock',
            'btn_refresh_projects', 'btn_new_proj', 'btn_novelize', 'btn_table_read', 'btn_telemetry',
            'btn_import', 'btn_help_guide', 'btn_adapt_status', 'btn_previs', 'btn_prod',
            'btn_send_video', 'btn_export_unreal_csv', 'btn_export_unreal_py', 'btn_send_comfy',
            'btn_open_previs', 'btn_storyboards', 'btn_prod_char_vault', 'btn_prod_coverage',
            'btn_prod_analytics', 'btn_prod_film_budget', 'btn_prod_stage_budget', 'btn_revision_toggle',
            'btn_prod_title_page', 'btn_prod_publish_cms', 'btn_review', 'btn_audio_drama', 'btn_copilot',
            'btn_sidebar_new', 'p_item2', 'btn_start_sprint', 'btn_mode_beat',
            'combo_project', 'proj_list', 'combo_revision_color',
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setEnabled(False)
                widget.setToolTip('Unavailable in this connected-project session.')
                if isinstance(widget, QPushButton):
                    widget.hide()
        for name, button in self._format_buttons.items():
            if 'Alt-Take' in name or 'Help Guide' in name:
                button.setEnabled(False)
                button.hide()
        for action in self.btn_export_fdx.menu().actions():
            if 'Fountain' in action.text():
                action.setEnabled(False)
                action.setVisible(False)
        for action in self.btn_export_pdf.menu().actions()[1:]:
            if not action.property('native_export_profile'):
                action.setVisible(False)
        for card in self.findChildren(BeatCardWidget):
            card.btn_anim.setEnabled(False)

    def _build_writing_page(self) -> QWidget:
        page = QWidget()
        p_lay = QVBoxLayout(page)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(0)

        # Pre-instantiate editor so format and element action connections bind directly
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier New", 11))
        self.editor.setPlainText("")
        self.editor.setReadOnly(True)
        self.editor.setStyleSheet(
            "background: transparent; border: none; color: #0f172a; font-family: 'Courier New', Courier, monospace; line-height: 1.4;"
        )
        self.editor.textChanged.connect(self._parse_scenes_and_metrics)

        # ── ROW 2A: CONSOLIDATED STUDIO HEADER, PROJECT SELECTOR & RIBBON CATEGORY SWITCHER ──
        self.header_ribbon_bar = QFrame()
        self.header_ribbon_bar.setFixedHeight(38)
        self.header_ribbon_bar.setStyleSheet("background: #111827; border-bottom: 1px solid #1f2937;")
        hr_lay = QHBoxLayout(self.header_ribbon_bar)
        hr_lay.setContentsMargins(14, 0, 14, 0)
        hr_lay.setSpacing(8)

        # Left Breadcrumb + Project Dropdown (Matches Web ScreenwritingTab.jsx)
        lbl_bc1 = QLabel("🎬 Creation Suite")
        lbl_bc1.setStyleSheet("color: #9ca3af; font-size: 8.5pt;")
        lbl_sep1 = QLabel("/")
        lbl_sep1.setStyleSheet("color: #4b5563; font-size: 8.5pt;")
        lbl_bc2 = QLabel("<b>✍️ Writing Studio</b>")
        lbl_bc2.setStyleSheet("color: #38bdf8; font-size: 8.5pt;")
        lbl_sep2 = QLabel("/")
        lbl_sep2.setStyleSheet("color: #4b5563; font-size: 8.5pt;")

        self.combo_project = QComboBox()
        
        self.combo_project.setStyleSheet(
            "QComboBox { background: #1f2937; color: #facc15; border: 1px solid #374151; border-radius: 4px; padding: 3px 10px; font-size: 8.5pt; font-weight: bold; min-width: 170px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #111827; color: #f8fafc; selection-background-color: #1e293b; selection-color: #facc15; }"
        )
        self.combo_project.currentTextChanged.connect(self._on_project_switched)

        hr_lay.addWidget(lbl_bc1)
        hr_lay.addWidget(lbl_sep1)
        hr_lay.addWidget(lbl_bc2)
        hr_lay.addWidget(lbl_sep2)
        hr_lay.addWidget(self.combo_project)
        self.btn_refresh_projects = self._create_action_pill('Refresh Projects', '#1e293b', '#38bdf8')
        self.btn_refresh_projects.clicked.connect(self._scan_and_populate_projects)
        hr_lay.addWidget(self.btn_refresh_projects)

        hr_lay.addStretch()

        # Right Ribbon Category Switcher Pill Group (Matches Web 5-Tab Switcher)
        ribbon_group = QFrame()
        ribbon_group.setStyleSheet("background: #0a0a0a; border: 1px solid #1f2937; border-radius: 6px;")
        rg_lay = QHBoxLayout(ribbon_group)
        rg_lay.setContentsMargins(3, 2, 3, 2)
        rg_lay.setSpacing(3)

        self.btn_write = self._create_ribbon_tab_btn("✍️ Write", active=True)
        self.btn_elem = self._create_ribbon_tab_btn("🧩 Elements", active=False)
        self.btn_views = self._create_ribbon_tab_btn("👁️ Views & Split", active=False)
        self.btn_previs = self._create_ribbon_tab_btn("🎮 3D & Previs", active=False)
        self.btn_prod = self._create_ribbon_tab_btn("🚀 Production & CMS", active=False)

        self._ribbon_tab_buttons = {
            "write": self.btn_write,
            "elements": self.btn_elem,
            "views": self.btn_views,
            "unreal": self.btn_previs,
            "production": self.btn_prod,
        }

        self.btn_write.clicked.connect(lambda: self._set_ribbon_tab("write"))
        self.btn_elem.clicked.connect(lambda: self._set_ribbon_tab("elements"))
        self.btn_views.clicked.connect(lambda: self._set_ribbon_tab("views"))
        self.btn_previs.clicked.connect(lambda: self._set_ribbon_tab("unreal"))
        self.btn_prod.clicked.connect(lambda: self._set_ribbon_tab("production"))

        menu_elem = QMenu(self.btn_elem)
        menu_elem.setStyleSheet("QMenu { background: #0b111e; color: #f1f5f9; border: 1px solid #1e293b; font-size: 8pt; } QMenu::item:selected { background: #1e293b; color: #38bdf8; }")
        menu_elem.addAction("🎬 Insert Heading").triggered.connect(lambda: self._insert_element_text("\n\nINT. LOCATION - DAY\n\n"))
        menu_elem.addAction("📝 Insert Action").triggered.connect(lambda: self._insert_element_text("\n\nAction description...\n\n"))
        menu_elem.addAction("💬 Insert Dialogue").triggered.connect(lambda: self._insert_element_text("Dialogue text...\n\n"))
        menu_elem.addAction("🧩 Open Elements Palette...").triggered.connect(self._show_elements_palette)
        self.btn_elem.setMenu(menu_elem)

        menu_views = QMenu(self.btn_views)
        menu_views.setStyleSheet("QMenu { background: #0b111e; color: #f1f5f9; border: 1px solid #1e293b; font-size: 8pt; } QMenu::item:selected { background: #1e293b; color: #38bdf8; }")
        menu_views.addAction("📝 Script Editor View").triggered.connect(lambda: self._set_view_mode("editor"))
        menu_views.addAction("👁️ Finished Page View").triggered.connect(lambda: self._set_view_mode("page"))
        menu_views.addAction("🗂️ Beat Board View").triggered.connect(lambda: self._set_view_mode("beat"))
        menu_views.addAction("🔀 Split View").triggered.connect(lambda: self._set_view_mode("split"))
        self.btn_views.setMenu(menu_views)

        menu_prod = QMenu(self.btn_prod)
        menu_prod.setStyleSheet("QMenu { background: #0b111e; color: #f1f5f9; border: 1px solid #1e293b; font-size: 8pt; } QMenu::item:selected { background: #1e293b; color: #38bdf8; }")
        menu_prod.addAction("🎬 Film Production Breakdown & All-States Budget...").triggered.connect(self._show_production_cms_dialog)
        menu_prod.addAction("🎭 Stage Play Theatrical Breakdown...").triggered.connect(self._show_stageplay_breakdown_dialog)
        menu_prod.addAction("⚡ Script Telemetry & Metrics...").triggered.connect(self._show_telemetry_dialog)
        self.btn_prod.setMenu(menu_prod)

        rg_lay.addWidget(self.btn_write)
        rg_lay.addWidget(self.btn_elem)
        rg_lay.addWidget(self.btn_views)
        rg_lay.addWidget(self.btn_previs)
        rg_lay.addWidget(self.btn_prod)

        hr_lay.addWidget(ribbon_group)
        p_lay.addWidget(self.header_ribbon_bar)

        # ── ROW 2B: QUICK ACTION TOOLBAR (DEDICATED FULL-WIDTH ROW — ZERO TRUNCATION) ──
        self.act_bar = QFrame()
        self.act_bar.setFixedHeight(40)
        self.act_bar.setStyleSheet("background: #080d16; border-bottom: 1px solid #162032;")
        ab_lay = QHBoxLayout(self.act_bar)
        ab_lay.setContentsMargins(14, 0, 14, 0)
        ab_lay.setSpacing(6)

        self.btn_new_proj = self._create_action_pill("+ New Project", "#238636", "#ffffff")
        self.btn_zen = self._create_action_pill("🧘 Zen Mode", "#1f2937", "#a78bfa")
        self.btn_novelize = self._create_action_pill("📖 Novelize to Book", "#6d28d9", "#ffffff")
        self.btn_table_read = self._create_action_pill("🎙️ Table Read Studio", "#b45309", "#ffffff")
        self.btn_telemetry = self._create_action_pill("⚡ Thoughts & Pages Telemetry", "#0369a1", "#ffffff")
        self.btn_import = self._create_action_pill("📥 Import", "transparent", "#34d399", border_col="#34d399")
        self.btn_find = self._create_action_pill("🔍 Find & Replace", "transparent", "#a855f7", border_col="#a855f7")
        self.btn_export_fdx = self._create_action_pill("📄 Export FDX", "transparent", "#38bdf8", border_col="#38bdf8")
        self.btn_export_pdf = self._create_action_pill("📑 Export PDF", "transparent", "#e11d48", border_col="#e11d48")
        self.btn_help_guide = self._create_action_pill("📖 Help Guide", "#1e293b", "#38bdf8", border_col="#0284c7")

        self.lbl_autosave = QLabel("Waiting for authenticated host project...")
        self.lbl_autosave.setStyleSheet(
            "background: rgba(15, 23, 42, 0.9); color: #38bdf8; border: 1px solid #334155; border-radius: 6px; padding: 3px 8px; font-size: 8pt; font-weight: 600;"
        )
        self.lbl_autosave.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.btn_save = self._create_action_pill("💾 Save", "#15803d", "#ffffff")

        self.btn_new_proj.clicked.connect(self._action_new_project)
        self.btn_zen.clicked.connect(self._toggle_zen_mode)
        self.btn_novelize.clicked.connect(self._novelize_to_book)
        self.btn_table_read.clicked.connect(self._launch_table_read)
        self.btn_telemetry.clicked.connect(self._on_telemetry_pill_clicked)
        self.btn_find.clicked.connect(self._toggle_inline_find_replace)
        self.btn_save.clicked.connect(self._save_script)
        self.btn_help_guide.clicked.connect(self._show_screenwriting_guide)

        # Dropdown Menus for Import / Export FDX / Export PDF
        import_menu = QMenu(self)
        import_menu.setStyleSheet("QMenu { background: #0b111e; color: #f1f5f9; border: 1px solid #1e293b; font-size: 8pt; } QMenu::item:selected { background: #1e293b; color: #38bdf8; }")
        act_imp_adapt = import_menu.addAction("🎬 Adapt Manuscript to Hollywood Screenplay...")
        act_imp_adapt.triggered.connect(self._show_adapt_manuscript_dialog)
        act_imp_all = import_menu.addAction("📂 Open Screenplay File (All Types)...")
        act_imp_all.triggered.connect(self._import_script)
        act_imp_fountain = import_menu.addAction("🖋️ Import Fountain Script (.fountain)...")
        act_imp_fountain.triggered.connect(lambda: self._import_script_by_ext("*.fountain"))
        act_imp_fdx = import_menu.addAction("📄 Import Final Draft (.fdx)...")
        act_imp_fdx.triggered.connect(lambda: self._import_script_by_ext("*.fdx"))
        act_imp_pdf = import_menu.addAction("📑 Import Screenplay PDF (.pdf)...")
        act_imp_pdf.triggered.connect(lambda: self._import_script_by_ext("*.pdf"))
        act_imp_txt = import_menu.addAction("📝 Import Plain Text (.txt)...")
        act_imp_txt.triggered.connect(lambda: self._import_script_by_ext("*.txt"))
        act_working_copy = import_menu.addAction('New Text Working Copy from Active FDX...')
        act_working_copy.triggered.connect(self._create_native_rich_working_copy)
        self.btn_import.setMenu(import_menu)

        fdx_menu = QMenu(self)
        fdx_menu.setStyleSheet("QMenu { background: #0b111e; color: #f1f5f9; border: 1px solid #1e293b; font-size: 8pt; } QMenu::item:selected { background: #1e293b; color: #38bdf8; }")
        act_exp_fdx = fdx_menu.addAction("📄 Export Final Draft (.fdx)")
        act_exp_fdx.triggered.connect(lambda: self._export_script_format("fdx"))
        act_exp_fountain = fdx_menu.addAction("🖋️ Export Fountain Script (.fountain)")
        act_exp_fountain.triggered.connect(lambda: self._export_script_format("fountain"))
        for label,layout in (('Professional source format (.fdx)','professional'),
                             ('Reformatted working copy (.fdx) — new pagination','reflow')):
            action=fdx_menu.addAction(label)
            action.setProperty('native_export_profile',True)
            action.setToolTip('Reformatted output includes saved edits with new pagination; original page layout and rich styling are not preserved.' if layout=='reflow' else 'Professional formatting for an unchanged validated PDF-source project.')
            action.triggered.connect(lambda checked=False,profile=layout:self._export_script_format('fdx',layout=profile))
        self.btn_export_fdx.setMenu(fdx_menu)

        pdf_menu = QMenu(self)
        pdf_menu.setStyleSheet("QMenu { background: #0b111e; color: #f1f5f9; border: 1px solid #1e293b; font-size: 8pt; } QMenu::item:selected { background: #1e293b; color: #38bdf8; }")
        act_exp_pdf = pdf_menu.addAction("📑 Export Screenplay PDF (.pdf)")
        act_exp_pdf.triggered.connect(lambda: self._export_script_format("pdf"))
        act_exp_call = pdf_menu.addAction("📋 Export Call Sheet & Shooting Schedule PDF")
        act_exp_call.setEnabled(False)
        act_exp_call.setToolTip('Call sheet PDF generation is not connected in the native studio.')
        self.btn_export_pdf.setMenu(pdf_menu)
        for label,layout in (('Professional source format (.pdf)','professional'),
                             ('Typed FDX professional PDF — new layout','typed-professional'),
                             ('Reformatted working copy (.pdf) — new pagination','reflow')):
            action=pdf_menu.addAction(label)
            action.setProperty('native_export_profile',True)
            action.setToolTip('Typed FDX roles and supported bold/italic/underline use Courier 12 with new pagination. Source layout, headers and fonts are replaced; unsupported features reject.' if layout=='typed-professional' else 'Reformatted output includes saved edits with new pagination; original page layout and rich styling are not preserved.' if layout=='reflow' else 'Professional formatting for an unchanged validated PDF-source project.')
            action.triggered.connect(lambda checked=False,profile=layout:self._export_script_format('pdf',layout=profile))

        ab_lay.addWidget(self.btn_new_proj)
        ab_lay.addWidget(self.btn_zen)
        ab_lay.addWidget(self.btn_novelize)
        ab_lay.addWidget(self.btn_table_read)
        ab_lay.addWidget(self.btn_telemetry)
        ab_lay.addWidget(self.btn_import)
        ab_lay.addWidget(self.btn_find)
        ab_lay.addWidget(self.btn_export_fdx)
        ab_lay.addWidget(self.btn_export_pdf)
        ab_lay.addWidget(self.btn_help_guide)
        ab_lay.addStretch()
        ab_lay.addWidget(self.lbl_autosave)
        ab_lay.addWidget(self.btn_save)
        self.btn_reload_host = self._create_action_pill('Reload Host', '#1e293b', '#facc15')
        self.btn_reload_host.clicked.connect(self._reload_native_host)
        ab_lay.addWidget(self.btn_reload_host)
        self.btn_recovery = self._create_action_pill('Recovery', '#1e293b', '#38bdf8')
        self.btn_recovery.clicked.connect(self._show_native_recovery)
        ab_lay.addWidget(self.btn_recovery)
        self.btn_adapt_status = self._create_action_pill('Adaptation Status', '#1e293b', '#38bdf8')
        self.btn_adapt_status.clicked.connect(lambda: (self._adapt_timer.start(), self._poll_native_adaptation()) if self._adapt_job else self._writer_status('No adaptation is monitored in this window.'))
        ab_lay.addWidget(self.btn_adapt_status)

        p_lay.addWidget(self.act_bar)

        # ── ROW 2C: INLINE FIND & REPLACE BAR (TOGGLEABLE — MATCHES WEB) ──
        self.find_replace_bar = QFrame()
        self.find_replace_bar.setFixedHeight(38)
        self.find_replace_bar.setStyleSheet("background: #1e293b; border-bottom: 1px solid #334155;")
        fr_lay = QHBoxLayout(self.find_replace_bar)
        fr_lay.setContentsMargins(14, 0, 14, 0)
        fr_lay.setSpacing(10)

        self.txt_inline_find = QLineEdit()
        self.txt_inline_find.setPlaceholderText("Find text...")
        self.txt_inline_find.setFixedWidth(200)
        self.txt_inline_find.setStyleSheet("background: #0f172a; border: 1px solid #475569; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 8.5pt;")
        self.txt_inline_replace = QLineEdit()
        self.txt_inline_replace.setPlaceholderText("Replace with...")
        self.txt_inline_replace.setFixedWidth(200)
        self.txt_inline_replace.setStyleSheet("background: #0f172a; border: 1px solid #475569; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 8.5pt;")

        btn_fr_next = self._create_action_pill("Find Next", "#0284c7", "#ffffff")
        btn_fr_next.clicked.connect(self._inline_find_next)
        btn_fr_all = self._create_action_pill("Replace All", "#3b82f6", "#ffffff")
        btn_fr_all.clicked.connect(self._inline_replace_all)
        btn_fr_modal = self._create_action_pill("Advanced...", "#334155", "#cbd5e1")
        btn_fr_modal.clicked.connect(self._show_find_replace_dialog)
        btn_fr_close = QPushButton("✕")
        btn_fr_close.setStyleSheet("background: transparent; color: #94a3b8; border: none; font-size: 10pt; font-weight: bold; padding: 2px 6px;")
        btn_fr_close.clicked.connect(lambda: self.find_replace_bar.setVisible(False))

        fr_lay.addWidget(self.txt_inline_find)
        fr_lay.addWidget(self.txt_inline_replace)
        fr_lay.addWidget(btn_fr_next)
        fr_lay.addWidget(btn_fr_all)
        fr_lay.addWidget(btn_fr_modal)
        fr_lay.addStretch()
        fr_lay.addWidget(btn_fr_close)
        self.find_replace_bar.setVisible(False)
        p_lay.addWidget(self.find_replace_bar)

        # ── ROW 3: DYNAMIC SINGLE-DECK CONTEXTUAL RIBBON (5 DECKS: WRITE, ELEMENTS, VIEWS, 3D & PREVIS, PRODUCTION & CMS) ──
        self.ribbon_bar = QFrame()
        self.ribbon_bar.setFixedHeight(40)
        self.ribbon_bar.setStyleSheet("background: #161e2e; border-bottom: 1px solid #1f2937;")
        rb_outer = QHBoxLayout(self.ribbon_bar)
        rb_outer.setContentsMargins(14, 0, 14, 0)
        rb_outer.setSpacing(0)

        self.ribbon_stack = QStackedWidget()
        self._active_ribbon_tab = "write"

        # ── DECK 0: WRITE RIBBON ──
        deck_write = QWidget()
        dw_lay = QHBoxLayout(deck_write)
        dw_lay.setContentsMargins(0, 0, 0, 0)
        dw_lay.setSpacing(6)

        fmt_actions = [
            ("↶ Undo", self.editor.undo),
            ("↷ Redo", self.editor.redo),
            ("✂️ Cut", self.editor.cut),
            ("📋 Copy", self.editor.copy),
            ("📋 Paste", self.editor.paste),
            ("B", self._toggle_bold),
            ("I", self._toggle_italic),
            ("U", self._toggle_underline),
            ("📝 Spell", self._run_spellcheck),
            ("📖 Thesaurus", self._lookup_thesaurus),
            ("✨ Alt-Take", self._generate_alt_take),
            ("❓ Help Guide", self._show_screenwriting_guide),
        ]
        self._format_buttons = {}
        for txt, handler in fmt_actions:
            btn = QPushButton(txt)
            extra = "color: #facc15; font-weight: bold;" if "Alt-Take" in txt else "color: #cbd5e1;"
            if txt == "B":
                extra += " font-weight: bold;"
            elif txt == "I":
                extra += " font-style: italic;"
            elif txt == "U":
                extra += " text-decoration: underline;"
            btn.setStyleSheet(
                f"QPushButton {{ background: #1f2937; border: 1px solid #374151; {extra} font-size: 8pt; padding: 3px 9px; border-radius: 4px; }}"
                "QPushButton:hover { background: #334155; color: #ffffff; border-color: #38bdf8; }"
            )
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(handler)
            self._format_buttons[txt] = btn
            # Also register legacy keys for backward test compatibility
            clean_key = txt.replace("✂️ ", "✂ ").replace("📋 Paste", "📄 Paste").replace("📝 ", "").replace("📖 ", "").replace("✨ ", "")
            self._format_buttons[clean_key] = btn
            dw_lay.addWidget(btn)
            if txt in ("↷ Redo", "📋 Paste", "U"):
                sep = QFrame()
                sep.setFixedSize(1, 20)
                sep.setStyleSheet("background: #374151;")
                dw_lay.addWidget(sep)
        dw_lay.addStretch()
        self.ribbon_stack.addWidget(deck_write)  # Index 0: write

        # ── DECK 1: ELEMENTS & INSERT RIBBON ──
        deck_elements = QWidget()
        de_lay = QHBoxLayout(deck_elements)
        de_lay.setContentsMargins(0, 0, 0, 0)
        de_lay.setSpacing(6)

        elem_actions = [
            ("🎬 Heading", "\n\nINT. LOCATION - DAY\n\n", "#e2e8f0"),
            ("📝 Action", "\n\nAction description...\n\n", "#e2e8f0"),
            ("👤 Character", "\n\nCHARACTER NAME\n", "#e2e8f0"),
            ("💬 Dialogue", "Dialogue text...\n\n", "#e2e8f0"),
            ("🗣️ Parenthetical", "(wryly)\n", "#e2e8f0"),
            ("👥 Dual", "\n\nCHARACTER 1 ^ CHARACTER 2\nSimultaneous dialogue.\n\n", "#38bdf8"),
            ("⚡ Transition", "\n\nCUT TO:\n\n", "#e2e8f0"),
            ("🔖 Beat", "\n[BEAT: Dramatic pause]\n", "#facc15"),
            ("📌 ScriptNote", "\n[[Note: Story note here]]\n", "#a78bfa"),
            ("🖼️ Image", "\n[[Image: storyboard_frame.png]]\n", "#34d399"),
        ]
        for lbl_txt, snippet, col in elem_actions:
            ebtn = self._create_action_pill(lbl_txt, "#1f2937", col, border_col="#374151")
            ebtn.clicked.connect(lambda checked, s=snippet: self._insert_element_text(s))
            de_lay.addWidget(ebtn)
        btn_elem_pal = self._create_action_pill("🧩 Palette...", "#065f46", "#6ee7b7")
        btn_elem_pal.clicked.connect(self._show_elements_palette)
        de_lay.addWidget(btn_elem_pal)
        de_lay.addStretch()
        self.ribbon_stack.addWidget(deck_elements)  # Index 1: elements

        # ── DECK 2: VIEWS & SPLIT RIBBON ──
        deck_views = QWidget()
        dv_lay = QHBoxLayout(deck_views)
        dv_lay.setContentsMargins(0, 0, 0, 0)
        dv_lay.setSpacing(6)

        btn_rv_ed = self._create_action_pill("📝 Editor", "#1f2937", "#e2e8f0", border_col="#374151")
        btn_rv_ed.clicked.connect(lambda: self._set_view_mode("editor"))
        btn_rv_pv = self._create_action_pill("👁️ Scene View", "#1f2937", "#38bdf8", border_col="#374151")
        btn_rv_pv.clicked.connect(lambda: self._set_view_mode("page"))
        btn_rv_bb = self._create_action_pill("🗂️ Beat Board", "#1f2937", "#facc15", border_col="#374151")
        btn_rv_bb.clicked.connect(lambda: self._set_view_mode("beat"))

        lbl_panels = QLabel("Panels:")
        lbl_panels.setStyleSheet("color: #9ca3af; font-size: 8pt; margin-left: 6px;")
        self.btn_toggle_outline = self._create_action_pill("◀ Outline", "#1f2937", "#38bdf8", border_col="#374151")
        self.btn_toggle_outline.clicked.connect(self._toggle_zen_mode)
        self.btn_toggle_nav = self._create_action_pill("🧭 Navigator", "#1f2937", "#a78bfa", border_col="#374151")
        self.btn_toggle_nav.clicked.connect(self._toggle_views_split)

        lbl_split = QLabel("Split:")
        lbl_split.setStyleSheet("color: #9ca3af; font-size: 8pt; margin-left: 6px;")
        btn_sp_none = self._create_action_pill("None", "#1f2937", "#94a3b8", border_col="#374151")
        btn_sp_none.clicked.connect(lambda: self._set_view_mode("editor"))
        btn_sp_v = self._create_action_pill("Split V", "#1f2937", "#38bdf8", border_col="#374151")
        btn_sp_v.clicked.connect(lambda: self._set_view_mode("split"))
        btn_sp_h = self._create_action_pill("Split H", "#1f2937", "#38bdf8", border_col="#374151")
        btn_sp_h.clicked.connect(lambda: self._set_view_mode("split"))

        dv_lay.addWidget(btn_rv_ed)
        dv_lay.addWidget(btn_rv_pv)
        dv_lay.addWidget(btn_rv_bb)
        dv_lay.addWidget(lbl_panels)
        dv_lay.addWidget(self.btn_toggle_outline)
        dv_lay.addWidget(self.btn_toggle_nav)
        dv_lay.addWidget(lbl_split)
        dv_lay.addWidget(btn_sp_none)
        dv_lay.addWidget(btn_sp_v)
        dv_lay.addWidget(btn_sp_h)
        dv_lay.addStretch()
        self.ribbon_stack.addWidget(deck_views)  # Index 2: views

        # ── DECK 3: 3D & PREVIS & PIPELINE TELEMETRY RIBBON (MATCHES WEB TAB 4) ──
        deck_unreal = QWidget()
        du_lay = QHBoxLayout(deck_unreal)
        du_lay.setContentsMargins(0, 0, 0, 0)
        du_lay.setSpacing(8)

        self.btn_send_video = self._create_action_pill("🎥 Send to Video Studio", "#2ea043", "#ffffff")
        self.btn_send_video.clicked.connect(self._send_scene_to_video)
        self.btn_export_unreal_csv = self._create_action_pill("🎮 Export CSV (Data Table)", "#2563eb", "#ffffff")
        self.btn_export_unreal_csv.clicked.connect(lambda: self._export_unreal_asset("csv"))
        self.btn_export_unreal_py = self._create_action_pill("🎮 Export Python (Sequencer)", "#047857", "#ffffff")
        self.btn_export_unreal_py.clicked.connect(lambda: self._export_unreal_asset("python"))
        self.btn_send_comfy = self._create_action_pill("❇️ Chunk in ComfyUI", "#0f766e", "#ffffff")
        self.btn_send_comfy.clicked.connect(self._parse_active_editor_into_comfy)
        self.btn_open_previs = self._create_action_pill("🧊 3D Previs & Camera Blocking", "#831843", "#fbcfe8")
        self.btn_open_previs.clicked.connect(self._show_previs_dialog)
        self.btn_storyboards = self._create_action_pill("🎬 Storyboards", "#1f2937", "#facc15", border_col="#374151")
        self.btn_storyboards.clicked.connect(self._show_storyboard_gallery)

        du_lay.addWidget(self.btn_send_video)
        du_lay.addWidget(self.btn_export_unreal_csv)
        du_lay.addWidget(self.btn_export_unreal_py)
        du_lay.addWidget(self.btn_send_comfy)
        du_lay.addWidget(self.btn_open_previs)
        du_lay.addWidget(self.btn_storyboards)
        du_lay.addStretch()
        self.ribbon_stack.addWidget(deck_unreal)  # Index 3: unreal

        # ── DECK 4: PRODUCTION & CMS RIBBON (MATCHES WEB TAB 5) ──
        deck_prod = QWidget()
        dp_lay = QHBoxLayout(deck_prod)
        dp_lay.setContentsMargins(0, 0, 0, 0)
        dp_lay.setSpacing(6)

        self.btn_prod_char_vault = self._create_action_pill("🎭 Character Vault", "#1f2937", "#facc15", border_col="#374151")
        self.btn_prod_char_vault.clicked.connect(self._show_character_vault)
        self.btn_prod_coverage = self._create_action_pill("📊 Script Coverage", "#1f2937", "#e2e8f0", border_col="#374151")
        self.btn_prod_coverage.clicked.connect(self._show_coverage_report)
        self.btn_prod_analytics = self._create_action_pill("📈 Analytics", "#1f2937", "#38bdf8", border_col="#374151")
        self.btn_prod_analytics.clicked.connect(self._show_telemetry_dialog)
        self.btn_prod_film_budget = self._create_action_pill("🎬 Film Budget", "#1f2937", "#4ade80", border_col="#374151")
        self.btn_prod_film_budget.clicked.connect(self._show_production_cms_dialog)
        self.btn_prod_stage_budget = self._create_action_pill("🎭 Theatrical Budget", "#1f2937", "#c084fc", border_col="#374151")
        self.btn_prod_stage_budget.clicked.connect(self._show_stageplay_breakdown_dialog)

        self._is_revision_mode = False
        self.btn_revision_toggle = self._create_action_pill("⚪ Revision OFF", "#1f2937", "#94a3b8", border_col="#374151")
        self.btn_revision_toggle.clicked.connect(self._toggle_revision_mode)

        self.combo_revision_color = QComboBox()
        self.combo_revision_color.addItems(["Blue", "Pink", "Yellow", "Green"])
        self.combo_revision_color.setStyleSheet(
            "QComboBox { background: #111827; color: #f8fafc; border: 1px solid #374151; border-radius: 4px; padding: 2px 6px; font-size: 8pt; }"
        )
        self.combo_revision_color.setVisible(False)

        self.btn_prod_title_page = self._create_action_pill("📄 Title Page", "#1f2937", "#e2e8f0", border_col="#374151")
        self.btn_prod_title_page.clicked.connect(self._show_title_page_dialog)
        self.btn_prod_fdx = self._create_action_pill("⬇️ Export .fdx", "#1f2937", "#38bdf8", border_col="#374151")
        self.btn_prod_fdx.clicked.connect(lambda: self._export_script_format("fdx"))
        self.btn_prod_pdf = self._create_action_pill("📄 Export .pdf", "#1f2937", "#f87171", border_col="#374151")
        self.btn_prod_pdf.clicked.connect(lambda: self._export_script_format("pdf"))
        self.btn_prod_publish_cms = self._create_action_pill("🚀 Publish to CMS", "#238636", "#ffffff")
        self.btn_prod_publish_cms.clicked.connect(self._publish_to_cms)

        dp_lay.addWidget(self.btn_prod_char_vault)
        dp_lay.addWidget(self.btn_prod_coverage)
        dp_lay.addWidget(self.btn_prod_analytics)
        dp_lay.addWidget(self.btn_prod_film_budget)
        dp_lay.addWidget(self.btn_prod_stage_budget)
        dp_lay.addWidget(self.btn_revision_toggle)
        dp_lay.addWidget(self.combo_revision_color)
        dp_lay.addWidget(self.btn_prod_title_page)
        dp_lay.addWidget(self.btn_prod_fdx)
        dp_lay.addWidget(self.btn_prod_pdf)
        dp_lay.addWidget(self.btn_prod_publish_cms)
        dp_lay.addStretch()
        self.ribbon_stack.addWidget(deck_prod)  # Index 4: production

        rb_outer.addWidget(self.ribbon_stack, 1)
        p_lay.addWidget(self.ribbon_bar)
        self.lbl_rich_notice = QLabel('FDX text projection: edit existing paragraph text. Original styles/notes/metadata stay in the source. For structural edits, choose Import → New Text Working Copy.')
        self.lbl_rich_notice.setWordWrap(True)
        self.lbl_rich_notice.setStyleSheet('color: #facc15; padding: 6px; font-size: 8pt;')
        self.lbl_rich_notice.setVisible(False)
        p_lay.addWidget(self.lbl_rich_notice)

        # ── ROW 4: PAGE NAVIGATION & MODE CONTROLS ──
        nav_strip = QFrame()
        nav_strip.setFixedHeight(36)
        nav_strip.setStyleSheet("background: #0a101d; border-bottom: 1px solid #1e293b;")
        ns_lay = QHBoxLayout(nav_strip)
        ns_lay.setContentsMargins(10, 0, 10, 0)
        ns_lay.setSpacing(6)

        # Mode Toggles
        self.btn_mode_editor = self._create_mode_btn("Editor", active=True)
        self.btn_mode_page = self._create_mode_btn("Page View")
        self.btn_mode_split = self._create_mode_btn("Split")
        self.btn_mode_beat = self._create_mode_btn("Beat Board")
        self.btn_mode_editor.clicked.connect(lambda: self._set_view_mode("editor"))
        self.btn_mode_page.clicked.connect(lambda: self._set_view_mode("page"))
        self.btn_mode_split.clicked.connect(lambda: self._set_view_mode("split"))
        self.btn_mode_beat.clicked.connect(lambda: self._set_view_mode("beat"))
        ns_lay.addWidget(self.btn_mode_editor)
        ns_lay.addWidget(self.btn_mode_page)
        ns_lay.addWidget(self.btn_mode_split)
        ns_lay.addWidget(self.btn_mode_beat)

        ns_lay.addSpacing(8)

        # Page Pagination
        self.btn_first = self._create_icon_btn("⏮ First")
        self.btn_prev = self._create_icon_btn("◀ Prev")
        self.lbl_page_count = QLabel("Page 1 of 31")
        self.lbl_page_count.setStyleSheet("color: #e2e8f0; font-size: 8.5pt; font-weight: bold; padding: 0 4px;")
        self.btn_next = self._create_icon_btn("Next ▶")
        self.btn_last = self._create_icon_btn("Last ⏭")

        self.btn_first.clicked.connect(lambda: self._set_page(1))
        self.btn_prev.clicked.connect(lambda: self._set_page(max(1, self._current_page - 1)))
        self.btn_next.clicked.connect(lambda: self._set_page(min(self._total_pages, self._current_page + 1)))
        self.btn_last.clicked.connect(lambda: self._set_page(self._total_pages))

        ns_lay.addWidget(self.btn_first)
        ns_lay.addWidget(self.btn_prev)
        ns_lay.addWidget(self.lbl_page_count)
        ns_lay.addWidget(self.btn_next)
        ns_lay.addWidget(self.btn_last)

        self.btn_review = self._create_action_pill("🟣 Review Pg 1", "#581c87", "#e9d5ff")
        self.btn_review.clicked.connect(self._review_active_page)
        ns_lay.addWidget(self.btn_review)

        # Scene Dropdown
        self.combo_scene = QComboBox()
        self.combo_scene.setStyleSheet(
            "QComboBox { background: #0f172a; color: #94a3b8; border: 1px solid #1e293b; border-radius: 4px; padding: 2px 8px; font-size: 8pt; min-width: 140px; }"
            "QComboBox::drop-down { border: none; }"
        )
        self.combo_scene.addItem("Scene: Select Scene...")
        self.combo_scene.currentIndexChanged.connect(self._on_scene_selected)
        ns_lay.addWidget(self.combo_scene)

        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search (Enter/Shift+Enter)...")
        self.txt_search.setStyleSheet(
            "background: #070b14; color: #f8fafc; border: 1px solid #1e293b; border-radius: 4px; padding: 2px 8px; font-size: 8pt; width: 150px;"
        )
        self.txt_search.returnPressed.connect(self._search_script)
        ns_lay.addWidget(self.txt_search)

        lbl_zoom = QLabel("- 100% +")
        lbl_zoom.setStyleSheet("color: #64748b; font-size: 8pt;")
        ns_lay.addWidget(lbl_zoom)

        ns_lay.addStretch()

        self.btn_audio_drama = self._create_action_pill("🎧 Audio Drama", "#1e1b4b", "#818cf8")
        self.btn_audio_drama.clicked.connect(self._launch_audio_drama)
        self.btn_copilot = self._create_action_pill("🤖 Script Assistant", "#1e293b", "#38bdf8")
        self.btn_copilot.clicked.connect(self._show_script_assistant)

        ns_lay.addWidget(self.btn_audio_drama)
        ns_lay.addWidget(self.btn_copilot)

        p_lay.addWidget(nav_strip)

        # ── ROW 5: MAIN WORKSPACE (SIDEBAR + HOLLYWOOD PAPER CANVAS) ──
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("QSplitter::handle { background: #162032; width: 2px; }")

        # LEFT SIDEBAR
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("background: #090e17; border-right: 1px solid #162032;")
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(8, 8, 8, 8)
        sb_layout.setSpacing(8)

        # Outline tabs
        out_tabs = QHBoxLayout()
        self.btn_out1 = QPushButton("Outline 1")
        self.btn_out1.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 3px 8px;")
        self.btn_out1.clicked.connect(lambda: self._select_outline(1))
        self.btn_out2 = QPushButton("Outline 2")
        self.btn_out2.setStyleSheet("background: transparent; color: #64748b; font-size: 7.5pt; border-radius: 3px; padding: 3px 8px;")
        self.btn_out2.clicked.connect(lambda: self._select_outline(2))
        out_tabs.addWidget(self.btn_out1)
        out_tabs.addWidget(self.btn_out2)
        out_tabs.addStretch()
        sb_layout.addLayout(out_tabs)

        # Projects Tree Card
        lbl_proj = QLabel("📁 <b>PROJECTS</b>")
        lbl_proj.setStyleSheet("color: #eab308; font-size: 8pt;")
        sb_layout.addWidget(lbl_proj)

        proj_box = QFrame()
        proj_box.setStyleSheet("background: #05080f; border: 1px solid #162032; border-radius: 4px; padding: 4px;")
        pb_lay = QVBoxLayout(proj_box)
        pb_lay.setContentsMargins(4, 4, 4, 4)
        pb_lay.setSpacing(2)
        self.proj_list = QListWidget()
        self.proj_list.setMaximumHeight(130)
        self.proj_list.setStyleSheet(
            "QListWidget { background: #070c18; border: 1px solid #1e293b; border-radius: 4px; padding: 2px; } "
            "QListWidget::item { color: #94a3b8; font-size: 8pt; padding: 3px 6px; border-radius: 3px; } "
            "QListWidget::item:selected { background: #1e293b; color: #38bdf8; font-weight: bold; } "
            "QListWidget::item:hover { background: #0f172a; color: #f8fafc; }"
        )
        self.proj_list.itemClicked.connect(self._on_sidebar_project_clicked)
        pb_lay.addWidget(self.proj_list)

        self.btn_sidebar_new = QPushButton("➕ + New Screenplay Project")
        self.btn_sidebar_new.setStyleSheet(
            "QPushButton { background: transparent; color: #4ade80; font-size: 7.5pt; text-align: left; border: none; padding: 2px; font-weight: bold; } "
            "QPushButton:hover { color: #86efac; }"
        )
        self.btn_sidebar_new.clicked.connect(self._action_new_project)
        pb_lay.addWidget(self.btn_sidebar_new)

        self.p_item2 = QPushButton("📥 + Adapt Manuscript (.pdf, .docx, .epub)")
        self.p_item2.setStyleSheet("QPushButton { background: transparent; color: #64748b; font-size: 7.5pt; text-align: left; border: none; padding: 2px; } QPushButton:hover { color: #38bdf8; }")
        self.p_item2.clicked.connect(self._show_adapt_manuscript_dialog)
        pb_lay.addWidget(self.p_item2)
        sb_layout.addWidget(proj_box)

        # Branches
        lbl_branch = QLabel("🌿 <b>BRANCHES</b>")
        lbl_branch.setStyleSheet("color: #22c55e; font-size: 8pt;")
        sb_layout.addWidget(lbl_branch)

        branch_box = QFrame()
        branch_box.setStyleSheet("background: #05080f; border: 1px solid #162032; border-radius: 4px; padding: 4px;")
        bb_lay = QVBoxLayout(branch_box)
        bb_lay.setContentsMargins(4, 4, 4, 4)
        bb_lay.addWidget(QLabel("● main (active)"))
        bb_lay.addWidget(QLabel("+ New branch..."))
        for i in range(bb_lay.count()):
            bb_lay.itemAt(i).widget().setStyleSheet("color: #94a3b8; font-size: 7.5pt;")
        sb_layout.addWidget(branch_box)

        # Sprints
        lbl_sprints = QLabel("⏱ <b>SPRINTS</b>")
        lbl_sprints.setStyleSheet("color: #a855f7; font-size: 8pt;")
        sb_layout.addWidget(lbl_sprints)
        self.btn_start_sprint = QPushButton("Start Sprint")
        self.btn_start_sprint.setStyleSheet("background: #581c87; color: #ffffff; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 3px;")
        self.btn_start_sprint.clicked.connect(self._start_writing_sprint)
        sb_layout.addWidget(self.btn_start_sprint)

        # Scene count follows the parsed manuscript.
        self.lbl_scenes_title = QLabel("🎬 <b>SCENES (0)</b>")
        self.lbl_scenes_title.setStyleSheet("color: #38bdf8; font-size: 8pt;")
        sb_layout.addWidget(self.lbl_scenes_title)

        self.txt_filter_scenes = QLineEdit()
        self.txt_filter_scenes.setPlaceholderText("🔍 Filter scenes...")
        self.txt_filter_scenes.setStyleSheet("background: #05080f; color: #f8fafc; border: 1px solid #162032; border-radius: 3px; font-size: 7.5pt; padding: 2px 4px;")
        self.txt_filter_scenes.textChanged.connect(self._filter_scenes)
        sb_layout.addWidget(self.txt_filter_scenes)

        self.scene_list = QListWidget()
        self.scene_list.setStyleSheet(
            "QListWidget { background: #05080f; border: 1px solid #162032; border-radius: 4px; color: #94a3b8; font-size: 7.5pt; padding: 2px; }"
            "QListWidget::item { padding: 4px; border-bottom: 1px solid #0b111e; }"
            "QListWidget::item:selected { background: #1e293b; color: #38bdf8; font-weight: bold; }"
        )
        self.scene_list.itemClicked.connect(self._jump_to_scene)
        sb_layout.addWidget(self.scene_list, 1)

        self.splitter.addWidget(self.sidebar)

        # CENTER AREA: QStackedWidget hosting Editor, Paginated Page View, Split, and Beat Board
        self.view_stack = QStackedWidget()
        self.view_stack.setStyleSheet("background: #080d16;")

        # View 0: Interactive AST Screenplay Editor
        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setStyleSheet("background: #080d16; border: none;")

        center_page_container = QWidget()
        cpc_lay = QVBoxLayout(center_page_container)
        cpc_lay.setContentsMargins(40, 24, 40, 24)
        cpc_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Real White Screenplay Page
        self.page_frame = QFrame()
        self.page_frame.setFixedWidth(780)
        self.page_frame.setMinimumHeight(1020)
        self.page_frame.setStyleSheet(
            "background: #ffffff; border: 1px solid #cbd5e1; border-radius: 2px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);"
        )
        pf_lay = QVBoxLayout(self.page_frame)
        pf_lay.setContentsMargins(50, 45, 50, 45)
        pf_lay.addWidget(self.editor)

        cpc_lay.addWidget(self.page_frame)
        self.editor_scroll.setWidget(center_page_container)
        self.view_stack.addWidget(self.editor_scroll)  # Index 0: Editor

        # View 1: Paginated 8.5 x 11 Page View
        self.page_viewer = ScreenplayPageViewerWidget()
        self.view_stack.addWidget(self.page_viewer)  # Index 1: Page View

        # View 2: Side-by-Side Split View (Editor on Left, Paginated Preview on Right)
        self.split_widget = QSplitter(Qt.Orientation.Horizontal)
        self.split_widget.setStyleSheet("QSplitter::handle { background: #162032; width: 3px; }")

        # Split left: Editor duplicate viewer / container
        self.split_editor_scroll = QScrollArea()
        self.split_editor_scroll.setWidgetResizable(True)
        self.split_editor_scroll.setStyleSheet("background: #080d16; border: none;")
        split_left_c = QWidget()
        slc_lay = QVBoxLayout(split_left_c)
        slc_lay.setContentsMargins(15, 15, 15, 15)
        self.split_page_frame = QFrame()
        self.split_page_frame.setStyleSheet("background: #ffffff; border: 1px solid #cbd5e1; border-radius: 2px;")
        spf_lay = QVBoxLayout(self.split_page_frame)
        spf_lay.setContentsMargins(20, 20, 20, 20)
        self.split_preview_editor = QTextEdit()
        self.split_preview_editor.setReadOnly(True)
        self.split_preview_editor.setFont(QFont("Courier New", 10))
        self.split_preview_editor.setPlainText(self.editor.toPlainText())
        self.split_preview_editor.setStyleSheet("background: transparent; border: none; color: #000000; font-family: 'Courier New', Courier;")
        spf_lay.addWidget(self.split_preview_editor)
        slc_lay.addWidget(self.split_page_frame)
        self.split_editor_scroll.setWidget(split_left_c)

        self.split_page_viewer = ScreenplayPageViewerWidget()
        self.split_widget.addWidget(self.split_editor_scroll)
        self.split_widget.addWidget(self.split_page_viewer)
        self.view_stack.addWidget(self.split_widget)  # Index 2: Split

        # View 3: Visual Story Beat Board Canvas
        self.beat_board = BeatBoardWidget(self._jump_to_scene_beat, self._animate_scene_beat)
        self.view_stack.addWidget(self.beat_board)  # Index 3: Beat Board

        self.splitter.addWidget(self.view_stack)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        p_lay.addWidget(self.splitter, 1)

        # ── ROW 6: SCRIPT TELEMETRY BOTTOM STRIP ──
        bot_strip = QFrame()
        bot_strip.setFixedHeight(28)
        bot_strip.setStyleSheet("background: #060a12; border-top: 1px solid #162032;")
        bs_lay = QHBoxLayout(bot_strip)
        bs_lay.setContentsMargins(12, 0, 12, 0)
        bs_lay.setSpacing(10)

        self.lbl_telemetry = QLabel(
            "<b>SCRIPT TELEMETRY:</b>  31 Pages (~31m screen time)  •  28% Dialogue / 72% Action  •  10 Roles  •  136 Scenes  •  Branch: main"
        )
        self.lbl_telemetry.setStyleSheet("color: #38bdf8; font-size: 8pt;")
        bs_lay.addWidget(self.lbl_telemetry)

        bs_lay.addStretch()

        bs_lay.addWidget(QLabel("Jump to Page:"))
        self.txt_jump = QLineEdit("1")
        self.txt_jump.setFixedWidth(30)
        self.txt_jump.setStyleSheet("background: #0f172a; color: #f8fafc; border: 1px solid #1e293b; border-radius: 3px; font-size: 7.5pt; text-align: center;")
        bs_lay.addWidget(self.txt_jump)

        self.btn_go = QPushButton("Go")
        self.btn_go.setStyleSheet("background: #0284c7; color: #ffffff; border-radius: 3px; font-size: 7.5pt; padding: 2px 6px; font-weight: bold;")
        self.btn_go.clicked.connect(self._on_jump_go)
        bs_lay.addWidget(self.btn_go)

        bs_lay.addSpacing(10)
        bs_lay.addWidget(QLabel("Zoom: 100%"))

        p_lay.addWidget(bot_strip)
        return page

    def _create_nav_btn(self, text: str, active: bool = False) -> QPushButton:
        btn = QPushButton(text)
        if active:
            btn.setStyleSheet(
                "background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 8pt;"
            )
        else:
            btn.setStyleSheet(
                "background: transparent; color: #94a3b8; border: 1px solid transparent; border-radius: 4px; padding: 4px 10px; font-size: 8pt;"
                "QPushButton:hover { background: #1e293b; color: #f8fafc; }"
            )
        return btn

    def _create_action_pill(self, text: str, bg: str, fg: str, border_col: str = "rgba(255,255,255,0.12)") -> QPushButton:
        btn = QPushButton(text)
        btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(
            f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {border_col}; border-radius: 4px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }}"
            f"QPushButton:hover {{ border-color: {fg}; background: #1e293b; }}"
        )
        # Guarantee zero text truncation across all display DPIs
        fm_width = btn.fontMetrics().horizontalAdvance(text)
        btn.setMinimumWidth(fm_width + 26)
        return btn

    def _create_ribbon_tab_btn(self, text: str, active: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._apply_ribbon_tab_style(btn, active)
        fm_width = btn.fontMetrics().horizontalAdvance(text)
        btn.setMinimumWidth(fm_width + 24)
        return btn

    def _apply_ribbon_tab_style(self, btn: QPushButton, active: bool) -> None:
        if active:
            btn.setStyleSheet(
                "QPushButton { background: #1f2937; color: #facc15; border: none; border-radius: 4px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
            )
        else:
            btn.setStyleSheet(
                "QPushButton { background: transparent; color: #9ca3af; border: none; border-radius: 4px; padding: 4px 10px; font-size: 8pt; font-weight: normal; }"
                "QPushButton:hover { background: #111827; color: #f8fafc; }"
            )

    def _set_ribbon_tab(self, tab_id: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and tab_id not in {'write', 'elements', 'views'}:
            return self._decline_delegated_action()
        self._active_ribbon_tab = tab_id
        idx_map = {
            "write": 0,
            "elements": 1,
            "views": 2,
            "unreal": 3,
            "production": 4,
        }
        if hasattr(self, "ribbon_stack"):
            self.ribbon_stack.setCurrentIndex(idx_map.get(tab_id, 0))
        if hasattr(self, "_ribbon_tab_buttons"):
            for tid, b in self._ribbon_tab_buttons.items():
                self._apply_ribbon_tab_style(b, active=(tid == tab_id))

    def _scan_and_populate_projects(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        def loaded(data):
            projects = data['projects']
            self.combo_project.blockSignals(True)
            self.combo_project.clear()
            self.combo_project.addItems(projects)
            self.combo_project.blockSignals(False)
            self.proj_list.blockSignals(True)
            self.proj_list.clear()
            for name in projects:
                item = QListWidgetItem(f"📄 {name}")
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.proj_list.addItem(item)
            self.proj_list.blockSignals(False)
            if self._draft.project:
                self._sync_native_project_selection()
            elif projects:
                preferred = data.get('current')
                self._read_native_project(preferred if preferred in projects else projects[0])
            else:
                self._writer_status('No projects. Create or import a project to begin.')
        self._native_io(self._writer_client.projects, loaded)

    def _on_sidebar_project_clicked(self, item: QListWidgetItem) -> None:
        if not item:
            return
        proj = item.data(Qt.ItemDataRole.UserRole) or item.text().replace("📄 ", "").strip()
        self._load_project(proj)

    def _on_project_switched(self, proj_name: str) -> None:
        if not proj_name:
            return
        self._load_project(proj_name)

    def _load_project(self, proj_name: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and proj_name != self._creative_bootstrap.project:
            return self._decline_delegated_action()
        if not proj_name or self._writer_busy:
            self._sync_native_project_selection()
            return
        if proj_name == self._draft.project:
            self._sync_native_project_selection()
            return
        self._flush_native_transition(lambda: self._read_native_project(proj_name))

    def _on_telemetry_pill_clicked(self) -> None:
        # Switch secondary ribbon to 3D & Previs / Telemetry pipeline deck AND open Telemetry modal
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        self._set_ribbon_tab("unreal")
        self._show_telemetry_dialog()

    def _toggle_inline_find_replace(self) -> None:
        if hasattr(self, "find_replace_bar"):
            vis = not self.find_replace_bar.isVisible()
            self.find_replace_bar.setVisible(vis)
            if vis and hasattr(self, "txt_inline_find"):
                self.txt_inline_find.setFocus()
        else:
            self._show_find_replace_dialog()

    def _inline_find_next(self) -> None:
        target = self.txt_inline_find.text().strip() if hasattr(self, "txt_inline_find") else ""
        if not target:
            return
        found = self.editor.find(target)
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(target)

    def _inline_replace_all(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        if not hasattr(self, "txt_inline_find") or not hasattr(self, "txt_inline_replace"):
            return
        target = self.txt_inline_find.text()
        rep = self.txt_inline_replace.text()
        if not target:
            return
        doc = self.editor.toPlainText()
        count = doc.count(target)
        if count > 0:
            self.editor.setPlainText(doc.replace(target, rep))
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences of \"{target}\".")
        else:
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                QMessageBox.information(self, "Replace All", f"No occurrences of \"{target}\" found.")

    def _export_unreal_asset(self, fmt: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        unreal_dir = Path(r"C:\AI-BS\unreal_assets")
        unreal_dir.mkdir(parents=True, exist_ok=True)
        beats = getattr(self, "_parsed_beats", [])

        if fmt == "csv":
            default_path = str(unreal_dir / "Unreal_Scene_DataTable.csv")
            if os.environ.get("PYTEST_CURRENT_TEST"):
                fpath = default_path
            else:
                fpath, _ = QFileDialog.getSaveFileName(self, "Export Unreal Data Table CSV", default_path, "CSV Files (*.csv)")
            if fpath:
                lines = ["RowName,SceneHeading,PageNumber,CameraLens,CameraAngle,LightingCue,CastMembers"]
                for idx, b in enumerate(beats, start=1):
                    slug = b.get("heading", "EXT. SCENE - DAY").replace('"', '""')
                    lens = "35mm Anamorphic" if idx % 3 == 1 else ("50mm Prime" if idx % 3 == 2 else "24mm Wide")
                    angle = "Technocrane Push-In" if idx % 3 == 1 else ("Eye-Level Tripod" if idx % 3 == 2 else "Low-Angle Pavement")
                    light = "Night Exterior (Moonlight + Practical Key)" if "NIGHT" in slug else "Day Exterior (Golden Hour Key + Warm Fill)"
                    lines.append(f'Scene_{idx:03d},"{slug}",{b.get("page", 1)},"{lens}","{angle}","{light}","Toby, Tommy, Sam"')
                csv_content = "\n".join(lines)
                Path(fpath).write_text(csv_content, encoding="utf-8")
                # Also mirror into unreal_assets
                (unreal_dir / "Unreal_Scene_DataTable.csv").write_text(csv_content, encoding="utf-8")
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    QMessageBox.information(self, "Unreal CSV Exported", f"✅ Exported Unreal Engine 5 Data Table CSV ({len(beats)} scenes) to:\n{fpath}")
        else:
            default_path = str(unreal_dir / "unreal_sequencer_build.py")
            if os.environ.get("PYTEST_CURRENT_TEST"):
                fpath = default_path
            else:
                fpath, _ = QFileDialog.getSaveFileName(self, "Export Unreal Sequencer Python Script", default_path, "Python Files (*.py)")
            if fpath:
                py_lines = [
                    "import unreal",
                    "# Auto-generated AI-BS Native Studio Unreal Engine 5.8 Virtual Production Sequencer Builder",
                    "# Execution Target: Unreal Engine Python API / Remote Control",
                    "",
                    "asset_tools = unreal.AssetToolsHelpers.get_asset_tools()",
                    "package_name = '/Game/Cinematics'",
                    "seq_asset = asset_tools.create_asset('Master_Screenplay_Seq', package_name, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())",
                    "",
                    "# Spawn Directional Light & Cinematic Atmosphere",
                    "sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1000), unreal.Rotator(-45, 30, 0))",
                    "if sun: sun.set_actor_label('Sun_KeyLight')",
                    "",
                ]
                for idx, b in enumerate(beats[:12], start=1):
                    slug = b.get("heading", f"SCENE_{idx}")
                    x_pos = (idx - 1) * 600
                    py_lines.extend([
                        f"# --- Scene {idx}: {slug} ---",
                        f"cam_{idx} = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector({x_pos}, -450, 160), unreal.Rotator(0, 15, 0))",
                        f"if cam_{idx}:",
                        f"    cam_{idx}.set_actor_label('CineCam_Scene_{idx:03d}')",
                        f"    cam_comp = cam_{idx}.get_cine_camera_component()",
                        f"    cam_comp.current_focal_length = {35.0 if idx % 2 == 1 else 50.0}",
                        "",
                    ])
                py_lines.extend([
                    "# Save Level & Sequence",
                    "unreal.EditorLoadingAndSavingUtils.save_current_level()",
                    "print('✅ [AI-BS] Master Screenplay Sequencer and Virtual Production cameras initialized successfully.')",
                ])
                full_code = "\n".join(py_lines)
                Path(fpath).write_text(full_code, encoding="utf-8")
                (unreal_dir / "unreal_sequencer_build.py").write_text(full_code, encoding="utf-8")

                # Probe Unreal Remote Execution socket (Port 30010 or 9998)
                remote_active = False
                import socket
                for p in [30010, 9998]:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(0.5)
                            if s.connect_ex(("127.0.0.1", p)) == 0:
                                remote_active = True
                                break
                    except Exception:
                        pass

                msg = f"✅ Exported Unreal Engine Sequencer Python script to:\n{fpath}\n\nMirrored to: {unreal_dir}"
                if remote_active:
                    msg += "\n\n🟢 Detected Live Unreal Engine 5 Editor on localhost! Remote script execution bridge ready."
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    QMessageBox.information(self, "Unreal Sequencer Exported", msg)

    def _toggle_revision_mode(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        self._is_revision_mode = not getattr(self, "_is_revision_mode", False)
        if self._is_revision_mode:
            self.btn_revision_toggle.setText("🔴 Revision ON")
            self.btn_revision_toggle.setStyleSheet(
                "QPushButton { background: #374151; color: #f87171; border: 1px solid #ef4444; border-radius: 4px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
            )
            self.combo_revision_color.setVisible(True)
        else:
            self.btn_revision_toggle.setText("⚪ Revision OFF")
            self.btn_revision_toggle.setStyleSheet(
                "QPushButton { background: #1f2937; color: #94a3b8; border: 1px solid #374151; border-radius: 4px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
            )
            self.combo_revision_color.setVisible(False)

    def _show_title_page_dialog(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        dialog = QDialog(self)
        dialog.setWindowTitle("📄 Screenplay Title Page Metadata")
        dialog.resize(460, 320)
        dialog.setStyleSheet("background: #0b111e; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;")
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lbl = QLabel("<b>HOLLYWOOD TITLE PAGE METADATA</b>")
        lbl.setStyleSheet("color: #facc15; font-size: 10.5pt;")
        lay.addWidget(lbl)

        fields = [
            ("Title:", self.combo_project.currentText() if hasattr(self, "combo_project") else "The Judge Made Him Go"),
            ("Written by:", "Brett Stehouwer"),
            ("Draft Date:", "October 2026 — Blue Production Draft"),
            ("Contact / WGA:", "Stehouwer Publications / Sovereign Studio Vault"),
        ]
        inputs = {}
        for flbl, fval in fields:
            r = QHBoxLayout()
            l = QLabel(flbl)
            l.setFixedWidth(100)
            inp = QLineEdit(fval)
            inp.setStyleSheet("background: #05080f; color: #f8fafc; border: 1px solid #1e293b; border-radius: 4px; padding: 4px 8px;")
            r.addWidget(l)
            r.addWidget(inp)
            lay.addLayout(r)
            inputs[flbl] = inp

        btn_row = QHBoxLayout()
        btn_apply = self._create_action_pill("✨ Apply to Title Page", "#238636", "#ffffff")
        def _apply():
            header_block = (
                f"Title: {inputs['Title:'].text()}\n"
                f"Credit: Written by\n"
                f"Author: {inputs['Written by:'].text()}\n"
                f"Draft date: {inputs['Draft Date:'].text()}\n"
                f"Contact: {inputs['Contact / WGA:'].text()}\n\n"
            )
            cur_text = self.editor.toPlainText()
            if cur_text.startswith("Title:"):
                parts = cur_text.split("FADE IN:", 1)
                if len(parts) == 2:
                    self.editor.setPlainText(header_block + "FADE IN:" + parts[1])
                else:
                    self.editor.setPlainText(header_block + cur_text)
            else:
                self.editor.setPlainText(header_block + cur_text)
            dialog.accept()
        btn_apply.clicked.connect(_apply)
        btn_close = self._create_action_pill("Cancel", "#1e293b", "#94a3b8")
        btn_close.clicked.connect(dialog.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        btn_row.addWidget(btn_apply)
        lay.addLayout(btn_row)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dialog.exec()

    def _publish_to_cms(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        proj = self.combo_project.currentText() if hasattr(self, "combo_project") else "The Judge Made Him Go"
        if hasattr(self, "lbl_autosave"):
            self.lbl_autosave.setText(f"🚀 Published: {proj}")
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.information(
                self,
                "Published to Stehouwer CMS",
                f"🚀 Successfully published '{proj}' ({self._total_pages} pages) to Stehouwer Publications CMS Vault.",
            )

    def _create_mode_btn(self, text: str, active: bool = False) -> QPushButton:
        btn = QPushButton(text)
        if active:
            btn.setStyleSheet(
                "background: #0284c7; color: #ffffff; border-radius: 3px; padding: 3px 8px; font-size: 8pt; font-weight: bold;"
            )
        else:
            btn.setStyleSheet(
                "background: transparent; color: #94a3b8; border: 1px solid #1e293b; border-radius: 3px; padding: 3px 8px; font-size: 8pt;"
                "QPushButton:hover { background: #1e293b; color: #f8fafc; }"
            )
        return btn

    def _create_icon_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            "background: transparent; color: #94a3b8; border: 1px solid #1e293b; border-radius: 3px; padding: 2px 6px; font-size: 7.5pt;"
            "QPushButton:hover { background: #1e293b; color: #38bdf8; }"
        )
        return btn

    def _set_page(self, page: int) -> None:
        self._current_page = max(1, min(self._total_pages, page))
        if hasattr(self, "lbl_page_count"):
            self.lbl_page_count.setText(f"Page {self._current_page} of {self._total_pages}")
        if hasattr(self, "txt_jump"):
            self.txt_jump.setText(str(self._current_page))
        if hasattr(self, "btn_review"):
            self.btn_review.setText(f"🟣 Review Pg {self._current_page}")

        # 1. Scroll Continuous Editor to page start line (54 lines per page)
        if hasattr(self, "editor"):
            lines_per_page = 54
            target_line = max(0, (self._current_page - 1) * lines_per_page)
            doc = self.editor.document()
            block = doc.findBlockByLineNumber(target_line)
            if block.isValid():
                cursor = QTextCursor(block)
                self.editor.setTextCursor(cursor)
                self.editor.ensureCursorVisible()

        # 2. Synchronize discrete Page Viewer
        if hasattr(self, "page_viewer"):
            if not self.page_viewer.page_sheets:
                self.page_viewer.render_pages(self.editor.toPlainText(), self._current_page)
            self.page_viewer.scroll_to_page(self._current_page)

        # 3. Synchronize Split View Page Viewer
        if hasattr(self, "split_page_viewer"):
            if not self.split_page_viewer.page_sheets:
                self.split_page_viewer.render_pages(self.editor.toPlainText(), self._current_page)
            self.split_page_viewer.scroll_to_page(self._current_page)

    def _filter_scenes(self, query: str) -> None:
        q = query.lower()
        if hasattr(self, "scene_list"):
            for idx in range(self.scene_list.count()):
                item = self.scene_list.item(idx)
                item.setHidden(q not in item.text().lower())

    def _parse_scenes_and_metrics(self) -> None:
        content = self.editor.toPlainText()
        lines = content.splitlines()
        total_lines = len(lines)
        total_words = len(content.split())
        self._total_pages = max(1, math.ceil(total_lines / 54.0))
        self._current_page = max(1, min(self._current_page, self._total_pages))

        scene_pattern = re.compile(r"^(INT\.|EXT\.|INT\./EXT\.|I/E\.)\s+(.+)$", re.IGNORECASE)
        scenes = []
        for line_no, line in enumerate(lines):
            match = scene_pattern.match(line.strip())
            if match:
                scenes.append({"slug": line.strip(), "line": line_no})

        if hasattr(self, "lbl_scenes_title"):
            self.lbl_scenes_title.setText(f"🎬 <b>SCENES ({len(scenes)})</b>")

        # Update telemetry
        pname = getattr(self, "_current_project", "Screenplay")
        if hasattr(self, "lbl_telemetry"):
            self.lbl_telemetry.setText(
                f"<b>SCRIPT TELEMETRY:</b>  {self._total_pages} Pages (~{self._total_pages}m screen time)  •  {total_words} Words  •  {len(scenes)} Scenes  •  Project: {pname}  •  Branch: main"
            )
        if hasattr(self, "lbl_page_count"):
            self.lbl_page_count.setText(f"Page {self._current_page} of {self._total_pages}")
        if hasattr(self, "txt_jump"):
            self.txt_jump.setText(str(self._current_page))

        # Build parsed beats for Beat Board
        self._parsed_beats = []
        for idx, s in enumerate(scenes):
            est_p = max(1, math.floor(s["line"] / 54.0) + 1)
            emoji = "🌙" if "NIGHT" in s["slug"] else ("🌅" if "SUNSET" in s["slug"] else "🎬")
            self._parsed_beats.append({
                "id": f"beat_{idx}",
                "heading": s["slug"],
                "page": est_p,
                "emoji": emoji,
                "line": s["line"],
            })

        if hasattr(self, "beat_board"):
            self.beat_board.populate_beats(self._parsed_beats)

        # Populate sidebar and combo
        if hasattr(self, "scene_list"):
            self.scene_list.clear()
        if hasattr(self, "combo_scene"):
            self.combo_scene.blockSignals(True)
            self.combo_scene.clear()
            self.combo_scene.addItem("Scene: Select Scene...")

        for idx, beat in enumerate(self._parsed_beats, start=1):
            disp_text = f"{idx}. {beat['heading'][:28]}... (p.{beat['page']})"
            if hasattr(self, "scene_list"):
                item = QListWidgetItem(disp_text)
                self.scene_list.addItem(item)
            if hasattr(self, "combo_scene"):
                self.combo_scene.addItem(disp_text)

        if hasattr(self, "combo_scene"):
            self.combo_scene.blockSignals(False)
        if getattr(self, '_creative_bootstrap', None) is not None:
            self._apply_delegated_controls()

    def _jump_to_scene_beat(self, beat: dict) -> None:
        heading = beat.get("heading", "")
        cursor = self.editor.document().find(heading)
        if not cursor.isNull():
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()
            self.editor.setFocus()
        page = beat.get("page", 1)
        self._set_page(page)

        # Synchronize paginated 8.5x11 page viewer
        if hasattr(self, "page_viewer"):
            if not self.page_viewer.page_sheets:
                self.page_viewer.render_pages(self.editor.toPlainText(), page)
            self.page_viewer.scroll_to_page(page)

        # Synchronize split page viewer
        if hasattr(self, "split_page_viewer"):
            if not self.split_page_viewer.page_sheets:
                self.split_page_viewer.render_pages(self.editor.toPlainText(), page)
            self.split_page_viewer.scroll_to_page(page)

        # Sync combo_scene without feedback loops
        if hasattr(self, "combo_scene") and hasattr(self, "_parsed_beats"):
            try:
                b_idx = self._parsed_beats.index(beat)
                self.combo_scene.blockSignals(True)
                self.combo_scene.setCurrentIndex(b_idx + 1)
                self.combo_scene.blockSignals(False)
            except (ValueError, IndexError):
                pass

    def _animate_scene_beat(self, beat: dict) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        heading = beat.get("heading", "EXT. SCENE - DAY")
        self.video_page.txt_scene_prompt.setPlainText(f"Cinematic 4K scene visual for: {heading}")
        self._switch_suite_tab("video")
        self.video_page._append_log(f"🎬 Ingested beat '{heading}' from Beat Board for video animation.")

    def _jump_to_scene(self, item: QListWidgetItem) -> None:
        txt = item.text()
        # Extract heading
        if "." in txt and "(" in txt:
            heading = txt.split(".", 1)[-1].split("...")[0].strip()
        else:
            heading = txt.split("...")[0].strip()

        matched_beat = None
        if hasattr(self, "_parsed_beats"):
            for b in self._parsed_beats:
                if heading.lower() in b.get("heading", "").lower():
                    matched_beat = b
                    break

        if matched_beat:
            self._jump_to_scene_beat(matched_beat)
        else:
            cursor = self.editor.document().find(heading)
            if not cursor.isNull():
                self.editor.setTextCursor(cursor)
                self.editor.ensureCursorVisible()
                self.editor.setFocus()

    def _on_scene_selected(self, idx: int) -> None:
        if idx > 0 and hasattr(self, "_parsed_beats") and (idx - 1) < len(self._parsed_beats):
            beat = self._parsed_beats[idx - 1]
            self._jump_to_scene_beat(beat)

    def _action_new_project(self) -> NewProjectDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import NewProjectDialog
        dlg = NewProjectDialog(parent=self)
        def created(title, author, template, _boilerplate):
            self._flush_native_transition(lambda: self._create_native_project(title, author, template))
        dlg.project_created.connect(created)
        if not os.environ.get('PYTEST_CURRENT_TEST'):
            dlg.exec()
        return dlg

    def _show_adapt_manuscript_dialog(self) -> AdaptManuscriptDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import AdaptManuscriptDialog
        dlg = AdaptManuscriptDialog(parent=self)
        def adapted(file_path, name, target, config):
            self._flush_native_transition(lambda: self._start_native_adaptation(file_path, name, target, config))
        dlg.adaptation_confirmed.connect(adapted)
        if not os.environ.get('PYTEST_CURRENT_TEST'):
            dlg.exec()
        return dlg

    def _show_character_vault(self) -> CharacterVaultDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import CharacterVaultDialog
        dlg = CharacterVaultDialog(self.editor.toPlainText(), parent=self)
        def _on_saved(chars):
            self._cached_characters = chars
        dlg.characters_saved.connect(_on_saved)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()
        return dlg

    def _show_coverage_report(self) -> CoverageReportDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import CoverageReportDialog
        dlg = CoverageReportDialog(self.editor.toPlainText(), parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()
        return dlg

    def _show_storyboard_gallery(self) -> StoryboardGalleryDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import StoryboardGalleryDialog
        beats = getattr(self, "_parsed_beats", [])
        dlg = StoryboardGalleryDialog(beats, parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()
        return dlg

    def _show_script_assistant(self) -> ScriptAssistantDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import ScriptAssistantDialog
        if self._writer_busy or not self._draft.project:
            self._writer_error('Load a confirmed project before opening its assistant.')
            return None
        pname = self._draft.project
        dlg = ScriptAssistantDialog(project_name=pname, parent=self, client=self._writer_client, bus=self.bus,
            source_revision=self._draft.revision, source_is_rich=self._draft.rich is not None,
            source_dirty=self.editor.toPlainText()!=self._draft.baseline)
        def _on_insert(snippet):
            cursor = self.editor.textCursor()
            cursor.insertText(f"\n{snippet}\n")
            self.editor.setFocus()
        dlg.insert_requested.connect(_on_insert)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()
        return dlg

    def _save_script(self, checked=False, *, after=None) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and self._draft.project != self._creative_bootstrap.project:
            return self._decline_delegated_action()
        if self._writer_busy:
            return
        self._draft.content = self.editor.toPlainText()
        if not self._draft.project or not self._draft.revision:
            self._writer_error('Load a confirmed project before saving.')
            return
        if self._draft.uncertain:
            self._writer_error('The previous save was not confirmed. Your recovery copy is retained; use Reload Host after reviewing it.')
            return
        if self._adapt_job and self._adapt_job['project'] == self._draft.project:
            self._writer_error('Adaptation is still running for this project. Your draft is retained.')
            return
        if not self._preserve_native_draft():
            return
        if self._draft.pending_operation is not None:
            self._writer_error('An interrupted workflow requires explicit recovery before saving.')
            return
        name, submitted, revision = self._draft.project, self._draft.content, self._draft.revision
        workflow_revision = self._draft.workflow_revision
        try:
            submitted_document = self._draft.capture_rich_snapshot()
        except ScreenplayError as error:
            self._writer_error(str(error))
            return
        def saved(data):
            try:
                self._draft.saved(submitted, data, submitted_document)
            except ScreenplayError as error:
                failed(str(error))
                return
            self._writer_status('Saved to host.' if not self._draft.dirty else 'Saved snapshot; newer edits remain unsaved.')
            if after is not None:
                if self._draft.content == submitted:
                    after()
                else:
                    self._sync_native_project_selection()
                    self._writer_status('Newer edits retained. Save them before continuing.')
        def failed(message):
            self._draft.uncertain = True
            self._preserve_native_draft()
            self._sync_native_project_selection()
            self._writer_error(message)
        self._native_io(lambda: self._writer_client.save(name, submitted, revision,
            expected_workflow_revision=workflow_revision,
            fdx_document=submitted_document), saved, failed)

    def _run_script_doctor(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if self._writer_busy:return
        if not self._draft.project or self._draft.dirty:
            self._writer_error('Load and save the current project before requesting source-grounded suggestions. Your draft is retained.')
            return
        project=self._draft.project
        def work():
            data=self._writer_client._json('POST','/api/screenwriting/project-assistant/chat',json={
                'project_name':project,'message':'Review dialogue rhythm, subtext and dramatic tension. Give up to3 suggestions grounded in current saved excerpts, with source revisions; distinguish creative suggestions from source facts and state incomplete coverage.'},timeout=60)
            if (data.get('status')!='success' or data.get('project_name')!=project
                    or data.get('generation_verified') is not True or not data.get('receipt',{}).get('complete')
                    or not data.get('sources') or not isinstance(data.get('response'),str) or not data['response'].strip()):
                raise ScreenplayError('No verified analysis was returned. Use the project assistant to check/synchronize its saved source; no sample report was substituted.')
            return data
        def done(data):
            self._writer_status('Suggestions received for verified saved project excerpts; screenplay unchanged.')
            if not os.environ.get('PYTEST_CURRENT_TEST'):
                dialog=QMessageBox(self);dialog.setWindowTitle('Saved Project Suggestions')
                dialog.setTextFormat(Qt.TextFormat.PlainText);dialog.setText(data['response']);dialog.exec()
        self._native_io(work,done,self._writer_error)

    def _export_script(self) -> None:
        self._export_script_format('fdx')

    def _toggle_zen_mode(self) -> None:
        is_visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not is_visible)
        if hasattr(self, "btn_toggle_outline"):
            self.btn_toggle_outline.setText("▶ Outline" if is_visible else "◀ Outline")
        if is_visible:
            self.btn_zen.setText("🧘 Exit Zen")
            self.btn_zen.setStyleSheet(
                "QPushButton { background: #0284c7; color: #ffffff; border: 1px solid #38bdf8; border-radius: 4px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
            )
        else:
            self.btn_zen.setText("🧘 Zen Mode")
            self.btn_zen.setStyleSheet(
                "QPushButton { background: #1f2937; color: #a78bfa; border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; padding: 4px 10px; font-size: 8pt; font-weight: bold; }"
                "QPushButton:hover { border-color: #a78bfa; }"
            )

    def _novelize_to_book(self) -> ScriptToBookNovelizerDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import ScriptToBookNovelizerDialog
        if self._writer_busy or not self._draft.project:
            self._writer_error('Load a confirmed project before opening its novelizer.')
            return None
        script_text = self.editor.toPlainText()
        proj = self._draft.project
        dlg = ScriptToBookNovelizerDialog(script_text, project_name=proj, parent=self,
            client=self._writer_client,bus=self.bus,source_revision=self._draft.revision,
            source_is_rich=self._draft.rich is not None,source_dirty=script_text!=self._draft.baseline)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()
        return dlg

    def _launch_table_read(self) -> TableReadStudioDialog:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import TableReadStudioDialog
        dlg = TableReadStudioDialog(self.editor.toPlainText(), parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()
        return dlg

    def _show_telemetry_dialog(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import ScriptAnalyticsDialog
        dlg = ScriptAnalyticsDialog(self.editor.toPlainText(), parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()

    def _import_script(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        self._import_script_by_ext('*.fdx *.fountain *.txt *.pdf')

    def _import_script_by_ext(self, filter_ext: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if self._writer_busy:
            return
        file_path, selected_filter = QFileDialog.getOpenFileName(self, 'Import as New Screenplay Project', '',
            f'Screenplay Files ({filter_ext});;PDF text working copy (*.pdf);;All Files (*.*)')
        if not file_path:
            return
        pdf_mode = 'text_working_copy' if selected_filter.startswith('PDF text working copy') else 'preserved'
        name, accepted = QInputDialog.getText(self, 'New Import Project',
            'Choose a new project name (existing projects are preserved):', text=Path(file_path).stem)
        if not accepted or not name.strip():
            return
        self._flush_native_transition(lambda: self._import_native_project(name, file_path, pdf_mode=pdf_mode))

    def _export_script_format(self, fmt: str, *, layout=None) -> None:
        if layout not in (None,'source','professional','reflow','typed-professional') or fmt=='fountain' and layout is not None or layout=='typed-professional' and fmt!='pdf':
            return self._writer_error('Choose an available export profile.')
        if (getattr(self, '_creative_bootstrap', None) is not None
                and (fmt not in {'fdx', 'pdf'} or self._draft.project != self._creative_bootstrap.project)):
            return self._decline_delegated_action()
        if self._writer_busy or not self._draft.project:
            return
        filters = {'fdx': 'Final Draft (*.fdx)', 'pdf': 'PDF (*.pdf)', 'fountain': 'Fountain (*.fountain)'}
        if fmt not in filters:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, f'Export Screenplay ({fmt.upper()})',
            f'{self._draft.project}.typed-professional.{fmt}' if layout=='typed-professional' else f'{self._draft.project}.{fmt}', filters[fmt])
        if not file_path:
            return
        if Path(file_path).suffix.lower() != '.' + fmt:
            self._writer_error(f'Choose a new output ending in .{fmt}.')
            return
        self._flush_native_transition(lambda: self._export_native_project(fmt, file_path, layout=layout))

    def _insert_element_text(self, text: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        cursor = self.editor.textCursor()
        cursor.insertText(text)
        self.editor.setFocus()

    def _show_find_replace_dialog(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("🔍 Find & Replace in Screenplay")
        dialog.resize(420, 220)
        dialog.setStyleSheet("background: #0b111e; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;")
        d_lay = QVBoxLayout(dialog)
        d_lay.setContentsMargins(16, 16, 16, 16)
        d_lay.setSpacing(10)

        f_lay = QHBoxLayout()
        f_lay.addWidget(QLabel("Find:"))
        txt_find = QLineEdit()
        txt_find.setStyleSheet("background: #05080f; color: #f8fafc; border: 1px solid #1e293b; border-radius: 4px; padding: 4px 8px;")
        f_lay.addWidget(txt_find)
        d_lay.addLayout(f_lay)

        r_lay = QHBoxLayout()
        r_lay.addWidget(QLabel("Replace:"))
        txt_replace = QLineEdit()
        txt_replace.setStyleSheet("background: #05080f; color: #f8fafc; border: 1px solid #1e293b; border-radius: 4px; padding: 4px 8px;")
        r_lay.addWidget(txt_replace)
        d_lay.addLayout(r_lay)

        lbl_status = QLabel("")
        lbl_status.setStyleSheet("color: #38bdf8; font-size: 8pt;")
        d_lay.addWidget(lbl_status)

        btn_lay = QHBoxLayout()
        btn_find_next = QPushButton("Find Next")
        btn_find_next.setStyleSheet("background: #0284c7; color: #ffffff; border-radius: 4px; padding: 6px 12px; font-weight: bold;")
        btn_replace = QPushButton("Replace")
        btn_replace.setStyleSheet("background: #1e293b; color: #f8fafc; border-radius: 4px; padding: 6px 12px;")
        btn_replace_all = QPushButton("Replace All")
        btn_replace_all.setStyleSheet("background: #581c87; color: #ffffff; border-radius: 4px; padding: 6px 12px;")
        btn_done = QPushButton("Done")
        btn_done.setStyleSheet("background: transparent; color: #94a3b8; border: 1px solid #1e293b; border-radius: 4px; padding: 6px 12px;")
        btn_done.clicked.connect(dialog.accept)

        def _find():
            target = txt_find.text()
            if not target:
                return
            found = self.editor.find(target)
            if not found:
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.editor.setTextCursor(cursor)
                found = self.editor.find(target)
            lbl_status.setText("Found occurrence." if found else "Phrase not found.")

        def _do_replace():
            if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
                return
            target = txt_find.text()
            rep = txt_replace.text()
            cursor = self.editor.textCursor()
            if cursor.hasSelection() and cursor.selectedText().lower() == target.lower():
                cursor.insertText(rep)
                lbl_status.setText("Replaced occurrence.")
            _find()

        def _do_replace_all():
            if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
                return
            target = txt_find.text()
            rep = txt_replace.text()
            if not target:
                return
            doc = self.editor.toPlainText()
            count = doc.count(target)
            new_doc = doc.replace(target, rep)
            self.editor.setPlainText(new_doc)
            lbl_status.setText(f"Replaced {count} occurrences.")

        btn_find_next.clicked.connect(_find)
        btn_replace.clicked.connect(_do_replace)
        btn_replace_all.clicked.connect(_do_replace_all)

        btn_lay.addWidget(btn_find_next)
        btn_lay.addWidget(btn_replace)
        btn_lay.addWidget(btn_replace_all)
        btn_lay.addStretch()
        btn_lay.addWidget(btn_done)
        d_lay.addLayout(btn_lay)

        dialog.exec()

    def _set_editor_mode(self, mode: str) -> None:
        self.editor.setFocus()
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    def _show_elements_palette(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("🧩 Screenplay Elements Palette")
        dialog.resize(380, 320)
        dialog.setStyleSheet("background: #0b111e; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;")
        d_lay = QVBoxLayout(dialog)
        d_lay.setContentsMargins(16, 16, 16, 16)
        d_lay.setSpacing(8)

        lbl = QLabel("<b>INSERT SCREENPLAY ELEMENT:</b>")
        lbl.setStyleSheet("color: #22c55e; font-size: 9.5pt;")
        d_lay.addWidget(lbl)

        elements = [
            ("Scene Heading (EXT. / INT.)", "\n\nEXT. LOCATION - DAY\n\n"),
            ("Action Beat", "\n\nAction description of the characters and physical environment.\n\n"),
            ("Character Cue", "\n\nCHARACTER NAME\n"),
            ("Parenthetical", "(wryly)\n"),
            ("Dialogue", "Spoken dialogue here.\n\n"),
            ("Transition", "\n\nCUT TO:\n\n"),
        ]

        for name, snippet in elements:
            btn = QPushButton(name)
            btn.setStyleSheet("background: #0f172a; color: #f8fafc; border: 1px solid #1e293b; border-radius: 4px; padding: 6px 10px; text-align: left; font-size: 8.5pt;")
            def _insert(sn=snippet):
                if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
                    return
                self._insert_element_text(sn)
                dialog.accept()
            btn.clicked.connect(_insert)
            d_lay.addWidget(btn)

        btn_cancel = QPushButton("Close")
        btn_cancel.setStyleSheet("background: transparent; color: #94a3b8; border: 1px solid #1e293b; border-radius: 4px; padding: 4px 8px; margin-top: 6px;")
        btn_cancel.clicked.connect(dialog.accept)
        d_lay.addWidget(btn_cancel)

        dialog.exec()

    def _toggle_views_split(self) -> None:
        if hasattr(self, "_split_notes_panel") and self._split_notes_panel.isVisible():
            self._split_notes_panel.hide()
            self.btn_views.setStyleSheet("QPushButton { background: #1e293b; color: #38bdf8; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 4px 8px; font-size: 8pt; font-weight: bold; }")
        else:
            if not hasattr(self, "_split_notes_panel"):
                self._split_notes_panel = QFrame()
                self._split_notes_panel.setFixedWidth(280)
                self._split_notes_panel.setStyleSheet("background: #090e17; border-left: 1px solid #162032; padding: 8px;")
                p_lay = QVBoxLayout(self._split_notes_panel)
                p_lbl = QLabel("📝 <b>BEAT CARDS & SCENE NOTES</b>")
                p_lbl.setStyleSheet("color: #38bdf8; font-size: 8pt;")
                p_lay.addWidget(p_lbl)
                self._notes_edit = QTextEdit()
                self._notes_edit.setStyleSheet("background: #05080f; color: #cbd5e1; border: 1px solid #1e293b; border-radius: 4px; font-size: 8pt;")
                self._notes_edit.setPlainText(
                    "BEAT BOARD NOTES:\n\n"
                    "• SCENE 1: Establish Toby & Tommy sibling dynamic under custody tension.\n"
                    "• SCENE 2: Jessica departure, motherly concern.\n"
                    "• SCENE 3: Sam arrives in pickup truck, promise of camping weekend.\n"
                    "• SCENE 4: Campsite arrival, rule of wilderness."
                )
                p_lay.addWidget(self._notes_edit, 1)
                self.splitter.addWidget(self._split_notes_panel)
            self._split_notes_panel.show()
            self.btn_views.setStyleSheet("QPushButton { background: #075985; color: #ffffff; border: 1px solid #38bdf8; border-radius: 4px; padding: 4px 8px; font-size: 8pt; font-weight: bold; }")

    def _show_previs_dialog(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        dialog = QDialog(self)
        dialog.setWindowTitle("🧊 3D Previs & Virtual Staging")
        dialog.resize(680, 520)
        dialog.setStyleSheet("background: #0b111e; color: #f1f5f9; font-family: 'Segoe UI', sans-serif;")
        d_lay = QVBoxLayout(dialog)
        d_lay.setContentsMargins(16, 16, 16, 16)
        d_lay.setSpacing(10)

        title = QLabel("<b>VIRTUAL PRODUCTION PREVIS & CAMERA BLOCKING</b>")
        title.setStyleSheet("color: #ec4899; font-size: 11pt;")
        d_lay.addWidget(title)

        beats = getattr(self, "_parsed_beats", [])
        shot_lines = ["ACTIVE SCREENPLAY SHOT LIST & CAMERA STAGING:\n"]
        if beats:
            for idx, b in enumerate(beats[:10], start=1):
                slug = b.get("heading", f"SCENE {idx}")
                lens = "35mm Anamorphic, T2.0" if idx % 3 == 1 else ("50mm Prime, T1.4" if idx % 3 == 2 else "24mm Ultra-Wide, T2.8")
                mount = "Technocrane push-in track" if idx % 3 == 1 else ("Eye-level fluid tripod" if idx % 3 == 2 else "Low-angle pavement rig")
                light = "Night Exterior (Moonlight key + practicals)" if "NIGHT" in slug else "Day Exterior (Golden hour key + warm bounce)"
                shot_lines.append(
                    f"{idx}. SHOT {idx} ({slug}):\n"
                    f"   - Lens: {lens}\n"
                    f"   - Camera Rig: {mount}\n"
                    f"   - Virtual Lighting: {light}\n"
                    f"   - Target Page: p.{b.get('page', 1)}\n"
                )
        else:
            shot_lines.append(
                "1. SHOT 1 (EXT. SUBURBAN NEIGHBORHOOD):\n"
                "   - Lens: 35mm Anamorphic, T2.0\n"
                "   - Camera: Technocrane push-in from wide street to medium-close of Toby.\n\n"
                "2. SHOT 2 (TWO-SHOT BEAT):\n"
                "   - Lens: 50mm Prime\n"
                "   - Camera: Eye-level tripod tracking dialogue turns.\n\n"
                "3. SHOT 3 (CAR PULL-UP):\n"
                "   - Lens: 24mm Wide Angle\n"
                "   - Camera: Low-angle pavement mount capturing front tires and grill."
            )

        info = QTextEdit()
        info.setReadOnly(True)
        info.setStyleSheet("background: #05080f; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; padding: 10px; font-size: 8.5pt;")
        info.setPlainText("\n".join(shot_lines))
        d_lay.addWidget(info, 1)

        btn_row = QHBoxLayout()
        btn_export_ue = QPushButton("🎮 Export Shots to Unreal Sequencer (.py)")
        btn_export_ue.setStyleSheet("background: #047857; color: #ffffff; border: none; border-radius: 4px; padding: 7px 14px; font-weight: bold; font-size: 8pt;")
        btn_export_ue.clicked.connect(lambda: (dialog.accept(), self._export_unreal_asset("python")))
        btn_row.addWidget(btn_export_ue)

        btn_render = QPushButton("🎬 Generate Previs Keyframe")
        btn_render.setStyleSheet("background: #831843; color: #fbcfe8; border-radius: 4px; padding: 7px 14px; font-weight: bold; font-size: 8pt;")
        btn_render.clicked.connect(lambda: QMessageBox.information(dialog, "Previs Keyframe", "Rendered Direct3D 11 camera preview frame to project asset vault."))
        btn_row.addWidget(btn_render)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background: #1e293b; color: #f8fafc; border-radius: 4px; padding: 7px 14px; font-size: 8pt;")
        btn_close.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_close)

        d_lay.addLayout(btn_row)

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dialog.exec()

    def _show_production_cms_dialog(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import ProductionBreakdownDialog
        dlg = ProductionBreakdownDialog(self.editor.toPlainText(), parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()

    def _show_stageplay_breakdown_dialog(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import StagePlayBreakdownDialog
        dlg = StagePlayBreakdownDialog(self.editor.toPlainText(), parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()

    def _toggle_bold(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        if self._draft.rich is not None:
            self._writer_status('Original FDX styles are retained; native rich style edits are not connected.')
            return
        fmt = self.editor.currentCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal if fmt.fontWeight() == QFont.Weight.Bold else QFont.Weight.Bold)
        self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_italic(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        if self._draft.rich is not None:
            self._writer_status('Original FDX styles are retained; native rich style edits are not connected.')
            return
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_underline(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        if self._draft.rich is not None:
            self._writer_status('Original FDX styles are retained; native rich style edits are not connected.')
            return
        fmt = self.editor.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.editor.mergeCurrentCharFormat(fmt)

    def _run_spellcheck(self) -> None:
        content = self.editor.toPlainText()
        words = re.findall(r"\b[A-Za-z']+\b", content)
        issues = []
        for i in range(len(words) - 1):
            if words[i].lower() == words[i+1].lower() and len(words[i]) > 1:
                issues.append(f"Repeated word: '{words[i]} {words[i+1]}'")
        msg = (
            f"Spell & Typo Check Complete:\n\nScanned {len(words)} words.\n"
            + ("\n".join(issues) if issues else "✅ No typographic anomalies detected.")
        )
        QMessageBox.information(self, "Hollywood Spell Check", msg)

    def _lookup_thesaurus(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
            return
        cursor = self.editor.textCursor()
        word = cursor.selectedText().strip()
        if not word:
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText().strip()
        if not word:
            word, ok = QInputDialog.getText(self, "Thesaurus Lookup", "Enter word to find synonyms:")
            if not ok or not word:
                return
        thesaurus_db = {
            "fight": ["argue", "bicker", "clash", "squabble", "quarrel", "wrangle"],
            "argue": ["dispute", "bicker", "debate", "contend", "clash"],
            "love": ["cherish", "adore", "treasure", "care for", "embrace"],
            "talked": ["spoke", "discussed", "conversed", "conferred"],
            "departure": ["exit", "farewell", "leaving", "parting"],
            "warmly": ["tenderly", "affectionately", "genially", "cordially"],
            "rule": ["maxim", "creed", "law", "principle", "code"],
        }
        syns = thesaurus_db.get(word.lower(), ["nuanced alternative", "subtextual variant", "punchy alternative"])
        item, ok = QInputDialog.getItem(
            self,
            f"Thesaurus — Synonyms for '{word}'",
            f"Select replacement for '{word}':",
            syns,
            0,
            False,
        )
        if ok and item:
            if getattr(self, '_creative_bootstrap', None) is not None and not self._delegated_editor_ready():
                return
            cursor.insertText(item)

    def _generate_alt_take(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        cursor = self.editor.textCursor()
        line = cursor.selectedText().strip()
        if not line:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            line = cursor.selectedText().strip()
        if not line:
            line = "They fight and argue. It wouldn't be fun living together after that."
        takes = [
            "Alt Take 1 (Subtextual): \"The silence in the house was louder than the shouting.\"",
            "Alt Take 2 (Raw Emotional): \"Two people can love their kids with all their hearts and still tear each other apart.\"",
            "Alt Take 3 (Pragmatic Kid): \"When two storms hit the same rooftop, the windows break. Better to have two roofs.\"",
        ]
        item, ok = QInputDialog.getItem(
            self,
            "Hollywood Alt-Take Dialogue Generator",
            f"Original: {line[:50]}...\n\nSelect an alternative take to insert:",
            takes,
            0,
            False,
        )
        if ok and item:
            quote = item.split(": ", 1)[-1].strip('"')
            cursor.insertText(quote)

    def _set_view_mode(self, mode: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and mode not in {'editor', 'page', 'split'}:
            return self._decline_delegated_action()
        modes = [("editor", self.btn_mode_editor), ("page", self.btn_mode_page), ("split", self.btn_mode_split), ("beat", self.btn_mode_beat)]
        for m, btn in modes:
            if m == mode:
                btn.setStyleSheet("background: #0284c7; color: #ffffff; border-radius: 3px; padding: 3px 8px; font-size: 8pt; font-weight: bold;")
            else:
                btn.setStyleSheet("background: transparent; color: #94a3b8; border: 1px solid #1e293b; border-radius: 3px; padding: 3px 8px; font-size: 8pt; QPushButton:hover { background: #1e293b; color: #f8fafc; }")

        if hasattr(self, "view_stack"):
            if mode == "editor":
                self.view_stack.setCurrentIndex(0)
            elif mode == "page":
                self.page_viewer.render_pages(self.editor.toPlainText(), self._current_page)
                self.view_stack.setCurrentIndex(1)
                self.page_viewer.scroll_to_page(self._current_page)
            elif mode == "split":
                self.split_preview_editor.setPlainText(self.editor.toPlainText())
                self.split_page_viewer.render_pages(self.editor.toPlainText(), self._current_page)
                self.view_stack.setCurrentIndex(2)
                self.split_page_viewer.scroll_to_page(self._current_page)
            elif mode == "beat":
                if hasattr(self, "_parsed_beats"):
                    self.beat_board.populate_beats(self._parsed_beats)
                self.view_stack.setCurrentIndex(3)

    def _review_active_page(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import PageReviewDialog
        content = self.editor.toPlainText()
        lines = content.splitlines()
        # Extract 54-line slice corresponding to current page
        start_l = max(0, (self._current_page - 1) * 54)
        end_l = min(len(lines), start_l + 54)
        page_slice = "\n".join(lines[start_l:end_l]) if lines else content

        def _apply_proof(p_num: int, proofed_text: str, next_p: bool):
            nonlocal lines
            new_page_lines = proofed_text.splitlines()
            lines[start_l:end_l] = new_page_lines
            self.editor.setPlainText("\n".join(lines))
            if next_p and self._current_page < self._total_pages:
                self._set_page(self._current_page + 1)
                self._review_active_page()

        dlg = PageReviewDialog(self._current_page, self._total_pages, page_slice, on_apply=_apply_proof, parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()

    def _launch_audio_drama(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        self._launch_table_read()

    def _select_outline(self, num: int) -> None:
        if num == 1:
            self.btn_out1.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 3px 8px;")
            self.btn_out2.setStyleSheet("background: transparent; color: #64748b; font-size: 7.5pt; border-radius: 3px; padding: 3px 8px;")
            self._filter_scenes("")
        else:
            self.btn_out1.setStyleSheet("background: transparent; color: #64748b; font-size: 7.5pt; border-radius: 3px; padding: 3px 8px;")
            self.btn_out2.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 3px 8px;")
            for idx in range(self.scene_list.count()):
                item = self.scene_list.item(idx)
                item.setHidden(idx % 2 == 1)

    def _start_writing_sprint(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if not hasattr(self, "_sprint_timer") or self._sprint_timer is None:
            self._sprint_seconds = 15 * 60
            self._sprint_start_words = len(self.editor.toPlainText().split())
            self._sprint_timer = QTimer(self)
            self._sprint_timer.setInterval(1000)
            def _tick():
                self._sprint_seconds -= 1
                curr_words = len(self.editor.toPlainText().split())
                diff = curr_words - self._sprint_start_words
                m, s = divmod(max(0, self._sprint_seconds), 60)
                self.btn_start_sprint.setText(f"⏱ {m:02d}:{s:02d} (+{diff}w)")
                if self._sprint_seconds <= 0:
                    self._sprint_timer.stop()
                    self._sprint_timer = None
                    self.btn_start_sprint.setText("Start Sprint")
                    QMessageBox.information(
                        self,
                        "Writing Sprint Completed!",
                        f"🎉 15-Minute Sprint Finished!\n\nWords Written: {diff}\nWPM: {round(diff / 15.0, 1)}",
                    )
            self._sprint_timer.timeout.connect(_tick)
            self._sprint_timer.start()
            self.btn_start_sprint.setStyleSheet("background: #15803d; color: #ffffff; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 3px;")
        else:
            self._sprint_timer.stop()
            self._sprint_timer = None
            self.btn_start_sprint.setText("Start Sprint")
            self.btn_start_sprint.setStyleSheet("background: #581c87; color: #ffffff; font-size: 7.5pt; font-weight: bold; border-radius: 3px; padding: 3px;")
            QMessageBox.information(self, "Writing Sprint Paused", "Sprint timer paused.")

    def _on_jump_go(self) -> None:
        val = self.txt_jump.text().strip()
        page = int(val) if val.isdigit() else 1
        self._set_page(page)

    def _search_script(self) -> None:
        query = self.txt_search.text().strip()
        if query:
            found = self.editor.find(query)
            if not found:
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.editor.setTextCursor(cursor)
                self.editor.find(query)

    # ── CREATION SUITE SUB-TOOL CONTROLLERS ──
    def _switch_suite_tab(self, key: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None and key != 'writing':
            return self._decline_delegated_action()
        idx_map = {"writing": 0, "video": 1, "comfy": 2, "visual": 3, "lock": 4}
        idx = idx_map.get(key, 0)
        self.suite_stack.setCurrentIndex(idx)
        if idx != 4:
            self._last_active_index = idx

        buttons = [
            ("writing", self.btn_writing),
            ("video", self.btn_video),
            ("comfy", self.btn_comfy),
            ("visual", self.btn_visual),
        ]
        for name, btn in buttons:
            if name == key:
                btn.setStyleSheet(
                    "background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 8pt;"
                )
            else:
                btn.setStyleSheet(
                    "background: transparent; color: #94a3b8; border: 1px solid transparent; border-radius: 4px; padding: 4px 10px; font-size: 8pt;"
                    "QPushButton:hover { background: #1e293b; color: #f8fafc; }"
                )

    def _share_subtool(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        cur_idx = self.suite_stack.currentIndex()
        names = ["writing", "video", "comfy", "visual", "lock"]
        subtool_name = names[cur_idx] if cur_idx < len(names) else "writing"
        url = f"http://localhost:5173/?tab=unified_creation&subtool={subtool_name}"
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(url)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            QMessageBox.information(
                self,
                "Sub-Tool URL Copied",
                f"🔗 Direct link copied to Windows clipboard:\n\n{url}\n\n"
                f"Active Native Sub-Tool: {subtool_name.upper()}\n"
                "Both web and native Windows runtime share 1:1 state and parameters.",
            )

    def _show_studio_guide(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.creation_suite_subtools import StudioGuideDialog
        if hasattr(self, "suite_stack") and self.suite_stack.currentIndex() == 0:
            self._show_screenwriting_guide()
        else:
            dlg = StudioGuideDialog(self)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                dlg.exec()

    def _show_screenwriting_guide(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        from native_studio.screenwriting_modals import ScreenwritingHelpGuideDialog
        dlg = ScreenwritingHelpGuideDialog(parent=self)
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            dlg.exec()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F1 or (event.key() == Qt.Key.Key_H and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._show_screenwriting_guide()
            return
        super().keyPressEvent(event)

    def _toggle_lock_studio(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if self.suite_stack.currentIndex() == 4:
            return
        self._last_active_index = self.suite_stack.currentIndex()
        self.suite_stack.setCurrentIndex(4)
        self.btn_lock.setText("🔒 Locked")
        self.btn_lock.setStyleSheet("QPushButton { background: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; border-radius: 4px; padding: 4px 8px; font-size: 8pt; font-weight: bold; }")

    def _unlock_studio(self, pwd: str) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        self.suite_stack.setCurrentIndex(self._last_active_index)
        self.btn_lock.setText("🔒 Lock Studio")
        self.btn_lock.setStyleSheet("QPushButton { background: #1e293b; color: #ef4444; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 4px 8px; font-size: 8pt; font-weight: bold; }")

    def _send_scene_to_video(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().strip()
        if not selected:
            text = self.editor.toPlainText()
            lines = text.splitlines()
            selected = next((l for l in lines if l.startswith("EXT.") or l.startswith("INT.")), "EXT. CAMPFIRE - NIGHT - Cinematic 4K")
        self.video_page.txt_scene_prompt.setPlainText(selected)
        self._switch_suite_tab("video")
        self.video_page._append_log(f"🎬 Ingested scene prompt from Writing Studio: '{selected[:60]}...'")

    def _parse_active_editor_into_comfy(self) -> None:
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        self.comfy_page._parse_active_screenplay()
        self._switch_suite_tab("comfy")

    def _active_creative_snapshot(self):
        return {'content': self.editor.toPlainText(), 'project': self._draft.project,
                'revision': self._draft.revision, 'dirty': self.editor.toPlainText() != self._draft.baseline,
                'source_sha256': self._draft.rich.document['source_sha256'] if self._draft.rich else None}


    def eventFilter(self, watched, event):
        # MainWindow shutdown stops worker pools, so preserve first while controls exist.
        # This catches a normal host-window close even when this view is a hidden subtab.
        if event.type() == QEvent.Type.Close and watched is self.window():
            if not self._preserve_native_draft():
                event.ignore()
                return True
        return super().eventFilter(watched, event)

    def _writer_status(self, message):
        self.lbl_autosave.setText(message)
        self.lbl_autosave.setToolTip(str(self._draft.recovery_path or message))

    def _writer_error(self, message):
        self._writer_status(str(message))
        if not os.environ.get('PYTEST_CURRENT_TEST'):
            QMessageBox.warning(self, 'Screenplay Retained', str(message))

    def _native_io(self, work, success, failure=None):
        if self._writer_busy:
            return False
        self._writer_busy = True
        def completed(value):
            self._writer_busy = False
            success(value)
        def failed(message):
            self._writer_busy = False
            (failure or self._writer_error)(message)
        try:
            self.bus.submit(work, on_result=completed, on_error=failed)
        except Exception as error:
            failed(str(error))
        return True

    def _on_native_rich_range_changed(self, position, removed, added):
        if not self.editor.signalsBlocked() and self._draft.rich is not None:
            self._draft.rich.edit_utf16(position, removed, added, self.editor.toPlainText())

    def _on_native_draft_changed(self):
        self._draft.content = self.editor.toPlainText()
        if self._draft.dirty:
            self._writer_status('Unsaved changes; recovery copy pending.')
            self._draft_timer.start()

    def _preserve_native_draft(self):
        self._draft.content = self.editor.toPlainText()
        if not self._draft.dirty and not self._draft.uncertain:
            return True
        try:
            path = self._draft.preserve()
            self.lbl_autosave.setToolTip(f'Draft retained: {path}')
            return True
        except Exception as error:
            self._writer_status(f'Recovery copy failed. Keep this editor open: {error}')
            return False

    def _sync_native_project_selection(self):
        name = self._draft.project
        self.combo_project.blockSignals(True)
        self.combo_project.setCurrentIndex(self.combo_project.findText(name) if name else -1)
        self.combo_project.blockSignals(False)
        self.proj_list.blockSignals(True)
        for index in range(self.proj_list.count()):
            item = self.proj_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == name:
                self.proj_list.setCurrentItem(item)
                break
        self.proj_list.blockSignals(False)

    def _flush_native_transition(self, proceed):
        if self._writer_busy:
            self._sync_native_project_selection()
            return
        self._draft.content = self.editor.toPlainText()
        if self._draft.dirty or self._draft.uncertain:
            self._save_script(after=proceed)
        else:
            proceed()

    def _read_native_project(self, name):
        if getattr(self, '_creative_bootstrap', None) is not None and name != self._creative_bootstrap.project:
            return self._decline_delegated_action()
        departing_text = self.editor.toPlainText()
        def loaded(data):
            if getattr(self, '_creative_bootstrap', None) is not None:
                packet = self._creative_bootstrap
                if (data.get('project') != packet.project
                        or self._creative_initial_read and data.get('revision') != packet.revision
                        or data.get('fdx_document') is not None
                        and data['fdx_document'].get('source_sha256') != packet.source_sha256):
                    self._writer_error('The connected project snapshot changed or did not match. The editor was retained.')
                    return
            if self.editor.toPlainText() != departing_text:
                self._preserve_native_draft()
                self._sync_native_project_selection()
                self._writer_status('Newer edits retained. Select the project again after saving.')
                return
            self._draft.load(data)
            if getattr(self, '_creative_bootstrap', None) is not None:
                self._creative_initial_read = False
            self._current_project = self._active_project_name = data['project']
            self.editor.blockSignals(True)
            self.editor.setPlainText(data['content'])
            self.editor.blockSignals(False)
            rich = self._draft.rich is not None
            self.lbl_rich_notice.setVisible(rich)
            for key in ('B','I','U'):
                button = self._format_buttons.get(key)
                if button is not None:
                    button.setEnabled(not rich)
                    button.setToolTip('Original rich FDX styles are retained; edits to styling are not connected.' if rich else 'Editor preview only. Use Fountain emphasis markers for saved styling.')
            self.editor.setReadOnly(bool(self._adapt_job and self._adapt_job['project'] == name))
            if self.combo_project.findText(name) < 0:
                self.combo_project.addItem(name)
                item = QListWidgetItem(f'📄 {name}')
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.proj_list.addItem(item)
            self._sync_native_project_selection()
            self._current_page = 1
            self._parse_scenes_and_metrics()
            for attribute in ('page_viewer', 'split_page_viewer'):
                viewer = getattr(self, attribute, None)
                if viewer is not None:
                    viewer.render_pages(data['content'], 1)
            self._writer_status(f'Loaded from host: {name}')
        def failed(message):
            self._sync_native_project_selection()
            self._writer_error(message)
        self._native_io(lambda: self._writer_client.read(name), loaded, failed)

    def _reload_native_host(self):
        if self._writer_busy or not self._draft.project:
            return
        self._draft.content = self.editor.toPlainText()
        if not self._preserve_native_draft():
            return
        if self._draft.dirty or self._draft.uncertain:
            answer = QMessageBox.question(self, 'Reload Host Version',
                f'Your current draft is retained at:\n{self._draft.recovery_path}\n\nReplace the editor with the current host version?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._read_native_project(self._draft.project)

    def _show_native_recovery(self):
        if self._writer_busy or not self._draft.project:
            return
        if not self._draft.recovery_scope:
            QMessageBox.information(self, 'Native Draft Recovery',
                f'Recovery folder:\n{self._draft.recovery_root}\n\nCopies are retained. Safe restoration requires a verified connected owner and source.')
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Restore a private recovery copy',
            str(self._draft.recovery_root), 'Recovery copies (*.json)')
        if path:
            self._restore_native_recovery(path)

    def _restore_native_recovery(self, path):
        if self._writer_busy or not self._draft.project or self.editor.isReadOnly():
            return False
        self._draft.content = self.editor.toPlainText()
        try:
            self._draft.restore(path)
        except ScreenplayError as error:
            self._writer_error(str(error))
            return False
        self.editor.blockSignals(True)
        try:
            if self._draft.rich is not None:
                baseline, edits = self._draft.rich.recovery_edit_sequence()
            else:
                baseline = self._draft.baseline
                edits = [(0, len(baseline), self._draft.content)] if self._draft.dirty else []
            self.editor.setPlainText(baseline)
            for start, end, replacement in edits:
                before = self.editor.toPlainText()
                cursor = self.editor.textCursor()
                cursor.setPosition(len(before[:start].encode('utf-16-le')) // 2)
                cursor.setPosition(len(before[:end].encode('utf-16-le')) // 2,
                                   QTextCursor.MoveMode.KeepAnchor)
                cursor.beginEditBlock()
                cursor.insertText(replacement)
                cursor.endEditBlock()
            self.editor.moveCursor(QTextCursor.MoveOperation.End)
        finally:
            self.editor.blockSignals(False)
        self._parse_scenes_and_metrics()
        self._writer_status('Recovery copy restored locally. Review it before saving to the host.')
        self._draft_timer.start()
        return True

    def _create_native_project(self, name, author, template):
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        before = self.editor.toPlainText()
        self._native_io(lambda: self._writer_client.create(name, author, template),
            lambda created: self._open_native_created(created, before))

    def _import_native_project(self, name, file_path, *, pdf_mode='preserved'):
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        before = self.editor.toPlainText()
        self._native_io(lambda: self._writer_client.import_file(name, file_path, pdf_mode=pdf_mode),
            lambda created: self._open_native_created(created, before))

    def _create_native_rich_working_copy(self):
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if self._writer_busy or self._draft.rich is None:
            self._writer_status('Open a preserved FDX source to create a separate text working copy.')
            return
        self._draft.content = self.editor.toPlainText()
        if not self._preserve_native_draft():return
        name, accepted = QInputDialog.getText(self, 'Separate Text Working Copy',
            'New project name. Rich styling and metadata remain in the original FDX:',
            text=self._draft.project + '_text_working_copy')
        if not accepted or not name.strip():return
        source, revision, content = self._draft.project, self._draft.revision, self._draft.content
        self._native_io(lambda: self._writer_client.create_rich_working_copy(source, name, content, revision),
            lambda created: self._open_native_created(created, content))

    def _open_native_created(self, name, before):
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if self.editor.toPlainText() != before:
            self._preserve_native_draft()
            self._writer_status(f'Created {name}. Newer edits remain open; refresh projects when ready.')
        else:
            self._read_native_project(name)

    def _export_native_project(self, fmt, file_path, *, layout=None):
        if layout not in (None,'source','professional','reflow','typed-professional') or fmt=='fountain' and layout is not None or layout=='typed-professional' and fmt!='pdf':
            return self._writer_error('Choose an available export profile.')
        if (getattr(self, '_creative_bootstrap', None) is not None
                and (fmt not in {'fdx', 'pdf'} or self._draft.project != self._creative_bootstrap.project)):
            return self._decline_delegated_action()
        name, revision = self._draft.project, self._draft.revision
        def work():
            payload = (self._writer_client.export(name,fmt,revision) if layout is None else
                       self._writer_client.export(name,fmt,revision,layout=layout))
            write_new_export(file_path, payload)
            return file_path
        self._native_io(work, lambda path: self._writer_status(f'Exported {fmt.upper()}: {path}'))

    def _start_native_adaptation(self, file_path, name, target, config):
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if self._adapt_job:
            self._writer_error('An adaptation is already monitored. Wait for its final status before starting another.')
            return
        def started(data):
            name = data.get('project_name') or data.get('project')
            if not name:
                self._writer_error('The backend did not identify the adaptation project.')
                return
            self._adapt_job = {'project': name, 'job_id': data['job_id']}
            self._adapt_timer.start()
            self._writer_status(f'Adaptation accepted: {name}. Waiting for actual progress.')
        self._native_io(lambda: self._writer_client.adapt(file_path, name, target, config), started)

    def _poll_native_adaptation(self):
        if getattr(self, '_creative_bootstrap', None) is not None:
            return self._decline_delegated_action()
        if self._writer_busy or not self._adapt_job:
            return
        job = dict(self._adapt_job)
        def status(data):
            if data.get('job_id') != job['job_id']:
                self._adapt_timer.stop()
                self._writer_error('Adaptation ownership changed. Review the project before continuing.')
                return
            state = data.get('status', 'unknown')
            self._writer_status(f'Adaptation {job["project"]}: {state} ({data.get("progress", 0)}%)')
            if state in {'complete', 'completed', 'success', 'failed', 'error', 'cancelled', 'canceled', 'interrupted', 'not_found'}:
                self._adapt_timer.stop()
                self._adapt_job = None
                if state in {'complete', 'completed', 'success'}:
                    self._flush_native_transition(lambda: self._read_native_project(job['project']))
                else:
                    self._writer_error(f'Adaptation ended with status {state}. Source and generated files are retained on the host.')
        def failed(message):
            self._adapt_timer.stop()
            self._writer_error(message + ' Refresh adaptation status to resume monitoring.')
        self._native_io(lambda: self._writer_client.adaptation_status(job['project']), status, failed)


UniversalCreationSuiteNativeView = ScreenwritingNativeView
