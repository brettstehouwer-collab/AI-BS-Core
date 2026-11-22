"""Modules for AI-BS Native Studio Control Center views."""

from __future__ import annotations

import time
from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from native_studio.engine import (
    VAULT_DATABASES,
    EngineBus,
    GpuProbe,
    fetch_page,
    list_tables,
    ollama_inventory,
    ollama_unload,
    probe_ports,
    run_matrix_doctor_heal,
    sample_system,
    top_processes,
)
from native_studio.theme import PALETTE, severity_color
from native_studio.widgets import Card, GaugeCard, MetricCard, StatusBadge


class HardwareView(QWidget):
    """View 1: AMD Ryzen 9 9950X CPU, RAM, NVMe Disks, and Top Memory Procs."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("System Hardware & Compute Platform")
        t.setObjectName("PanelTitle")
        st = QLabel("AMD Ryzen 9 9950X (16C/32T) • High-Speed DDR5 • Multi-NVMe Arrays")
        st.setObjectName("PanelSubtitle")
        title_box.addWidget(t)
        title_box.addWidget(st)
        hdr.addLayout(title_box)
        hdr.addStretch()

        self.refresh_btn = QPushButton("↻ Refresh Now")
        self.refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self.refresh_btn)
        main_layout.addLayout(hdr)

        # KPIs Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        self.cpu_gauge = GaugeCard("CPU Total Load", warn_at=75.0, crit_at=90.0)
        self.ram_gauge = GaugeCard("System Memory (RAM)", warn_at=85.0, crit_at=95.0)
        self.disk_c_gauge = GaugeCard("Drive C: (Primary NVMe)", warn_at=85.0, crit_at=95.0)
        self.disk_e_gauge = GaugeCard("Drive E: (Ollama & Media)", warn_at=85.0, crit_at=95.0)

        grid.addWidget(self.cpu_gauge, 0, 0)
        grid.addWidget(self.ram_gauge, 0, 1)
        grid.addWidget(self.disk_c_gauge, 1, 0)
        grid.addWidget(self.disk_e_gauge, 1, 1)
        main_layout.addLayout(grid)

        # Top Memory Consumers Table
        proc_card = Card("Top Host Working Memory Processes (RAM)")
        self.proc_table = QTableWidget(0, 3)
        self.proc_table.setHorizontalHeaderLabels(["Process Name", "PID", "Working Memory (GB)"])
        self.proc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.proc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        proc_card.layout_box.addWidget(self.proc_table)
        main_layout.addWidget(proc_card)

        # Auto refresh timer (3s)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)
        self.refresh()

    def refresh(self) -> None:
        self.bus.submit(sample_system, on_result=self._on_sys_data)
        self.bus.submit(top_processes, 7, on_result=self._on_proc_data)

    def _on_sys_data(self, data: dict[str, Any]) -> None:
        cpu = data.get("cpu_pct", 0.0)
        self.cpu_gauge.set_value(cpu, f"{cpu:.1f}%", f"{data.get('ts') and time.strftime('%H:%M:%S')}")

        ram_pct = data.get("ram_pct", 0.0)
        used_gb = data.get("ram_used_gb", 0.0)
        tot_gb = data.get("ram_total_gb", 0.0)
        self.ram_gauge.set_value(ram_pct, f"{used_gb:.1f} / {tot_gb:.1f} GB ({ram_pct:.1f}%)")

        for d in data.get("disks", []):
            if d.get("drive") == "C:":
                u_pct = d.get("used_pct", 0.0)
                self.disk_c_gauge.set_value(u_pct, f"{d.get('free_gb', 0):.1f} GB Free", f"{d.get('used_pct'):.1f}% Full")
            elif d.get("drive") == "E:":
                u_pct = d.get("used_pct", 0.0)
                self.disk_e_gauge.set_value(u_pct, f"{d.get('free_gb', 0):.1f} GB Free", f"{d.get('used_pct'):.1f}% Full")

    def _on_proc_data(self, procs: list[dict[str, Any]]) -> None:
        self.proc_table.setRowCount(len(procs))
        for row, p in enumerate(procs):
            name_item = QTableWidgetItem(str(p.get("name", "")))
            pid_item = QTableWidgetItem(str(p.get("pid", "")))
            mem_item = QTableWidgetItem(f"{p.get('rss_gb', 0):.2f} GB")
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            mem_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.proc_table.setItem(row, 0, name_item)
            self.proc_table.setItem(row, 1, pid_item)
            self.proc_table.setItem(row, 2, mem_item)


class GpuView(QWidget):
    """View 2: NVIDIA GeForce RTX 4090 Direct NVML Telemetry & Fan Locks."""

    def __init__(self, bus: EngineBus, probe: GpuProbe, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus, self.probe = bus, probe

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("Sovereign GPU & Tensor Engine")
        t.setObjectName("PanelTitle")
        st = QLabel("NVIDIA GeForce RTX 4090 24GB • Direct NVML Hardware Binding")
        st.setObjectName("PanelSubtitle")
        title_box.addWidget(t)
        title_box.addWidget(st)
        hdr.addLayout(title_box)
        hdr.addStretch()

        self.auto_fan_btn = QPushButton("❄️ Auto Driver Curve")
        self.auto_fan_btn.clicked.connect(lambda: self.set_fan(None))
        self.lock_fan_btn = QPushButton("🔥 Lock Fans 100%")
        self.lock_fan_btn.setObjectName("Danger")
        self.lock_fan_btn.clicked.connect(lambda: self.set_fan(100))
        hdr.addWidget(self.auto_fan_btn)
        hdr.addWidget(self.lock_fan_btn)
        layout.addLayout(hdr)

        # Top KPIs
        grid = QGridLayout()
        grid.setSpacing(12)

        self.temp_kpi = MetricCard("GPU Core Thermals", "-- °C", "Frosty 100% Lock Target: < 40°C")
        self.vram_gauge = GaugeCard("VRAM Allocated (24 GB Total)", warn_at=80.0, crit_at=95.0)
        self.power_kpi = MetricCard("Board Power Draw", "-- W", "TDP Ceiling: 450 W")
        self.fan_kpi = MetricCard("Active Fan Speed", "-- %", "PWM Controller State")

        grid.addWidget(self.temp_kpi, 0, 0)
        grid.addWidget(self.vram_gauge, 0, 1)
        grid.addWidget(self.power_kpi, 1, 0)
        grid.addWidget(self.fan_kpi, 1, 1)
        layout.addLayout(grid)

        # Details Card
        details_card = Card("Engine Clocks, Driver & Architecture Metadata")
        self.det_label = QLabel("Initializing NVML hardware bindings...")
        self.det_label.setStyleSheet("color: #8b9bb4; font-family: 'Cascadia Mono', Consolas; font-size: 10pt;")
        details_card.layout_box.addWidget(self.det_label)
        layout.addWidget(details_card)
        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2500)
        self.refresh()

    def set_fan(self, target: int | None) -> None:
        def _do():
            return self.probe.set_fans(target)
        self.bus.submit(_do, on_result=lambda msg: self.refresh())

    def refresh(self) -> None:
        self.bus.submit(self.probe.sample, on_result=self._on_gpu_data)

    def _on_gpu_data(self, data: dict[str, Any]) -> None:
        if not data.get("detected"):
            self.temp_kpi.set_value("OFFLINE", PALETTE["rose"], data.get("error", "Not detected"))
            return

        temp = data.get("temp_c")
        t_col = severity_color(float(temp) if temp else None, warn=65, crit=75, base="emerald")
        self.temp_kpi.set_value(f"{temp}°C" if temp is not None else "--", t_col)

        v_used = data.get("vram_used_gb", 0.0)
        v_tot = data.get("vram_total_gb", 24.0)
        v_pct = (v_used / v_tot * 100.0) if v_tot > 0 else 0.0
        v_free = v_tot - v_used
        self.vram_gauge.set_value(v_pct, f"{v_used:.2f} / {v_tot:.1f} GB", f"{v_free:.2f} GB Free Headroom")

        pwr = data.get("power_w")
        self.power_kpi.set_value(f"{pwr:.1f} W" if pwr else "--", PALETTE["amber"])

        fan = data.get("fan_pct")
        self.fan_kpi.set_value(f"{fan}%" if fan is not None else "Auto", PALETTE["cyan"])

        # Details
        clocks = f"Graphics Clock: {data.get('core_mhz', '--')} MHz | Memory Clock: {data.get('mem_mhz', '--')} MHz\n"
        driver = f"NVIDIA Driver: {data.get('driver', '--')} | Hardware Target: {data.get('name', 'NVIDIA GeForce RTX 4090')}"
        self.det_label.setText(f"{clocks}{driver}")


class PortMatrixView(QWidget):
    """View 3: 18-Port Collision Matrix & In-Process Matrix Doctor."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("18-Port Ecosystem Matrix & Topology")
        t.setObjectName("PanelTitle")
        st = QLabel("Static Socket Reservation • In-Process Diagnostic & Self-Healing Matrix Doctor")
        st.setObjectName("PanelSubtitle")
        title_box.addWidget(t)
        title_box.addWidget(st)
        hdr.addLayout(title_box)
        hdr.addStretch()

        self.heal_btn = QPushButton("⚡ In-Process Matrix Doctor: Heal")
        self.heal_btn.setObjectName("Accent")
        self.heal_btn.clicked.connect(self.heal)
        self.probe_btn = QPushButton("↻ Scan Matrix")
        self.probe_btn.clicked.connect(self.scan)
        hdr.addWidget(self.heal_btn)
        hdr.addWidget(self.probe_btn)
        layout.addLayout(hdr)

        # Port Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Port", "Subsystem Name", "Category", "State", "PID / Process"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Doctor output log
        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("Console")
        self.log_box.setMaximumHeight(110)
        self.log_box.setReadOnly(True)
        self.log_box.setPlainText("AI-BS Matrix Doctor ready. Press 'Scan Matrix' or 'Heal' to test.\n")
        layout.addWidget(self.log_box)

        self.scan()

    def scan(self) -> None:
        self.probe_btn.setEnabled(False)
        self.bus.submit(probe_ports, on_result=self._on_ports)

    def heal(self) -> None:
        self.heal_btn.setEnabled(False)
        self.log_box.appendPlainText(f"[{time.strftime('%H:%M:%S')}] Executing in-process Matrix Doctor heal routine...")
        self.bus.submit(run_matrix_doctor_heal, on_result=self._on_healed)

    def _on_healed(self, res: Any) -> None:
        self.heal_btn.setEnabled(True)
        self.log_box.appendPlainText(f"[{time.strftime('%H:%M:%S')}] Matrix Doctor completed: {res}\n")
        self.scan()

    def _on_ports(self, results: dict[int, dict[str, Any]]) -> None:
        self.probe_btn.setEnabled(True)
        self.table.setRowCount(len(results))
        for row, (port, info) in enumerate(sorted(results.items())):
            p_item = QTableWidgetItem(f":{port}")
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            name_item = QTableWidgetItem(info.get("name", ""))
            cat_item = QTableWidgetItem(info.get("category", ""))
            online = info.get("online", False)

            st_badge = StatusBadge(online)
            pid = info.get("pid")
            proc = info.get("process")
            owner_text = f"{proc} ({pid})" if proc and pid else (f"PID {pid}" if pid else "--")
            owner_item = QTableWidgetItem(owner_text)
            owner_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, p_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, cat_item)
            self.table.setCellWidget(row, 3, st_badge)
            self.table.setItem(row, 4, owner_item)


class OllamaFleetView(QWidget):
    """View 4: Local Ollama Neural Fleet Model Swarm."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("Sovereign Neural LLM Fleet")
        t.setObjectName("PanelTitle")
        st = QLabel("Multi-Model Ollama Swarm on Drive E: (Ports 11434 & 11435)")
        st.setObjectName("PanelSubtitle")
        title_box.addWidget(t)
        title_box.addWidget(st)
        hdr.addLayout(title_box)
        hdr.addStretch()

        self.port_select = QComboBox()
        self.port_select.addItem("GPU Node (Port 11434)", 11434)
        self.port_select.addItem("CPU Node (Port 11435)", 11435)
        self.port_select.currentIndexChanged.connect(self.refresh)
        hdr.addWidget(self.port_select)

        self.refresh_btn = QPushButton("↻ Refresh Models")
        self.refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self.refresh_btn)
        layout.addLayout(hdr)

        # Active Model Loaded Banner
        self.active_banner = QLabel("No active models in VRAM")
        self.active_banner.setStyleSheet(
            f"background-color: #0d1424; border: 1px solid {PALETTE['border']}; border-radius: 8px; "
            f"padding: 10px 14px; font-weight: 600; color: {PALETTE['emerald']};"
        )
        layout.addWidget(self.active_banner)

        # Models Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Model Tag", "Size", "Family", "Quant", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        port = self.port_select.currentData()
        self.refresh_btn.setEnabled(False)
        self.bus.submit(ollama_inventory, port, on_result=self._on_models, on_error=self._on_err)

    def _on_err(self, err: str) -> None:
        self.refresh_btn.setEnabled(True)
        self.active_banner.setText(f"Ollama Node Offline or Unreachable: {err}")
        self.active_banner.setStyleSheet("color: #fb7185; padding: 10px; background: #0d1424; border-radius: 8px;")
        self.table.setRowCount(0)

    def _on_models(self, data: dict[str, Any]) -> None:
        self.refresh_btn.setEnabled(True)
        loaded = data.get("loaded", [])
        if loaded:
            txt = " • ".join(f"🔥 {m['name']} ({m['vram_gb']:.2f} GB in VRAM)" for m in loaded)
            self.active_banner.setText(f"Active Loaded: {txt}")
        else:
            self.active_banner.setText("❄️ Standby: Zero models currently occupying VRAM")

        models = data.get("models", [])
        self.table.setRowCount(len(models))
        port = data.get("port", 11434)

        for row, m in enumerate(models):
            name = m.get("name", "")
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{m.get('size_gb', 0):.2f} GB"))
            self.table.setItem(row, 2, QTableWidgetItem(m.get("family", "")))
            self.table.setItem(row, 3, QTableWidgetItem(m.get("quant", "")))

            btn = QPushButton("Unload")
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda _, n=name, p=port: self._unload(p, n))
            self.table.setCellWidget(row, 4, btn)

    def _unload(self, port: int, model: str) -> None:
        self.bus.submit(ollama_unload, port, model, on_result=lambda _: self.refresh())


class VaultBrowserView(QWidget):
    """View 5: High-Performance SQLite Data Vaults Explorer."""

    def __init__(self, bus: EngineBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bus = bus

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header & Database Picker
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("Master SQLite Data Vaults")
        t.setObjectName("PanelTitle")
        st = QLabel("Read-Only WAL Query Pipeline • 350,000+ Synchronized Records")
        st.setObjectName("PanelSubtitle")
        title_box.addWidget(t)
        title_box.addWidget(st)
        hdr.addLayout(title_box)
        hdr.addStretch()

        self.db_combo = QComboBox()
        for name, path in VAULT_DATABASES.items():
            if path.exists():
                self.db_combo.addItem(f"{name} ({round(path.stat().st_size / (1024*1024), 1)} MB)", str(path))
        self.db_combo.currentIndexChanged.connect(self._on_db_change)
        hdr.addWidget(self.db_combo)
        layout.addLayout(hdr)

        # Splitter: Left = Table List, Right = Records View
        split = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Tables
        left_w = QWidget()
        left_lay = QVBoxLayout(left_w)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.addWidget(QLabel("Tables & Row Counts:"))
        self.table_list = QTableWidget(0, 2)
        self.table_list.setHorizontalHeaderLabels(["Table", "Rows"])
        self.table_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_list.cellClicked.connect(self._on_table_click)
        left_lay.addWidget(self.table_list)
        split.addWidget(left_w)

        # Right panel: Data Grid
        right_w = QWidget()
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(0, 0, 0, 0)

        filter_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter records (search text columns)...")
        self.search_edit.returnPressed.connect(self._run_search)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._run_search)
        filter_bar.addWidget(self.search_edit)
        filter_bar.addWidget(self.search_btn)
        right_lay.addLayout(filter_bar)

        self.data_grid = QTableWidget(0, 0)
        right_lay.addWidget(self.data_grid)

        split.addWidget(right_w)
        split.setSizes([260, 680])
        layout.addWidget(split)

        self._current_table: str | None = None
        self._on_db_change()

    def _on_db_change(self) -> None:
        path = self.db_combo.currentData()
        if not path:
            return
        self.bus.submit(list_tables, path, on_result=self._populate_tables)

    def _populate_tables(self, tables: list[tuple[str, int]]) -> None:
        self.table_list.setRowCount(len(tables))
        for row, (name, count) in enumerate(tables):
            self.table_list.setItem(row, 0, QTableWidgetItem(name))
            cnt_str = f"{count:,}" if count >= 0 else "?"
            cnt_item = QTableWidgetItem(cnt_str)
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_list.setItem(row, 1, cnt_item)
        if tables:
            self._current_table = tables[0][0]
            self._fetch_records()

    def _on_table_click(self, row: int, col: int) -> None:
        t_item = self.table_list.item(row, 0)
        if t_item:
            self._current_table = t_item.text()
            self._fetch_records()

    def _run_search(self) -> None:
        self._fetch_records(self.search_edit.text().strip() or None)

    def _fetch_records(self, search: str | None = None) -> None:
        path = self.db_combo.currentData()
        if not path or not self._current_table:
            return
        self.bus.submit(
            fetch_page,
            path,
            self._current_table,
            0,
            150,
            search,
            on_result=self._populate_records,
        )

    def _populate_records(self, page: dict[str, Any]) -> None:
        cols = page.get("columns", [])
        rows = page.get("rows", [])
        self.data_grid.clear()
        self.data_grid.setColumnCount(len(cols))
        self.data_grid.setHorizontalHeaderLabels(cols)
        self.data_grid.setRowCount(len(rows))

        for r_idx, r_data in enumerate(rows):
            for c_idx, val in enumerate(r_data):
                txt = str(val) if val is not None else ""
                item = QTableWidgetItem(txt[:100] + "..." if len(txt) > 100 else txt)
                self.data_grid.setItem(r_idx, c_idx, item)
