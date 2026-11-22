"""Low-overhead HTTPX clients restricted to local Ollama HTTP transports."""
import hashlib
import json
import re
import ssl
import threading
from urllib.parse import urlsplit

import httpx

from gpu.compute_scheduler import GPUAdmissionError


# No HTTPS origin is admitted here. Reusing this context avoids loading the
# Windows CA store for each plaintext loopback client; TLS checks stay enabled.
_LOCAL_HTTP_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

# Volatile patterns that commonly invalidate Ollama KV prefix caches when placed
# inside system messages or early prefix blocks (ISO timestamps, RFC2822 dates,
# dynamic request/UUID markers, or live tick timers).
_VOLATILE_PREFIX_PATTERNS = (
    ("iso_timestamp", re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b")),
    ("epoch_ms", re.compile(r"\b(?:timestamp|nonce|placed_ts|server_utc)\s*[:=]\s*['\"]?\d{10,16}(?:\.\d+)?\b", re.IGNORECASE)),
    ("request_uuid", re.compile(r"\b(?:request_id|trace_id|correlation_id)\s*[:=]\s*['\"]?[0-9a-fA-F-]{16,36}\b", re.IGNORECASE)),
)


def canonicalize_tool_definitions(tools):
    """Deterministically sort tool schemas and property keys to prevent KV cache churn."""
    if not tools or not isinstance(tools, (list, tuple)):
        return []

    def _sort_name(tool):
        if not isinstance(tool, dict):
            return ""
        fn = tool.get("function")
        if isinstance(fn, dict) and isinstance(fn.get("name"), str):
            return fn["name"]
        return str(tool.get("name", ""))

    def _canonical_obj(obj):
        if isinstance(obj, dict):
            return {k: _canonical_obj(obj[k]) for k in sorted(obj)}
        if isinstance(obj, list):
            return [_canonical_obj(item) for item in obj]
        return obj

    canonical = [_canonical_obj(tool) for tool in tools if isinstance(tool, dict)]
    canonical.sort(key=_sort_name)
    return canonical


def detect_volatile_prefix_markers(text):
    """Return non-sensitive rule names of volatile markers found in a prefix string."""
    if not isinstance(text, str) or not text:
        return ()
    detected = []
    for label, pattern in _VOLATILE_PREFIX_PATTERNS:
        if pattern.search(text):
            detected.append(label)
    return tuple(detected)


def _sha256_json(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PromptPrefixStabilityAnalyzer:
    """Tracks Ollama prompt-prefix stability across turns without storing raw prompts.

    Measures whether the static prefix (system messages + tool definitions + prior
    conversation prefix) remains byte-identical across turns so Ollama's KV cache
    can reuse prefill work on the RTX 4090 instead of recomputing from token 0.
    """

    def __init__(self, max_scopes=128):
        self._max_scopes = max(1, int(max_scopes))
        self._lock = threading.Lock()
        self._history_by_scope = {}
        self._totals = {
            "total_requests": 0,
            "stable_system_hits": 0,
            "stable_tool_hits": 0,
            "prefix_extension_hits": 0,
            "invalidations": 0,
            "volatile_prefix_warnings": 0,
        }

    def analyze_payload(self, payload, *, scope="default", canonicalize_tools=False):
        """Inspect an Ollama /api/chat or /api/generate payload and return a redacted stability receipt."""
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")

        model = str(payload.get("model") or "unknown")
        options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
        ctx_affecting_options = {
            k: options[k]
            for k in ("num_ctx", "num_gpu", "rope_frequency_base", "rope_frequency_scale")
            if k in options
        }

        raw_tools = payload.get("tools")
        if canonicalize_tools and isinstance(raw_tools, list):
            tools_for_hash = canonicalize_tool_definitions(raw_tools)
            payload["tools"] = tools_for_hash
        elif isinstance(raw_tools, list):
            tools_for_hash = raw_tools
        else:
            tools_for_hash = []

        messages = payload.get("messages")
        system_blocks = []
        message_hashes = []
        volatile_markers = set()

        if isinstance(messages, list):
            for idx, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    continue
                role = str(msg.get("role") or "user")
                content = str(msg.get("content") or "")
                msg_hash = _sha256_json({"role": role, "content": content})
                message_hashes.append(msg_hash)
                if role == "system":
                    system_blocks.append(content)
                    for marker in detect_volatile_prefix_markers(content):
                        volatile_markers.add(marker)
                elif idx == 0:
                    for marker in detect_volatile_prefix_markers(content):
                        volatile_markers.add(marker)
        else:
            system_text = str(payload.get("system") or "")
            if system_text:
                system_blocks.append(system_text)
                for marker in detect_volatile_prefix_markers(system_text):
                    volatile_markers.add(marker)
            prompt_text = str(payload.get("prompt") or "")
            if prompt_text:
                message_hashes.append(_sha256_json({"role": "user", "content": prompt_text}))

        system_hash = _sha256_json(system_blocks)
        tools_hash = _sha256_json(tools_for_hash)
        options_hash = _sha256_json(ctx_affecting_options)
        static_anchor_hash = _sha256_json({
            "model": model,
            "system_hash": system_hash,
            "tools_hash": tools_hash,
            "options_hash": options_hash,
        })

        scope_key = f"{scope}:{model}"
        with self._lock:
            self._totals["total_requests"] += 1
            if volatile_markers:
                self._totals["volatile_prefix_warnings"] += 1

            prev = self._history_by_scope.get(scope_key)
            invalidation_reasons = []
            matched_prefix_messages = 0
            is_prefix_extension = False

            if prev is None:
                status = "cold_start"
            else:
                if prev["system_hash"] == system_hash:
                    self._totals["stable_system_hits"] += 1
                else:
                    invalidation_reasons.append("system_prompt_changed")

                if prev["tools_hash"] == tools_hash:
                    self._totals["stable_tool_hits"] += 1
                else:
                    invalidation_reasons.append("tool_definitions_changed")

                if prev["options_hash"] != options_hash:
                    invalidation_reasons.append("context_options_changed")

                for old_h, new_h in zip(prev["message_hashes"], message_hashes):
                    if old_h == new_h:
                        matched_prefix_messages += 1
                    else:
                        break

                if not invalidation_reasons:
                    prev_count = len(prev["message_hashes"])
                    if prev_count > 0 and matched_prefix_messages >= max(1, prev_count - 1):
                        is_prefix_extension = True
                        self._totals["prefix_extension_hits"] += 1
                        status = "cache_hit_prefix_extended"
                    elif matched_prefix_messages > 0:
                        status = "partial_prefix_reuse"
                    else:
                        invalidation_reasons.append("history_prefix_diverged")
                        self._totals["invalidations"] += 1
                        status = "invalidated"
                else:
                    self._totals["invalidations"] += 1
                    status = "invalidated"

            if len(self._history_by_scope) >= self._max_scopes and scope_key not in self._history_by_scope:
                oldest_key = next(iter(self._history_by_scope))
                del self._history_by_scope[oldest_key]

            self._history_by_scope[scope_key] = {
                "system_hash": system_hash,
                "tools_hash": tools_hash,
                "options_hash": options_hash,
                "static_anchor_hash": static_anchor_hash,
                "message_hashes": tuple(message_hashes),
            }

            total_msgs = len(message_hashes)
            reuse_ratio = round(matched_prefix_messages / total_msgs, 4) if total_msgs > 0 else 0.0

            return {
                "schema": "aibs.prompt_prefix_stability.v1",
                "scope": scope_key,
                "model": model,
                "status": status,
                "static_anchor_hash": static_anchor_hash[:16],
                "system_hash": system_hash[:16],
                "tools_hash": tools_hash[:16],
                "options_hash": options_hash[:16],
                "message_count": total_msgs,
                "matched_prefix_messages": matched_prefix_messages,
                "prefix_reuse_ratio": reuse_ratio,
                "is_prefix_extension": is_prefix_extension,
                "invalidation_reasons": tuple(invalidation_reasons),
                "volatile_prefix_markers": tuple(sorted(volatile_markers)),
            }

    def snapshot_metrics(self):
        """Return aggregate cache stability statistics across all observed turns."""
        with self._lock:
            return dict(self._totals, tracked_scopes=len(self._history_by_scope))

    def reset(self):
        with self._lock:
            self._history_by_scope.clear()
            for key in self._totals:
                self._totals[key] = 0


_DEFAULT_PREFIX_ANALYZER = PromptPrefixStabilityAnalyzer()


def get_prefix_stability_analyzer():
    """Return the process-wide PromptPrefixStabilityAnalyzer singleton."""
    return _DEFAULT_PREFIX_ANALYZER



def local_ollama_host(host):
    """Validate a base origin before constructing any client or sending data."""
    if not isinstance(host, str):
        raise GPUAdmissionError("local_ollama_endpoint_required")
    try:
        parsed = urlsplit(host)
        # Accessing port also validates malformed and out-of-range ports.
        parsed.port
    except (TypeError, ValueError) as exc:
        raise GPUAdmissionError("local_ollama_endpoint_required") from exc
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise GPUAdmissionError("local_ollama_endpoint_required")
    return host.rstrip("/")


async def _require_local_request(request):
    # Guard actual request destinations too, including redirects if a future
    # caller opts into them. A valid construction origin grants no remote I/O.
    origin = request.url.copy_with(path="/", query=None, fragment=None)
    local_ollama_host(str(origin))


def local_ollama_client(*hosts, timeout, client_factory=None):
    """Build one client for validated local origins, preserving caller timeouts.

    Only loopback HTTP transports may use the empty trust-store context. Other
    HTTPX clients retain their existing certificate and environment behavior.
    The injected constructor supports offline callers without opening sockets.
    """
    if not hosts:
        raise GPUAdmissionError("local_ollama_endpoint_required")
    for host in hosts:
        local_ollama_host(host)
    constructor = client_factory if client_factory is not None else httpx.AsyncClient
    return constructor(timeout=timeout, trust_env=False, verify=_LOCAL_HTTP_CONTEXT,
                       event_hooks={"request": [_require_local_request]})
