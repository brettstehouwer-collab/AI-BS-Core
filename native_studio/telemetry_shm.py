"""Shared-memory telemetry frame (numpy only, no Qt) used by the Studio and the Dear PyGui HUD.

The Studio process is the single writer; the HUD process attaches read-only by name.
No sockets, no HTTP: this is a named Windows file mapping in RAM.

Layout: one float64 vector. ``seq`` is incremented before and after each write
(seqlock) so a reader can discard torn frames.
"""

from __future__ import annotations

import time
from multiprocessing import shared_memory

import numpy as np

SHM_NAME = "AIBS_NATIVE_TELEMETRY_V1"

FIELDS: tuple[str, ...] = (
    "seq", "ts",
    # GPU (NVML)
    "gpu_ok", "gpu_temp_c", "gpu_util_pct", "gpu_vram_used_gb", "gpu_vram_total_gb",
    "gpu_power_w", "gpu_power_limit_w", "gpu_fan_pct", "gpu_core_mhz", "gpu_mem_mhz",
    # Host
    "cpu_pct", "ram_pct", "ram_used_gb", "ram_total_gb",
    # Audio kernel
    "aud_running", "aud_exclusive", "aud_latency_ms", "aud_block_ms", "aud_cb_avg_ms",
    "aud_cb_max_ms", "aud_cpu_pct", "aud_underflows", "aud_bpm", "aud_step",
    # AI compute worker
    "ai_running", "ai_cuda", "ai_iter", "ai_step_ms", "ai_gflops", "ai_loss", "ai_vram_mb",
    # Ecosystem
    "ports_online", "ports_total", "ollama_gpu_online", "ollama_cpu_online", "ollama_loaded",
    "compute_target",  # 0 = GPU node :11434, 1 = CPU node :11435
    "ports_mask",      # bit i = i-th legacy PORT_ORDER slot; reserved bits stay zero
)
IDX = {name: i for i, name in enumerate(FIELDS)}
HISTORY = 240  # samples kept by readers for plots

# V1 bit positions are stable. Reserved slots are omitted from active probes/UI.
PORT_ORDER: tuple[tuple[int, str], ...] = (
    (80, "Nginx"), (3001, "Node"), (4455, "Reserved"), (5173, "Vite"), (5174, "BcastVite"),
    (8000, "Go GW"), (8001, "Chroma1"), (8002, "Chroma2"), (8005, "Bcast"), (8006, "Social"),
    (8007, "Crypto"), (8008, "Supabase"), (8010, "SHM"), (8013, "VST3"), (8055, "Directus"),
    (8080, "FastAPI"), (8085, "Bio"), (8088, "NVENC"), (8089, "HLS"), (8099, "MCP"),
    (8188, "Comfy Pri"), (8189, "Comfy"), (8888, "UE5"), (11434, "Ollama GPU"), (11435, "Ollama CPU"),
)



class TelemetryWriter:
    def __init__(self, name: str = SHM_NAME) -> None:
        size = len(FIELDS) * 8
        try:
            self.shm = shared_memory.SharedMemory(name=name, create=True, size=size)
        except FileExistsError:
            self.shm = shared_memory.SharedMemory(name=name, create=False, size=size)
        self.arr = np.ndarray((len(FIELDS),), dtype=np.float64, buffer=self.shm.buf)
        self.arr[:] = 0.0

    def write(self, values: dict[str, float]) -> None:
        a = self.arr
        a[0] += 1.0  # odd = write in progress
        for k, v in values.items():
            i = IDX.get(k)
            if i is not None and v is not None:
                a[i] = float(v)
        a[1] = time.time()
        a[0] += 1.0  # even = stable

    def close(self) -> None:
        try:
            if hasattr(self, "arr"):
                del self.arr
            if hasattr(self, "shm") and self.shm is not None:
                try:
                    self.shm.close()
                except Exception:
                    pass
                try:
                    self.shm.unlink()
                except Exception:
                    pass
                self.shm = None
        except Exception:  # noqa: BLE001
            pass


class TelemetryReader:
    def __init__(self, name: str = SHM_NAME) -> None:
        self.shm = shared_memory.SharedMemory(name=name, create=False)
        self.arr = np.ndarray((len(FIELDS),), dtype=np.float64, buffer=self.shm.buf)

    def read(self) -> dict[str, float]:
        for _ in range(8):
            s0 = self.arr[0]
            snap = self.arr.copy()
            if s0 == snap[0] and int(s0) % 2 == 0:
                return {k: float(snap[i]) for k, i in IDX.items()}
        return {k: float(self.arr[i]) for k, i in IDX.items()}

    def close(self) -> None:
        try:
            del self.arr
            self.shm.close()
        except Exception:  # noqa: BLE001
            pass
