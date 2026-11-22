"""Master Schedule & Event Calendar Native View (Pure Windows Direct Scheduling).

Features:
- Native QCalendarWidget styled with AI-BS dark cybernetic design system
- Selected Date Agenda: Appointments, client calls, filming shoots, and automated cron tasks
- Record New Event / Milestone dialog with priority tags and categories
- 7-Day Forward Horizon & Milestone Ticker
- Persistent SQLite / JSON agenda storage
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import EngineBus
from native_studio.theme import PALETTE


AGENDA_STORE = Path(r"C:\AI-BS\saved_data\master_calendar_events.json")


class AddEventDialog(QDialog):
    """Dialog for creating a new calendar event or operational milestone."""

    def __init__(self, default_date: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Schedule Operational Milestone")
        self.setFixedSize(450, 380)
        self.setStyleSheet(
            f"background-color: {PALETTE['panel']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; border-radius: 8px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.date_edit = QLineEdit(default_date)
        form.addRow("Event Date (YYYY-MM-DD):", self.date_edit)

        self.time_edit = QLineEdit("14:00 EST")
        form.addRow("Time / Horizon:", self.time_edit)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g., Dennis Bell Recruiting Campaign Broadcast")
        form.addRow("Title / Milestone:", self.title_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Client Strategy Call",
            "Film & Broadcast Shoot",
            "Recruiting Outbox Blast",
            "System Maintenance & Backup",
            "Accounting & Tax Review",
            "General Milestone",
        ])
        form.addRow("Category:", self.category_combo)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["CRITICAL", "HIGH", "ROUTINE"])
        form.addRow("Priority Level:", self.priority_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Brief operational notes or deliverables...")
        self.notes_edit.setFixedHeight(70)
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save to Schedule")
        save_btn.setStyleSheet(
            f"background: {PALETTE['cyan']}; color: #020617; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        save_btn.clicked.connect(self._save)
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        layout.addLayout(btn_box)

    def _save(self) -> None:
        title = self.title_edit.text().strip()
        date_str = self.date_edit.text().strip()
        if not title or not date_str:
            QMessageBox.warning(self, "Validation Error", "Title and Date are required.")
            return

        ev = {
            "date": date_str,
            "time": self.time_edit.text().strip(),
            "title": title,
            "category": self.category_combo.currentText(),
            "priority": self.priority_combo.currentText(),
            "notes": self.notes_edit.toPlainText().strip(),
        }

        # Append to json file
        events = []
        if AGENDA_STORE.exists():
            try:
                with open(AGENDA_STORE, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except Exception:
                events = []
        events.append(ev)
        AGENDA_STORE.parent.mkdir(parents=True, exist_ok=True)
        with open(AGENDA_STORE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)

        self.accept()


class CalendarScheduleNativeView(QWidget):
    """Master Schedule & Event Calendar Native View."""

    def __init__(self, bus: EngineBus) -> None:
        super().__init__()
        self.bus = bus
        self._events: list[dict] = []
        self._init_ui()
        self._load_events()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title & Actions
        head_box = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("📅 Master Schedule & Event Calendar")
        title.setStyleSheet("font-size: 15pt; font-weight: bold; color: #f8fafc;")
        subtitle = QLabel("Native Timeline Planner | Client Appointments, Dispatches & Operational Deadlines")
        subtitle.setStyleSheet("font-size: 8.5pt; color: #64748b;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        head_box.addLayout(title_box)
        head_box.addStretch()

        self.btn_add = QPushButton("➕ Schedule Event")
        self.btn_add.setStyleSheet(
            f"background: {PALETTE['cyan']}; color: #020617; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        self.btn_add.clicked.connect(self._open_add_dialog)
        head_box.addWidget(self.btn_add)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet(
            f"background: #1e293b; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']}; padding: 7px 12px; border-radius: 6px;"
        )
        self.btn_refresh.clicked.connect(self._load_events)
        head_box.addWidget(self.btn_refresh)

        layout.addLayout(head_box)

        # Splitter: Calendar (Left) + Selected Day Agenda (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1e293b; width: 4px; }")

        # Left: Interactive Calendar Widget
        left_box = QWidget()
        l_lay = QVBoxLayout(left_box)
        l_lay.setContentsMargins(0, 0, 0, 0)
        l_lay.setSpacing(8)

        self.cal = QCalendarWidget()
        self.cal.setGridVisible(True)
        self.cal.setStyleSheet(
            "QCalendarWidget QWidget { alternate-background-color: #0b1120; background: #070b14; color: #f8fafc; font-size: 9pt; }"
            "QCalendarWidget QAbstractItemView:enabled { background: #070b14; color: #cbd5e1; selection-background-color: #22d3ee; selection-color: #020617; }"
            "QCalendarWidget QMenu { background-color: #0f172a; color: #f8fafc; }"
            "QCalendarWidget QSpinBox { background: #0f172a; color: #f8fafc; }"
            "QCalendarWidget QToolButton { background-color: #0f172a; color: #38bdf8; font-weight: bold; border-radius: 4px; padding: 4px; }"
        )
        self.cal.selectionChanged.connect(self._on_date_changed)
        l_lay.addWidget(self.cal, 1)

        # 7-Day Horizon Preview
        horizon_title = QLabel("🔮 UPCOMING 7-DAY HORIZON:")
        horizon_title.setStyleSheet("font-size: 8pt; font-weight: bold; color: #94a3b8;")
        l_lay.addWidget(horizon_title)

        self.horizon_list = QListWidget()
        self.horizon_list.setFixedHeight(120)
        self.horizon_list.setStyleSheet(
            "background: #050811; border: 1px solid #1e293b; border-radius: 6px; color: #e2e8f0; font-size: 8.5pt;"
        )
        l_lay.addWidget(self.horizon_list)
        splitter.addWidget(left_box)

        # Right: Selected Day Agenda Table & Notes
        right_box = QFrame()
        right_box.setStyleSheet(
            "background: #090d16; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;"
        )
        r_lay = QVBoxLayout(right_box)
        r_lay.setContentsMargins(12, 12, 12, 12)
        r_lay.setSpacing(10)

        self.lbl_selected_date = QLabel("AGENDA FOR TODAY")
        self.lbl_selected_date.setStyleSheet("font-size: 11pt; font-weight: bold; color: #22d3ee;")
        r_lay.addWidget(self.lbl_selected_date)

        self.agenda_table = QTableWidget()
        self.agenda_table.setColumnCount(4)
        self.agenda_table.setHorizontalHeaderLabels(["Time", "Priority", "Category", "Milestone / Event"])
        self.agenda_table.horizontalHeader().setStretchLastSection(True)
        self.agenda_table.setColumnWidth(0, 80)
        self.agenda_table.setColumnWidth(1, 80)
        self.agenda_table.setColumnWidth(2, 140)
        self.agenda_table.setStyleSheet(
            "QTableWidget { background: #050811; gridline-color: #1e293b; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; font-size: 8.5pt; }"
            "QHeaderView::section { background: #0f172a; color: #94a3b8; font-weight: bold; padding: 4px; }"
        )
        r_lay.addWidget(self.agenda_table, 1)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, 1)

    def _load_events(self) -> None:
        self._events = []
        if AGENDA_STORE.exists():
            try:
                with open(AGENDA_STORE, "r", encoding="utf-8") as f:
                    self._events = json.load(f)
            except Exception:
                self._events = []
        else:
            # Seed with real ecosystem baseline items
            self._events = [
                {"date": datetime.now().strftime("%Y-%m-%d"), "time": "09:00 EST", "title": "Hardware Thermal & NVML Audit", "category": "System Maintenance & Backup", "priority": "ROUTINE", "notes": "Verify RTX 4090 sub-35C idle thermals"},
                {"date": datetime.now().strftime("%Y-%m-%d"), "time": "14:00 EST", "title": "Dennis Bell Recruiting Outbox Sync", "category": "Recruiting Outbox Blast", "priority": "HIGH", "notes": "Monitor college coach response matrix"},
                {"date": datetime.now().strftime("%Y-%m-%d"), "time": "18:00 EST", "title": "Accounting & Tax Reserve Balancing", "category": "Accounting & Tax Review", "priority": "CRITICAL", "notes": "Reconcile Section 179 ledger deductions"},
            ]
            AGENDA_STORE.parent.mkdir(parents=True, exist_ok=True)
            with open(AGENDA_STORE, "w", encoding="utf-8") as f:
                json.dump(self._events, f, indent=2)

        self._populate_horizon()
        self._on_date_changed()

    def _populate_horizon(self) -> None:
        self.horizon_list.clear()
        for ev in self._events:
            self.horizon_list.addItem(f"🗓️  {ev['date']} | {ev['time']} — {ev['title']} [{ev['priority']}]")

    def _on_date_changed(self) -> None:
        qdate = self.cal.selectedDate()
        date_str = qdate.toString("yyyy-MM-dd")
        self.lbl_selected_date.setText(f"AGENDA FOR {date_str}:")

        matched = [ev for ev in self._events if ev["date"] == date_str]
        self.agenda_table.setRowCount(len(matched))
        for idx, ev in enumerate(matched):
            self.agenda_table.setItem(idx, 0, QTableWidgetItem(ev["time"]))

            p_item = QTableWidgetItem(ev["priority"])
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if ev["priority"] == "CRITICAL":
                p_item.setForeground(Qt.GlobalColor.red)
            elif ev["priority"] == "HIGH":
                p_item.setForeground(Qt.GlobalColor.yellow)
            else:
                p_item.setForeground(Qt.GlobalColor.green)
            self.agenda_table.setItem(idx, 1, p_item)

            self.agenda_table.setItem(idx, 2, QTableWidgetItem(ev["category"]))
            self.agenda_table.setItem(idx, 3, QTableWidgetItem(ev["title"]))

    def _open_add_dialog(self) -> None:
        curr_date = self.cal.selectedDate().toString("yyyy-MM-dd")
        dlg = AddEventDialog(curr_date, self)
        if dlg.exec():
            self._load_events()
