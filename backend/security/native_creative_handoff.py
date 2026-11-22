"""Memory-only capabilities for a future owner-fenced native creative adapter.

No routes are registered here. Callers must verify browser authority/project fences
before issue, bind a trusted owned invocation object, and retain existing store CAS.
No local-admin fallback or process identity inferred from caller-supplied PID.
"""
from dataclasses import dataclass
import hashlib
import math
import re
import secrets
import threading
import time


class HandoffDenied(PermissionError):
    def __init__(self):
        super().__init__('Native creative authorization is unavailable or out of scope.')


@dataclass(frozen=True, repr=False)
class CreativeScope:
    owner: str
    project: str
    opening_revision: str
    source_sha256: str
    candidate_sha256: str

    def __post_init__(self):
        if not isinstance(self.owner, str) or not re.fullmatch(r'firebase:[^:\s]{1,128}:[^\s]{1,256}', self.owner):
            raise HandoffDenied()
        for value in (self.project, self.opening_revision):
            if not isinstance(value, str) or not value or len(value) > 256 or any(ord(c) < 32 for c in value):
                raise HandoffDenied()
        for value in (self.source_sha256, self.candidate_sha256):
            if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
                raise HandoffDenied()


@dataclass(repr=False)
class _Record:
    scope: CreativeScope
    invocation: object
    deadline: float
    auth_deadline: float


class CreativeHandoffs:
    """Bounded process-local store; restart/config invalidation discards authority.

    auth_deadline is mandatory monotonic time derived by the trusted verifier.
    It must never come from request fields or unverified JWT decoding. Invocation
    is a controller-owned object, not a serializable identifier or secret.
    """
    OPERATIONS = frozenset({'read', 'save', 'export_fdx', 'export_pdf'})

    def __init__(self, *, clock=time.monotonic, capacity=64):
        if type(capacity) is not int or not 1 <= capacity <= 256:
            raise ValueError('Invalid handoff capacity')
        self._clock, self._capacity = clock, capacity
        self._lock = threading.Lock()
        self._grants, self._leases, self._issued = {}, {}, {}

    @staticmethod
    def _digest(token, prefix):
        if not isinstance(token, str) or not token.startswith(prefix) or not 40 <= len(token) <= 96:
            raise HandoffDenied()
        return hashlib.sha256(token.encode('utf-8')).digest()

    def _prune(self, now):
        for store in (self._grants, self._leases):
            for key in [key for key, record in store.items() if record.deadline <= now]:
                del store[key]
        for owner in [owner for owner, issued in self._issued.items() if issued + 30 <= now]:
            del self._issued[owner]

    def issue(self, scope, invocation, *, auth_deadline):
        if not isinstance(scope, CreativeScope) or invocation is None or isinstance(invocation, (str, int, bytes)):
            raise HandoffDenied()
        if type(auth_deadline) not in (int, float) or not math.isfinite(auth_deadline):
            raise HandoffDenied()
        with self._lock:
            now = self._clock()
            self._prune(now)
            if (auth_deadline <= now or len(self._grants) >= self._capacity
                    or len(self._issued) >= self._capacity and scope.owner not in self._issued
                    or self._issued.get(scope.owner, -math.inf) + 1 > now):
                raise HandoffDenied()
            token = 'nch_g_' + secrets.token_urlsafe(32)
            self._grants[self._digest(token, 'nch_g_')] = _Record(scope, invocation, min(now + 30, auth_deadline), min(now + 300, auth_deadline))
            self._issued[scope.owner] = now
            return token

    def redeem(self, token, invocation):
        return self.redeem_with_details(token, invocation)[0]

    def redeem_with_details(self, token, invocation):
        """Atomic one-use redemption plus authoritative scope/remaining lifetime."""
        key = self._digest(token, 'nch_g_')
        with self._lock:
            now = self._clock()
            self._prune(now)
            record = self._grants.get(key)
            if record is None or record.invocation is not invocation or len(self._leases) >= self._capacity:
                raise HandoffDenied()
            del self._grants[key]
            lease = 'nch_l_' + secrets.token_urlsafe(32)
            self._leases[self._digest(lease, 'nch_l_')] = _Record(record.scope, invocation, min(now + 300, record.auth_deadline), record.auth_deadline)
            return lease, record.scope, min(now + 300, record.auth_deadline) - now

    def issue_verified(self, scope, invocation, context):
        """Join the SDK-verified context to the existing project-fenced scope."""
        from security.firebase_auth import VerifiedFirebaseContext
        if (not isinstance(context, VerifiedFirebaseContext) or not isinstance(scope, CreativeScope)
                or context.principal != scope.owner):
            raise HandoffDenied()
        return self.issue(scope, invocation, auth_deadline=context.valid_until_monotonic)

    def authorize(self, lease, invocation, *, project, operation):
        return self.authorize_with_lifetime(lease, invocation, project=project, operation=operation)[0]

    def authorize_with_lifetime(self, lease, invocation, *, project, operation):
        """Return scope and server-derived remaining lifetime under one lock."""
        key = self._digest(lease, 'nch_l_')
        with self._lock:
            now = self._clock()
            self._prune(now)
            record = self._leases.get(key)
            if (record is None or record.invocation is not invocation or project != record.scope.project
                    or operation not in self.OPERATIONS):
                raise HandoffDenied()
            return record.scope, record.deadline - now

    def revoke_invocation(self, invocation):
        with self._lock:
            for store in (self._grants, self._leases):
                for key in [key for key, record in store.items() if record.invocation is invocation]:
                    del store[key]

    def invalidate_all(self):
        """Required on authorization-configuration change; no implicit renewal."""
        with self._lock:
            self._grants.clear()
            self._leases.clear()
            self._issued.clear()
