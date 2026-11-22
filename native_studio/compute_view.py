"""AI Compute Lab: PyQt6 front-end for the CUDA/AI worker thread + live telemetry hub.

Data path (all in-process / RAM):
    AiComputeWorker (QThread, torch) --metrics signal--> this view (GUI thread)
    TelemetryHub    (QThread)        --frame signal----> this view + shared memory -> Dear PyGui HUD
"""

from __future__ import annotations

from collections import deque

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from native_studio.ai_compute import AiComputeWorker, ollama_stream_job, reference_training_job, torch_device_info
from native_studio.dpg_hud import launch_hud
from native_studio.engine import PORT_MATRIX
from native_studio.telemetry_hub import TelemetryHub
from native_studio.theme import PALETTE
from native_studio.widgets import Card, GaugeCard, MetricCard

pg.setConfigOptions(antialias=True, background="#050912", foreground="#8b9bb4")


class ComputeLabView(QWidget):
    def __init__(self, hub: TelemetryHub, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.hub = hub
        self.worker: AiComputeWorker | None = None
        self._hud = None
        self._loss: deque[float] = deque(maxlen=400)
        self._step: deque[float] = deque(maxlen=400)
        self._gflops: deque[float] = deque(maxlen=400)
        self._tokens = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)
        t = QLabel("🧪  AI Compute Lab & Live Telemetry")
        t.setObjectName("PanelTitle")
        s = QLabel("QThread CUDA/AI worker • NVML + psutil + 20-port matrix + audio kernel • shared-memory feed to Dear PyGui HUD • no local web server")
        s.setObjectName("PanelSubtitle")
        root.addWidget(t)
        root.addWidget(s)

        info = torch_device_info()
        self.dev_label = QLabel(
            f"torch {info.get('version', 'n/a')}  •  compute device: {info.get('device', info.get('error'))}"
            + ("" if info.get("cuda") else "   ⚠ install a CUDA torch build to run on the RTX 4090"))
        self.dev_label.setStyleSheet(f"color:{PALETTE['cyan'] if info.get('cuda') else PALETTE['amber']};")
        root.addWidget(self.dev_label)

        ctl = QHBoxLayout()
        self.job_box = QComboBox()
        self.job_box.addItem("Reference training (autograd / AdamW)", "train")
        self.job_box.addItem("Ollama token stream (VRAM-governed node)", "ollama")
        self.prompt = QLineEdit("Explain a lock-free SPSC ring buffer in two sentences.")
        self.start_btn = QPushButton("▶ Start Worker")
        self.start_btn.setObjectName("Accent")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        hud_btn = QPushButton("🖥 Launch Dear PyGui HUD")
        hud_btn.clicked.connect(self._launch_hud)
        for w in (self.job_box, self.prompt, self.start_btn, self.stop_btn, hud_btn):
            ctl.addWidget(w)
        ctl.setStretch(1, 1)
        root.addLayout(ctl)

        grid = QGridLayout()
        self.k_state = MetricCard("Worker", "IDLE", "")
        self.k_step = MetricCard("Step time", "--", "")
        self.k_gflops = MetricCard("Throughput", "--", "")
        self.k_loss = MetricCard("Loss / tok/s", "--", "")
        for i, k in enumerate((self.k_state, self.k_step, self.k_gflops, self.k_loss)):
            grid.addWidget(k, 0, i)
        self.g_gpu = GaugeCard("RTX 4090 util", 80, 95)
        self.g_vram = GaugeCard("VRAM", 75, 90)
        self.g_cpu = GaugeCard("Ryzen CPU", 75, 90)
        self.g_ram = GaugeCard("RAM", 80, 92)
        for i, g in enumerate((self.g_gpu, self.g_vram, self.g_cpu, self.g_ram)):
            grid.addWidget(g, 1, i)
        root.addLayout(grid)

        mid = QHBoxLayout()
        pc = Card("Live compute plots")
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.addLegend()
        self.c_step = self.plot.plot(pen=pg.mkPen("#22d3ee", width=2), name="step ms")
        self.c_loss = self.plot.plot(pen=pg.mkPen("#e879f9", width=2), name="loss")
        pc.layout_box.addWidget(self.plot)
        mid.addWidget(pc, 3)
        rc = Card("Route / ports / log")
        self.route = QLabel("--")
        self.route.setWordWrap(True)
        self.ports = QLabel("--")
        self.ports.setWordWrap(True)
        self.ports.setStyleSheet(f"color:{PALETTE['muted']}; font-size:8pt;")
        self.log = QPlainTextEdit()
        self.log.setObjectName("Console")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        for w in (self.route, self.ports, self.log):
            rc.layout_box.addWidget(w)
        mid.addWidget(rc, 2)
        root.addLayout(mid, 1)

        hub.frame.connect(self._on_frame)  # queued: emitted from the hub thread

    # ------------------------------------------------------------------ worker
    def _start(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        if self.job_box.currentData() == "ollama":
            port = 11435 if self.hub.latest.get("shm", {}).get("compute_target", 0) >= 1 else 11434
            self.worker = AiComputeWorker(ollama_stream_job, {"port": port, "prompt": self.prompt.text()}, max_hz=30)
        else:
            self.worker = AiComputeWorker(reference_training_job, max_hz=20)
        self.worker.metrics.connect(self._on_metrics)
        self.worker.log.connect(self.log.appendPlainText)
        self.worker.state.connect(self._on_state)
        self.hub.attach_ai(lambda w=self.worker: dict(w.last))
        self._loss.clear()
        self._step.clear()
        self._tokens = ""
        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _stop(self) -> None:
        if self.worker:
            self.worker.request_stop()

    def _on_state(self, s: str) -> None:
        self.log.appendPlainText(f"[worker] {s}")
        self.k_state.set_value(s.split(":")[0].upper(), PALETTE["emerald"] if s == "running" else PALETTE["rose"] if s.startswith("error") else PALETTE["muted"], s if s.startswith("error") else "")
        if s != "running":
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_metrics(self, m: dict) -> None:
        if "token" in m:
            self._tokens += m["token"]
            self.log.setPlainText(self._tokens)
            self.k_loss.set_value(f"{m['tok_s']:.1f} tok/s", PALETTE["cyan"], f"{m['iter']} tokens")
            self.k_step.set_value("stream", sub="Ollama daemon")
            return
        self._step.append(m["step_ms"])
        self._loss.append(m["loss"])
        self.c_step.setData(list(self._step))
        self.c_loss.setData(list(self._loss))
        dev = "CUDA" if m["cuda"] else "CPU"
        self.k_state.set_value("RUNNING", PALETTE["emerald"], f"iter {m['iter']} on {dev}")
        self.k_step.set_value(f"{m['step_ms']:.2f} ms", sub=f"{dev} • VRAM alloc {m['vram_mb']:.0f} MB")
        self.k_gflops.set_value(f"{m['gflops']:.1f} GFLOPS", sub="fwd+bwd estimate")
        self.k_loss.set_value(f"{m['loss']:.4f}", sub="MSE")

    # --------------------------------------------------------------- telemetry
    def _on_frame(self, snap: dict) -> None:
        g = snap.get("gpu", {})
        if g.get("detected"):
            self.g_gpu.set_value(g["util_pct"], f"{g['util_pct']}%", f"{g['temp_c']}°C • {g.get('power_w') or 0:.0f} W • fan {g.get('fan_pct')}%")
            self.g_vram.set_value(g["vram_used_gb"] / g["vram_total_gb"] * 100, f"{g['vram_used_gb']:.1f} GB", f"of {g['vram_total_gb']:.0f} GB")
        sysd = snap.get("sys", {})
        if sysd:
            self.g_cpu.set_value(sysd["cpu_pct"])
            self.g_ram.set_value(sysd["ram_pct"], f"{sysd['ram_pct']:.0f}%", f"{sysd['ram_used_gb']:.1f}/{sysd['ram_total_gb']:.0f} GB")
        shm = snap.get("shm", {})
        if shm:
            node = "CPU node :11435 (free VRAM < 3.5 GB)" if shm.get("compute_target", 0) >= 1 else "GPU node :11434 (headroom OK)"
            self.route.setText(f"VRAM governor → inference routed to {node}")
        ports = snap.get("ports")
        if ports:
            on = [f"{p}" for p, d in ports.items() if d["online"]]
            off = [f"{p}" for p, d in ports.items() if not d["online"]]
            self.ports.setText(f"Online {len(on)}/{len(PORT_MATRIX)}: {', '.join(on) or '-'}\nOffline: {', '.join(off) or '-'}")

    def _launch_hud(self) -> None:
        if self._hud is None or self._hud.poll() is not None:
            self._hud = launch_hud()

    def shutdown(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(3000)
        if self._hud and self._hud.poll() is None:
            self._hud.terminate()
