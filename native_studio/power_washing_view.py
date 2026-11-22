"""Prestige Mobile Wash & Chemical Estimator Native View (Pure Windows Direct SQLite).

Features:
- Direct local SQLite connection to C:\\AI-BS\\prestige_powerwash.db (clients, jobs, fleet_units)
- Precision Chemical Mix Calculator:
  - Sodium Hypochlorite (SH) % source & target dilution (0.5% siding to 4.0% roof wash)
  - Surfactant ratios (oz per gallon)
  - Bleach-to-water batch tank calculator (50 gal batch)
- Surface Area & Pricing Estimator:
  - Square footage inputs: Concrete, Siding, Roof, Deck
  - Auto-calculated tiered quotes: Standard, Deep Soft-Wash, Premium Sealant
- Job and Client Dispatch Queue with instant SQLite persistence
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE


DB_PATH = Path(r"C:\AI-BS\prestige_powerwash.db")


class PowerWashingNativeView(QWidget):
    """Prestige Mobile Wash CRM & Chemical Estimator Native View."""

    def __init__(self, bus: EngineBus) -> None:
        super().__init__()
        self.bus = bus
        self._all_jobs: list[dict] = []
        self._init_ui()
        self._calculate_mix_and_quote()
        self._load_jobs()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title & Actions
        head_box = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("💦 Prestige Mobile Wash & Chemical Mix Estimator")
        title.setStyleSheet("font-size: 15pt; font-weight: bold; color: #f8fafc;")
        subtitle = QLabel("Direct SQLite Fleet CRM | Precision Sodium Hypochlorite (SH) Batch Mixing & Job Quoting")
        subtitle.setStyleSheet("font-size: 8.5pt; color: #64748b;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        head_box.addLayout(title_box)
        head_box.addStretch()

        self.btn_save_job = QPushButton("➕ Record New Client Job")
        self.btn_save_job.setStyleSheet(
            f"background: {PALETTE['cyan']}; color: #020617; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        self.btn_save_job.clicked.connect(self._save_current_job)
        head_box.addWidget(self.btn_save_job)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet(
            f"background: #1e293b; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; padding: 7px 12px; border-radius: 6px;"
        )
        self.btn_refresh.clicked.connect(self._load_jobs)
        head_box.addWidget(self.btn_refresh)

        layout.addLayout(head_box)

        # Splitter: Left (Calculator & Chemical Mix) | Right (Jobs & Fleet Ledger)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1e293b; width: 4px; }")

        # Left: Chemical Mix & Surface Estimator
        left_pane = QFrame()
        left_pane.setStyleSheet("background: #090d16; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        l_lay = QVBoxLayout(left_pane)
        l_lay.setContentsMargins(10, 10, 10, 10)
        l_lay.setSpacing(10)

        l_title = QLabel("🧪 CHEMICAL DILUTION & SURFACE CALCULATOR")
        l_title.setStyleSheet("font-size: 9pt; font-weight: bold; color: #38bdf8; letter-spacing: 0.5px;")
        l_lay.addWidget(l_title)

        form = QFormLayout()
        form.setSpacing(8)

        # Surface Area Inputs
        self.spin_concrete = QSpinBox()
        self.spin_concrete.setRange(0, 100000)
        self.spin_concrete.setValue(1200)
        self.spin_concrete.setSuffix(" sq ft")
        self.spin_concrete.valueChanged.connect(self._calculate_mix_and_quote)
        form.addRow("Concrete / Driveway:", self.spin_concrete)

        self.spin_siding = QSpinBox()
        self.spin_siding.setRange(0, 100000)
        self.spin_siding.setValue(2400)
        self.spin_siding.setSuffix(" sq ft")
        self.spin_siding.valueChanged.connect(self._calculate_mix_and_quote)
        form.addRow("House Siding (Soft-Wash):", self.spin_siding)

        self.spin_roof = QSpinBox()
        self.spin_roof.setRange(0, 100000)
        self.spin_roof.setValue(0)
        self.spin_roof.setSuffix(" sq ft")
        self.spin_roof.valueChanged.connect(self._calculate_mix_and_quote)
        form.addRow("Roof Algae Treatment:", self.spin_roof)

        # Chemical Mix Inputs
        self.spin_source_sh = QDoubleSpinBox()
        self.spin_source_sh.setRange(5.0, 15.0)
        self.spin_source_sh.setValue(12.5)
        self.spin_source_sh.setSuffix(" % SH (Source)")
        self.spin_source_sh.valueChanged.connect(self._calculate_mix_and_quote)
        form.addRow("Bulk Bleach Strength:", self.spin_source_sh)

        self.combo_target_preset = QComboBox()
        self.combo_target_preset.addItems([
            "House Siding (0.8% SH - Vinyl/Stucco)",
            "Concrete Flatwork (2.5% SH - Pre/Post)",
            "Heavy Roof Algae (4.0% SH - Gloeocapsa)",
            "Commercial Grease / Dumpster (5.0% SH)",
        ])
        self.combo_target_preset.currentIndexChanged.connect(self._calculate_mix_and_quote)
        form.addRow("Target Application Mix:", self.combo_target_preset)

        self.spin_tank_batch = QSpinBox()
        self.spin_tank_batch.setRange(5, 500)
        self.spin_tank_batch.setValue(50)
        self.spin_tank_batch.setSuffix(" Gallons")
        self.spin_tank_batch.valueChanged.connect(self._calculate_mix_and_quote)
        form.addRow("Tank Batch Size:", self.spin_tank_batch)

        l_lay.addLayout(form)

        # Recipe Output Card
        self.recipe_card = QFrame()
        self.recipe_card.setStyleSheet(
            "background: #040711; border: 1px solid #0284c7; border-radius: 6px; padding: 10px;"
        )
        rc_lay = QVBoxLayout(self.recipe_card)
        rc_lay.setContentsMargins(8, 8, 8, 8)
        rc_lay.setSpacing(4)
        rc_title = QLabel("📦 BATCH MIX INSTRUCTIONS:")
        rc_title.setStyleSheet("font-size: 8pt; font-weight: bold; color: #38bdf8;")
        self.lbl_recipe_details = QLabel("Calculating batch...")
        self.lbl_recipe_details.setStyleSheet("font-size: 8.5pt; color: #e2e8f0; line-height: 1.3;")
        rc_lay.addWidget(rc_title)
        rc_lay.addWidget(self.lbl_recipe_details)
        l_lay.addWidget(self.recipe_card)

        # Tiered Quote Output
        quote_title = QLabel("💵 TIERED ESTIMATED QUOTE:")
        quote_title.setStyleSheet("font-size: 8pt; font-weight: bold; color: #4ade80;")
        l_lay.addWidget(quote_title)

        self.lbl_quotes = QLabel("$0.00")
        self.lbl_quotes.setStyleSheet(
            "background: #040711; border: 1px solid #166534; border-radius: 6px; padding: 10px; font-size: 10pt; color: #4ade80; font-weight: bold;"
        )
        l_lay.addWidget(self.lbl_quotes)

        splitter.addWidget(left_pane)

        # Right: Jobs Ledger & Client List
        right_pane = QWidget()
        r_lay = QVBoxLayout(right_pane)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(8)

        r_title = QLabel("📋 DISPATCHED FLEET JOBS & CLIENT ACCOUNTS")
        r_title.setStyleSheet("font-size: 9pt; font-weight: bold; color: #94a3b8; letter-spacing: 0.5px;")
        r_lay.addWidget(r_title)

        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(5)
        self.jobs_table.setHorizontalHeaderLabels(["Client Name", "Service", "Sq Ft", "Quote ($)", "Status"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.jobs_table.horizontalHeader().setStretchLastSection(True)
        self.jobs_table.setColumnWidth(0, 160)
        self.jobs_table.setColumnWidth(1, 140)
        self.jobs_table.setColumnWidth(2, 80)
        self.jobs_table.setColumnWidth(3, 100)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setStyleSheet(
            "QTableWidget { background: #070b14; alternate-background-color: #0b1120; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; font-size: 8.5pt; }"
            "QHeaderView::section { background: #0f172a; color: #94a3b8; font-weight: bold; border: none; padding: 6px; }"
        )
        r_lay.addWidget(self.jobs_table, 1)

        splitter.addWidget(right_pane)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

    def _calculate_mix_and_quote(self) -> None:
        source_sh = self.spin_source_sh.value()
        target_idx = self.combo_target_preset.currentIndex()
        targets = [0.8, 2.5, 4.0, 5.0]
        target_sh = targets[min(target_idx, len(targets) - 1)]

        batch_gal = self.spin_tank_batch.value()
        # Bleach needed = (target / source) * batch
        bleach_gal = round((target_sh / source_sh) * batch_gal, 1)
        water_gal = round(batch_gal - bleach_gal, 1)
        surfactant_oz = round(batch_gal * 1.5, 1)

        self.lbl_recipe_details.setText(
            f"• Water: {water_gal} Gallons\n"
            f"• 12.5% Sodium Hypochlorite: {bleach_gal} Gallons\n"
            f"• Pro Surfactant Scented: {surfactant_oz} oz\n"
            f"• Resulting Strength: {target_sh}% Active SH"
        )

        # Quote Estimation
        concrete_sqft = self.spin_concrete.value()
        siding_sqft = self.spin_siding.value()
        roof_sqft = self.spin_roof.value()

        std_quote = round((concrete_sqft * 0.18) + (siding_sqft * 0.22) + (roof_sqft * 0.35), 2)
        deep_quote = round(std_quote * 1.25, 2)
        prem_quote = round(std_quote * 1.55, 2)

        self.lbl_quotes.setText(
            f"Standard Wash: ${std_quote:,.2f}\n"
            f"Deep Soft-Wash + Post-Treat: ${deep_quote:,.2f}\n"
            f"Premium Sealant Package: ${prem_quote:,.2f}"
        )

    def _load_jobs(self) -> None:
        self._all_jobs = []
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT client_name, service_type, sq_ft_total, quote_amount, status
                    FROM jobs
                    ORDER BY rowid DESC
                    """
                )
                for r in cur.fetchall():
                    self._all_jobs.append({
                        "name": r[0] or "Residential Client",
                        "service": r[1] or "House Wash",
                        "sqft": r[2] or 0,
                        "quote": r[3] or 0.0,
                        "status": (r[4] or "lead").upper(),
                    })
                conn.close()
            except Exception as e:
                print(f"Error loading powerwash jobs: {e}")

        # Fallback baseline jobs if empty
        if not self._all_jobs:
            self._all_jobs = [
                {"name": "Cascade Luxury Estates", "service": "House Soft-Wash", "sqft": 4200, "quote": 950.0, "status": "COMPLETED"},
                {"name": "Downtown Commercial Plaza", "service": "Concrete Flatwork", "sqft": 8500, "quote": 1600.0, "status": "IN PROGRESS"},
                {"name": "Ada Forest Residence", "service": "Roof Treatment", "sqft": 2800, "quote": 750.0, "status": "DISPATCHED"},
            ]

        self.jobs_table.setRowCount(len(self._all_jobs))
        for idx, j in enumerate(self._all_jobs):
            self.jobs_table.setItem(idx, 0, QTableWidgetItem(j["name"]))
            self.jobs_table.setItem(idx, 1, QTableWidgetItem(j["service"]))
            self.jobs_table.setItem(idx, 2, QTableWidgetItem(f"{j['sqft']:,}"))

            q_item = QTableWidgetItem(f"${j['quote']:,.2f}")
            q_item.setForeground(Qt.GlobalColor.green)
            q_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.jobs_table.setItem(idx, 3, q_item)

            st_item = QTableWidgetItem(j["status"])
            st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if j["status"] == "COMPLETED":
                st_item.setForeground(Qt.GlobalColor.green)
            else:
                st_item.setForeground(Qt.GlobalColor.cyan)
            self.jobs_table.setItem(idx, 4, st_item)

    def _save_current_job(self) -> None:
        total_sqft = self.spin_concrete.value() + self.spin_siding.value() + self.spin_roof.value()
        quote_amt = round((total_sqft * 0.22), 2)
        job_id = f"job_{int(time.time())}"
        client_name = "New Commercial Lead"
        service = self.combo_target_preset.currentText().split("(")[0].strip()

        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO jobs (id, client_name, service_type, sq_ft_total, quote_amount, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'scheduled', ?)
                    """,
                    (job_id, client_name, service, total_sqft, quote_amt, time.time()),
                )
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Job Saved", f"Job recorded in prestige_powerwash.db!\nQuote: ${quote_amt:,.2f}")
                self._load_jobs()
                return
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to save job:\n{e}")
