"""Read-only inventory helpers. No driver, firmware, clock or power writes."""
from __future__ import annotations

import importlib.metadata
import platform
import subprocess
from typing import Any

from .gpu_telemetry import NvidiaSMITelemetry


def collect_inventory() -> dict[str, Any]:
    packages = {}
    for name in ("torch", "nvidia-cuda-runtime-cu12", "onnxruntime-gpu", "httpx"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    result = {"os": platform.platform(), "python": platform.python_version(),
              "packages": packages, "gpu": NvidiaSMITelemetry().read(),
              "cuda_runtime_note": "Driver-supported CUDA version and installed runtime packages are distinct.",
              "firmware_changed": False}
    try:
        process = subprocess.run(["nvidia-smi", "-q"], capture_output=True, text=True, timeout=5, check=False)
        result["nvidia_smi_query"] = {"returncode": process.returncode,
                                      "stdout": process.stdout if process.returncode == 0 else None}
    except (OSError, subprocess.SubprocessError) as exc:
        result["nvidia_smi_query"] = {"error_type": type(exc).__name__}
    return result
