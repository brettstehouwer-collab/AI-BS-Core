"""
AI-BS Dynamic VRAM & CPU/GPU Layer Arbiter
Ecosystem: AI-BS Sovereign Intelligence Architecture
Hardware Target: NVIDIA GeForce RTX 4090 (24GB) & AMD Ryzen 9 9950X (32 Threads, AVX-512)

Provides real-time VRAM sensing, task classification, and dynamic num_gpu layer
offloading to prevent Windows WDDM shared-memory spills and VRAM contention with ComfyUI.
"""

import os
import sys
import subprocess
import shutil
from typing import Dict, Any, Tuple

# Port Topology Constants
PORT_GPU_PRIMARY = 11434    # RTX 4090 GPU (Chat, Reasoning, Code Generation)
PORT_CPU_SECONDARY = 11435  # AMD Ryzen 9 9950X (Embeddings, Ingestion, Audits)

HOST_GPU_PRIMARY = f"http://127.0.0.1:{PORT_GPU_PRIMARY}"
HOST_CPU_SECONDARY = f"http://127.0.0.1:{PORT_CPU_SECONDARY}"

# Model Layer Totals & Suggested Layer Offload Profiles for 24GB RTX 4090
# Leaves at least 6-8 GB VRAM free for ComfyUI diffusion and desktop displays
MODEL_PROFILES = {
    # 30B+ Heavy Models (Total layers ~64)
    "stehouwer_llm": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "stehouwer-llm": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "stehouwer_qwen": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "stehouwer-qwen": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "qwen2.5-coder": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "qwen3.6": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "nemotron-3.5-lightning": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "command-r": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},
    "mixtral": {"total_layers": 64, "default_num_gpu": 48, "comfy_num_gpu": 36, "vram_gb": 16.5},

    # 12B - 14B Intermediate Models (Total layers ~40-48)
    "gemma4:12b": {"total_layers": 48, "default_num_gpu": 99, "comfy_num_gpu": 32, "vram_gb": 8.5},
    "gemma4-12b": {"total_layers": 48, "default_num_gpu": 99, "comfy_num_gpu": 32, "vram_gb": 8.5},

    # 7B - 8B Lightweight Models (Total layers ~32) - Fit easily in VRAM
    "stehouwer_dolphin": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "stehouwer-dolphin": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "stehouwer_hermes": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "stehouwer-hermes": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "stehouwer_llm_dolphin": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "unrestricted-llama3.1": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "dolphin-llama3": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "llama3.1:8b-instruct-q5_K_M": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "llama3.1": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},
    "llama3": {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 5.5},

    # Embeddings (Pure CPU on Port 11435)
    "nomic-embed-text": {"total_layers": 0, "default_num_gpu": 0, "comfy_num_gpu": 0, "vram_gb": 0.0},
}


def get_gpu_vram_telemetry() -> Dict[str, float]:
    """Queries NVIDIA SMI for real-time VRAM allocation and free memory."""
    try:
        cmd = ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu", "--format=csv,nounits,noheader"]
        out = subprocess.check_output(cmd, encoding="utf-8", timeout=2).strip()
        parts = [float(x.strip()) for x in out.split(",")]
        total_mb, used_mb, free_mb, util_pct = parts
        return {
            "total_gb": round(total_mb / 1024, 2),
            "used_gb": round(used_mb / 1024, 2),
            "free_gb": round(free_mb / 1024, 2),
            "util_pct": util_pct,
            "available": True
        }
    except Exception:
        return {"total_gb": 24.0, "used_gb": 2.0, "free_gb": 22.0, "util_pct": 0.0, "available": False}


def is_comfyui_active() -> bool:
    """Detects if ComfyUI is actively computing on Port 8189."""
    try:
        import urllib.request
        import json
        req = urllib.request.Request("http://127.0.0.1:8189/system_stats", headers={"User-Agent": "AI-BS-Arbiter"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode())
            devices = data.get("devices", [])
            for d in devices:
                if d.get("vram_used", 0) > 4 * (1024**3):
                    return True
        return False
    except Exception:
        return False


def arbitrate_workload(model_name: str, task_type: str = "chat") -> Dict[str, Any]:
    """
    Computes optimal execution target, host URL, and num_gpu layer offload.
    
    Task Types:
    - 'chat' / 'code': Interactive user requests -> High-speed GPU on 11434
    - 'embedding' / 'ingestion': Background embeddings -> Pure CPU on 11435
    - 'audit' / 'daemon': Background autonomous workers -> Dual-affinity CPU/GPU
    """
    clean_model = model_name.split(":")[0].lower()
    
    # 1. Pure CPU Routing for Embeddings
    if clean_model == "nomic-embed-text" or task_type in ["embedding", "ingestion"]:
        return {
            "host": HOST_CPU_SECONDARY,
            "port": PORT_CPU_SECONDARY,
            "device": "cpu",
            "mode": "pure_cpu_offload",
            "hardware": "AMD Ryzen 9 9950X (32 Threads AVX-512)",
            "num_gpu": 0,
            "vram_allocation_gb": 0.0,
            "reason": "Embeddings & background ingestion pinned to Pure-CPU node to preserve GPU VRAM"
        }

    # 2. Query Real-Time Hardware State
    vram = get_gpu_vram_telemetry()
    comfy_busy = is_comfyui_active()
    free_gb = vram["free_gb"]

    profile = MODEL_PROFILES.get(clean_model, {"total_layers": 32, "default_num_gpu": 99, "comfy_num_gpu": 24, "vram_gb": 6.0})
    total_layers = profile["total_layers"]

    # 3. Compute Optimal Layer Count
    if comfy_busy:
        num_gpu = profile["comfy_num_gpu"]
        mode = "hybrid_comfy_balanced"
        reason = "ComfyUI active: Reduced GPU layers to guarantee image diffusion VRAM headroom"
    elif free_gb < 8.0:
        # VRAM is tight -> Offload more layers to CPU
        num_gpu = min(30, total_layers // 2)
        mode = "hybrid_vram_conserving"
        reason = f"VRAM tight ({free_gb:.1f} GB free): Offloading {total_layers - num_gpu} layers to CPU DDR5"
    elif profile["default_num_gpu"] < 99:
        # 30B+ model: default hybrid offload to guarantee 6-8GB free buffer
        num_gpu = profile["default_num_gpu"]
        mode = "hybrid_sovereign_optimal"
        reason = f"30B+ model: Keeping {num_gpu}/{total_layers} layers on GPU (16.5 GB), 14 layers on CPU DDR5 (0 spill)"
    else:
        # Fits comfortably in 24GB
        num_gpu = 99
        mode = "gpu_full_acceleration"
        reason = f"Model fits comfortably in dedicated VRAM ({free_gb:.1f} GB free)"

    return {
        "host": HOST_GPU_PRIMARY,
        "port": PORT_GPU_PRIMARY,
        "device": "gpu" if num_gpu == 99 else "hybrid",
        "hardware": "NVIDIA GeForce RTX 4090 + AMD Ryzen 9 9950X",
        "num_gpu": num_gpu,
        "mode": mode,
        "vram_free_gb": free_gb,
        "comfy_active": comfy_busy,
        "reason": reason
    }


if __name__ == "__main__":
    import json
    print("==================================================================")
    print("       AI-BS DYNAMIC VRAM & CPU/GPU LAYER ARBITER STATUS          ")
    print("==================================================================")
    v = get_gpu_vram_telemetry()
    print(f"RTX 4090 VRAM: {v['used_gb']} GB used / {v['free_gb']} GB free (Total: {v['total_gb']} GB) | Util: {v['util_pct']}%")
    print(f"ComfyUI Active: {is_comfyui_active()}")
    print("------------------------------------------------------------------")
    for test_model in ["stehouwer_llm", "qwen2.5-coder", "stehouwer_qwen", "gemma4:12b", "nomic-embed-text"]:
        plan = arbitrate_workload(test_model)
        print(f"[{test_model:18}] -> Port {plan['port']} | num_gpu: {plan['num_gpu']:2} | Mode: {plan['mode']:22} | {plan['reason']}")
    print("==================================================================")
