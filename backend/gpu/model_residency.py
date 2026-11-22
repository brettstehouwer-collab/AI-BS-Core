"""Observed residency only: no model unloads, preloads or prompt storage."""
from __future__ import annotations

import math
import threading
import time
from typing import Any


class ModelResidencyManager:
    def __init__(self, *, max_age_s: float = 10.0):
        self.max_age_s = max_age_s
        self._lock = threading.Lock()
        self._observed: dict[str, dict] = {}
        self._updated = 0.0

    def update(self, models: list[dict[str, Any]]) -> None:
        if not isinstance(models, list):
            raise ValueError("invalid_residency_snapshot")
        observed = {}
        for model in models:
            if not isinstance(model, dict):
                continue
            name = model.get("name", model.get("model"))
            size = model.get("size_vram")
            if not isinstance(name, str) or not name or len(name) > 256:
                continue
            if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size) or size < 0:
                continue
            observed[name] = {"size_vram_mib": size / 1024 ** 2}
        with self._lock:
            self._observed, self._updated = observed, time.monotonic()

    def contains(self, name: str) -> bool:
        with self._lock:
            if time.monotonic() - self._updated > self.max_age_s:
                return False
            keys = (name, name + ":latest") if ":" not in name else (name,)
            return any(self._observed.get(key, {}).get("size_vram_mib", 0) > 0 for key in keys)

    def snapshot(self) -> dict:
        with self._lock:
            age = time.monotonic() - self._updated if self._updated else None
            return {"models": dict(self._observed), "age_s": round(age, 3) if age is not None else None,
                    "fresh": age is not None and age <= self.max_age_s, "source": "externally_supplied_ollama_api_ps",
                    "automatic_eviction": False}


def build_embedding_batches(inputs: list[str], *, max_items: int = 8, max_chars: int = 16000) -> list[list[str]]:
    """Bound batches without truncating or changing any input item."""
    if not isinstance(max_items, int) or isinstance(max_items, bool) or not 1 <= max_items <= 128:
        raise ValueError("invalid_batch_item_limit")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 1 <= max_chars <= 1000000:
        raise ValueError("invalid_batch_character_limit")
    batches: list[list[str]] = []
    pending: list[str] = []
    chars = 0
    for value in inputs:
        if not isinstance(value, str) or len(value) > max_chars:
            raise ValueError("embedding_item_exceeds_limit")
        if pending and (len(pending) >= max_items or chars + len(value) > max_chars):
            batches.append(pending)
            pending, chars = [], 0
        pending.append(value)
        chars += len(value)
    if pending:
        batches.append(pending)
    return batches


def adaptive_embedding_batches(inputs: list[str], *, available_mib: float, max_items: int = 8) -> list[list[str]]:
    """Conservative input batching heuristic; no kernel throughput guarantee."""
    if not isinstance(available_mib, (float, int)) or not math.isfinite(available_mib) or available_mib < 0:
        raise ValueError("invalid_available_memory")
    count = min(max_items, max(1, int(available_mib // 256)))
    # A low-memory decision can reduce item count, but never lower the accepted
    # per-item size or truncate text merely because current memory is busy.
    return build_embedding_batches(inputs, max_items=count, max_chars=16000)
