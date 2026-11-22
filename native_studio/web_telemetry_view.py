"""Web Traffic & Telemetry Suite View for AI-BS Native Studio (Subtab: beta).

1:1 visual & functional parity with BetaAnalyticsTab.jsx:
- 6 Sub-View Navigation Tabs: User Sessions, Ecosystem Ports, Site Traffic, Wire Packets, OTA Sensors, API Compute
- 5 Top KPI Telemetry Cards (Pageviews, Unique Visitors, Dwell Time, Bandwidth, 18 Matrix Ports)
- Decoupled L7 Transactions & Physical Wire Frames Stream Table with SHA-256 Wire Hashes
- Multi-Domain Selector (Stehouwer Publishing vs The Simple Chef) and Unavailable telemetry until a verified capture source is connected
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE


PORTS_18 = [
    ("80", "Nginx Gateway", "UNAVAILABLE", "#94a3b8"),
    ("3001", "Node Backend", "UNAVAILABLE", "#94a3b8"),
    ("5173", "Vite Dev & Desktop Studio", "UNAVAILABLE", "#94a3b8"),
    ("8000", "Go Gateway", "UNAVAILABLE", "#94a3b8"),
    ("8002", "ChromaDB Vector Store", "UNAVAILABLE", "#94a3b8"),
    ("8005", "Broadcast Daemon", "UNAVAILABLE", "#94a3b8"),
    ("8006", "Social Hub (Twitch/IRC)", "UNAVAILABLE", "#94a3b8"),
    ("8007", "Crypto Swarm & Scalp Bot", "UNAVAILABLE", "#94a3b8"),
    ("8010", "SHM Windows Ring Telemetry", "UNAVAILABLE", "#94a3b8"),
    ("8013", "VST3 Audio Bridge", "UNAVAILABLE", "#94a3b8"),
    ("8080", "FastAPI Core Engine", "UNAVAILABLE", "#94a3b8"),
    ("8085", "Ubuntu-Bio Bridge", "UNAVAILABLE", "#94a3b8"),
    ("8088", "Broadcast Kernel & NVENC", "UNAVAILABLE", "#94a3b8"),
    ("8089", "WSL HLS Ingest", "UNAVAILABLE", "#94a3b8"),
    ("8099", "Gemini MCP Gateway", "UNAVAILABLE", "#94a3b8"),
    ("8189", "ComfyUI Secondary / Screenplay", "UNAVAILABLE", "#94a3b8"),
    ("8888", "Unreal Engine Signaling", "UNAVAILABLE", "#94a3b8"),
    ("11434", "Ollama Host Swarm", "UNAVAILABLE", "#94a3b8"),
    ("11435", "Ollama E-Drive Extended", "UNAVAILABLE", "#94a3b8"),
]


class WebTelemetryNativeView(QWidget):
    """Web Traffic & Telemetry Suite View matching BetaAnalyticsTab.jsx."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._traffic_records = []
        self._build_ui()
        self._render_wire_table()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Header Bar
        hdr = QFrame()
        hdr.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 12px;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(8, 6, 8, 6)

        title = QLabel("📈  Web Traffic & <span style='color: #38bdf8;'>Telemetry Suite</span>")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #f8fafc;")
        h_lay.addWidget(title)
        h_lay.addStretch()

        self.cmb_domain = QComboBox()
        self.cmb_domain.addItems(["Stehouwer Publishing (Main)", "The Simple Chef (Hospitality)", "All Monitored Domains"])
        self.cmb_domain.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        h_lay.addWidget(self.cmb_domain)
        main_layout.addWidget(hdr)

        # 2. 5 Top KPI Cards
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)

        self.kpi_cards_data = [
            ("Total Pageviews", "Unavailable", "No verified source", "#94a3b8"),
            ("Unique Visitors", "Unavailable", "No verified source", "#94a3b8"),
            ("Avg Dwell Time", "Unavailable", "No verified source", "#94a3b8"),
            ("Bandwidth Flow", "Unavailable", "No verified source", "#94a3b8"),
            ("Matrix Ports", "Unavailable", "No health receipts", "#94a3b8"),
        ]

        for col, (title_t, val_t, sub_t, color) in enumerate(self.kpi_cards_data):
            card = QFrame()
            card.setStyleSheet(f"background: #0d121d; border: 1px solid #1e293b; border-top: 2px solid {color}; border-radius: 6px; padding: 10px;")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(4, 2, 4, 2)
            c_lay.setSpacing(2)

            lbl_t = QLabel(title_t)
            lbl_t.setStyleSheet("color: #94a3b8; font-size: 7.5pt; font-weight: 600;")
            c_lay.addWidget(lbl_t)

            lbl_v = QLabel(val_t)
            lbl_v.setStyleSheet(f"color: {color}; font-size: 11pt; font-weight: bold;")
            c_lay.addWidget(lbl_v)

            lbl_s = QLabel(sub_t)
            lbl_s.setStyleSheet("color: #64748b; font-size: 7pt;")
            c_lay.addWidget(lbl_s)

            kpi_grid.addWidget(card, 0, col)

        main_layout.addLayout(kpi_grid)

        # 3. Sub-View Navigation Switcher (6 tabs)
        nav_row = QHBoxLayout()
        self.nav_btns = []
        subtabs = [
            ("user_sessions", "👤 User Presence"),
            ("ecosystem_ports", "🌐 18-Port Matrix"),
            ("wire_packets", "⚡ Wire Hashes & L7 Stream"),
            ("site_traffic", "📊 Site Traffic Analytics"),
            ("air_sensors", "📡 OTA RF Sensors"),
            ("api_compute", "🧪 FastAPI & Ollama Latency"),
        ]

        self.deck = QStackedWidget()

        for idx, (skey, slabel) in enumerate(subtabs):
            btn = QPushButton(slabel)
            is_first = (idx == 2)  # Default to Wire Packets
            btn.setStyleSheet(
                f"QPushButton {{ background: {'#1e293b' if is_first else 'transparent'}; color: {'#38bdf8' if is_first else '#94a3b8'}; border: 1px solid {'#38bdf8' if is_first else '#1e293b'}; border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 8pt; }}"
                "QPushButton:hover { background: #334155; color: #ffffff; }"
            )
            btn.clicked.connect(lambda checked, i=idx: self._set_subview(i))
            self.nav_btns.append(btn)
            nav_row.addWidget(btn)

        nav_row.addStretch()
        main_layout.addLayout(nav_row)

        # Build Sub-Views
        # Page 0: User Presence
        p_users = self._build_users_page()
        self.deck.addWidget(p_users)

        # Page 1: Ecosystem Ports
        p_ports = self._build_ports_page()
        self.deck.addWidget(p_ports)

        # Page 2: Wire Packets Stream (Default)
        p_wire = self._build_wire_page()
        self.deck.addWidget(p_wire)

        # Page 3: Site Traffic
        p_traffic = self._build_traffic_page()
        self.deck.addWidget(p_traffic)

        # Page 4: OTA Sensors
        p_sensors = self._build_sensors_page()
        self.deck.addWidget(p_sensors)

        # Page 5: API Compute
        p_api = self._build_api_page()
        self.deck.addWidget(p_api)

        self.deck.setCurrentIndex(2)
        main_layout.addWidget(self.deck, 1)

    def _set_subview(self, index: int) -> None:
        self.deck.setCurrentIndex(index)
        for idx, b in enumerate(self.nav_btns):
            is_active = (idx == index)
            b.setStyleSheet(
                f"QPushButton {{ background: {'#1e293b' if is_active else 'transparent'}; color: {'#38bdf8' if is_active else '#94a3b8'}; border: 1px solid {'#38bdf8' if is_active else '#1e293b'}; border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 8pt; }}"
                "QPushButton:hover { background: #334155; color: #ffffff; }"
            )

    def _build_wire_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Controls
        c_row = QHBoxLayout()
        c_row.addWidget(QLabel("⚡ Decoupled L7 Transactions & Physical Wire Frames Stream:"))
        c_row.addStretch()

        btn_pause = QPushButton("Feed unavailable")
        btn_pause.setStyleSheet("background: #1e293b; color: #f8fafc; border-radius: 4px; padding: 4px 10px; font-size: 8pt;")
        btn_pause.setEnabled(False)
        c_row.addWidget(btn_pause)
        lay.addLayout(c_row)

        # Wire Table
        self.wire_table = QTableWidget()
        self.wire_table.setColumnCount(6)
        self.wire_table.setHorizontalHeaderLabels(["Timestamp", "Method", "Route / Endpoint", "Wire SHA-256 Hash", "Status", "Latency"])
        self.wire_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.wire_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.wire_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.wire_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.wire_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.wire_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.wire_table.setStyleSheet(
            "QTableWidget { background: #05080f; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; font-family: monospace; font-size: 8pt; }"
            "QHeaderView::section { background: #0f141f; color: #94a3b8; font-weight: bold; border: 1px solid #1e293b; padding: 5px; font-family: sans-serif; }"
        )
        lay.addWidget(self.wire_table, 1)
        return w

    def _build_ports_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        grid = QGridLayout()
        grid.setSpacing(8)

        for idx, (port, service, status, color) in enumerate(PORTS_18):
            row = idx // 4
            col = idx % 4
            card = QFrame()
            card.setStyleSheet(f"background: #0d121d; border: 1px solid #1e293b; border-left: 3px solid {color}; border-radius: 6px; padding: 8px;")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(4, 2, 4, 2)
            c_lay.setSpacing(2)

            lbl_p = QLabel(f"<b>Port :{port}</b>")
            lbl_p.setStyleSheet("color: #f8fafc; font-size: 9pt;")
            lbl_s = QLabel(service)
            lbl_s.setStyleSheet("color: #94a3b8; font-size: 7.5pt;")
            lbl_st = QLabel(f"● {status}")
            lbl_st.setStyleSheet(f"color: {color}; font-size: 7.5pt; font-weight: bold;")

            c_lay.addWidget(lbl_p)
            c_lay.addWidget(lbl_s)
            c_lay.addWidget(lbl_st)
            grid.addWidget(card, row, col)

        lay.addLayout(grid)
        lay.addStretch()
        return w

    def _build_users_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("User session telemetry unavailable: no verified session source connected")
        lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 9.5pt;")
        lay.addWidget(lbl)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Session ID", "User Identity", "Role / Authority", "Host IP", "Active Subsystem"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("QTableWidget { background: #05080f; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; }")
        table.setRowCount(0)
        lay.addWidget(QLabel("Unavailable: no verified telemetry source connected"))
        lay.addWidget(table, 1)
        return w

    def _build_traffic_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        grid = QGridLayout()
        grid.setSpacing(10)

        metrics = [(title, "Unavailable: no verified telemetry source connected") for title in
                   ("Top Pages", "Traffic Sources", "Client Diagnostics", "Core Web Vitals")]

        for idx, (title_m, body_m) in enumerate(metrics):
            card = QFrame()
            card.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 6px; padding: 12px;")
            c_lay = QVBoxLayout(card)
            c_lay.addWidget(QLabel(f"<b>{title_m}</b>"))
            lbl_b = QLabel(body_m)
            lbl_b.setStyleSheet("color: #cbd5e1; font-family: monospace; font-size: 8pt; line-height: 1.4;")
            c_lay.addWidget(lbl_b)
            grid.addWidget(card, idx // 2, idx % 2)

        lay.addLayout(grid)
        lay.addStretch()
        return w

    def _build_sensors_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("📡 Over-The-Air (OTA) RF Sensors & Environmental Node Telemetry:")
        lbl.setStyleSheet("color: #f59e0b; font-weight: bold;")
        lay.addWidget(lbl)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Node ID", "Sensor Type", "Reading", "RSSI", "Battery / Power"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("QTableWidget { background: #05080f; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; }")
        table.setRowCount(0)
        lay.addWidget(QLabel("Unavailable: no verified telemetry source connected"))
        lay.addWidget(table, 1)
        return w

    def _build_api_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("🧪 FastAPI Core (Port 8080) & Local Ollama Swarm (Port 11434) In-Process Latency:")
        lbl.setStyleSheet("color: #38bdf8; font-weight: bold;")
        lay.addWidget(lbl)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Subsystem / Route", "Average Latency", "P99 Latency", "Health State"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("QTableWidget { background: #05080f; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; }")
        table.setRowCount(0)
        lay.addWidget(QLabel("Unavailable: no verified telemetry source connected"))
        lay.addWidget(table, 1)
        return w

    def _seed_wire_traffic(self) -> None:
        # Compatibility callback: absent capture evidence never creates packet records.
        self._render_wire_table()

    def _add_live_packet(self) -> None:
        # Compatibility callback: absent capture evidence never creates packet records.
        self._render_wire_table()

    def _render_wire_table(self) -> None:
        self.wire_table.setRowCount(len(self._traffic_records))
        for i, row in enumerate(self._traffic_records):
            for j, val in enumerate(row):
                item = QTableWidgetItem(val)
                if j == 1:
                    item.setForeground(QColor("#10b981") if val == "GET" else QColor("#38bdf8"))
                elif j == 3:
                    item.setForeground(QColor("#a855f7"))
                elif j == 4:
                    item.setForeground(QColor("#10b981"))
                self.wire_table.setItem(i, j, item)
