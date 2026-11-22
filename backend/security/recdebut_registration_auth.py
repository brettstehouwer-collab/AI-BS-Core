"""Dedicated, dormant-by-default website intake authentication. No provider calls."""
import hashlib
import hmac
import os
import re
import time

from fastapi import HTTPException, Request

MAX_BODY = 16384


async def verify_registration(request: Request):
    secret = os.environ.get('RECDEBUT_REGISTRATION_SECRET', '')
    if len(secret) < 32:
        raise HTTPException(503, 'Website registration connection is not configured.')
    stamp = request.headers.get('x-recdebut-timestamp', '')
    signature = request.headers.get('x-recdebut-signature', '')
    if not re.fullmatch(r'[0-9]{10}', stamp) or abs(time.time() - int(stamp)) > 300:
        raise HTTPException(401, 'Invalid or expired website receipt.')
    if not re.fullmatch(r'[a-f0-9]{64}', signature):
        raise HTTPException(401, 'Invalid website receipt.')
    # Bound streamed bodies too; Content-Length is not authoritative.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY:
            raise HTTPException(413, 'Website receipt exceeds 16 KiB.')
    request._body = bytes(body)
    expected = hmac.new(secret.encode(), stamp.encode() + b'.' + bytes(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, 'Invalid website receipt.')
