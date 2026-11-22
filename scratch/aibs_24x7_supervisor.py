"""AI-BS Single Master 24/7 Auto-Heal Supervisor.

Continuously monitors and auto-heals every high-stakes 24/7 AI-BS subsystem:
  1. Structural Dip Strategy Engine (Port 8007)
  2. Agent 2 Orderbook Scout (orderbook_scout_signals.json)
  3. Agent 3 Triangular Arb Scout
  4. Agent 4 Risk Watchdog (agent4_watchdog_status.json)
  5. Crypto Email & Alert Notifier (crypto_email_notifier.py)
  6. Go Cognitive Gateway (aibs_engine.exe on Port 8000)
  7. FastAPI Core Backend (AI_BS_Backend on Port 8080)
  8. Vite Frontend Dashboard (Port 5173)
  9. ChromaDB Vector Engine (Port 8002)
 10. Ollama Local LLM Nodes (GPU Port 11434 + CPU Port 11435)
 11. Cloudflare Tunnel (cloudflared.exe -> api.brettstehouwer.live)
 12. OCI Stack Claimer (oci_stack_claimer.py -> us-chicago-1 Ampere VM)

Writes live health telemetry every 30s to:
  - C:\\AI-BS\\saved_data\\master_supervisor_status.json
  - C:\\AI-BS\\saved_data\\master_supervisor.log
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
import urllib.request

BASE_DIR = Path(r"C:\AI-BS")
SAVED_DATA_DIR = BASE_DIR / "saved_data"
STATUS_FILE = SAVED_DATA_DIR / "master_supervisor_status.json"
LOG_FILE = SAVED_DATA_DIR / "master_supervisor.log"
LOCK_PORT = 18007  # Single-instance mutex socket

RECOVERY_PYTHON = BASE_DIR / r"runtime\recovery-20261110\Scripts\python.exe"
SYS_PYTHON312 = Path(r"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe")
CHROMA_EXE = BASE_DIR / r"pyppeteer_env\Scripts\chroma.exe"
GO_GATEWAY_EXE = BASE_DIR / r"go-core\aibs_engine.exe"
CLOUDFLARED_EXE = BASE_DIR / "cloudflared.exe"
DEVTOOLS_NODE = BASE_DIR / r"runtime\devtools\node-v24.22.1-win-x64\node.exe"
VITE_BIN = BASE_DIR / r"frontend\node_modules\vite\bin\vite.js"
OLLAMA_EXE = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"))

OCI_CONTROLLER_STATE_FILE = SAVED_DATA_DIR / "oci_controller_state.json"
OCI_NON_RELAUNCH_MODES = frozenset({
    "MONITOR",
    "HALT",
    "HALT_COST_POLICY",
    "HALT_CONFIG_MISMATCH",
    "HALT_AUTH_ERROR",
    "MANUAL_REVIEW",
    "MANUAL_REVIEW_UNMANAGED_VM",
    "OUTAGE_RECOVERY_REQUIRED",
})

CHECK_INTERVAL_SEC = 30.0
DETACHED_FLAGS = 0x08000000 | 0x00000200 | 0x00000008  # CREATE_NO_WINDOW | NEW_GROUP | DETACHED


def should_launch_oci_claimer(state_path: Path = OCI_CONTROLLER_STATE_FILE) -> tuple[bool, str]:
    """Never treat completed or explicitly halted OCI provisioning as a crash loop (Sec 6.2)."""
    if not state_path.exists():
        return True, "no_controller_state_yet"
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        mode = str(data.get("mode") or "INSPECT").upper()
        if mode in OCI_NON_RELAUNCH_MODES or mode.startswith("HALT") or mode.startswith("MANUAL_REVIEW"):
            return False, f"controller_mode={mode}"
        return True, f"controller_mode={mode}"
    except Exception as exc:
        # Malformed state requires manual/controller inspection rather than blind spawn loop
        return False, f"unreadable_controller_state:{exc}"


def configure_logging() -> logging.Logger:
    SAVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("aibs_master_supervisor")
    log.setLevel(logging.INFO)
    if not log.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        log.addHandler(fh)
        log.addHandler(sh)
    return log


def is_port_open(port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def get_running_command_lines() -> list[tuple[int, str, str]]:
    """Return list of (pid, name, commandline) via PowerShell CIM query."""
    cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('python.exe','pythonw.exe','node.exe','aibs_engine.exe','cloudflared.exe','ollama.exe','chroma.exe') } | "
        "ForEach-Object { \"$($_.ProcessId)|$($_.Name)|$($_.CommandLine)\" }"
    )
    try:
        out = subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            creationflags=0x08000000,
            timeout=12,
        ).decode("utf-8", errors="ignore")
        rows: list[tuple[int, str, str]] = []
        for line in out.splitlines():
            parts = line.strip().split("|", 2)
            if len(parts) == 3 and parts[0].isdigit():
                rows.append((int(parts[0]), parts[1], parts[2]))
        return rows
    except Exception:
        return []


def has_process_matching(procs: list[tuple[int, str, str]], substring: str) -> list[int]:
    sub_low = substring.lower()
    return [pid for pid, _name, cmd in procs if sub_low in cmd.lower()]


def spawn_background(
    args: list[str],
    cwd: Path,
    log: logging.Logger,
    label: str,
    extra_env: dict[str, str] | None = None,
) -> int | None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.Popen(
            args,
            cwd=str(cwd),
            env=env,
            creationflags=DETACHED_FLAGS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        log.info("AUTO-HEALED [%s] -> spawned PID %d (%s)", label, proc.pid, " ".join(args[:3]))
        return proc.pid
    except Exception as exc:
        log.error("Failed spawning [%s]: %s", label, exc)
        return None


def supervise_once(
    log: logging.Logger,
    heal_counts: dict[str, int],
    *,
    safe_recovery_mode: bool | None = None,
    status_file: Path | None = None,
    oci_state_file: Path | None = None,
    strict_io: bool = False,
) -> dict[str, Any]:
    procs = get_running_command_lines()
    py_exe = str(RECOVERY_PYTHON if RECOVERY_PYTHON.exists() else SYS_PYTHON312)
    sys_py = str(SYS_PYTHON312 if SYS_PYTHON312.exists() else RECOVERY_PYTHON)
    if safe_recovery_mode is None:
        safe_recovery_mode = os.environ.get("AIBS_SAFE_RECOVERY_MODE", "").strip().lower() == "passive"
    eff_status_file = status_file or STATUS_FILE
    eff_oci_state_file = oci_state_file or OCI_CONTROLLER_STATE_FILE

    trader_cmd = [py_exe, "-u", "-B", str(BASE_DIR / r"scratch\structural_dip_engine.py")]
    if safe_recovery_mode:
        trader_cmd.extend(["--role", "passive"])

    services: list[dict[str, Any]] = [
        {
            "id": "structural_dip_engine",
            "label": "Agent 1 · Structural Dip Trading Engine (:8007)",
            "port": 8007,
            "match": "structural_dip_engine.py",
            "cmd": trader_cmd,
            "cwd": BASE_DIR / "scratch",
        },
        {
            "id": "agent2_orderbook_scout",
            "label": "Agent 2 · Orderbook Depth Scout",
            "port": None,
            "match": "agent2_orderbook_scout.py",
            "cmd": [py_exe, "-u", "-B", str(BASE_DIR / r"scratch\agent2_orderbook_scout.py")],
            "cwd": BASE_DIR / "scratch",
        },
        {
            "id": "agent3_triangular_arb",
            "label": "Agent 3 · Triangular Arb Scout",
            "port": None,
            "match": "agent3_triangular_arb.py",
            "cmd": [py_exe, "-u", "-B", str(BASE_DIR / r"scratch\agent3_triangular_arb.py")],
            "cwd": BASE_DIR / "scratch",
        },
        {
            "id": "agent4_risk_watchdog",
            "label": "Agent 4 · Risk & Drawdown Watchdog",
            "port": None,
            "match": "agent4_risk_watchdog.py",
            "cmd": [py_exe, "-u", "-B", str(BASE_DIR / r"scratch\agent4_risk_watchdog.py")],
            "cwd": BASE_DIR / "scratch",
        },
        {
            "id": "crypto_email_notifier",
            "label": "Crypto Email & Fill Notifier",
            "port": None,
            "match": "crypto_email_notifier.py",
            "cmd": [py_exe, "-u", "-B", str(BASE_DIR / r"scratch\crypto_email_notifier.py")],
            "cwd": BASE_DIR / "scratch",
        },
        {
            "id": "go_cognitive_gateway",
            "label": "Go Cognitive Engine Gateway (:8000)",
            "port": 8000,
            "match": "aibs_engine.exe",
            "cmd": [str(GO_GATEWAY_EXE)],
            "cwd": BASE_DIR / "go-core",
        },
        {
            "id": "fastapi_backend",
            "label": "FastAPI AI-BS Backend (:8080)",
            "port": 8080,
            "match": "AI_BS_Backend",
            "cmd": [
                py_exe,
                "-m",
                "uvicorn",
                "AI_BS_Backend:app",
                "--app-dir",
                str(BASE_DIR / "backend"),
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
                "--workers",
                "1",
                "--no-access-log",
            ],
            "cwd": BASE_DIR / "backend",
        },
        {
            "id": "vite_frontend",
            "label": "Vite Frontend Dashboard (:5173)",
            "port": 5173,
            "match": "vite.js",
            "cmd": [
                str(DEVTOOLS_NODE),
                str(VITE_BIN),
                "--host",
                "127.0.0.1",
                "--port",
                "5173",
                "--strictPort",
            ],
            "cwd": BASE_DIR / "frontend",
        },
        {
            "id": "chromadb_vector_store",
            "label": "ChromaDB Vector Engine (:8002)",
            "port": 8002,
            "match": "chroma.exe",
            "cmd": [
                str(CHROMA_EXE),
                "run",
                "--path",
                r"E:\AI_BS_Resources\ChromaDB",
                "--port",
                "8002",
                "--host",
                "127.0.0.1",
            ],
            "cwd": BASE_DIR,
        },
        {
            "id": "ollama_gpu_11434",
            "label": "Ollama Local LLM GPU Node (:11434)",
            "port": 11434,
            "match": None,  # Port-checked
            "cmd": [str(OLLAMA_EXE), "serve"],
            "cwd": BASE_DIR,
            "env": {
                "OLLAMA_HOST": "127.0.0.1:11434",
                "OLLAMA_MODELS": r"C:\AI-BS\models\ollama",
                "CUDA_VISIBLE_DEVICES": "0",
                "OLLAMA_MAX_LOADED_MODELS": "1",
                "OLLAMA_NUM_PARALLEL": "1",
                "OLLAMA_FLASH_ATTENTION": "1",
                "OLLAMA_KEEP_ALIVE": "15m",
            },
        },
        {
            "id": "cloudflared_tunnel",
            "label": "Cloudflare Sovereign Tunnel (ai-bs)",
            "port": None,
            "match": "cloudflared.exe",
            "cmd": [
                str(CLOUDFLARED_EXE),
                "tunnel",
                "--config",
                r"C:\Users\footb\.cloudflared\config.yml",
                "--origincert",
                r"C:\Users\footb\.cloudflared\cert.pem",
                "run",
                "ai-bs",
            ],
            "cwd": BASE_DIR,
        },
        {
            "id": "oci_stack_claimer",
            "label": "Oracle Cloud Ampere Claimer (20m cadence)",
            "port": None,
            "match": "oci_stack_claimer.py",
            "cmd": [sys_py, "-u", "-B", str(BASE_DIR / r"scratch\oci_stack_claimer.py")],
            "cwd": BASE_DIR / "scratch",
        },
        {
            "id": "mobile_crypto_relay",
            "label": "Mobile Crypto Read-Only Relay (:8017)",
            "port": 8017,
            "match": "mobile_crypto_relay.py",
            "cmd": [py_exe, "-u", "-B", str(BASE_DIR / r"scratch\mobile_crypto_relay.py")],
            "cwd": BASE_DIR / "scratch",
        },
    ]

    report_rows: list[dict[str, Any]] = []
    for svc in services:
        sid = svc["id"]
        port = svc["port"]
        match_str = svc["match"]

        port_ok = is_port_open(port) if port is not None else True
        pids = has_process_matching(procs, match_str) if match_str else []
        proc_ok = (len(pids) > 0) if match_str else True

        # Service is healthy if port is listening (when port-bound) or process exists (when non-port daemon)
        healthy = port_ok if port is not None else proc_ok
        action = "ONLINE"

        if sid == "oci_stack_claimer" and not healthy:
            allow_spawn, oci_reason = should_launch_oci_claimer(eff_oci_state_file)
            if not allow_spawn:
                healthy = True
                action = f"IDLE_OK ({oci_reason})"

        if not healthy:
            heal_counts[sid] = heal_counts.get(sid, 0) + 1
            new_pid = spawn_background(
                svc["cmd"],
                svc["cwd"],
                log,
                svc["label"],
                svc.get("env"),
            )
            action = f"AUTO_HEALED (PID {new_pid})" if new_pid else "HEAL_FAILED"
            if new_pid:
                pids.append(new_pid)

        report_rows.append({
            "id": sid,
            "label": svc["label"],
            "port": port,
            "healthy": healthy or action.startswith("AUTO_HEALED"),
            "status": action,
            "pids": pids,
            "heals_total": heal_counts.get(sid, 0),
        })

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "supervisor_pid": os.getpid(),
        "safe_recovery_mode": bool(safe_recovery_mode),
        "check_interval_sec": CHECK_INTERVAL_SEC,
        "services_total": len(report_rows),
        "services_healthy": sum(1 for r in report_rows if r["healthy"]),
        "services": report_rows,
        "status_write_ok": True,
    }
    try:
        if eff_status_file.exists() and eff_status_file.is_dir():
            raise IsADirectoryError(f"STATUS_FILE points to a directory: {eff_status_file}")
        eff_status_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = eff_status_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        os.replace(tmp, eff_status_file)
    except Exception as exc:
        summary["status_write_ok"] = False
        summary["status_write_error"] = str(exc)
        log.error("SUPERVISOR_STATUS_WRITE_FAILED (%s): %s", eff_status_file, exc)
        if strict_io:
            raise
    return summary


def main() -> int:
    log = configure_logging()
    safe_passive = (
        "--safe-boot-passive" in sys.argv
        or os.environ.get("AIBS_SAFE_RECOVERY_MODE", "").strip().lower() == "passive"
    )
    if "--once" in sys.argv:
        summary = supervise_once(log, {}, safe_recovery_mode=safe_passive)
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("status_write_ok", False) else 1

    # Acquire single-instance loopback socket mutex so duplicate supervisors never collide
    lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_sock.bind(("127.0.0.1", LOCK_PORT))
        lock_sock.listen(1)
    except OSError:
        log.info("Master 24/7 Supervisor already running on lock port %d. Exiting duplicate.", LOCK_PORT)
        return 0

    log.info("=================================================================")
    log.info("AI-BS Single Master 24/7 Auto-Heal Supervisor ACTIVE (PID %d)", os.getpid())
    log.info("Monitoring 12 high-stakes services every %.0fs", CHECK_INTERVAL_SEC)
    log.info("=================================================================")

    heal_counts: dict[str, int] = {}
    while True:
        try:
            supervise_once(log, heal_counts)
        except Exception as exc:
            log.error("Supervisor iteration error: %s", exc)
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    raise SystemExit(main())

