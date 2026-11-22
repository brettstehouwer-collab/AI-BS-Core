"""FE Express Box Truck Automation Hub — Sovereign Native Studio View.

Direct Win32 Direct2D / DirectX GUI with Zero Browser Engines (No WebView2/Chromium)
and Zero Local Web Servers. 
The existing AI-BS service owns dispatch data and operations:
- Live Public Load Board (Trulos Public Live Ingestor + Multi-Threaded QThread)
- 1-Tap Fleet Switcher (All Fleet | 🚚 Box Truck ≤10k lbs | 🚐 Cargo Van ≤4.5k lbs)
- Negotiation Engine & Counter-Bid Generator (Pre-filled for Devin)
- Smart Backhaul Radar (Reloads towards Grand Rapids, MI terminal)
- Devin's Active Dispatches & Native BOL Proof Attacher (Windows QFileDialog)
- Realized Trip Profit & Expense Ledger
- 1099 Subcontract Driver Directory & Year-End Tax Settlements Spreadsheet
- Direct External Calls to Public Load Boards and Route Distance APIs
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.fe_express_service import FEExpressClient
from native_studio.engine import EngineBus
from native_studio.theme import PALETTE
from native_studio.widgets import Card, MetricCard

DEVIN_PROFILE = {
    "name": "Devin",
    "company": "FE Express LLC",
    "email": "Devin.feexpress@gmail.com",
    "phone": "(616) 315-7483",
    "phone_digits": "6163157483",
    "mc": "MC-1482910",
    "usdot": "USDOT-3918241",
    "insurance": "$1,000,000 Auto Liability / $100,000 Cargo"
}


def classify_equipment(equipment_str: str, weight: float = 0.0) -> Dict[str, Any]:
    eq_lower = (equipment_str or "").lower()
    semi_keywords = ["53'", "semi", "tractor", "double drop", "heavy haul", "lowboy"]
    is_semi = any(s in eq_lower for s in semi_keywords) and not any(k in eq_lower for k in ['box', 'van', 'straight'])

    van_keywords = ['cargo van', 'sprinter', 'transit', 'promaster', 'cube van', 'van']
    box_keywords = ["24'", "26'", 'box truck', 'straight truck', 'boxtruck', 'box', 'straight']

    is_van = any(v in eq_lower for v in van_keywords) and not any(b in eq_lower for b in ["53'", 'dry van', 'reefer'])
    is_box = any(b in eq_lower for b in box_keywords) and not is_semi

    if not is_van and not is_box and not is_semi:
        if 'hotshot' in eq_lower or 'partial' in eq_lower:
            if 0 < weight <= 4500:
                is_van = True
            elif 0 < weight <= 10000:
                is_box = True

    vehicle_type = "UNKNOWN"
    if is_box:
        vehicle_type = "BOX_TRUCK"
    elif is_van:
        vehicle_type = "CARGO_VAN"

    return {"is_box": is_box, "is_van": is_van, "vehicle_type": vehicle_type, "is_semi": is_semi}




class FEExpressNativeView(QWidget):
    """Full-fidelity native Win32 direct widget for FE Express inside AI-BS Native Studio."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None, *, service=None) -> None:
        super().__init__(parent)
        self.bus = bus
        self.api = service if service is not None else FEExpressClient()
        self._snapshot = {}
        self._refresh_pending = False
        self._write_pending = False

        self.vehicle_filter = "ALL"
        self.raw_loads_cache = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Ribbon
        header_card = Card(None, self)
        h_lay = QHBoxLayout()
        header_card.setContentLayout(h_lay)

        title_col = QVBoxLayout()
        lbl_title = QLabel("🚚 FE EXPRESS | Box Truck & Van Automation Hub")
        lbl_title.setStyleSheet("font-size: 15pt; font-weight: 800; color: #00f0ff;")
        lbl_sub = QLabel("Native workspace • Connected to the AI-BS dispatch service")
        lbl_sub.setStyleSheet("font-size: 8.5pt; color: #94a3b8;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)
        h_lay.addLayout(title_col)
        h_lay.addStretch()

        self.in_home_base = QLineEdit("Grand Rapids, MI")
        self.in_home_base.setFixedWidth(160)
        self.in_home_base.setStyleSheet("background: rgba(15,23,42,0.8); color: #fff; border: 1px solid #334155; padding: 5px; border-radius: 4px;")
        lbl_hb = QLabel("Home Base:")
        lbl_hb.setStyleSheet("color: #94a3b8; font-size: 8.5pt;")
        h_lay.addWidget(lbl_hb)
        h_lay.addWidget(self.in_home_base)

        self.btn_sync_live = QPushButton("🌐 Pull Live Loads")
        self.btn_sync_live.setStyleSheet("background: #059669; color: #fff; font-weight: 800; border-radius: 6px; padding: 6px 14px;")
        self.btn_sync_live.clicked.connect(self.trigger_live_public_sync)
        h_lay.addWidget(self.btn_sync_live)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setStyleSheet("background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; border-radius: 6px; padding: 6px 12px; font-weight: bold;")
        btn_refresh.clicked.connect(self.refresh_all_data)
        h_lay.addWidget(btn_refresh)

        layout.addWidget(header_card)

        # Devin Dispatch Quick Profile Ribbon
        profile_bar = QFrame()
        profile_bar.setStyleSheet("background-color: #0F172A; border: 1px solid #2563EB; border-radius: 6px; padding: 6px 12px;")
        p_layout = QHBoxLayout(profile_bar)
        
        lbl_p_info = QLabel(
            f"👤 <b>Dispatcher: Devin</b> (FE Express LLC) | "
            f"📞 Direct: <b style='color:#10B981'>{DEVIN_PROFILE['phone']}</b> | "
            f"✉️ Email: <b style='color:#38BDF8'>{DEVIN_PROFILE['email']}</b> | "
            f"Authority: {DEVIN_PROFILE['mc']} | {DEVIN_PROFILE['usdot']}"
        )
        lbl_p_info.setStyleSheet("color: #f8fafc; font-size: 8.5pt;")
        p_layout.addWidget(lbl_p_info)
        p_layout.addStretch()

        btn_call = QPushButton("📞 Call")
        btn_call.setStyleSheet("background-color: #059669; color: white; padding: 4px 10px; font-weight: bold; border-radius: 4px;")
        btn_call.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"tel:{DEVIN_PROFILE['phone_digits']}")))
        p_layout.addWidget(btn_call)

        btn_sms = QPushButton("💬 SMS")
        btn_sms.setStyleSheet("background-color: #0284C7; color: white; padding: 4px 10px; font-weight: bold; border-radius: 4px;")
        btn_sms.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"sms:{DEVIN_PROFILE['phone_digits']}")))
        p_layout.addWidget(btn_sms)

        btn_email = QPushButton("✉️ Email")
        btn_email.setStyleSheet("background-color: #4F46E5; color: white; padding: 4px 10px; font-weight: bold; border-radius: 4px;")
        btn_email.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"mailto:{DEVIN_PROFILE['email']}")))
        p_layout.addWidget(btn_email)

        layout.addWidget(profile_bar)

        # Telemetry Banner
        self.status_banner = QLabel("🟢 REAL PUBLIC BOARD FEED (Trulos Live) | Initializing...")
        self.status_banner.setStyleSheet(
            "background-color: #064E3B; color: #A7F3D0; border: 1px solid #10B981; "
            "border-radius: 6px; padding: 6px 10px; font-weight: bold; font-size: 9pt;"
        )
        layout.addWidget(self.status_banner)

        # 4 Navigation Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1F2937; background-color: #0B0F19; border-radius: 8px; }
            QTabBar::tab { background-color: #1E293B; color: #94A3B8; padding: 8px 16px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; font-size: 8.5pt; }
            QTabBar::tab:selected { background-color: #2563EB; color: #FFFFFF; }
            QTableWidget { background-color: #111827; gridline-color: #1F2937; border: none; color: #F8FAFC; }
            QHeaderView::section { background-color: #1F2937; color: #9CA3AF; padding: 5px; border: none; font-weight: bold; font-size: 8.5pt; }
        """)
        layout.addWidget(self.tabs)

        # Tab 1: Live Board
        self.tab_board = QWidget()
        self.setup_tab_board()
        self.tabs.addTab(self.tab_board, "📋 Live Load Board")

        # Tab 2: Devin's Active Hauls
        self.tab_active = QWidget()
        self.setup_tab_active()
        self.tabs.addTab(self.tab_active, "🚚 Devin's Active Hauls")

        # Tab 3: Trip Profit & BOL Ledger
        self.tab_ledger = QWidget()
        self.setup_tab_ledger()
        self.tabs.addTab(self.tab_ledger, "💰 Trip Profit & BOL Ledger")

        # Tab 4: 1099 Drivers & Tax Spreadsheet
        self.tab_drivers = QWidget()
        self.setup_tab_drivers()
        self.tabs.addTab(self.tab_drivers, "👥 1099 Drivers & Tax Spreadsheet")

        # Tab 5: Owner-Operator Yield & Uptime Cockpit
        self.tab_owner_operator = QWidget()
        self.setup_tab_owner_operator()
        self.tabs.addTab(self.tab_owner_operator, "🚀 Owner-Operator Cockpit")

        # High-Speed Local Screen & Database Refresh (2 seconds)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.update_live_telemetry)
        self.telemetry_timer.start(2000)

        # Periodic read-only service refresh (never live-board scraping)
        self.auto_sync_timer = QTimer(self)
        self.auto_sync_timer.timeout.connect(self.trigger_background_auto_sync)
        self.auto_sync_timer.start(30000)  # 30 seconds

        self.refresh_all_data()

    def trigger_background_auto_sync(self):
        """Refresh stored state only; automatic scraping is not a client lifecycle action."""
        self.refresh_all_data()

    # ── Tab 1: Live Board ──
    def setup_tab_board(self):
        lay = QVBoxLayout(self.tab_board)
        lay.setContentsMargins(8, 8, 8, 8)

        # Filter Strip
        f_box = QFrame()
        f_box.setStyleSheet("background-color: #111827; border: 1px solid #1F2937; border-radius: 6px; padding: 6px;")
        f_lay = QHBoxLayout(f_box)

        lbl_fleet = QLabel("Fleet Match:")
        lbl_fleet.setStyleSheet("font-weight: bold; color: #38BDF8; font-size: 8.5pt;")
        f_lay.addWidget(lbl_fleet)

        self.btn_fleet_all = QPushButton("All Fleet")
        self.btn_fleet_all.setStyleSheet("background-color: #2563EB; color: white; border-radius: 4px; padding: 4px 8px; font-size: 8pt; font-weight: bold;")
        self.btn_fleet_all.clicked.connect(lambda: self.set_vehicle_filter("ALL"))
        f_lay.addWidget(self.btn_fleet_all)

        self.btn_fleet_box = QPushButton("🚚 Box Truck (≤10k lbs)")
        self.btn_fleet_box.setStyleSheet("background-color: #1E293B; color: #94A3B8; border-radius: 4px; padding: 4px 8px; font-size: 8pt; font-weight: bold;")
        self.btn_fleet_box.clicked.connect(lambda: self.set_vehicle_filter("BOX_TRUCK"))
        f_lay.addWidget(self.btn_fleet_box)

        self.btn_fleet_van = QPushButton("🚐 Cargo Van (≤4.5k lbs)")
        self.btn_fleet_van.setStyleSheet("background-color: #1E293B; color: #94A3B8; border-radius: 4px; padding: 4px 8px; font-size: 8pt; font-weight: bold;")
        self.btn_fleet_van.clicked.connect(lambda: self.set_vehicle_filter("CARGO_VAN"))
        f_lay.addWidget(self.btn_fleet_van)

        f_lay.addSpacing(12)

        self.in_search_orig = QLineEdit()
        self.in_search_orig.setPlaceholderText("Origin City / State...")
        self.in_search_orig.textChanged.connect(self.apply_board_filters)
        self.in_search_orig.setStyleSheet("background-color: #1F2937; border: 1px solid #374151; color: #F8FAFC; padding: 4px 6px; border-radius: 4px;")
        f_lay.addWidget(self.in_search_orig)

        self.in_search_dest = QLineEdit()
        self.in_search_dest.setPlaceholderText("Dest City / State...")
        self.in_search_dest.textChanged.connect(self.apply_board_filters)
        self.in_search_dest.setStyleSheet("background-color: #1F2937; border: 1px solid #374151; color: #F8FAFC; padding: 4px 6px; border-radius: 4px;")
        f_lay.addWidget(self.in_search_dest)

        self.in_min_rpm = QLineEdit()
        self.in_min_rpm.setPlaceholderText("Min $/mi...")
        self.in_min_rpm.setFixedWidth(75)
        self.in_min_rpm.textChanged.connect(self.apply_board_filters)
        self.in_min_rpm.setStyleSheet("background-color: #1F2937; border: 1px solid #374151; color: #F8FAFC; padding: 4px 6px; border-radius: 4px;")
        f_lay.addWidget(self.in_min_rpm)

        self.in_min_pay = QLineEdit()
        self.in_min_pay.setPlaceholderText("Min Pay $...")
        self.in_min_pay.setFixedWidth(75)
        self.in_min_pay.textChanged.connect(self.apply_board_filters)
        self.in_min_pay.setStyleSheet("background-color: #1F2937; border: 1px solid #374151; color: #F8FAFC; padding: 4px 6px; border-radius: 4px;")
        f_lay.addWidget(self.in_min_pay)

        lay.addWidget(f_box)

        # Table
        self.table_board = QTableWidget(0, 10)
        self.table_board.setHorizontalHeaderLabels([
            "Score", "Origin ➡️ Destination", "Equipment & Vehicle Match",
            "Weight", "Pay ($)", "Loaded Mi / RPM", "True RPM (w/ DH)",
            "Broker", "Credit Score", "1-Click Actions"
        ])
        self.table_board.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_board.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_board.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table_board)

    def set_vehicle_filter(self, mode: str):
        self.vehicle_filter = mode
        self.btn_fleet_all.setStyleSheet("background-color: #2563EB; color: white;" if mode == "ALL" else "background-color: #1E293B; color: #94A3B8;")
        self.btn_fleet_box.setStyleSheet("background-color: #2563EB; color: white;" if mode == "BOX_TRUCK" else "background-color: #1E293B; color: #94A3B8;")
        self.btn_fleet_van.setStyleSheet("background-color: #2563EB; color: white;" if mode == "CARGO_VAN" else "background-color: #1E293B; color: #94A3B8;")
        self.apply_board_filters()

    def apply_board_filters(self):
        orig_q = self.in_search_orig.text().strip().lower()
        dest_q = self.in_search_dest.text().strip().lower()
        try:
            min_rpm = float(self.in_min_rpm.text().strip()) if self.in_min_rpm.text().strip() else None
        except ValueError:
            min_rpm = None
        try:
            min_pay = float(self.in_min_pay.text().strip()) if self.in_min_pay.text().strip() else None
        except ValueError:
            min_pay = None

        self.table_board.setRowCount(0)
        for r in self.raw_loads_cache:
            origin = (r.get("origin_city_state") or "").lower()
            dest = (r.get("dest_city_state") or "").lower()
            pay = float(r.get("flat_rate_pay") or 0.0)
            rpm = float(r.get("true_rpm") or r.get("rpm") or 0.0)
            weight = float(r.get("weight_lbs") or 0.0)
            equip = r.get("equipment_type") or ""

            if orig_q and orig_q not in origin:
                continue
            if dest_q and dest_q not in dest:
                continue
            if min_rpm is not None and rpm < min_rpm:
                continue
            if min_pay is not None and pay < min_pay:
                continue

            v_info = classify_equipment(equip, weight)
            if self.vehicle_filter == "BOX_TRUCK" and not v_info["is_box"]:
                continue
            if self.vehicle_filter == "CARGO_VAN" and not v_info["is_van"]:
                continue

            row_idx = self.table_board.rowCount()
            self.table_board.insertRow(row_idx)

            score_item = QTableWidgetItem(r.get("score", "Reject"))
            if r.get("score") == "Greenlight":
                score_item.setBackground(QColor("#065F46"))
            elif r.get("score") == "Caution":
                score_item.setBackground(QColor("#92400E"))
            else:
                score_item.setBackground(QColor("#991B1B"))
            self.table_board.setItem(row_idx, 0, score_item)

            self.table_board.setItem(row_idx, 1, QTableWidgetItem(f"{r.get('origin_city_state')} ➡️ {r.get('dest_city_state')}"))
            
            v_badge = "🚚 Box Truck" if v_info["is_box"] else ("🚐 Cargo Van" if v_info["is_van"] else "⚠️ General")
            self.table_board.setItem(row_idx, 2, QTableWidgetItem(f"{v_badge} | {equip}"))
            self.table_board.setItem(row_idx, 3, QTableWidgetItem(f"{weight:,.0f} lbs"))
            self.table_board.setItem(row_idx, 4, QTableWidgetItem(f"${pay:,.0f}"))
            self.table_board.setItem(row_idx, 5, QTableWidgetItem(f"{r.get('total_miles', 0):,.0f} mi (${r.get('rpm', 0):.2f})"))
            self.table_board.setItem(row_idx, 6, QTableWidgetItem(f"${r.get('true_rpm', 0):.2f} (+{r.get('deadhead_miles', 0):,.0f} DH)"))
            self.table_board.setItem(row_idx, 7, QTableWidgetItem(str(r.get("broker_name", ""))))

            cr = self._snapshot.get('brokerCredits', {}).get(r.get("broker_name", ""), {})
            f_status = cr.get("factoring_status") or cr.get("factoring", "Unavailable")
            self.table_board.setItem(row_idx, 8, QTableWidgetItem(f"{cr.get('score', '—')} ({f_status})"))

            # Actions
            actions_widget = QWidget()
            a_layout = QHBoxLayout(actions_widget)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            btn_bid = QPushButton("💼 Bid")
            btn_bid.setStyleSheet("background-color: #2563EB; font-size: 8pt; padding: 3px 6px; border-radius: 3px; font-weight: bold; color: white;")
            btn_bid.clicked.connect(lambda _, load=r: self.open_bid_dialog(load))
            a_layout.addWidget(btn_bid)

            btn_radar = QPushButton("🔄 Backhaul")
            btn_radar.setStyleSheet("background-color: #059669; font-size: 8pt; padding: 3px 6px; border-radius: 3px; font-weight: bold; color: white;")
            btn_radar.clicked.connect(lambda _, load=r: self.open_backhaul_dialog(load))
            a_layout.addWidget(btn_radar)

            btn_book = QPushButton("⚡ Book")
            btn_book.setStyleSheet("background-color: #7C3AED; font-size: 8pt; padding: 3px 6px; border-radius: 3px; font-weight: bold; color: white;")
            btn_book.clicked.connect(lambda _, load=r: self.confirm_manual_book_load(load))
            a_layout.addWidget(btn_book)

            self.table_board.setCellWidget(row_idx, 9, actions_widget)

    def open_bid_dialog(self, load: Dict[str, Any]):
        origin = load.get("origin_city_state", "")
        dest = load.get("dest_city_state", "")
        posted_pay = float(load.get("flat_rate_pay", 0.0))
        target_bid = round(posted_pay * 1.10, 2) if posted_pay > 0 else 850.0

        dlg = QDialog(self)
        dlg.setWindowTitle(f"💼 Rate Bid: {load.get('load_id')}")
        dlg.resize(650, 480)
        dlg.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
        d_lay = QVBoxLayout(dlg)

        lbl = QLabel(f"<b>Negotiation Bid:</b> {origin} ➡️ {dest} (${posted_pay:,.0f} posted pay)")
        lbl.setStyleSheet("color: #38BDF8; font-size: 11pt;")
        d_lay.addWidget(lbl)

        txt = QTextEdit()
        txt.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border: 1px solid #334155; font-family: 'Consolas'; font-size: 9pt;")
        email_text = (
            f"Hello {load.get('broker_name')} Team,\n\n"
            f"We have an empty 26' Box Truck w/ Liftgate & Pallet Jack ready near {origin} "
            f"and can take load {load.get('load_id')} immediately.\n\n"
            f"• Origin: {origin}\n• Destination: {dest}\n• Miles: {load.get('total_miles', 0)} loaded\n"
            f"• All-In Bid: ${target_bid:,.2f} (Clean rate)\n\n"
            f"Authority: MC-1482910 | USDOT-3918241\n"
            f"Direct Contact: Devin @ (616) 315-7483 | Devin.feexpress@gmail.com\n"
        )
        txt.setPlainText(email_text)
        d_lay.addWidget(txt)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Email")
        btn_copy.setStyleSheet("background-color: #2563EB; color: white; padding: 6px 12px; font-weight: bold;")
        btn_copy.clicked.connect(lambda: (QApplication.clipboard().setText(txt.toPlainText()), QMessageBox.information(dlg, "Copied", "Bid copied!")))
        btn_row.addWidget(btn_copy)

        btn_mail = QPushButton("✉️ Launch Mail")
        btn_mail.setStyleSheet("background-color: #059669; color: white; padding: 6px 12px; font-weight: bold;")
        btn_mail.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"mailto:?subject=Rate%20Bid%20{load.get('load_id')}&body={QUrl.toPercentEncoding(txt.toPlainText()).data().decode()}")))
        btn_row.addWidget(btn_mail)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background-color: #475569; color: white; padding: 6px 12px;")
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        d_lay.addLayout(btn_row)

        dlg.exec()

    def open_backhaul_dialog(self, load: Dict[str, Any]):
        home = self.in_home_base.text().strip() or "Grand Rapids, MI"
        dlg = QDialog(self)
        dlg.setWindowTitle("Smart Backhaul Radar")
        dlg.resize(750, 400)
        layout = QVBoxLayout(dlg)
        status = QLabel("Finding stored return freight...")
        status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(status)
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Load ID", "Lane", "Equipment", "Weight", "Pay ($)"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table)
        alive = [True]
        def populate(candidates):
            if not alive[0]:
                return
            status.setText(f"Return freight matches: {len(candidates)}")
            for item in candidates:
                row = table.rowCount()
                table.insertRow(row)
                values = [item.get('load_id', ''), f"{item.get('origin_city_state', '')} → {item.get('dest_city_state', '')}",
                          item.get('equipment_type', ''), f"{item.get('weight_lbs', 0):,.0f} lbs", f"${item.get('flat_rate_pay', 0):,.0f}"]
                for column, value in enumerate(values):
                    table.setItem(row, column, QTableWidgetItem(str(value)))
        def failed(message):
            if alive[0]:
                status.setText("Return freight unavailable — " + str(message))
        self.bus.submit(self.api.find_backhauls, load.get('load_id'), home, on_result=populate, on_error=failed)
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        layout.addWidget(close)
        dlg.exec()
        alive[0] = False

    def confirm_manual_book_load(self, load: Dict[str, Any]):
        ans = QMessageBox.question(
            self, "Confirm Manual Booking",
            f"Book load {load.get('load_id')} ({load.get('origin_city_state')} → {load.get('dest_city_state')}) "
            f"for ${load.get('flat_rate_pay', 0):,.0f} into Active Hauls?\n\nManual operator approval is required.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        def saved(result):
            QMessageBox.information(self, "Booked", "The dispatch service confirmed this load booking.")
            self.refresh_all_data()
            self.tabs.setCurrentIndex(1)
        self._run_action(lambda: self.api.book_load(dict(load)), on_success=saved)

    # ── Tab 2: Devin's Active Hauls ──
    def setup_tab_active(self):
        lay = QVBoxLayout(self.tab_active)
        lay.setContentsMargins(8, 8, 8, 8)

        lbl = QLabel("🚚 Devin's Active Hauls & Live Dispatch Stepper")
        lbl.setStyleSheet("font-size: 11pt; font-weight: bold; color: #10B981;")
        lay.addWidget(lbl)

        self.table_active = QTableWidget(0, 9)
        self.table_active.setHorizontalHeaderLabels([
            "Dispatch ID", "Lane", "Status", "Gross Revenue",
            "Est Fuel", "Est Tolls", "Net Profit", "BOL / Proof", "Actions"
        ])
        self.table_active.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_active.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_active)

    def load_active_dispatches_ui(self):
        dispatches = self._snapshot.get('dispatches', [])
        self.table_active.setRowCount(0)
        for d in dispatches:
            if d.get("status") == "DELIVERED":
                continue
            idx = self.table_active.rowCount()
            self.table_active.insertRow(idx)

            self.table_active.setItem(idx, 0, QTableWidgetItem(d.get("dispatch_id")))
            self.table_active.setItem(idx, 1, QTableWidgetItem(f"{d.get('origin')} ➡️ {d.get('destination')}"))
            
            st_item = QTableWidgetItem(d.get("status", "ASSIGNED"))
            st_item.setForeground(QColor("#38BDF8"))
            self.table_active.setItem(idx, 2, st_item)

            self.table_active.setItem(idx, 3, QTableWidgetItem(f"${d.get('gross_pay', 0):,.2f}"))
            self.table_active.setItem(idx, 4, QTableWidgetItem(f"${d.get('fuel_cost', 0):,.2f}"))
            self.table_active.setItem(idx, 5, QTableWidgetItem(f"${d.get('tolls_cost', 0):,.2f}"))
            
            net_item = QTableWidgetItem(f"${d.get('net_profit', 0):,.2f}")
            net_item.setForeground(QColor("#10B981"))
            self.table_active.setItem(idx, 6, net_item)

            bol_url = d.get("bol_photo_url")
            self.table_active.setItem(idx, 7, QTableWidgetItem("✅ Attached" if bol_url else "⚠️ Pending"))

            btn_bol = QPushButton("📸 Upload BOL")
            btn_bol.setStyleSheet("background-color: #059669; font-size: 8pt; padding: 3px 6px; border-radius: 3px; font-weight: bold; color: white;")
            btn_bol.clicked.connect(lambda _, disp=d: self.open_bol_dialog(disp))
            self.table_active.setCellWidget(idx, 8, btn_bol)

    def open_bol_dialog(self, dispatch: Dict[str, Any]):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"📸 Attach BOL: {dispatch.get('dispatch_id')}")
        dlg.resize(480, 360)
        dlg.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
        d_lay = QVBoxLayout(dlg)
        form = QFormLayout()

        combo_status = QComboBox()
        combo_status.addItems(["DELIVERED", "EN_ROUTE_DELIVERY", "EN_ROUTE_PICKUP"])
        combo_status.setStyleSheet("background-color: #1E293B; color: white; padding: 4px;")

        spin_fuel = QDoubleSpinBox()
        spin_fuel.setRange(0.0, 5000.0)
        spin_fuel.setValue(float(dispatch.get("fuel_cost", 40.0)))
        spin_fuel.setStyleSheet("background-color: #1E293B; color: white;")

        spin_tolls = QDoubleSpinBox()
        spin_tolls.setRange(0.0, 1000.0)
        spin_tolls.setValue(float(dispatch.get("tolls_cost", 20.0)))
        spin_tolls.setStyleSheet("background-color: #1E293B; color: white;")

        lbl_file = QLabel("No file selected")
        lbl_file.setStyleSheet("color: #94A3B8; font-size: 8pt;")

        selected_path = [dispatch.get("bol_photo_url") or ""]

        def choose_f():
            path, _ = QFileDialog.getOpenFileName(dlg, "Select BOL File", "", "Files (*.png *.jpg *.jpeg *.pdf)")
            if path:
                selected_path[0] = path
                lbl_file.setText(Path(path).name)

        btn_choose = QPushButton("📁 Choose File")
        btn_choose.setStyleSheet("background-color: #2563EB; color: white; padding: 4px 8px; font-weight: bold;")
        btn_choose.clicked.connect(choose_f)

        f_row = QHBoxLayout()
        f_row.addWidget(btn_choose)
        f_row.addWidget(lbl_file)

        form.addRow("Haul Status:", combo_status)
        form.addRow("Actual Fuel ($):", spin_fuel)
        form.addRow("Actual Tolls ($):", spin_tolls)
        form.addRow("BOL Document:", f_row)
        d_lay.addLayout(form)

        btn_save = QPushButton("💾 Save & Lock Delivery")
        btn_save.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 8px;")
        def save():
            payload = {"status": combo_status.currentText(), "fuel_cost": spin_fuel.value(),
                       "tolls_cost": spin_tolls.value(), "bol_photo_url": selected_path[0]}
            def saved(result):
                QMessageBox.information(dlg, "Saved", "The dispatch service confirmed the haul update.")
                dlg.accept()
                self.refresh_all_data()
            self._run_action(lambda: self.api.update_load_accounting(dispatch.get('dispatch_id'), payload), on_success=saved)
        btn_save.clicked.connect(save)
        d_lay.addWidget(btn_save)

        dlg.exec()

    # ── Tab 3: Trip Profit Ledger ──
    def setup_tab_ledger(self):
        lay = QVBoxLayout(self.tab_ledger)
        lay.setContentsMargins(8, 8, 8, 8)

        self.lbl_ledger_summary = QLabel("💰 Total Realized Net Profit: $0.00")
        self.lbl_ledger_summary.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #10B981; background-color: #064E3B; "
            "border: 1px solid #10B981; border-radius: 6px; padding: 8px 12px;"
        )
        lay.addWidget(self.lbl_ledger_summary)

        self.table_ledger = QTableWidget(0, 8)
        self.table_ledger.setHorizontalHeaderLabels([
            "Dispatch ID", "Date", "Lane", "Gross Pay", "Fuel", "Tolls", "Net Take-Home", "Proof"
        ])
        self.table_ledger.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_ledger.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_ledger)

    def load_ledger_ui(self):
        dispatches = self._snapshot.get('dispatches', [])
        self.table_ledger.setRowCount(0)
        total_net = 0.0

        for d in dispatches:
            idx = self.table_ledger.rowCount()
            self.table_ledger.insertRow(idx)

            net = float(d.get("net_profit", 0.0))
            total_net += net

            self.table_ledger.setItem(idx, 0, QTableWidgetItem(d.get("dispatch_id")))
            self.table_ledger.setItem(idx, 1, QTableWidgetItem(str(d.get("dispatched_at", ""))[:10]))
            self.table_ledger.setItem(idx, 2, QTableWidgetItem(f"{d.get('origin')} ➡️ {d.get('destination')}"))
            self.table_ledger.setItem(idx, 3, QTableWidgetItem(f"${d.get('gross_pay', 0):,.2f}"))
            self.table_ledger.setItem(idx, 4, QTableWidgetItem(f"${d.get('fuel_cost', 0):,.2f}"))
            self.table_ledger.setItem(idx, 5, QTableWidgetItem(f"${d.get('tolls_cost', 0):,.2f}"))

            net_item = QTableWidgetItem(f"${net:,.2f}")
            net_item.setForeground(QColor("#10B981"))
            self.table_ledger.setItem(idx, 6, net_item)

            bol = d.get("bol_photo_url")
            if bol and os.path.exists(bol):
                btn_view = QPushButton("📄 View")
                btn_view.setStyleSheet("background-color: #2563EB; font-size: 8pt; padding: 2px 6px; border-radius: 3px; font-weight: bold; color: white;")
                btn_view.clicked.connect(lambda _, b=bol: QDesktopServices.openUrl(QUrl.fromLocalFile(b)))
                self.table_ledger.setCellWidget(idx, 7, btn_view)
            else:
                self.table_ledger.setItem(idx, 7, QTableWidgetItem("None"))

        self.lbl_ledger_summary.setText(f"💰 Total Realized Net Profit (All Dispatches): ${total_net:,.2f}")

    # ── Tab 4: 1099 Drivers & Tax Spreadsheet ──
    def setup_tab_drivers(self):
        lay = QVBoxLayout(self.tab_drivers)
        lay.setContentsMargins(8, 8, 8, 8)

        h_bar = QHBoxLayout()
        lbl_t = QLabel("👥 1099 Subcontract Driver Roster & Trip Settlements")
        lbl_t.setStyleSheet("font-size: 11pt; font-weight: bold; color: #F59E0B;")
        h_bar.addWidget(lbl_t)
        h_bar.addStretch()

        btn_add_drv = QPushButton("➕ Add 1099 Driver")
        btn_add_drv.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 5px 12px; border-radius: 4px;")
        btn_add_drv.clicked.connect(self.open_add_driver_dialog)
        h_bar.addWidget(btn_add_drv)

        btn_add_settle = QPushButton("💵 Record Trip Settlement")
        btn_add_settle.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 5px 12px; border-radius: 4px;")
        btn_add_settle.clicked.connect(self.open_add_settlement_dialog)
        h_bar.addWidget(btn_add_settle)

        lay.addLayout(h_bar)

        self.table_drivers = QTableWidget(0, 7)
        self.table_drivers.setHorizontalHeaderLabels([
            "Driver ID", "Full Name", "Contact", "Tax ID (Last 4)", "Agreed Rate", "Med Card Exp", "W-9 Status"
        ])
        self.table_drivers.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_drivers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_drivers)

        lbl_s = QLabel("1099 Payouts & Tax Settlements Ledger:")
        lbl_s.setStyleSheet("color: #94A3B8; font-weight: bold; margin-top: 6px;")
        lay.addWidget(lbl_s)

        self.table_settlements = QTableWidget(0, 8)
        self.table_settlements.setHorizontalHeaderLabels([
            "Settlement ID", "Date", "Driver", "Lane", "Gross Load", "Earned", "Deductions", "Net 1099 Payout"
        ])
        self.table_settlements.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_settlements.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_settlements)

    def load_drivers_ui(self):
        drivers = self._snapshot.get('drivers', [])
        settlements = self._snapshot.get('settlements', [])

        self.table_drivers.setRowCount(0)
        for d in drivers:
            idx = self.table_drivers.rowCount()
            self.table_drivers.insertRow(idx)

            self.table_drivers.setItem(idx, 0, QTableWidgetItem(d.get("driver_id")))
            self.table_drivers.setItem(idx, 1, QTableWidgetItem(d.get("full_name")))
            self.table_drivers.setItem(idx, 2, QTableWidgetItem(f"{d.get('phone', '')} | {d.get('email', '')}"))
            self.table_drivers.setItem(idx, 3, QTableWidgetItem(f"***-**-{d.get('tax_id_or_ssn_last4', 'XXXX')}"))
            
            rate_text = f"{d.get('pay_rate', 25)}% Gross" if d.get('pay_model') == 'PERCENT_GROSS' else f"${d.get('pay_rate', 0.55)}/mi"
            self.table_drivers.setItem(idx, 4, QTableWidgetItem(rate_text))
            self.table_drivers.setItem(idx, 5, QTableWidgetItem(str(d.get("medical_card_exp", ""))))
            self.table_drivers.setItem(idx, 6, QTableWidgetItem("✅ On File" if d.get("w9_on_file") == 1 else "⚠️ Pending"))

        self.table_settlements.setRowCount(0)
        driver_map = {d["driver_id"]: d["full_name"] for d in drivers}
        for s in settlements:
            idx = self.table_settlements.rowCount()
            self.table_settlements.insertRow(idx)

            self.table_settlements.setItem(idx, 0, QTableWidgetItem(s.get("settlement_id")))
            self.table_settlements.setItem(idx, 1, QTableWidgetItem(str(s.get("trip_date", ""))))
            self.table_settlements.setItem(idx, 2, QTableWidgetItem(driver_map.get(s.get("driver_id"), s.get("driver_id"))))
            self.table_settlements.setItem(idx, 3, QTableWidgetItem(s.get("origin_dest", "")))
            self.table_settlements.setItem(idx, 4, QTableWidgetItem(f"${s.get('gross_load_pay', 0):,.2f}"))
            self.table_settlements.setItem(idx, 5, QTableWidgetItem(f"${s.get('contractor_pay', 0):,.2f}"))
            
            deduct = float(s.get("fuel_deduction", 0.0)) + float(s.get("cash_advance", 0.0))
            self.table_settlements.setItem(idx, 6, QTableWidgetItem(f"-${deduct:,.2f}"))

            payout_item = QTableWidgetItem(f"${s.get('net_1099_payout', 0):,.2f}")
            payout_item.setForeground(QColor("#10B981"))
            self.table_settlements.setItem(idx, 7, payout_item)

    def open_add_driver_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("➕ Add 1099 Subcontract Driver")
        dlg.resize(450, 400)
        dlg.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
        d_lay = QVBoxLayout(dlg)
        form = QFormLayout()

        in_name = QLineEdit()
        in_phone = QLineEdit()
        in_email = QLineEdit()
        in_ssn = QLineEdit()
        in_rate = QDoubleSpinBox()
        in_rate.setRange(0.0, 1000.0)
        in_rate.setValue(25.0)

        combo_model = QComboBox()
        combo_model.addItems(["PERCENT_GROSS", "PER_MILE", "FLAT_PER_DAY"])

        form.addRow("Driver Full Name*:", in_name)
        form.addRow("Phone Number:", in_phone)
        form.addRow("Email Address:", in_email)
        form.addRow("SSN/EIN Last 4:", in_ssn)
        form.addRow("Pay Model:", combo_model)
        form.addRow("Pay Rate:", in_rate)
        d_lay.addLayout(form)

        btn_save = QPushButton("💾 Save Driver")
        btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px;")
        def save():
            if not in_name.text().strip():
                QMessageBox.warning(dlg, "Error", "Name required")
                return
            payload = {"full_name": in_name.text().strip(), "phone": in_phone.text().strip(),
                       "email": in_email.text().strip(), "tax_id_or_ssn_last4": in_ssn.text().strip() or "XXXX",
                       "pay_model": combo_model.currentText(), "pay_rate": in_rate.value()}
            def saved(result):
                dlg.accept()
                self.refresh_all_data()
            self._run_action(lambda: self.api.save_contractor_driver(payload), on_success=saved)
        btn_save.clicked.connect(save)
        d_lay.addWidget(btn_save)

        dlg.exec()

    def open_add_settlement_dialog(self):
        drivers = self._snapshot.get('drivers', [])
        if not drivers:
            QMessageBox.warning(self, "No Drivers", "Please add a driver first.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("💵 Record Trip Settlement")
        dlg.resize(450, 420)
        dlg.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
        d_lay = QVBoxLayout(dlg)
        form = QFormLayout()

        combo_drv = QComboBox()
        for d in drivers:
            combo_drv.addItem(d["full_name"], d)

        in_lane = QLineEdit()
        in_lane.setPlaceholderText("Grand Rapids, MI -> Chicago, IL")

        spin_gross = QDoubleSpinBox()
        spin_gross.setRange(0.0, 20000.0)
        spin_gross.setValue(600.0)

        spin_miles = QDoubleSpinBox()
        spin_miles.setRange(0.0, 5000.0)
        spin_miles.setValue(180.0)

        spin_deduct = QDoubleSpinBox()
        spin_deduct.setRange(0.0, 5000.0)
        spin_deduct.setValue(0.0)

        form.addRow("Driver:", combo_drv)
        form.addRow("Haul Lane:", in_lane)
        form.addRow("Gross Pay ($):", spin_gross)
        form.addRow("Miles:", spin_miles)
        form.addRow("Fuel/Advance Deduct ($):", spin_deduct)
        d_lay.addLayout(form)

        btn_save = QPushButton("✅ Record Payout")
        btn_save.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px;")
        def save():
            d_data = combo_drv.currentData()
            gross = spin_gross.value()
            rate = float(d_data.get('pay_rate', 25.0))
            earned = gross * (rate / 100.0) if d_data.get('pay_model') == 'PERCENT_GROSS' else spin_miles.value() * rate
            payload = {"driver_id": d_data['driver_id'], "origin_dest": in_lane.text().strip() or "Custom Haul",
                       "total_miles": spin_miles.value(), "gross_load_pay": gross, "contractor_pay": earned,
                       "fuel_deduction": spin_deduct.value(), "net_1099_payout": round(earned - spin_deduct.value(), 2),
                       "payment_status": "PAID"}
            def saved(result):
                dlg.accept()
                self.refresh_all_data()
            self._run_action(lambda: self.api.record_settlement(payload), on_success=saved)
        btn_save.clicked.connect(save)
        d_lay.addWidget(btn_save)

        dlg.exec()

    # ── Tab 5: Owner-Operator Yield & Uptime Cockpit ──
    def setup_tab_owner_operator(self):
        lay = QVBoxLayout(self.tab_owner_operator)
        lay.setContentsMargins(8, 8, 8, 8)

        # Header
        h_bar = QHBoxLayout()
        lbl_t = QLabel("🚀 Owner-Operator Yield & Uptime Cockpit (Triangulation, IFTA, Clearance)")
        lbl_t.setStyleSheet("font-size: 11pt; font-weight: bold; color: #EC4899;")
        h_bar.addWidget(lbl_t)
        h_bar.addStretch()

        btn_recalc = QPushButton("🔄 Refresh Loops")
        btn_recalc.setStyleSheet("background-color: #BE185D; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px;")
        btn_recalc.clicked.connect(self.load_owner_operator_ui)
        h_bar.addWidget(btn_recalc)
        lay.addLayout(h_bar)

        # Triangulation Table
        self.table_triangulation = QTableWidget(0, 6)
        self.table_triangulation.setHorizontalHeaderLabels([
            "Loop Name", "Loaded", "Deadhead", "Gross Pay", "True RPM", "Est. EBITDA"
        ])
        self.table_triangulation.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_triangulation.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_triangulation)

        # Bottom Grid for IFTA and Clearance
        b_grid = QGridLayout()

        # IFTA Card
        f_ifta = QFrame()
        f_ifta.setStyleSheet("background-color: #0F172A; border: 1px solid #10B981; border-radius: 6px; padding: 6px;")
        lay_i = QVBoxLayout(f_ifta)
        lbl_i_title = QLabel("📊 <b>IFTA Quarterly Tax (2026-Q4)</b>")
        lbl_i_title.setStyleSheet("color: #10B981; font-size: 10pt;")
        lay_i.addWidget(lbl_i_title)
        self.lbl_ifta_status = QLabel("Calculating...")
        self.lbl_ifta_status.setStyleSheet("color: #F8FAFC; font-size: 8.5pt;")
        lay_i.addWidget(self.lbl_ifta_status)
        b_grid.addWidget(f_ifta, 0, 0)

        # Clearance Card
        f_clr = QFrame()
        f_clr.setStyleSheet("background-color: #0F172A; border: 1px solid #F59E0B; border-radius: 6px; padding: 6px;")
        lay_c = QVBoxLayout(f_clr)
        lbl_c_title = QLabel("🛡️ <b>Commercial Clearance Radar (12'6\")</b>")
        lbl_c_title.setStyleSheet("color: #F59E0B; font-size: 10pt;")
        lay_c.addWidget(lbl_c_title)
        lbl_c_txt = QLabel("⚠️ <b>CRITICAL:</b> Lake Shore Drive (US-41) Commercial Prohibited. STAA truck routes only.")
        lbl_c_txt.setStyleSheet("color: #F87171; font-size: 8.5pt;")
        lay_c.addWidget(lbl_c_txt)
        b_grid.addWidget(f_clr, 0, 1)

        lay.addLayout(b_grid)

    def load_owner_operator_ui(self):
        chains = self._snapshot.get('chains', [])
        self.table_triangulation.setRowCount(0)

        for c in chains:
            r = self.table_triangulation.rowCount()
            self.table_triangulation.insertRow(r)
            self.table_triangulation.setItem(r, 0, QTableWidgetItem(c.get("name")))
            self.table_triangulation.setItem(r, 1, QTableWidgetItem(f"{c.get('total_loaded_miles')} mi"))
            self.table_triangulation.setItem(r, 2, QTableWidgetItem(f"{c.get('total_deadhead_miles')} mi"))
            self.table_triangulation.setItem(r, 3, QTableWidgetItem(f"${c.get('total_gross_pay', 0):,.2f}"))

            rpm_item = QTableWidgetItem(f"${c.get('effective_true_rpm', 0):.2f}/mi")
            rpm_item.setForeground(QColor("#10B981"))
            self.table_triangulation.setItem(r, 4, rpm_item)

            ebitda_item = QTableWidgetItem(f"${c.get('projected_net_ebitda', 0):,.2f}")
            ebitda_item.setForeground(QColor("#38BDF8"))
            self.table_triangulation.setItem(r, 5, ebitda_item)

        try:
            ifta = self._snapshot.get('ifta')
            if not isinstance(ifta, dict):
                self.lbl_ifta_status.setText('IFTA data unavailable. Refresh the dispatch service.')
                return
            status_txt = "Refund Due" if ifta.get("total_net_tax_due", 0) <= 0 else "Tax Owed"
            amt = abs(ifta.get("total_net_tax_due", 0))
            self.lbl_ifta_status.setText(
                f"Miles: {ifta.get('total_miles')} mi | Fuel: {ifta.get('total_gallons_purchased')} gal | MPG: {ifta.get('fleet_mpg')}<br>"
                f"Net IFTA Position: <b style='color:#10B981'>${amt:,.2f} ({status_txt})</b>"
            )
        except Exception as e:
            self.lbl_ifta_status.setText(f"IFTA error: {e}")

    # ── Ingest & Telemetry ──
    def trigger_live_public_sync(self):
        if self._write_pending:
            return
        home = self.in_home_base.text().strip() or "Grand Rapids, MI"
        self.btn_sync_live.setEnabled(False)
        self.btn_sync_live.setText("Fetching...")
        self._run_action(lambda: self.api.sync_public_loads(home),
                         on_success=lambda count: self.on_live_sync_finished(count, "OK"))

    def on_live_sync_finished(self, count: int, status: str):
        self.btn_sync_live.setEnabled(True)
        self.btn_sync_live.setText("🌐 Pull Live Loads")
        self.refresh_all_data()

    def refresh_all_data(self):
        if self._refresh_pending:
            return
        self._refresh_pending = True
        home = self.in_home_base.text().strip() or "Grand Rapids, MI"
        self.bus.submit(self.api.snapshot, home,
                        on_result=lambda data: self._apply_service_snapshot(data, home),
                        on_error=self._on_refresh_error)

    def _on_refresh_error(self, message):
        self._refresh_pending = False
        self._service_error = str(message)
        self.status_banner.setText("Dispatch data unavailable — " + self._service_error)

    def _apply_service_snapshot(self, data, home):
        self._refresh_pending = False
        if home != (self.in_home_base.text().strip() or "Grand Rapids, MI"):
            self.refresh_all_data()
            return
        self._service_error = ""
        self._snapshot = data
        self.load_board_from_db()
        self.load_active_dispatches_ui()
        self.load_ledger_ui()
        self.load_drivers_ui()
        self.load_owner_operator_ui()
        self.update_live_telemetry()

    def _run_action(self, operation, on_success=None):
        """One explicit action at a time; never retry an uncertain write automatically."""
        if self._write_pending:
            self.status_banner.setText("A dispatch action is already awaiting confirmation.")
            return
        self._write_pending = True
        self.status_banner.setText("Waiting for the dispatch service to confirm the action...")
        def restore_controls():
            self._write_pending = False
            self.btn_sync_live.setEnabled(True)
            self.btn_sync_live.setText("🌐 Pull Live Loads")
        def completed(result):
            restore_controls()
            self._service_error = ""
            if on_success:
                on_success(result)
            else:
                self.refresh_all_data()
        def failed(message):
            restore_controls()
            self._service_error = str(message)
            self.status_banner.setText("Action not confirmed — " + self._service_error)
        self.bus.submit(operation, on_result=completed, on_error=failed)

    def load_board_from_db(self):
        # Kept as an internal renderer name for callers; it never opens a database.
        self.raw_loads_cache = list(self._snapshot.get('loads', []))
        self.apply_board_filters()

    def update_live_telemetry(self):
        if getattr(self, '_service_error', ''):
            return
        if not self._snapshot:
            self.status_banner.setText('Loading dispatch service data...')
            return
        status = self._snapshot.get('status', {})
        total_loads = status.get('total_loads', len(self.raw_loads_cache))
        green_loads = status.get('greenlight_loads', 0)
        dispatches = self._snapshot.get('dispatches', [])
        active_count = len([d for d in dispatches if d.get('status') != 'DELIVERED'])
        drivers_count = len(self._snapshot.get('drivers', []))
        self.status_banner.setText(
            f"AI-BS DISPATCH SERVICE | Active Leads: {total_loads} | "
            f"Greenlight: {green_loads} | Active Hauls: {active_count} | "
            f"1099 Drivers: {drivers_count} | Terminal: {self.in_home_base.text().strip() or 'Grand Rapids, MI'}")
        self.tabs.setTabText(0, f"📋 Live Load Board ({len(self.raw_loads_cache)})")
        self.tabs.setTabText(1, f"🚚 Devin's Active Hauls ({active_count})")
        total_net = sum(float(d.get('net_profit', 0.0)) for d in dispatches)
        self.tabs.setTabText(2, f"💰 Trip Profit & BOL Ledger (${total_net:,.0f})")
        self.tabs.setTabText(3, f"👥 1099 Drivers & Tax Spreadsheet ({drivers_count})")
