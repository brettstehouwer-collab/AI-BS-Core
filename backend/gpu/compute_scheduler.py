"""Bounded cooperative scheduling for admitted local GPU inference calls."""
from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager
import inspect
import json
import math
from pathlib import Path
import time
import threading
from typing import Any

from .gpu_telemetry import NvidiaSMITelemetry, finite_number
from .model_residency import ModelResidencyManager
from .stability_supervisor import StabilitySupervisor
from .vram_manager import available_budget_mib


class GPUAdmissionError(RuntimeError):
    def __init__(self, reason: str, *, retryable: bool = False):
        self.reason, self.retryable = reason, retryable
        super().__init__(reason)


def latency_summary(samples) -> dict:
    ordered = sorted(samples)
    def percentile(q):
        if not ordered:
            return None
        position = (len(ordered) - 1) * q
        lower, upper = math.floor(position), math.ceil(position)
        return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 3)
    return {"sample_count": len(ordered), "p50_ms": percentile(.50), "p95_ms": percentile(.95), "p99_ms": percentile(.99)}


class AdaptiveGPUController:
    def __init__(self, telemetry_provider=None, *, profile: str = "balanced", max_queue: int = 32,
                 max_wait_s: float = 30.0, poll_s: float = 0.25):
        self.profiles = json.loads(Path(__file__).with_name("acceleration_profiles.yaml").read_text(encoding="utf-8"))
        if profile not in self.profiles or not self.profiles[profile].get("available", True):
            raise GPUAdmissionError("profile_unavailable")
        if isinstance(max_queue, bool) or not isinstance(max_queue, int) or not 1 <= max_queue <= 256:
            raise ValueError("invalid_queue_bound")
        if not 0 < max_wait_s <= 300 or not 0 < poll_s <= 5:
            raise ValueError("invalid_wait_bound")
        self.profile_name, self.profile = profile, dict(self.profiles[profile])
        self.max_queue, self.max_wait_s, self.poll_s = max_queue, max_wait_s, poll_s
        self.telemetry_provider = telemetry_provider or NvidiaSMITelemetry(prefer_nvml=True)
        self.residency, self.stability = ModelResidencyManager(), StabilitySupervisor()
        self._condition = asyncio.Condition()
        self._pending: list[dict] = []
        self._active: dict[int, dict] = {}
        self._sequence = 0
        self._allocation_epoch = 0
        self._completed, self._rejected, self._cancelled = 0, 0, 0
        self._queue_samples = deque(maxlen=256)
        self._service_samples = deque(maxlen=256)
        self._last_reason = None

    def update_residency(self, models: list[dict[str, Any]]) -> None:
        self.residency.update(models)

    def record_realtime_observation(self, *, latency_ms: float, deadline_ms: float, underruns: int = 0) -> None:
        self.stability.record_realtime(latency_ms=latency_ms, deadline_ms=deadline_ms, underruns=underruns)

    async def _telemetry(self, *, fresh: bool = False) -> dict:
        try:
            provider = self.telemetry_provider
            operation = provider.sample if hasattr(provider, "sample") else provider
            result = operation(fresh=fresh) if isinstance(provider, NvidiaSMITelemetry) else operation()
            if inspect.isawaitable(result):
                result = await result
            return result if isinstance(result, dict) else {"available": False}
        except Exception as exc:
            return {"available": False, "error_type": type(exc).__name__}

    async def set_profile(self, name: str) -> None:
        async with self._condition:
            if name not in self.profiles or not self.profiles[name].get("available", True):
                raise GPUAdmissionError("profile_unavailable")
            if self._active or self._pending:
                raise GPUAdmissionError("profile_in_use")
            self.profile_name, self.profile = name, dict(self.profiles[name])

    def _first_eligible(self):
        pressure = self.stability.realtime_pressure()
        candidates = [entry for entry in self._pending
                      if not pressure or entry["workload"] in ("audio", "video", "realtime")]
        return min(candidates, key=lambda item: (item["priority"], item["id"]), default=None)

    async def _acquire(self, model: str, workload: str, estimated_vram_mib: float, priority: int) -> dict:
        if not isinstance(model, str) or not model.strip() or len(model) > 256:
            raise ValueError("invalid_model")
        if not isinstance(workload, str) or not workload or len(workload) > 64:
            raise ValueError("invalid_workload")
        if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 100:
            raise ValueError("invalid_priority")
        if isinstance(estimated_vram_mib, bool) or not isinstance(estimated_vram_mib, (float, int)) or not math.isfinite(estimated_vram_mib) or estimated_vram_mib < 0:
            raise ValueError("invalid_vram_estimate")
        if estimated_vram_mib == 0 and not self.residency.contains(model):
            raise GPUAdmissionError("vram_estimate_required")
        loop = asyncio.get_running_loop()
        started, deadline = loop.time(), loop.time() + self.max_wait_s
        async with self._condition:
            if len(self._pending) >= self.max_queue:
                self._rejected += 1
                raise GPUAdmissionError("queue_full", retryable=True)
            self._sequence += 1
            entry = {"id": self._sequence, "model": model, "workload": workload, "priority": priority,
                     "reserved_mib": float(estimated_vram_mib), "enqueued": started}
            self._pending.append(entry)
        acquired = False
        last_wait_reason = "queue_timeout"
        try:
            while True:
                async with self._condition:
                    first = self._first_eligible()
                    if first is not entry or len(self._active) >= self.profile["max_active"]:
                        last_wait_reason = "realtime_pressure" if self.stability.realtime_pressure() and workload not in ("audio", "video", "realtime") else "queue_timeout"
                        remaining = deadline - loop.time()
                        if remaining <= 0:
                            raise GPUAdmissionError(last_wait_reason, retryable=True)
                        try:
                            await asyncio.wait_for(self._condition.wait(), timeout=min(self.poll_s, remaining))
                        except asyncio.TimeoutError:
                            pass
                        continue
                    epoch = self._allocation_epoch
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        raise GPUAdmissionError(last_wait_reason, retryable=True)
                try:
                    telemetry = await asyncio.wait_for(self._telemetry(fresh=True), timeout=remaining)
                except asyncio.TimeoutError as exc:
                    # Cancelling the await removes this waiter; it cannot stop
                    # an NVML call already running in asyncio.to_thread.
                    raise GPUAdmissionError("telemetry_timeout", retryable=True) from exc
                reason = self.stability.assess(telemetry, self.profile)
                if reason:
                    raise GPUAdmissionError(reason, retryable=True)
                if estimated_vram_mib == 0 and not self.residency.contains(model):
                    raise GPUAdmissionError("vram_estimate_required")
                total = finite_number(telemetry["gpu"]["memory_total_mib"])
                if estimated_vram_mib > total * self.profile["vram_fraction"] - self.profile["reserve_mib"]:
                    raise GPUAdmissionError("vram_request_exceeds_profile")
                async with self._condition:
                    if epoch != self._allocation_epoch:
                        continue
                    first = self._first_eligible()
                    reserved = sum(item["reserved_mib"] for item in self._active.values())
                    budget = available_budget_mib(telemetry, self.profile, reserved)
                    realtime_block = self.stability.realtime_pressure() and workload not in ("audio", "video", "realtime")
                    if loop.time() > deadline:
                        raise GPUAdmissionError(last_wait_reason, retryable=True)
                    if first is entry and len(self._active) < self.profile["max_active"] and budget >= estimated_vram_mib and budget > 0 and not realtime_block:
                        self._pending.remove(entry)
                        entry["started"] = loop.time()
                        self._active[entry["id"]] = entry
                        self._queue_samples.append((entry["started"] - started) * 1000)
                        acquired = True
                        self._condition.notify_all()
                        return {"lease_id": entry["id"], "model": model, "workload": workload,
                                "reserved_mib": estimated_vram_mib, "profile": self.profile_name,
                                "keep_alive_s": self.profile["keep_alive_s"]}
                    last_wait_reason = "realtime_pressure" if realtime_block else "vram_pressure" if budget < estimated_vram_mib or budget <= 0 else "queue_timeout"
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        raise GPUAdmissionError(last_wait_reason, retryable=True)
                    try:
                        await asyncio.wait_for(self._condition.wait(), timeout=min(self.poll_s, remaining))
                    except asyncio.TimeoutError:
                        pass
        except asyncio.CancelledError:
            self._cancelled += 1
            raise
        except GPUAdmissionError as exc:
            self._rejected += 1
            self._last_reason = exc.reason
            raise
        finally:
            if not acquired:
                async with self._condition:
                    if entry in self._pending:
                        self._pending.remove(entry)
                    self._condition.notify_all()

    async def _release(self, lease_id: int) -> None:
        async with self._condition:
            entry = self._active.pop(lease_id, None)
            if entry is not None:
                self._allocation_epoch += 1
                self._completed += 1
                self._service_samples.append((asyncio.get_running_loop().time() - entry["started"]) * 1000)
            self._condition.notify_all()

    @asynccontextmanager
    async def lease(self, model: str, workload: str = "chat", estimated_vram_mib: float = 0, priority: int = 10):
        token = await self._acquire(model, workload, estimated_vram_mib, priority)
        try:
            yield token
        finally:
            await self._release(token["lease_id"])

    async def snapshot(self) -> dict:
        telemetry = await self._telemetry()
        health_reason = self.stability.assess(telemetry, self.profile)
        async with self._condition:
            active = len(self._active)
            reserved = sum(entry["reserved_mib"] for entry in self._active.values())
            scheduler = {"active": active, "queued": len(self._pending), "queue_limit": self.max_queue,
                         "max_active": self.profile["max_active"], "reserved_mib": reserved,
                         "completed_leases": self._completed, "rejected": self._rejected,
                         "cancelled_waiters": self._cancelled, "last_rejection": self._last_reason,
                         "queue_wait": latency_summary(self._queue_samples),
                         "lease_duration": latency_summary(self._service_samples)}
        return {"profile_name": self.profile_name, "profile": dict(self.profile), "telemetry": telemetry,
                "health": {"admission_available": health_reason is None, "reason": health_reason},
                "available_budget_mib": available_budget_mib(telemetry, self.profile, reserved) if health_reason is None else 0,
                "scheduler": scheduler, "residency": self.residency.snapshot(), "stability": self.stability.snapshot(),
                "experimental_available": False, "firmware_modified": False,
                "limitations": ["Cooperative process-local scheduler; external GPU users and direct Ollama callers are not controlled.",
                                "Reservations are estimates, not CUDA allocations; device memory is rechecked before admission.",
                                "Admission timeout stops waiting for telemetry; an in-flight NVML worker thread cannot be terminated.",
                                "Latency percentiles describe admitted lease durations and queue waits, not audio hardware deadlines.",
                                "Real-time protection requires explicitly supplied latency/underrun observations; active work is not preempted."]}


_controller: AdaptiveGPUController | None = None
_controller_lock = threading.Lock()


def get_controller() -> AdaptiveGPUController:
    global _controller
    with _controller_lock:
        if _controller is None:
            _controller = AdaptiveGPUController()
    return _controller
