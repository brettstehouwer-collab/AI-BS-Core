import asyncio
import logging
import psutil
import subprocess
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] Plotter: %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────
# Directories matching user batch script
TEMP_DIR = os.getenv("CHIA_TEMP_DIR", r"S:\chia-temp")
FINAL_DIR = os.getenv("CHIA_FINAL_DIR", r"S:\chia-final")

# Keys matching user batch script
FARMER_PUBLIC_KEY = os.getenv(
    "CHIA_FARMER_PUBKEY",
    "b392acc23c32aa2606d426cc8c1b9f72984780e2feae81b4d0c9f1c0d77a7e3f24dd29172b0d0e61929b6b30aab7c29d",
)
POOL_PUBLIC_KEY = os.getenv(
    "CHIA_POOL_PUBKEY",
    "89ba46428c05c372de18c0c0aad7d3256d6850c2ae7d3d238f1bee2a422172e4c8a236adca7bfc959a07e57121fdcab6",
)

# Standard plotting settings
K_SIZE = 32
RAM_MB = int(os.getenv("CHIA_RAM_MB", "3400"))
THREADS = int(os.getenv("CHIA_THREADS", "2"))
BUCKETS = int(os.getenv("CHIA_BUCKETS", "128"))
PLOT_SIZE_GB = 108.8

# Resource guards
MAX_PLOTS = int(os.getenv("CHIA_MAX_PLOTS", "11"))  # Defaulting to batch script target
MAX_CPU_PERCENT = 98.0
MIN_FREE_TEMP_GB = 256
MIN_FREE_FINAL_GB = 110

TELEMETRY_FILE = Path(__file__).parent / "logs" / "chia_plotter_telemetry.json"


def get_plot_count() -> int:
    if not os.path.exists(FINAL_DIR):
        return 0
    return len([f for f in os.listdir(FINAL_DIR) if f.endswith(".plot")])


def check_resources() -> tuple[bool, str]:
    """Guard rails before triggering a new plot."""
    if MAX_PLOTS > 0 and get_plot_count() >= MAX_PLOTS:
        return False, f"Max plots reached ({MAX_PLOTS})"

    cpu = psutil.cpu_percent(interval=1.0)
    if cpu > MAX_CPU_PERCENT:
        return False, f"CPU usage too high ({cpu:.1f}%)"

    try:
        free_temp_gb = psutil.disk_usage(TEMP_DIR).free / (1024**3)
        free_final_gb = psutil.disk_usage(FINAL_DIR).free / (1024**3)
        if free_temp_gb < MIN_FREE_TEMP_GB:
            return (
                False,
                f"Insufficient temp space: {free_temp_gb:.1f} GB < {MIN_FREE_TEMP_GB} GB",
            )
        if free_final_gb < MIN_FREE_FINAL_GB:
            return (
                False,
                f"Insufficient final space: {free_final_gb:.1f} GB < {MIN_FREE_FINAL_GB} GB",
            )
    except Exception as e:
        return False, f"Disk check failed: {e}"

    return True, "Conditions optimal for standard plotting"


def write_telemetry(status: str, progress: float = 0.0):
    try:
        TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "status": status,
            "progress": round(progress, 2),
            "total_plots_done": get_plot_count(),
            "target_plots": MAX_PLOTS,
        }
        with open(TELEMETRY_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Failed to write telemetry: {e}")


def build_plot_command(chia_exe: str) -> list[str]:
    """Build standard chia plot command (N=1 since loop handles iteration)."""
    cmd = [
        chia_exe,
        "plots",
        "create",
        "-k",
        str(K_SIZE),
        "-b",
        str(RAM_MB),
        "-r",
        str(THREADS),
        "-u",
        str(BUCKETS),
        "-t",
        TEMP_DIR,
        "-d",
        FINAL_DIR,
        "-n",
        "1",
        "-f",
        FARMER_PUBLIC_KEY,
        "-p",
        POOL_PUBLIC_KEY,
    ]
    return cmd


async def run_plotter_loop():
    logger.info("Chia Plotter Daemon — Standard mode initialized.")
    write_telemetry("Starting up...")

    # Custom installation path provided by user
    chia_exe = r"C:\AI-BS\New folder\Chia\resources\app.asar.unpacked\daemon\chia.exe"

    if not os.path.exists(chia_exe):
        chia_exe = "chia.exe"  # Fallback to PATH

    while True:
        try:
            can_plot, reason = check_resources()

            if can_plot:
                logger.info(f"Starting plot: {reason}")
                write_telemetry("Plotting (0%)", 0.0)
                cmd = build_plot_command(chia_exe)
                logger.info(f"CMD: {' '.join(cmd)}")

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                logger.info(f"Standard Plotter PID: {proc.pid}")

                # Read output incrementally to parse progress
                current_progress = 0.0
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break

                    line_str = line.decode().strip()

                    # Basic progress heuristics for standard plotter
                    if "Computing table" in line_str:
                        # e.g., Computing table 2 (Phase 1)
                        match = re.search(r"Computing table (\d+)", line_str)
                        if match:
                            tbl = int(match.group(1))
                            current_progress = min(40.0, tbl * (40 / 7))
                            write_telemetry(
                                "Phase 1: Forward Propagation", current_progress
                            )
                    elif "Backpropagating on table" in line_str:
                        match = re.search(r"Backpropagating on table (\d+)", line_str)
                        if match:
                            tbl = 7 - int(match.group(1))
                            current_progress = 40.0 + min(20.0, tbl * (20 / 7))
                            write_telemetry(
                                "Phase 2: Backpropagation", current_progress
                            )
                    elif "Compressing tables" in line_str:
                        match = re.search(r"Compressing tables (\d+) and", line_str)
                        if match:
                            tbl = int(match.group(1))
                            current_progress = 60.0 + min(35.0, tbl * (35 / 7))
                            write_telemetry("Phase 3: Compression", current_progress)
                    elif "Write checkpoint tables" in line_str:
                        current_progress = 95.0
                        write_telemetry("Phase 4: Checkpoints", current_progress)

                await proc.wait()

                if proc.returncode == 0:
                    logger.info(
                        f"Plot complete. Total plots in {FINAL_DIR}: {get_plot_count()}"
                    )
                    write_telemetry("Plot Complete", 100.0)
                else:
                    logger.error(f"Plot failed (rc={proc.returncode})")
                    write_telemetry("Failed (Cooldown)", current_progress)

                logger.info("Cooling down 60s before next plot check...")
                await asyncio.sleep(60)

            else:
                logger.info(f"Plotting paused: {reason}")
                write_telemetry(f"Paused: {reason}", 0.0)
                await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Plotter loop error: {e}")
            write_telemetry("Error", 0.0)

        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_plotter_loop())
