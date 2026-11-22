"""Admission health checks. Existing external workloads are never terminated."""
from __future__ import annotations

import time
from .gpu_telemetry import finite_number


class StabilitySupervisor:
    def __init__(self, *, max_telemetry_age_s: float = 10.0):
        self.max_telemetry_age_s = max_telemetry_age_s
        self._realtime = None

    def assess(self, telemetry: dict, profile: dict) -> str | None:
        if not telemetry.get("available"):
            return "telemetry_unavailable"
        age = finite_number(telemetry.get("age_s"))
        observed = finite_number(telemetry.get("observed_at_unix"))
        if age is None or age < 0 or age > self.max_telemetry_age_s or observed is None:
            return "telemetry_stale"
        if time.time() - observed > self.max_telemetry_age_s + 1 or observed - time.time() > 2:
            return "telemetry_stale"
        gpu = telemetry.get("gpu") or {}
        if not isinstance(gpu, dict):
            return "telemetry_invalid"
        total, used, free, temperature = (finite_number(gpu.get(key)) for key in (
            "memory_total_mib", "memory_used_mib", "memory_free_mib", "temperature_c"))
        if any(value is None for value in (total, used, free, temperature)):
            return "telemetry_incomplete"
        if total <= 0 or min(used, free) < 0 or used > total or free > total or used + free > total + 64 or temperature < 0:
            return "telemetry_invalid"
        if temperature >= profile["max_temperature_c"]:
            return "thermal_limit"
        power, limit = (finite_number(gpu.get(key)) for key in ("power_w", "power_limit_w"))
        if power is not None and limit is not None and limit > 0 and power > limit * 1.05:
            return "power_limit"
        return None

    def record_realtime(self, *, latency_ms: float, deadline_ms: float, underruns: int = 0) -> None:
        latency, deadline = finite_number(latency_ms), finite_number(deadline_ms)
        if latency is None or deadline is None or latency < 0 or deadline <= 0:
            raise ValueError("invalid_realtime_observation")
        if isinstance(underruns, bool) or not isinstance(underruns, int) or underruns < 0:
            raise ValueError("invalid_underruns")
        self._realtime = {"latency_ms": latency, "deadline_ms": deadline, "underruns": underruns,
                          "observed_monotonic": time.monotonic()}

    def realtime_pressure(self) -> bool:
        observation = self._realtime
        return bool(observation and time.monotonic() - observation["observed_monotonic"] < 5
                    and (observation["underruns"] > 0 or observation["latency_ms"] > observation["deadline_ms"]))

    def snapshot(self) -> dict:
        observation = self._realtime
        return {"realtime_pressure": self.realtime_pressure(),
                "realtime_observation": {key: value for key, value in observation.items() if key != "observed_monotonic"}
                if observation else None, "existing_workloads_preempted": False}
