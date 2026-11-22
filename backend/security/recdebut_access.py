"""Private RecDebut administration, explicit public intake, and signed SMS webhooks."""
import asyncio
import hashlib
import hmac
import os
import re
from pathlib import Path
from dotenv import dotenv_values
from fastapi import HTTPException, Request
from security.firebase_auth import verify_admin_credentials

PREFIXES = ('/api/v1/recdebut', '/api/recdebut')


async def textbee_body(request: Request):
    """Bound the authenticated raw body before decoding or HMAC verification."""
    size, chunks = 0, []
    async for chunk in request.stream():
        size += len(chunk)
        if size > 65536:
            raise HTTPException(413, 'SMS event exceeds 64 KiB.')
        chunks.append(chunk)
    body = b''.join(chunks)
    request._body = body  # Preserve exact bytes for dependency/handler reuse.
    return body


def is_recdebut_path(path):
    path = path.lower().rstrip('/')
    return any(path == prefix or path.startswith(prefix + '/') for prefix in PREFIXES) or path.startswith('/r/')


async def require_recdebut_access(request: Request):
    path = request.url.path.rstrip('/')
    suffix = next((path[len(prefix):] for prefix in PREFIXES if path.startswith(prefix + '/')), None)
    if request.method in ('GET', 'POST') and suffix is not None and re.fullmatch(
        r'/workflow/unsubscribe/[A-Za-z0-9_-]{43}', suffix
    ):
        # Opaque recipient token is checked by the handler. No administrative bypass.
        return
    if request.method == 'GET' and suffix is not None and re.fullmatch(
        r'/workflow/links/[A-Za-z0-9_-]{43}', suffix
    ):
        # The handler requires an immutable provider-accepted email plan.
        return
    if request.method == 'GET' and (
        re.fullmatch(r'/r/\d+', path)
        or (suffix is not None and re.fullmatch(r'/(?:r/\d+|track/(?:open|click)/[^/]+/\d+)', suffix))
    ):
        return
    if request.method == 'POST' and suffix == '/register':
        return
    if request.method == 'POST' and suffix == '/webhooks/registration':
        from security.recdebut_registration_auth import verify_registration
        await verify_registration(request)
        return
    if request.method == 'POST' and suffix in {'/webhooks/textbee', '/sms/inbound'}:
        secret = os.environ.get('TEXTBEE_WEBHOOK_SECRET')
        if secret is None:
            secret = dotenv_values(Path(__file__).resolve().parents[2] / '.env').get('TEXTBEE_WEBHOOK_SECRET', '')
        if not secret:
            raise HTTPException(503, 'SMS webhook verification is not configured.')
        signature = request.headers.get('x-signature', '')
        if not re.fullmatch(r'[0-9a-f]{64}', signature):
            raise HTTPException(401, 'Invalid webhook signature.')
        body = await textbee_body(request)
        expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(401, 'Invalid webhook signature.')
        return
    key = request.headers.get('x-admin-key', '') or request.headers.get('x-api-key', '')
    if await asyncio.to_thread(verify_admin_credentials, key, request.headers.get('authorization', '')):
        return
    raise HTTPException(403, 'Administrator authorization is required for RecDebut administration.')
