r"""
AI-BS Autonomous Ecosystem Spawner & Multi-Port Supervisor
Probes and guarantees that all required sovereign local service daemons are running silently in the background:
- 11434: Ollama GPU Primary Swarm (RTX 4090 24GB VRAM)
- 11435: Ollama CPU Embeddings Swarm (Ryzen 9 9950X AVX-512 for nomic-embed-text / ChromaDB vector indexing)
- 8080:  FastAPI Master Engine Hub (AI_BS_Backend.py)
- 8007:  Crypto Swarm & Scalp Bot (crypto_trader_bot.py + 24/7 Watchdog)
- 5173:  Primary React Dashboard (Vite Frontend)
- 8001:  ChromaDB Vector Store (E:\AI_BS_Resources\ChromaDB or C:\AI-BS\chroma_db)
- 8002:  ChromaDB Secondary Mirror Store
- 5174:  BroadcastStudioApp Vite
- 8005:  Broadcast Kernel Daemon
- 8006:  Twitch / IRC Social Hub
- 8008:  Supabase Kong Gateway
- 8013:  VST3 Audio Bridge
- 8088:  Broadcast NVENC Hardware Encoder
- 8188:  ComfyUI Primary Proxy
"""

import sys
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

ROOT_DIR = Path(r"C:\AI-BS")
BACKEND_DIR = ROOT_DIR / "backend"
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PYTHON_EXE = ROOT_DIR / "pyppeteer_env" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

PYTHONW_EXE = ROOT_DIR / "pyppeteer_env" / "Scripts" / "pythonw.exe"
if not PYTHONW_EXE.exists():
    PYTHONW_EXE = PYTHON_EXE

CHROMA_EXE = ROOT_DIR / "pyppeteer_env" / "Scripts" / "chroma.exe"
CHROMA_DB_PRIMARY = Path(r"E:\AI_BS_Resources\ChromaDB") if Path(r"E:\AI_BS_Resources\ChromaDB").exists() else ROOT_DIR / "chroma_db"
CHROMA_DB_PRIMARY.mkdir(parents=True, exist_ok=True)

CHROMA_DB_SECONDARY = ROOT_DIR / "chroma_db"
CHROMA_DB_SECONDARY.mkdir(parents=True, exist_ok=True)

# Locate Ollama binary
OLLAMA_EXE = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"))
if not OLLAMA_EXE.exists():
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(p) / "ollama.exe"
        if candidate.exists():
            OLLAMA_EXE = candidate
            break

FLAGS = 0
if sys.platform == "win32":
    FLAGS = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def get_ollama_env(port: int) -> Dict[str, str]:
    """Generates dual-port Ollama configuration: GPU (11434) vs CPU AVX-512 Embeddings (11435)."""
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
    env["OLLAMA_MODELS"] = r"C:\AI-BS\models\ollama" if Path(r"C:\AI-BS\models\ollama").exists() else r"E:\AI_BS_Resources\Ollama"

    if port == 11435:
        # PURE-CPU Workhorse on AMD Ryzen 9 9950X (32 Threads, AVX-512)
        # Dedicated to nomic-embed-text embeddings, ChromaDB indexing, and background tasks (0 VRAM used)
        env["CUDA_VISIBLE_DEVICES"] = "-1"
        env["OLLAMA_LLM_LIBRARY"] = "cpu"
        env["OLLAMA_NUM_PARALLEL"] = "4"
        env["OLLAMA_MAX_LOADED_MODELS"] = "2"
        env["OLLAMA_FLASH_ATTENTION"] = "0"
        env["OLLAMA_KEEP_ALIVE"] = "60m"
    else:
        # DEDICATED RTX 4090 GPU Node (Port 11434)
        # Low-latency chat, code generation, and sovereign reasoning
        # OLLAMA_KEEP_ALIVE=0 guarantees weights load strictly on-demand and unload immediately
        env["CUDA_VISIBLE_DEVICES"] = "0"
        env["OLLAMA_MAX_LOADED_MODELS"] = "1"
        env["OLLAMA_NUM_PARALLEL"] = "1"
        env["OLLAMA_FLASH_ATTENTION"] = "1"
        env["OLLAMA_KEEP_ALIVE"] = "0"

    return env


DAEMON_SPECS = [
    # ── 1. Sovereign AI Core: Dual-Port Ollama (GPU 11434 / CPU Embeddings 11435) ──
    {
        "port": 11434,
        "name": "Ollama GPU Swarm (RTX 4090)",
        "cwd": ROOT_DIR,
        "cmd": [str(OLLAMA_EXE), "serve"],
        "env_fn": lambda: get_ollama_env(11434),
        "log": LOGS_DIR / "ollama_gpu_11434.log",
        "wait_s": 3.0,
    },
    {
        "port": 11435,
        "name": "Ollama CPU Embeddings Swarm (Ryzen 9 9950X AVX-512 / nomic-embed-text)",
        "cwd": ROOT_DIR,
        "cmd": [str(OLLAMA_EXE), "serve"],
        "env_fn": lambda: get_ollama_env(11435),
        "log": LOGS_DIR / "ollama_cpu_embeddings_11435.log",
        "wait_s": 3.0,
    },

    # ── 2. Vector Memory: ChromaDB (Port 8001 Primary & Port 8002 Secondary) ──
    {
        "port": 8001,
        "name": "ChromaDB Primary Vector Store",
        "cwd": BACKEND_DIR,
        "cmd": [str(CHROMA_EXE), "run", "--path", str(CHROMA_DB_PRIMARY), "--port", "8001", "--host", "127.0.0.1"],
        "log": LOGS_DIR / "chroma_8001.log",
        "wait_s": 2.5,
    },
    {
        "port": 8002,
        "name": "ChromaDB Secondary Mirror Store",
        "cwd": BACKEND_DIR,
        "cmd": [str(CHROMA_EXE), "run", "--path", str(CHROMA_DB_SECONDARY), "--port", "8002", "--host", "127.0.0.1"],
        "log": LOGS_DIR / "chroma_8002.log",
        "wait_s": 2.5,
    },

    # ── 3. Central Core: FastAPI Master Engine (Port 8080) ──
    {
        "port": 8080,
        "name": "FastAPI Master Engine",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "AI_BS_Backend.py")],
        "log": LOGS_DIR / "AI_BS_Backend.log",
        "wait_s": 3.0,
    },

    # ── 4. Financial Engine: Crypto Swarm & Scalp Bot (Port 8007) ──
    {
        "port": 8007,
        "name": "Crypto Swarm & Scalp Bot",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "crypto_trader_bot.py")],
        "log": LOGS_DIR / "crypto_trader_8007.log",
        "wait_s": 2.5,
    },

    # ── 5. User Interface: Primary React Dashboard (Vite Port 5173) ──
    {
        "port": 5173,
        "name": "Primary React Dashboard (Vite)",
        "cwd": ROOT_DIR / "frontend",
        "cmd": ["cmd.exe", "/c", "npm", "run", "dev"],
        "log": LOGS_DIR / "vite_dashboard_5173.log",
        "wait_s": 3.5,
    },

    # ── 6. Broadcast & Audio Subsystems ──
    {
        "port": 5174,
        "name": "BroadcastStudioApp Vite",
        "cwd": ROOT_DIR / "BroadcastStudioApp",
        "cmd": ["cmd.exe", "/c", "npm", "run", "dev"],
        "log": LOGS_DIR / "broadcast_vite_5174.log",
        "wait_s": 3.5,
    },
    {
        "port": 8005,
        "name": "Broadcast Kernel Daemon",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "aibs_broadcast_daemon.py")],
        "log": LOGS_DIR / "aibs_broadcast_daemon.log",
        "wait_s": 2.0,
    },
    {
        "port": 8006,
        "name": "Twitch / IRC Social Hub",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "aibs_social_daemon.py")],
        "log": LOGS_DIR / "aibs_social_daemon.log",
        "wait_s": 2.0,
    },
    {
        "port": 8008,
        "name": "Supabase Kong Gateway",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "aibs_supabase_gateway.py")],
        "log": LOGS_DIR / "supabase_gateway_8008.log",
        "wait_s": 1.5,
    },
    {
        "port": 8013,
        "name": "VST3 Audio Bridge",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "aibs_vst_daemon.py")],
        "log": LOGS_DIR / "vst_bridge_8013.log",
        "wait_s": 2.0,
    },
    {
        "port": 8088,
        "name": "Broadcast NVENC Hardware Encoder",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "aibs_broadcast_kernel.py")],
        "log": LOGS_DIR / "broadcast_kernel_8088.log",
        "wait_s": 2.5,
    },
    {
        "port": 8188,
        "name": "ComfyUI Primary & Diffusion Standby Proxy (8188/8189)",
        "cwd": BACKEND_DIR,
        "cmd": [str(PYTHONW_EXE), str(BACKEND_DIR / "comfy_primary_proxy_8188.py")],
        "log": LOGS_DIR / "comfy_proxy_8188.log",
        "wait_s": 1.5,
    },
]


def ensure_crypto_watchdog() -> None:
    """Guarantees the 24/7 Autonomous Crypto Watchdog process is running."""
    watchdog_script = BACKEND_DIR / "core" / "unified_crypto_pearl_watchdog.py"
    if not watchdog_script.exists():
        return

    try:
        import psutil
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            cmd = " ".join(p.info.get("cmdline") or [])
            if "unified_crypto_pearl_watchdog.py" in cmd:
                return  # already running
    except Exception:
        pass

    try:
        log_out = LOGS_DIR / "crypto_watchdog.log"
        log_err = LOGS_DIR / "crypto_watchdog.err"
        f_out = open(log_out, "a", encoding="utf-8", errors="ignore")
        f_err = open(log_err, "a", encoding="utf-8", errors="ignore")
        subprocess.Popen(
            [str(PYTHONW_EXE), str(watchdog_script)],
            cwd=str(BACKEND_DIR),
            stdout=f_out,
            stderr=f_err,
            creationflags=FLAGS
        )
    except Exception:
        pass


def _trigger_wmi_breakaway_spawner() -> bool:
    """
    Uses Windows WMI (Win32_Process.Create) to spawn `aibs_ecosystem_spawner.py --wmi-worker`
    under WmiPrvSE.exe so that background daemons break away from any parent Job Object.
    """
    if sys.platform != "win32":
        return False
    try:
        spawner_script = str(BACKEND_DIR / "aibs_ecosystem_spawner.py")
        cmd_line = f'"{PYTHONW_EXE}" "{spawner_script}" --wmi-worker --force'
        ps_cmd = (
            "Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
            f"-Arguments @{{CommandLine='{cmd_line}'; CurrentDirectory='{ROOT_DIR}'}} | Out-Null"
        )
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5.0,
            creationflags=FLAGS,
        )
        return True
    except Exception:
        return False


SPAWNER_LOCK_FILE = ROOT_DIR / "spawner.lock"


def _acquire_spawner_lock(timeout_seconds: float = 15.0) -> bool:
    """Acquires a file-based mutual exclusion lock with PID validation to prevent double-spawning race conditions."""
    import time
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            if SPAWNER_LOCK_FILE.exists():
                content = SPAWNER_LOCK_FILE.read_text(encoding="utf-8").strip().split(":")
                if len(content) == 2:
                    lock_pid, lock_time = int(content[0]), float(content[1])
                    # If lock is stale (> 30s) or process no longer exists, break it
                    if time.time() - lock_time > 30.0:
                        SPAWNER_LOCK_FILE.unlink(missing_ok=True)
                    else:
                        try:
                            import psutil
                            if not psutil.pid_exists(lock_pid):
                                SPAWNER_LOCK_FILE.unlink(missing_ok=True)
                            else:
                                time.sleep(0.5)
                                continue
                        except Exception:
                            SPAWNER_LOCK_FILE.unlink(missing_ok=True)
            # Create atomic lock
            with open(SPAWNER_LOCK_FILE, "x", encoding="utf-8") as f:
                f.write(f"{os.getpid()}:{time.time()}")
            return True
        except FileExistsError:
            time.sleep(0.5)
        except Exception:
            return True
    return False


def _release_spawner_lock():
    try:
        SPAWNER_LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def activate_all_daemons(verbose: bool = True) -> Dict[str, Any]:
    """
    Probes every ecosystem service port and boots offline daemons silently in the background.
    Protected by mutual exclusion lock and strict WMI-breakaway single-execution semantics.
    """
    is_wmi_worker = "--wmi-worker" in sys.argv or "--force" in sys.argv
    if not is_wmi_worker and os.environ.get('AI_BS_BACKEND_MANAGE_DAEMONS', '').strip().lower() != 'true':
        active = [spec['port'] for spec in DAEMON_SPECS if is_port_open(spec['port'])]
        pending = [spec['port'] for spec in DAEMON_SPECS if spec['port'] not in active]
        return {'spawned': [], 'already_online': active, 'active_now': active,
                'pending': pending, 'details': {}, 'activation_disabled': True}
    offline_initial = [spec["port"] for spec in DAEMON_SPECS if not is_port_open(spec["port"])]

    # If all daemons are already listening, return immediately without locking
    if not offline_initial:
        if verbose:
            print("[ONLINE] All core ecosystem daemons are already listening. No spawn required.")
        return {
            "spawned": [],
            "already_online": [s["port"] for s in DAEMON_SPECS],
            "active_now": [s["port"] for s in DAEMON_SPECS],
            "pending": [],
            "details": {s["port"]: {"name": s["name"], "status": "ALREADY_ONLINE", "port": s["port"]} for s in DAEMON_SPECS}
        }

    # If running on Windows as parent (not worker), trigger WMI breakaway to detach from Job Object
    if offline_initial and not is_wmi_worker and sys.platform == "win32":
        if verbose:
            print(f"[WMI-BREAKAWAY] Delegating {len(offline_initial)} offline daemons to WMI worker: {offline_initial}")
        if _trigger_wmi_breakaway_spawner():
            # Wait for WMI worker to boot and bind the ports
            for _ in range(25):
                time.sleep(0.4)
                if all(is_port_open(p) for p in offline_initial):
                    break
            
            # CRITICAL FIX: Return the live port verification immediately.
            # DO NOT fall through to spawn them locally a second time!
            verified_active = [p for p in offline_initial if is_port_open(p)]
            verified_pending = [p for p in offline_initial if not is_port_open(p)]
            if verbose:
                print(f"[WMI-BREAKAWAY] Settled: {len(verified_active)} online, {len(verified_pending)} pending.")
            return {
                "spawned": verified_active,
                "already_online": [s["port"] for s in DAEMON_SPECS if s["port"] not in offline_initial],
                "active_now": [s["port"] for s in DAEMON_SPECS if is_port_open(s["port"])],
                "pending": verified_pending,
                "details": {s["port"]: {"name": s["name"], "status": "WMI_SPAWNED" if s["port"] in verified_active else "PENDING", "port": s["port"]} for s in DAEMON_SPECS}
            }

    # Acquire lock for worker execution
    _acquire_spawner_lock(timeout_seconds=10.0)

    try:
        results = {}
        spawned = []
        already_online = []

        for spec in DAEMON_SPECS:
            port = spec["port"]
            name = spec["name"]

            # Double-check port right before launching
            if is_port_open(port):
                already_online.append(port)
                results[port] = {"name": name, "status": "ALREADY_ONLINE", "port": port}
                if verbose:
                    print(f"[ONLINE] Port {port:5d} ({name}) already listening.")
                continue

            if verbose:
                print(f"[SPAWNING] Port {port:5d} ({name})...")

            try:
                cwd = str(spec["cwd"])
                log_stdout = str(spec["log"])
                log_stderr = str(spec["log"]).replace(".log", ".err")
                
                f_out = open(log_stdout, "a", encoding="utf-8", errors="ignore")
                f_err = open(log_stderr, "a", encoding="utf-8", errors="ignore")

                proc_env = spec["env_fn"]() if "env_fn" in spec else os.environ.copy()

                subprocess.Popen(
                    spec["cmd"],
                    cwd=cwd,
                    stdout=f_out,
                    stderr=f_err,
                    env=proc_env,
                    creationflags=FLAGS
                )
                spawned.append(port)
                results[port] = {"name": name, "status": "SPAWNED", "port": port}
                # Brief settling time per daemon to prevent port collision
                time.sleep(0.2)
            except Exception as e:
                results[port] = {"name": name, "status": "FAILED", "error": str(e), "port": port}
                if verbose:
                    print(f"  [ERROR] Failed to spawn {name}: {e}")

        # Ensure crypto 24/7 watchdog is running alongside 8007
        ensure_crypto_watchdog()

        # Allow spawned daemons brief settling time
        if spawned:
            time.sleep(2.0)

        # Post-validation
        active_now = []
        pending_now = []
        for spec in DAEMON_SPECS:
            p = spec["port"]
            if is_port_open(p):
                active_now.append(p)
                if p in results:
                    results[p]["verified_listening"] = True
            else:
                pending_now.append(p)
                if p in results:
                    results[p]["verified_listening"] = False

        return {
            "spawned": spawned,
            "already_online": already_online,
            "active_now": active_now,
            "pending": pending_now,
            "details": results
        }
    finally:
        _release_spawner_lock()


spawn_all_daemons = activate_all_daemons


def probe_ports(ports: Optional[List[int]] = None) -> Dict[int, bool]:
    """Probes specified ports (or all 25 ecosystem ports) and returns {port: is_open}."""
    target_ports = ports or [
        80, 3001, 4455, 5173, 5174, 8000, 8001, 8002, 8005, 8006,
        8007, 8008, 8010, 8013, 8055, 8080, 8085, 8088, 8089, 8099,
        8188, 8189, 8888, 11434, 11435
    ]
    return {p: is_port_open(p) for p in target_ports}


if __name__ == "__main__":
    is_wmi = "--wmi-worker" in sys.argv
    if not is_wmi:
        print("==================================================")
        print("AI-BS AUTONOMOUS ECOSYSTEM MULTI-PORT SPAWNER")
        print("==================================================")
    res = activate_all_daemons(verbose=not is_wmi)
    if not is_wmi:
        print("\n--------------------------------------------------")
        print(f"Verified Active: {len(res['active_now'])}/{len(DAEMON_SPECS)}")
        print(f"Active Ports: {res['active_now']}")
        if res['pending']:
            print(f"Pending/Offline: {res['pending']}")
        print("--------------------------------------------------")

