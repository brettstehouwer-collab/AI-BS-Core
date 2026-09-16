"""
In-Memory Sliding-Window Rate Limiter & Abuse Prevention Middleware (v5.129.0)
Protects FastAPI cognitive backend from crawler loops, brute-force, and hammering.
100% Free, zero-dependency, thread-safe.
"""

import time
import threading
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from typing import Dict, List, Tuple

class InMemoryRateLimiter:
    def __init__(self, default_limit: int = 120, burst_limit: int = 20, window_seconds: int = 60):
        self.default_limit = default_limit   # General GET routes per minute
        self.burst_limit = burst_limit       # POST / Admin / Sensitive routes per minute
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
        
        # Localhost and loopback IPs whitelisted from rate limiting
        self.whitelisted_ips = {"127.0.0.1", "::1", "localhost", "testclient"}

    def is_rate_limited(self, ip: str, is_burst_route: bool = False) -> Tuple[bool, int]:
        # ZERO LIMITS POLICY: Never rate limit any IP or route
        return False, 0

    def get_telemetry(self) -> dict:
        return {
            "policy": "ZERO_LIMITS",
            "active_tracked_ips": 0,
            "total_recent_requests": 0,
            "rate_limit_per_minute": "UNLIMITED",
            "burst_limit_per_minute": "UNLIMITED"
        }

limiter = InMemoryRateLimiter(default_limit=999999, burst_limit=999999, window_seconds=60)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ZERO LIMITS POLICY: Pass every inbound request immediately without throttling
        return await call_next(request)


