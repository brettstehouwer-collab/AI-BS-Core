"""BLUEPRINT: PyQt6 window + background CUDA/AI thread + live telemetry + Dear PyGui HUD.

Run:  python native_studio/boilerplate_pyqt6_dpg_cuda.py

Thread / process map (no sockets, no web server anywhere):

    [GUI thread]        PyQt6 widgets only. Receives queued signals.
    [AiComputeWorker]   QThread, owns torch/CUDA. Emits ``metrics`` signals.
    [TelemetryHub]      QThread, samples NVML/psutil/ports/audio, emits ``frame``
                        and writes a named shared-memory block.
    [AudioEngine]       WASAPI Exclusive callback thread (MMCSS Pro Audio), fed by an SPSC ring.
    [dpg_hud.py]        separate process, Dear PyGui (DX11), reads the shared-memory block.

To drive your own model, write ``def my_job(ctx): yield {"iter":..., "step_ms":..., ...}``
and pass it to ``AiComputeWorker(my_job)``. Check ``ctx.stop.is_set()`` in your loop.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from native_studio.ai_compute import AiComputeWorker, reference_training_job, torch_device_info
from native_studio.dpg_hud import launch_hud
from native_studio.engine import GpuProbe
from native_studio.telemetry_hub import TelemetryHub
from native_studio.theme import STYLESHEET


class Blueprint(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI-BS Blueprint: PyQt6 + CUDA worker + Dear PyGui HUD")
        self.resize(720, 260)
        body = QWidget()
        self.setCentralWidget(body)
        lay = QVBoxLayout(body)
        self.info = QLabel(str(torch_device_info()))
        self.gpu = QLabel("GPU: --")
        self.ai = QLabel("AI: idle")
        row = QHBoxLayout()
        self.go = QPushButton("Start AI worker")
        self.hud = QPushButton("Open Dear PyGui HUD")
        row.addWidget(self.go)
        row.addWidget(self.hud)
        for w in (self.info, self.gpu, self.ai):
            lay.addWidget(w)
        lay.addLayout(row)

        # 1) telemetry thread -> GUI (queued) + shared memory
        self.hub = TelemetryHub(GpuProbe())
        self.hub.frame.connect(self.on_frame)
        self.hub.start()

        # 2) AI worker thread -> GUI (queued)
        self.worker = AiComputeWorker(reference_training_job)
        self.worker.metrics.connect(self.on_metrics)
        self.hub.attach_ai(lambda: dict(self.worker.last))  # so the HUD sees the same numbers
        self.go.clicked.connect(self.worker.start)

        # 3) HUD process
        self._hud = None
        self.hud.clicked.connect(self.open_hud)

    def on_frame(self, snap: dict) -> None:
        g = snap.get("gpu", {})
        if g.get("detected"):
            self.gpu.setText(f"GPU {g['temp_c']} C | {g['util_pct']}% | VRAM {g['vram_used_gb']:.1f}/{g['vram_total_gb']:.0f} GB")

    def on_metrics(self, m: dict) -> None:
        self.ai.setText(f"AI iter {m['iter']} | {m['step_ms']:.2f} ms | {m['gflops']:.1f} GFLOPS | loss {m['loss']:.4f} | "
                        f"{'CUDA' if m['cuda'] else 'CPU'}")

    def open_hud(self) -> None:
        if self._hud is None or self._hud.poll() is not None:
            self._hud = launch_hud()

    def closeEvent(self, e) -> None:  # noqa: ANN001
        self.worker.request_stop()
        self.worker.wait(3000)
        self.hub.shutdown()
        if self._hud and self._hud.poll() is None:
            self._hud.terminate()
        super().closeEvent(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    w = Blueprint()
    w.show()
    sys.exit(app.exec())
