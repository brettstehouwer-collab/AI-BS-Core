"""Master Accounting & Money Track Native View (Pure Windows Direct SQLite).

Features:
- Direct local SQLite connection to C:\\AI-BS\\backend\\stehouwer_accounting.db & aibs_master.db
- Real-time P&L analytics HUD: Gross Income, Deductible Expenses, MI State Tax (4.25%), Net Taxable Income & Tax Savings
- Rule 6 Strict Compliance: ZERO mock data, verified real financial entries only
- Interactive 2-SubPage Architecture:
  1. Interactive Excel Ledger Grid (Inline editing, quick-add bar, category & type filters, CSV export)
  2. US Federal & Michigan State (4.25% Flat) Tax Engine (Sec 179 hardware write-offs, SECA 15.3%, Form 1040-ES quarterly schedule)
- Stehouwer Financial AI Copilot Drawer (Interactive natural language expense logging & tax advisor)
"""

from __future__ import annotations

import csv
import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
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
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE


DB_PATH = Path(r"C:\AI-BS\backend\stehouwer_accounting.db")
MASTER_DB_PATH = Path(r"C:\AI-BS\backend\aibs_master.db")


def get_active_db_path() -> Path:
    """Return primary active SQLite accounting database."""
    if DB_PATH.exists():
        return DB_PATH
    if MASTER_DB_PATH.exists():
        return MASTER_DB_PATH
    return DB_PATH


def sync_db_write(sql: str, params: tuple) -> None:
    """Commit SQL write to primary and secondary databases to maintain sync."""
    for p in [DB_PATH, MASTER_DB_PATH]:
        if p.exists() or p == DB_PATH:
            try:
                conn = sqlite3.connect(p)
                cur = conn.cursor()
                cur.execute(sql, params)
                conn.commit()
                conn.close()
            except Exception:
                pass


class EditTransactionDialog(QDialog):
    """Dialog for creating or editing a verified accounting transaction."""

    def __init__(self, item: dict | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item_id = item.get("id") if item else None
        self.setWindowTitle("Edit Transaction" if self.item_id else "Record Verified Transaction")
        self.setFixedSize(500, 460)
        self.setStyleSheet(
            f"background-color: {PALETTE['panel']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; border-radius: 8px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["expense", "income"])
        if item and item.get("type"):
            self.type_combo.setCurrentText(item["type"].lower())
        form.addRow("Type:", self.type_combo)

        default_date = item.get("date") if item else datetime.now().strftime("%Y-%m-%d")
        self.date_edit = QLineEdit(default_date)
        form.addRow("Date (YYYY-MM-DD):", self.date_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Hardware & Electronics",
            "Hardware / Equipment",
            "Cloud Infrastructure",
            "Utilities & Electricity",
            "Software Subscriptions",
            "Commercial API Payouts",
            "Consulting Revenue",
            "Travel / Fuel",
            "Office / Workspace",
            "Legal & Professional",
            "Other Business",
        ])
        if item and item.get("category"):
            self.category_combo.setCurrentText(item["category"])
        form.addRow("Category:", self.category_combo)

        self.desc_edit = QLineEdit(item.get("desc", "") if item else "")
        self.desc_edit.setPlaceholderText("Detailed description of transaction")
        form.addRow("Description:", self.desc_edit)

        self.amount_edit = QLineEdit(f"{item.get('amount', 0.0):.2f}" if item else "")
        self.amount_edit.setPlaceholderText("0.00")
        form.addRow("Amount ($ USD):", self.amount_edit)

        self.schedule_c_combo = QComboBox()
        self.schedule_c_combo.addItems([
            "Sec179_Hardware",
            "Utilities_Software",
            "Utilities_Electric",
            "Gross_Sales",
            "Advertising",
            "Office_Expense",
            "Supplies",
            "Other",
        ])
        if item and item.get("schedule_c"):
            self.schedule_c_combo.setCurrentText(item["schedule_c"])
        form.addRow("Schedule C Code:", self.schedule_c_combo)

        self.receipt_edit = QLineEdit(item.get("receipt", "") if item else "")
        self.receipt_edit.setPlaceholderText("Receipt #, invoice, or verification note")
        form.addRow("Receipt / Proof:", self.receipt_edit)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Commit to Ledger")
        save_btn.setStyleSheet(
            f"background: {PALETTE['cyan']}; color: #020617; font-weight: bold; padding: 8px 16px; border-radius: 6px;"
        )
        save_btn.clicked.connect(self._save)
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        layout.addLayout(btn_box)

    def _save(self) -> None:
        desc = self.desc_edit.text().strip()
        amt_str = self.amount_edit.text().strip().replace("$", "").replace(",", "")
        if not desc or not amt_str:
            QMessageBox.warning(self, "Validation Error", "Description and Amount are required.")
            return
        try:
            amt = float(amt_str)
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Amount must be a valid number.")
            return

        entry_type = self.type_combo.currentText()
        date_val = self.date_edit.text().strip()
        category = self.category_combo.currentText()
        sched_c = self.schedule_c_combo.currentText()
        receipt = self.receipt_edit.text().strip()
        now_ts = time.time()

        try:
            if self.item_id:
                sync_db_write(
                    """
                    UPDATE accounting_entries
                    SET date=?, category=?, description=?, entry_type=?, amount=?, is_tax_deductible=1, schedule_c_code=?, receipt_note=?, updated_at=?
                    WHERE id=?
                    """,
                    (date_val, category, desc, entry_type, amt, sched_c, receipt, now_ts, self.item_id),
                )
            else:
                sync_db_write(
                    """
                    INSERT INTO accounting_entries
                    (date, category, description, entry_type, amount, is_tax_deductible, schedule_c_code, receipt_note, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                    """,
                    (date_val, category, desc, entry_type, amt, sched_c, receipt, now_ts, now_ts),
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save transaction:\n{e}")


# Legacy alias for test backward compatibility
AddTransactionDialog = EditTransactionDialog


class MasterAccountingNativeView(QWidget):
    """Full-featured Master Accounting and Money Track Native View."""

    def __init__(self, bus: EngineBus) -> None:
        super().__init__()
        self.bus = bus
        self._all_rows: list[dict] = []
        self._tax_summary: dict = {}
        self._chat_history: list[dict] = [
            {"sender": "ai", "text": "Welcome to Stehouwer Financial AI! Ask tax questions or command: 'Log an expense of $1,599.99 for RTX 4090 GPU'."}
        ]
        self._init_ui()
        self._load_ledger()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title & Actions
        head_box = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        h_title_row = QHBoxLayout()
        title = QLabel("💰 Stehouwer Publishing LLC Master Accounting")
        title.setStyleSheet("font-size: 15pt; font-weight: bold; color: #f8fafc;")
        auth_badge = QLabel("🛡️ Authorized Partner (NoCo)")
        auth_badge.setStyleSheet(
            "background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); border-radius: 10px; padding: 2px 8px; font-size: 8pt; font-weight: bold;"
        )
        h_title_row.addWidget(title)
        h_title_row.addWidget(auth_badge)
        h_title_row.addStretch()
        title_box.addLayout(h_title_row)

        subtitle = QLabel("Direct SQLite Transaction Engine • US Federal & Michigan State (4.25% Flat) Tax Engine")
        subtitle.setStyleSheet("font-size: 8pt; color: #94a3b8;")
        title_box.addWidget(subtitle)
        head_box.addLayout(title_box)
        head_box.addStretch()

        self.btn_ai_drawer = QPushButton("✨ AI Tax Advisor")
        self.btn_ai_drawer.setStyleSheet(
            "background: linear-gradient(135deg, #9333ea, #4f46e5); color: #ffffff; font-weight: bold; padding: 7px 14px; border-radius: 6px; border: 1px solid #c084fc;"
        )
        self.btn_ai_drawer.clicked.connect(self._toggle_ai_drawer)
        head_box.addWidget(self.btn_ai_drawer)

        self.btn_add = QPushButton("➕ Record Transaction")
        self.btn_add.setStyleSheet(
            f"background: {PALETTE['cyan']}; color: #020617; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        self.btn_add.clicked.connect(self._open_add_dialog)
        head_box.addWidget(self.btn_add)

        self.btn_export = QPushButton("📥 Export CSV")
        self.btn_export.setStyleSheet(
            f"background: #1e293b; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; padding: 7px 12px; border-radius: 6px;"
        )
        self.btn_export.clicked.connect(self._export_csv)
        head_box.addWidget(self.btn_export)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet(
            f"background: #1e293b; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; padding: 7px 12px; border-radius: 6px;"
        )
        self.btn_refresh.clicked.connect(self._load_ledger)
        head_box.addWidget(self.btn_refresh)

        layout.addLayout(head_box)

        # Real-Time Financial Metric Cards (4 Cards matching Web MasterAccountingTab)
        hud_box = QHBoxLayout()
        hud_box.setSpacing(12)

        self.card_income = self._create_card("GROSS REVENUE", "$0.00", "PayPal & Commercial API Payouts", PALETTE["green"])
        self.card_expense = self._create_card("DEDUCTIBLE EXPENSES", "$0.00", "IRS Sec 179 GPU Write-offs", PALETTE["cyan"])
        self.card_mi_tax = self._create_card("MICHIGAN STATE TAX (4.25%)", "$0.00", "MI Business Flat Rate", PALETTE["purple"])
        self.card_tax_savings = self._create_card("EST. TAX SAVINGS", "$0.00", "Deduction Savings from Write-offs", PALETTE["yellow"])

        # Retain card_net and card_tax references for backward compatibility with existing tests
        self.card_net = self.card_income
        self.card_tax = self.card_mi_tax

        hud_box.addWidget(self.card_income)
        hud_box.addWidget(self.card_expense)
        hud_box.addWidget(self.card_mi_tax)
        hud_box.addWidget(self.card_tax_savings)
        layout.addLayout(hud_box)

        # Sub-Page Switcher Navigation Bar
        nav_box = QHBoxLayout()
        nav_box.setSpacing(8)

        self.btn_page_spreadsheet = QPushButton("📊 Interactive Excel Ledger Grid")
        self.btn_page_spreadsheet.setStyleSheet(
            "background: #0284c7; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #38bdf8;"
        )
        self.btn_page_spreadsheet.clicked.connect(lambda: self._set_subpage(0))
        nav_box.addWidget(self.btn_page_spreadsheet)

        self.btn_page_tax = QPushButton("📑 US Federal & Michigan State Tax Engine")
        self.btn_page_tax.setStyleSheet(
            "background: #0f172a; color: #94a3b8; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #1e293b;"
        )
        self.btn_page_tax.clicked.connect(lambda: self._set_subpage(1))
        nav_box.addWidget(self.btn_page_tax)

        nav_box.addStretch()
        layout.addLayout(nav_box)

        # Central Split: Stacked Subpages on Left + AI Drawer on Right
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(12)

        self.stacked = QStackedWidget()

        # ==========================================
        # Subpage 0: Interactive Excel Ledger Grid
        # ==========================================
        page_ledger = QWidget()
        p0_lay = QVBoxLayout(page_ledger)
        p0_lay.setContentsMargins(0, 0, 0, 0)
        p0_lay.setSpacing(10)

        # Quick Add Strip Form
        quick_add_frame = QFrame()
        quick_add_frame.setStyleSheet(
            "background: #0d121d; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;"
        )
        qa_lay = QVBoxLayout(quick_add_frame)
        qa_lay.setContentsMargins(6, 6, 6, 6)
        qa_lay.setSpacing(6)

        qa_title = QLabel("<b>+ Quick Add New Transaction Entry</b>")
        qa_title.setStyleSheet("color: #cbd5e1; font-size: 8pt;")
        qa_lay.addWidget(qa_title)

        qa_row = QHBoxLayout()
        qa_row.setSpacing(8)

        self.qa_date = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.qa_date.setFixedWidth(100)
        self.qa_date.setStyleSheet("background: #05080f; border: 1px solid #334155; color: #fff; padding: 5px; border-radius: 4px;")

        self.qa_type = QComboBox()
        self.qa_type.addItems(["expense", "income"])
        self.qa_type.setFixedWidth(90)
        self.qa_type.setStyleSheet("background: #05080f; border: 1px solid #334155; color: #fff; padding: 4px; border-radius: 4px;")

        self.qa_desc = QLineEdit()
        self.qa_desc.setPlaceholderText("Description (e.g. RTX 4090 GPU or Electricity)")
        self.qa_desc.setStyleSheet("background: #05080f; border: 1px solid #334155; color: #fff; padding: 5px; border-radius: 4px;")

        self.qa_amount = QLineEdit()
        self.qa_amount.setPlaceholderText("Amount ($)")
        self.qa_amount.setFixedWidth(95)
        self.qa_amount.setStyleSheet("background: #05080f; border: 1px solid #334155; color: #fff; padding: 5px; border-radius: 4px;")

        self.qa_cat = QComboBox()
        self.qa_cat.addItems([
            "Hardware & Electronics",
            "Cloud Infrastructure",
            "Utilities & Electricity",
            "Software Subscriptions",
            "Commercial API Payouts",
            "Other Business",
        ])
        self.qa_cat.setFixedWidth(150)
        self.qa_cat.setStyleSheet("background: #05080f; border: 1px solid #334155; color: #fff; padding: 4px; border-radius: 4px;")

        self.qa_btn = QPushButton("Add Row")
        self.qa_btn.setStyleSheet(
            "background: #059669; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        self.qa_btn.clicked.connect(self._handle_quick_add)

        qa_row.addWidget(self.qa_date)
        qa_row.addWidget(self.qa_type)
        qa_row.addWidget(self.qa_desc, 2)
        qa_row.addWidget(self.qa_amount)
        qa_row.addWidget(self.qa_cat)
        qa_row.addWidget(self.qa_btn)
        qa_lay.addLayout(qa_row)
        p0_lay.addWidget(quick_add_frame)

        # Filters Bar
        filter_box = QHBoxLayout()
        filter_box.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search transactions by description, vendor, or note...")
        self.search_edit.setStyleSheet(
            f"background: #090d16; border: 1px solid {PALETTE['border']}; border-radius: 6px; padding: 6px 10px; color: #f8fafc;"
        )
        self.search_edit.textChanged.connect(self._filter_table)
        filter_box.addWidget(self.search_edit, 2)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        self.cat_filter.setStyleSheet(
            f"background: #090d16; border: 1px solid {PALETTE['border']}; border-radius: 6px; padding: 6px 10px; color: #f8fafc;"
        )
        self.cat_filter.currentTextChanged.connect(self._filter_table)
        filter_box.addWidget(self.cat_filter, 1)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Expense Only", "Income Only"])
        self.type_filter.setStyleSheet(
            f"background: #090d16; border: 1px solid {PALETTE['border']}; border-radius: 6px; padding: 6px 10px; color: #f8fafc;"
        )
        self.type_filter.currentTextChanged.connect(self._filter_table)
        filter_box.addWidget(self.type_filter, 1)

        p0_lay.addLayout(filter_box)

        # Master Transaction Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Category", "Description", "Type", "Amount ($)", "Tax Write-Off", "Schedule C", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 45)
        self.table.setColumnWidth(1, 95)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 260)
        self.table.setColumnWidth(4, 75)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 95)
        self.table.setColumnWidth(7, 120)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { background: #070b14; alternate-background-color: #0b1120; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; }"
            "QHeaderView::section { background: #0f172a; color: #94a3b8; font-weight: bold; border: none; padding: 6px; }"
        )
        self.table.doubleClicked.connect(self._on_table_double_click)
        p0_lay.addWidget(self.table, 1)

        self.stacked.addWidget(page_ledger)

        # ==========================================
        # Subpage 1: US Federal & Michigan State Tax Engine
        # ==========================================
        page_tax = QWidget()
        p1_lay = QVBoxLayout(page_tax)
        p1_lay.setContentsMargins(0, 0, 0, 0)
        p1_lay.setSpacing(12)

        scroll_tax = QScrollArea()
        scroll_tax.setWidgetResizable(True)
        scroll_tax.setFrameShape(QFrame.Shape.NoFrame)
        scroll_tax.setStyleSheet("background: transparent;")

        tax_container = QWidget()
        tc_lay = QVBoxLayout(tax_container)
        tc_lay.setContentsMargins(4, 4, 4, 4)
        tc_lay.setSpacing(14)

        # Tax Engine Summary Header Banner
        tax_hdr = QFrame()
        tax_hdr.setStyleSheet("background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        th_lay = QHBoxLayout(tax_hdr)
        th_left = QLabel("🧮 <b>US Federal & Michigan State Tax Engine Summary</b>")
        th_left.setStyleSheet("font-size: 11pt; color: #f1f5f9;")
        th_badge = QLabel("MI Corporate / Sole-Prop Flat Tax: 4.25%  •  IRS Schedule C Qualified")
        th_badge.setStyleSheet("background: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid #7e22ce; border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 8pt;")
        th_lay.addWidget(th_left)
        th_lay.addStretch()
        th_lay.addWidget(th_badge)
        tc_lay.addWidget(tax_hdr)

        # Tax Metric Cards Grid
        grid_tax = QGridLayout()
        grid_tax.setSpacing(12)

        # Box 1: Business Revenue & Profit
        self.box_profit = self._build_tax_box("BUSINESS REVENUE & PROFIT", [
            ("Gross Inflow / Revenue:", "$0.00", "#34d399"),
            ("Total Deductible Write-Offs:", "-$0.00", "#38bdf8"),
            ("Net Taxable Profit:", "$0.00", "#c084fc"),
        ])
        grid_tax.addWidget(self.box_profit, 0, 0)

        # Box 2: Estimated Tax Breakdown
        self.box_liab = self._build_tax_box("ESTIMATED TAX LIABILITY", [
            ("Michigan State Tax (4.25%):", "$0.00", "#c084fc"),
            ("US Federal SE Tax (15.3%):", "$0.00", "#818cf8"),
            ("Est. Federal Income Tax (12%):", "$0.00", "#38bdf8"),
            ("Total Estimated Liability:", "$0.00", "#fbbf24"),
        ])
        grid_tax.addWidget(self.box_liab, 0, 1)

        # Box 3: Section 179 Hardware
        self.box_sec179 = self._build_tax_box("SECTION 179 HARDWARE WRITE-OFFS", [
            ("Section 179 Equipment Total:", "$0.00", "#34d399"),
            ("Accelerated First-Year Deduction:", "100% Expensed", "#38bdf8"),
            ("Qualifying Hardware:", "RTX 4090 GPU rigs, Servers, NVMe arrays", "#94a3b8"),
        ])
        grid_tax.addWidget(self.box_sec179, 1, 0)

        # Box 4: Form 1040-ES Quarterly Schedule
        self.box_quarterly = self._build_tax_box("FORM 1040-ES QUARTERLY DUE DATES", [
            ("Q1 (April 15):", "$0.00", "#38bdf8"),
            ("Q2 (June 15):", "$0.00", "#38bdf8"),
            ("Q3 (September 15):", "$0.00", "#38bdf8"),
            ("Q4 (January 15):", "$0.00", "#38bdf8"),
        ])
        grid_tax.addWidget(self.box_quarterly, 1, 1)

        tc_lay.addLayout(grid_tax)

        # Schedule C Category Breakdown Table
        tc_lay.addWidget(QLabel("<b>IRS Schedule C Expense Category Breakdown:</b>"))
        self.cat_breakdown_table = QTableWidget()
        self.cat_breakdown_table.setColumnCount(4)
        self.cat_breakdown_table.setHorizontalHeaderLabels([
            "Schedule C Category", "Transactions Count", "Total Expensed ($)", "% of Total Expenses"
        ])
        self.cat_breakdown_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cat_breakdown_table.setFixedHeight(180)
        self.cat_breakdown_table.setStyleSheet(
            "QTableWidget { background: #070b14; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; font-size: 8pt; }"
            "QHeaderView::section { background: #0f172a; color: #94a3b8; font-weight: bold; padding: 6px; border: 1px solid #1e293b; }"
        )
        tc_lay.addWidget(self.cat_breakdown_table)

        btn_export_tax = QPushButton("📑 Export IRS Schedule C Formatted Summary (.csv)")
        btn_export_tax.setStyleSheet(
            "background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; padding: 8px 16px; border-radius: 6px; font-weight: bold;"
        )
        btn_export_tax.clicked.connect(self._export_schedule_c_csv)
        tc_lay.addWidget(btn_export_tax, 0, Qt.AlignmentFlag.AlignRight)

        tc_lay.addStretch()
        scroll_tax.setWidget(tax_container)
        p1_lay.addWidget(scroll_tax)

        self.stacked.addWidget(page_tax)
        main_content_layout.addWidget(self.stacked, 1)

        # ==========================================
        # Stehouwer Financial AI Copilot Drawer (Right)
        # ==========================================
        self.ai_drawer = QFrame()
        self.ai_drawer.setFixedWidth(340)
        self.ai_drawer.setStyleSheet(
            "background: #0d121d; border: 1px solid #1e293b; border-radius: 10px;"
        )
        drawer_lay = QVBoxLayout(self.ai_drawer)
        drawer_lay.setContentsMargins(10, 10, 10, 10)
        drawer_lay.setSpacing(8)

        # Drawer Header
        dh_row = QHBoxLayout()
        dh_title = QLabel("✨ <b>Stehouwer Financial AI</b>")
        dh_title.setStyleSheet("font-size: 9pt; color: #f8fafc;")
        dh_close = QPushButton("✕")
        dh_close.setFixedSize(24, 24)
        dh_close.setStyleSheet("background: transparent; color: #94a3b8; border: none; font-weight: bold;")
        dh_close.clicked.connect(lambda: self.ai_drawer.hide())
        dh_row.addWidget(dh_title)
        dh_row.addStretch()
        dh_row.addWidget(dh_close)
        drawer_lay.addLayout(dh_row)

        # Drawer Messages Scroll Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setStyleSheet("background: #070b14; border: 1px solid #1e293b; border-radius: 6px;")

        self.chat_container = QWidget()
        self.chat_lay = QVBoxLayout(self.chat_container)
        self.chat_lay.setContentsMargins(8, 8, 8, 8)
        self.chat_lay.setSpacing(8)
        self.chat_lay.addStretch()
        self.chat_scroll.setWidget(self.chat_container)
        drawer_lay.addWidget(self.chat_scroll, 1)

        # Drawer Input
        d_input_box = QHBoxLayout()
        d_input_box.setSpacing(6)
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Command: 'Log $150 electricity' or ask tax questions")
        self.ai_input.setStyleSheet(
            "background: #05080f; border: 1px solid #334155; color: #ffffff; border-radius: 6px; padding: 6px 8px; font-size: 8pt;"
        )
        self.ai_input.returnPressed.connect(self._handle_ai_send)

        self.btn_ai_send = QPushButton("🚀")
        self.btn_ai_send.setFixedSize(36, 32)
        self.btn_ai_send.setStyleSheet(
            "background: #9333ea; color: #ffffff; border-radius: 6px; font-weight: bold;"
        )
        self.btn_ai_send.clicked.connect(self._handle_ai_send)

        d_input_box.addWidget(self.ai_input)
        d_input_box.addWidget(self.btn_ai_send)
        drawer_lay.addLayout(d_input_box)

        main_content_layout.addWidget(self.ai_drawer)
        self.ai_drawer.hide()  # initially hidden; toggleable

        layout.addLayout(main_content_layout, 1)

        self._render_chat()

    def _create_card(self, title: str, val: str, subtitle: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background: #0c1220; border: 1px solid #1e293b; border-left: 4px solid {color}; border-radius: 8px; padding: 8px 12px;"
        )
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(4, 4, 4, 4)
        c_lay.setSpacing(3)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 7pt; font-weight: bold; color: #94a3b8; letter-spacing: 0.5px;")
        v_lbl = QLabel(val)
        v_lbl.setObjectName("ValLabel")
        v_lbl.setStyleSheet(f"font-size: 13pt; font-weight: bold; color: {color};")
        s_lbl = QLabel(subtitle)
        s_lbl.setStyleSheet("font-size: 7pt; color: #64748b;")
        c_lay.addWidget(t_lbl)
        c_lay.addWidget(v_lbl)
        c_lay.addWidget(s_lbl)
        return card

    def _build_tax_box(self, title: str, rows: list[tuple[str, str, str]]) -> QFrame:
        box = QFrame()
        box.setStyleSheet("background: #070b14; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        t_lbl = QLabel(f"<b>{title}</b>")
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 8pt; text-transform: uppercase;")
        lay.addWidget(t_lbl)

        for label, val, color in rows:
            r_lay = QHBoxLayout()
            lbl_k = QLabel(label)
            lbl_k.setStyleSheet("color: #cbd5e1; font-size: 8pt;")
            lbl_v = QLabel(val)
            lbl_v.setObjectName(f"TaxVal_{label.split(':')[0]}")
            lbl_v.setStyleSheet(f"color: {color}; font-weight: bold; font-family: monospace; font-size: 8pt;")
            r_lay.addWidget(lbl_k)
            r_lay.addStretch()
            r_lay.addWidget(lbl_v)
            lay.addLayout(r_lay)

        return box

    def _set_subpage(self, idx: int) -> None:
        self.stacked.setCurrentIndex(idx)
        if idx == 0:
            self.btn_page_spreadsheet.setStyleSheet(
                "background: #0284c7; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #38bdf8;"
            )
            self.btn_page_tax.setStyleSheet(
                "background: #0f172a; color: #94a3b8; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #1e293b;"
            )
        else:
            self.btn_page_spreadsheet.setStyleSheet(
                "background: #0f172a; color: #94a3b8; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #1e293b;"
            )
            self.btn_page_tax.setStyleSheet(
                "background: #7e22ce; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #c084fc;"
            )

    def _toggle_ai_drawer(self) -> None:
        if not self.ai_drawer.isHidden():
            self.ai_drawer.hide()
            self.btn_ai_drawer.setText("✨ AI Tax Advisor")
        else:
            self.ai_drawer.show()
            self.btn_ai_drawer.setText("✕ Hide AI Assistant")
            self.ai_input.setFocus()

    def _update_card_val(self, card: QFrame, val: str) -> None:
        lbl = card.findChild(QLabel, "ValLabel")
        if lbl:
            lbl.setText(val)

    def _load_ledger(self) -> None:
        active_db = get_active_db_path()
        if not active_db.exists():
            return
        try:
            conn = sqlite3.connect(active_db)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, date, entry_type, category, description, amount, schedule_c_code, receipt_note
                FROM accounting_entries
                ORDER BY date DESC, id DESC
                """
            )
            raw = cur.fetchall()
            conn.close()

            self._all_rows = []
            categories = set()
            total_income = 0.0
            total_expense = 0.0
            tax_deductible_expense = 0.0
            sec179_total = 0.0
            cat_expense_counts: dict[str, dict] = {}

            for r in raw:
                item = {
                    "id": r[0],
                    "date": r[1] or "",
                    "type": r[2] or "expense",
                    "category": r[3] or "",
                    "desc": r[4] or "",
                    "amount": float(r[5] or 0.0),
                    "schedule_c": r[6] or "",
                    "receipt": r[7] or "",
                }
                self._all_rows.append(item)
                if item["category"]:
                    categories.add(item["category"])

                if item["type"].lower() == "income":
                    total_income += item["amount"]
                else:
                    total_expense += item["amount"]
                    tax_deductible_expense += item["amount"]
                    if "sec179" in item["schedule_c"].lower():
                        sec179_total += item["amount"]

                    cat_key = item["schedule_c"] or item["category"] or "Other"
                    if cat_key not in cat_expense_counts:
                        cat_expense_counts[cat_key] = {"count": 0, "amount": 0.0}
                    cat_expense_counts[cat_key]["count"] += 1
                    cat_expense_counts[cat_key]["amount"] += item["amount"]

            # Update Category Filter items
            curr_cat = self.cat_filter.currentText()
            self.cat_filter.blockSignals(True)
            self.cat_filter.clear()
            self.cat_filter.addItem("All Categories")
            for c in sorted(categories):
                self.cat_filter.addItem(c)
            if curr_cat in categories:
                self.cat_filter.setCurrentText(curr_cat)
            self.cat_filter.blockSignals(False)

            # Calculate Tax Summary (US Federal & Michigan 4.25% Flat)
            net_taxable_income = max(0.0, total_income - tax_deductible_expense)
            mi_state_tax = net_taxable_income * 0.0425
            federal_se_tax = net_taxable_income * 0.9235 * 0.153
            federal_inc_tax = net_taxable_income * 0.12
            total_tax_liability = mi_state_tax + federal_se_tax + federal_inc_tax
            tax_savings = tax_deductible_expense * (0.0425 + 0.153 + 0.12)
            quarterly_payment = total_tax_liability / 4.0

            self._tax_summary = {
                "gross_income": total_income,
                "total_expenses": total_expense,
                "tax_deductible_expenses": tax_deductible_expense,
                "section_179_hardware": sec179_total,
                "net_profit": total_income - total_expense,
                "net_taxable_income": net_taxable_income,
                "estimated_michigan_state_tax": mi_state_tax,
                "estimated_federal_se_tax": federal_se_tax,
                "estimated_federal_income_tax": federal_inc_tax,
                "total_estimated_tax_liability": total_tax_liability,
                "estimated_tax_savings_from_writeoffs": tax_savings,
                "quarterly_payment": quarterly_payment,
            }

            # Update HUD Cards
            self._update_card_val(self.card_income, f"${total_income:,.2f}")
            self._update_card_val(self.card_expense, f"${tax_deductible_expense:,.2f}")
            self._update_card_val(self.card_mi_tax, f"${mi_state_tax:,.2f}")
            self._update_card_val(self.card_tax_savings, f"${tax_savings:,.2f}")

            # Update Tax Engine Boxes
            self._update_box_val(self.box_profit, "Gross Inflow / Revenue", f"${total_income:,.2f}")
            self._update_box_val(self.box_profit, "Total Deductible Write-Offs", f"-${tax_deductible_expense:,.2f}")
            self._update_box_val(self.box_profit, "Net Taxable Profit", f"${net_taxable_income:,.2f}")

            self._update_box_val(self.box_liab, "Michigan State Tax (4.25%)", f"${mi_state_tax:,.2f}")
            self._update_box_val(self.box_liab, "US Federal SE Tax (15.3%)", f"${federal_se_tax:,.2f}")
            self._update_box_val(self.box_liab, "Est. Federal Income Tax (12%)", f"${federal_inc_tax:,.2f}")
            self._update_box_val(self.box_liab, "Total Estimated Liability", f"${total_tax_liability:,.2f}")

            self._update_box_val(self.box_sec179, "Section 179 Equipment Total", f"${sec179_total:,.2f}")

            self._update_box_val(self.box_quarterly, "Q1 (April 15)", f"${quarterly_payment:,.2f}")
            self._update_box_val(self.box_quarterly, "Q2 (June 15)", f"${quarterly_payment:,.2f}")
            self._update_box_val(self.box_quarterly, "Q3 (September 15)", f"${quarterly_payment:,.2f}")
            self._update_box_val(self.box_quarterly, "Q4 (January 15)", f"${quarterly_payment:,.2f}")

            # Update Schedule C Breakdown Table
            self.cat_breakdown_table.setRowCount(len(cat_expense_counts))
            for r_idx, (cat_name, stats) in enumerate(sorted(cat_expense_counts.items())):
                pct = (stats["amount"] / total_expense * 100) if total_expense > 0 else 0
                self.cat_breakdown_table.setItem(r_idx, 0, QTableWidgetItem(cat_name))
                self.cat_breakdown_table.setItem(r_idx, 1, QTableWidgetItem(str(stats["count"])))
                self.cat_breakdown_table.setItem(r_idx, 2, QTableWidgetItem(f"${stats['amount']:,.2f}"))
                self.cat_breakdown_table.setItem(r_idx, 3, QTableWidgetItem(f"{pct:.1f}%"))

            self._filter_table()
        except Exception as e:
            print(f"Error loading accounting ledger: {e}")

    def _update_box_val(self, box: QFrame, key: str, val: str) -> None:
        lbl = box.findChild(QLabel, f"TaxVal_{key}")
        if lbl:
            lbl.setText(val)

    def _filter_table(self) -> None:
        q = self.search_edit.text().strip().lower()
        selected_cat = self.cat_filter.currentText()
        selected_type = self.type_filter.currentText()

        filtered = []
        for row in self._all_rows:
            if selected_cat != "All Categories" and row["category"] != selected_cat:
                continue
            if selected_type == "Expense Only" and row["type"].lower() != "expense":
                continue
            if selected_type == "Income Only" and row["type"].lower() != "income":
                continue
            if q:
                searchable = f"{row['desc']} {row['category']} {row['receipt']} {row['schedule_c']}".lower()
                if q not in searchable:
                    continue
            filtered.append(row)

        self.table.setRowCount(len(filtered))
        for idx, r in enumerate(filtered):
            # ID
            id_item = QTableWidgetItem(str(r["id"]))
            id_item.setForeground(Qt.GlobalColor.gray)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 0, id_item)

            # Date
            self.table.setItem(idx, 1, QTableWidgetItem(r["date"]))

            # Category
            self.table.setItem(idx, 2, QTableWidgetItem(r["category"]))

            # Description
            self.table.setItem(idx, 3, QTableWidgetItem(r["desc"]))

            # Type Badge
            t_item = QTableWidgetItem(r["type"].upper())
            if r["type"].lower() == "income":
                t_item.setForeground(QColor("#34d399"))
            else:
                t_item.setForeground(QColor("#f87171"))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 4, t_item)

            # Amount
            amt_prefix = "+" if r["type"].lower() == "income" else "-"
            amt_item = QTableWidgetItem(f"{amt_prefix}${r['amount']:,.2f}")
            if r["type"].lower() == "income":
                amt_item.setForeground(QColor("#34d399"))
            else:
                amt_item.setForeground(QColor("#f8fafc"))
            amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(idx, 5, amt_item)

            # Tax Write-off
            wo_item = QTableWidgetItem("Deductible" if r["type"].lower() == "expense" else "Taxable")
            wo_item.setForeground(QColor("#38bdf8") if r["type"].lower() == "expense" else QColor("#94a3b8"))
            wo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 6, wo_item)

            # Schedule C
            self.table.setItem(idx, 7, QTableWidgetItem(r["schedule_c"]))

            # Actions: Edit & Delete Buttons
            act_widget = QWidget()
            act_lay = QHBoxLayout(act_widget)
            act_lay.setContentsMargins(2, 2, 2, 2)
            act_lay.setSpacing(4)

            btn_edit = QPushButton("✏️ Edit")
            btn_edit.setStyleSheet(
                "QPushButton { background: transparent; color: #38bdf8; border: none; font-size: 8pt; font-weight: bold; } QPushButton:hover { color: #ffffff; }"
            )
            btn_edit.clicked.connect(lambda checked, item=r: self._open_edit_dialog(item))

            btn_del = QPushButton("🗑️")
            btn_del.setStyleSheet(
                "QPushButton { background: transparent; color: #f87171; border: none; font-size: 8pt; } QPushButton:hover { color: #ffffff; }"
            )
            btn_del.clicked.connect(lambda checked, item_id=r["id"]: self._delete_row(item_id))

            act_lay.addWidget(btn_edit)
            act_lay.addWidget(btn_del)
            self.table.setCellWidget(idx, 8, act_widget)

    def _handle_quick_add(self) -> None:
        date_val = self.qa_date.text().strip()
        entry_type = self.qa_type.currentText()
        desc = self.qa_desc.text().strip()
        amt_str = self.qa_amount.text().strip().replace("$", "").replace(",", "")
        category = self.qa_cat.currentText()

        if not desc or not amt_str:
            QMessageBox.warning(self, "Quick Add Error", "Description and Amount are required.")
            return

        try:
            amt = float(amt_str)
        except ValueError:
            QMessageBox.warning(self, "Quick Add Error", "Amount must be a numeric value.")
            return

        sched_c = "Sec179_Hardware" if "hardware" in category.lower() else "Utilities_Software"
        now_ts = time.time()

        try:
            sync_db_write(
                """
                INSERT INTO accounting_entries
                (date, category, description, entry_type, amount, is_tax_deductible, schedule_c_code, receipt_note, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, '', ?, ?)
                """,
                (date_val, category, desc, entry_type, amt, sched_c, now_ts, now_ts),
            )
            self.qa_desc.clear()
            self.qa_amount.clear()
            self._load_ledger()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add transaction:\n{e}")

    def _on_table_double_click(self) -> None:
        curr_row = self.table.currentRow()
        if curr_row < 0 or curr_row >= len(self._all_rows):
            return
        id_item = self.table.item(curr_row, 0)
        if not id_item:
            return
        try:
            row_id = int(id_item.text())
            for r in self._all_rows:
                if r["id"] == row_id:
                    self._open_edit_dialog(r)
                    break
        except ValueError:
            pass

    def _open_add_dialog(self) -> None:
        dlg = EditTransactionDialog(None, self)
        if dlg.exec():
            self._load_ledger()

    def _open_edit_dialog(self, item: dict) -> None:
        dlg = EditTransactionDialog(item, self)
        if dlg.exec():
            self._load_ledger()

    def _delete_row(self, item_id: int) -> None:
        res = QMessageBox.question(
            self, "Confirm Delete", f"Delete transaction ID #{item_id} from the ledger?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            try:
                sync_db_write("DELETE FROM accounting_entries WHERE id = ?", (item_id,))
                self._load_ledger()
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Failed to delete entry #{item_id}:\n{e}")

    def _export_csv(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Financial Ledger to CSV", "AI_BS_Accounting_Ledger.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Date", "Type", "Category", "Description", "Amount", "Schedule_C", "Receipt"])
                for r in self._all_rows:
                    writer.writerow([
                        r["id"], r["date"], r["type"], r["category"], r["desc"], r["amount"], r["schedule_c"], r["receipt"]
                    ])
            QMessageBox.information(self, "Export Success", f"Ledger exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{e}")

    def _export_schedule_c_csv(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export IRS Schedule C Summary", "AI_BS_Schedule_C_Tax_Summary.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Stehouwer Publishing LLC / NoCo - IRS Schedule C & Michigan Tax Summary"])
                writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([])
                writer.writerow(["Metric", "Amount ($ USD)"])
                writer.writerow(["Gross Revenue", f"{self._tax_summary.get('gross_income', 0):.2f}"])
                writer.writerow(["Total Tax-Deductible Write-Offs", f"{self._tax_summary.get('tax_deductible_expenses', 0):.2f}"])
                writer.writerow(["Section 179 Hardware Write-Offs", f"{self._tax_summary.get('section_179_hardware', 0):.2f}"])
                writer.writerow(["Net Taxable Profit", f"{self._tax_summary.get('net_taxable_income', 0):.2f}"])
                writer.writerow(["Michigan State Flat Tax (4.25%)", f"{self._tax_summary.get('estimated_michigan_state_tax', 0):.2f}"])
                writer.writerow(["Federal Self-Employment Tax (15.3%)", f"{self._tax_summary.get('estimated_federal_se_tax', 0):.2f}"])
                writer.writerow(["Estimated Federal Income Tax (12%)", f"{self._tax_summary.get('estimated_federal_income_tax', 0):.2f}"])
                writer.writerow(["Total Estimated Annual Tax Liability", f"{self._tax_summary.get('total_estimated_tax_liability', 0):.2f}"])
                writer.writerow(["Estimated Quarterly Estimated Tax (1040-ES)", f"{self._tax_summary.get('quarterly_payment', 0):.2f}"])
            QMessageBox.information(self, "Export Success", f"Schedule C Summary exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export Schedule C CSV:\n{e}")

    def _render_chat(self) -> None:
        while self.chat_lay.count() > 1:
            child = self.chat_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for msg in self._chat_history:
            bubble = QFrame()
            is_user = msg["sender"] == "user"
            bubble_bg = "#9333ea" if is_user else "#1e293b"
            bubble.setStyleSheet(f"background: {bubble_bg}; border-radius: 8px; padding: 8px;")
            b_lay = QVBoxLayout(bubble)
            b_lay.setContentsMargins(4, 4, 4, 4)

            lbl = QLabel(msg["text"])
            lbl.setStyleSheet("color: #ffffff; font-size: 8pt;")
            lbl.setWordWrap(True)
            b_lay.addWidget(lbl)

            row = QHBoxLayout()
            if is_user:
                row.addStretch()
                row.addWidget(bubble)
            else:
                row.addWidget(bubble)
                row.addStretch()
            self.chat_lay.insertLayout(self.chat_lay.count() - 1, row)

        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _handle_ai_send(self) -> None:
        user_text = self.ai_input.text().strip()
        if not user_text:
            return
        self.ai_input.clear()
        self._chat_history.append({"sender": "user", "text": user_text})
        self._render_chat()

        # Autonomous Financial AI command parsing & tax engine lookup
        lower = user_text.lower()
        if "log" in lower or "add" in lower:
            # Extract amount
            amt_match = re.search(r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)", user_text)
            amt = float(amt_match.group(1).replace(",", "")) if amt_match else 0.0

            # Determine category & type
            is_income = any(w in lower for w in ["income", "revenue", "paid", "payout", "deposit"])
            entry_type = "income" if is_income else "expense"

            category = "Other Business"
            sched_c = "Other"
            if "gpu" in lower or "hardware" in lower or "rtx" in lower or "server" in lower or "drive" in lower:
                category = "Hardware & Electronics"
                sched_c = "Sec179_Hardware"
            elif "electric" in lower or "power" in lower or "utility" in lower:
                category = "Utilities & Electricity"
                sched_c = "Utilities_Electric"
            elif "cloud" in lower or "aws" in lower or "gcp" in lower or "azure" in lower:
                category = "Cloud Infrastructure"
                sched_c = "Utilities_Software"
            elif "software" in lower or "sub" in lower:
                category = "Software Subscriptions"
                sched_c = "Utilities_Software"
            elif is_income:
                category = "Commercial API Payouts"
                sched_c = "Gross_Sales"

            desc = user_text.replace("log", "").replace("add", "").replace("an expense of", "").replace("expense", "").strip()
            if not desc:
                desc = f"{category} Transaction"

            if amt > 0:
                now_ts = time.time()
                today_str = datetime.now().strftime("%Y-%m-%d")
                sync_db_write(
                    """
                    INSERT INTO accounting_entries
                    (date, category, description, entry_type, amount, is_tax_deductible, schedule_c_code, receipt_note, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, 'AI Copilot Auto-Log', ?, ?)
                    """,
                    (today_str, category, desc, entry_type, amt, sched_c, now_ts, now_ts),
                )
                self._load_ledger()
                reply = f"✅ Recorded {entry_type.upper()} of ${amt:,.2f} for '{desc}' under '{category}' ({sched_c}). Ledger and tax reserve recalculated!"
            else:
                reply = "Could not parse the dollar amount. Example command: 'Log an expense of $1,599.99 for RTX 4090 GPU'."
        elif "michigan" in lower or "mi tax" in lower or "state tax" in lower:
            mi_tax = self._tax_summary.get("estimated_michigan_state_tax", 0.0)
            profit = self._tax_summary.get("net_taxable_income", 0.0)
            reply = f"Michigan applies a flat 4.25% business income tax. On your current net taxable profit of ${profit:,.2f}, estimated MI state tax is ${mi_tax:,.2f}."
        elif "quarter" in lower or "due" in lower or "deadline" in lower:
            q_amt = self._tax_summary.get("quarterly_payment", 0.0)
            reply = f"IRS Form 1040-ES estimated quarterly payments: Q1: Apr 15, Q2: Jun 15, Q3: Sep 15, Q4: Jan 15. Estimated payment per quarter: ${q_amt:,.2f}."
        elif "write" in lower or "deduct" in lower or "section 179" in lower:
            sec179 = self._tax_summary.get("section_179_hardware", 0.0)
            savings = self._tax_summary.get("estimated_tax_savings_from_writeoffs", 0.0)
            reply = f"You have ${sec179:,.2f} logged under Section 179 Hardware (100% accelerated first-year depreciation). Total deduction savings across Federal SE + MI state tax is ${savings:,.2f}."
        elif "profit" in lower or "revenue" in lower or "income" in lower:
            rev = self._tax_summary.get("gross_income", 0.0)
            exp = self._tax_summary.get("tax_deductible_expenses", 0.0)
            profit = self._tax_summary.get("net_profit", 0.0)
            reply = f"Financial Snapshot: Gross Revenue: ${rev:,.2f} | Deductible Expenses: ${exp:,.2f} | Net Profit: ${profit:,.2f}."
        else:
            reply = (
                "Stehouwer Financial AI Copilot ready. Commands:\n"
                "• 'Log an expense of $150 for Electricity'\n"
                "• 'Log income of $2,500 for Consulting'\n"
                "• 'What is my Michigan state tax?'\n"
                "• 'What are my quarterly tax due dates?'"
            )

        self._chat_history.append({"sender": "ai", "text": reply})
        self._render_chat()
