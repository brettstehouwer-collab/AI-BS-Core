#!/usr/bin/env bash
set -euo pipefail

# AI-BS Tier-3 NVMe KV Storage Allocation
NVME_MOUNT="${NVME_MOUNT:-/var/lib/ai_bs_kv}"
mkdir -p "${NVME_MOUNT}"

# Set Runtime Environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LMCACHE_CONFIG_FILE="${SCRIPT_DIR}/lmcache_config.yaml"
export VLLM_USE_V1=1
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

# Allocate non-conflicting port (Default 8009; port 8000 is reserved for Go Matrix Gateway)
VLLM_PORT="${VLLM_PORT:-8009}"
VLLM_MODEL="${VLLM_MODEL:-meta-llama/Llama-3.1-8B-Instruct}"

echo "[vLLM Daemon] Starting LMCache engine on 127.0.0.1:${VLLM_PORT} using ${VLLM_MODEL}..."

exec python3 -m vllm.entrypoints.openai.api_server \
  --model "${VLLM_MODEL}" \
  --port "${VLLM_PORT}" \
  --host 127.0.0.1 \
  --gpu-memory-utilization 0.88 \
  --swap-space 16 \
  --kv-cache-dtype fp8 \
  --enable-prefix-caching \
  --max-model-len 131072 \
  --kv-transfer-config '{"kv_connector":"LMCacheConnector","kv_role":"kv_both"}'
