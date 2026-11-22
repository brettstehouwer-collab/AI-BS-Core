"""GPU admission for local Ollama calls, without changing execution authority.

Only callers using this adapter are governed. A lease is cooperative admission,
not a driver memory quota, cross-process isolation, or a firmware control.
"""
import asyncio
import math
import os
import time
from contextlib import asynccontextmanager

import httpx

from core.local_ollama_http import _LOCAL_HTTP_CONTEXT, local_ollama_client, local_ollama_host
from gpu.compute_scheduler import GPUAdmissionError, get_controller


_MIB = 1048576
_DEFAULT_CONTEXT = 4096
_MAX_CONTEXT = 8192
_MAX_RESIDENCY_ATTEMPTS = 3


def admitted_options(options, admission):
    """Bind enabled admission limits while preserving omitted legacy options."""
    result = dict(options or {})
    for key in ("num_ctx", "num_batch"):
        if admission.get(key) is not None:
            result[key] = admission[key]
    return result


class OllamaDispatcher:
    def __init__(self, controller=None, client_factory=httpx.AsyncClient, *, enabled=True):
        if not isinstance(enabled, bool):
            raise ValueError("invalid_adaptive_gpu_rollout_flag")
        self.enabled = enabled
        self.controller = controller or get_controller()
        self.client_factory = client_factory
        self._catalog = {}
        self._residency = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _models(response):
        response.raise_for_status()
        data = response.json()
        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, list) or any(not isinstance(model, dict) for model in models):
            raise ValueError("invalid_ollama_inventory")
        return models

    async def _resident_models(self, host):
        async with local_ollama_client(host, timeout=3.0, client_factory=self.client_factory) as client:
            resident = self._models(await client.get(host + "/api/ps"))
        self._residency[host] = resident
        return resident

    async def _discover(self, host):
        # Metadata only: never load, unload, pull, or evict a model here.
        async with self._lock:
            now = time.monotonic()
            async with local_ollama_client(host, timeout=3.0, client_factory=self.client_factory) as client:
                cached = self._catalog.get(host)
                if not cached or now - cached[0] > 30:
                    response = await client.get(host + "/api/tags")
                    catalog = self._models(response)
                    self._catalog[host] = (now, catalog)
                else:
                    catalog = cached[1]
                response = await client.get(host + "/api/ps")
                resident = self._models(response)
            self._residency[host] = resident
            # Never use a different server's residency to admit this host.
            return catalog, resident

    @staticmethod
    def _match(models, name):
        exact = name if ":" in name else name + ":latest"
        return next((m for m in models if m.get("name", m.get("model")) == exact), None)

    @staticmethod
    def _bounded_options(options):
        if options is None:
            options = {}
        if not isinstance(options, dict):
            raise GPUAdmissionError("unsupported_gpu_options")
        num_ctx = options.get("num_ctx", _DEFAULT_CONTEXT)
        num_batch = options.get("num_batch", 512)
        num_gpu = options.get("num_gpu", -1)
        for value, minimum, maximum in ((num_ctx, 1, _MAX_CONTEXT), (num_batch, 1, 512), (num_gpu, -1, 99)):
            if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                raise GPUAdmissionError("unsupported_gpu_options")
        # This controller observes one device, so it cannot admit an explicit
        # alternate device or a caller-specified split across devices.
        if options.get("main_gpu", 0) != 0 or "tensor_split" in options:
            raise GPUAdmissionError("unsupported_gpu_options")
        return num_ctx, num_batch, num_gpu

    def _keep_alive(self, token=None):
        token = token if isinstance(token, dict) else {}
        profile = getattr(self.controller, "profile", {})
        profile_bound = profile.get("keep_alive_s", 300) if isinstance(profile, dict) else 300
        values = (token.get("keep_alive_s", profile_bound), profile_bound)
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) or value < 0 for value in values):
            raise GPUAdmissionError("invalid_keep_alive_bound")
        return int(min(300, *values))

    @classmethod
    def _incremental_estimate(cls, resident, model, desired_mib):
        observed = cls._match(resident, model)
        size_vram = observed.get("size_vram", 0) if observed else 0
        if (isinstance(size_vram, bool) or not isinstance(size_vram, (int, float))
                or not math.isfinite(size_vram) or size_vram < 0):
            size_vram = 0
        # Observed memory is already included in device telemetry. Subtract
        # only that allocation, never infer full residency from nonzero bytes.
        resident_mib = min(size_vram / _MIB, desired_mib)
        return max(768, math.ceil(desired_mib - resident_mib)), resident_mib

    @asynccontextmanager
    async def lease(self, model, host, *, workload="chat", priority=10, options=None):
        host = local_ollama_host(host)
        if not self.enabled:
            token = {"gpu_admitted": False, "execution": "controller_disabled",
                     "host": host, "keep_alive_s": 300}
            if isinstance(options, dict):
                token.update({key: options[key] for key in ("num_ctx", "num_batch") if key in options})
            yield token
            return
        if not isinstance(model, str) or not model.strip() or len(model) > 256:
            raise GPUAdmissionError("invalid_model")
        num_ctx, num_batch, num_gpu = self._bounded_options(options)
        if num_gpu == 0:
            # An explicit CPU-only request needs no GPU reservation. Port number
            # alone does not prove that an Ollama server is CPU-only.
            yield {"gpu_admitted": False, "execution": "explicit_cpu", "host": host,
                   "keep_alive_s": self._keep_alive(), "num_ctx": num_ctx, "num_batch": num_batch}
            return
        try:
            catalog, resident = await self._discover(host)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise GPUAdmissionError("ollama_inventory_unavailable", retryable=True) from exc
        model_info = self._match(catalog, model)
        if not model_info:
            raise GPUAdmissionError("model_not_installed")
        size = model_info.get("size", 0)
        if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size) or size <= 0:
            raise GPUAdmissionError("model_size_unavailable")
        # Disk bytes do not specify KV-cache geometry, partial offload, or peak
        # allocations. This conservative heuristic is not a memory safety proof.
        # Callers must bind the yielded context and batch bounds to inference.
        context_margin = max(1024, math.ceil(num_ctx / 1024) * 512)
        desired_mib = math.ceil(size / _MIB * 1.10) + 1024 + context_margin
        incremental, _ = self._incremental_estimate(resident, model, desired_mib)
        for _ in range(_MAX_RESIDENCY_ATTEMPTS):
            async with self.controller.lease(model=model, workload=workload,
                                             estimated_vram_mib=incremental, priority=priority) as token:
                # Queueing can outlive keep-alive, or another caller can reload
                # the model with different options. Recheck even partial memory.
                try:
                    resident = await self._resident_models(host)
                except (httpx.HTTPError, ValueError, TypeError) as exc:
                    raise GPUAdmissionError("ollama_inventory_unavailable", retryable=True) from exc
                refreshed_estimate, resident_mib = self._incremental_estimate(resident, model, desired_mib)
                if refreshed_estimate > incremental:
                    incremental = refreshed_estimate
                    continue
                self.controller.update_residency(resident)
                yield {"gpu_admitted": True, "estimated_incremental_mib": incremental,
                       "desired_allocation_mib": desired_mib,
                       "observed_resident_mib": resident_mib,
                       "estimate_source": "disk_weights_context_minus_observed_residency" if resident_mib else "disk_weights_plus_context_margin",
                       "host": host, "num_ctx": num_ctx, "num_batch": num_batch,
                       "keep_alive_s": self._keep_alive(token)}
                return
        raise GPUAdmissionError("model_residency_unstable", retryable=True)


_dispatcher = None


def get_dispatcher():
    global _dispatcher
    if _dispatcher is None:
        # Opt in only after measured workload acceptance. Standalone benchmark
        # instances explicitly use enabled=True and do not change this setting.
        _dispatcher = OllamaDispatcher(enabled=os.environ.get("AIBS_ADAPTIVE_GPU_ENABLED") == "true")
    return _dispatcher
