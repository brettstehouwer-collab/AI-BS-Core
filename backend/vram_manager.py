import os
import sys
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
import requests
import psutil

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from core.event_bus import matrix_event_bus
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VRAMArbiter] %(message)s")

class VRAMOrchestrator:
    """
    Active GPU VRAM Arbiter for RTX 4090 (24GB VRAM).
    Dynamically arbitrates GPU memory between ComfyUI generation, Ollama LLM inference (ports 11434 & 11435),
    Unreal Engine 5 Pixel Streaming, and NVENC Broadcast encoders.
    """
    def __init__(
        self,
        total_vram_gb: float = 24.0,
        ollama_hosts: Optional[List[str]] = None,
        comfy_host: str = "http://127.0.0.1:8189"
    ):
        self.total_vram_gb = total_vram_gb
        self.ollama_hosts = ollama_hosts or ["http://127.0.0.1:11434", "http://127.0.0.1:11435"]
        self.comfy_host = comfy_host
        self.allocations: Dict[str, float] = {}
        self.active_primary_model = "stehouwer_llm"
        self._lock = asyncio.Lock() if sys.version_info >= (3, 7) else None

    def flush_torch_cuda_cache(self):
        """Forces local PyTorch process to release unreferenced GPU tensors and IPC shared memory."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                logging.info("[VRAM] Flushed local PyTorch CUDA caching allocator")
            except Exception as e:
                logging.debug(f"[VRAM] Torch CUDA flush note: {e}")

    def notify_event_bus(self, event_name: str = "allocation_changed"):
        """Publishes live VRAM metrics across Matrix Event Bus."""
        if EVENT_BUS_AVAILABLE:
            try:
                data = self.get_detailed_telemetry()
                asyncio.create_task(matrix_event_bus.publish("vram", event_name, data, source="vram_manager"))
            except Exception:
                pass

    def get_detailed_telemetry(self) -> Dict[str, Any]:
        cuda_allocated = 0.0
        cuda_reserved = 0.0
        if TORCH_AVAILABLE and torch.cuda.is_available():
            cuda_allocated = round(torch.cuda.memory_allocated(0) / (1024 ** 3), 2)
            cuda_reserved = round(torch.cuda.memory_reserved(0) / (1024 ** 3), 2)

        return {
            "total_vram_gb": self.total_vram_gb,
            "allocated_budget_gb": round(self.used_vram_gb, 2),
            "free_budget_gb": round(self.free_vram_gb, 2),
            "cuda_allocated_gb": cuda_allocated,
            "cuda_reserved_gb": cuda_reserved,
            "allocations": self.allocations,
            "unreal_active": self.check_unreal_engine_active()
        }

    @property
    def used_vram_gb(self) -> float:
        return sum(self.allocations.values())

    @property
    def free_vram_gb(self) -> float:
        return max(0.0, self.total_vram_gb - self.used_vram_gb)

    def offload_ollama_vram(self, model_name: Optional[str] = None) -> bool:
        """Flushes Ollama model weights from GPU VRAM across all configured Ollama instances."""
        target_model = model_name or self.active_primary_model
        success = False
        for host in self.ollama_hosts:
            try:
                url = f"{host}/api/generate"
                payload = {"model": target_model, "keep_alive": "0s"}
                res = requests.post(url, json=payload, timeout=2.0)
                if res.status_code == 200:
                    logging.info(f"Offloaded Ollama model '{target_model}' from {host} (keep_alive: 0s)")
                    success = True
            except Exception as e:
                logging.debug(f"Host {host} offload check: {e}")
        if success:
            self.allocations.pop("ollama", None)
        return success

    def warm_ollama_vram(self, model_name: Optional[str] = None, host: Optional[str] = None) -> bool:
        """Pre-warms Ollama model weights back into GPU VRAM in background."""
        target_model = model_name or self.active_primary_model
        target_host = host or self.ollama_hosts[0]
        try:
            url = f"{target_host}/api/generate"
            payload = {"model": target_model, "prompt": "", "keep_alive": "10m"}
            requests.post(url, json=payload, timeout=2.0)
            logging.info(f"Pre-warmed Ollama model '{target_model}' into VRAM on {target_host}")
            self.allocations["ollama"] = 8.0  # Approximate LLM allocation
            return True
        except Exception as e:
            logging.warning(f"Failed to warm Ollama VRAM on {target_host}: {e}")
        return False

    def offload_comfyui_vram(self) -> bool:
        """Invokes ComfyUI /free API to purge cached diffusion weights and empty PyTorch CUDA cache."""
        try:
            url = f"{self.comfy_host}/free"
            payload = {"unload_models": True, "free_memory": True}
            res = requests.post(url, json=payload, timeout=2.5)
            if res.status_code == 200:
                logging.info("Successfully offloaded ComfyUI diffusion models & flushed CUDA cache")
                self.allocations.pop("comfyui", None)
                return True
        except Exception as e:
            logging.debug(f"ComfyUI free endpoint skipped: {e}")
        return False

    def check_unreal_engine_active(self) -> bool:
        """Checks if Unreal Editor / Engine process is active and consuming GPU memory."""
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'] or ''
                if 'unrealeditor' in name.lower() or 'ue_5' in name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def request_gpu_budget(self, requester: str, required_vram_gb: float, auto_evict: bool = True) -> bool:
        """
        Requests GPU memory budget for a heavy workload (e.g. ComfyUI Flux render).
        If memory is insufficient and auto_evict is True, it offloads idle LLMs and triggers ComfyUI cache purge.
        """
        logging.info(f"Allocation request: '{requester}' needs {required_vram_gb} GB (Free: {self.free_vram_gb:.1f} GB)")

        if self.free_vram_gb >= required_vram_gb:
            self.allocations[requester] = required_vram_gb
            self.flush_torch_cuda_cache()
            self.notify_event_bus("budget_allocated")
            return True

        if auto_evict:
            logging.info(f"VRAM budget tight ({self.free_vram_gb:.1f} GB free). Triggering proactive offloads...")
            self.offload_ollama_vram()
            self.offload_comfyui_vram()
            self.flush_torch_cuda_cache()
            if self.free_vram_gb >= required_vram_gb:
                self.allocations[requester] = required_vram_gb
                self.notify_event_bus("budget_allocated")
                return True

        if self.free_vram_gb >= required_vram_gb:
            self.allocations[requester] = required_vram_gb
            self.notify_event_bus("budget_allocated")
            return True

        logging.warning(f"GPU Allocation Rejected for '{requester}'. Needed: {required_vram_gb} GB, Available: {self.free_vram_gb:.1f} GB")
        return False

    def release_gpu_budget(self, requester: str, restore_ollama: bool = True) -> float:
        """Releases allocated VRAM, cleans ComfyUI cache if ComfyUI finished, and optionally warms the primary LLM."""
        freed = self.allocations.pop(requester, 0.0)
        logging.info(f"Released {freed:.1f} GB VRAM from '{requester}'. Current free: {self.free_vram_gb:.1f} GB")

        if requester == "comfyui":
            self.offload_comfyui_vram()

        self.flush_torch_cuda_cache()
        self.notify_event_bus("budget_released")

        if restore_ollama and "ollama" not in self.allocations:
            try:
                self.warm_ollama_vram()
            except Exception:
                pass
        return freed

vram_orchestrator = VRAMOrchestrator()
vram_arbiter = vram_orchestrator

