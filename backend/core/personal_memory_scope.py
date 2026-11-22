"""Request-scoped personal identity and conservative derived-memory admission.

The caller must supply the existing authentication resolver's verified principal.
Headers, request bodies and archived statements never establish this context.
"""
from contextvars import ContextVar
import os
import re

MEMORY_PROMPT_LIMIT = 6000
_principal = ContextVar('aibs_verified_personal_memory_principal', default=None)


def bind_memory_principal(principal):
    valid = principal == 'local_admin'
    if isinstance(principal, str) and principal.startswith('firebase:'):
        parts = principal.split(':', 2)
        valid = len(parts) == 3 and bool(parts[1]) and bool(parts[2])
    if (not valid or not isinstance(principal, str) or len(principal) > 512
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in principal)):
        raise PermissionError('Verified personal-memory ownership is required.')
    return _principal.set(principal)


def reset_memory_principal(token):
    _principal.reset(token)


def current_memory_principal():
    return _principal.get()


def resolve_personal_identity(client_id=None, user_id=None):
    principal = _principal.get()
    if principal is None:
        raise PermissionError('Verified personal-memory ownership is required.')
    client = 'stehouwer_publishing'
    user = 'brett' if principal == 'local_admin' else principal
    if client_id not in (None, client) or user_id not in (None, user):
        raise PermissionError('The requested personal-memory scope is not available.')
    return client, user


def is_sensitive_memory_text(text):
    if not isinstance(text, str):
        return True
    patterns = (
        r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----',
        r'\b(?:sk-|ghp_|AIzaSy)[A-Za-z0-9_\-]{12,}',
        r'\b[A-Za-z0-9]{10}msh[A-Za-z0-9]{20,}',
        r'(?i)\bbearer\s+[A-Za-z0-9._~+/\-]+=*',
        r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
        r'(?i)\b(?:password|api[_ -]?key|access[_ -]?token|client[_ -]?secret)\s*(?:=|:|is\s)\s*\S+',
    )
    if any(re.search(pattern, text) for pattern in patterns):
        return True
    return any(value and len(value) >= 8 and value in text for name, value in os.environ.items()
               if any(word in name.upper() for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL')))
