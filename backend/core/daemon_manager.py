"""
daemon_manager.py — Centralized supervisor for all AI-BS background daemons.

Features
--------
- Spawns daemons as non-blocking child processes (CREATE_NEW_PROCESS_GROUP on Windows).
- Uses psutil for reliable cross-platform health checks.
- Runs a watchdog thread that detects crashes and auto-restarts within a
  configurable backoff policy.
- Provides a clean shutdown interface consumed by FastAPI lifespan hooks
  and the unified launcher.
- Writes authoritative .pid files; prevents zombie double-starts by checking
  both the in-memory registry AND the on-disk pid file.
- Sets DAEMON_MANAGER_OWNED=1 in the child environment so daemons know they
  are supervised and can skip their own PID-file self-write logic.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from core.tool_schemas import ShellCommand
import psutil

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WATCHDOG_INTERVAL: float = float(os.getenv("DAEMON_WATCHDOG_INTERVAL", "5"))  # seconds
MAX_RESTART_ATTEMPTS: int = int(os.getenv("DAEMON_MAX_RESTARTS", "5"))
RESTART_BACKOFF_BASE: float = float(os.getenv("DAEMON_RESTART_BACKOFF", "3"))  # seconds


# ---------------------------------------------------------------------------
# Internal data structure for a managed daemon
# ---------------------------------------------------------------------------


@dataclass
class _ManagedDaemon:
    name: str
    cmd: ShellCommand
    proc: Optional[subprocess.Popen] = field(default=None, repr=False)
    restart_count: int = 0
    last_restart_at: float = 0.0
    enabled: bool = True  # set to False to permanently disable auto-restart
    port: Optional[int] = None
    category: str = "static"  # "static" or "jit"
    vram_mb_estimate: int = 0


# Immutable 18-Port Ecosystem Topology Matrix
ECOSYSTEM_PORTS = [
    {"port": 80, "name": "Nginx Gateway", "tier": "network", "category": "static"},
    {"port": 3001, "name": "Node Backend", "tier": "backend", "category": "static"},
    {"port": 4455, "name": "OBS WebSocket", "tier": "streaming", "category": "jit"},
    {"port": 5173, "name": "Vite Dev & Studio", "tier": "frontend", "category": "static"},
    {"port": 8000, "name": "Go Gateway", "tier": "gateway", "category": "static"},
    {"port": 8002, "name": "ChromaDB Store", "tier": "database", "category": "static"},
    {"port": 8005, "name": "Broadcast Daemon", "tier": "streaming", "category": "static"},
    {"port": 8006, "name": "Social Hub (Twitch/IRC)", "tier": "social", "category": "jit"},
    {"port": 8007, "name": "Crypto Swarm & Scalp Bot", "tier": "trading", "category": "static"},
    {"port": 8010, "name": "SHM Telemetry Gateway", "tier": "telemetry", "category": "static"},
    {"port": 8013, "name": "VST3 Audio Bridge", "tier": "audio", "category": "jit"},
    {"port": 8080, "name": "FastAPI Core Engine", "tier": "core", "category": "static"},
    {"port": 8085, "name": "Ubuntu-Bio Bridge", "tier": "bridge", "category": "jit"},
    {"port": 8088, "name": "Broadcast Kernel & NVENC", "tier": "video", "category": "jit"},
    {"port": 8089, "name": "WSL HLS Ingest", "tier": "streaming", "category": "jit"},
    {"port": 8099, "name": "Gemini Local MCP", "tier": "ai", "category": "static"},
    {"port": 8189, "name": "ComfyUI (RTX 4090)", "tier": "diffusion", "category": "jit"},
    {"port": 8888, "name": "Unreal Engine Signaling", "tier": "rendering", "category": "jit"},
    {"port": 11434, "name": "Ollama Host", "tier": "llm", "category": "jit"},
    {"port": 11435, "name": "Ollama E-Drive", "tier": "llm", "category": "jit"},
]


# ---------------------------------------------------------------------------
# DaemonManager
# ---------------------------------------------------------------------------


class DaemonManager:
    """
    Central supervisor for AI-BS background daemons.

    Usage (typical FastAPI lifespan pattern)
    ----------------------------------------
        manager = DaemonManager()
        manager.register("trainer_daemon", [sys.executable, "trainer_daemon.py"])

        @asynccontextmanager
        async def lifespan(app):
            manager.start_all()
            yield
            manager.stop_all()

        app = FastAPI(lifespan=lifespan)
    """

    def __init__(self, base_dir: str | None = None):
        self.base_dir: Path = Path(base_dir or os.path.dirname(__file__)).resolve()
        self._daemons: Dict[str, _ManagedDaemon] = {}
        self._lock: threading.RLock = threading.RLock()
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._listeners: list = []

    # ------------------------------------------------------------------
    # Public registration & listener API
    # ------------------------------------------------------------------

    def register_listener(self, cb) -> None:
        """Register a callback (event_type, daemon_name, payload) for state change events."""
        with self._lock:
            if cb not in self._listeners:
                self._listeners.append(cb)

    def _notify_listeners(self, event_type: str, daemon_name: str, payload: dict | None = None) -> None:
        listeners = []
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event_type, daemon_name, payload or {})
            except Exception as e:
                logger.warning("DaemonManager listener error: %s", e)

    def register(
        self,
        name: str,
        cmd: ShellCommand,
        auto_start: bool = True,
        port: Optional[int] = None,
        category: str = "static",
        vram_mb_estimate: int = 0,
    ) -> None:
        """Register a daemon so it can be managed. Must be called before start_all()."""
        with self._lock:
            if name in self._daemons:
                logger.warning(
                    "DaemonManager: '%s' already registered — skipping.", name
                )
                return
            self._daemons[name] = _ManagedDaemon(
                name=name,
                cmd=cmd,
                enabled=auto_start,
                port=port,
                category=category,
                vram_mb_estimate=vram_mb_estimate,
            )
            logger.debug(
                "DaemonManager: registered daemon '%s' (port=%s, category=%s).",
                name,
                port,
                category,
            )

    # ------------------------------------------------------------------
    # Pre-flight Port Reclamation & Cleanup
    # ------------------------------------------------------------------

    @staticmethod
    def reclaim_ports(ports: list[int]) -> int:
        """
        Scans system for processes listening on target ports and gracefully terminates them.
        Returns total number of orphan/zombie processes terminated.
        """
        terminated_count = 0
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port in ports and conn.pid:
                    try:
                        p = psutil.Process(conn.pid)
                        if p.pid == os.getpid():
                            continue
                        logger.warning(
                            "DaemonManager: Reclaiming port %d occupied by PID %d (%s)...",
                            conn.laddr.port,
                            p.pid,
                            p.name(),
                        )
                        p.terminate()
                        try:
                            p.wait(timeout=2)
                        except psutil.TimeoutExpired:
                            p.kill()
                        terminated_count += 1
                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        psutil.ZombieProcess,
                    ):
                        pass
        except Exception as e:
            logger.warning("DaemonManager: Pre-flight port sweep error: %s", e)
        return terminated_count

    # ------------------------------------------------------------------
    # Lifecycle: start / stop
    # ------------------------------------------------------------------

    def start_all(self, target_ports: list[int] | None = None) -> None:
        """Spawn all registered daemons and begin watchdog supervision."""
        if target_ports:
            self.reclaim_ports(target_ports)
        logger.info(
            "DaemonManager: starting all daemons (%d registered).", len(self._daemons)
        )
        with self._lock:
            for daemon in self._daemons.values():
                if daemon.enabled:
                    self._spawn(daemon)
        self._start_watchdog()

    def stop_all(self, timeout: float = 8.0) -> None:
        """
        Signal the watchdog to stop, then gracefully terminate all daemons.
        Falls back to SIGKILL / TerminateProcess if the process doesn't exit.
        """
        logger.info("DaemonManager: initiating graceful shutdown of all daemons.")
        self._stop_event.set()
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=5)

        with self._lock:
            for daemon in list(self._daemons.values()):
                self._terminate(daemon, timeout=timeout)

    def start_daemon(self, name: str) -> bool:
        """Start a single registered daemon by name. Returns True on success."""
        with self._lock:
            daemon = self._daemons.get(name)
            if not daemon:
                logger.error("DaemonManager: no daemon registered as '%s'.", name)
                return False
            daemon.enabled = True
            return self._spawn(daemon)

    def restart_daemon(self, name: str, timeout: float = 5.0) -> bool:
        """Restart a single registered daemon by name. Returns True on success."""
        with self._lock:
            daemon = self._daemons.get(name)
            if not daemon:
                logger.error("DaemonManager: no daemon registered as '%s'.", name)
                return False
            self._terminate(daemon, timeout=timeout)
            daemon.enabled = True
            return self._spawn(daemon)

    def stop_daemon(self, name: str, timeout: float = 8.0) -> bool:
        """Stop a single running daemon by name. Returns True on success."""
        with self._lock:
            daemon = self._daemons.get(name)
            if not daemon:
                logger.error("DaemonManager: no daemon registered as '%s'.", name)
                return False
            daemon.enabled = False  # prevent watchdog from restarting it
            return self._terminate(daemon, timeout=timeout)

    def restart_daemon(self, name: str) -> bool:
        """Stop and re-spawn a named daemon."""
        self.stop_daemon(name)
        with self._lock:
            daemon = self._daemons.get(name)
            if not daemon:
                return False
            daemon.enabled = True
            daemon.restart_count = 0
            return self._spawn(daemon)

    # ------------------------------------------------------------------
    # Status / health
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, dict]:
        """
        Return a dict of name → {running, pid, restart_count} for all daemons.
        """
        out = {}
        with self._lock:
            for name, daemon in self._daemons.items():
                alive = self._is_alive(daemon)
                out[name] = {
                    "running": alive,
                    "pid": daemon.proc.pid if daemon.proc and alive else None,
                    "restart_count": daemon.restart_count,
                    "enabled": daemon.enabled,
                }
        return out

    def health_check(self) -> Dict[str, bool]:
        """Quick {name: alive} map — suitable for a /health API endpoint."""
        with self._lock:
            return {name: self._is_alive(d) for name, d in self._daemons.items()}

    @staticmethod
    def check_hardware_thermal_throttle(threshold_celsius: float = 82.0) -> bool:
        """Check whether system temperatures exceed safe GPU/CPU operating threshold."""
        if psutil and hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for _name, entries in temps.items():
                        for entry in entries:
                            if entry.current > threshold_celsius:
                                return True
            except Exception:
                pass
        return False

    @staticmethod
    def get_hardware_metrics() -> dict:
        """Inspect CPU, RAM, and NVIDIA RTX 4090 VRAM metrics."""
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=None) if psutil else 0.0,
            "ram_percent": psutil.virtual_memory().percent if psutil else 0.0,
            "gpu": {
                "vram_used_mb": 0,
                "vram_total_mb": 24576,
                "name": "NVIDIA GeForce RTX 4090 (24GB VRAM)",
                "temp_c": 0.0,
            }
        }
        try:
            import torch
            if torch.cuda.is_available():
                metrics["gpu"]["vram_used_mb"] = int(torch.cuda.memory_allocated(0) / (1024 * 1024))
                metrics["gpu"]["vram_total_mb"] = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
                metrics["gpu"]["name"] = torch.cuda.get_device_name(0)
        except Exception:
            pass
        return metrics

    def get_full_ecosystem_status(self) -> dict:
        """
        Inspect all 18 collision-free ports across the host system and return
        authoritative PID, process name, RSS memory, and operational status.
        """
        active_sockets: Dict[int, int] = {}
        if psutil:
            try:
                for conn in psutil.net_connections(kind="inet"):
                    if conn.status == "LISTEN" or (os.name == "nt" and conn.laddr and conn.laddr.port):
                        port = conn.laddr.port
                        if conn.pid and port in [p["port"] for p in ECOSYSTEM_PORTS]:
                            if port not in active_sockets:
                                active_sockets[port] = conn.pid
            except Exception as e:
                logger.debug("DaemonManager net_connections sweep warning: %s", e)

        ports_status = []
        online_count = 0
        for ep in ECOSYSTEM_PORTS:
            port = ep["port"]
            pid = active_sockets.get(port)
            proc_name = None
            mem_mb = 0.0
            is_online = False

            if pid and psutil and psutil.pid_exists(pid):
                try:
                    p = psutil.Process(pid)
                    proc_name = p.name()
                    mem_mb = round(p.memory_info().rss / (1024 * 1024), 1)
                    is_online = True
                    online_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Check if this port is supervised in registered daemons
            supervised = False
            daemon_name = None
            with self._lock:
                for d_name, d in self._daemons.items():
                    if d.port == port:
                        supervised = True
                        daemon_name = d_name
                        break

            ports_status.append({
                "port": port,
                "name": ep["name"],
                "tier": ep["tier"],
                "category": ep["category"],
                "status": "ONLINE" if is_online else "OFFLINE",
                "pid": pid if is_online else None,
                "process_name": proc_name,
                "memory_mb": mem_mb,
                "supervised": supervised,
                "daemon_name": daemon_name,
            })

        hw_metrics = self.get_hardware_metrics()

        return {
            "version": "v5.266.0",
            "timestamp": time.time(),
            "online_ports": online_count,
            "total_ports": len(ECOSYSTEM_PORTS),
            "ports": ports_status,
            "hardware": hw_metrics,
            "registered_daemons_count": len(self._daemons),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _spawn(self, daemon: _ManagedDaemon) -> bool:
        """
        Spawn a daemon subprocess. Guards against double-starts by checking:
          1. In-memory Popen object is still alive.
          2. On-disk .pid file points to a live process.
        """
        # Guard 1: in-memory check
        if self._is_alive(daemon):
            logger.warning(
                "DaemonManager: '%s' is already running (PID %d).",
                daemon.name,
                daemon.proc.pid,
            )
            return False

        # Guard 2: stale pid-file check (check both base_dir and state_dir)
        state_dir = self.base_dir.parent / "state"
        possible_pid_paths = [
            self._pid_path(daemon.name),
            state_dir / f"{daemon.name}.pid",
        ]
        for p_path in possible_pid_paths:
            if p_path.exists():
                try:
                    stale_pid = int(p_path.read_text().strip())
                    if psutil.pid_exists(stale_pid):
                        try:
                            proc = psutil.Process(stale_pid)
                            if "python" in proc.name().lower():
                                logger.warning(
                                    "DaemonManager: '%s' already running externally from pid file (PID %d). Adopting existing process.",
                                    daemon.name, stale_pid
                                )
                                daemon.proc = _AdoptedProcess(stale_pid)
                                return True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (ValueError, OSError):
                    pass
                try:
                    p_path.unlink(missing_ok=True)
                except Exception:
                    pass

        # Guard 3: Dynamic psutil query by script name
        if psutil:
            script_name = None
            for arg in daemon.cmd.args:
                if arg.endswith(".py"):
                    script_name = Path(arg).name
                    break
            
            if script_name:
                for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if p.info['name'] and 'python' in p.info['name'].lower():
                            cmd = ' '.join(p.info['cmdline'] or [])
                            if script_name.lower() in cmd.lower():
                                logger.warning(
                                    "DaemonManager: '%s' already running dynamically detected (PID %d). Adopting existing process.",
                                    daemon.name, p.info['pid']
                                )
                                daemon.proc = _AdoptedProcess(p.info['pid'])
                                return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

        # Thermal throttle guard for JIT daemons
        if daemon.category == "jit" and self.check_hardware_thermal_throttle():
            logger.warning(
                "DaemonManager: Thermal throttle guard active (>82°C). Suppressing JIT spawn of '%s'.",
                daemon.name,
            )
            return False

        env = os.environ.copy()
        env["DAEMON_MANAGER_OWNED"] = "1"  # tell daemon to skip self-PID write

        try:
            creation_flags = (
                (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0
            )

            # Ensure logs directory exists
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            log_path = logs_dir / f"{daemon.name}.log"

            # Open the log file in append mode. We don't close it here; the OS closes it when the subprocess dies.
            # In a production system, we'd manage these file handles more
            # robustly or use a logger daemon.
            log_handle = open(log_path, "a", encoding="utf-8")

            proc = subprocess.Popen(
                [daemon.cmd.command] + daemon.cmd.args,
                cwd=str(daemon.cmd.cwd),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )
        except FileNotFoundError as exc:
            logger.error(
                "DaemonManager: cannot spawn '%s' — command not found: %s",
                daemon.name,
                exc,
            )
            return False
        except OSError as exc:
            logger.error("DaemonManager: OS error spawning '%s': %s", daemon.name, exc)
            return False

        daemon.proc = proc
        daemon.last_restart_at = time.monotonic()
        pid_path.write_text(str(proc.pid), encoding="utf-8")
        logger.info("DaemonManager: started '%s' (PID %d).", daemon.name, proc.pid)
        self._notify_listeners("start", daemon.name, {"pid": proc.pid, "port": daemon.port, "category": daemon.category})
        return True

    def _terminate(self, daemon: _ManagedDaemon, timeout: float = 8.0) -> bool:
        """Gracefully terminate a daemon; force-kill after timeout."""
        proc = daemon.proc
        if proc is None:
            return True

        pid = proc.pid
        try:
            if isinstance(proc, _AdoptedProcess):
                # Adopted process — use psutil directly
                try:
                    ps_proc = psutil.Process(pid)
                    ps_proc.terminate()
                    ps_proc.wait(timeout=timeout)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        psutil.Process(pid).kill()
                    except psutil.NoSuchProcess:
                        pass
            else:
                if os.name == "nt":
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "DaemonManager: '%s' did not exit in %.1fs — killing.",
                        daemon.name,
                        timeout,
                    )
                    proc.kill()
                    proc.wait()
        except OSError as exc:
            logger.warning(
                "DaemonManager: error terminating '%s': %s", daemon.name, exc
            )
        finally:
            daemon.proc = None
            try:
                self._pid_path(daemon.name).unlink(missing_ok=True)
            except Exception:
                pass

        logger.info("DaemonManager: stopped '%s' (was PID %d).", daemon.name, pid)
        self._notify_listeners("stop", daemon.name, {"pid": pid, "port": daemon.port, "category": daemon.category})
        return True

    def _is_alive(self, daemon: _ManagedDaemon) -> bool:
        """Return True if the daemon process is currently running."""
        if daemon.proc is None:
            return False
        pid = daemon.proc.pid
        if not psutil.pid_exists(pid):
            return False
        if isinstance(daemon.proc, _AdoptedProcess):
            return True
        return daemon.proc.poll() is None

    def _pid_path(self, name: str) -> Path:
        return self.base_dir / f"{name}.pid"

    # ------------------------------------------------------------------
    # Watchdog
    # ------------------------------------------------------------------

    def _start_watchdog(self) -> None:
        """Launch the background watchdog thread."""
        self._stop_event.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="daemon-watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()
        logger.info(
            "DaemonManager: watchdog started (interval=%.1fs).", WATCHDOG_INTERVAL
        )

    def _watchdog_loop(self) -> None:
        """
        Poll all registered daemons every WATCHDOG_INTERVAL seconds.
        If a daemon has died and is still enabled, attempt a restart subject
        to exponential backoff and MAX_RESTART_ATTEMPTS.
        """
        while not self._stop_event.wait(WATCHDOG_INTERVAL):
            with self._lock:
                for daemon in self._daemons.values():
                    if not daemon.enabled:
                        continue
                    if self._is_alive(daemon):
                        # If the daemon has run stably for 10 seconds, reset its crash counter.
                        # This prevents accumulation of restarts over long
                        # periods of uptime.
                        elapsed = time.monotonic() - daemon.last_restart_at
                        if elapsed > 10.0 and daemon.restart_count > 0:
                            logger.debug(
                                "DaemonManager: '%s' ran stably for %.1fs. Resetting restart counter.",
                                daemon.name,
                                elapsed,
                            )
                            daemon.restart_count = 0
                        continue

                    # Daemon is dead
                    if daemon.restart_count >= MAX_RESTART_ATTEMPTS:
                        if daemon.enabled:
                            logger.error(
                                "DaemonManager: '%s' exceeded max restart attempts (%d). "
                                "Disabling auto-restart.",
                                daemon.name,
                                MAX_RESTART_ATTEMPTS,
                            )
                            daemon.enabled = False
                            self._notify_listeners("crash", daemon.name, {"restart_count": daemon.restart_count, "port": daemon.port})
                        continue

                    # Exponential backoff
                    backoff = RESTART_BACKOFF_BASE * (2**daemon.restart_count)
                    elapsed = time.monotonic() - daemon.last_restart_at
                    if elapsed < backoff:
                        logger.debug(
                            "DaemonManager: '%s' backoff %.1fs remaining.",
                            daemon.name,
                            backoff - elapsed,
                        )
                        continue

                    logger.warning(
                        "DaemonManager: '%s' died — restarting (attempt %d/%d).",
                        daemon.name,
                        daemon.restart_count + 1,
                        MAX_RESTART_ATTEMPTS,
                    )
                    daemon.restart_count += 1
                    self._notify_listeners("restart", daemon.name, {"attempt": daemon.restart_count, "port": daemon.port})
                    self._spawn(daemon)

        logger.info("DaemonManager: watchdog stopped.")


# ---------------------------------------------------------------------------
# Thin wrapper so we can track adopted (externally-started) PIDs
# ---------------------------------------------------------------------------


class _AdoptedProcess:
    """Minimal shim that satisfies DaemonManager's duck-typed proc interface."""

    __slots__ = ("pid",)

    def __init__(self, pid: int):
        self.pid = pid


# ---------------------------------------------------------------------------
# Default daemon registry — edit here to add new daemons
# ---------------------------------------------------------------------------


def build_default_manager(base_dir: str | None = None) -> DaemonManager:
    """
    Factory that builds a DaemonManager pre-configured with all known AI-BS daemons.
    Import and call this from unified_stehouwer_launcher or FastAPI lifespan.
    """
    manager = DaemonManager(base_dir=base_dir)

    base = Path(base_dir or os.path.dirname(__file__)).resolve()

    # Trainer daemon — tails transcripts and writes structured logs
    manager.register(
        "trainer_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "trainer_daemon.py")],
        ),
        auto_start=False,
    )

    # ChromaDB daemon — serves the SQLite vector DB over HTTP (Local C: Drive)
    manager.register(
        "chroma_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[
                "-c",
                "import sys, chromadb.cli.cli; sys.argv = ['chroma', 'run', '--path', r'"
                + str(base / "stehouwer_vector_memory")
                + "', '--port', '8001']; chromadb.cli.cli.app()",
            ],
        ),
    )

    # ChromaDB E-Drive daemon — serves the E: Drive vector memory on port 8002
    manager.register(
        "chroma_edrive_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[
                "-c",
                "import sys, chromadb.cli.cli; sys.argv = ['chroma', 'run', '--path', r'E:\\AI_BS_Resources\\ChromaDB', '--port', '8002']; chromadb.cli.cli.app()",
            ],
        ),
    )

    # Memory daemon — vectorizes session history into ChromaDB
    manager.register(
        "memory_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "memory_daemon.py")],
        ),
    )

    # Extend here for gcs_sync_daemon, etc.
    # manager.register("gcs_sync_daemon", [sys.executable, str(base / "backend" / "gcs_sync_daemon.py")])

    # Auto-Healer daemon — self-healing crash watcher
    manager.register(
        "auto_healer_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "auto_healer_daemon.py")],
        ),
    )

    # Research Agent daemon — web scraping market intelligence
    manager.register(
        "research_agent_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "research_agent_daemon.py")],
        ),
    )

    # Mining telemetry daemon
    manager.register(
        "minerwatch_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "minerwatch_daemon.py")],
        ),
        auto_start=True,
    )

    # Chia plotter daemon (heavy background task - auto_start disabled for VRAM preservation)
    manager.register(
        "chia_plotter_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "chia_plotter_daemon.py")],
        ),
        auto_start=False,
    )

    # Wallet tracker daemon
    manager.register(
        "wallet_tracker_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "wallet_tracker_daemon.py")],
        ),
    )

    # Compute monetization daemon (Vast.ai)
    manager.register(
        "compute_monetization_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "compute_monetization_daemon.py")],
        ),
        auto_start=False,
    )

    # Drip-Style AutoBuy daemon (offloaded for high-concurrency LLM inference)
    manager.register(
        "drip_trader_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base / "Crypto-Swarm",
            args=[str(base / "Crypto-Swarm" / "drip_trader_daemon.py")],
        ),
        auto_start=False,
    )

    # Crypto Researcher daemon
    manager.register(
        "researcher_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base / "Crypto-Swarm",
            args=[str(base / "Crypto-Swarm" / "researcher_daemon.py")],
        ),
        auto_start=True,
    )

    # Discord Bot Command Bridge
    manager.register(
        "discord_bot_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "discord_bot_daemon.py")],
        ),
    )

    # Predictive Engine (Multi-head Daemon - deferred)
    manager.register(
        "predictive_engine_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "predictive_engine.py")],
        ),
        auto_start=False,
    )

    # Context Ingestor (Full-Repository & Telemetry)
    manager.register(
        "context_ingestor_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "context_ingestor_daemon.py")],
        ),
        auto_start=True,
    )

    # Stehouwer Publishing Web Server (Port 80 for Cloudflare Tunnel)
    manager.register(
        "stehouwer_web_server",
        ShellCommand(
            command=sys.executable,
            cwd=Path(r"C:\StehouwerPublishing.com"),
            args=[str(Path(r"C:\StehouwerPublishing.com") / "stehouwer_web_server.py")],
        ),
        auto_start=True,
    )

    # Broadcast Daemon on port 8005
    manager.register(
        "broadcast_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base / "backend",
            args=[str(base / "backend" / "aibs_broadcast_daemon.py")],
        ),
        auto_start=True,
    )

    # Unreal Python Signaling Server
    manager.register(
        "unreal_signaling_daemon",
        ShellCommand(
            command=sys.executable,
            cwd=base,
            args=[str(base / "backend" / "AI_BS_Unreal_Signaling_Server.py")],
        ),
        auto_start=True,
    )

    return manager


# ---------------------------------------------------------------------------
# CLI entry-point (standalone supervisor mode)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    mgr = build_default_manager()
    mgr.start_all()
    logger.info("DaemonManager running standalone. Press Ctrl+C to stop.")

    # Start HTTP status server to mimic the Go version on port 6081
    import http.server
    import json

    class StatusHTTPServer(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress HTTP access logging to keep stdout clean
            pass

        def do_GET(self):
            if self.path == "/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                # Format to match Go version (e.g. pid=0 if not running)
                status_data = {}
                for name, info in mgr.status().items():
                    status_data[name] = {
                        "running": info["running"],
                        "pid": info["pid"] if info["pid"] is not None else 0,
                        "restart_count": info["restart_count"],
                        "enabled": info["enabled"],
                    }
                self.wfile.write(json.dumps(status_data).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path.startswith("/restart/"):
                daemon_name = self.path[len("/restart/") :]
                success = mgr.restart_daemon(daemon_name)
                if success:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {"status": "ok", "message": f"Restarted {daemon_name}"}
                        ).encode("utf-8")
                    )
                else:
                    self.send_response(404)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

    def start_http_server():
        try:
            server = http.server.HTTPServer(("127.0.0.1", 6081), StatusHTTPServer)
            logger.info("Status HTTP server listening on http://127.0.0.1:6081")
            server.serve_forever()
        except Exception as e:
            logger.error("Failed to start Status HTTP server: %s", e)

    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    try:
        while True:
            time.sleep(10)
            logger.info("Daemon status: %s", mgr.status())
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
        mgr.stop_all()
