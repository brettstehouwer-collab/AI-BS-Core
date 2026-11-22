"""Matrix Blueprint & ROI Financial Architecture View for AI-BS Native Studio (Subtab: ecosystem_blueprint).

1:1 visual & functional parity with EcosystemBlueprintTab.jsx:
- Dynamic TCO & ROI Simulator with interactive sliders:
  1. SaaS Tool Count (1 - 50)
  2. Cost Per Tool / Mo ($20 - $500)
  3. Manual Labor Hours / Wk (1 - 40 hrs @ $50/hr)
  4. AI-BS Sovereign Cluster Maintenance Tier ($500 - $5,000)
- Real-time Financial Outflow Comparison Cards:
  - Traditional Fragmented SaaS Monthly Outflow
  - AI-BS Sovereign Stack Monthly Outflow
  - Monthly Retained Capital
  - 5-Year Cumulative Outflow & 5-Year Net Cash Retained
  - 5-Year ROI %
- 6 Master Operating Hubs Selector with deep architectural entity breakdown
- Matrix Doctor Diagnostic & Self-Healing Engine
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus, PORT_MATRIX, probe_ports, run_matrix_doctor_heal
from native_studio.task_context import Binding, TaskContextAdapter
import hashlib
import json
import uuid
from native_studio.service_orchestrator import sweep_zombie_nodes_native
from native_studio.theme import PALETTE


def _probe_ports_context(*, task_context):
    task_context.progress('reading', 0)
    result = probe_ports()
    task_context.check_cancelled()
    task_context.progress('complete', len(result), len(result))
    # Preserve integer port keys across the explicitly JSON-only task protocol.
    return [[port, data] for port, data in result.items()]




HUBS_DATA = [
    {
        "id": "stehouwer_publishing",
        "title": "I. Stehouwer Publishing & Executive HQ",
        "badge": "OPERATIONS & FINANCE",
        "color": "#00f0ff",
        "desc": "Bare-metal operational nerve center managing physical services, client ledgers, and secure storage.",
        "entities": [
            ("Prestige Mobile Wash CRM", "Commercial pressure washing, chemical estimators & fleet dispatch", "power_washing"),
            ("Master Accounting & Taxes", "Automated P&L balance sheets, expense classification & receipt OCR", "master_accounting"),
            ("Shared Cloud Drive", "Local Google Drive-style cloud storage & document sync", "shared_cloud_drive"),
            ("OSINT Recon & API Hub", "Deep intelligence, domain recon, and B2B lead discovery", "unified_osint"),
        ],
    },
    {
        "id": "hollywood_creation",
        "title": "II. Hollywood & Multimedia Creation Suite",
        "badge": "ENTERTAINMENT PRODUCTION",
        "color": "#ff007f",
        "desc": "Full-spectrum creative studio generating industry-standard scripts, beats, and 4K video.",
        "entities": [
            ("Universal Screenwriting AST", "Hollywood screenplays, FDX serializer & Book-to-Script matrix", "unified_creation"),
            ("AI Music Studio (DAW)", "Pattern-based DAW, MIDI piano roll, 8-track mixer & WASAPI Pro Audio", "music_daw"),
            ("ComfyUI Creative Studio", "ComfyUI Wan2.1 generative video & RTX 4090 NVENC master MP4 export", "comfy_workspace"),
            ("BV-Media Creator Studio", "Dedicated BsMedia-Chat, ChromaDB Media Vault & Storyboard generator", "bv_media_creator"),
        ],
    },
    {
        "id": "noto_hospitality",
        "title": "III. Noto Hospitality OS & Living Enclaves",
        "badge": "PHYSICAL VENUES & LAND",
        "color": "#a371f7",
        "desc": "Autonomous venue management, multi-bar logistics, and acoustic-agricultural enclave telemetry.",
        "entities": [
            ("Notō Multi-Bar Inventory", "Live bottle counting across Grand Rapids/Grand Haven & MLCC POs", "notos_enterprise"),
            ("Banquet Architect 2D/3D", "Interactive floorplans, seating charts & dietary registries", "banquet_architect"),
            ("Project NoCo Living Stage", "23-acre enclave IoT telemetry, solar balance & living stage acoustics", "project_noco"),
        ],
    },
    {
        "id": "creator_revenue",
        "title": "IV. Creator Revenue & Growth Engine",
        "badge": "MONETIZATION & ADS",
        "color": "#10b981",
        "desc": "Commercial growth infrastructure with public storefronts, ad copy generators, and lead scoring.",
        "entities": [
            ("Digital Storefront & Pricing", "Monetize local compute, passes & crypto checkout", "digital_storefront"),
            ("Advertising Studio", "Targeted ad copy, campaign funnels & creative variants", "advertising"),
            ("Personal Brand Studio", "AI ghostwriter & multi-channel social content matrix", "personal_brand"),
            ("Recreational Debut", "Dennis Bell college recruiting portal & mass SMS broadcast suite", "rec_debut"),
        ],
    },
    {
        "id": "neural_intelligence",
        "title": "V. Autonomous Neural Intelligence & IDE",
        "badge": "AI BRAIN & IPC CORE",
        "color": "#f59e0b",
        "desc": "Local AI orchestration running 13 Ollama models, multi-agent DAGs, and sub-ms shared memory.",
        "entities": [
            ("Executive Command Cockpit", "Unified Autonomous Command Bus, 4-Pillar Matrix & Tiered Governance HUD", "executive_cockpit"),
            ("BS-CHAT Pro IDE", "Split-pane sovereign code editor & 121 in-process tool bus", "ide"),
            ("Sovereign Swarm", "14-Agent multi-model collaboration hub running on Port 11434", "sovereign_swarm"),
            ("ChromaDB Vector Store", "Semantic long-term vector memory & RAG knowledge explorer", "agent_memory"),
        ],
    },
    {
        "id": "satellite_applications",
        "title": "VI. Decoupled Satellites & Standalone App Builds",
        "badge": "STANDALONE BUILDS",
        "color": "#38bdf8",
        "desc": "Independently packageable native executables, direct Win32 windows, and GPU trainers.",
        "entities": [
            ("Steam Gaming Hub", "Native game library, launcher & hardware RTX 4090 Game Mode governor", "steam_gaming"),
            ("Phone & Tablet Repair Lab", "Master teardowns, Face ID diagnostics & diode values", "phone_repair"),
            ("Sovereign Bible Hub", "Dual KJV & NIV canonical New Testament reader", "bible_hub"),
            ("AI Compute Lab", "Dear PyGui HUD, CUDA batch workers & MMCSS Pro Audio", "ai_compute"),
        ],
    },
]


class EcosystemBlueprintNativeView(QWidget):
    """Matrix Blueprint & ROI Financial Architecture View."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._active_hub_idx = 0

        # Sliders default values
        self._tool_count = 25
        self._cost_per_tool = 133
        self._labor_hours = 10
        self._maint_tier = 2000
        self.theatrical_mode = False
        self.plays_list = ["JuliesPlace_S1E1", "NoCo_LivingStage_Master", "Echoes_Within_Teaser"]
        self.port_cards: dict[int, dict] = {}
        self.is_probing = False
        self.is_healing = False

        self._build_ui()
        self._recalculate()
        QTimer.singleShot(250, self._probe_matrix_doctor)

    def _build_ui(self) -> None:

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: #070b12;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # 1. Header Bar
        hdr = QFrame()
        hdr.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 12px;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(8, 6, 8, 6)

        title = QLabel("🌐  Matrix Blueprint & <span style='color: #38bdf8;'>Financial Architecture ROI</span>")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #f8fafc;")
        h_lay.addWidget(title)
        h_lay.addStretch()

        btn_doc = QPushButton("🩺 Run Matrix Doctor Auto-Heal")
        btn_doc.setStyleSheet("background: #059669; color: #ffffff; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 8pt;")
        btn_doc.clicked.connect(self._heal_matrix_doctor)
        h_lay.addWidget(btn_doc)

        layout.addWidget(hdr)

        self.lbl_doctor_status = QLabel("")
        self.lbl_doctor_status.setStyleSheet("background: #064e3b; color: #6ee7b7; padding: 6px 12px; border-radius: 6px; font-size: 8pt;")
        self.lbl_doctor_status.hide()
        layout.addWidget(self.lbl_doctor_status)

        # 2. Dynamic TCO & ROI Simulator Card
        sim_frame = QFrame()
        sim_frame.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 14px;")
        s_lay = QVBoxLayout(sim_frame)
        s_lay.setContentsMargins(10, 8, 10, 8)
        s_lay.setSpacing(12)

        s_lay.addWidget(QLabel("💰 <b>Dynamic TCO & ROI Financial Simulator (Interactive Architecture Sliders)</b>"))

        slider_grid = QGridLayout()
        slider_grid.setSpacing(10)

        # Slider 1: Tool Count
        self.lbl_s1 = QLabel(f"Fragmented SaaS Tools: <b>{self._tool_count}</b>")
        self.sl_tools = QSlider(Qt.Orientation.Horizontal)
        self.sl_tools.setRange(1, 50)
        self.sl_tools.setValue(self._tool_count)
        self.sl_tools.valueChanged.connect(self._on_slider_changed)
        slider_grid.addWidget(self.lbl_s1, 0, 0)
        slider_grid.addWidget(self.sl_tools, 0, 1)

        # Slider 2: Cost Per Tool
        self.lbl_s2 = QLabel(f"Avg Cost / Tool / Mo: <b>${self._cost_per_tool}</b>")
        self.sl_cost = QSlider(Qt.Orientation.Horizontal)
        self.sl_cost.setRange(20, 500)
        self.sl_cost.setValue(self._cost_per_tool)
        self.sl_cost.valueChanged.connect(self._on_slider_changed)
        slider_grid.addWidget(self.lbl_s2, 0, 2)
        slider_grid.addWidget(self.sl_cost, 0, 3)

        # Slider 3: Labor Hours
        self.lbl_s3 = QLabel(f"Data Sync Labor: <b>{self._labor_hours} hrs/wk</b> ($50/hr)")
        self.sl_labor = QSlider(Qt.Orientation.Horizontal)
        self.sl_labor.setRange(1, 40)
        self.sl_labor.setValue(self._labor_hours)
        self.sl_labor.valueChanged.connect(self._on_slider_changed)
        slider_grid.addWidget(self.lbl_s3, 1, 0)
        slider_grid.addWidget(self.sl_labor, 1, 1)

        # Slider 4: Maintenance Tier
        self.lbl_s4 = QLabel(f"AI-BS Sovereign Cluster: <b>${self._maint_tier}/mo</b>")
        self.sl_tier = QSlider(Qt.Orientation.Horizontal)
        self.sl_tier.setRange(500, 5000)
        self.sl_tier.setValue(self._maint_tier)
        self.sl_tier.setSingleStep(250)
        self.sl_tier.valueChanged.connect(self._on_slider_changed)
        slider_grid.addWidget(self.lbl_s4, 1, 2)
        slider_grid.addWidget(self.sl_tier, 1, 3)

        s_lay.addLayout(slider_grid)

        # Results KPI Grid
        self.res_grid = QGridLayout()
        self.res_grid.setSpacing(10)

        self.card_saas_mo, self.lbl_saas_val, self.lbl_saas_sub = self._create_metric_card(
            "Traditional SaaS Outflow", "$6,690 / mo", "Monthly recurring drain", "#ef4444", sim_frame
        )
        self.card_aibs_mo, self.lbl_aibs_val, self.lbl_aibs_sub = self._create_metric_card(
            "AI-BS Sovereign Cluster", "$2,000 / mo", "100% Owned Hardware", "#10b981", sim_frame
        )
        self.card_saved_mo, self.lbl_saved_val, self.lbl_saved_sub = self._create_metric_card(
            "Net Cash Retained", "+$4,690 / mo", "Immediate profit boost", "#38bdf8", sim_frame
        )
        self.card_5yr_outflow, self.lbl_5yr_outflow_val, self.lbl_5yr_outflow_sub = self._create_metric_card(
            "5-Yr Outflow: SaaS vs AI-BS", "$401,400 vs $120,000", "Total Capital Saved: $281,400", "#a855f7", sim_frame
        )
        self.card_5yr_roi, self.lbl_5yr_roi_val, self.lbl_5yr_roi_sub = self._create_metric_card(
            "5-Year Cumulative ROI", "234.5%", "Return on Sovereign Investment", "#f59e0b", sim_frame
        )

        self.res_grid.addWidget(self.card_saas_mo, 0, 0)
        self.res_grid.addWidget(self.card_aibs_mo, 0, 1)
        self.res_grid.addWidget(self.card_saved_mo, 0, 2)
        self.res_grid.addWidget(self.card_5yr_outflow, 1, 0, 1, 2)
        self.res_grid.addWidget(self.card_5yr_roi, 1, 2)

        s_lay.addLayout(self.res_grid)
        layout.addWidget(sim_frame)

        # 3. 6 Core Operating Hubs Selector
        hub_frame = QFrame()
        hub_frame.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 14px;")
        h_lay2 = QVBoxLayout(hub_frame)
        h_lay2.setContentsMargins(10, 8, 10, 8)
        h_lay2.setSpacing(10)

        h_lay2.addWidget(QLabel("🏛️ <b>The 6 Sovereign Operating Hubs & Architecture Matrix</b>"))

        # Hub Buttons row
        hub_btn_row = QHBoxLayout()
        self.hub_btns = []
        for idx, h in enumerate(HUBS_DATA):
            btn = QPushButton(h["title"].split(".")[1].strip())
            is_active = (idx == self._active_hub_idx)
            btn.setStyleSheet(
                f"QPushButton {{ background: {'#1e293b' if is_active else 'transparent'}; color: {'#38bdf8' if is_active else '#94a3b8'}; border: 1px solid {'#38bdf8' if is_active else '#1e293b'}; border-radius: 4px; padding: 6px 10px; font-weight: bold; font-size: 8pt; }}"
                "QPushButton:hover { background: #334155; color: #ffffff; }"
            )
            btn.clicked.connect(lambda checked, i=idx: self._select_hub(i))
            self.hub_btns.append(btn)
            hub_btn_row.addWidget(btn)

        h_lay2.addLayout(hub_btn_row)

        # Hub details container
        self.hub_detail_lay = QVBoxLayout()
        self._render_hub_details()
        h_lay2.addLayout(self.hub_detail_lay)

        layout.addWidget(hub_frame)

        # 4. Section 5: Theatrical Film Hub (NoCo Vision)
        self.theatrical_frame = self._build_theatrical_hub()
        layout.addWidget(self.theatrical_frame)

        # 5. Matrix Doctor 24-Port Diagnostic & Self-Healing Deck
        self.doctor_frame = self._build_matrix_doctor_suite()
        layout.addWidget(self.doctor_frame)

        # 6. Bottom Investment Banner
        self.banner_frame = self._build_invest_banner()
        layout.addWidget(self.banner_frame)

        layout.addStretch()

        scroll.setWidget(container)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

    def _build_theatrical_hub(self) -> QFrame:
        tf = QFrame()
        tf.setStyleSheet("background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 18px;")
        t_lay = QVBoxLayout(tf)
        t_lay.setContentsMargins(14, 12, 14, 12)
        t_lay.setSpacing(14)

        top_row = QHBoxLayout()
        lbl_title = QLabel("🎬 <b>THEATRICAL FILM HUB & VIRTUAL PRODUCTION</b>")
        lbl_title.setStyleSheet("color: #ff007f; font-size: 11pt; font-weight: 800; text-transform: uppercase;")
        top_row.addWidget(lbl_title)
        top_row.addStretch()

        self.btn_theatrical_toggle = QPushButton("ENABLE THEATRICAL OVERRIDE (PAUSE ECO)")
        self.btn_theatrical_toggle.setStyleSheet(
            "background: #10b981; color: #ffffff; border: none; padding: 7px 16px; border-radius: 6px; font-weight: bold; font-size: 8pt; cursor: pointer;"
        )
        self.btn_theatrical_toggle.clicked.connect(self._toggle_theatrical_override)
        top_row.addWidget(self.btn_theatrical_toggle)
        t_lay.addLayout(top_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(14)

        # Left: Virtual Set Scripts
        scripts_box = QFrame()
        scripts_box.setStyleSheet("background: rgba(255,255,255,0.03); border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        sb_lay = QVBoxLayout(scripts_box)
        sb_lay.setContentsMargins(8, 8, 8, 8)
        sb_lay.setSpacing(8)

        lbl_s_title = QLabel("VIRTUAL SET SCRIPTS (CHROMADB)")
        lbl_s_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: bold;")
        sb_lay.addWidget(lbl_s_title)

        inp_row = QHBoxLayout()
        self.txt_new_play = QLineEdit()
        self.txt_new_play.setPlaceholderText("New Play Name (e.g. JuliesPlace_S1E1)")
        self.txt_new_play.setStyleSheet("background: #000000; border: 1px solid #30363d; color: #ffffff; padding: 6px 10px; border-radius: 4px; font-size: 8pt;")
        btn_create_play = QPushButton("Create")
        btn_create_play.setStyleSheet("background: #3b82f6; color: #ffffff; border: none; padding: 6px 14px; border-radius: 4px; font-size: 8pt; font-weight: bold;")
        btn_create_play.clicked.connect(self._create_theatrical_play)
        inp_row.addWidget(self.txt_new_play, 1)
        inp_row.addWidget(btn_create_play)
        sb_lay.addLayout(inp_row)

        self.plays_container = QVBoxLayout()
        self.plays_container.setSpacing(6)
        self._render_plays_list()
        sb_lay.addLayout(self.plays_container)
        content_row.addWidget(scripts_box, 1)

        # Right: Unreal Engine 5.8 Telemetry
        ue_box = QFrame()
        ue_box.setStyleSheet("background: rgba(255,255,255,0.03); border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        ue_lay = QVBoxLayout(ue_box)
        ue_lay.setContentsMargins(8, 8, 8, 8)
        ue_lay.setSpacing(6)

        lbl_ue_title = QLabel("UNREAL ENGINE 5.8 TELEMETRY")
        lbl_ue_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: bold;")
        ue_lay.addWidget(lbl_ue_title)

        self.lbl_director_status = QLabel("<b>Director Daemon:</b> <span style='color: #ef4444;'>SUSPENDED</span>")
        self.lbl_director_status.setStyleSheet("font-size: 8pt; color: #cbd5e1;")
        ue_lay.addWidget(self.lbl_director_status)

        lbl_sig = QLabel("<b>Signaling Server:</b> 127.0.0.1:8888")
        lbl_sig.setStyleSheet("font-size: 8pt; color: #cbd5e1;")
        ue_lay.addWidget(lbl_sig)

        lbl_scene = QLabel("<b>Active Scene:</b> Julie's Place - Master Sequence")
        lbl_scene.setStyleSheet("font-size: 8pt; color: #cbd5e1;")
        ue_lay.addWidget(lbl_scene)

        lbl_pipe = QLabel("<b>Asset Pipeline:</b> C:\\AI-BS\\JuliesPlace\\RawAssets")
        lbl_pipe.setStyleSheet("font-size: 8pt; color: #cbd5e1;")
        ue_lay.addWidget(lbl_pipe)

        lbl_note = QLabel("* Theatrical override suspends background Crypto TWAP mining to allocate RTX 4090 VRAM entirely to Unreal Engine Path Tracing.")
        lbl_note.setStyleSheet("color: #f59e0b; font-size: 7.5pt;")
        lbl_note.setWordWrap(True)
        ue_lay.addWidget(lbl_note)
        content_row.addWidget(ue_box, 1)

        t_lay.addLayout(content_row)
        return tf

    def _render_plays_list(self) -> None:
        while self.plays_container.count():
            item = self.plays_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for play in self.plays_list:
            row = QFrame()
            row.setStyleSheet("background: #000000; border: 1px solid #222222; border-radius: 4px; padding: 4px 8px;")
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(4, 2, 4, 2)
            lbl = QLabel(f"🗄️ {play}")
            lbl.setStyleSheet("color: #e2e8f0; font-size: 7.5pt;")
            r_lay.addWidget(lbl)
            self.plays_container.addWidget(row)

    def _toggle_theatrical_override(self) -> None:
        self.theatrical_mode = not self.theatrical_mode
        if self.theatrical_mode:
            self.btn_theatrical_toggle.setText("DISABLE THEATRICAL OVERRIDE")
            self.btn_theatrical_toggle.setStyleSheet("background: #ef4444; color: #ffffff; border: none; padding: 7px 16px; border-radius: 6px; font-weight: bold; font-size: 8pt;")
            self.lbl_director_status.setText("<b>Director Daemon:</b> <span style='color: #10b981;'>ACTIVE</span>")
        else:
            self.btn_theatrical_toggle.setText("ENABLE THEATRICAL OVERRIDE (PAUSE ECO)")
            self.btn_theatrical_toggle.setStyleSheet("background: #10b981; color: #ffffff; border: none; padding: 7px 16px; border-radius: 6px; font-weight: bold; font-size: 8pt;")
            self.lbl_director_status.setText("<b>Director Daemon:</b> <span style='color: #ef4444;'>SUSPENDED</span>")

    def _create_theatrical_play(self) -> None:
        name = self.txt_new_play.text().strip()
        if name and name not in self.plays_list:
            self.plays_list.append(name)
            self.txt_new_play.clear()
            self._render_plays_list()

    def _build_matrix_doctor_suite(self) -> QFrame:
        df = QFrame()
        df.setStyleSheet("background: rgba(15, 23, 42, 0.95); border: 1px solid #1e293b; border-radius: 12px; padding: 20px;")
        d_lay = QVBoxLayout(df)
        d_lay.setContentsMargins(16, 14, 16, 14)
        d_lay.setSpacing(14)

        # Header row
        top_row = QHBoxLayout()
        glow_dot = QFrame()
        glow_dot.setFixedSize(10, 10)
        glow_dot.setStyleSheet("background: #00f0ff; border-radius: 5px; box-shadow: 0 0 8px #00f0ff;")
        top_row.addWidget(glow_dot)

        lbl_head = QLabel("🩺 <b>MATRIX DOCTOR: 25-PORT DIAGNOSTIC & SELF-HEALING SUITE</b>")
        lbl_head.setStyleSheet("color: #ffffff; font-size: 11pt; font-weight: 800;")
        top_row.addWidget(lbl_head)
        top_row.addStretch()

        self.btn_probe = QPushButton(f"🔄 Probe {len(PORT_MATRIX)} Ports")
        self.btn_probe.setStyleSheet(
            "background: #1e293b; color: #00f0ff; border: 1px solid #00f0ff; padding: 6px 14px; border-radius: 6px; font-size: 8pt; font-weight: bold; cursor: pointer;"
        )
        self.btn_probe.clicked.connect(self._probe_matrix_doctor)
        top_row.addWidget(self.btn_probe)

        self.btn_sweep_zombies = QPushButton("🧹 Sweep Zombie Nodes")
        self.btn_sweep_zombies.setStyleSheet(
            "background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; padding: 6px 14px; border-radius: 6px; font-size: 8pt; font-weight: bold; cursor: pointer;"
        )
        self.btn_sweep_zombies.clicked.connect(self._sweep_zombies)
        top_row.addWidget(self.btn_sweep_zombies)

        self.btn_heal = QPushButton("⚡ Run Automated Self-Heal")
        self.btn_heal.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #0284c7); color: #ffffff; border: none; padding: 6px 18px; border-radius: 6px; font-size: 8pt; font-weight: bold; cursor: pointer;"
        )
        self.btn_heal.clicked.connect(self._heal_matrix_doctor)
        top_row.addWidget(self.btn_heal)

        d_lay.addLayout(top_row)

        # Heal status message
        self.lbl_heal_msg = QLabel()
        self.lbl_heal_msg.setStyleSheet("padding: 8px 12px; background: rgba(5, 150, 105, 0.2); border: 1px solid #059669; border-radius: 6px; font-size: 8pt; color: #6ee7b7;")
        self.lbl_heal_msg.hide()
        d_lay.addWidget(self.lbl_heal_msg)

        # 4 Metric Cards strip
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)

        card_score, self.lbl_score_val, self.lbl_score_sub = self._create_metric_card(
            "Ecosystem Health Score", "100%", "Status: OPTIMAL", "#10b981", df
        )
        card_online, self.lbl_ports_online_val, self.lbl_ports_online_sub = self._create_metric_card(
            "Online Ports", f"{len(PORT_MATRIX)} / {len(PORT_MATRIX)} Online", "All sockets conflict-free", "#38bdf8", df
        )
        card_crit, self.lbl_crit_val, self.lbl_crit_sub = self._create_metric_card(
            "Critical Services", "6 / 6 (100%)", "Core infrastructure up", "#a855f7", df
        )
        card_locks, self.lbl_locks_val, self.lbl_locks_sub = self._create_metric_card(
            "Stale Locks / PIDs", "0 Managed", "Zero dead lockfiles", "#f59e0b", df
        )

        metrics_row.addWidget(card_score)
        metrics_row.addWidget(card_online)
        metrics_row.addWidget(card_crit)
        metrics_row.addWidget(card_locks)
        d_lay.addLayout(metrics_row)

        # 25-Port Badges Grid
        lbl_grid_title = QLabel("LIVE ECOSYSTEM SOCKET MATRIX (PORTS 80 - 11435)")
        lbl_grid_title.setStyleSheet("color: #64748b; font-size: 7.5pt; font-weight: bold; margin-top: 6px;")
        d_lay.addWidget(lbl_grid_title)

        ports_grid = QGridLayout()
        ports_grid.setSpacing(8)

        ports_list = sorted(PORT_MATRIX.keys())
        cols = 4

        for idx, port in enumerate(ports_list):
            name, cat = PORT_MATRIX[port]
            card = QFrame()
            card.setStyleSheet("background: #0b1120; border: 1px solid #1e293b; border-radius: 6px; padding: 6px 10px;")
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(6, 4, 6, 4)
            c_lay.setSpacing(6)

            info_lay = QVBoxLayout()
            info_lay.setContentsMargins(0, 0, 0, 0)
            info_lay.setSpacing(2)

            lbl_p_name = QLabel(f"<b>{name}</b>")
            lbl_p_name.setStyleSheet("color: #ffffff; font-size: 8pt;")
            lbl_p_sub = QLabel(f"Port {port} • {cat}")
            lbl_p_sub.setStyleSheet("color: #64748b; font-size: 7pt;")
            info_lay.addWidget(lbl_p_name)
            info_lay.addWidget(lbl_p_sub)
            c_lay.addLayout(info_lay)

            c_lay.addStretch()

            lbl_status = QLabel("ONLINE")
            lbl_status.setStyleSheet("background: #10b981; color: #ffffff; border-radius: 3px; padding: 2px 6px; font-size: 7pt; font-weight: bold;")
            c_lay.addWidget(lbl_status)

            self.port_cards[port] = {
                "card": card,
                "name": lbl_p_name,
                "sub": lbl_p_sub,
                "badge": lbl_status,
                "critical": port in (8080, 8000, 8002, 8010, 5173, 11434),
            }

            ports_grid.addWidget(card, idx // cols, idx % cols)

        d_lay.addLayout(ports_grid)
        return df

    def _build_invest_banner(self) -> QFrame:
        bf = QFrame()
        bf.setStyleSheet("background: #064e3b; border: 1px solid #059669; border-radius: 8px; padding: 14px;")
        b_lay = QVBoxLayout(bf)
        b_lay.setContentsMargins(12, 10, 12, 10)
        b_lay.setSpacing(4)
        b_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t = QLabel("<b>INVEST IN AI-BS: ONE PLATFORM. ZERO SUBSCRIPTIONS.</b>")
        t.setStyleSheet("color: #ffffff; font-size: 9.5pt; font-weight: 800; letter-spacing: 0.5px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_lay.addWidget(t)

        s = QLabel("Keep your critical business data private. Keep your revenue in your company.")
        s.setStyleSheet("color: #a7f3d0; font-size: 8pt;")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_lay.addWidget(s)

        return bf

    def _probe_matrix_doctor(self) -> None:
        if self.is_probing or getattr(self, '_probe_closed', False):
            return
        if getattr(self, '_probe_adapter', None) is None:
            self._probe_adapter = TaskContextAdapter(self.bus)
            self._probe_adapter.task_event.connect(self._on_probe_task_event)
            self._probe_workspace = 'ports_' + uuid.uuid4().hex
            self._probe_generation = 0
        self._probe_generation += 1
        self._probe_revision = self._port_matrix_digest()
        binding = Binding(self._probe_workspace, 'local_port_monitor', self._probe_generation,
                          self._probe_revision, 'probe_ports', 'io')
        self.is_probing = True
        self._probe_result_applied = False
        self.btn_probe.setText("Probing...")
        self.btn_probe.setEnabled(False)
        try:
            self._probe_adapter.bind(binding)
            self._probe_task_id = self._probe_adapter.submit(binding, _probe_ports_context, deadline_seconds=10)
        except (ValueError, RuntimeError):
            self._finish_probe_unconfirmed()

    @staticmethod
    def _port_matrix_digest():
        return hashlib.sha256(json.dumps(sorted(PORT_MATRIX.items()), separators=(',', ':')).encode('utf-8')).hexdigest()

    def _finish_probe_unconfirmed(self):
        self.is_probing = False
        self.btn_probe.setEnabled(True)
        self.btn_probe.setText(f'🔄 Probe {len(PORT_MATRIX)} Ports')
        self.lbl_score_sub.setText('Probe not confirmed; previous status retained.')

    def _on_probe_task_event(self, raw):
        if getattr(self, '_probe_closed', False):
            return
        event = json.loads(raw)
        if event['task_id'] != getattr(self, '_probe_task_id', None):
            return
        kind, data = event['kind'], event['data']
        if kind == 'progress':
            self.btn_probe.setText('Updating status...' if data['stage'] == 'complete' else 'Probing...')
        elif kind == 'result' and self._port_matrix_digest() == self._probe_revision:
            if (type(data) is list and len(data) == len(PORT_MATRIX)
                    and all(type(row) is list and len(row) == 2 and type(row[0]) is int
                            and row[0] in PORT_MATRIX and type(row[1]) is dict for row in data)
                    and len({row[0] for row in data}) == len(PORT_MATRIX)):
                self._on_probe_result(dict(data))
                self._probe_result_applied = True
        elif kind == 'finished':
            self._probe_task_id = None
            if not self._probe_result_applied:
                self._finish_probe_unconfirmed()

    def shutdown(self):
        self._probe_closed = True
        if getattr(self, '_probe_adapter', None) is not None:
            self._probe_adapter.shutdown()

    def _on_probe_result(self, ports_data: dict) -> None:
        self.is_probing = False
        self.btn_probe.setText(f"🔄 Probe {len(PORT_MATRIX)} Ports")
        self.btn_probe.setEnabled(True)

        if not isinstance(ports_data, dict):
            return

        online_count = sum(1 for p in ports_data.values() if p.get("online"))
        total_count = len(PORT_MATRIX)
        health_score = int((online_count / max(1, total_count)) * 100)

        crit_online = sum(1 for p, d in ports_data.items() if d.get("online") and p in (8080, 8000, 8002, 8010, 5173, 11434))
        total_crit = 6

        status_text = "OPTIMAL" if health_score >= 80 else ("DEGRADED" if health_score >= 40 else "CRITICAL")
        color = "#10b981" if health_score >= 80 else ("#f59e0b" if health_score >= 40 else "#ef4444")

        self.lbl_score_val.setText(f"{health_score}%")
        self.lbl_score_val.setStyleSheet(f"color: {color}; font-size: 11pt; font-weight: bold;")
        self.lbl_score_sub.setText(f"Status: {status_text}")

        self.lbl_ports_online_val.setText(f"{online_count} / {total_count} Online")
        self.lbl_crit_val.setText(f"{crit_online} / {total_crit} ({int((crit_online / total_crit) * 100)}%)")

        for port, entry in self.port_cards.items():
            p_res = ports_data.get(port, {})
            is_up = bool(p_res.get("online"))
            badge = entry["badge"]
            if is_up:
                badge.setText("ONLINE")
                badge.setStyleSheet("background: #10b981; color: #ffffff; border-radius: 3px; padding: 2px 6px; font-size: 7pt; font-weight: bold;")
            else:
                badge.setText("OFFLINE")
                badge.setStyleSheet("background: #1e293b; color: #f87171; border: 1px solid #334155; border-radius: 3px; padding: 2px 6px; font-size: 7pt; font-weight: bold;")

    def _sweep_zombies(self) -> None:
        self.btn_sweep_zombies.setText("Sweeping Zombies...")
        self.btn_sweep_zombies.setEnabled(False)
        self.lbl_heal_msg.show()
        self.lbl_heal_msg.setText("Scanning host OS processes for zombie nodes with zero listening sockets...")
        self.bus.submit(sweep_zombie_nodes_native, False, on_result=self._on_sweep_zombies_result)

    def _on_sweep_zombies_result(self, res: dict) -> None:
        self.btn_sweep_zombies.setText("🧹 Sweep Zombie Nodes")
        self.btn_sweep_zombies.setEnabled(True)
        count = res.get("terminated_count", 0) if isinstance(res, dict) else 0
        scanned = res.get("total_scanned", 0) if isinstance(res, dict) else 0
        self.lbl_heal_msg.setText(f"✅ Zombie Sweep Complete: Inspected {scanned} PIDs. Terminated {count} defunct zombie nodes.")
        QTimer.singleShot(4000, lambda: self.lbl_heal_msg.hide())
        self._probe_matrix_doctor()

    def _heal_matrix_doctor(self) -> None:
        if self.is_healing:
            return
        self.is_healing = True
        self.btn_heal.setText("Healing System...")
        self.btn_heal.setEnabled(False)
        self.lbl_heal_msg.show()
        self.lbl_heal_msg.setText("Running automated self-healing routines across all ports, SQLite locks, and NVML telemetry...")
        self.bus.submit(run_matrix_doctor_heal, on_result=self._on_heal_result)

    def _on_heal_result(self, heal_data: dict) -> None:
        self.is_healing = False
        self.btn_heal.setText("⚡ Run Automated Self-Heal")
        self.btn_heal.setEnabled(True)

        actions = heal_data.get("actions_taken", []) if isinstance(heal_data, dict) else []
        action_count = len(actions)
        self.lbl_heal_msg.setText(f"✅ Auto-Heal Complete: Cleared {action_count} stale lockfiles. Master WAL checkpoint applied.")
        QTimer.singleShot(4000, lambda: self.lbl_heal_msg.hide())
        self._probe_matrix_doctor()

    def _run_matrix_doctor(self) -> None:
        self._heal_matrix_doctor()


    def _create_metric_card(self, title: str, val: str, sub: str, color: str, parent: QWidget | None = None) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame(parent)
        card.setStyleSheet(f"background: #070b12; border: 1px solid #1e293b; border-top: 2px solid {color}; border-radius: 6px; padding: 10px;")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94a3b8; font-size: 7.5pt; font-weight: 600;")
        lay.addWidget(lbl_t)

        lbl_v = QLabel(val)
        lbl_v.setObjectName("Val")
        lbl_v.setStyleSheet(f"color: {color}; font-size: 11pt; font-weight: bold;")
        lay.addWidget(lbl_v)

        lbl_s = QLabel(sub)
        lbl_s.setObjectName("Sub")
        lbl_s.setStyleSheet("color: #64748b; font-size: 7.5pt;")
        lay.addWidget(lbl_s)
        return card, lbl_v, lbl_s

    def _on_slider_changed(self) -> None:
        self._tool_count = self.sl_tools.value()
        self._cost_per_tool = self.sl_cost.value()
        self._labor_hours = self.sl_labor.value()
        self._maint_tier = self.sl_tier.value()

        self.lbl_s1.setText(f"Fragmented SaaS Tools: <b>{self._tool_count}</b>")
        self.lbl_s2.setText(f"Avg Cost / Tool / Mo: <b>${self._cost_per_tool}</b>")
        self.lbl_s3.setText(f"Data Sync Labor: <b>{self._labor_hours} hrs/wk</b> ($50/hr)")
        self.lbl_s4.setText(f"AI-BS Sovereign Cluster: <b>${self._maint_tier}/mo</b>")

        self._recalculate()

    def _recalculate(self) -> None:
        # Traditional SaaS monthly = (tools * cost) + (hours * 4.33 * $50) + $1,200 (cloud glue)
        monthly_saas = (self._tool_count * self._cost_per_tool) + int(self._labor_hours * 4.33 * 50) + 1200
        monthly_aibs = self._maint_tier
        monthly_retained = monthly_saas - monthly_aibs

        five_yr_saas = monthly_saas * 60
        five_yr_aibs = monthly_aibs * 60
        five_yr_savings = five_yr_saas - five_yr_aibs
        roi_pct = (five_yr_savings / max(1, five_yr_aibs)) * 100

        self.lbl_saas_val.setText(f"${monthly_saas:,} / mo")
        self.lbl_aibs_val.setText(f"${monthly_aibs:,} / mo")
        self.lbl_saved_val.setText(f"+${monthly_retained:,} / mo")

        self.lbl_5yr_outflow_val.setText(f"${five_yr_saas:,} vs ${five_yr_aibs:,}")
        self.lbl_5yr_outflow_sub.setText(f"Total 5-Year Capital Saved: +${five_yr_savings:,}")

        self.lbl_5yr_roi_val.setText(f"{roi_pct:.1f}%")

    def _select_hub(self, index: int) -> None:
        self._active_hub_idx = index
        for idx, btn in enumerate(self.hub_btns):
            is_active = (idx == index)
            btn.setStyleSheet(
                f"QPushButton {{ background: {'#1e293b' if is_active else 'transparent'}; color: {'#38bdf8' if is_active else '#94a3b8'}; border: 1px solid {'#38bdf8' if is_active else '#1e293b'}; border-radius: 4px; padding: 6px 10px; font-weight: bold; font-size: 8pt; }}"
                "QPushButton:hover { background: #334155; color: #ffffff; }"
            )
        self._render_hub_details()

    def _render_hub_details(self) -> None:
        # Clear existing
        while self.hub_detail_lay.count():
            item = self.hub_detail_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        hub = HUBS_DATA[self._active_hub_idx]

        desc_lbl = QLabel(f"<b>{hub['title']}</b> — {hub['desc']}")
        desc_lbl.setStyleSheet(f"color: {hub['color']}; font-size: 9pt; margin-top: 6px;")
        self.hub_detail_lay.addWidget(desc_lbl)

        grid = QGridLayout()
        grid.setSpacing(8)

        for col, (name, edesc, tab_key) in enumerate(hub["entities"]):
            card = QFrame()
            card.setStyleSheet("background: #070b12; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(4, 2, 4, 2)
            c_lay.setSpacing(4)

            top_row = QHBoxLayout()
            lbl_n = QLabel(f"<b>{name}</b>")
            lbl_n.setStyleSheet("color: #f8fafc; font-size: 8.5pt;")
            top_row.addWidget(lbl_n)
            top_row.addStretch()

            btn_jump = QPushButton("Open Subsystem ↗")
            btn_jump.setStyleSheet("background: #1e293b; color: #38bdf8; border-radius: 4px; padding: 3px 8px; font-size: 7.5pt; font-weight: bold;")
            btn_jump.clicked.connect(lambda checked, tk=tab_key: self._jump_tab(tk))
            top_row.addWidget(btn_jump)
            c_lay.addLayout(top_row)

            lbl_d = QLabel(edesc)
            lbl_d.setStyleSheet("color: #94a3b8; font-size: 7.5pt;")
            lbl_d.setWordWrap(True)
            c_lay.addWidget(lbl_d)

            grid.addWidget(card, col // 2, col % 2)

        self.hub_detail_lay.addLayout(grid)

    def _jump_tab(self, tab_key: str) -> None:
        parent = self.window()
        if hasattr(parent, "jump_to_tab"):
            parent.jump_to_tab(tab_key)
