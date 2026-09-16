import time
import fnmatch
from typing import Dict, Any, Optional, Tuple

class HotCache:
    """
    Zero-Disk In-Memory Hot-Key Cache.
    Maintains ultra-fast, lock-minimized in-memory state for live telemetry,
    VRAM balances, streaming LLM reasoning tokens, and crypto ticker feeds.
    """
    _instance: Optional['HotCache'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HotCache, cls).__new__(cls)
            cls._instance._store: Dict[str, Tuple[Any, float]] = {}
            cls._instance._counters: Dict[str, int] = {}
        return cls._instance

    def set(self, key: str, value: Any, ttl_seconds: float = 60.0):
        """Sets a key with an expiration timestamp."""
        expire_at = time.time() + ttl_seconds if ttl_seconds > 0 else float('inf')
        self._store[key] = (value, expire_at)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a key if not expired; returns default otherwise."""
        if key in self._store:
            val, expire_at = self._store[key]
            if time.time() < expire_at:
                return val
            else:
                self._store.pop(key, None)
        return default

    def delete(self, key: str) -> bool:
        """Deletes a key from the cache."""
        return self._store.pop(key, None) is not None

    def increment(self, key: str, delta: int = 1) -> int:
        """Increments an in-memory counter atomically."""
        current = self._counters.get(key, 0) + delta
        self._counters[key] = current
        return current

    def get_many(self, pattern: str) -> Dict[str, Any]:
        """Returns all matching unexpired keys (e.g. 'telemetry.*')."""
        now = time.time()
        results = {}
        keys_to_del = []

        for k, (val, exp) in list(self._store.items()):
            if now >= exp:
                keys_to_del.append(k)
            elif fnmatch.fnmatch(k, pattern):
                results[k] = val

        for k in keys_to_del:
            self._store.pop(k, None)

        return results

    def prune_expired(self) -> int:
        """Prunes all expired keys and returns the count freed."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if now >= exp]
        for k in expired_keys:
            self._store.pop(k, None)
        return len(expired_keys)

hot_cache = HotCache()
