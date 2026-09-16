"""
AI-BS Broadcast Engine: Streaming URL & Stream Key Security Validator
Sovereign validation for RTMP, RTMPS, SRT, and WebRTC streaming ingestion endpoints.
Defends against command injection, shell metacharacters, and malformed streaming parameters.
"""

import re
import urllib.parse
from typing import Dict, Any, List, Optional

# Supported ingestion protocols
ALLOWED_PROTOCOLS = {"rtmp", "rtmps", "srt", "webrtc", "ws", "wss", "http", "https"}

# Strict pattern for forbidden shell characters in streaming URLs (permits ? and & for query parameters)
URL_SHELL_INJECTION_PATTERN = re.compile(r"[\s;|`$<>'\"\\\x00-\x1f]")

# Strict pattern for forbidden shell characters in stream keys
KEY_SHELL_INJECTION_PATTERN = re.compile(r"[\s;&|`$<>'\"\\\x00-\x1f]")

# Provider-specific stream key regex patterns
YOUTUBE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}(?:-[a-zA-Z0-9]{4})?$")
TWITCH_KEY_PATTERN = re.compile(r"^live_[0-9]+_[a-zA-Z0-9]{16,64}$")
FACEBOOK_KEY_PATTERN = re.compile(r"^FB-[0-9]+-[0-9]+-[a-zA-Z0-9_\-]+$")
GENERIC_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.\:\/+=]{3,256}$")


def mask_stream_key(key: Optional[str]) -> str:
    """
    Returns a masked version of a stream key for safe UI telemetry and logging.
    Example: 'je5p-8zxu-d7rj-d73s-cvu6' -> 'je5p-****-****-****-cvu6'
    """
    if not key:
        return ""
    stripped = key.strip()
    if len(stripped) <= 8:
        return "********"
    prefix = stripped[:4]
    suffix = stripped[-4:]
    return f"{prefix}****{suffix}"


def detect_provider(hostname: str, url: str = "") -> str:
    """Detects streaming provider from hostname or URL."""
    low_host = hostname.lower()
    low_url = url.lower()
    if "youtube.com" in low_host or "youtube" in low_url:
        return "YouTube Live"
    if "twitch.tv" in low_host or "live-video.net" in low_host or "twitch" in low_url:
        return "Twitch"
    if "facebook.com" in low_host or "fbcdn.net" in low_host:
        return "Facebook Live"
    if "kick.com" in low_host or "global-contribute.live-video.net" in low_host:
        return "Kick"
    if "127.0.0.1" in low_host or "localhost" in low_host:
        return "Local Ingest"
    return "Custom Endpoint"


def validate_stream_url(url: str) -> Dict[str, Any]:
    """
    Validates a streaming ingestion URL (RTMP, RTMPS, SRT, WebRTC).
    Checks protocol scheme, host, port range, and sanitizes against injection vulnerabilities.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not url or not isinstance(url, str):
        return {
            "valid": False,
            "url": url,
            "errors": ["Streaming URL is empty or non-string"],
            "protocol": None,
            "host": None,
            "port": None,
            "provider": "Unknown"
        }

    raw_url = url.strip()

    # 1. Shell Injection & Control Character Check
    if URL_SHELL_INJECTION_PATTERN.search(raw_url):
        errors.append("Streaming URL contains illegal whitespace or shell metacharacters")

    # 2. Scheme / Protocol parsing
    try:
        parsed = urllib.parse.urlparse(raw_url)
    except Exception as e:
        return {
            "valid": False,
            "url": raw_url,
            "errors": [f"Malformed URL structure: {str(e)}"],
            "protocol": None,
            "host": None,
            "port": None,
            "provider": "Unknown"
        }

    protocol = parsed.scheme.lower()
    if not protocol:
        errors.append("Missing protocol scheme (e.g. rtmp://, rtmps://, srt://)")
    elif protocol not in ALLOWED_PROTOCOLS:
        errors.append(f"Unsupported streaming protocol '{protocol}'. Allowed: {', '.join(sorted(ALLOWED_PROTOCOLS))}")

    # 3. Host and Port parsing
    host = parsed.hostname
    if not host:
        errors.append("Streaming URL lacks a valid hostname or IP address")

    port = parsed.port
    if port is None:
        if protocol == "rtmp":
            port = 1935
        elif protocol in ("rtmps", "https"):
            port = 443
        elif protocol == "srt":
            port = 9000
        elif protocol in ("http", "ws"):
            port = 80
        elif protocol == "wss":
            port = 443
    else:
        if port < 1 or port > 65535:
            errors.append(f"Port {port} is out of valid range (1-65535)")

    # 4. SRT specific query parameter validation
    if protocol == "srt" and parsed.query:
        query_params = urllib.parse.parse_qs(parsed.query)
        if "latency" in query_params:
            try:
                lat = int(query_params["latency"][0])
                if lat < 20 or lat > 5000:
                    warnings.append(f"SRT latency {lat}ms is outside typical operational window (20-5000ms)")
            except ValueError:
                errors.append("SRT latency query parameter must be an integer (in milliseconds)")
        if "mode" in query_params:
            mode = query_params["mode"][0].lower()
            if mode not in ("caller", "listener", "rendezvous"):
                errors.append(f"Invalid SRT mode '{mode}'. Must be caller, listener, or rendezvous")

    provider = detect_provider(host or "", raw_url)

    return {
        "valid": len(errors) == 0,
        "url": raw_url,
        "protocol": protocol,
        "host": host,
        "port": port,
        "path": parsed.path,
        "provider": provider,
        "errors": errors,
        "warnings": warnings
    }


def validate_stream_key(key: Optional[str], provider_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates a stream key for cryptographic sanity and provider formatting.
    Masks the key for safe UI telemetry.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if key is None or key == "":
        return {
            "valid": True,
            "is_empty": True,
            "masked_key": "",
            "errors": [],
            "warnings": ["Stream key is not set (permitted for SRT listeners or open relays)"]
        }

    raw_key = key.strip()

    # 1. Shell Injection & Forbidden Metacharacters Check
    if KEY_SHELL_INJECTION_PATTERN.search(raw_key):
        errors.append("Stream key contains illegal whitespace or shell metacharacters")

    # 2. Length check
    if len(raw_key) < 3:
        errors.append("Stream key is too short (minimum 3 characters)")
    elif len(raw_key) > 512:
        errors.append("Stream key exceeds maximum allowed length (512 characters)")

    # 3. Provider-specific format heuristics
    detected_format = "generic"
    if YOUTUBE_KEY_PATTERN.match(raw_key):
        detected_format = "YouTube Live"
    elif TWITCH_KEY_PATTERN.match(raw_key):
        detected_format = "Twitch"
    elif FACEBOOK_KEY_PATTERN.match(raw_key):
        detected_format = "Facebook Live"
    elif GENERIC_KEY_PATTERN.match(raw_key):
        detected_format = "Custom / Generic"
    else:
        errors.append("Stream key contains unsupported characters")

    # Provider mismatch warning
    if provider_hint and detected_format not in ("Custom / Generic", provider_hint, "generic"):
        if provider_hint == "YouTube Live" and detected_format != "YouTube Live":
            warnings.append(f"Stream key format does not match typical {provider_hint} format (xxxx-xxxx-xxxx-xxxx-xxxx)")
        elif provider_hint == "Twitch" and detected_format != "Twitch":
            warnings.append(f"Stream key format does not match typical {provider_hint} format (live_...)")

    return {
        "valid": len(errors) == 0,
        "is_empty": False,
        "masked_key": mask_stream_key(raw_key),
        "detected_format": detected_format,
        "errors": errors,
        "warnings": warnings
    }


def validate_stream_endpoint(url: str, key: str = "", name: str = "") -> Dict[str, Any]:
    """
    Performs full combined validation of a streaming endpoint (URL + Stream Key).
    """
    url_res = validate_stream_url(url)
    key_res = validate_stream_key(key, provider_hint=url_res.get("provider"))

    combined_errors = url_res.get("errors", []) + key_res.get("errors", [])
    combined_warnings = url_res.get("warnings", []) + key_res.get("warnings", [])

    return {
        "valid": len(combined_errors) == 0,
        "name": name or url_res.get("provider", "Stream Endpoint"),
        "url": url_res.get("url"),
        "protocol": url_res.get("protocol"),
        "host": url_res.get("host"),
        "port": url_res.get("port"),
        "provider": url_res.get("provider"),
        "url_valid": url_res.get("valid", False),
        "key_valid": key_res.get("valid", False),
        "masked_key": key_res.get("masked_key", ""),
        "errors": combined_errors,
        "warnings": combined_warnings
    }
