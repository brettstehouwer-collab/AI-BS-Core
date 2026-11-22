#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NVME_DIR="${NVME_DIR:-/var/lib/ai_bs_kv}"
mkdir -p "${NVME_DIR}"

VLLM_PORT="${VLLM_PORT:-8009}"
API_PORT="${UNBOUNDED_ENGINE_PORT:-8089}"

echo "[AI-BS] Initializing NVMe Virtual Memory Tier at ${NVME_DIR}..."

# 1. Start vLLM with LMCache in background
"${SCRIPT_DIR}/start_vllm_daemon.sh" &
VLLM_PID=$!

echo "[AI-BS] vLLM Daemon initialized (PID: ${VLLM_PID}). Awaiting model readiness on port ${VLLM_PORT}..."

# 2. Wait for vLLM Health Endpoint
until curl -s "http://127.0.0.1:${VLLM_PORT}/health" > /dev/null; do
    sleep 2
done

echo "[AI-BS] Inference engine operational. Starting Continuous FastAPI Gateway on port ${API_PORT}..."

# 3. Start Unbounded API Engine
python3 "${SCRIPT_DIR}/unbounded_engine.py" &
API_PID=$!

trap "echo '[AI-BS] Halting Unbounded Stack...'; kill ${VLLM_PID} ${API_PID}; exit" SIGINT SIGTERM
wait
