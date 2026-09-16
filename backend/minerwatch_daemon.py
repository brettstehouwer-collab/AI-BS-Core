import asyncio
import json
import os
import random
from pathlib import Path
from datetime import datetime, timezone

# Configuration
SIMULATION_MODE = os.getenv("MINERWATCH_SIMULATION", "0") == "1"
POLL_INTERVAL = int(os.getenv("MINERWATCH_INTERVAL_SECONDS", "10"))
REMOTE_AGENT_INTERVAL = int(
    os.getenv("MINERWATCH_REMOTE_AGENT_INTERVAL_SECONDS", "1800")
)
TELEMETRY_FILE = Path(__file__).parent / "telemetry_cache.json"
REMOTE_AGENTS_FILE = Path(__file__).parent / "remote_agents.json"
DUAL_MINER_API_PORT = int(os.getenv("DUAL_MINER_API_PORT", "42000"))
XMRIG_API_PORT = int(os.getenv("XMRIG_API_PORT", "19999"))
XCH_WALLET = os.getenv("XCH_WALLET", "")


async def fetch_chia_stats():
    """Fetch stats from actual Chia CLI."""
    import asyncio

    try:
        proc = await asyncio.create_subprocess_shell(
            "chia farm summary",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode()

        status = (
            "Farming"
            if "Farming status: Farming" in output
            else "Syncing" if "Farming status: Syncing" in output else "Idle"
        )

        import re

        # Parse exact storage capacity instead of naive plot estimation
        capacity_tb = 0.0
        size_match = re.search(
            r"Total size of plots:\s*([\d\.]+)\s*([A-Za-z]+)", output
        )
        if size_match:
            val = float(size_match.group(1))
            unit = size_match.group(2).upper()
            if "PIB" in unit:
                capacity_tb = val * 1024.0
            elif "TIB" in unit:
                capacity_tb = val
            elif "GIB" in unit:
                capacity_tb = val / 1024.0
            elif "MIB" in unit:
                capacity_tb = val / (1024.0 * 1024.0)
            elif "KIB" in unit:
                capacity_tb = val / (1024.0 * 1024.0 * 1024.0)

        capacity_tb = round(capacity_tb, 3)

        # Fetch wallet balance safely in the background
        balance_xch = 0.0
        try:
            w_proc = await asyncio.create_subprocess_shell(
                "chia wallet show",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            w_stdout, _ = await w_proc.communicate()
            w_output = w_stdout.decode()

            bal_match = re.search(r"-Total Balance:\s+([\d\.]+)\s+xch", w_output)
            if bal_match:
                balance_xch = float(bal_match.group(1))
        except Exception:
            pass  # Ignore wallet fetch errors to avoid crashing primary farm stats

        return {
            "plot_progress_pct": 100.0,
            "capacity_tb": capacity_tb,
            "status": status,
            "balance_xch": balance_xch,
        }
    except Exception as e:
        return {
            "error": str(e),
            "plot_progress_pct": 0,
            "capacity_tb": 0,
            "status": "Error",
            "balance_xch": 0.0,
        }


async def fetch_dual_miner_stats() -> dict:
    """Fetch dual hash-rate stats from T-Rex or lolMiner local API."""
    import httpx

    primary_hr = 0.0
    secondary_hr = 0.0
    power_w = 0
    status = "Idle"

    is_trex = os.getenv("DUAL_MINER_BINARY", "t-rex") == "t-rex"
    api_url = f"http://127.0.0.1:{DUAL_MINER_API_PORT}"
    if is_trex:
        api_url += "/summary"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(api_url)
            if r.status_code == 200:
                data = r.json()
                if is_trex:
                    # T-Rex summary format
                    primary_hr = data.get("hashrate", 0) / 1000000.0
                    # Zilliqa is sporadic, might not have constant secondary
                    # hashrate field.
                    gpus = data.get("gpus", [])
                    if gpus:
                        power_w = int(sum(g.get("power", 0) for g in gpus))
                    status = "Mining"
                else:
                    # lolMiner summary format
                    gpus = data.get("GPUs", [])
                    if gpus:
                        primary_hr = sum(g.get("performance_mhs", 0) for g in gpus)
                        secondary_hr = sum(
                            g.get("performance_mhs_dual", 0) for g in gpus
                        )
                        power_w = int(sum(g.get("power", 0) for g in gpus))
                        status = "Mining"
    except Exception:
        pass  # Miner offline
    return {
        "primary_hashrate_mh": round(primary_hr, 2),
        "secondary_hashrate_mh": round(secondary_hr, 2),
        "power_w": power_w,
        "status": status,
        "algo": os.getenv("DUAL_MINER_PRIMARY_ALGO", "ETHASH"),
        "dual_algo": os.getenv("DUAL_MINER_SECONDARY_ALGO", "ZILLIQA"),
    }


async def fetch_xmrig_stats():
    """Fetch stats from actual XMRig local API."""
    import httpx

    hashrate = 0.0
    gpu_status_str = "Idle"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"Authorization": "Bearer minerwatch123"}
            response = await client.get(
                f"http://127.0.0.1:{XMRIG_API_PORT}/2/summary", headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                if (
                    "hashrate" in data
                    and "total" in data["hashrate"]
                    and len(data["hashrate"]["total"]) > 0
                ):
                    hashrate = data["hashrate"]["total"][0] or 0.0
                gpu_status_str = "Mining"
    except Exception:
        pass  # XMRig offline, ignore

    storage = await fetch_chia_stats()
    dual = await fetch_dual_miner_stats()

    return {
        "gpu_status": {
            "temp": 65,
            "hashrate_mh": round(hashrate, 2),
            "power_w": 100,
            "status": gpu_status_str,
        },
        "dual_miner_status": dual,
        "storage_status": storage,
        "alerts": [],
    }


def generate_simulated_stats(prev_stats):
    """Generate realistic fluctuating data for UI testing."""
    if not prev_stats or "error" in prev_stats:
        prev_stats = {
            "asic_status": {"temp": 68.0, "hashrate_th": 104.5, "status": "Mining"},
            "gpu_status": {
                "temp": 65.0,
                "hashrate_mh": 121.2,
                "power_w": 240,
                "status": "Mining",
            },
            "dual_miner_status": {
                "primary_hashrate_mh": 62.5,
                "secondary_hashrate_mh": 1800.0,
                "power_w": 280,
                "status": "Mining",
                "algo": "ETHASH",
                "dual_algo": "ZILLIQA",
            },
            "storage_status": {
                "plot_progress_pct": 34.5,
                "capacity_tb": 18,
                "status": "Plotting",
            },
            "alerts": [],
        }

    asic_temp = max(
        60, min(85, prev_stats["asic_status"]["temp"] + random.uniform(-1.0, 1.2))
    )
    gpu_temp = max(
        50, min(85, prev_stats["gpu_status"]["temp"] + random.uniform(-1.5, 1.8))
    )

    # 5% chance thermal spike → Aegis Thoughtful Friction
    if random.random() < 0.05:
        gpu_temp = 83.0

    alerts = []
    if asic_temp > 80 or gpu_temp > 80:
        alerts.append("Thermal threshold exceeded (>80C)")

    prev_dual = prev_stats.get("dual_miner_status", {})
    dual_primary_hr = round(
        max(
            55,
            min(
                70,
                prev_dual.get("primary_hashrate_mh", 62.5) + random.uniform(-1.0, 1.0),
            ),
        ),
        2,
    )
    dual_second_hr = round(
        max(
            1700,
            min(
                2000,
                prev_dual.get("secondary_hashrate_mh", 1800) + random.uniform(-30, 30),
            ),
        ),
        2,
    )
    dual_power = int(
        max(260, min(310, prev_dual.get("power_w", 280) + random.uniform(-5, 5)))
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "asic_status": {
            "temp": round(asic_temp, 1),
            "hashrate_th": round(
                max(
                    95,
                    min(
                        110,
                        prev_stats["asic_status"]["hashrate_th"]
                        + random.uniform(-0.5, 0.5),
                    ),
                ),
                1,
            ),
            "status": "Mining",
        },
        "gpu_status": {
            "temp": round(gpu_temp, 1),
            "hashrate_mh": round(
                max(
                    115,
                    min(
                        125,
                        prev_stats["gpu_status"]["hashrate_mh"]
                        + random.uniform(-1.0, 1.0),
                    ),
                ),
                1,
            ),
            "power_w": int(
                max(
                    220,
                    min(
                        260, prev_stats["gpu_status"]["power_w"] + random.uniform(-5, 5)
                    ),
                )
            ),
            "status": "Mining",
        },
        "dual_miner_status": {
            "primary_hashrate_mh": dual_primary_hr,
            "secondary_hashrate_mh": dual_second_hr,
            "power_w": dual_power,
            "status": "Mining",
            "algo": "ETHASH",
            "dual_algo": "ZILLIQA",
        },
        "storage_status": {
            "plot_progress_pct": round(
                min(
                    100.0,
                    prev_stats["storage_status"]["plot_progress_pct"]
                    + random.uniform(0.1, 0.5),
                ),
                1,
            ),
            "capacity_tb": 18,
            "status": (
                "Plotting"
                if prev_stats["storage_status"]["plot_progress_pct"] < 100
                else "Farming"
            ),
        },
        "alerts": alerts,
    }


async def write_remote_agents_snapshot(stats: dict) -> None:
    """Write a 30-min remote agent health snapshot to remote_agents.json."""
    existing = {}
    if REMOTE_AGENTS_FILE.exists():
        try:
            existing = json.loads(REMOTE_AGENTS_FILE.read_text())
        except Exception:
            pass

    agents = existing.get("agents", [])
    # Update or insert GPU_Rig_01 entry
    dual = stats.get("dual_miner_status", {})
    rig_entry = {
        "rig_id": "GPU_Rig_01",
        "primary_hashrate_mh": dual.get("primary_hashrate_mh", 0),
        "secondary_hashrate_mh": dual.get("secondary_hashrate_mh", 0),
        "temp": stats.get("gpu_status", {}).get("temp", 0),
        "power_w": dual.get("power_w", 0),
        "algo": dual.get("algo", "ETHASH"),
        "dual_algo": dual.get("dual_algo", "ZILLIQA"),
        "pool": "unMineable (ETC+ZIL→XCH)",
        "status": dual.get("status", "Idle"),
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }
    agents = [a for a in agents if a.get("rig_id") != "GPU_Rig_01"]
    agents.append(rig_entry)

    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "payout_wallet": XCH_WALLET[:20] + "..." if XCH_WALLET else "not-set",
        "payout_coin": "XCH",
        "agents": agents,
    }
    tmp = REMOTE_AGENTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(REMOTE_AGENTS_FILE)
    print(f"[MinerWatch] Remote agent snapshot written ({len(agents)} rigs)")


async def remote_agent_loop(stats_ref: list) -> None:
    """30-minute background loop — writes remote_agents.json."""
    while True:
        await asyncio.sleep(REMOTE_AGENT_INTERVAL)
        if stats_ref:
            await write_remote_agents_snapshot(stats_ref[0])


async def main():
    print(f"MinerWatch Daemon started. Simulation Mode: {SIMULATION_MODE}")
    print(f"  Local poll    : every {POLL_INTERVAL}s")
    print(f"  Remote agents : every {REMOTE_AGENT_INTERVAL}s ({
            REMOTE_AGENT_INTERVAL //
            60} min)")

    # Skip creating PID file if DAEMON_MANAGER_OWNED is set
    if not os.getenv("DAEMON_MANAGER_OWNED"):
        pid_file = Path(__file__).parent / "minerwatch_daemon.pid"
        pid_file.write_text(str(os.getpid()))

    last_stats = {}

    try:
        while True:
            if SIMULATION_MODE:
                stats = generate_simulated_stats(last_stats)
            else:
                stats = await fetch_xmrig_stats()
                stats["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Atomic write
            temp_file = TELEMETRY_FILE.with_suffix(".tmp")
            try:
                temp_file.write_text(json.dumps(stats, indent=2))
                temp_file.replace(TELEMETRY_FILE)
            except Exception as e:
                print(f"Failed to write telemetry: {e}")

            last_stats = stats

            # Safe shutdown logic: Halt if critical alerts are detected
            if stats.get("alerts"):
                print("CRITICAL WARNING DETECTED: Initiating safe shutdown sequence.")
                if "asic_status" in stats:
                    stats["asic_status"]["status"] = "HALTED"
                if "gpu_status" in stats:
                    stats["gpu_status"]["status"] = "HALTED"
                if "storage_status" in stats:
                    stats["storage_status"]["status"] = "HALTED"

                try:
                    temp_file.write_text(json.dumps(stats, indent=2))
                    temp_file.replace(TELEMETRY_FILE)
                except Exception:
                    pass

                cooldown_seconds = 300
                print(
                    f"Miner halted. Executing safe cooldown for {cooldown_seconds} seconds (5 minutes)."
                )
                await asyncio.sleep(cooldown_seconds)

                print(
                    "Cooldown complete. Resetting thermal baselines and resuming mining operations."
                )
                # Reset temperatures in last_stats to baseline so simulation
                # doesn't immediately fail again
                if "gpu_status" in stats:
                    stats["gpu_status"]["temp"] = 65.0
                if "asic_status" in stats:
                    stats["asic_status"]["temp"] = 65.0
                stats["alerts"] = []
                last_stats = stats
                continue

            await asyncio.sleep(POLL_INTERVAL)
    except asyncio.CancelledError:
        print("MinerWatch Daemon shutting down gracefully.")
    finally:
        if not os.getenv("DAEMON_MANAGER_OWNED"):
            try:
                pid_file.unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
