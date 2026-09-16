import subprocess
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CHIA_CLI = r"C:\Users\footb\AppData\Local\Programs\Chia\resources\app.asar.unpacked\daemon\chia.exe"
TELEMETRY_FILE = Path(__file__).parent.parent / "logs" / "chia_plotter_telemetry.json"


def get_chia_stats():
    """
    Runs `chia farm summary` and parses the output.
    If the daemon is offline, returns an error status.
    Also reads the plotter telemetry JSON.
    """
    stats = {
        "status": "Offline",
        "total_plots": "0",
        "plot_size": "0.000 GiB",
        "estimated_time_to_win": "Unknown",
        "total_chia_farmed": "0.0",
        "connection_error": False,
        "plotter_telemetry": {
            "status": "Offline",
            "progress": 0.0,
            "total_plots_done": 0,
            "target_plots": 0,
        },
    }

    # Attempt to read plotter telemetry
    if TELEMETRY_FILE.exists():
        try:
            with open(TELEMETRY_FILE, "r") as f:
                stats["plotter_telemetry"] = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read plotter telemetry: {e}")
            stats["plotter_telemetry"]["status"] = "Telemetry Error"

    try:
        # Run chia farm summary
        result = subprocess.run(
            [CHIA_CLI, "farm", "summary"], capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            if "Cannot connect to host localhost" in result.stderr:
                stats["connection_error"] = True
                stats["status"] = "Daemon Offline"
            else:
                stats["status"] = "Error"
            return stats

        output = result.stdout

        # Parse the output
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("Farming status:"):
                stats["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("Total chia farmed:"):
                stats["total_chia_farmed"] = line.split(":", 1)[1].strip()
            elif line.startswith("Plot count for all harvesters:"):
                stats["total_plots"] = line.split(":", 1)[1].strip()
            elif line.startswith("Total size of plots:"):
                stats["plot_size"] = line.split(":", 1)[1].strip()
            elif line.startswith("Expected time to win:"):
                stats["estimated_time_to_win"] = line.split(":", 1)[1].strip()

        return stats

    except Exception as e:
        logger.error(f"Failed to fetch chia stats: {e}")
        stats["status"] = "Error fetching data"
        stats["connection_error"] = True
        return stats


def start_chia_daemon():
    """Starts the chia daemon in the background."""
    try:
        # Start daemon
        subprocess.Popen([CHIA_CLI, "start", "farmer-no-wallet"])
        return True
    except Exception as e:
        logger.error(f"Failed to start chia daemon: {e}")
        return False


def stop_chia_daemon():
    """Stops the chia daemon."""
    try:
        subprocess.run([CHIA_CLI, "stop", "all", "-d"], capture_output=True, timeout=15)
        return True
    except Exception as e:
        logger.error(f"Failed to stop chia daemon: {e}")
        return False
