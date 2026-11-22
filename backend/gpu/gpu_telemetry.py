"""Bounded read-only NVIDIA telemetry; unavailable values are never invented."""
from __future__ import annotations

import asyncio
import copy
import csv
import io
from importlib import import_module
import math
import subprocess
import threading
import time
from typing import Any

FIELDS = (
    "index", "uuid", "name", "pci.device_id", "driver_version", "vbios_version",
    "memory.total", "memory.used", "memory.free", "temperature.gpu", "power.draw",
    "power.limit", "utilization.gpu",
)
NUMERIC = {
    "index": "index", "memory.total": "memory_total_mib", "memory.used": "memory_used_mib",
    "memory.free": "memory_free_mib", "temperature.gpu": "temperature_c",
    "power.draw": "power_w", "power.limit": "power_limit_w", "utilization.gpu": "utilization_pct",
}


def finite_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def parse_nvidia_csv(raw: str) -> list[dict[str, Any]]:
    devices = []
    for row in csv.reader(io.StringIO(raw)):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != len(FIELDS):
            raise ValueError("unexpected_nvidia_smi_columns")
        device: dict[str, Any] = {}
        for field, value in zip(FIELDS, row):
            value = value.strip()
            device[NUMERIC.get(field, field.replace(".", "_"))] = finite_number(value) if field in NUMERIC else value
        devices.append(device)
    return devices


class NvidiaSMITelemetry:
    def __init__(self, *, gpu_index: int = 0, ttl_s: float = 2.0, timeout_s: float = 3.0, prefer_nvml: bool = False):
        if isinstance(gpu_index, bool) or not isinstance(gpu_index, int) or gpu_index < 0:
            raise ValueError("invalid_gpu_index")
        if not 0 <= ttl_s <= 10 or not 0 < timeout_s <= 10:
            raise ValueError("invalid_telemetry_bounds")
        self.gpu_index = gpu_index
        self.ttl_s, self.timeout_s = ttl_s, timeout_s
        self.prefer_nvml = prefer_nvml
        self._lock = threading.Lock()
        self._cache: dict[str, Any] | None = None
        self._sampled_monotonic = 0.0
        self._sensors = None
        self._sensors_monotonic = 0.0

    def _nvml_devices(self):
        # Optional NVIDIA Python bindings; reads only. Import/init happen on
        # demand in the telemetry worker, with balanced driver reference counts.
        api = import_module('pynvml')
        api.nvmlInit()
        try:
            def decoded(value):
                return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value
            count = api.nvmlDeviceGetCount()
            handle = api.nvmlDeviceGetHandleByIndex(self.gpu_index)
            memory = api.nvmlDeviceGetMemoryInfo(handle)
            pci = api.nvmlDeviceGetPciInfo(handle)
            # WDDM sensor queries can each block for tens of milliseconds.
            # Refresh allocation every admission; temperatures/power/utilization
            # retain an explicit, at-most-two-second age to bound that overhead.
            if self._sensors is None or time.monotonic() - self._sensors_monotonic >= min(self.ttl_s, 2.0):
                self._sensors = {
                    'temperature_c': api.nvmlDeviceGetTemperature(handle, api.NVML_TEMPERATURE_GPU),
                    'power_w': api.nvmlDeviceGetPowerUsage(handle) / 1000,
                    'power_limit_w': api.nvmlDeviceGetPowerManagementLimit(handle) / 1000,
                    'utilization_pct': api.nvmlDeviceGetUtilizationRates(handle).gpu}
                self._sensors_monotonic = time.monotonic()
            gpu = {'index': self.gpu_index, 'uuid': decoded(api.nvmlDeviceGetUUID(handle)),
                   'name': decoded(api.nvmlDeviceGetName(handle)),
                   'pci_device_id': f'0x{pci.pciDeviceId:08X}',
                   'driver_version': decoded(api.nvmlSystemGetDriverVersion()),
                   'vbios_version': decoded(api.nvmlDeviceGetVbiosVersion(handle)),
                   'memory_total_mib': memory.total / 1048576,
                   'memory_used_mib': memory.used / 1048576,
                   'memory_free_mib': memory.free / 1048576,
                   **self._sensors,
                   'sensor_age_s': round(time.monotonic() - self._sensors_monotonic, 4)}
            return gpu, count
        finally:
            api.nvmlShutdown()

    def read(self, *, fresh: bool = False) -> dict[str, Any]:
        with self._lock:
            if not fresh and self._cache is not None and time.monotonic() - self._sampled_monotonic < self.ttl_s:
                result = copy.deepcopy(self._cache)
                elapsed = time.monotonic() - self._sampled_monotonic
                result["age_s"] = round(elapsed, 4)
                gpu = result.get("gpu")
                if isinstance(gpu, dict) and "sensor_age_s" in gpu:
                    # The last allocation sample can already contain older
                    # sensors. Advance both ages on this copy, leaving the
                    # original sample unchanged for subsequent cache reads.
                    sensor_age = finite_number(gpu["sensor_age_s"])
                    gpu["sensor_age_s"] = round(sensor_age + elapsed, 4) if sensor_age is not None else None
                return result
            sampled = time.time()
            try:
                if self.prefer_nvml:
                    try:
                        selected, count = self._nvml_devices()
                        result = {'available': True, 'source': 'nvml', 'observed_at_unix': time.time(),
                                  'age_s': 0.0, 'gpu': selected, 'device_count': count}
                        self._cache, self._sampled_monotonic = result, time.monotonic()
                        return copy.deepcopy(result)
                    except Exception:
                        # Missing bindings, unsupported NVML query, or driver
                        # errors fall back to the bounded read-only CLI.
                        pass
                process = subprocess.run(
                    ["nvidia-smi", f"--query-gpu={','.join(FIELDS)}", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=self.timeout_s, check=False,
                )
                if process.returncode:
                    raise RuntimeError("nvidia_smi_nonzero")
                devices = parse_nvidia_csv(process.stdout)
                selected = next((device for device in devices if device["index"] == self.gpu_index), None)
                if selected is None:
                    raise ValueError("requested_gpu_not_observed")
                result = {"available": True, "source": "nvidia-smi", "observed_at_unix": sampled,
                          "age_s": 0.0, "gpu": selected, "device_count": len(devices)}
            except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
                result = {"available": False, "source": "nvidia-smi", "observed_at_unix": sampled,
                          "age_s": 0.0, "gpu": None, "error_type": type(exc).__name__}
            self._cache = result
            self._sampled_monotonic = time.monotonic()
            return copy.deepcopy(result)

    async def sample(self, *, fresh: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self.read, fresh=fresh)
