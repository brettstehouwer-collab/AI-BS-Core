"""AI-BS Native Studio engine layer.

Everything in this module is UI-free and is executed on QThreadPool worker
threads via ``EngineBus.submit``. The GUI thread never calls these functions
directly. Results travel back to widgets through Qt signals (queued
connections), so there is no HTTP/WebSocket between the UI and AI-BS logic.

External compute engines (Ollama, ComfyUI, ChromaDB, Crypto Swarm) are still
separate daemons during Phases 1-4 and are only ever contacted from workers.
"""

from __future__ import annotations

import importlib
import os
import socket
import sqlite3
import sys
import threading
import time
import traceback
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import psutil
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, pyqtSignal, pyqtSlot

AI_BS_ROOT = Path(os.environ.get("AI_BS_ROOT", r"C:\AI-BS"))
BACKEND_DIR = AI_BS_ROOT / "backend"
TASK_TIMEOUT_S = 5400  # 90-minute ecosystem-wide ceiling

# Immutable port collision matrix (AGENTS.md section 2).
PORT_MATRIX: dict[int, tuple[str, str]] = {
    80: ("Nginx Gateway", "Edge Proxy"),
    3001: ("Node Backend", "Service Layer"),
    5173: ("Vite Dev Server (Web UI)", "Web Desktop"),
    5174: ("BroadcastStudioApp Vite", "Native Desktop App"),
    8000: ("Go Gateway", "IPC Gateway"),
    8001: ("ChromaDB Primary Vector Store", "Vector Memory"),
    8002: ("ChromaDB Secondary Mirror", "Vector Memory"),
    8005: ("Broadcast Daemon", "Broadcast Kernel"),
    8006: ("Social Hub (Twitch/IRC)", "Social Automation"),
    8007: ("Crypto Swarm & Scalp Bot", "Financial Engine"),
    8008: ("Supabase Kong Gateway", "Database Gateway"),
    8010: ("SHM Telemetry", "Shared Memory IPC"),
    8013: ("VST3 Audio Bridge", "Audio DSP"),
    8055: ("Directus Backend", "Bio-Sensor Bridge"),
    8080: ("FastAPI Core Engine", "Central Core"),
    8085: ("Ubuntu-Bio Bridge", "WSL2 Biocompute"),
    8088: ("Broadcast Kernel & NVENC", "Hardware Encoding"),
    8089: ("WSL HLS Ingest", "Stream Ingest"),
    8099: ("Gemini MCP", "MCP Infrastructure"),
    8188: ("ComfyUI Primary", "Generative Media"),
    8189: ("ComfyUI Studio", "Screenplay Diffusion"),
    8888: ("Unreal Engine Signaling", "Virtual Production"),
    11434: ("Ollama GPU Swarm (RTX 4090)", "Neural Core"),
    11435: ("Ollama CPU Embeddings Swarm", "Neural Embeddings Core"),
}


VAULT_DATABASES: dict[str, Path] = {
    "stehouwer_vault.db": BACKEND_DIR / "stehouwer_vault.db",
    "aibs_master.db": BACKEND_DIR / "aibs_master.db",
    "agent_harness_sessions.db": AI_BS_ROOT / "saved_data" / "agent_harness_sessions.db",
    "clients.db": BACKEND_DIR / "clients.db",
    "lexicon_vault.db": BACKEND_DIR / "lexicon_vault.db",
    "unreal_assets.db": BACKEND_DIR / "unreal_assets.db",
}


# ---------------------------------------------------------------------------
# Worker bus
# ---------------------------------------------------------------------------
class WorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    finished = pyqtSignal()


class Task(QRunnable):
    """A unit of background work. Never touches widgets."""

    def __init__(self, fn: Callable[..., Any], args: tuple, kwargs: dict):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = WorkerSignals()
        self.cancel_event = threading.Event()
        self.setAutoDelete(False)

    def run(self) -> None:  # executes on a pool thread
        try:
            value = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI log
            tb = traceback.format_exc(limit=3).strip().splitlines()[-1]
            try:
                self.signals.error.emit(f"{type(exc).__name__}: {exc}" if str(exc) else tb)
            except RuntimeError:
                pass
        else:
            if not self.cancel_event.is_set():
                try:
                    self.signals.result.emit(value)
                except RuntimeError:
                    pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass


class _TaskRelay(QObject):
    """GUI-owned delivery fence; workers never invoke widget callbacks."""

    def __init__(self, bus, task, generation, on_result, on_error):
        super().__init__(bus)
        self.bus, self.task, self.generation = bus, task, generation
        self.on_result, self.on_error = on_result, on_error

    def _admitted(self):
        return (self.task is not None and not self.bus._stopping
                and self.generation == self.bus._generation
                and not self.task.cancel_event.is_set())

    @pyqtSlot(object)
    def result(self, value):
        if self._admitted() and self.on_result is not None:
            self.on_result(value)

    @pyqtSlot(str)
    def error(self, message):
        if self._admitted() and self.on_error is not None:
            self.on_error(message)

    @pyqtSlot()
    def finished(self):
        if self.task is not None:
            self.bus._retire(self.task)


class EngineBus(QObject):
    """Dedicated thread pool + bookkeeping for in-flight tasks."""

    active_changed = pyqtSignal(int)
    admission_changed = pyqtSignal(object)
    drained = pyqtSignal()

    def __init__(self, max_threads: int = 8):
        super().__init__()
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(max_threads)
        self._active: set[Task] = set()
        # finished is emitted before QRunnable.run actually returns. Keep all
        # wrappers/signals alive until a real pool barrier, including clear()'s
        # queued tasks which will never emit finished.
        self._owned: dict[Task, _TaskRelay] = {}
        self._retired: set[Task] = set()
        self._generation = 0
        self._stopping = False
        self._drained = False
        self._drain_timer = QTimer(self)
        self._drain_timer.setInterval(20)
        self._drain_timer.timeout.connect(self._poll_pool_barrier)
        self._pending = deque()
        self._running: set[Task] = set()
        self._admission_configured = False
        self._admission_paused = False
        self._admission_max_workers = max_threads
        self._admission_start_interval_ms = 0
        self._admission_batch_size = 128
        self._admission_cooldown_ms = 0
        self._admission_next_start = 0.0
        self._admission_batch_started = 0
        self._admission_batch_wait = False
        self._admission_timer = QTimer(self)
        self._admission_timer.setInterval(15)
        self._admission_timer.timeout.connect(self._admit_pending)

    def admission_snapshot(self) -> dict[str, Any]:
        return {
            'max_workers': self._admission_max_workers,
            'start_interval_ms': self._admission_start_interval_ms,
            'batch_size': self._admission_batch_size,
            'batch_cooldown_ms': self._admission_cooldown_ms,
            'paused': self._admission_paused,
            'queued': len(self._pending),
            'in_flight': len(self._running),
            'active_threads': self.pool.activeThreadCount(),
            'stopping': self._stopping,
            'scope': 'All tasks submitted through this native EngineBus; external services retain their own controls.',
        }

    def _admission_changed(self) -> None:
        self.admission_changed.emit(self.admission_snapshot())

    def _withdraw_pool_queue(self) -> None:
        # Preserve the legacy immediate QThreadPool admission until controls are
        # explicitly used. On activation, recover only jobs tryTake proves have
        # not started. Running callables are never interrupted.
        withdrawn = []
        for task in self._owned:
            if task in self._running and self.pool.tryTake(task):
                self._running.discard(task)
                withdrawn.append(task)
        self._pending = deque([*withdrawn, *self._pending])

    def configure_admission(self, max_workers: int, start_interval_ms: int = 0,
                            batch_size: int = 128, batch_cooldown_ms: int = 0) -> None:
        for name, value, lower, upper in (
            ('max_workers', max_workers, 1, 64),
            ('start_interval_ms', start_interval_ms, 0, 3600000),
            ('batch_size', batch_size, 1, 4096),
            ('batch_cooldown_ms', batch_cooldown_ms, 0, 3600000),
        ):
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError(f'{name} is outside its bounded range')
        if self._stopping:
            raise RuntimeError('EngineBus is shutting down')
        self._admission_configured = True
        self._withdraw_pool_queue()
        self._admission_max_workers = max_workers
        self._admission_start_interval_ms = start_interval_ms
        self._admission_batch_size = batch_size
        self._admission_cooldown_ms = batch_cooldown_ms
        self.pool.setMaxThreadCount(max_workers)
        if self._admission_batch_started >= batch_size:
            self._admission_batch_wait = True
        self._admit_pending()

    def pause_admission(self) -> None:
        if self._stopping:
            return
        self._admission_configured = True
        self._admission_paused = True
        self._withdraw_pool_queue()
        self._admission_timer.stop()
        self._admission_changed()

    def resume_admission(self) -> None:
        if not self._stopping:
            self._admission_paused = False
            self._admit_pending()

    def cancel_pending(self) -> int:
        self._admission_configured = True
        self._withdraw_pool_queue()
        count = 0
        while self._pending:
            task = self._pending.popleft()
            task.cancel_event.set()
            self._active.discard(task)
            self._retired.add(task)
            count += 1
        self._admission_timer.stop()
        self.active_changed.emit(len(self._active))
        self._admission_changed()
        self._poll_pool_barrier()
        return count

    @pyqtSlot()
    def _admit_pending(self) -> None:
        if self._stopping or self._admission_paused:
            self._admission_timer.stop()
            return
        now = time.monotonic()
        if (self._admission_batch_wait and not self._running
                and self.pool.waitForDone(0)):
            self._admission_batch_wait = False
            self._admission_batch_started = 0
            self._admission_next_start = max(
                self._admission_next_start, now + self._admission_cooldown_ms / 1000)
        while self._pending:
            if self._admission_configured and (
                    len(self._running) >= self._admission_max_workers
                    or self._admission_batch_wait or now < self._admission_next_start):
                break
            task = self._pending.popleft()
            if task.cancel_event.is_set():
                self._active.discard(task)
                self._retired.add(task)
                self.active_changed.emit(len(self._active))
                continue
            self._running.add(task)
            self.pool.start(task)
            self._admission_batch_started += 1
            if self._admission_configured:
                self._admission_next_start = now + self._admission_start_interval_ms / 1000
                if self._admission_batch_started >= self._admission_batch_size:
                    self._admission_batch_wait = True
                now = time.monotonic()
        if self._pending:
            self._admission_timer.start()
        else:
            self._admission_timer.stop()
        if self._retired:
            self._poll_pool_barrier()
        self._admission_changed()

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_result: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> Task:
        if self._stopping:
            raise RuntimeError('EngineBus is shutting down; new work is not admitted')
        if len(self._active) >= 4096:
            raise RuntimeError('Native background queue is full')
        task = Task(fn, args, kwargs)
        relay = _TaskRelay(self, task, self._generation, on_result, on_error)
        task.signals.result.connect(relay.result, Qt.ConnectionType.QueuedConnection)
        task.signals.error.connect(relay.error, Qt.ConnectionType.QueuedConnection)
        task.signals.finished.connect(relay.finished, Qt.ConnectionType.QueuedConnection)
        self._owned[task] = relay
        self._active.add(task)
        self.active_changed.emit(len(self._active))
        self._pending.append(task)
        self._admit_pending()
        return task

    def dispatch(
        self,
        fn: Callable[..., Any],
        *args: Any,
        callback: Callable[[Any], None] | None = None,
        on_result: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> Task:
        return self.submit(fn, *args, on_result=callback or on_result, on_error=on_error, **kwargs)

    def _retire(self, task: Task) -> None:
        self._active.discard(task)
        self._running.discard(task)
        self._retired.add(task)
        self.active_changed.emit(len(self._active))
        self._poll_pool_barrier()
        self._admit_pending()

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def is_drained(self) -> bool:
        return self._drained

    def _release(self, tasks) -> None:
        for task in list(tasks):
            relay = self._owned.pop(task, None)
            self._retired.discard(task)
            if relay is None:
                continue
            for signal, slot in ((task.signals.result, relay.result),
                                 (task.signals.error, relay.error),
                                 (task.signals.finished, relay.finished)):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
            # Already posted Qt events can outlive disconnect. Make the receiver
            # inert before deferred QObject deletion on its owning GUI thread.
            relay.task = relay.on_result = relay.on_error = None
            relay.deleteLater()

    def _complete_stop(self) -> None:
        if self._drained:
            return
        self._drain_timer.stop()
        self._admission_timer.stop()
        self._release(self._owned)
        self._active.clear()
        self._pending.clear()
        self._running.clear()
        self._drained = True
        self.active_changed.emit(0)
        self._admission_changed()
        self.drained.emit()

    @pyqtSlot()
    def _poll_pool_barrier(self) -> None:
        if self._drained:
            return
        if self.pool.waitForDone(0):
            if self._stopping:
                self._complete_stop()
            else:
                self._release(self._retired)
                self._drain_timer.stop()
        elif self._stopping or self._retired:
            self._drain_timer.start()

    def shutdown(self, timeout_ms: int = 3000) -> bool:
        """Request stop once; True requires a real native pool join.

        Use timeout_ms=0 on the window-close path and retain this bus/window
        while False is returned. The GUI timer emits drained after work returns.
        Cancellation never forcibly terminates a callable.
        """
        if not isinstance(timeout_ms, int) or timeout_ms < 0:
            raise ValueError('EngineBus shutdown requires a bounded nonnegative timeout')
        if self._drained:
            return True
        if not self._stopping:
            self._stopping = True
            self._admission_timer.stop()
            self._pending.clear()
            self._generation += 1
            for task in self._owned:
                task.cancel_event.set()
            self.pool.clear()
        if self.pool.waitForDone(timeout_ms):
            self._complete_stop()
            return True
        self._drain_timer.start()
        return False


# ---------------------------------------------------------------------------
# System + GPU telemetry
# ---------------------------------------------------------------------------
def sample_system() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    disks = []
    for root in ("C:\\", "D:\\", "E:\\"):
        try:
            u = psutil.disk_usage(root)
            disks.append({"drive": root[:2], "total_gb": u.total / 1024**3, "free_gb": u.free / 1024**3,
                          "used_pct": u.percent, "online": True})
        except OSError:
            disks.append({"drive": root[:2], "online": False})
    return {
        "ts": time.time(),
        "cpu_pct": psutil.cpu_percent(interval=None),
        "cpu_per_core": psutil.cpu_percent(interval=None, percpu=True),
        "ram_total_gb": vm.total / 1024**3,
        "ram_used_gb": (vm.total - vm.available) / 1024**3,
        "ram_pct": vm.percent,
        "disks": disks,
    }


def top_processes(limit: int = 10) -> list[dict[str, Any]]:
    rows = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        mi = p.info.get("memory_info")
        if mi is None:
            continue
        rows.append({"pid": p.info["pid"], "name": p.info.get("name") or "?", "rss_gb": mi.rss / 1024**3})
    rows.sort(key=lambda r: r["rss_gb"], reverse=True)
    return rows[:limit]


class GpuProbe:
    """Direct NVML binding (nvml.dll) for the RTX 4090. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.ok = False
        self.error: str | None = None
        self._h = None
        try:
            import pynvml

            self.nv = pynvml
            pynvml.nvmlInit()
            self._h = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.ok = True
        except Exception as exc:  # noqa: BLE001
            self.error = f"NVML unavailable: {exc}"

    @staticmethod
    def _safe(fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Exception:  # noqa: BLE001
            return None

    def sample(self) -> dict[str, Any]:
        if not self.ok:
            return {"detected": False, "error": self.error}
        nv, h = self.nv, self._h
        with self._lock:
            mem = nv.nvmlDeviceGetMemoryInfo(h)
            util = nv.nvmlDeviceGetUtilizationRates(h)
            name = nv.nvmlDeviceGetName(h)
            driver = self._safe(nv.nvmlSystemGetDriverVersion)
            return {
                "detected": True,
                "name": name.decode() if isinstance(name, bytes) else name,
                "driver": driver.decode() if isinstance(driver, bytes) else driver,
                "temp_c": nv.nvmlDeviceGetTemperature(h, nv.NVML_TEMPERATURE_GPU),
                "util_pct": util.gpu,
                "vram_total_gb": mem.total / 1024**3,
                "vram_used_gb": mem.used / 1024**3,
                "power_w": self._safe(lambda: nv.nvmlDeviceGetPowerUsage(h) / 1000.0),
                "power_limit_w": self._safe(lambda: nv.nvmlDeviceGetEnforcedPowerLimit(h) / 1000.0),
                "fan_pct": self._safe(lambda: nv.nvmlDeviceGetFanSpeed(h)),
                "core_mhz": self._safe(lambda: nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_GRAPHICS)),
                "mem_mhz": self._safe(lambda: nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_MEM)),
            }

    def set_fans(self, percent: int | None) -> str:
        """percent=None restores the driver auto curve. Requires elevation."""
        if not self.ok:
            raise RuntimeError(self.error or "NVML unavailable")
        nv, h = self.nv, self._h
        with self._lock:
            count = nv.nvmlDeviceGetNumFans(h)
            try:
                for i in range(count):
                    if percent is None:
                        nv.nvmlDeviceSetDefaultFanSpeed_v2(h, i)
                    else:
                        nv.nvmlDeviceSetFanSpeed_v2(h, i, int(percent))
            except nv.NVMLError as exc:
                raise RuntimeError(f"{exc} (fan control needs AI_BS_Studio to run as Administrator)") from exc
        return f"Auto fan curve restored on {count} fan(s)" if percent is None else f"Locked {count} fan(s) at {percent}%"


# ---------------------------------------------------------------------------
# Port matrix + Matrix Doctor (in-process)
# ---------------------------------------------------------------------------
def _probe(port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _listen_owners() -> dict[int, int]:
    owners: dict[int, int] = {}
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.status == psutil.CONN_LISTEN and c.laddr and c.pid:
                owners.setdefault(c.laddr.port, c.pid)
    except (psutil.AccessDenied, PermissionError):
        pass
    return owners


def probe_ports() -> dict[int, dict[str, Any]]:
    ports = list(PORT_MATRIX)
    with ThreadPoolExecutor(max_workers=len(ports)) as ex:
        online = dict(zip(ports, ex.map(_probe, ports)))
    owners = _listen_owners()
    out: dict[int, dict[str, Any]] = {}
    for port in ports:
        name, category = PORT_MATRIX[port]
        pid = owners.get(port)
        proc = None
        if pid:
            try:
                proc = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc = None
        out[port] = {"name": name, "category": category, "online": online[port], "pid": pid, "process": proc}
    return out


def _load_backend_module(name: str):
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    return importlib.import_module(name)


def run_matrix_doctor_heal() -> Any:
    return _load_backend_module("aibs_matrix_doctor").heal_ecosystem()


# ---------------------------------------------------------------------------
# Ollama fleet (external engine until Phase 4.5 brings llama.cpp in-process)
# ---------------------------------------------------------------------------
def ollama_inventory(port: int) -> dict[str, Any]:
    import httpx

    base = f"http://127.0.0.1:{port}"
    with httpx.Client(timeout=httpx.Timeout(6.0, connect=1.5)) as client:
        tags = client.get(f"{base}/api/tags").json().get("models", [])
        try:
            loaded = client.get(f"{base}/api/ps").json().get("models", [])
        except Exception:  # noqa: BLE001
            loaded = []
    models = []
    for m in tags:
        d = m.get("details") or {}
        models.append({
            "name": m.get("name", "?"),
            "size_gb": (m.get("size") or 0) / 1024**3,
            "family": d.get("family", ""),
            "params": d.get("parameter_size", ""),
            "quant": d.get("quantization_level", ""),
            "modified": (m.get("modified_at") or "")[:19].replace("T", " "),
        })
    models.sort(key=lambda r: r["name"])
    running = [{
        "name": m.get("name", "?"),
        "vram_gb": (m.get("size_vram") or 0) / 1024**3,
        "size_gb": (m.get("size") or 0) / 1024**3,
        "expires": (m.get("expires_at") or "")[:19].replace("T", " "),
    } for m in loaded]
    return {"port": port, "models": models, "loaded": running}


def ollama_unload(port: int, model: str) -> str:
    import httpx

    with httpx.Client(timeout=httpx.Timeout(60.0, connect=1.5)) as client:
        r = client.post(f"http://127.0.0.1:{port}/api/generate", json={"model": model, "keep_alive": 0})
        r.raise_for_status()
    return f"Unloaded {model} from port {port}"


# ---------------------------------------------------------------------------
# SQLite vaults (read-only, WAL-safe)
# ---------------------------------------------------------------------------
def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _ro_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True, timeout=5)
    conn.execute("PRAGMA query_only = ON")
    return conn


def list_tables(db_path: Path) -> list[tuple[str, int]]:
    conn = _ro_connect(db_path)
    try:
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        out = []
        for n in names:
            try:
                out.append((n, conn.execute(f"SELECT COUNT(*) FROM {quote_ident(n)}").fetchone()[0]))
            except sqlite3.Error:
                out.append((n, -1))
        return out
    finally:
        conn.close()


def fetch_page(db_path: Path, table: str, offset: int = 0, limit: int = 200,
               search: str | None = None) -> dict[str, Any]:
    conn = _ro_connect(db_path)
    try:
        q = quote_ident(table)
        info = conn.execute(f"PRAGMA table_info({q})").fetchall()
        columns = [r[1] for r in info]
        where, params = "", []
        if search:
            text_cols = [r[1] for r in info
                         if not r[2] or any(t in r[2].upper() for t in ("TEXT", "CHAR", "CLOB", "JSON"))]
            if text_cols:
                where = " WHERE " + " OR ".join(f"{quote_ident(c)} LIKE ?" for c in text_cols)
                params = [f"%{search}%"] * len(text_cols)
        rows = conn.execute(f"SELECT * FROM {q}{where} LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
        total = None if search else conn.execute(f"SELECT COUNT(*) FROM {q}").fetchone()[0]
        return {"table": table, "columns": columns, "rows": rows, "offset": offset, "limit": limit,
                "total": total, "search": search}
    finally:
        conn.close()
