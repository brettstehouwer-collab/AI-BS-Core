"""
unified_crypto_pearl_watchdog.py — Autonomous 24/7 Background Supervisor
=========================================================================
Ensures:
1. Crypto Trader Bot (Port 8007) is ALWAYS running to NEVER miss a trigger event.
   - Pings http://127.0.0.1:8007/healthz every 5 seconds.
   - If offline or socket frozen, kills orphan processes and immediately relaunches.
2. Pearl Wallet and Payout Watcher are ALWAYS running in the background UNLESS explicitly stopped by the user.
   - Respects sentinel flag: C:\\AI-BS\\.pearl_stopped
   - If .pearl_stopped does NOT exist: ensures Pearl Wallet.exe (or oyster-windows-x64.exe)
     and pearl_payout_watcher.py are active. Auto-restarts them if closed or crashed.
   - If .pearl_stopped DOES exist: leaves Pearl stopped until user calls Start_Pearl.bat or start API.
"""

import os
import sys
import time
import json
import logging
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

BASE_DIR = Path(r"C:\AI-BS").resolve()
BACKEND_DIR = BASE_DIR / "backend"
LOGS_DIR = BASE_DIR / "logs"
STATE_DIR = BASE_DIR / "state"
LOGS_DIR.mkdir(exist_ok=True)
STATE_DIR.mkdir(exist_ok=True)

WATCHDOG_LOG = LOGS_DIR / "unified_watchdog.log"
STATUS_JSON = STATE_DIR / "unified_watchdog_status.json"
WATCHDOG_PID_FILE = STATE_DIR / "unified_crypto_pearl_watchdog.pid"
PEARL_STOPPED_FILE = BASE_DIR / ".pearl_stopped"

PYTHON_EXE = str(BASE_DIR / "pyppeteer_env" / "Scripts" / "pythonw.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = str(BASE_DIR / "pyppeteer_env" / "Scripts" / "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

CRYPTO_BOT_SCRIPT = str(BACKEND_DIR / "crypto_trader_bot.py")
PEARL_WALLET_EXE = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Pearl Wallet\Pearl Wallet.exe"))
PEARL_WATCHER_SCRIPT = str(BASE_DIR / "miners" / "pearl_payout_watcher.py")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Watchdog] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(WATCHDOG_LOG, encoding="utf-8")
    ]
)
logger = logging.getLogger("UnifiedWatchdog")

crypto_restart_count = 0
pearl_restart_count = 0
last_crypto_ok = 0.0
last_pearl_ok = 0.0
last_discord_attempt = 0.0
DISCORD_RETRY_INTERVAL = 300.0  # Wait at least 5 minutes before retrying Discord if it exits
consecutive_crypto_failures = 0
STARTUP_GRACE_PERIOD_SEC = 45.0
MAX_CONSECUTIVE_FAILURES = 3

WINDOWLESS_FLAGS = ((subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if sys.platform == "win32" else 0)



def acquire_singleton():
    """Ensure only a single instance of the watchdog runs."""
    current_pid = os.getpid()
    if WATCHDOG_PID_FILE.exists():
        try:
            old_pid = int(WATCHDOG_PID_FILE.read_text(encoding="utf-8").strip())
            if old_pid != current_pid and psutil and psutil.pid_exists(old_pid):
                proc = psutil.Process(old_pid)
                cmd = " ".join(proc.cmdline() or [])
                if "unified_crypto_pearl_watchdog.py" in cmd:
                    logger.warning(f"Another Watchdog instance is already active (PID {old_pid}). Exiting cleanly.")
                    sys.exit(0)
        except Exception:
            pass
    try:
        WATCHDOG_PID_FILE.write_text(str(current_pid), encoding="utf-8")
    except Exception:
        pass


def release_singleton():
    try:
        if WATCHDOG_PID_FILE.exists():
            WATCHDOG_PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def is_process_running(name_substr: str) -> tuple[bool, list[int]]:
    """Check if any process name contains name_substr (case-insensitive)."""
    pids = []
    if psutil:
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pname = p.info['name']
                if pname and name_substr.lower() in pname.lower():
                    pids.append(p.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return (len(pids) > 0, pids)


def is_script_running(script_substr: str) -> tuple[bool, list[int]]:
    """Check if any python process has script_substr in its command line."""
    pids = []
    if psutil:
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if p.info['name'] and 'python' in p.info['name'].lower():
                    cmd = ' '.join(p.info['cmdline'] or [])
                    if script_substr.lower() in cmd.lower():
                        pids.append(p.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return (len(pids) > 0, pids)


def check_crypto_bot_health() -> bool:
    """Ping Port 8007 telemetry endpoint to verify the trading bot is actively serving ticks."""
    try:
        req = urllib.request.Request("http://127.0.0.1:8007/healthz", headers={"User-Agent": "AI-BS-Watchdog/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass
    return False


def kill_processes_by_script(script_substr: str):
    """Terminate stale or frozen python processes executing a specific script."""
    running, pids = is_script_running(script_substr)
    for pid in pids:
        try:
            logger.warning(f"Terminating stale process {pid} running {script_substr}...")
            if psutil:
                proc = psutil.Process(pid)
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except psutil.TimeoutExpired:
                    proc.kill()
        except Exception as e:
            logger.debug(f"Error terminating PID {pid}: {e}")


def launch_crypto_bot():
    """Launch the crypto trading bot as an independent detached background process."""
    global crypto_restart_count, consecutive_crypto_failures
    logger.warning("Spawning resilient Crypto Trader Bot on Port 8007...")
    try:
        # Pre-flight: Kill any zombie holding port 8007 or running the script
        kill_processes_by_script("crypto_trader_bot.py")

        bot_stdout = str(LOGS_DIR / "crypto_trader_bot.log")
        bot_stderr = str(LOGS_DIR / "crypto_trader_bot.err")
        powershell_cmd = f"Start-Process -FilePath '{PYTHON_EXE}' -ArgumentList '{CRYPTO_BOT_SCRIPT}' -WorkingDirectory '{BACKEND_DIR}' -RedirectStandardOutput '{bot_stdout}' -RedirectStandardError '{bot_stderr}' -WindowStyle Hidden"
        subprocess.Popen(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", powershell_cmd],
            creationflags=WINDOWLESS_FLAGS
        )
        crypto_restart_count += 1
        consecutive_crypto_failures = 0
        logger.info(f"Crypto Trader Bot launched via Start-Process. Total Restarts: {crypto_restart_count}")
    except Exception as e:
        logger.error(f"Failed to launch Crypto Trader Bot: {e}")



def launch_pearl():
    """Launch Pearl Wallet in the background (minimized) and start the payout watcher."""
    global pearl_restart_count
    logger.info("Spawning Pearl Wallet & Payout Watcher in background...")
    try:
        if PEARL_WALLET_EXE.exists():
            # Launch Pearl Wallet minimized so it stays active without intrusive popups
            powershell_cmd = f"Start-Process -FilePath '{PEARL_WALLET_EXE}' -WindowStyle Minimized"
            subprocess.Popen(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", powershell_cmd],
                creationflags=WINDOWLESS_FLAGS
            )
            pearl_restart_count += 1
            logger.info(f"Pearl Wallet launched minimized. Total Restarts: {pearl_restart_count}")
        else:
            logger.warning(f"Pearl Wallet executable not found at {PEARL_WALLET_EXE}")

        # Ensure Pearl Payout Watcher is also running
        watcher_running, _ = is_script_running("pearl_payout_watcher.py")
        if not watcher_running and os.path.exists(PEARL_WATCHER_SCRIPT):
            subprocess.Popen(
                [PYTHON_EXE, PEARL_WATCHER_SCRIPT],
                cwd=str(Path(PEARL_WATCHER_SCRIPT).parent),
                creationflags=WINDOWLESS_FLAGS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("Pearl Payout Watcher spawned in background.")
    except Exception as e:
        logger.error(f"Failed to launch Pearl components: {e}")


def stop_pearl_gracefully():
    """Mark Pearl as stopped by user and terminate wallet processes."""
    PEARL_STOPPED_FILE.write_text(f"STOPPED_BY_USER\nTimestamp: {time.time()}\n", encoding="utf-8")
    logger.info("Created .pearl_stopped sentinel file.")

    # Gracefully terminate Pearl processes
    for substr in ["Pearl Wallet", "oyster"]:
        _, pids = is_process_running(substr)
        for pid in pids:
            try:
                logger.info(f"Stopping Pearl process {pid} ({substr})...")
                if psutil:
                    proc = psutil.Process(pid)
                    proc.terminate()
            except Exception:
                pass
    kill_processes_by_script("pearl_payout_watcher.py")
    logger.info("Pearl background processes stopped gracefully.")


def start_pearl_explicitly():
    """Clear sentinel stop flag and immediately launch Pearl."""
    if PEARL_STOPPED_FILE.exists():
        PEARL_STOPPED_FILE.unlink(missing_ok=True)
        logger.info("Cleared .pearl_stopped sentinel file.")
    launch_pearl()


def update_status_file(crypto_online: bool, pearl_status: str, pearl_pids: list[int]):
    """Persist watchdog health metrics to state/unified_watchdog_status.json."""
    status_payload = {
        "timestamp": time.time(),
        "crypto_bot": {
            "online": crypto_online,
            "port": 8007,
            "restarts": crypto_restart_count,
            "last_healthy": last_crypto_ok,
        },
        "pearl": {
            "status": pearl_status,
            "user_stopped": PEARL_STOPPED_FILE.exists(),
            "pids": pearl_pids,
            "restarts": pearl_restart_count,
            "last_healthy": last_pearl_ok,
        }
    }
    try:
        with open(STATUS_JSON, "w", encoding="utf-8") as f:
            json.dump(status_payload, f, indent=2)
    except Exception:
        pass


def run_watchdog_cycle():
    """Single supervision evaluation cycle."""
    global last_crypto_ok, last_pearl_ok, consecutive_crypto_failures

    # --- 1. Supervise Crypto Trader Bot ---
    crypto_online = check_crypto_bot_health()
    if crypto_online:
        last_crypto_ok = time.time()
        consecutive_crypto_failures = 0
    else:
        # Check if process is already running and warming up
        is_running, pids = is_script_running("crypto_trader_bot.py")
        in_grace_period = False
        if is_running and psutil:
            try:
                min_create_time = min(psutil.Process(p).create_time() for p in pids)
                age = time.time() - min_create_time
                if age < STARTUP_GRACE_PERIOD_SEC:
                    in_grace_period = True
                    logger.info(f"Crypto Trader Bot is warming up (age: {age:.1f}s / {STARTUP_GRACE_PERIOD_SEC:.0f}s grace period). Awaiting Port 8007...")
            except Exception:
                pass

        if not in_grace_period:
            consecutive_crypto_failures += 1
            if not is_running or consecutive_crypto_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.warning(f"Crypto Trader Bot (Port 8007) is NOT responding! (failures: {consecutive_crypto_failures}, running: {is_running}). Initiating auto-recovery...")
                launch_crypto_bot()
                time.sleep(2.0)
                crypto_online = check_crypto_bot_health()
            else:
                logger.warning(f"Crypto Trader Bot health check failed ({consecutive_crypto_failures}/{MAX_CONSECUTIVE_FAILURES}). Waiting before restart...")

    # --- 2. Supervise Pearl Ecosystem ---
    pearl_pids = []
    if PEARL_STOPPED_FILE.exists():
        pearl_status = "stopped_by_user"
    else:
        # Check if Pearl Wallet or Oyster daemon is running
        wallet_running, w_pids = is_process_running("Pearl Wallet")
        oyster_running, o_pids = is_process_running("oyster")
        pearl_pids = list(set(w_pids + o_pids))

        if wallet_running or oyster_running:
            pearl_status = "running"
            last_pearl_ok = time.time()

            # Also ensure pearl_payout_watcher is up
            pwatcher_running, _ = is_script_running("pearl_payout_watcher.py")
            if not pwatcher_running and os.path.exists(PEARL_WATCHER_SCRIPT):
                logger.info("Pearl Payout Watcher was offline — re-launching...")
                subprocess.Popen(
                    [PYTHON_EXE, PEARL_WATCHER_SCRIPT],
                    cwd=str(Path(PEARL_WATCHER_SCRIPT).parent),
                    creationflags=WINDOWLESS_FLAGS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        else:
            pearl_status = "restarting"
            logger.warning("Pearl Wallet is NOT running and not stopped by user! Auto-restarting in background...")
            launch_pearl()

    # --- 3. Supervise Discord Bot Continuous Stream ---
    global last_discord_attempt
    discord_running, _ = is_script_running("discord_bot_daemon.py")
    if not discord_running:
        now = time.time()
        if (now - last_discord_attempt) >= DISCORD_RETRY_INTERVAL:
            discord_script = str(BACKEND_DIR / "discord_bot_daemon.py")
            if os.path.exists(discord_script):
                last_discord_attempt = now
                logger.info("Discord Bot Daemon is offline — spawning background process (windowless)...")
                subprocess.Popen(
                    [PYTHON_EXE, discord_script],
                    cwd=str(BACKEND_DIR),
                    creationflags=WINDOWLESS_FLAGS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

    update_status_file(crypto_online, pearl_status, pearl_pids)


def watchdog_loop():
    logger.info("Unified Crypto & Pearl Autonomous Watchdog Online.")
    logger.info(f"Monitoring Crypto Bot on Port 8007. Sentinel file: {PEARL_STOPPED_FILE}")
    while True:
        try:
            run_watchdog_cycle()
        except Exception as e:
            logger.error(f"Error in watchdog cycle: {e}", exc_info=True)
        time.sleep(5.0)


if __name__ == "__main__":
    import atexit
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "stop-pearl":
            stop_pearl_gracefully()
            print("[OK] Pearl stopped and marked stopped by user.")
            sys.exit(0)
        elif cmd == "start-pearl":
            start_pearl_explicitly()
            print("[OK] Pearl started and sentinel cleared.")
            sys.exit(0)
        elif cmd == "status":
            run_watchdog_cycle()
            if STATUS_JSON.exists():
                print(STATUS_JSON.read_text(encoding="utf-8"))
            sys.exit(0)

    acquire_singleton()
    atexit.register(release_singleton)
    try:
        watchdog_loop()
    finally:
        release_singleton()
