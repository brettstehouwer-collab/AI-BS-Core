"""In-process live telemetry hub.

One sampler thread aggregates everything the ecosystem already measures and
publishes it two ways, both local to the machine's RAM:

1. ``frame`` Qt signal  -> PyQt6 widgets (queued connection, GUI thread consumes).
2. named shared memory  -> the Dear PyGui HUD process (``dpg_hud.py``).

Sources (all pre-existing AI-BS components, called directly, no HTTP):
* ``engine.GpuProbe``          NVML: temp / util / VRAM / power / fan / clocks
* ``engine.sample_system``     psutil: CPU, RAM
* ``engine.probe_ports``       the active service collision matrix
* ``engine.ollama_inventory``  loaded models on :11434 / :11435
* ``audio_kernel.AudioEngine`` measured WASAPI latency / callback timing
* ``ai_compute.AiComputeWorker`` live iteration time, GFLOPS, loss

Compute-node routing mirrors ``backend/core/vram_resource_arbiter.check_compute_target``
(free VRAM < 3.5 GB -> CPU node :11435) but uses real NVML numbers. The arbiter's own
``get_vram_telemetry`` returns a hard-coded 24 GB profile when torch has no CUDA, so it is
deliberately not used as a data source here.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal

from native_studio.engine import PORT_MATRIX, GpuProbe, ollama_inventory, probe_ports, sample_system
from native_studio.telemetry_shm import PORT_ORDER, TelemetryWriter

if tuple(p for p, _ in PORT_ORDER if p != 4455) != tuple(PORT_MATRIX):
    raise RuntimeError("telemetry_shm.PORT_ORDER drifted from engine.PORT_MATRIX")

MIN_FREE_VRAM_GB = 3.5


class TelemetryHub(QThread):
    frame = pyqtSignal(dict)

    def __init__(self, gpu_probe: GpuProbe, hz: float = 4.0, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.gpu = gpu_probe
        self.period = 1.0 / hz
        self._stop = threading.Event()
        self._audio: Any = None
        self._ai_last: Callable[[], dict[str, Any]] | None = None
        self.writer: TelemetryWriter | None = None
        self.latest: dict[str, Any] = {}

    def attach_audio(self, engine: Any) -> None:
        self._audio = engine

    def attach_ai(self, last_metrics: Callable[[], dict[str, Any]]) -> None:
        self._ai_last = last_metrics

    def shutdown(self, timeout_ms: int = 2000) -> bool:
        """Request a stop and report whether the bounded drain completed.

        The sampling thread owns the mapping through its final write. Callers
        must retain this QThread while False is returned and defer window
        destruction until it finishes; closing the mapping here would race a
        sampler still waiting on a local service or hardware read.
        Pass timeout_ms=0 from the GUI close coordinator to keep it responsive;
        the legacy default remains 2000ms for other callers.
        """
        if not isinstance(timeout_ms, int) or timeout_ms < 0:
            raise ValueError('Sampler shutdown requires a bounded nonnegative timeout')
        self._stop.set()
        return bool(self.wait(timeout_ms))

    def run(self) -> None:
        try:
            self._sample_until_stopped()
        except Exception as exc:  # A Qt worker exception must not abort the UI.
            self._stop.set()
            self.latest = {
                "ts": time.time(),
                "telemetry_available": False,
                "error_type": type(exc).__name__,
            }
            try:
                self.frame.emit(self.latest)
            except Exception:
                pass
        finally:
            writer = self.writer
            self.writer = None
            if writer is not None:
                try:
                    writer.close()
                except Exception:
                    pass

    def _sample_until_stopped(self) -> None:
        if self._stop.is_set():
            return
        self.writer = TelemetryWriter()
        ports_cache: dict[int, dict[str, Any]] = {}
        ports_ts = ollama_ts = 0.0
        ollama_loaded = 0
        order = [port for port, _ in PORT_ORDER]  # preserve the V1 mask ABI
        while not self._stop.is_set():
            t0 = time.time()
            v: dict[str, float] = {}
            snap: dict[str, Any] = {"ts": t0}
            try:
                g = self.gpu.sample()
                snap["gpu"] = g
                if g.get("detected"):
                    free = g["vram_total_gb"] - g["vram_used_gb"]
                    v.update(gpu_ok=1, gpu_temp_c=g["temp_c"], gpu_util_pct=g["util_pct"],
                             gpu_vram_used_gb=g["vram_used_gb"], gpu_vram_total_gb=g["vram_total_gb"],
                             gpu_power_w=g.get("power_w") or 0, gpu_power_limit_w=g.get("power_limit_w") or 0,
                             gpu_fan_pct=g.get("fan_pct") or 0, gpu_core_mhz=g.get("core_mhz") or 0,
                             gpu_mem_mhz=g.get("mem_mhz") or 0,
                             compute_target=0.0 if free >= MIN_FREE_VRAM_GB else 1.0)
            except Exception as exc:  # noqa: BLE001
                snap["gpu"] = {"detected": False, "error": str(exc)}
            try:
                s = sample_system()
                snap["sys"] = s
                v.update(cpu_pct=s["cpu_pct"], ram_pct=s["ram_pct"], ram_used_gb=s["ram_used_gb"],
                         ram_total_gb=s["ram_total_gb"])
            except Exception:  # noqa: BLE001
                pass
            if t0 - ports_ts > 5.0:
                ports_ts = t0
                try:
                    ports_cache = probe_ports()
                except Exception:  # noqa: BLE001
                    pass
            if ports_cache:
                mask = sum(1 << i for i, p in enumerate(order) if p in PORT_MATRIX and ports_cache.get(p, {}).get("online"))
                v.update(ports_online=bin(mask).count("1"), ports_total=len(PORT_MATRIX), ports_mask=mask,
                         ollama_gpu_online=1 if ports_cache.get(11434, {}).get("online") else 0,
                         ollama_cpu_online=1 if ports_cache.get(11435, {}).get("online") else 0)
                snap["ports"] = {port: state for port, state in ports_cache.items() if port in PORT_MATRIX}
                if t0 - ollama_ts > 10.0 and ports_cache.get(11434, {}).get("online"):
                    ollama_ts = t0
                    try:
                        ollama_loaded = len(ollama_inventory(11434)["loaded"])
                    except Exception:  # noqa: BLE001
                        pass
                v["ollama_loaded"] = ollama_loaded
            if self._audio is not None:
                a = self._audio.stats()
                v.update(aud_running=1 if a.mode.startswith("WASAPI") else 0, aud_exclusive=1 if a.exclusive else 0,
                         aud_latency_ms=a.reported_latency_ms, aud_block_ms=a.block_ms, aud_cb_avg_ms=a.cb_avg_ms,
                         aud_cb_max_ms=a.cb_max_ms, aud_cpu_pct=a.cpu_load, aud_underflows=a.underflows,
                         aud_bpm=self._audio.bpm, aud_step=self._audio.play_step)
                snap["audio"] = a
            if self._ai_last is not None:
                m = self._ai_last() or {}
                if m:
                    v.update(ai_running=1, ai_cuda=1 if m.get("cuda") else 0, ai_iter=m.get("iter", 0),
                             ai_step_ms=m.get("step_ms", 0), ai_gflops=m.get("gflops", 0),
                             ai_loss=m.get("loss", 0), ai_vram_mb=m.get("vram_mb", 0))
                else:
                    v["ai_running"] = 0
                snap["ai"] = m
            self.writer.write(v)
            snap["shm"] = v
            self.latest = snap
            self.frame.emit(snap)
            self._stop.wait(max(0.0, self.period - (time.time() - t0)))
