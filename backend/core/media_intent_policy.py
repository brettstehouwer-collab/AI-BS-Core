"""Deterministic media intent boundaries and read-only local service observations.

No model, tool registry, database, media queue or application module is imported.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from urllib.parse import urlsplit

MAX_PROMPT = 128000
MAX_STATUS_BYTES = 65536
STATUS_TIMEOUT_SECONDS = 3.0
_COMFY = re.compile(r'\bcomfy(?:[\s_-]*ui)?\b', re.IGNORECASE)
_MEDIA = re.compile(r'\b(?:comfy(?:[\s_-]*ui)?|images?|photos?|pictures?|videos?|renders?|'
                    r'portraits?|wallpapers?|paintings?|drawings?|illustrations?|artworks?|'
                    r'3d\s+(?:models?|meshes?)|animations?|img2img|txt2img|t2i|generate_comfy_\w+)\b', re.IGNORECASE)
_VERB = r'(?:generate|create|make|render|draw|paint|sketch|produce|illustrate|visualize|depict|design|animate)'
_POLITE = r'(?:(?:please|now)\s+|(?:can|could|would|will)\s+you\s+(?:please\s+)?|i\s+want\s+(?:you\s+to\s+)?)*'


def intent_text(body):
    """Current user's raw input is authority; attachments/history are context only."""
    if not isinstance(body, dict):
        return None
    raw = body.get('user_prompt')
    if raw is None:
        raw = body.get('prompt', '')
        if raw is None or isinstance(raw, str) and not raw.strip():
            messages = body.get('messages')
            if isinstance(messages, list) and messages:
                last = messages[-1]
                if isinstance(last, dict) and last.get('role') == 'user':
                    raw = last.get('content')
    if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_PROMPT:
        return None
    return raw.strip()


def _outside_quoted_data(text):
    text = re.sub(r'```[\s\S]*?(?:```|$)', ' ', text)
    text = re.sub(r'`[^`]*`|"[^"\n]*"|\u201c[^\u201d\n]*\u201d', ' ', text)
    # Single quotes following a letter are apostrophes, not quotation delimiters.
    return re.sub(r"(?<!\w)'[^'\n]*'(?!\w)", ' ', text).strip()


def classify_media_message(prompt):
    """Return a non-generating category, otherwise leave explicit/ordinary routing.

    A service name is not an order. Informational, negated and quoted instructions
    cannot be promoted into media commands by later substring heuristics.
    """
    if not isinstance(prompt, str) or len(prompt) > MAX_PROMPT:
        return 'media_denied'
    text = prompt.strip()
    outside = _outside_quoted_data(text)
    lower = outside.casefold()
    mentions = bool(_MEDIA.search(text))
    if not mentions:
        return None

    # A status question takes precedence even if followed by a conditional job.
    # Conditional/mixed messages are not authority to bypass this observation.
    status_start = re.search(
        r'^(?:please\s+)?(?:is|are|was|were|why|check|verify|what(?:\s+is|\'s)|'
        r'tell\s+me\s+(?:if|whether)|can\s+you\s+check)\b', lower)
    status_word = re.search(r'\b(?:running|online|offline|available|availability|healthy|health|'
                            r'status|state|ready|reachable|working|stopped|responding|up|down)\b', lower)
    shorthand_status = re.fullmatch(r'/?comfy(?:[\s_-]*ui)?\s*:?\s+(?:status|health|running|online)\??', lower)
    if _COMFY.search(text) and status_word and (status_start or shorthand_status):
        return 'comfy_status'

    if (re.search(r"\b(?:do\s+not|don't|dont|not|never|no\s+need\s+to|stop|avoid)\s+" + _VERB + r'\b', lower)
            or re.match(r"^(?:do\s+not|don't|dont|never|stop|avoid)\b", lower)):
        return 'media_denied'

    explicit = bool(re.match(r'^' + _POLITE + _VERB + r'\b', lower))
    explicit = explicit or bool(re.match(
        r'^' + _POLITE + r'use\s+comfy(?:[\s_-]*ui)?\s+(?:to\s+)?' + _VERB + r'\b', lower))
    explicit = explicit or bool(re.match(
        r'^/(?:imagine|render|image|draw|paint|generate|t2i|txt2img|comfy|comfyui)\b\s+\S', lower))
    explicit = explicit or bool(re.match(r'^(?:t2i|txt2img|comfy(?:\s*ui)?)\s*:\s*\S', lower))
    if explicit:
        return None

    # These are capability/how-to/reporting questions, not creation requests.
    if (re.match(r'^(?:how|why|what|when|where|which|explain|tell\s+me|is|are|was|were|did|does|do|'
                 r'has|have|can|could|would|will|should|error|warning|traceback|exception|failed|'
                 r'can\s+comfy(?:[\s_-]*ui)?|'
                 r'does\s+comfy(?:[\s_-]*ui)?|is\s+comfy(?:[\s_-]*ui)?|did\s+it|the\s+log|this\s+log|logs?\s+say)\b', lower)
            or re.search(r'\b(?:existing|saved|previous|last)\b', lower)
            or not _MEDIA.search(outside)
            or re.fullmatch(r'comfy(?:[\s_-]*ui)?[?.!]*', lower)):
        return 'media_inquiry'
    if _COMFY.search(outside):
        return 'media_inquiry'
    return None


def _status_origins():
    raw = os.environ.get('COMFYUI_HOST', 'http://127.0.0.1:8189').strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return ()
    if (parsed.scheme not in {'http', 'https'} or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}
            or port not in {8188, 8189} or parsed.username or parsed.password
            or parsed.path not in {'', '/'} or parsed.query or parsed.fragment):
        return ()
    primary = raw.rstrip('/')
    # Observe both established local Comfy slots only when the first is offline.
    alternate_port = 8188 if port == 8189 else 8189
    alternate = f'http://127.0.0.1:{alternate_port}'
    return (primary, alternate)


async def probe_comfy_status(*, transport=None):
    """At most two local GETs; a response is not model/checkpoint readiness."""
    origins = _status_origins()
    if not origins:
        return {'status': 'unverified', 'generation_submitted': False}
    try:
        async with asyncio.timeout(STATUS_TIMEOUT_SECONDS):
            return await _probe_comfy_origins(origins, transport)
    except Exception:
        return {'status': 'unverified', 'generation_submitted': False}


async def _probe_comfy_origins(origins, transport):
    import httpx
    result = {'status': 'unverified', 'generation_submitted': False}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(1.5, connect=0.75),
                                     follow_redirects=False, trust_env=False, transport=transport) as client:
            for origin in origins:
                try:
                    async with client.stream('GET', origin + '/system_stats') as response:
                        if response.status_code != 200:
                            return result
                        raw = bytearray()
                        async for chunk in response.aiter_bytes():
                            raw.extend(chunk)
                            if len(raw) > MAX_STATUS_BYTES:
                                return result
                    data = json.loads(raw)
                    if (not isinstance(data, dict) or not isinstance(data.get('system'), dict)
                            or not isinstance(data.get('devices'), list)):
                        return result
                    return {'status': 'running', 'port': urlsplit(origin).port,
                            'generation_submitted': False}
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    continue
                except Exception:
                    return result
    except Exception:
        return result
    return {'status': 'offline', 'generation_submitted': False}


async def resolve_media_status(body):
    """Return a factual non-generating reply before any search/model/tool routing."""
    if not isinstance(body, dict):
        return None
    mode = body.get('mode')
    mode = mode.strip().lower() if isinstance(mode, str) else mode
    prompt = intent_text(body)
    if prompt is None:
        if body.get('user_prompt') is not None:
            return 'The current user message is invalid or empty. No generation, model or tool was invoked.\n'
        return None
    category = classify_media_message(prompt)
    if category == 'comfy_status':
        state = await probe_comfy_status()
        if state['status'] == 'running':
            text = f"ComfyUI responded to a read-only health check on local port {state['port']}. "
            text += 'This confirms a service response, not model or checkpoint readiness.'
        elif state['status'] == 'offline':
            text = 'ComfyUI is offline or not reachable on the configured local ComfyUI ports.'
        else:
            text = 'ComfyUI status could not be verified from a valid local health response.'
        return text + '\nNo generation was submitted, and no service or model was started.\n'
    if body.get('plan_only') is True or mode not in {None, '', 'execute'}:
        return None
    if category == 'media_denied':
        return 'No media generation was submitted. A negated, quoted or informational message is not permission to create media.\n'
    if category == 'media_inquiry':
        return ('This is an informational media message; no generation was submitted. '
                'Ask "Is ComfyUI running?" for a read-only availability check, or explicitly request '
                'an image/video and describe the scene to create media.\n')
    return None


async def media_status_response(body):
    """Plain-text adapter; JSON/OpenAI routes should use resolve_media_status."""
    text = await resolve_media_status(body)
    if text is None:
        return None
    from fastapi.responses import StreamingResponse
    return StreamingResponse(iter([text]), media_type='text/plain', headers={'Cache-Control': 'no-store'})
