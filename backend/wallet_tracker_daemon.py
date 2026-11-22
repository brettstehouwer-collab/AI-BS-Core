"""
wallet_tracker_daemon.py — Background daemon to monitor Dogecoin passive income.

Queries the public Dogechain API periodically to fetch the live balance of the
DOGE_WALLET specified in the .env file.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] wallet_tracker: %(message)s",
)
logger = logging.getLogger(__name__)

# Config
WORKSPACE_DIR = Path(__file__).parent.resolve()
ENV_FILE = WORKSPACE_DIR / ".env"
OUTPUT_FILE = WORKSPACE_DIR / "wallet_telemetry.json"
POLL_INTERVAL_SECONDS = 300  # 5 minutes


def load_doge_wallet():
    """Extract DOGE_WALLET directly from .env without third-party libraries."""
    env_file = ENV_FILE
    if not env_file.exists():
        env_file = WORKSPACE_DIR.parent / ".env"

    if not env_file.exists():
        logger.error(f"Cannot find .env file at {ENV_FILE} or {WORKSPACE_DIR.parent / '.env'}")
        return None

    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DOGE_WALLET="):
                    return line.split("=", 1)[1].strip()
    except Exception as e:
        logger.error(f"Error reading .env: {e}")
    return None


def fetch_balance(address: str) -> str:
    """Fetch DOGE balance from BlockCypher API."""
    url = f"https://api.blockcypher.com/v1/doge/main/addrs/{address}/balance"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            # Balance is returned in koinu (1 DOGE = 10^8 koinu)
            balance_doge = data.get("balance", 0) / 1e8
            return f"{balance_doge:.8f}"
    except Exception as e:
        logger.error(f"Failed to fetch balance: {e}")
    return None


def write_telemetry(address: str, balance: str):
    """Write telemetry JSON to disk for the backend to serve."""
    payload = {
        "status": "active",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "address": address,
        "balance_doge": balance,
        "currency": "DOGE",
        "client_id": "stehouwer_publishing",
    }

    try:
        # Write to temp file then rename to avoid partial reads by backend
        temp_file = OUTPUT_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        temp_file.replace(OUTPUT_FILE)
        logger.info(f"Updated telemetry: {balance} DOGE")
    except Exception as e:
        logger.error(f"Failed to write telemetry: {e}")


def main():
    logger.info("Wallet Tracker Daemon starting up...")

    # Check if we should skip our own PID management
    if os.environ.get("DAEMON_MANAGER_OWNED") != "1":
        pid_file = WORKSPACE_DIR / "wallet_tracker_daemon.pid"
        pid_file.write_text(str(os.getpid()))

    while True:
        address = load_doge_wallet()
        if not address:
            logger.warning("No DOGE_WALLET found in .env. Retrying in 60s...")
            time.sleep(60)
            continue

        balance = fetch_balance(address)
        if balance is not None:
            write_telemetry(address, balance)

        # Sleep for the interval
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
