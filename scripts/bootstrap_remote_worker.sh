#!/bin/bash
# ==============================================================================
# AI-BS Sovereign Distributed Cluster - Remote Worker Bootstrap Script
# Target: Spot GPU Instances (Vast.ai / Clore.ai / Ubuntu 22.04+ Containers)
# Connects to AI-BS NATS JetStream (Port 4222) and Temporal (Port 7233)
# ==============================================================================

set -e

AIBS_HOST_IP="${1:-host.ai-bs.local}"
AIBS_NATS_PORT="${2:-4222}"
AIBS_TEMPORAL_PORT="${3:-7233}"
NODE_IDENTIFIER="${4:-vast-worker-$(hostname)}"

echo "=== [AI-BS Cluster] Initializing Worker Node: ${NODE_IDENTIFIER} ==="
echo "=== Connecting to AI-BS Central Spine at ${AIBS_HOST_IP} ==="

# 1. System packages & CUDA driver checks
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get install -y --no-install-recommends \
    curl wget git jq python3 python3-pip python3-venv \
    ca-certificates net-tools

# 2. Check NVIDIA GPU & VRAM
if command -v nvidia-smi &> /dev/null; then
    echo "=== GPU Detected ==="
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
    echo "[WARNING] No nvidia-smi found! Running in CPU fallback mode."
fi

# 3. Create isolated worker environment
VENV_PATH="/opt/aibs_worker_venv"
python3 -m venv "${VENV_PATH}"
source "${VENV_PATH}/bin/activate"

pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir \
    nats-py \
    temporalio \
    psutil \
    requests \
    websockets

# 4. Generate Python Worker Daemon
cat << 'EOF' > /opt/aibs_worker_daemon.py
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
import nats
import psutil

HOST_IP = os.getenv("AIBS_HOST_IP", "127.0.0.1")
NATS_PORT = os.getenv("AIBS_NATS_PORT", "4222")
NODE_ID = os.getenv("NODE_IDENTIFIER", "worker_node")

def get_gpu_telemetry():
    telemetry = {"gpus": [], "driver": "N/A"}
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            text=True, timeout=5
        )
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                telemetry["gpus"].append({
                    "name": parts[0],
                    "total_mb": float(parts[1]),
                    "used_mb": float(parts[2]),
                    "free_mb": float(parts[3]),
                    "util_pct": float(parts[4]),
                    "temp_c": float(parts[5]),
                })
    except Exception:
        pass
    return telemetry

async def main():
    nats_url = f"nats://{HOST_IP}:{NATS_PORT}"
    print(f"Connecting to NATS JetStream at {nats_url}...")
    nc = None
    while True:
        try:
            nc = await nats.connect(nats_url, connect_timeout=5, max_reconnect_attempts=60)
            print("Connected to AI-BS NATS Spine!")
            break
        except Exception as e:
            print(f"Waiting for host connection ({e})... retrying in 5s")
            await asyncio.sleep(5)

    async def handle_task(msg):
        data = json.loads(msg.data.decode())
        print(f"Received task: {data.get('task_id')}")
        # Acknowledge receipt
        await msg.respond(json.dumps({"status": "ACCEPTED", "node_id": NODE_ID}).encode())

    await nc.subscribe(f"aibs.cluster.tasks.{NODE_ID}", cb=handle_task)
    await nc.subscribe("aibs.cluster.tasks.broadcast", cb=handle_task)

    # Telemetry Heartbeat Loop
    while True:
        try:
            gpu_data = get_gpu_telemetry()
            payload = {
                "node_id": NODE_ID,
                "timestamp": time.time(),
                "hostname": platform.node(),
                "cpu_percent": psutil.cpu_percent(),
                "ram_percent": psutil.virtual_memory().percent,
                "gpu_telemetry": gpu_data,
                "status": "ONLINE"
            }
            await nc.publish(f"aibs.cluster.heartbeats.{NODE_ID}", json.dumps(payload).encode())
        except Exception as err:
            print(f"Heartbeat error: {err}")
        await asyncio.sleep(5.0)

if __name__ == "__main__":
    asyncio.run(main())
EOF

# 5. Launch Worker Daemon in Background
export AIBS_HOST_IP
export AIBS_NATS_PORT
export NODE_IDENTIFIER

echo "=== Starting AI-BS Remote Worker Background Daemon ==="
python3 /opt/aibs_worker_daemon.py > /var/log/aibs_worker.log 2>&1 &

echo "=== [SUCCESS] AI-BS Remote Worker Node is Online and Federated ==="
