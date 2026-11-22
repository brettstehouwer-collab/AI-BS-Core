"""Client Onboarding & Intake Engine View for AI-BS Native Studio.

1:1 visual & functional parity with OnboardingTab.jsx:
- Client Profile & Deployment Configuration Form
- Starter Templates (Apex Media ComfyUI, Notō Hospitality POS, RecDebut Sports)
- Interactive 3-Tier Service Cards (MVP $2,500, Pipeline $7,500, Cluster $15,000)
- Automated Onboarding Stages checklist
- Recent Pipeline Intakes table persisted in local SQLite
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE

_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _ROOT / "saved_data" / "stehouwer_vault.db"


def _ensure_onboarding_db() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS client_intakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            company_name TEXT,
            email TEXT,
            tier TEXT,
            objective TEXT,
            tech_stack TEXT,
            deployment_pref TEXT,
            sla TEXT,
            status TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM client_intakes")
    if cur.fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.executemany(
            """
            INSERT INTO client_intakes 
            (client_name, company_name, email, tier, objective, tech_stack, deployment_pref, sla, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "Sarah Jenkins",
                    "Apex Media Dynamics",
                    "sarah@apexmediadynamics.com",
                    "Autonomous Pipeline ($7,500)",
                    "Automate 4K video rendering and Demucs audio stem separation via RTX 4090 ComfyUI engine.",
                    "Python / PyTorch / ComfyUI / React",
                    "Local Workstation + Cloudflare Tunnel",
                    "< 2min Turnaround on Shorts",
                    "Active Pipeline",
                    now,
                ),
                (
                    "Marcus Bell",
                    "Notō Restaurant Group",
                    "marcus@notobar.com",
                    "Sovereign Cluster ($15,000)",
                    "Deploy multi-bar stock replenishment, real-time barback dispatch, and MLCC distributor automation.",
                    "FastAPI / SQLite / React / Tailwind",
                    "Local LAN Kiosk + Cloud Sync",
                    "Sub-second POS Order Routing",
                    "Active Pipeline",
                    now,
                ),
            ],
        )
        conn.commit()
    return conn


class OnboardingNativeView(QWidget):
    """Client Onboarding & Intake Engine View."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._selected_tier = "Autonomous Pipeline"
        self._build_ui()
        self._load_intakes()

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

        title = QLabel("🚀  Client Onboarding & <span style='color: #38bdf8;'>Intake Engine</span>")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #f8fafc;")
        h_lay.addWidget(title)
        h_lay.addStretch()

        badge = QLabel("TIERED GOVERNANCE & SLA ACTIVE")
        badge.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #059669; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 8pt;")
        h_lay.addWidget(badge)
        layout.addWidget(hdr)

        # 2. Starter Presets Bar
        preset_bar = QHBoxLayout()
        preset_bar.addWidget(QLabel("Apply Starter Presets:"))

        btn_p1 = QPushButton("⚡ Apex Media AI (ComfyUI)")
        btn_p1.setStyleSheet("background: #1e293b; color: #38bdf8; border-radius: 4px; padding: 5px 12px; font-size: 8pt; font-weight: bold;")
        btn_p1.clicked.connect(self._apply_apex_preset)
        preset_bar.addWidget(btn_p1)

        btn_p2 = QPushButton("🍸 Notō Hospitality (Multi-Bar)")
        btn_p2.setStyleSheet("background: #1e293b; color: #a855f7; border-radius: 4px; padding: 5px 12px; font-size: 8pt; font-weight: bold;")
        btn_p2.clicked.connect(self._apply_noto_preset)
        preset_bar.addWidget(btn_p2)

        btn_p3 = QPushButton("🏀 Dennis Bell RecDebut")
        btn_p3.setStyleSheet("background: #1e293b; color: #f59e0b; border-radius: 4px; padding: 5px 12px; font-size: 8pt; font-weight: bold;")
        btn_p3.clicked.connect(self._apply_recdebut_preset)
        preset_bar.addWidget(btn_p3)

        preset_bar.addStretch()
        layout.addLayout(preset_bar)

        # 3. Interactive Service Tier Cards
        tier_grid = QGridLayout()
        tier_grid.setSpacing(10)

        self.tier_cards = {}
        tiers_info = [
            ("starter", "Phase 1 MVP", "Fast MVP Prototype & Architecture Audit", "$2,500", "#38bdf8"),
            ("growth", "Autonomous Pipeline", "Full AI-BS Autonomous Agent Swarm Integration", "$7,500", "#10b981"),
            ("enterprise", "Sovereign Cluster", "Dedicated Local RTX 4090 GPU & Tailscale Node", "$15,000", "#ec4899"),
        ]

        for col, (tid, name, desc, price, color) in enumerate(tiers_info):
            card = QFrame()
            is_active = (name == self._selected_tier)
            border_color = color if is_active else "#1e293b"
            bg = "#121b2a" if is_active else "#0d121d"
            card.setStyleSheet(f"background: {bg}; border: 1.5px solid {border_color}; border-radius: 8px; padding: 12px;")

            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(6, 4, 6, 4)
            c_lay.setSpacing(4)

            top_row = QHBoxLayout()
            lbl_name = QLabel(f"<b>{name}</b>")
            lbl_name.setStyleSheet(f"color: {color}; font-size: 9.5pt;")
            lbl_price = QLabel(f"<b>{price}</b>")
            lbl_price.setStyleSheet("color: #f8fafc; font-size: 11pt; font-weight: bold;")
            top_row.addWidget(lbl_name)
            top_row.addStretch()
            top_row.addWidget(lbl_price)
            c_lay.addLayout(top_row)

            lbl_desc = QLabel(desc)
            lbl_desc.setStyleSheet("color: #94a3b8; font-size: 8pt;")
            lbl_desc.setWordWrap(True)
            c_lay.addWidget(lbl_desc)

            btn_sel = QPushButton("Selected" if is_active else "Select Tier")
            btn_sel.setStyleSheet(
                f"background: {color if is_active else '#1e293b'}; color: {'#000000' if is_active else '#f8fafc'}; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 8pt;"
            )
            btn_sel.clicked.connect(lambda checked, n=name: self._set_tier(n))
            c_lay.addWidget(btn_sel)

            self.tier_cards[name] = (card, btn_sel, color)
            tier_grid.addWidget(card, 0, col)

        layout.addLayout(tier_grid)

        # 4. Form Section
        form_frame = QFrame()
        form_frame.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 14px;")
        f_lay = QVBoxLayout(form_frame)
        f_lay.setContentsMargins(10, 8, 10, 8)
        f_lay.setSpacing(10)

        f_lay.addWidget(QLabel("📝 <b>Client Dossier & Architectural Configuration</b>"))

        f_grid = QGridLayout()
        f_grid.setSpacing(8)

        f_grid.addWidget(QLabel("Client Name:"), 0, 0)
        self.txt_name = QLineEdit("Sarah Jenkins")
        self.txt_name.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        f_grid.addWidget(self.txt_name, 0, 1)

        f_grid.addWidget(QLabel("Company / Entity:"), 0, 2)
        self.txt_company = QLineEdit("Apex Media Dynamics")
        self.txt_company.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        f_grid.addWidget(self.txt_company, 0, 3)

        f_grid.addWidget(QLabel("Contact Email:"), 1, 0)
        self.txt_email = QLineEdit("sarah@apexmediadynamics.com")
        self.txt_email.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        f_grid.addWidget(self.txt_email, 1, 1)

        f_grid.addWidget(QLabel("Target Tech Stack:"), 1, 2)
        self.txt_tech = QLineEdit("Python / PyTorch / ComfyUI / React")
        self.txt_tech.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        f_grid.addWidget(self.txt_tech, 1, 3)

        f_grid.addWidget(QLabel("Deployment Preference:"), 2, 0)
        self.txt_deploy = QLineEdit("Local Workstation + Cloudflare Tunnel")
        self.txt_deploy.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        f_grid.addWidget(self.txt_deploy, 2, 1)

        f_grid.addWidget(QLabel("SLA Requirements:"), 2, 2)
        self.txt_sla = QLineEdit("< 2min Turnaround on Shorts")
        self.txt_sla.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        f_grid.addWidget(self.txt_sla, 2, 3)

        f_lay.addLayout(f_grid)

        f_lay.addWidget(QLabel("Primary Architectural Objective:"))
        self.txt_objective = QTextEdit("Automate 4K video rendering and Demucs audio stem separation via local RTX 4090 ComfyUI engine.")
        self.txt_objective.setFixedHeight(60)
        self.txt_objective.setStyleSheet("background: #070b12; color: #f8fafc; border: 1px solid #334155; padding: 6px 10px; border-radius: 4px;")
        f_lay.addWidget(self.txt_objective)

        # Submit button
        btn_submit_row = QHBoxLayout()
        self.btn_submit = QPushButton("🚀 Ratify Contract & Onboard Client to Sovereign Matrix")
        self.btn_submit.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669); color: #ffffff; border-radius: 6px; padding: 10px 24px; font-weight: bold; font-size: 9.5pt; }"
            "QPushButton:hover { background: #10b981; }"
        )
        self.btn_submit.clicked.connect(self._submit_intake)
        btn_submit_row.addWidget(self.btn_submit)

        self.lbl_submit_status = QLabel("")
        self.lbl_submit_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 8.5pt;")
        btn_submit_row.addWidget(self.lbl_submit_status)
        btn_submit_row.addStretch()

        f_lay.addLayout(btn_submit_row)
        layout.addWidget(form_frame)

        # 5. Recent Pipeline Intakes Table
        table_frame = QFrame()
        table_frame.setStyleSheet("background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 14px;")
        t_lay = QVBoxLayout(table_frame)
        t_lay.setContentsMargins(10, 8, 10, 8)
        t_lay.setSpacing(8)

        t_lay.addWidget(QLabel("📋 <b>Active Pipeline Intakes & Ratified Client Ledgers</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Company", "Client", "Tier", "Status", "Tech Stack", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setFixedHeight(180)
        self.table.setStyleSheet(
            "QTableWidget { background: #05080f; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; }"
            "QHeaderView::section { background: #0f141f; color: #94a3b8; font-weight: bold; border: 1px solid #1e293b; padding: 5px; }"
        )
        t_lay.addWidget(self.table)
        layout.addWidget(table_frame)
        layout.addStretch()

        scroll.setWidget(container)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

    def _set_tier(self, name: str) -> None:
        self._selected_tier = name
        for tname, (card, btn, col) in self.tier_cards.items():
            if tname == name:
                card.setStyleSheet(f"background: #121b2a; border: 1.5px solid {col}; border-radius: 8px; padding: 12px;")
                btn.setText("Selected")
                btn.setStyleSheet(f"background: {col}; color: #000000; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 8pt;")
            else:
                card.setStyleSheet("background: #0d121d; border: 1.5px solid #1e293b; border-radius: 8px; padding: 12px;")
                btn.setText("Select Tier")
                btn.setStyleSheet("background: #1e293b; color: #f8fafc; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 8pt;")

    def _apply_apex_preset(self) -> None:
        self.txt_name.setText("Sarah Jenkins")
        self.txt_company.setText("Apex Media Dynamics")
        self.txt_email.setText("sarah@apexmediadynamics.com")
        self.txt_tech.setText("Python / PyTorch / ComfyUI / React")
        self.txt_deploy.setText("Local Workstation + Cloudflare Tunnel")
        self.txt_sla.setText("< 2min Turnaround on Shorts")
        self.txt_objective.setText("Automate 4K video rendering and Demucs audio stem separation via local RTX 4090 ComfyUI engine.")
        self._set_tier("Autonomous Pipeline")

    def _apply_noto_preset(self) -> None:
        self.txt_name.setText("Marcus Bell")
        self.txt_company.setText("Notō Restaurant Group")
        self.txt_email.setText("marcus@notobar.com")
        self.txt_tech.setText("FastAPI / SQLite / React / Tailwind")
        self.txt_deploy.setText("Local LAN Kiosk + Cloud Sync")
        self.txt_sla.setText("Sub-second POS Order Routing")
        self.txt_objective.setText("Deploy multi-bar stock replenishment, real-time barback dispatch, and MLCC distributor order automation.")
        self._set_tier("Sovereign Cluster")

    def _apply_recdebut_preset(self) -> None:
        self.txt_name.setText("Dennis Bell")
        self.txt_company.setText("RecDebut Sports Program")
        self.txt_email.setText("dennis@recdebut.org")
        self.txt_tech.setText("Python / SQLite / Twilio / React")
        self.txt_deploy.setText("AI-BS Sovereign Desktop + Tailscale")
        self.txt_sla.setText("24/7 Real-Time Recruiter Alerts")
        self.txt_objective.setText("Mass SMS broadcast engine delivering 2,171 student-athlete profiles to NCAA/NAIA college scouts.")
        self._set_tier("Autonomous Pipeline")

    def _submit_intake(self) -> None:
        client = self.txt_name.text().strip()
        company = self.txt_company.text().strip()
        email = self.txt_email.text().strip()
        tech = self.txt_tech.text().strip()
        deploy = self.txt_deploy.text().strip()
        sla = self.txt_sla.text().strip()
        obj = self.txt_objective.toPlainText().strip()

        if not company:
            self.lbl_submit_status.setText("❌ Company name is required.")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = _ensure_onboarding_db()
        conn.execute(
            """
            INSERT INTO client_intakes 
            (client_name, company_name, email, tier, objective, tech_stack, deployment_pref, sla, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (client, company, email, self._selected_tier, obj, tech, deploy, sla, "Active Pipeline", now),
        )
        conn.commit()
        conn.close()

        self.lbl_submit_status.setText(f"✅ Success: {company} onboarded into Sovereign Matrix.")
        self._load_intakes()

    def _load_intakes(self) -> None:
        try:
            conn = _ensure_onboarding_db()
            cur = conn.cursor()
            cur.execute("SELECT company_name, client_name, tier, status, tech_stack, created_at FROM client_intakes ORDER BY id DESC")
            rows = cur.fetchall()
            conn.close()

            self.table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                for j in range(6):
                    item = QTableWidgetItem(str(r[j]))
                    if j == 3:
                        item.setForeground(Qt.GlobalColor.green)
                    self.table.setItem(i, j, item)
        except Exception:
            pass
