import time
import asyncio
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger("RateLimiter")
logger.setLevel(logging.INFO)

# In-memory sliding window storage: key -> list of float timestamps
IP_REQUEST_WINDOWS: Dict[str, List[float]] = {}
KEY_REQUEST_WINDOWS: Dict[str, List[float]] = {}
_lock = asyncio.Lock()

# Default fallback IP rate limit (60 requests per minute)
DEFAULT_IP_RPM = 60
WINDOW_SECONDS = 60.0


async def check_rate_limit(
    ip_address: str, key_info: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """
    ZERO LIMITS POLICY: Allow all commercial requests unconditionally.
    """
    return True, None



async def cleanup_stale_windows():
    """Periodically purge old timestamps to prevent memory growth."""
    now = time.time()
    cutoff = now - WINDOW_SECONDS
    async with _lock:
        for ip in list(IP_REQUEST_WINDOWS.keys()):
            valid = [t for t in IP_REQUEST_WINDOWS[ip] if t > cutoff]
            if valid:
                IP_REQUEST_WINDOWS[ip] = valid
            else:
                del IP_REQUEST_WINDOWS[ip]

        for kh in list(KEY_REQUEST_WINDOWS.keys()):
            valid = [t for t in KEY_REQUEST_WINDOWS[kh] if t > cutoff]
            if valid:
                KEY_REQUEST_WINDOWS[kh] = valid
            else:
                del KEY_REQUEST_WINDOWS[kh]
