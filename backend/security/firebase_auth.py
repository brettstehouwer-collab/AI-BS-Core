"""Verify Firebase administrator ID tokens at the backend boundary."""

from __future__ import annotations

import hashlib
import math
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token
except Exception:  # Keep key-based local administration available without google-auth.
    Request = None
    id_token = None


FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "ai-bs-dashboard")
_request = Request() if Request else None
_token_cache: dict[str, tuple[float, str, str]] = {}
_cache_lock = threading.Lock()


def _admin_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in os.getenv("AI_BS_ADMIN_EMAILS", "").split(",")
        if email.strip()
    }


def firebase_admin_principal(token: str, *, _fresh: bool = False) -> str | None:
    """Return a stable subject only after SDK verification and admin admission."""
    if not token or not id_token or not _request:
        return None

    allowed_emails = _admin_emails()
    if not allowed_emails:
        return None

    now = time.time()
    token_fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _cache_lock:
        cached = _token_cache.get(token_fingerprint)
        if not _fresh and cached and cached[0] > now:
            return cached[2] if cached[1] in allowed_emails else None
        if len(_token_cache) > 2048:
            for key, (expires_at, _, _) in list(_token_cache.items()):
                if expires_at <= now:
                    _token_cache.pop(key, None)

    try:
        claims: dict[str, Any] = id_token.verify_firebase_token(
            token,
            _request,
            audience=FIREBASE_PROJECT_ID,
        )
    except Exception:
        return None

    if not isinstance(claims, dict):
        return None
    email_claim = claims.get("email")
    email = email_claim.strip().lower() if isinstance(email_claim, str) else ""
    verified = claims.get("email_verified") is True
    subject = claims.get("sub")
    expiry = claims.get("exp")
    try:
        expiry_valid = (not isinstance(expiry, bool) and isinstance(expiry, (int, float))
                        and math.isfinite(expiry) and expiry > now)
    except (OverflowError, ValueError):
        expiry_valid = False
    if (not email or not verified or not isinstance(subject, str) or not subject.strip()
            or subject != subject.strip() or len(subject) > 128
            or not expiry_valid):
        return None
    if email not in allowed_emails:
        return None

    principal = f"firebase:{FIREBASE_PROJECT_ID}:{subject}"
    with _cache_lock:
        _token_cache[token_fingerprint] = (min(float(expiry), now + 300), email, principal)
    return principal


@dataclass(frozen=True, repr=False)
class VerifiedFirebaseContext:
    principal: str
    valid_until_monotonic: float


def verified_firebase_context(token: str) -> VerifiedFirebaseContext | None:
    """Fresh SDK admission plus conservative lifetime for native delegation.

    Never decode unverified claims or turn local-service keys into document owners.
    The existing cache's SDK-validated expiry is capped at 300 seconds; use the
    pre-verification monotonic sample so verification latency cannot extend it.
    No context is reconstructed from an older cached principal alone.
    """
    if not isinstance(token, str) or not token:
        return None
    monotonic_start, wall_start = time.monotonic(), time.time()
    principal = firebase_admin_principal(token, _fresh=True)
    if principal is None:
        return None
    fingerprint = hashlib.sha256(token.encode('utf-8')).hexdigest()
    with _cache_lock:
        cached = _token_cache.get(fingerprint)
        if not cached or cached[2] != principal or cached[1] not in _admin_emails():
            return None
        remaining = min(300.0, cached[0] - wall_start)
    deadline = monotonic_start + remaining
    if not math.isfinite(deadline) or deadline <= time.monotonic():
        return None
    return VerifiedFirebaseContext(principal, deadline)


def is_firebase_admin_token(token: str) -> bool:
    """Keep the existing boolean authorization interface."""
    return firebase_admin_principal(token) is not None


def get_admin_principal(key: str = "", authorization: str = "") -> str | None:
    """Resolve local-admin or SDK-verified Firebase ownership; ignore client IDs."""
    expected = os.getenv("AI_BS_ADMIN_KEY", "")
    if key and expected and secrets.compare_digest(key, expected):
        return "local_admin"
    bearer = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if bearer and expected and secrets.compare_digest(bearer, expected):
        return "local_admin"
    if not bearer and key and key.count(".") == 2:
        bearer = key
    return firebase_admin_principal(bearer)


def verify_admin_credentials(key: str = "", authorization: str = "") -> bool:
    """Verify a configured local admin key or a Firebase admin Bearer token."""
    expected = os.getenv("AI_BS_ADMIN_KEY", "")
    if key and expected and secrets.compare_digest(key, expected):
        return True

    bearer = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    if bearer and expected and secrets.compare_digest(bearer, expected):
        return True
    if not bearer and key and key.count(".") == 2:
        bearer = key
    return is_firebase_admin_token(bearer)
