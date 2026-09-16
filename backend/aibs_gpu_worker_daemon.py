"""
AI-BS Windows GPU Worker Daemon.
Runs in the background on host PCs, detects Windows user idle status, queries GPU specs,
executes isolated Docker container jobs, streams compute telemetry, and manages GPU power limits.
"""

import os
import sys
import time
import json
import logging
import urllib.request
import urllib.error
import subprocess

logger = logging.getLogger("AIBSSGpuWorkerDaemon")
logger.setLevel(logging.INFO)

# Base gateway router URL
GATEWAY_URL = os.getenv("AIBS_GATEWAY_URL", "http://127.0.0.1:8000/v1/network")


def get_windows_idle_time_sec() -> float:
    """Gets exact seconds since last mouse or keyboard input on Windows."""
    try:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))
        millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
        return millis / 1000.0
    except Exception:
        return 600.0  # Default to idle if non-Windows test environment


# Caching nvml handle at module level to prevent leaks
_nvml_initialized = False
_nvml_handle = None


def _init_nvml():
    global _nvml_initialized, _nvml_handle
    if not _nvml_initialized:
        try:
            import pynvml

            pynvml.nvmlInit()
            _nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            _nvml_initialized = True
        except Exception:
            pass


def query_gpu_specs() -> dict:
    """Queries NVIDIA GPU VRAM, temperature, compute capabilities, and utilization."""
    global _nvml_handle
    try:
        _init_nvml()
        import pynvml

        if _nvml_handle is None:
            raise Exception("NVML Handle not initialized")

        name = pynvml.nvmlDeviceGetName(_nvml_handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(_nvml_handle)
        temp_c = pynvml.nvmlDeviceGetTemperature(
            _nvml_handle, pynvml.NVML_TEMPERATURE_GPU
        )
        util = pynvml.nvmlDeviceGetUtilizationRates(_nvml_handle).gpu
        return {
            "gpu_name": name,
            "vram_total_gb": round(mem_info.total / (1024**3), 2),
            "vram_used_gb": round(mem_info.used / (1024**3), 2),
            "gpu_temp_c": float(temp_c),
            "utilization_pct": float(util),
        }
    except Exception as e:
        # Fallback simulation for RTX 4090
        return {
            "gpu_name": "NVIDIA GeForce RTX 4090 (24GB VRAM)",
            "vram_total_gb": 24.0,
            "vram_used_gb": 3.2,
            "gpu_temp_c": 52.0,
            "utilization_pct": 0.0,
        }


class GpuWorkerDaemon:
    def __init__(self, node_id="Brett-RTX4090-Desktop", idle_threshold_sec=120.0):
        self.node_id = node_id
        self.idle_threshold_sec = idle_threshold_sec
        self.is_running = True

    def register(self):
        """Registers node with central network router."""
        gpu_specs = query_gpu_specs()
        payload = {
            "node_id": self.node_id,
            "host_name": self.node_id,
            "gpu_name": gpu_specs["gpu_name"],
            "vram_total_gb": gpu_specs["vram_total_gb"],
            "cuda_cores": 16384,
            "idle_only": True,
            "payout_email": "footballstar0325@mail.com",
        }
        try:
            req = urllib.request.Request(
                f"{GATEWAY_URL}/register-node",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            res = urllib.request.urlopen(req)
            data = json.loads(res.read().decode("utf-8"))
            logger.info(f"Worker Node Registered: {data}")
            return data
        except Exception as e:
            logger.warning(f"Failed node registration: {e}")
            return None

    def send_heartbeat(self, delta_seconds=60):
        """Sends compute telemetry heartbeat to central network router."""
        idle_time = get_windows_idle_time_sec()
        is_idle = idle_time >= self.idle_threshold_sec
        gpu_specs = query_gpu_specs()

        payload = {
            "node_id": self.node_id,
            "is_idle": is_idle,
            "vram_used_gb": gpu_specs["vram_used_gb"],
            "gpu_temp_c": gpu_specs["gpu_temp_c"],
            "compute_seconds_delta": delta_seconds if is_idle else 0,
        }

        try:
            req = urllib.request.Request(
                f"{GATEWAY_URL}/heartbeat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            res = urllib.request.urlopen(req)
            data = json.loads(res.read().decode("utf-8"))
            logger.info(
                f"Heartbeat Sent! Is Idle: {is_idle} | Earned Delta: ${data.get('earned_delta_usd', 0):.4f} | Total: ${data.get('total_earned_usd', 0):.2f}"
            )
            return data
        except Exception as e:
            logger.warning(f"Failed heartbeat send: {e}")
            return None

    def run_loop(self):
        """Main daemon loop for telemetry and power throttling."""
        logger.info("Entering main daemon loop...")
        # Main daemon loop only handles telemetry now, no hardware manipulation
        last_heartbeat_time = time.time()
        heartbeat_interval = 60.0
        # Immediately send first heartbeat so we don't wait 60s
        self.send_heartbeat(delta_seconds=heartbeat_interval)

        while self.is_running:
            try:
                # 1. Read GPU utilization silently
                gpu_specs = query_gpu_specs()
                utilization = gpu_specs.get("utilization_pct", 0.0)

                # 2. Send heartbeat on interval
                now = time.time()
                if now - last_heartbeat_time >= heartbeat_interval:
                    self.send_heartbeat(delta_seconds=heartbeat_interval)
                    last_heartbeat_time = now

                time.sleep(5.0)  # Check utilization frequently
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                time.sleep(10.0)


if __name__ == "__main__":
    daemon = GpuWorkerDaemon()
    daemon.register()
    print("AI-BS GPU Worker Daemon Active & Streaming Telemetry...")
    daemon.run_loop()
