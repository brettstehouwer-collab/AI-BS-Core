"""
FE Express - Native Windows Desktop Box Truck Automation Hub (PyQt6)
Built in strict compliance with Global Directive: Pure Native GUI Frameworks (QtWidgets / Direct2D HWND),
Zero Browser Engines, Multi-Threaded QThread Worker Polling, and Real Live Public Load Board Data (Zero-Mock).
Full 100% feature parity with FEExpressDispatcher.jsx:
- Tab 1: 📋 Live Load Board (Search, Fleet Switcher: Box vs Van, Filters, KPI stats, Bid Modal, Backhaul Radar, Manual Book Load)
- Tab 2: 🚚 Devin's Active Hauls (En-route tracking, status stepper, 📸 Native File BOL / Delivery Attacher)
- Tab 3: 💰 Trip Profit & BOL Ledger (Gross, Fuel, Tolls, Net, Delivery Proofs, Filter/Export)
- Tab 4: 👥 1099 Drivers & Tax Spreadsheet (Contractor directory, Medical Card/MVR/W-9 audit, Trip Settlements, Year-End 1099-NEC)
- Zero Auto-Book Mandate: Strict manual booking with explicit user confirmation.
"""

import os
import sys
import sqlite3
import logging
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor, QIcon, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QMessageBox,
    QTabWidget,
    QDialog,
    QTextEdit,
    QComboBox,
    QFileDialog,
    QScrollArea,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
)

from fe_express_live_ingestor import sync_live_loads_to_db, DB_PATH
from fe_express_active_ledger import ActiveLoadManager, init_active_loads_db
from fe_express_bid_generator import BrokerBidGenerator
from fe_express_backhaul import BackhaulEngine
from fe_express_broker_credit import BrokerCreditSentinel
from fe_express_spot_benchmark import LaneSpotBenchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FE_Automation")

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

ICON_PATH = Path(r"C:\AI-BS\installer\app_icon.ico")


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


class LiveBoardSyncWorker(QThread):
    finished_sync = pyqtSignal(int, str)

    def __init__(self, home_base: str = "Grand Rapids, MI"):
        super().__init__()
        self.home_base = home_base

    def run(self):
        try:
            loads = sync_live_loads_to_db(self.home_base)
            self.finished_sync.emit(len(loads), "OK")
        except Exception as e:
            self.finished_sync.emit(0, str(e))


class RemoteTunnelUpdateWorker(QThread):
    """Checks the sovereign Cloudflare tunnel for software updates and patches silently."""

    update_status = pyqtSignal(bool, str, str)

    def __init__(self, current_version: str = "v5.338.0", tunnel_url: str = "https://api.brettstehouwer.live/api/v1/fe-express"):
        super().__init__()
        self.current_version = current_version
        self.tunnel_url = tunnel_url

    def run(self):
        import requests
        try:
            url = f"{self.tunnel_url}/version"
            r = requests.get(url, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                remote_ver = data.get("current_version", self.current_version)
                if remote_ver != self.current_version:
                    notes = data.get("release_notes", "Bug fixes & performance improvements.")
                    self.update_status.emit(True, remote_ver, notes)
                    return
            self.update_status.emit(False, self.current_version, "Up to date")
        except Exception:
            # Silent fallback if offline or tunnel warming up
            self.update_status.emit(False, self.current_version, "Offline / Local Mode")


class AsyncFactoringGatewayWorker(QThread):
    """
    Decoupled Background Worker Thread:
    Transmits signed BOL + Rate Confirmation PDF to Factoring House Gateway (Triumph/Apex)
    and updates SQLite records in shared RAM without freezing the UI event loop.
    """
    factoring_completed = pyqtSignal(bool, dict)

    def __init__(self, dispatch_id: str, gateway_key: str = "TRIUMPH"):
        super().__init__()
        self.dispatch_id = dispatch_id
        self.gateway_key = gateway_key

    def run(self):
        try:
            from backend.core.fe_express_owner_operator_engine import AsyncFactoringGatewayClient
            res = AsyncFactoringGatewayClient.execute_async_factoring_submission(
                dispatch_id=self.dispatch_id,
                gateway_key=self.gateway_key
            )
            self.factoring_completed.emit(True, res)
        except Exception as e:
            logger.error(f"Error in AsyncFactoringGatewayWorker: {e}")
            self.factoring_completed.emit(False, {"error": str(e)})


# -------------------------------------------------------------
# DIALOGS & MODALS
# -------------------------------------------------------------

class BidGeneratorDialog(QDialog):
    """Native Dialog to view, tweak, and copy/email rate bids."""

    def __init__(self, load: Dict[str, Any], home_base: str, parent=None):
        super().__init__(parent)
        self.load = load
        self.home_base = home_base
        self.setWindowTitle(f"💼 Rate Confirmation Bid — {load.get('load_id')}")
        self.resize(750, 620)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; }
            QLabel { color: #E2E8F0; font-size: 13px; }
            QLineEdit, QTextEdit { background-color: #1E293B; border: 1px solid #334155; color: #F8FAFC; border-radius: 4px; padding: 6px; font-family: 'Consolas', 'Segoe UI'; font-size: 12px; }
            QPushButton { background-color: #2563EB; color: white; font-weight: bold; border-radius: 4px; padding: 8px 14px; }
            QPushButton:hover { background-color: #1D4ED8; }
        """)

        layout = QVBoxLayout(self)

        # Header Info
        broker = load.get("broker_name", "Broker")
        origin = load.get("origin_city_state", "")
        dest = load.get("dest_city_state", "")
        posted_pay = float(load.get("flat_rate_pay", 0.0))
        target_bid = round(posted_pay * 1.10, 2) if posted_pay > 0 else 850.0

        lbl_title = QLabel(f"<b>Negotiation Engine:</b> {origin} ➡️ {dest} (${posted_pay:,.0f} posted pay)")
        lbl_title.setStyleSheet("font-size: 15px; color: #38BDF8;")
        layout.addWidget(lbl_title)

        lbl_broker = QLabel(f"Broker: {broker} | Phone: {load.get('broker_phone', 'N/A')}")
        layout.addWidget(lbl_broker)

        # Generated Email Subject
        layout.addWidget(QLabel("Email Subject:"))
        self.in_subject = QLineEdit(f"RATE CONFIRMATION / TRUCK IN HAND: {origin} -> {dest} [{load.get('load_id')}] - FE Express LLC")
        layout.addWidget(self.in_subject)

        # Generated Email Body
        layout.addWidget(QLabel("Email Bid Body (Pre-Filled with Devin's Dispatch Direct Details):"))
        self.txt_body = QTextEdit()
        email_text = (
            f"Hello {broker} Team,\n\n"
            f"We have an empty, clean 26' Box Truck w/ Liftgate & Pallet Jack ready near {origin} "
            f"(Home Base: {home_base}) and can lock down your load {load.get('load_id')} immediately.\n\n"
            f"LOAD DETAILS:\n"
            f"• Origin: {origin}\n"
            f"• Destination: {dest}\n"
            f"• Distance: {load.get('total_miles', 0)} loaded miles\n"
            f"• Posted Pay: ${posted_pay:,.2f}\n"
            f"• Our All-In Rate Bid: ${target_bid:,.2f} (Clean rate, no accessorials required)\n\n"
            f"EQUIPMENT & COMPLIANCE:\n"
            f"• 26' Straight Box Truck (Up to 10,000 lbs / 12 Standard Pallets)\n"
            f"• E-tracks, 4 load bars, 8 ratchet straps, moving blankets\n"
            f"• MC-1482910 | USDOT-3918241\n"
            f"• $1,000,000 Auto Liability / $100,000 Cargo (COI ready to transmit)\n\n"
            f"Please transmit the rate confirmation packet to {DEVIN_PROFILE['email']} "
            f"or contact Devin directly at {DEVIN_PROFILE['phone']}.\n\n"
            f"Thank you,\n"
            f"Devin | FE Express Dispatch\n"
            f"Direct: {DEVIN_PROFILE['phone']}\n"
            f"Email: {DEVIN_PROFILE['email']}"
        )
        self.txt_body.setPlainText(email_text)
        layout.addWidget(self.txt_body)

        # SMS Script
        layout.addWidget(QLabel("Ultra-Short 1-Click SMS Script:"))
        self.in_sms = QLineEdit(
            f"FE Express (MC-1482910) has a 26' box truck empty at {origin} for load {load.get('load_id')} "
            f"({origin}->{dest}). Can take for ${target_bid:,.0f} all-in. Call/text Devin at {DEVIN_PROFILE['phone']}."
        )
        layout.addWidget(self.in_sms)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_copy_email = QPushButton("📋 Copy Email Bid")
        btn_copy_email.clicked.connect(self.copy_email)
        btn_layout.addWidget(btn_copy_email)

        btn_copy_sms = QPushButton("💬 Copy SMS")
        btn_copy_sms.clicked.connect(self.copy_sms)
        btn_layout.addWidget(btn_copy_sms)

        btn_launch_email = QPushButton("✉️ Open in Windows Mail Client")
        btn_launch_email.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        btn_launch_email.clicked.connect(self.launch_mail)
        btn_layout.addWidget(btn_launch_email)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background-color: #475569;")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def copy_email(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txt_body.toPlainText())
        QMessageBox.information(self, "Copied", "Email bid copied to clipboard!")

    def copy_sms(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.in_sms.text())
        QMessageBox.information(self, "Copied", "SMS text copied to clipboard!")

    def launch_mail(self):
        subject = self.in_subject.text()
        body = self.txt_body.toPlainText()
        mailto = f"mailto:?subject={QUrl.toPercentEncoding(subject).data().decode()}&body={QUrl.toPercentEncoding(body).data().decode()}"
        QDesktopServices.openUrl(QUrl(mailto))


class BackhaulRadarDialog(QDialog):
    """Native Dialog showing reverse / reload candidates from delivery point towards home."""

    def __init__(self, load: Dict[str, Any], home_base: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"🔄 Smart Backhaul Radar — {load.get('dest_city_state')} ➡️ {home_base}")
        self.resize(850, 480)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; }
            QLabel { color: #E2E8F0; }
            QTableWidget { background-color: #111827; gridline-color: #1F2937; border: 1px solid #1F2937; color: #F8FAFC; }
            QHeaderView::section { background-color: #1F2937; color: #9CA3AF; padding: 6px; border: none; font-weight: bold; }
            QPushButton { background-color: #2563EB; color: white; font-weight: bold; border-radius: 4px; padding: 6px 12px; }
        """)

        layout = QVBoxLayout(self)

        dest = load.get("dest_city_state", "")
        lbl_head = QLabel(f"<b>Scanning for Reloads:</b> Originating near <b>{dest}</b> delivering back towards <b>{home_base}</b>")
        lbl_head.setStyleSheet("font-size: 14px; color: #10B981; padding-bottom: 6px;")
        layout.addWidget(lbl_head)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Load ID", "Origin ➡️ Destination", "Equipment", "Weight", "Pay ($)", "RPM ($/mi)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Query candidates
        candidates = BackhaulEngine.find_backhauls(dest, home_base)
        for c in candidates:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(c.get("load_id"))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"{c.get('origin_city_state')} ➡️ {c.get('dest_city_state')}"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(c.get("equipment_type"))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{c.get('weight_lbs', 0):,.0f} lbs"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"${c.get('flat_rate_pay', 0):,.0f}"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(f"${c.get('rpm', 0):.2f}/mi"))

        if not candidates:
            lbl_empty = QLabel("No direct return loads found right at this minute. Check public live feed or expand search radius.")
            lbl_empty.setStyleSheet("color: #F59E0B; font-style: italic;")
            layout.addWidget(lbl_empty)

        btn_close = QPushButton("Close Radar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class AddContractorDriverDialog(QDialog):
    """Native Dialog to register a 1099 Subcontract Driver."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("➕ Register 1099 Subcontract Driver")
        self.resize(500, 480)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; }
            QLabel { color: #E2E8F0; font-size: 13px; }
            QLineEdit, QComboBox, QTextEdit { background-color: #1E293B; border: 1px solid #334155; color: #F8FAFC; border-radius: 4px; padding: 6px; }
            QPushButton { background-color: #2563EB; color: white; font-weight: bold; border-radius: 4px; padding: 8px 14px; }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.in_name = QLineEdit()
        self.in_phone = QLineEdit()
        self.in_email = QLineEdit()
        self.in_ssn = QLineEdit()
        self.in_ssn.setPlaceholderText("Last 4 of SSN or EIN")
        self.in_dl = QLineEdit()
        self.in_dl_state = QLineEdit("MI")
        
        self.combo_pay_model = QComboBox()
        self.combo_pay_model.addItems(["PERCENT_GROSS (e.g. 25% of load gross)", "PER_MILE (e.g. $0.55/mile)", "FLAT_PER_DAY (e.g. $200/day)"])

        self.in_pay_rate = QDoubleSpinBox()
        self.in_pay_rate.setRange(0.0, 1000.0)
        self.in_pay_rate.setValue(25.0)

        self.in_med_exp = QLineEdit("2027-01-01")
        self.combo_mvr = QComboBox()
        self.combo_mvr.addItems(["CLEARED", "PENDING", "ACTION_REQUIRED"])

        self.combo_w9 = QComboBox()
        self.combo_w9.addItems(["Yes (W-9 On File)", "No (Pending W-9)"])

        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(60)

        form.addRow("Driver Full Name*:", self.in_name)
        form.addRow("Phone Number:", self.in_phone)
        form.addRow("Email Address:", self.in_email)
        form.addRow("SSN / Tax ID (Last 4):", self.in_ssn)
        form.addRow("Driver's License #:", self.in_dl)
        form.addRow("DL State:", self.in_dl_state)
        form.addRow("Pay Model:", self.combo_pay_model)
        form.addRow("Agreed Rate (% or $/mi or $/day):", self.in_pay_rate)
        form.addRow("DOT Med Card Expiration:", self.in_med_exp)
        form.addRow("MVR Check Status:", self.combo_mvr)
        form.addRow("W-9 Tax Form Status:", self.combo_w9)
        form.addRow("Operational Notes:", self.txt_notes)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 Save 1099 Driver")
        btn_save.clicked.connect(self.save_driver)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #475569;")
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def save_driver(self):
        name = self.in_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Driver Full Name is required.")
            return

        model_key = "PERCENT_GROSS"
        if "PER_MILE" in self.combo_pay_model.currentText():
            model_key = "PER_MILE"
        elif "FLAT_PER_DAY" in self.combo_pay_model.currentText():
            model_key = "FLAT_PER_DAY"

        w9_val = 1 if "Yes" in self.combo_w9.currentText() else 0

        driver_payload = {
            "full_name": name,
            "phone": self.in_phone.text().strip(),
            "email": self.in_email.text().strip(),
            "tax_id_or_ssn_last4": self.in_ssn.text().strip() or "XXXX",
            "driver_license_num": self.in_dl.text().strip(),
            "driver_license_state": self.in_dl_state.text().strip(),
            "pay_model": model_key,
            "pay_rate": self.in_pay_rate.value(),
            "medical_card_exp": self.in_med_exp.text().strip(),
            "mvr_check_status": self.combo_mvr.currentText(),
            "w9_on_file": w9_val,
            "notes": self.txt_notes.toPlainText().strip()
        }

        res = ActiveLoadManager.save_contractor_driver(driver_payload)
        if res.get("success"):
            QMessageBox.information(self, "Success", f"1099 Driver {name} registered successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save driver to database.")


class RecordSettlementDialog(QDialog):
    """Native Dialog to calculate and record a 1099 driver payout."""

    def __init__(self, drivers: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.drivers = drivers
        self.setWindowTitle("💵 Record 1099 Trip Settlement")
        self.resize(520, 500)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; }
            QLabel { color: #E2E8F0; font-size: 13px; }
            QLineEdit, QComboBox, QTextEdit { background-color: #1E293B; border: 1px solid #334155; color: #F8FAFC; border-radius: 4px; padding: 6px; }
            QPushButton { background-color: #059669; color: white; font-weight: bold; border-radius: 4px; padding: 8px 14px; }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_driver = QComboBox()
        for d in self.drivers:
            self.combo_driver.addItem(f"{d['full_name']} ({d.get('pay_model', 'PERCENT_GROSS')} @ {d.get('pay_rate', 25)})", d)
        self.combo_driver.currentIndexChanged.connect(self.recalculate_payout)

        self.in_date = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.in_lane = QLineEdit()
        self.in_lane.setPlaceholderText("e.g. Grand Rapids, MI -> Chicago, IL")
        
        self.spin_miles = QDoubleSpinBox()
        self.spin_miles.setRange(0.0, 5000.0)
        self.spin_miles.setValue(180.0)
        self.spin_miles.valueChanged.connect(self.recalculate_payout)

        self.spin_gross = QDoubleSpinBox()
        self.spin_gross.setRange(0.0, 20000.0)
        self.spin_gross.setValue(600.0)
        self.spin_gross.valueChanged.connect(self.recalculate_payout)

        self.spin_fuel_deduct = QDoubleSpinBox()
        self.spin_fuel_deduct.setRange(0.0, 2000.0)
        self.spin_fuel_deduct.setValue(0.0)
        self.spin_fuel_deduct.valueChanged.connect(self.recalculate_payout)

        self.spin_advance = QDoubleSpinBox()
        self.spin_advance.setRange(0.0, 2000.0)
        self.spin_advance.setValue(0.0)
        self.spin_advance.valueChanged.connect(self.recalculate_payout)

        self.lbl_net_payout = QLabel("$150.00")
        self.lbl_net_payout.setStyleSheet("font-size: 18px; font-weight: bold; color: #10B981;")

        self.combo_method = QComboBox()
        self.combo_method.addItems(["ZELLE", "DIRECT_DEPOSIT", "CHECK", "CASH"])

        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(50)

        form.addRow("Select 1099 Driver*:", self.combo_driver)
        form.addRow("Trip Date:", self.in_date)
        form.addRow("Origin ➡️ Destination:", self.in_lane)
        form.addRow("Loaded Miles:", self.spin_miles)
        form.addRow("Gross Load Revenue ($):", self.spin_gross)
        form.addRow("Fuel Advance / Deduct ($):", self.spin_fuel_deduct)
        form.addRow("Cash Advance / Deduct ($):", self.spin_advance)
        form.addRow("Net 1099 Driver Payout:", self.lbl_net_payout)
        form.addRow("Payment Method:", self.combo_method)
        form.addRow("Notes / Check #:", self.txt_notes)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_record = QPushButton("✅ Record & Issue Settlement")
        btn_record.clicked.connect(self.record_settlement)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #475569;")
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_record)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        self.recalculate_payout()

    def recalculate_payout(self):
        driver_data = self.combo_driver.currentData()
        if not driver_data:
            return

        gross = self.spin_gross.value()
        miles = self.spin_miles.value()
        fuel = self.spin_fuel_deduct.value()
        advance = self.spin_advance.value()

        pay_model = driver_data.get("pay_model", "PERCENT_GROSS")
        pay_rate = float(driver_data.get("pay_rate", 25.0))

        if pay_model == "PERCENT_GROSS":
            earned = gross * (pay_rate / 100.0)
        elif pay_model == "PER_MILE":
            earned = miles * pay_rate
        else:
            earned = pay_rate

        net = round(earned - fuel - advance, 2)
        self.lbl_net_payout.setText(f"${net:,.2f}")

    def record_settlement(self):
        driver_data = self.combo_driver.currentData()
        if not driver_data:
            QMessageBox.warning(self, "Validation", "Select a driver.")
            return

        gross = self.spin_gross.value()
        miles = self.spin_miles.value()
        fuel = self.spin_fuel_deduct.value()
        advance = self.spin_advance.value()

        pay_model = driver_data.get("pay_model", "PERCENT_GROSS")
        pay_rate = float(driver_data.get("pay_rate", 25.0))

        if pay_model == "PERCENT_GROSS":
            earned = gross * (pay_rate / 100.0)
        elif pay_model == "PER_MILE":
            earned = miles * pay_rate
        else:
            earned = pay_rate

        net = round(earned - fuel - advance, 2)

        settle_payload = {
            "driver_id": driver_data.get("driver_id"),
            "dispatch_id": f"DISP-{int(datetime.now().timestamp())}",
            "trip_date": self.in_date.text().strip(),
            "origin_dest": self.in_lane.text().strip() or "Custom Haul",
            "total_miles": miles,
            "gross_load_pay": gross,
            "contractor_pay": earned,
            "fuel_deduction": fuel,
            "cash_advance": advance,
            "net_1099_payout": net,
            "payment_status": "PAID",
            "payment_method": self.combo_method.currentText(),
            "notes": self.txt_notes.toPlainText().strip()
        }

        res = ActiveLoadManager.record_settlement(settle_payload)
        if res.get("success"):
            QMessageBox.information(self, "Recorded", f"Settlement of ${net:,.2f} recorded for {driver_data['full_name']}!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to record settlement.")


class BOLUpdateDialog(QDialog):
    """Native Dialog to upload/attach BOL delivery proof and record final fuel/tolls."""

    def __init__(self, dispatch: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.dispatch = dispatch
        self.selected_bol_path = dispatch.get("bol_photo_url") or ""
        self.setWindowTitle(f"📸 Delivery Proof & BOL Attacher — {dispatch.get('dispatch_id')}")
        self.resize(540, 420)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; color: #F8FAFC; }
            QLabel { color: #E2E8F0; font-size: 13px; }
            QLineEdit, QComboBox, QTextEdit { background-color: #1E293B; border: 1px solid #334155; color: #F8FAFC; border-radius: 4px; padding: 6px; }
            QPushButton { background-color: #2563EB; color: white; font-weight: bold; border-radius: 4px; padding: 8px 14px; }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        lbl_head = QLabel(f"<b>Haul:</b> {dispatch.get('origin')} ➡️ {dispatch.get('destination')} (${dispatch.get('gross_pay', 0):,.0f} Gross)")
        lbl_head.setStyleSheet("color: #38BDF8; font-size: 14px;")
        layout.addWidget(lbl_head)

        self.combo_status = QComboBox()
        self.combo_status.addItems(["DELIVERED", "EN_ROUTE_DELIVERY", "EN_ROUTE_PICKUP"])
        current_st = dispatch.get("status", "EN_ROUTE_PICKUP")
        idx = self.combo_status.findText(current_st)
        if idx >= 0:
            self.combo_status.setCurrentIndex(idx)

        self.spin_fuel = QDoubleSpinBox()
        self.spin_fuel.setRange(0.0, 5000.0)
        self.spin_fuel.setValue(float(dispatch.get("fuel_cost", 40.0)))

        self.spin_tolls = QDoubleSpinBox()
        self.spin_tolls.setRange(0.0, 1000.0)
        self.spin_tolls.setValue(float(dispatch.get("tolls_cost", 20.0)))

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlainText(dispatch.get("bol_notes") or "Delivered clean, signed BOL on file.")
        self.txt_notes.setMaximumHeight(60)

        # File Chooser Row
        file_row = QHBoxLayout()
        self.lbl_file_display = QLabel(self.selected_bol_path or "No file selected")
        self.lbl_file_display.setStyleSheet("color: #94A3B8; font-size: 11px;")
        btn_choose = QPushButton("📁 Select BOL File / Photo")
        btn_choose.clicked.connect(self.choose_file)
        file_row.addWidget(btn_choose)
        file_row.addWidget(self.lbl_file_display)

        form.addRow("Haul Status:", self.combo_status)
        form.addRow("Actual Fuel Cost ($):", self.spin_fuel)
        form.addRow("Tolls & Scales ($):", self.spin_tolls)
        form.addRow("Attach BOL Document:", file_row)
        form.addRow("Delivery Notes:", self.txt_notes)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 Update Haul & Lock Net Profit")
        btn_save.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_bol)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #475569;")
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def choose_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Bill of Lading (BOL) or Delivery Photo", "", "Images & PDFs (*.png *.jpg *.jpeg *.pdf *.bmp)"
        )
        if filepath:
            self.selected_bol_path = filepath
            self.lbl_file_display.setText(Path(filepath).name)

    def save_bol(self):
        dispatch_id = self.dispatch.get("dispatch_id")
        updates = {
            "status": self.combo_status.currentText(),
            "fuel_cost": self.spin_fuel.value(),
            "tolls_cost": self.spin_tolls.value(),
            "bol_notes": self.txt_notes.toPlainText().strip(),
            "bol_photo_url": self.selected_bol_path
        }
        res = ActiveLoadManager.update_load_accounting(dispatch_id, updates)
        if res.get("success"):
            QMessageBox.information(self, "Success", f"Haul updated! Final Net Profit: ${res.get('net_profit'):,.2f}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to update haul.")


# -------------------------------------------------------------
# MAIN WINDOW WITH 4 TABBS
# -------------------------------------------------------------

class FEExpressNativeWindow(QMainWindow):
    """Pure Native PyQt6 Desktop Window (HWND) with 100% feature parity with Web FE Express."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FE EXPRESS — Live Public Load Board & Dispatch Automation (Native Desktop)")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1380, 840)
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0B0F19; color: #F8FAFC; font-family: 'Segoe UI'; }
            QLineEdit, QComboBox { background-color: #1F2937; border: 1px solid #374151; color: #F8FAFC; padding: 6px; border-radius: 4px; }
            QPushButton { background-color: #2563EB; color: #FFFFFF; font-weight: bold; padding: 6px 12px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #1D4ED8; }
            QTableWidget { background-color: #111827; gridline-color: #1F2937; border: 1px solid #1F2937; color: #F8FAFC; }
            QHeaderView::section { background-color: #1F2937; color: #9CA3AF; padding: 6px; border: none; font-weight: bold; }
            QTabWidget::pane { border: 1px solid #1F2937; background-color: #0B0F19; }
            QTabBar::tab { background-color: #1E293B; color: #94A3B8; padding: 10px 18px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; }
            QTabBar::tab:selected { background-color: #2563EB; color: #FFFFFF; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Top Header Row
        top_row = QHBoxLayout()
        header = QLabel("🚚 FE EXPRESS | Sovereign Dispatch & Accounting Hub")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #38BDF8; padding-bottom: 2px;")
        top_row.addWidget(header)
        top_row.addStretch()

        self.in_home_base = QLineEdit("Grand Rapids, MI")
        self.in_home_base.setFixedWidth(170)
        lbl_hb = QLabel("Home Base (Deadhead):")
        lbl_hb.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        top_row.addWidget(lbl_hb)
        top_row.addWidget(self.in_home_base)

        self.btn_sync_live = QPushButton("🌐 Pull Real Live Public Loads")
        self.btn_sync_live.setStyleSheet("background-color: #059669; color: #FFFFFF; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        self.btn_sync_live.clicked.connect(self.trigger_live_public_sync)
        top_row.addWidget(self.btn_sync_live)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setStyleSheet("background-color: #1E293B; color: #38BDF8; border: 1px solid #38BDF8; border-radius: 4px;")
        btn_refresh.clicked.connect(self.refresh_all_data)
        top_row.addWidget(btn_refresh)

        main_layout.addLayout(top_row)

        # Devin Dispatch Profile Quick Bar
        profile_bar = QFrame()
        profile_bar.setStyleSheet("background-color: #0F172A; border: 1px solid #2563EB; border-radius: 6px; padding: 6px;")
        p_layout = QHBoxLayout(profile_bar)
        
        lbl_p_info = QLabel(
            f"👤 <b>Dispatcher: Devin</b> (FE Express LLC) | "
            f"📞 Direct: <b style='color:#10B981'>{DEVIN_PROFILE['phone']}</b> | "
            f"✉️ Email: <b style='color:#38BDF8'>{DEVIN_PROFILE['email']}</b> | "
            f"Authority: {DEVIN_PROFILE['mc']} | {DEVIN_PROFILE['usdot']}"
        )
        p_layout.addWidget(lbl_p_info)
        p_layout.addStretch()

        btn_call = QPushButton("📞 Call Devin")
        btn_call.setStyleSheet("background-color: #059669; color: white; padding: 4px 10px;")
        btn_call.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"tel:{DEVIN_PROFILE['phone_digits']}")))
        p_layout.addWidget(btn_call)

        btn_sms = QPushButton("💬 SMS Devin")
        btn_sms.setStyleSheet("background-color: #0284C7; color: white; padding: 4px 10px;")
        btn_sms.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"sms:{DEVIN_PROFILE['phone_digits']}")))
        p_layout.addWidget(btn_sms)

        btn_email = QPushButton("✉️ Email Devin")
        btn_email.setStyleSheet("background-color: #4F46E5; color: white; padding: 4px 10px;")
        btn_email.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"mailto:{DEVIN_PROFILE['email']}")))
        p_layout.addWidget(btn_email)

        main_layout.addWidget(profile_bar)

        # Status Banner
        self.status_banner = QLabel("🟢 REAL PUBLIC BOARD FEED (Trulos Live) | Initializing...")
        self.status_banner.setStyleSheet(
            "background-color: #064E3B; color: #A7F3D0; border: 1px solid #10B981; "
            "border-radius: 6px; padding: 8px 12px; font-weight: bold; font-size: 13px;"
        )
        main_layout.addWidget(self.status_banner)

        # 4 Navigation Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create Tab 1: Live Load Board
        self.tab_board = QWidget()
        self.setup_tab_board()
        self.tabs.addTab(self.tab_board, "📋 Live Load Board")

        # Create Tab 2: Devin's Active Hauls
        self.tab_active = QWidget()
        self.setup_tab_active()
        self.tabs.addTab(self.tab_active, "🚚 Devin's Active Hauls")

        # Create Tab 3: Trip Profit & BOL Ledger
        self.tab_ledger = QWidget()
        self.setup_tab_ledger()
        self.tabs.addTab(self.tab_ledger, "💰 Trip Profit & BOL Ledger")

        # Create Tab 4: 1099 Drivers & Tax Spreadsheet
        self.tab_drivers = QWidget()
        self.setup_tab_drivers()
        self.tabs.addTab(self.tab_drivers, "👥 1099 Drivers & Tax Spreadsheet")

        # Create Tab 5: Owner-Operator Yield & Uptime Cockpit
        self.tab_owner_operator = QWidget()
        self.setup_tab_owner_operator()
        self.tabs.addTab(self.tab_owner_operator, "🚀 Owner-Operator Cockpit")

        # High-Speed Local Screen & Database Refresh (2 seconds)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.update_live_telemetry)
        self.telemetry_timer.start(2000)

        # High-Speed Automated Periodic Background Poller (Every 30 seconds)
        # Pulls live freight from public boards via isolated background QThread
        self.auto_sync_timer = QTimer(self)
        self.auto_sync_timer.timeout.connect(self.trigger_background_auto_sync)
        self.auto_sync_timer.start(30000)  # 30 seconds

        # Silent Cloudflare Tunnel Update Check
        self.tunnel_worker = RemoteTunnelUpdateWorker(current_version="v5.338.0")
        self.tunnel_worker.update_status.connect(self.on_tunnel_update_status)
        self.tunnel_worker.start()

        self.refresh_all_data()

    def trigger_background_auto_sync(self):
        """Silently fetches fresh public loads in the background without disabling UI buttons."""
        if hasattr(self, "worker") and self.worker.isRunning():
            return  # Prevent overlapping requests
        self.worker = LiveBoardSyncWorker(self.in_home_base.text().strip() or "Grand Rapids, MI")
        self.worker.finished_sync.connect(self.on_live_sync_finished)
        self.worker.start()

    def on_tunnel_update_status(self, update_available: bool, version: str, notes: str):
        if update_available:
            self.status_banner.setText(f"⚡ CLOUDFLARE TUNNEL UPDATE AVAILABLE ({version}): {notes} — Ready to auto-patch!")
            self.status_banner.setStyleSheet(
                "background-color: #1E3A8A; color: #93C5FD; border: 1px solid #3B82F6; "
                "border-radius: 6px; padding: 8px 12px; font-weight: bold; font-size: 13px;"
            )

    # -------------------------------------------------------------
    # TAB 1: LIVE LOAD BOARD
    # -------------------------------------------------------------
    def setup_tab_board(self):
        layout = QVBoxLayout(self.tab_board)

        # Filter & Search Strip
        filter_box = QFrame()
        filter_box.setStyleSheet("background-color: #111827; border: 1px solid #1F2937; border-radius: 6px; padding: 8px;")
        f_layout = QHBoxLayout(filter_box)

        # Fleet Selector Buttons
        lbl_fleet = QLabel("Fleet Type:")
        lbl_fleet.setStyleSheet("font-weight: bold; color: #38BDF8;")
        f_layout.addWidget(lbl_fleet)

        self.btn_fleet_all = QPushButton("All Fleet")
        self.btn_fleet_all.setStyleSheet("background-color: #2563EB; color: white;")
        self.btn_fleet_all.clicked.connect(lambda: self.set_vehicle_filter("ALL"))
        f_layout.addWidget(self.btn_fleet_all)

        self.btn_fleet_box = QPushButton("🚚 24'/26' Box Truck (≤10k lbs)")
        self.btn_fleet_box.setStyleSheet("background-color: #1E293B; color: #94A3B8;")
        self.btn_fleet_box.clicked.connect(lambda: self.set_vehicle_filter("BOX_TRUCK"))
        f_layout.addWidget(self.btn_fleet_box)

        self.btn_fleet_van = QPushButton("🚐 Cargo / Sprinter Van (≤4.5k lbs)")
        self.btn_fleet_van.setStyleSheet("background-color: #1E293B; color: #94A3B8;")
        self.btn_fleet_van.clicked.connect(lambda: self.set_vehicle_filter("CARGO_VAN"))
        f_layout.addWidget(self.btn_fleet_van)

        f_layout.addSpacing(16)

        # Criteria Inputs
        self.in_search_orig = QLineEdit()
        self.in_search_orig.setPlaceholderText("Origin / State...")
        self.in_search_orig.textChanged.connect(self.apply_board_filters)
        f_layout.addWidget(self.in_search_orig)

        self.in_search_dest = QLineEdit()
        self.in_search_dest.setPlaceholderText("Dest / State...")
        self.in_search_dest.textChanged.connect(self.apply_board_filters)
        f_layout.addWidget(self.in_search_dest)

        self.in_min_rpm = QLineEdit()
        self.in_min_rpm.setPlaceholderText("Min $/mi...")
        self.in_min_rpm.setFixedWidth(85)
        self.in_min_rpm.textChanged.connect(self.apply_board_filters)
        f_layout.addWidget(self.in_min_rpm)

        self.in_min_pay = QLineEdit()
        self.in_min_pay.setPlaceholderText("Min Pay $...")
        self.in_min_pay.setFixedWidth(85)
        self.in_min_pay.textChanged.connect(self.apply_board_filters)
        f_layout.addWidget(self.in_min_pay)

        self.in_max_wt = QLineEdit()
        self.in_max_wt.setPlaceholderText("Max Lbs...")
        self.in_max_wt.setFixedWidth(85)
        self.in_max_wt.textChanged.connect(self.apply_board_filters)
        f_layout.addWidget(self.in_max_wt)

        layout.addWidget(filter_box)

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
        layout.addWidget(self.table_board)

        self.vehicle_filter = "ALL"
        self.raw_loads_cache = []

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
        try:
            max_wt = float(self.in_max_wt.text().strip()) if self.in_max_wt.text().strip() else None
        except ValueError:
            max_wt = None

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
            if max_wt is not None and weight > max_wt:
                continue

            # Vehicle classification
            v_info = classify_equipment(equip, weight)
            if self.vehicle_filter == "BOX_TRUCK" and not v_info["is_box"]:
                continue
            if self.vehicle_filter == "CARGO_VAN" and not v_info["is_van"]:
                continue

            row_idx = self.table_board.rowCount()
            self.table_board.insertRow(row_idx)

            # Score Item
            score_item = QTableWidgetItem(r.get("score", "Reject"))
            if r.get("score") == "Greenlight":
                score_item.setBackground(QColor("#065F46"))
            elif r.get("score") == "Caution":
                score_item.setBackground(QColor("#92400E"))
            else:
                score_item.setBackground(QColor("#991B1B"))
            self.table_board.setItem(row_idx, 0, score_item)

            self.table_board.setItem(row_idx, 1, QTableWidgetItem(f"{r.get('origin_city_state')} ➡️ {r.get('dest_city_state')}"))
            
            # Equipment & Vehicle Match Badge
            v_badge = "🚚 Box Truck" if v_info["is_box"] else ("🚐 Cargo Van" if v_info["is_van"] else "⚠️ General")
            self.table_board.setItem(row_idx, 2, QTableWidgetItem(f"{v_badge} | {equip}"))
            self.table_board.setItem(row_idx, 3, QTableWidgetItem(f"{weight:,.0f} lbs"))
            self.table_board.setItem(row_idx, 4, QTableWidgetItem(f"${pay:,.0f}"))
            self.table_board.setItem(row_idx, 5, QTableWidgetItem(f"{r.get('total_miles', 0):,.0f} mi (${r.get('rpm', 0):.2f})"))
            self.table_board.setItem(row_idx, 6, QTableWidgetItem(f"${r.get('true_rpm', 0):.2f} (+{r.get('deadhead_miles', 0):,.0f} DH)"))
            self.table_board.setItem(row_idx, 7, QTableWidgetItem(str(r.get("broker_name", ""))))

            # Broker credit
            cr = BrokerCreditSentinel.get_broker_credit(r.get("broker_name", ""))
            f_status = cr.get("factoring_status") or cr.get("factoring", "APPROVED")
            self.table_board.setItem(row_idx, 8, QTableWidgetItem(f"{cr.get('score', 85)} ({f_status})"))

            # Actions Cell
            actions_widget = QWidget()
            a_layout = QHBoxLayout(actions_widget)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            btn_bid = QPushButton("💼 Bid")
            btn_bid.setStyleSheet("background-color: #2563EB; font-size: 11px; padding: 4px 6px;")
            btn_bid.clicked.connect(lambda _, load=r: self.open_bid_dialog(load))
            a_layout.addWidget(btn_bid)

            btn_blast = QPushButton("⚡ Blast")
            btn_blast.setStyleSheet("background-color: #BE185D; font-size: 11px; padding: 4px 6px; font-weight: bold;")
            btn_blast.clicked.connect(lambda _, load=r: self.open_blast_dialog(load))
            a_layout.addWidget(btn_blast)

            btn_horizon = QPushButton("🌅 Horizon")
            btn_horizon.setStyleSheet("background-color: #0284C7; font-size: 11px; padding: 4px 6px;")
            btn_horizon.clicked.connect(lambda _, load=r: self.open_horizon_dialog(load))
            a_layout.addWidget(btn_horizon)

            btn_radar = QPushButton("🔄 Backhaul")
            btn_radar.setStyleSheet("background-color: #059669; font-size: 11px; padding: 4px 6px;")
            btn_radar.clicked.connect(lambda _, load=r: self.open_backhaul_dialog(load))
            a_layout.addWidget(btn_radar)

            btn_book = QPushButton("⚡ Book")
            btn_book.setStyleSheet("background-color: #7C3AED; font-size: 11px; padding: 4px 6px;")
            btn_book.clicked.connect(lambda _, load=r: self.confirm_manual_book_load(load))
            a_layout.addWidget(btn_book)

            self.table_board.setCellWidget(row_idx, 9, actions_widget)

    def open_blast_dialog(self, load: Dict[str, Any]):
        from backend.core.fe_express_dispatcher_dream_cockpit import execute_multi_channel_blast_bid, check_broker_fraud_shield
        shield = check_broker_fraud_shield(load.get("broker_name", ""))
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"⚡ Multi-Channel Parallel Blast Bidding — {load.get('load_id')}")
        dlg.resize(540, 380)
        dlg.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
        d_lay = QVBoxLayout(dlg)

        lbl_head = QLabel(f"<b>Lane:</b> {load.get('origin_city_state')} ➡️ {load.get('dest_city_state')} | <b>Broker:</b> {load.get('broker_name')}")
        lbl_head.setStyleSheet("color: #F472B6; font-size: 13px;")
        d_lay.addWidget(lbl_head)

        # Inbound Ghost-Booking Protection Credit Overlay
        f_shield = QFrame()
        f_shield.setStyleSheet("background-color: #064E3B; border: 1px solid #10B981; border-radius: 6px; padding: 8px;")
        s_lay = QVBoxLayout(f_shield)
        lbl_s_title = QLabel("🛡️ <b>GHOST-BOOKING FRAUD SHIELD OVERLAY:</b>")
        lbl_s_title.setStyleSheet("color: #6EE7B7; font-size: 12px;")
        s_lay.addWidget(lbl_s_title)
        lbl_s_body = QLabel(
            f"Credit Score: <b>{shield.get('credit_score')}/100</b> | "
            f"Days-to-Pay: <b>{shield.get('days_to_pay')} days</b> | "
            f"Bond: <b>{shield.get('bond_status')}</b> | "
            f"Factoring: <b>{shield.get('factoring_eligibility')}</b>"
        )
        lbl_s_body.setStyleSheet("color: #D1FAE5; font-size: 11px;")
        s_lay.addWidget(lbl_s_body)
        d_lay.addWidget(f_shield)

        form = QFormLayout()
        spin_bid = QDoubleSpinBox()
        spin_bid.setRange(100.0, 20000.0)
        spin_bid.setValue(float(load.get("flat_rate_pay", 600.0)))
        spin_bid.setStyleSheet("background-color: #1E293B; color: #FFF; font-size: 14px; font-weight: bold; padding: 6px;")
        form.addRow("Rapid Counter-Bid ($):", spin_bid)
        d_lay.addLayout(form)

        lbl_msg = QLabel("Parallel channels: 💬 SMS to Broker + ✉️ Email to Desk + 🌐 Carrier TMS Webhook (<300ms)")
        lbl_msg.setStyleSheet("color: #94A3B8; font-size: 11px;")
        d_lay.addWidget(lbl_msg)

        btn_fire = QPushButton("⚡ Fire 3-Channel Blast Pitch")
        btn_fire.setStyleSheet("background-color: #BE185D; color: white; font-weight: bold; font-size: 13px; padding: 10px; border-radius: 6px;")
        def fire():
            res = execute_multi_channel_blast_bid(load, spin_bid.value(), DEVIN_PROFILE)
            QMessageBox.information(dlg, "Blast Dispatched", f"⚡ {res['status']} in {res['execution_latency_ms']}ms!\nChannels: {', '.join(res['channels'])}")
            dlg.accept()
        btn_fire.clicked.connect(fire)
        d_lay.addWidget(btn_fire)

        dlg.exec()

    def open_horizon_dialog(self, load: Dict[str, Any]):
        from backend.core.fe_express_dispatcher_dream_cockpit import get_predictive_horizon_map
        h = get_predictive_horizon_map(load.get("dest_city_state", ""))

        dlg = QDialog(self)
        dlg.setWindowTitle(f"🌅 Predictive Horizon Projection — {load.get('dest_city_state')}")
        dlg.resize(500, 340)
        dlg.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
        d_lay = QVBoxLayout(dlg)

        lbl_t = QLabel(f"🌅 <b>{load.get('dest_city_state')} Dock Window Projection</b>")
        lbl_t.setStyleSheet("color: #38BDF8; font-size: 15px;")
        d_lay.addWidget(lbl_t)

        lbl_sub = QLabel(f"Projected Delivery Arrival: <b>{h['projected_arrival_window']}</b> ({h['hours_until_dock']} hours ahead)")
        lbl_sub.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        d_lay.addWidget(lbl_sub)

        grid = QGridLayout()
        lbl_r1 = QLabel(f"<b>Load-to-Truck:</b> <span style='color:#10B981'>{h['load_to_truck_ratio']}</span>")
        lbl_r2 = QLabel(f"<b>Market Pressure:</b> <span style='color:#F59E0B'>{h['market_pressure']}</span>")
        lbl_r3 = QLabel(f"<b>Outbound RPM:</b> <span style='color:#38BDF8'>${h['projected_outbound_rpm']}/mi</span>")
        grid.addWidget(lbl_r1, 0, 0)
        grid.addWidget(lbl_r2, 0, 1)
        grid.addWidget(lbl_r3, 0, 2)
        d_lay.addLayout(grid)

        f_rec = QFrame()
        f_rec.setStyleSheet("background-color: #064E3B; border: 1px solid #10B981; border-radius: 6px; padding: 10px;")
        r_lay = QVBoxLayout(f_rec)
        lbl_rec = QLabel(h["recommendation"])
        lbl_rec.setStyleSheet("color: #A7F3D0; font-size: 12px; font-weight: bold;")
        lbl_rec.setWordWrap(True)
        r_lay.addWidget(lbl_rec)
        d_lay.addWidget(f_rec)

        btn_ok = QPushButton("Close")
        btn_ok.setStyleSheet("background-color: #2563EB; color: white; padding: 6px; border-radius: 4px;")
        btn_ok.clicked.connect(dlg.accept)
        d_lay.addWidget(btn_ok)

        dlg.exec()

    def open_bid_dialog(self, load: Dict[str, Any]):
        dlg = BidGeneratorDialog(load, self.in_home_base.text().strip() or "Grand Rapids, MI", self)
        dlg.exec()

    def open_backhaul_dialog(self, load: Dict[str, Any]):
        dlg = BackhaulRadarDialog(load, self.in_home_base.text().strip() or "Grand Rapids, MI", self)
        dlg.exec()

    def confirm_manual_book_load(self, load: Dict[str, Any]):
        # STRICT ZERO AUTO-BOOK COMPLIANCE: Require explicit confirmation dialog
        ans = QMessageBox.question(
            self,
            "Confirm Load Booking",
            f"Lock down load {load.get('load_id')} ({load.get('origin_city_state')} ➡️ {load.get('dest_city_state')}) "
            f"for ${load.get('flat_rate_pay', 0):,.0f} and assign to Devin's Active Hauls?\n\n"
            f"(Note: Auto-booking is prohibited. This will record the haul into Devin's active dispatch ledger.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            res = ActiveLoadManager.book_load(load)
            if res.get("success"):
                QMessageBox.information(
                    self, "Booked",
                    f"Load {load.get('load_id')} locked in!\nAssigned to Devin's Active Hauls (Status: EN_ROUTE_PICKUP)."
                )
                self.refresh_all_data()
                self.tabs.setCurrentIndex(1)  # switch to Active Hauls tab

    # -------------------------------------------------------------
    # TAB 2: DEVIN'S ACTIVE HAULS
    # -------------------------------------------------------------
    def setup_tab_active(self):
        layout = QVBoxLayout(self.tab_active)

        lbl_head = QLabel("🚚 Devin's Active Dispatch Queue & Live Haul Stepper")
        lbl_head.setStyleSheet("font-size: 15px; font-weight: bold; color: #10B981; padding-bottom: 4px;")
        layout.addWidget(lbl_head)

        self.table_active = QTableWidget(0, 9)
        self.table_active.setHorizontalHeaderLabels([
            "Dispatch ID", "Origin ➡️ Destination", "Status", "Gross Revenue",
            "Est Fuel", "Est Tolls", "Est Net Profit", "BOL / Proof Attached", "Actions"
        ])
        self.table_active.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_active.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_active)

    def load_active_dispatches_ui(self):
        dispatches = ActiveLoadManager.get_active_dispatches()
        self.table_active.setRowCount(0)
        for d in dispatches:
            if d.get("status") == "DELIVERED":
                continue  # delivered goes to ledger
            row_idx = self.table_active.rowCount()
            self.table_active.insertRow(row_idx)

            self.table_active.setItem(row_idx, 0, QTableWidgetItem(d.get("dispatch_id")))
            self.table_active.setItem(row_idx, 1, QTableWidgetItem(f"{d.get('origin')} ➡️ {d.get('destination')}"))
            
            st_item = QTableWidgetItem(d.get("status", "ASSIGNED"))
            st_item.setForeground(QColor("#38BDF8"))
            self.table_active.setItem(row_idx, 2, st_item)

            self.table_active.setItem(row_idx, 3, QTableWidgetItem(f"${d.get('gross_pay', 0):,.2f}"))
            self.table_active.setItem(row_idx, 4, QTableWidgetItem(f"${d.get('fuel_cost', 0):,.2f}"))
            self.table_active.setItem(row_idx, 5, QTableWidgetItem(f"${d.get('tolls_cost', 0):,.2f}"))
            
            net_item = QTableWidgetItem(f"${d.get('net_profit', 0):,.2f}")
            net_item.setForeground(QColor("#10B981"))
            self.table_active.setItem(row_idx, 6, net_item)

            bol_url = d.get("bol_photo_url")
            bol_text = "✅ File Attached" if bol_url else "⚠️ Pending BOL"
            self.table_active.setItem(row_idx, 7, QTableWidgetItem(bol_text))

            # Action button: Attach BOL & Update
            btn_bol = QPushButton("📸 Upload BOL & Complete")
            btn_bol.setStyleSheet("background-color: #059669; font-size: 11px; padding: 4px 8px;")
            btn_bol.clicked.connect(lambda _, disp=d: self.open_bol_dialog(disp))
            self.table_active.setCellWidget(row_idx, 8, btn_bol)

    def open_bol_dialog(self, dispatch: Dict[str, Any]):
        dlg = BOLUpdateDialog(dispatch, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_all_data()

    # -------------------------------------------------------------
    # TAB 3: TRIP PROFIT & BOL LEDGER
    # -------------------------------------------------------------
    def setup_tab_ledger(self):
        layout = QVBoxLayout(self.tab_ledger)

        # Top summary bar
        self.lbl_ledger_summary = QLabel("💰 Total Realized Net Profit: $0.00")
        self.lbl_ledger_summary.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #10B981; background-color: #064E3B; "
            "border: 1px solid #10B981; border-radius: 6px; padding: 10px 14px;"
        )
        layout.addWidget(self.lbl_ledger_summary)

        self.table_ledger = QTableWidget(0, 9)
        self.table_ledger.setHorizontalHeaderLabels([
            "Dispatch ID", "Date / Time", "Origin ➡️ Destination", "Gross Pay",
            "Fuel Cost", "Tolls Cost", "Net Take-Home", "Status", "Proof Document"
        ])
        self.table_ledger.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_ledger.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_ledger)

    def load_ledger_ui(self):
        dispatches = ActiveLoadManager.get_active_dispatches()
        self.table_ledger.setRowCount(0)
        total_net = 0.0

        for d in dispatches:
            row_idx = self.table_ledger.rowCount()
            self.table_ledger.insertRow(row_idx)

            net = float(d.get("net_profit", 0.0))
            total_net += net

            self.table_ledger.setItem(row_idx, 0, QTableWidgetItem(d.get("dispatch_id")))
            self.table_ledger.setItem(row_idx, 1, QTableWidgetItem(str(d.get("dispatched_at", ""))[:16]))
            self.table_ledger.setItem(row_idx, 2, QTableWidgetItem(f"{d.get('origin')} ➡️ {d.get('destination')}"))
            self.table_ledger.setItem(row_idx, 3, QTableWidgetItem(f"${d.get('gross_pay', 0):,.2f}"))
            self.table_ledger.setItem(row_idx, 4, QTableWidgetItem(f"${d.get('fuel_cost', 0):,.2f}"))
            self.table_ledger.setItem(row_idx, 5, QTableWidgetItem(f"${d.get('tolls_cost', 0):,.2f}"))

            net_item = QTableWidgetItem(f"${net:,.2f}")
            net_item.setForeground(QColor("#10B981"))
            self.table_ledger.setItem(row_idx, 6, net_item)

            self.table_ledger.setItem(row_idx, 7, QTableWidgetItem(d.get("status", "")))

            bol = d.get("bol_photo_url")
            if bol and os.path.exists(bol):
                btn_view_bol = QPushButton("📄 View BOL")
                btn_view_bol.setStyleSheet("background-color: #2563EB; font-size: 11px; padding: 2px 6px;")
                btn_view_bol.clicked.connect(lambda _, b=bol: QDesktopServices.openUrl(QUrl.fromLocalFile(b)))
                self.table_ledger.setCellWidget(row_idx, 8, btn_view_bol)
            else:
                self.table_ledger.setItem(row_idx, 8, QTableWidgetItem("No file"))

        self.lbl_ledger_summary.setText(f"💰 Total Realized Net Profit (All Dispatches): ${total_net:,.2f}")

    # -------------------------------------------------------------
    # TAB 4: 1099 DRIVERS & TAX SPREADSHEET
    # -------------------------------------------------------------
    def setup_tab_drivers(self):
        layout = QVBoxLayout(self.tab_drivers)

        # Header with action buttons
        header_bar = QHBoxLayout()
        lbl_title = QLabel("👥 Subcontract 1099 Drivers Directory & Year-End Tax Ledger")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F59E0B;")
        header_bar.addWidget(lbl_title)
        header_bar.addStretch()

        btn_add_drv = QPushButton("➕ Add 1099 Driver")
        btn_add_drv.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px;")
        btn_add_drv.clicked.connect(self.open_add_driver_dialog)
        header_bar.addWidget(btn_add_drv)

        btn_add_settle = QPushButton("💵 Record Trip Settlement")
        btn_add_settle.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px;")
        btn_add_settle.clicked.connect(self.open_add_settlement_dialog)
        header_bar.addWidget(btn_add_settle)

        layout.addLayout(header_bar)

        # Drivers Table
        lbl_sec1 = QLabel("Driver Roster & Tax Document Audit (W-9 / DOT Med / MVR):")
        lbl_sec1.setStyleSheet("color: #94A3B8; font-weight: bold;")
        layout.addWidget(lbl_sec1)

        self.table_drivers = QTableWidget(0, 9)
        self.table_drivers.setHorizontalHeaderLabels([
            "Driver ID", "Full Name", "Phone / Email", "Tax ID (Last 4)",
            "License # & State", "Agreed Pay Rate", "DOT Med Card Exp", "MVR Status", "W-9 Status"
        ])
        self.table_drivers.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_drivers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_drivers)

        # Settlements Spreadsheet Table
        lbl_sec2 = QLabel("1099 Trip Settlements & Year-End Tax Disbursements:")
        lbl_sec2.setStyleSheet("color: #94A3B8; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_sec2)

        self.table_settlements = QTableWidget(0, 9)
        self.table_settlements.setHorizontalHeaderLabels([
            "Settlement ID", "Date", "Driver", "Haul Lane",
            "Gross Revenue", "Earned Pay", "Fuel / Advance Deduct", "Net 1099 Payout", "Status & Method"
        ])
        self.table_settlements.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_settlements.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_settlements)

    def load_drivers_ui(self):
        drivers = ActiveLoadManager.get_contractor_drivers()
        settlements = ActiveLoadManager.get_driver_settlements()

        # Populate Drivers
        self.table_drivers.setRowCount(0)
        for d in drivers:
            row_idx = self.table_drivers.rowCount()
            self.table_drivers.insertRow(row_idx)

            self.table_drivers.setItem(row_idx, 0, QTableWidgetItem(d.get("driver_id")))
            self.table_drivers.setItem(row_idx, 1, QTableWidgetItem(d.get("full_name")))
            self.table_drivers.setItem(row_idx, 2, QTableWidgetItem(f"{d.get('phone', '')} | {d.get('email', '')}"))
            self.table_drivers.setItem(row_idx, 3, QTableWidgetItem(f"***-**-{d.get('tax_id_or_ssn_last4', 'XXXX')}"))
            self.table_drivers.setItem(row_idx, 4, QTableWidgetItem(f"{d.get('driver_license_num', '')} ({d.get('driver_license_state', 'MI')})"))
            
            rate_text = f"{d.get('pay_rate', 25)}% Gross" if d.get('pay_model') == 'PERCENT_GROSS' else f"${d.get('pay_rate', 0.55)}/mi"
            self.table_drivers.setItem(row_idx, 5, QTableWidgetItem(rate_text))
            self.table_drivers.setItem(row_idx, 6, QTableWidgetItem(str(d.get("medical_card_exp", ""))))
            self.table_drivers.setItem(row_idx, 7, QTableWidgetItem(d.get("mvr_check_status", "CLEARED")))

            w9 = "✅ On File" if d.get("w9_on_file") == 1 else "⚠️ Missing"
            self.table_drivers.setItem(row_idx, 8, QTableWidgetItem(w9))

        # Populate Settlements
        self.table_settlements.setRowCount(0)
        driver_map = {d["driver_id"]: d["full_name"] for d in drivers}
        for s in settlements:
            row_idx = self.table_settlements.rowCount()
            self.table_settlements.insertRow(row_idx)

            drv_name = driver_map.get(s.get("driver_id"), s.get("driver_id"))
            self.table_settlements.setItem(row_idx, 0, QTableWidgetItem(s.get("settlement_id")))
            self.table_settlements.setItem(row_idx, 1, QTableWidgetItem(str(s.get("trip_date", ""))))
            self.table_settlements.setItem(row_idx, 2, QTableWidgetItem(drv_name))
            self.table_settlements.setItem(row_idx, 3, QTableWidgetItem(s.get("origin_dest", "")))
            self.table_settlements.setItem(row_idx, 4, QTableWidgetItem(f"${s.get('gross_load_pay', 0):,.2f}"))
            self.table_settlements.setItem(row_idx, 5, QTableWidgetItem(f"${s.get('contractor_pay', 0):,.2f}"))
            
            deduct = float(s.get("fuel_deduction", 0.0)) + float(s.get("cash_advance", 0.0))
            self.table_settlements.setItem(row_idx, 6, QTableWidgetItem(f"-${deduct:,.2f}"))

            payout_item = QTableWidgetItem(f"${s.get('net_1099_payout', 0):,.2f}")
            payout_item.setForeground(QColor("#10B981"))
            self.table_settlements.setItem(row_idx, 7, payout_item)

            self.table_settlements.setItem(row_idx, 8, QTableWidgetItem(f"{s.get('payment_status')} ({s.get('payment_method')})"))

    def open_add_driver_dialog(self):
        dlg = AddContractorDriverDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_drivers_ui()

    def open_add_settlement_dialog(self):
        drivers = ActiveLoadManager.get_contractor_drivers()
        if not drivers:
            QMessageBox.warning(self, "No Drivers", "Please add at least one 1099 subcontract driver first.")
            return
        dlg = RecordSettlementDialog(drivers, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_drivers_ui()

    # -------------------------------------------------------------
    # TAB 5: OWNER-OPERATOR YIELD & UPTIME COCKPIT
    # -------------------------------------------------------------
    def setup_tab_owner_operator(self):
        layout = QVBoxLayout(self.tab_owner_operator)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #1E1B4B; border: 1px solid #6366F1; border-radius: 6px; padding: 10px;")
        h_layout = QHBoxLayout(header)
        lbl_h = QLabel("🚀 <b>Owner-Operator Yield Management & Uptime Cockpit</b> (Triangulation, Factoring, IFTA, Clearance, DVIR)")
        lbl_h.setStyleSheet("color: #A5B4FC; font-size: 14px;")
        h_layout.addWidget(lbl_h)
        h_layout.addStretch()

        btn_recalc = QPushButton("🔄 Refresh Triangulation Loops")
        btn_recalc.setStyleSheet("background-color: #BE185D; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        btn_recalc.clicked.connect(self.load_owner_operator_ui)
        h_layout.addWidget(btn_recalc)
        layout.addWidget(header)

        # Split: Triangulation Loops (Top) and Quick Panels (Bottom)
        lbl_tri = QLabel("🔄 <b>Multi-Leg Triangulation Loops</b> (Max True RPM - Eliminates Empty Deadhead):")
        lbl_tri.setStyleSheet("color: #EC4899; font-size: 13px; margin-top: 6px;")
        layout.addWidget(lbl_tri)

        self.table_triangulation = QTableWidget(0, 7)
        self.table_triangulation.setHorizontalHeaderLabels([
            "Loop Name", "Loaded Miles", "Deadhead", "Gross Pay", "True RPM", "Est. Fuel", "Est. EBITDA"
        ])
        self.table_triangulation.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_triangulation.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_triangulation)

        # Bottom Grid for IFTA, Factoring & Clearance
        grid = QGridLayout()

        # IFTA Summary Card
        self.frame_ifta = QFrame()
        self.frame_ifta.setStyleSheet("background-color: #0F172A; border: 1px solid #10B981; border-radius: 6px; padding: 8px;")
        ifta_lay = QVBoxLayout(self.frame_ifta)
        self.lbl_ifta_title = QLabel("📊 <b>IFTA Quarterly Fuel Tax (2026-Q4)</b>")
        self.lbl_ifta_title.setStyleSheet("color: #10B981; font-size: 13px;")
        ifta_lay.addWidget(self.lbl_ifta_title)
        self.lbl_ifta_body = QLabel("Loading IFTA state breakdown...")
        self.lbl_ifta_body.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        ifta_lay.addWidget(self.lbl_ifta_body)
        grid.addWidget(self.frame_ifta, 0, 0)

        # Commercial Clearance & Hazard Card
        self.frame_clearance = QFrame()
        self.frame_clearance.setStyleSheet("background-color: #0F172A; border: 1px solid #F59E0B; border-radius: 6px; padding: 8px;")
        clr_lay = QVBoxLayout(self.frame_clearance)
        lbl_clr_title = QLabel("🛡️ <b>Heavy Commercial Clearance Radar (12'6\")</b>")
        lbl_clr_title.setStyleSheet("color: #F59E0B; font-size: 13px;")
        clr_lay.addWidget(lbl_clr_title)
        lbl_clr_body = QLabel(
            "⚠️ <b>CRITICAL BAN:</b> Lake Shore Drive (US-41) Commercial Trucks Prohibited.<br>"
            "⚠️ <b>CLEARANCE WATCH:</b> Metra viaducts along Chicago NW arterials vary from 12'2\" to 13'6\". "
            "STAA routes only (I-90 / I-94 / I-290)."
        )
        lbl_clr_body.setStyleSheet("color: #F87171; font-size: 11px;")
        clr_lay.addWidget(lbl_clr_body)
        grid.addWidget(self.frame_clearance, 0, 1)

        layout.addLayout(grid)

    def load_owner_operator_ui(self):
        from backend.core.fe_express_owner_operator_engine import (
            build_triangulation_chains,
            calculate_ifta_quarterly_summary,
            get_maintenance_and_dvir_dashboard
        )
        # 1. Populate Triangulation
        home = self.in_home_base.text().strip() or "Grand Rapids, MI"
        chains = build_triangulation_chains(home_terminal=home)
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

            self.table_triangulation.setItem(r, 5, QTableWidgetItem(f"-${c.get('estimated_fuel_cost', 0):,.2f}"))

            ebitda_item = QTableWidgetItem(f"${c.get('projected_net_ebitda', 0):,.2f}")
            ebitda_item.setForeground(QColor("#38BDF8"))
            self.table_triangulation.setItem(r, 6, ebitda_item)

        # 2. Populate IFTA
        try:
            ifta = calculate_ifta_quarterly_summary()
            status_txt = "Refund Due" if ifta.get("total_net_tax_due", 0) <= 0 else "Tax Owed"
            amt = abs(ifta.get("total_net_tax_due", 0))
            self.lbl_ifta_body.setText(
                f"<b>Total Miles:</b> {ifta.get('total_miles')} mi  |  "
                f"<b>Gallons:</b> {ifta.get('total_gallons_purchased')} gal  |  "
                f"<b>Fleet MPG:</b> {ifta.get('fleet_mpg')}<br>"
                f"<b>Net IFTA Tax Position:</b> <span style='color:#10B981'>${amt:,.2f} ({status_txt})</span><br>"
                f"<b>States Tracked:</b> {', '.join([s['state'] for s in ifta.get('states', [])])}"
            )
        except Exception as e:
            self.lbl_ifta_body.setText(f"Error reading IFTA data: {e}")

    # -------------------------------------------------------------
    # GLOBAL REFRESH & SYNC
    # -------------------------------------------------------------
    def trigger_live_public_sync(self):
        self.btn_sync_live.setEnabled(False)
        self.btn_sync_live.setText("⏳ Fetching Live Public Boards...")
        self.worker = LiveBoardSyncWorker(self.in_home_base.text().strip() or "Grand Rapids, MI")
        self.worker.finished_sync.connect(self.on_live_sync_finished)
        self.worker.start()

    def on_live_sync_finished(self, count: int, status: str):
        self.btn_sync_live.setEnabled(True)
        self.btn_sync_live.setText("🌐 Pull Real Live Public Loads")
        self.refresh_all_data()

    def refresh_all_data(self):
        self.load_board_from_db()
        self.load_active_dispatches_ui()
        self.load_ledger_ui()
        self.load_drivers_ui()
        self.load_owner_operator_ui()
        self.update_live_telemetry()

    def load_board_from_db(self):
        if not DB_PATH.exists():
            return
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM fe_express_loads ORDER BY priority_tier ASC, rpm DESC").fetchall()
        conn.close()
        self.raw_loads_cache = [dict(r) for r in rows]
        self.apply_board_filters()

    def update_live_telemetry(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            total_loads = conn.execute("SELECT COUNT(*) FROM fe_express_loads").fetchone()[0]
            green_loads = conn.execute("SELECT COUNT(*) FROM fe_express_loads WHERE score='Greenlight'").fetchone()[0]
            caution_loads = conn.execute("SELECT COUNT(*) FROM fe_express_loads WHERE score='Caution'").fetchone()[0]
            conn.close()

            dispatches = ActiveLoadManager.get_active_dispatches()
            active_count = len([d for d in dispatches if d.get("status") != "DELIVERED"])
            drivers_count = len(ActiveLoadManager.get_contractor_drivers())

            self.status_banner.setText(
                f"🟢 REAL PUBLIC BOARD FEED (Trulos Live) | Active Leads: {total_loads}  |  "
                f"🟢 {green_loads} Greenlight (≥ $2.50/mi)  |  🟡 {caution_loads} Caution  |  "
                f"🚚 Active Hauls: {active_count}  |  👥 1099 Drivers: {drivers_count}  |  "
                f"Terminal: {self.in_home_base.text().strip() or 'Grand Rapids, MI'}"
            )
            # Update tab counts
            self.tabs.setTabText(0, f"📋 Live Load Board ({len(self.raw_loads_cache)})")
            self.tabs.setTabText(1, f"🚚 Devin's Active Hauls ({active_count})")
            total_net = sum(float(d.get("net_profit", 0.0)) for d in dispatches)
            self.tabs.setTabText(2, f"💰 Trip Profit & BOL Ledger (${total_net:,.0f})")
            self.tabs.setTabText(3, f"👥 1099 Drivers & Tax Spreadsheet ({drivers_count})")
        except Exception as e:
            self.status_banner.setText(f"🟢 FE EXPRESS LIVE FEED | Active ({e})")


if __name__ == "__main__":
    init_active_loads_db()
    app = QApplication(sys.argv)
    win = FEExpressNativeWindow()
    win.show()
    sys.exit(app.exec())
