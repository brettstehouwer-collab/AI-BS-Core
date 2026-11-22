"""PIN sessions grant access only to FE Express, never administrator identity."""
import asyncio
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from pathlib import Path

from fastapi import HTTPException, Request
from security.firebase_auth import verify_admin_credentials

PREFIX = '/api/v1/fe-express'
CONFIG = Path(__file__).resolve().parents[2] / 'saved_data/private_access/fe_express_pin.json'


class PinSessions:
    token_prefix = 'fe1.'
    scope = 'fe_express'
    def __init__(self, config_path=CONFIG, clock=time.monotonic):
        self.config_path = Path(config_path)
        self.clock = clock
        self.lock = threading.Lock()
        self.sessions = {}
        self.failures = []
        self.ttl = 8 * 60 * 60

    def login(self, pin):
        return self._login(pin, isinstance(pin, str) and re.fullmatch(r'[0-9]{4}', pin))

    def _login(self, credential, valid_format):
        with self.lock:
            now = self.clock()
            self.failures = [t for t in self.failures if now - t < 300]
            if len(self.failures) >= 10:
                raise HTTPException(429, 'Too many attempts. Try again in five minutes.')
            try:
                config = json.loads(self.config_path.read_text(encoding='utf-8'))
                salt = bytes.fromhex(config['salt'])
                expected = bytes.fromhex(config['digest'])
                iterations = config['iterations']
                if iterations != 600000 or len(salt) != 32 or len(expected) != 32:
                    raise ValueError('Invalid configuration')
            except (OSError, ValueError, KeyError, TypeError):
                raise HTTPException(503, 'PIN access is unavailable.') from None
            digest = hashlib.pbkdf2_hmac('sha256', (credential if valid_format else '').encode(), salt, iterations)
            if not valid_format or not hmac.compare_digest(digest, expected):
                self.failures.append(now)
                raise HTTPException(401, 'Incorrect phone number or PIN.' if self.scope == 'website_pages' else 'Incorrect PIN.')
            # Tokens are opaque, short-lived and invalidated by a backend restart.
            self.sessions = {k: v for k, v in self.sessions.items() if v > now}
            if len(self.sessions) >= 128:
                raise HTTPException(429, 'Session limit reached. Try again later.')
            token = self.token_prefix + secrets.token_urlsafe(32)
            self.sessions[hashlib.sha256(token.encode()).hexdigest()] = now + self.ttl
            return {'access_token': token, 'token_type': 'Bearer', 'expires_in': self.ttl, 'scope': self.scope}

    def valid(self, authorization):
        if not isinstance(authorization, str) or not authorization.startswith('Bearer ' + self.token_prefix):
            return False
        token = authorization[7:]
        with self.lock:
            digest = hashlib.sha256(token.encode()).hexdigest()
            expiry = self.sessions.get(digest, 0)
            if expiry <= self.clock():
                self.sessions.pop(digest, None)
                return False
            return True

    def revoke(self, authorization):
        with self.lock:
            self.sessions.pop(hashlib.sha256(authorization[7:].encode()).hexdigest(), None)


sessions = PinSessions()


async def require_fe_express_access(request: Request):
    # Only the exact login operation is public. Every other FE operation requires a session.
    if request.method == 'POST' and request.url.path == PREFIX + '/pin/login':
        return
    authorization = request.headers.get('authorization', '')
    if sessions.valid(authorization):
        return
    from security.website_phone_access import sessions as website_sessions
    if website_sessions.valid(authorization):
        return
    key = request.headers.get('x-admin-key', '') or request.headers.get('x-api-key', '')
    if await asyncio.to_thread(verify_admin_credentials, key, authorization):
        return
    raise HTTPException(401, 'Enter the FE Express PIN to continue.')
