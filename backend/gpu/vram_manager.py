"""Conservative cooperative reservations, separate from actual device allocation."""
from __future__ import annotations

from .gpu_telemetry import finite_number


def available_budget_mib(telemetry: dict, profile: dict, reserved_mib: float = 0) -> float:
    gpu = telemetry.get("gpu") or {}
    total = finite_number(gpu.get("memory_total_mib"))
    used = finite_number(gpu.get("memory_used_mib"))
    free = finite_number(gpu.get("memory_free_mib"))
    if not telemetry.get("available") or any(value is None for value in (total, used, free)):
        return 0.0
    return max(0.0, min(total * profile["vram_fraction"] - used, free) - profile["reserve_mib"] - reserved_mib)
