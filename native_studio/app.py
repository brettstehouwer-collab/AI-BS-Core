"""AI-BS Native Studio Master Application Shell (All-in-One Pure Native Windows).

Direct Win32 Direct2D / DirectX GUI with zero browser engines, zero Electron,
and zero local web servers. Houses every hub, pillar, BS-CHAT Pro, and all 46 sub-tabs.
Features:
- 1:1 Web-Parity Shell:
  - Top Mom Mode Banner (🌸 🔔 MOM VERSION — CLICK HERE FOR BIG TEXT & EASY VIEW 🌸)
  - TopNavbar with 4 Master Hub Category Pills (Intelligence & Code, Creative Media, Business, Engineering)
  - Horizontal Scrolling SubTabBar with < and > arrow controls and cyber-glow indicators
  - Quick Dock bar + Ambient Hardware Telemetry Chip (RTX 4090 + Ryzen 9 9950X)
  - Universal Ctrl+K Search Palette
  - Full-Width Viewport with Optional Collapsible Hub Sidebar
- 100% Dedicated Native Views for all 46 Sub-Tabs:
  - ExecutiveCockpitFullView, BsChatIdeFullView, RecDebutNativeView, HostTerminalView
  - MusicDawView, SovereignSwarmView, WorkflowDagNativeView, DeepLearningStudioNativeView
  - NutritionNativeView, AgentMemoryNativeView, ReasoningAttentionNativeView
  - SystemHealthNativeView, VirtualMachinesNativeView, AutomationConsoleNativeView
  - LexiconNativeView, DefinitionsLoreNativeView
  - BvMediaCreatorNativeView, ComfyWorkspaceNativeView, ScreenwritingNativeView
  - PersonalBrandNativeView, AdvertisingStudioNativeView, SyndicationNativeView
  - UnifiedMediaGalleryNativeView, TheatricalPrompterProjectorNativeView, NeonLoungeStudioNativeView
  - DigitalStorefrontNativeView
  - CloudDriveNativeView, OperationsAuditNativeView, MasterAccountingNativeView
  - ClientsCrmNativeView, LeadMatrixNativeView, OsintReconNativeView, OnboardingNativeView
  - SovereignNdaNativeView, EmailClientNativeView, LostPropertyNativeView, CalendarScheduleNativeView
  - WebTelemetryNativeView, EcosystemBlueprintNativeView
  - PhoneRepairNativeView, PowerWashingNativeView, BanquetCadNativeView, NotoInventoryNativeView
  - ProjectNoCoNativeView, NocoVisionNativeView, CryptoSwarmNativeView, GamingLabNativeView
  - SteamGamingNativeView, BibleHubNativeView
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Ensure all subprocess calls on Windows are completely silent (zero console / OpenConsole popups)
if sys.platform == "win32":
    _orig_run = subprocess.run
    _orig_popen = subprocess.Popen
    _orig_check_output = subprocess.check_output

    _hidden_startupinfo = subprocess.STARTUPINFO()
    _hidden_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _hidden_startupinfo.wShowWindow = 0

    def _silent_run(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if "startupinfo" not in kwargs:
            kwargs["startupinfo"] = _hidden_startupinfo
        return _orig_run(*args, **kwargs)

    class _SilentPopen(_orig_popen):
        def __init__(self, *args, **kwargs):
            if "creationflags" not in kwargs:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            if "startupinfo" not in kwargs:
                kwargs["startupinfo"] = _hidden_startupinfo
            super().__init__(*args, **kwargs)

    def _silent_check_output(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if "startupinfo" not in kwargs:
            kwargs["startupinfo"] = _hidden_startupinfo
        return _orig_check_output(*args, **kwargs)

    subprocess.run = _silent_run
    subprocess.Popen = _SilentPopen
    subprocess.check_output = _silent_check_output

# Ensure C:\AI-BS root is in sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_NATIVE_DIR = str(Path(__file__).resolve().parent)
if _NATIVE_DIR not in sys.path:
    sys.path.insert(0, _NATIVE_DIR)
if not getattr(sys, 'frozen', False):
    for _live_dir in (r"C:\AI-BS\backend", r"C:\AI-BS\native_studio", r"C:\AI-BS"):
        if os.path.isdir(_live_dir) and _live_dir not in sys.path:
            sys.path.insert(0, _live_dir)

from native_studio.runtime_policy import configure_frozen_dependencies
configure_frozen_dependencies()

if __name__ == '__main__' and '--scratchpad-syntax-worker' in sys.argv:
    from native_studio.syntax_worker import main as syntax_worker_main
    sys.exit(syntax_worker_main(sys.argv[1:]))

if (__name__ == '__main__' and '--packaged-writer-acceptance' in sys.argv
        and '--native-creative-pipe-bootstrap' not in sys.argv):
    sys.exit(2)

# Explicit delegated launches finish their stdin/authorization handshake before
# Qt imports, worker pools, full-shell views or background hub initialization.
if __name__ == '__main__' and any(flag in sys.argv for flag in ('--native-creative-bootstrap','--native-creative-pipe-bootstrap')):
    from native_studio.native_creative_entry import main as native_creative_main
    if '--packaged-writer-acceptance' in sys.argv:
        def _run_packaged_writer_acceptance(session, packet):
            from native_studio.packaged_writer_acceptance import run_writer_acceptance
            return run_writer_acceptance(session, packet)
        sys.exit(native_creative_main([sys.argv[0], '--native-creative-pipe-bootstrap'],
                                     run_writer=_run_packaged_writer_acceptance))
    sys.exit(native_creative_main(sys.argv))

# Release acceptance intentionally bypasses MainWindow, daemon management,
# samplers and the broad application-view import graph. It is opt-in only.
if __name__ == '__main__' and '--packaged-authoring-acceptance' in sys.argv:
    from native_studio.packaged_authoring_acceptance import main as packaged_authoring_main
    sys.exit(packaged_authoring_main(sys.argv[1:]))

if __name__ == '__main__' and '--packaged-chapter-acceptance' in sys.argv:
    from native_studio.packaged_chapter_acceptance import main as packaged_chapter_acceptance_main
    sys.exit(packaged_chapter_acceptance_main(sys.argv[1:]))

if __name__ == '__main__' and '--saved-play-release-smoke' in sys.argv:
    from native_studio.saved_play_release_smoke import saved_play_release_smoke_main
    sys.exit(saved_play_release_smoke_main(sys.argv[1:]))

if __name__ == '__main__' and any(flag in sys.argv for flag in
        ('--placement-release-smoke', '--placement-reopen-smoke')):
    from native_studio.placement_release_smoke import placement_release_smoke_main
    sys.exit(placement_release_smoke_main(sys.argv[1:]))

if __name__ == '__main__' and '--asset-release-smoke' in sys.argv:
    from native_studio.asset_release_smoke import asset_release_smoke_main
    sys.exit(asset_release_smoke_main(sys.argv[1:]))

if __name__ == '__main__' and any(flag in sys.argv for flag in
        ('--game-build-smoke', '--creator-release-smoke')):
    from native_studio.game_release_smoke import release_smoke_main
    sys.exit(release_smoke_main(sys.argv[1:]))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap, QLinearGradient
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from native_studio import __version__
from native_studio.window_geometry import fit_startup_geometry
from native_studio.runtime_policy import allow_background_daemon_management, allow_exit_process_cleanup, allow_background_update_checks
from native_studio.engine import EngineBus, GpuProbe
from native_studio.theme import STYLESHEET, PALETTE, apply_dark_titlebar
from native_studio.navigation_registry import (
    NATIVE_MASTER_HUBS,
    PINNED_QUICK_TABS,
    SIMPLE_MODE_ITEMS,
    TAB_KEY_ALIASES,
    get_all_subtabs_flat,
    find_subtab_spec,
)

# Core & Dedicated View Imports
from native_studio.executive_cockpit_full import ExecutiveCockpitFullView
from native_studio.bs_chat_ide_full import BsChatIdeFullView
from native_studio.rec_debut_view import RecDebutNativeView
from native_studio.fe_express_view import FEExpressNativeView
from native_studio.subsystem_views import HostTerminalView
from native_studio.music_daw_view import MusicDawView
from native_studio.screen_mirror_view import ScreenMirrorNativeView
from native_studio.compute_view import ComputeLabView
from native_studio.telemetry_hub import TelemetryHub
from native_studio.comfy_workspace_view import ComfyWorkspaceNativeView
from native_studio.noto_inventory_view import NotoInventoryNativeView
from native_studio.banquet_cad_view import BanquetCadNativeView
from native_studio.accounting_view import MasterAccountingNativeView
from native_studio.clients_crm_view import ClientsCrmNativeView
from native_studio.screenwriting_view import ScreenwritingNativeView
from native_studio.cloud_drive_view import CloudDriveNativeView
from native_studio.calendar_view import CalendarScheduleNativeView
from native_studio.steam_gaming_view import SteamGamingNativeView
from native_studio.power_washing_view import PowerWashingNativeView
from native_studio.crypto_swarm_view import CryptoSwarmNativeView
from native_studio.phone_repair_view import PhoneRepairNativeView
from native_studio.bible_hub_view import BibleHubNativeView

# New Dedicated High-Fidelity Views
from native_studio.system_health_view import SystemHealthNativeView
from native_studio.syndication_view import SyndicationNativeView
from native_studio.onboarding_view import OnboardingNativeView
from native_studio.web_telemetry_view import WebTelemetryNativeView
from native_studio.ecosystem_blueprint_view import EcosystemBlueprintNativeView
from native_studio.automation_console_view import AutomationConsoleNativeView
from native_studio.nutrition_view import NutritionNativeView
from native_studio.lexicon_view import LexiconNativeView
from native_studio.email_client_view import EmailClientNativeView
from native_studio.cluster_view import ClusterEngineNativeView

# Blended Operational, Creative, Engineering & Intelligence Suites
from native_studio.operations_views import (
    OperationsAuditNativeView,
    LeadMatrixNativeView,
    OsintReconNativeView,
    SovereignNdaNativeView,
    LostPropertyNativeView,
)
from native_studio.creative_suite_views import (
    BvMediaCreatorNativeView,
    PersonalBrandNativeView,
    AdvertisingStudioNativeView,
    DigitalStorefrontNativeView,
    UnifiedMediaGalleryNativeView,
    TheatricalPrompterProjectorNativeView,
    NeonLoungeStudioNativeView,
    UniversalOmniStudioNativeView,
)
from native_studio.engineering_views import (
    ProjectNoCoNativeView,
    NocoVisionNativeView,
    GamingLabNativeView,
)
from native_studio.intelligence_views import (
    SovereignChatView,
    SovereignSwarmView,
    DeepLearningStudioNativeView,
    AgentMemoryNativeView,
    ReasoningAttentionNativeView,
    VirtualMachinesNativeView,
    DefinitionsLoreNativeView,
    WorkflowDagNativeView,
)
from native_studio.updater import UpdateDialog, check_for_updates_worker


class CommandPaletteDialog(QDialog):
    """Ctrl+K Search Everywhere & Universal Tool Jumper."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Jump to Tool or Subsystem [Ctrl+K]")
        self.setFixedSize(620, 440)
        self.setStyleSheet(
            f"background-color: {PALETTE['panel']}; color: {PALETTE['text']}; border: 1px solid #7c3aed; border-radius: 10px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type tool name, subsystem, or keyword...")
        self.search_edit.setStyleSheet(
            "background: #040810; border: 1px solid #22d3ee; border-radius: 6px; padding: 10px; font-size: 11pt; color: #ffffff;"
        )
        self.search_edit.textChanged.connect(self._filter_items)
        layout.addWidget(self.search_edit)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "background: #040810; border: 1px solid #1e293b; border-radius: 6px; padding: 4px;"
        )
        self.list_widget.itemDoubleClicked.connect(self._activate_item)
        layout.addWidget(self.list_widget)

        self.selected_key: str | None = None
        self._all_items = get_all_subtabs_flat()
        self._populate("")

    def _populate(self, filter_text: str) -> None:
        self.list_widget.clear()
        q = filter_text.strip().lower()
        if not q or any(k in q for k in ["update", "check", "pull", "sync", "rebuild", "git"]):
            li = QListWidgetItem("🔄  Check for Updates & Live Hot-Reload  [Action]\n    Pull latest Git changes and sync live without rebuilding")
            li.setData(Qt.ItemDataRole.UserRole, "action:check_updates")
            self.list_widget.addItem(li)
        for item in self._all_items:
            combined = f"{item.label} {item.description} {item.badge}".lower()
            if not q or q in combined:
                li = QListWidgetItem(f"{item.icon}  {item.label}  [{item.badge}]\n    {item.description}")
                li.setData(Qt.ItemDataRole.UserRole, item.key)
                self.list_widget.addItem(li)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _filter_items(self, text: str) -> None:
        self._populate(text)

    def _activate_item(self, item: QListWidgetItem) -> None:
        self.list_widget.setCurrentItem(item)
        self.accept()

    def accept(self) -> None:
        current = self.list_widget.currentItem()
        if current is None:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(key, str) or not key:
            return
        self.selected_key = key
        super().accept()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
            return
        super().keyPressEvent(event)


class MomModeView(QWidget):
    """High-contrast, large-font friendly dashboard for Mom & Julie."""

    def __init__(self, on_select_tab, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.on_select_tab = on_select_tab

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: #070b14;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # Top Banner in Mom Mode
        banner = QFrame()
        banner.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #be185d, stop:1 #ec4899);"
            "border-radius: 12px; padding: 20px;"
        )
        b_lay = QVBoxLayout(banner)
        title = QLabel("🌸 Julie & Mom Mode — Big Text & Easy View 🌸")
        title.setStyleSheet("font-size: 20pt; font-weight: 800; color: #ffffff;")
        sub = QLabel("Select any simplified module below for big text and immediate 1-click access.")
        sub.setStyleSheet("font-size: 13pt; color: #fdf2f8;")
        b_lay.addWidget(title)
        b_lay.addWidget(sub)
        layout.addWidget(banner)

        # 5 Big Action Cards Grid
        grid = QGridLayout()
        grid.setSpacing(18)

        for idx, item in enumerate(SIMPLE_MODE_ITEMS):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background: #0f172a; border: 2px solid #ec4899; border-radius: 12px; padding: 18px; }"
                "QFrame:hover { background: #1e293b; border-color: #38bdf8; }"
            )
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(8)

            lbl_icon = QLabel(item["icon"])
            lbl_icon.setStyleSheet("font-size: 32pt;")
            c_lay.addWidget(lbl_icon)

            lbl_label = QLabel(item["label"])
            lbl_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #f8fafc;")
            c_lay.addWidget(lbl_label)

            lbl_desc = QLabel(item["description"])
            lbl_desc.setStyleSheet("font-size: 11pt; color: #94a3b8;")
            lbl_desc.setWordWrap(True)
            c_lay.addWidget(lbl_desc)

            btn = QPushButton(f"Open {item['label']} ➔")
            btn.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ec4899, stop:1 #a855f7); color: #ffffff; border-radius: 8px; padding: 12px 20px; font-size: 12pt; font-weight: bold; }"
                "QPushButton:hover { opacity: 0.9; }"
            )
            btn.clicked.connect(lambda checked, k=item["key"]: self.on_select_tab(k))
            c_lay.addWidget(btn)

            grid.addWidget(card, idx // 2, idx % 2)

        layout.addLayout(grid)
        layout.addStretch()
        scroll.setWidget(container)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)


class TrippyRootWidget(QWidget):
    """Deep Cosmic & Psychedelic Wallpaper Root Canvas with Direct2D Glass Tinting."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Root")
        self.wallpaper_enabled: bool = True

        # Locate psychedelic_theme.jpg in public folder or bundled PyInstaller assets
        candidate_paths = [
            Path(r"C:\AI-BS\frontend\public\psychedelic_theme.jpg"),
            Path(__file__).resolve().parent.parent / "frontend" / "public" / "psychedelic_theme.jpg",
            Path(getattr(sys, "_MEIPASS", ".")) / "assets" / "psychedelic_theme.jpg",
        ]
        self._pixmap: QPixmap | None = None
        for p in candidate_paths:
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self._pixmap = pix
                    break

    def toggle_wallpaper(self) -> bool:
        self.wallpaper_enabled = not self.wallpaper_enabled
        self.update()
        return self.wallpaper_enabled

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        w, h = self.width(), self.height()

        if self.wallpaper_enabled and self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - w) // 2
            y = (scaled.height() - h) // 2
            painter.drawPixmap(0, 0, scaled, x, y, w, h)
            # Rich cosmic violet-indigo semi-transparent glass overlay (85% opacity)
            painter.fillRect(self.rect(), QColor(11, 6, 28, 222))
        else:
            # Fallback deep psychedelic nebula gradient
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor(28, 12, 58))
            grad.setColorAt(0.5, QColor(12, 6, 28))
            grad.setColorAt(1.0, QColor(5, 10, 32))
            painter.fillRect(self.rect(), grad)

        painter.end()


class MainWindow(QMainWindow):
    """Universal Sovereign Desktop Studio containing all AI-BS hubs, tools, and subsystems."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"AI-BS Sovereign Studio v{__version__} [Windows 10/11 x64 Pure Native]")
        self.resize(1620, 980)
        self.setMinimumSize(1150, 750)

        # Background Bus & GPU Probe
        self.bus = EngineBus(max_threads=12)
        self.gpu_probe = GpuProbe()
        self.hub = TelemetryHub(self.gpu_probe)

        # Audio kernel bound to WASAPI Exclusive
        self.view_daw = MusicDawView(self.bus)
        self.hub.attach_audio(self.view_daw.engine)

        # State tracking
        self._active_hub_idx = 0
        self._active_subtab_key = "executive_cockpit"
        self._is_mom_mode = False
        self._subviews_cache: Dict[str, QWidget] = {}
        self._subtab_buttons: Dict[str, QPushButton] = {}
        self._hub_category_buttons: List[QPushButton] = []

        self._build_ui()
        self._fit_startup_to_screen()

        # Telemetry sampler
        self.hub.frame.connect(self._on_hub_frame)
        self.hub.start()

        # Service ownership remains with the gateway unless explicitly enabled.
        try:
            if allow_background_daemon_management():
                from backend.aibs_ecosystem_spawner import activate_all_daemons
                self.bus.submit(activate_all_daemons, verbose=False)
                self._daemon_watchdog_timer = QTimer(self)
                self._daemon_watchdog_timer.setInterval(20000)
                self._daemon_watchdog_timer.timeout.connect(lambda: self.bus.submit(activate_all_daemons, verbose=False))
                self._daemon_watchdog_timer.start()
        except Exception:
            pass

        # Background update work requires separate explicit permission.
        if allow_background_update_checks():
            QTimer.singleShot(10000, self._check_for_background_updates)

    def _check_for_background_updates(self) -> None:
        # Permission may have been revoked while the startup timer was pending.
        if allow_background_update_checks():
            self.bus.submit(check_for_updates_worker, on_result=self._on_bg_update_check_result)

    def _fit_startup_to_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        # Qt frame styling is not the Windows resize border/title decoration.
        # Realize the still-hidden native window so frameMargins is meaningful;
        # reserve conservative decoration if the platform reports zero margins.
        self.winId()
        handle = self.windowHandle()
        margins = handle.frameMargins() if handle is not None else None
        frame_width = max(16, margins.left()+margins.right()) if margins is not None else 16
        frame_height = max(40, margins.top()+margins.bottom()) if margins is not None else 40
        fitted = fit_startup_geometry((available.x(), available.y(), available.width(), available.height()),
                                      frame=(frame_width, frame_height))
        self.setMinimumSize(fitted.minimum_width, fitted.minimum_height)
        self.resize(fitted.width, fitted.height)
        self.move(fitted.x, fitted.y)

    def _build_ui(self) -> None:
        self.trippy_root = TrippyRootWidget()
        self.setCentralWidget(self.trippy_root)
        main_root_lay = QVBoxLayout(self.trippy_root)
        main_root_lay.setContentsMargins(0, 0, 0, 0)
        main_root_lay.setSpacing(0)

        # ── 1. TOP MOM VERSION BANNER (CLICKABLE TOGGLE) ──
        self.mom_banner = QFrame()
        self.mom_banner.setObjectName("MomBanner")
        self.mom_banner.setFixedHeight(34)
        mb_lay = QHBoxLayout(self.mom_banner)
        mb_lay.setContentsMargins(12, 0, 12, 0)

        self.btn_mom_banner = QPushButton("🌸 🔔 MOM VERSION — CLICK HERE FOR BIG TEXT & EASY VIEW 🌸")
        self.btn_mom_banner.setStyleSheet(
            "background: transparent; border: none; color: #ffffff; font-weight: 800; font-size: 9.5pt; letter-spacing: 1px;"
        )
        self.btn_mom_banner.clicked.connect(self._toggle_mom_mode)
        mb_lay.addWidget(self.btn_mom_banner)
        main_root_lay.addWidget(self.mom_banner)

        # ── 2. TOP NAVBAR (BRAND, CATEGORY PILLS, QUICK DOCK, AMBIENT HARDWARE CHIP) ──
        self.top_navbar = self._build_top_navbar()
        main_root_lay.addWidget(self.top_navbar)

        # ── 3. HORIZONTAL SUBTAB BAR (< ARROW, SCROLLABLE PILLS, > ARROW) ──
        self.subtab_bar_widget = self._build_subtab_bar()
        main_root_lay.addWidget(self.subtab_bar_widget)

        # ── 4. MAIN CENTRAL CONTENT AREA (SIDEBAR + STACK) ──
        content_body = QWidget()
        cb_lay = QHBoxLayout(content_body)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setSpacing(0)

        # Optional Collapsible Sidebar
        self.sidebar = self._build_sidebar()
        self.sidebar.hide()  # Default to full-width web-style layout!
        cb_lay.addWidget(self.sidebar)

        # Central Viewport Stack
        self.stack = QStackedWidget()

        # Page for Mom Mode
        self.mom_view = MomModeView(self.jump_to_tab)
        self.stack.addWidget(self.mom_view)

        cb_lay.addWidget(self.stack, 1)
        main_root_lay.addWidget(content_body, 1)

        # Status Bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.chip_label = QLabel("❄️ Telemetry Initializing...")
        self.tasks_label = QLabel("Active Workers: 0")
        self.engine_label = QLabel("Pure Win32 Direct2D Engine")

        self.status.addPermanentWidget(self.chip_label)
        self.status.addPermanentWidget(self.tasks_label)
        self.status.addPermanentWidget(self.engine_label)

        self.bus.active_changed.connect(lambda n: self.tasks_label.setText(f"Active Workers: {n}"))

        # Initialize to first subtab
        self._select_hub_category(0)
        self.jump_to_tab("executive_cockpit")

    def _build_top_navbar(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("TopNavbar")
        # Every existing action keeps its natural readable width. Overflow is
        # navigable rather than squeezing labels into unreadable fragments.
        nav.setFixedHeight(76)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        lay.setContentsMargins(14, 4, 14, 4)
        lay.setSpacing(10)

        # Sidebar toggle
        self.btn_toggle_sidebar = QPushButton("☰")
        self.btn_toggle_sidebar.setToolTip("Toggle Hub Sidebar")
        self.btn_toggle_sidebar.setStyleSheet(
            "QPushButton { background: #121b30; color: #22d3ee; border: 1px solid #1e2a44; border-radius: 6px; padding: 4px 10px; font-size: 11pt; font-weight: bold; }"
            "QPushButton:hover { background: #1e293b; border-color: #22d3ee; }"
        )
        self.btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        lay.addWidget(self.btn_toggle_sidebar)

        # Brand
        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand = QLabel("Stehouwer AI")
        brand.setStyleSheet("font-size: 12pt; font-weight: 800; color: #22d3ee; letter-spacing: 0.5px;")
        brand_sub = QLabel(f"SOVEREIGN NATIVE v{__version__}")
        brand_sub.setStyleSheet("font-size: 6.5pt; font-weight: bold; color: #a78bfa; letter-spacing: 1px;")
        brand_box.addWidget(brand)
        brand_box.addWidget(brand_sub)
        lay.addLayout(brand_box)

        lay.addSpacing(8)

        # 4 Master Category Buttons (Pills)
        pill_labels = [
            "🧠 Intelligence & Code",
            "🎨 Creative Media",
            "💼 Business & Ops",
            "🛠️ Engineering Labs",
        ]
        for idx, hub in enumerate(NATIVE_MASTER_HUBS):
            txt = pill_labels[idx] if idx < len(pill_labels) else f"{hub.icon}  {hub.label}"
            btn = QPushButton(txt)
            btn.setStyleSheet(self._get_category_pill_style(is_active=(idx == 0)))
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, i=idx: self._select_hub_category(i))
            self._hub_category_buttons.append(btn)
            lay.addWidget(btn)

        lay.addStretch()

        # Pinned Quick Dock Ribbon with Left/Right Controls
        self.btn_quick_left = QPushButton("◀")
        self.btn_quick_left.setFixedSize(20, 26)
        self.btn_quick_left.setStyleSheet(
            "QPushButton { background: #0d1424; color: #94a3b8; border: 1px solid #1e2a44; border-radius: 4px; font-size: 7pt; font-weight: bold; }"
            "QPushButton:hover { color: #22d3ee; border-color: #22d3ee; }"
        )
        self.btn_quick_left.clicked.connect(self._scroll_quick_dock_left)
        lay.addWidget(self.btn_quick_left)

        self.quick_scroll = QScrollArea()
        self.quick_scroll.setFixedHeight(34)
        self.quick_scroll.setWidgetResizable(True)
        self.quick_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.quick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.quick_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.quick_scroll.setStyleSheet("background: transparent;")

        self.quick_container = QWidget()
        quick_lay = QHBoxLayout(self.quick_container)
        quick_lay.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        quick_lay.setContentsMargins(0, 0, 0, 0)
        quick_lay.setSpacing(5)

        for pt in PINNED_QUICK_TABS:
            btn = QPushButton(f"{pt['icon']} {pt['label']}")
            btn.setStyleSheet(
                "QPushButton { background: rgba(18, 27, 48, 0.85); color: #94a3b8; border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 6px; padding: 4px 8px; font-size: 7.5pt; font-weight: 600; white-space: nowrap; }"
                "QPushButton:hover { background: rgba(56, 189, 248, 0.2); color: #ffffff; border-color: #38bdf8; }"
            )
            btn.clicked.connect(lambda checked, k=pt["key"]: self.jump_to_tab(k))
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            quick_lay.addWidget(btn)

        self.quick_scroll.setWidget(self.quick_container)
        self.quick_scroll.setMinimumWidth(180)
        lay.addWidget(self.quick_scroll)

        self.btn_quick_right = QPushButton("▶")
        self.btn_quick_right.setFixedSize(20, 26)
        self.btn_quick_right.setStyleSheet(
            "QPushButton { background: #0d1424; color: #94a3b8; border: 1px solid #1e2a44; border-radius: 4px; font-size: 7pt; font-weight: bold; }"
            "QPushButton:hover { color: #22d3ee; border-color: #22d3ee; }"
        )
        self.btn_quick_right.clicked.connect(self._scroll_quick_dock_right)
        lay.addWidget(self.btn_quick_right)

        # Ambient Hardware Chip
        self.hw_chip = QLabel("❄️ 44°C | ⚡ 3.0/24G | 💻 19%")
        self.hw_chip.setStyleSheet(
            "background: rgba(15, 23, 42, 0.9); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 6px; padding: 4px 8px; font-weight: bold; font-size: 7.5pt;"
        )
        lay.addWidget(self.hw_chip)

        # Ctrl+K Jump
        self.search_btn = QPushButton("🔍 Ctrl+K")
        self.search_btn.setStyleSheet(
            "QPushButton { background: rgba(34,211,238,0.1); color: #22d3ee; border: 1px solid rgba(34,211,238,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 8pt; }"
            "QPushButton:hover { background: rgba(34,211,238,0.2); }"
        )
        self.search_btn.clicked.connect(self._open_command_palette)
        lay.addWidget(self.search_btn)

        # Mom Mode Button
        self.btn_mom_toggle = QPushButton("🌸 Mom Mode")
        self.btn_mom_toggle.setStyleSheet(
            "QPushButton { background: rgba(236, 72, 153, 0.15); color: #ec4899; border: 1px solid rgba(236, 72, 153, 0.35); border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 8pt; }"
            "QPushButton:hover { background: rgba(236, 72, 153, 0.3); }"
        )
        self.btn_mom_toggle.clicked.connect(self._toggle_mom_mode)
        lay.addWidget(self.btn_mom_toggle)

        # Trippy Wallpaper Toggle
        self.btn_wallpaper_toggle = QPushButton("✨ Trippy Theme: ON")
        self.btn_wallpaper_toggle.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 46, 147, 0.25), stop:1 rgba(0, 240, 255, 0.25)); color: #00f0ff; border: 1px solid rgba(0, 240, 255, 0.45); border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 8pt; }"
            "QPushButton:hover { background: rgba(0, 240, 255, 0.35); border-color: #00f0ff; color: #ffffff; }"
        )
        self.btn_wallpaper_toggle.clicked.connect(self._toggle_trippy_wallpaper)
        lay.addWidget(self.btn_wallpaper_toggle)

        # Check for Updates Button
        self.btn_update = QPushButton("🔄 Updates")
        self.btn_update.setToolTip("Check for updates, sync git, and hot-reload code in-place (No rebuild required)")
        self.btn_update.setStyleSheet(
            "QPushButton { background: rgba(0, 240, 255, 0.12); color: #00f0ff; border: 1px solid rgba(0, 240, 255, 0.35); border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 8pt; }"
            "QPushButton:hover { background: rgba(0, 240, 255, 0.25); border-color: #00f0ff; color: #ffffff; }"
        )
        self.btn_update.clicked.connect(self._open_update_dialog)
        lay.addWidget(self.btn_update)

        for widget in (self.btn_toggle_sidebar, self.hw_chip, self.search_btn,
                       self.btn_mom_toggle, self.btn_wallpaper_toggle, self.btn_update):
            widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.nav_scroll = QScrollArea(nav)
        self.nav_scroll.setObjectName('MainNavigationScroll')
        self.nav_scroll.setAccessibleName('Main navigation — scroll horizontally for all controls')
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_scroll.setWidget(row)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.nav_scroll)
        return nav

    def _toggle_trippy_wallpaper(self) -> None:
        is_on = self.trippy_root.toggle_wallpaper()
        self.btn_wallpaper_toggle.setText("✨ Trippy Theme: ON" if is_on else "🌌 Nebula Mode: ON")

    def _build_subtab_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("SubTabBar")
        bar.setFixedHeight(46)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 2, 10, 2)
        lay.setSpacing(6)

        # Left Scroll Arrow
        self.btn_scroll_left = QPushButton("◀")
        self.btn_scroll_left.setFixedSize(28, 28)
        self.btn_scroll_left.setStyleSheet(
            "QPushButton { background: #0d1424; color: #94a3b8; border: 1px solid #1e2a44; border-radius: 4px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { color: #22d3ee; border-color: #22d3ee; }"
        )
        self.btn_scroll_left.clicked.connect(self._scroll_subtabs_left)
        lay.addWidget(self.btn_scroll_left)

        # Scroll area for subtabs
        self.subtab_scroll = QScrollArea()
        self.subtab_scroll.setWidgetResizable(True)
        self.subtab_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.subtab_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.subtab_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.subtab_scroll.setStyleSheet("background: transparent;")

        self.subtab_container = QWidget()
        self.subtab_container_lay = QHBoxLayout(self.subtab_container)
        self.subtab_container_lay.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.subtab_container_lay.setContentsMargins(4, 2, 4, 2)
        self.subtab_container_lay.setSpacing(6)
        self.subtab_container_lay.addStretch()

        self.subtab_scroll.setWidget(self.subtab_container)
        lay.addWidget(self.subtab_scroll, 1)

        # Right Scroll Arrow
        self.btn_scroll_right = QPushButton("▶")
        self.btn_scroll_right.setFixedSize(28, 28)
        self.btn_scroll_right.setStyleSheet(
            "QPushButton { background: #0d1424; color: #94a3b8; border: 1px solid #1e2a44; border-radius: 4px; font-size: 8pt; font-weight: bold; }"
            "QPushButton:hover { color: #22d3ee; border-color: #22d3ee; }"
        )
        self.btn_scroll_right.clicked.connect(self._scroll_subtabs_right)
        lay.addWidget(self.btn_scroll_right)

        return bar

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 14, 14, 14)
        sb_layout.setSpacing(6)

        sb_layout.addWidget(QLabel("PRIMARY COMMAND HUBS:"))
        self.hub_list = QListWidget()
        self.hub_list.setObjectName("Nav")

        for h in NATIVE_MASTER_HUBS:
            self.hub_list.addItem(QListWidgetItem(f"{h.icon}  {h.label}"))

        self.hub_list.currentRowChanged.connect(self._on_sidebar_row_changed)
        sb_layout.addWidget(self.hub_list)

        sb_layout.addStretch()
        footer = QLabel("● ZERO BROWSER ENGINES\n● DIRECT WIN32 DIRECT2D\n● 52 NATIVE SUBSYSTEMS")
        footer.setObjectName("SidebarFooter")
        sb_layout.addWidget(footer)

        return sidebar

    def _get_category_pill_style(self, is_active: bool) -> str:
        if is_active:
            return (
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d92bb8, stop:0.5 #7c3aed, stop:1 #00f0ff); color: #ffffff; border: 1.5px solid #00f0ff; border-radius: 8px; padding: 5px 11px; font-weight: 800; font-size: 8.5pt; }"
            )
        return (
            "QPushButton { background: rgba(18, 9, 46, 0.85); color: #b8a3d6; border: 1px solid rgba(168, 85, 247, 0.25); border-radius: 8px; padding: 5px 11px; font-size: 8.5pt; font-weight: 600; }"
            "QPushButton:hover { background: rgba(46, 28, 89, 0.95); color: #ffffff; border-color: #00f0ff; }"
        )

    def _get_subtab_pill_style(self, is_active: bool) -> str:
        if is_active:
            return (
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0,240,255,0.28), stop:1 rgba(217,43,184,0.22)); color: #00f0ff; border: 1.5px solid #00f0ff; border-radius: 6px; padding: 5px 12px; font-weight: 800; font-size: 8pt; }"
            )
        return (
            "QPushButton { background: rgba(13, 7, 34, 0.85); color: #a793c9; border: 1px solid rgba(168, 85, 247, 0.2); border-radius: 6px; padding: 5px 12px; font-size: 8pt; }"
            "QPushButton:hover { background: rgba(28, 15, 69, 0.9); color: #ffffff; border-color: #00f0ff; }"
        )

    def _select_hub_category(self, cat_idx: int) -> None:
        self._active_hub_idx = cat_idx

        # Update category buttons styling
        for idx, btn in enumerate(self._hub_category_buttons):
            btn.setStyleSheet(self._get_category_pill_style(is_active=(idx == cat_idx)))

        # Repopulate SubTabBar with this hub's subtabs
        hub = NATIVE_MASTER_HUBS[cat_idx]

        # Clear existing buttons
        while self.subtab_container_lay.count():
            item = self.subtab_container_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._subtab_buttons.clear()

        for sub in hub.sub_tabs:
            is_active = (sub.key == self._active_subtab_key)
            btn = QPushButton(f"{sub.icon}  {sub.label}")
            btn.setStyleSheet(self._get_subtab_pill_style(is_active=is_active))
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, k=sub.key: self.jump_to_tab(k))
            self._subtab_buttons[sub.key] = btn
            self.subtab_container_lay.addWidget(btn)

        self.subtab_container_lay.addStretch()

    def _scroll_subtabs_left(self) -> None:
        bar = self.subtab_scroll.horizontalScrollBar()
        bar.setValue(bar.value() - 200)

    def _scroll_subtabs_right(self) -> None:
        bar = self.subtab_scroll.horizontalScrollBar()
        bar.setValue(bar.value() + 200)

    def _scroll_quick_dock_left(self) -> None:
        if hasattr(self, "quick_scroll"):
            bar = self.quick_scroll.horizontalScrollBar()
            bar.setValue(bar.value() - 160)

    def _scroll_quick_dock_right(self) -> None:
        if hasattr(self, "quick_scroll"):
            bar = self.quick_scroll.horizontalScrollBar()
            bar.setValue(bar.value() + 160)

    def _toggle_sidebar(self) -> None:
        if self.sidebar.isVisible():
            self.sidebar.hide()
            self.btn_toggle_sidebar.setText("☰")
        else:
            self.sidebar.show()
            self.btn_toggle_sidebar.setText("✕")

    def _toggle_mom_mode(self) -> None:
        self._is_mom_mode = not self._is_mom_mode
        if self._is_mom_mode:
            self.btn_mom_banner.setText("🌸 MOM MODE ACTIVE — CLICK TO RETURN TO MASTER STUDIO 🌸")
            self.btn_mom_toggle.setText("⚡ Master Mode")
            self.subtab_bar_widget.hide()
            self.stack.setCurrentWidget(self.mom_view)
        else:
            self.btn_mom_banner.setText("🌸 🔔 MOM VERSION — CLICK HERE FOR BIG TEXT & EASY VIEW 🌸")
            self.btn_mom_toggle.setText("🌸 Mom Mode")
            self.subtab_bar_widget.show()
            self.jump_to_tab(self._active_subtab_key)

    def _on_sidebar_row_changed(self, row: int) -> None:
        if 0 <= row < len(NATIVE_MASTER_HUBS):
            self._select_hub_category(row)
            # Jump to default tab
            def_key = NATIVE_MASTER_HUBS[row].default_tab
            self.jump_to_tab(def_key)

    def jump_to_tab(self, tab_key: str) -> None:
        """Directly activates any subtab, creating and caching its dedicated view."""
        tab_key = TAB_KEY_ALIASES.get(tab_key, tab_key)
        self._active_subtab_key = tab_key

        if self._is_mom_mode:
            self._toggle_mom_mode()

        # Find which category owns this tab
        cat_idx = None
        for idx, h in enumerate(NATIVE_MASTER_HUBS):
            for sub in h.sub_tabs:
                if sub.key == tab_key:
                    cat_idx = idx
                    break
            if cat_idx is not None:
                break

        if cat_idx is not None and cat_idx != self._active_hub_idx:
            self._select_hub_category(cat_idx)

        # Update subtab buttons styling
        active_btn = None
        for skey, sbtn in self._subtab_buttons.items():
            is_act = (skey == tab_key)
            sbtn.setStyleSheet(self._get_subtab_pill_style(is_active=is_act))
            if is_act:
                active_btn = sbtn

        if active_btn is not None and hasattr(self, "subtab_scroll"):
            self.subtab_scroll.ensureWidgetVisible(active_btn, 50, 0)

        # Get or create dedicated view
        view = self._get_or_create_subview(tab_key)
        if view:
            if self.stack.indexOf(view) == -1:
                self.stack.addWidget(view)
            self.stack.setCurrentWidget(view)

    def _get_or_create_subview(self, key: str) -> QWidget:
        key = TAB_KEY_ALIASES.get(key, key)
        if key in self._subviews_cache:
            return self._subviews_cache[key]

        view: Optional[QWidget] = None

        # ── Intelligence & Code Hub Views ──
        if key == "executive_cockpit" or key == "dashboard":
            view = ExecutiveCockpitFullView(self.bus)
        elif key == "ide":
            view = BsChatIdeFullView(self.bus)
        elif key == "sovereign_swarm":
            view = SovereignSwarmView(self.bus)
        elif key == "workflow_dag":
            view = WorkflowDagNativeView(self.bus)
        elif key == "terminal":
            view = HostTerminalView(self.bus)
        elif key == "deep_learning_studio":
            view = DeepLearningStudioNativeView(self.bus)
        elif key == "nutrition_subsystem":
            view = NutritionNativeView(self.bus)
        elif key == "agent_memory":
            view = AgentMemoryNativeView(self.bus)
        elif key == "reasoning_attention":
            view = ReasoningAttentionNativeView(self.bus)
        elif key == "system_health":
            view = SystemHealthNativeView(self.bus, self.gpu_probe)
        elif key == "cluster_engine":
            view = ClusterEngineNativeView(self.bus)
        elif key == "vms":
            view = VirtualMachinesNativeView(self.bus)
        elif key == "automation_console":
            view = AutomationConsoleNativeView(self.bus)
        elif key == "lexicon_dashboard":
            view = LexiconNativeView(self.bus)
        elif key in ("definitions", "learning_material_hub"):
            view = DefinitionsLoreNativeView(self.bus)

        # ── Creative Media Studio Hub Views ──
        elif key in ("bv_media_creator", "media_studio"):
            view = BvMediaCreatorNativeView(self.bus)
        elif key == "comfy_workspace":
            view = ComfyWorkspaceNativeView(self.bus)
        elif key in ("unified_creation", "stehouwer_cms", "universal_creation", "creation_suite", "video_studio", "comfyui_studio", "visual_scripting"):
            view = ScreenwritingNativeView(self.bus)
            if key == "video_studio":
                view._switch_suite_tab("video")
            elif key == "comfyui_studio":
                view._switch_suite_tab("comfy")
            elif key == "visual_scripting":
                view._switch_suite_tab("visual")
        elif key == "music_daw":
            view = self.view_daw
        elif key == "personal_brand":
            view = PersonalBrandNativeView(self.bus)
        elif key == "advertising":
            view = AdvertisingStudioNativeView(self.bus)
        elif key == "syndication":
            view = SyndicationNativeView(self.bus)
        elif key == "unified_media_gallery":
            view = UnifiedMediaGalleryNativeView(self.bus)
        elif key in ("theatrical_teleprompter", "theatrical_projector"):
            view = TheatricalPrompterProjectorNativeView(self.bus)
        elif key in ("neon_lounge_studio", "public_playground"):
            view = NeonLoungeStudioNativeView(self.bus)
        elif key == "universal_studio":
            view = UniversalOmniStudioNativeView(self.bus)
        elif key == "digital_storefront":
            view = DigitalStorefrontNativeView(self.bus)
        elif key in ("screen_mirror", "wireless_display", "screen_cast"):
            view = ScreenMirrorNativeView(self.bus)

        # ── Business & Operations Hub Views ──
        elif key in ("shared_cloud_drive", "documents"):
            view = CloudDriveNativeView(self.bus)
        elif key == "operations_audit":
            view = OperationsAuditNativeView(self.bus)
        elif key in ("master_accounting", "moneytrack"):
            view = MasterAccountingNativeView(self.bus)
        elif key == "clients":
            view = ClientsCrmNativeView(self.bus)
        elif key == "leadmatrix":
            view = LeadMatrixNativeView(self.bus)
        elif key == "unified_osint":
            view = OsintReconNativeView(self.bus)
        elif key == "rec_debut":
            view = RecDebutNativeView(self.bus)
        elif key == "fe_express":
            view = FEExpressNativeView(self.bus)
        elif key == "onboarding":
            view = OnboardingNativeView(self.bus)
        elif key == "nda_module":
            view = SovereignNdaNativeView(self.bus)
        elif key == "email_client":
            view = EmailClientNativeView(self.bus)
        elif key == "lost_property":
            view = LostPropertyNativeView(self.bus)
        elif key == "unified_calendar":
            view = CalendarScheduleNativeView(self.bus)
        elif key == "beta":
            view = WebTelemetryNativeView(self.bus)
        elif key == "ecosystem_blueprint":
            view = EcosystemBlueprintNativeView(self.bus)

        # ── Engineering & Specialized Labs Hub Views ──
        elif key == "phone_repair":
            view = PhoneRepairNativeView(self.bus)
        elif key == "power_washing":
            view = PowerWashingNativeView(self.bus)
        elif key == "banquet_architect":
            view = BanquetCadNativeView(self.bus)
        elif key in ("notos_enterprise", "noto_inventory"):
            view = NotoInventoryNativeView(self.bus)
        elif key == "project_noco":
            view = ProjectNoCoNativeView(self.bus)
        elif key == "noco_vision":
            view = NocoVisionNativeView(self.bus)
        elif key in ("unified_crypto", "crypto_trader"):
            view = CryptoSwarmNativeView(self.bus)
        elif key == "game_build":
            from native_studio.game_build_view import GameBuildNativeView
            view = GameBuildNativeView(self.bus)
        elif key == "gaming_lab":
            view = GamingLabNativeView(self.bus)
        elif key == "steam_gaming":
            view = SteamGamingNativeView(self.bus)
        elif key == "bible_hub":
            view = BibleHubNativeView(self.bus)
        elif key == "ai_compute":
            view = ComputeLabView(self.hub)
        else:
            view = ExecutiveCockpitFullView(self.bus)

        self._subviews_cache[key] = view
        return view

    def _open_command_palette(self) -> None:
        dlg = CommandPaletteDialog(self)
        if dlg.exec() and dlg.selected_key:
            if dlg.selected_key == "action:check_updates":
                self._open_update_dialog()
            else:
                self.jump_to_tab(dlg.selected_key)

    def _open_update_dialog(self) -> None:
        dlg = UpdateDialog(bus=self.bus, parent=self)
        dlg.exec()

    def _on_bg_update_check_result(self, res: dict) -> None:
        if res and res.get("has_updates"):
            n = res.get("commits_behind", 1)
            self.btn_update.setText(f"🚀 Update ({n})")
            self.btn_update.setStyleSheet(
                "QPushButton { background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid #f59e0b; border-radius: 6px; padding: 4px 10px; font-weight: 800; font-size: 8pt; }"
                "QPushButton:hover { background: rgba(245, 158, 11, 0.4); color: #ffffff; }"
            )

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_K and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._open_command_palette()
            return
        super().keyPressEvent(event)

    def _on_hub_frame(self, snap: dict) -> None:
        telemetry = snap.get("gpu") or {}
        cpu = (snap.get("sys") or {}).get("cpu_pct", 0.0)
        if telemetry.get("detected"):
            t = telemetry["temp_c"]
            v_used = telemetry["vram_used_gb"]
            v_tot = telemetry["vram_total_gb"]
            p = telemetry.get("power_w") or 0.0
            self.chip_label.setText(f"❄️ {t}°C | ⚡ {v_used:.1f}/{v_tot:.0f} GB VRAM | 🔋 {p:.0f} W")
            self.hw_chip.setText(f"❄️ {t}°C | ⚡ {v_used:.1f}/{v_tot:.0f}G | 💻 {cpu:.0f}% ↗")

    def closeEvent(self, event) -> None:
        state = getattr(self, '_close_state', 'OPEN')
        if state == 'CLOSED':
            event.accept()
            return
        if state == 'READY':
            # Closing a client does not authorize terminating other processes.
            try:
                if allow_exit_process_cleanup():
                    from backend.zombie_node_cleaner import sweep_zombie_nodes
                    sweep_zombie_nodes(dry_run=False)
            except Exception:
                pass
            self._close_state = 'CLOSED'
            super().closeEvent(event)
            return
        if state == 'STOPPING' or getattr(self, '_preparing_close', False):
            event.ignore()
            return
        self._preparing_close = True
        parts = list({id(part): part for part in
                      [self.view_daw, *getattr(self, '_subviews_cache', {}).values()]}.values())
        try:
            game_workspace = getattr(self, '_subviews_cache', {}).get('game_build')
            if game_workspace is not None and not game_workspace.prepare_close(
                    lambda: QTimer.singleShot(0, self.close)):
                event.ignore()
                return
            # Chapter shutdown can take time. Recheck every live chat's newest
            # snapshot after it completes, before disabling editing or teardown.
            for part in parts:
                recovery = getattr(part, '_chat_recovery', None)
                if recovery is not None and not recovery.flush_for_close():
                    event.ignore()
                    return
        finally:
            self._preparing_close = False

        self._close_state = 'STOPPING'
        self._shutdown_setup_complete = False
        self._shutdown_error = None
        self.setEnabled(False)
        # Prevent submission-producing GUI timers from racing bus admission.
        # The bus's drain timer has a separate QObject owner and stays active.
        for timer in self.findChildren(QTimer):
            timer.stop()
        self._shutdown_timer = QTimer(self)
        self._shutdown_timer.setInterval(20)
        self._shutdown_timer.timeout.connect(self._poll_shutdown)
        self.bus.drained.connect(self._poll_shutdown)
        self.hub.finished.connect(self._poll_shutdown)
        terminal = getattr(self.bus, '_native_terminal', None)
        if terminal is not None:
            try:
                terminal.shutdown()
            except Exception as exc:
                self._shutdown_error = type(exc).__name__
        batch_controller = getattr(self.bus, '_process_batch_controller', None)
        if batch_controller is not None:
            try:
                batch_controller.shutdown()
            except Exception as exc:
                self._shutdown_error = type(exc).__name__
        self.bus.shutdown(0)
        for part in parts:
            if hasattr(part, 'shutdown'):
                try:
                    part.shutdown()
                except Exception as exc:
                    # Retain the session on teardown failure; never silently
                    # claim its owners are safe to destroy.
                    self._shutdown_error = type(exc).__name__
        self.hub.shutdown(0)
        self._shutdown_setup_complete = True
        event.ignore()
        self._shutdown_timer.start()
        self._poll_shutdown()

    def _poll_shutdown(self) -> None:
        if (getattr(self, '_close_state', 'OPEN') != 'STOPPING'
                or not self._shutdown_setup_complete):
            return
        if self._shutdown_error is not None:
            self._shutdown_timer.stop()
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage('Shutdown needs attention; the session is retained. ' + self._shutdown_error)
            return
        # finished signals are notifications; only the actual native barriers
        # authorize window destruction (including QThread final TLS cleanup).
        batch_controller = getattr(self.bus, '_process_batch_controller', None)
        if batch_controller is not None and batch_controller.snapshot().get('drain_failed'):
            self._shutdown_error = 'Owned batch cleanup is not confirmed; session retained.'
            self._shutdown_timer.stop()
            self.statusBar().showMessage(self._shutdown_error)
            return
        batches_drained = batch_controller is None or batch_controller.is_drained
        terminal = getattr(self.bus, '_native_terminal', None)
        terminal_drained = terminal is None or terminal.is_drained
        if self.bus.is_drained and self.hub.wait(0) and batches_drained and terminal_drained:
            self._shutdown_timer.stop()
            self._close_state = 'READY'
            QTimer.singleShot(0, self.close)



def main() -> int:
    if any(flag in sys.argv for flag in ('--placement-release-smoke', '--placement-reopen-smoke')):
        from native_studio.placement_release_smoke import placement_release_smoke_main
        return placement_release_smoke_main(sys.argv[1:])
    if '--creator-release-smoke' in sys.argv:
        from native_studio.game_release_smoke import release_smoke_main
        return release_smoke_main(sys.argv[1:])
    if "--game-build-smoke" in sys.argv:
        from native_studio.game_release_smoke import run_game_release_smoke
        index = sys.argv.index("--game-build-smoke")
        if index + 1 >= len(sys.argv):
            return 2
        return run_game_release_smoke(Path(sys.argv[index + 1]))
    if "--check-local-connection" in sys.argv:
        from native_studio.local_connection import write_connection_diagnostic
        return 0 if write_connection_diagnostic() else 2
    if "--hud" in sys.argv:
        from native_studio.dpg_hud import main as hud_main
        return hud_main()
    # Guard: if AI_BS_Studio.exe was accidentally invoked with a .py script argument, exit immediately
    if any(str(arg).lower().endswith(".py") for arg in sys.argv[1:]):
        return 0
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    win = MainWindow()
    apply_dark_titlebar(win)
    win.show()
    if '--game-development' in sys.argv:
        win.jump_to_tab('game_build')
    if '--bs-chat' in sys.argv:
        win.jump_to_tab('ide')
    if '--work-controls' in sys.argv:
        from native_studio.process_batch_view import open_batch_controls
        open_batch_controls(win.bus, win)
    code = app.exec()
    return code


if __name__ == "__main__":
    sys.exit(main())

