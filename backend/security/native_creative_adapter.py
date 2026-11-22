"""Server-owned join of live native transport identity and creative authority.

No global registry, routes, launcher, credentials or local-admin fallback. The
trusted controller registers exact owned invocations; request data cannot attach
a PID or choose a peer resolver. Revocation removes authority without closing an
editor or its draft-recovery process. Downstream owner/source/CAS checks remain
the creative store's responsibility after this authorization boundary.
"""
from __future__ import annotations
import math
import re
import inspect
import threading

from security.native_creative_handoff import CreativeHandoffs, CreativeScope, HandoffDenied
from security.native_creative_peer import NativePeerResolver, OwnedInvocation


class NativeCreativeAdapter:
    """Bounded process-local registry; lifecycle operations are serialized.

    Exited or changed identities are pruned and revoked on registry access. There
    is no background poller. The supplied grant store belongs to this adapter's
    configuration lifetime: invalidate_all clears both pending grants and leases.
    A successful resolve is a point-in-time check, not a transaction enclosing a
    later creative write or protection from privileged process/code injection.
    """
    def __init__(self, grants, *, peer_resolver=None, capacity=64, on_redeemed=None):
        if on_redeemed is not None and (not callable(on_redeemed) or inspect.iscoroutinefunction(on_redeemed)):
            raise ValueError('A synchronous trusted acknowledgement is required')
        self._on_redeemed=on_redeemed
        if type(grants) is not CreativeHandoffs:
            raise ValueError('An owned CreativeHandoffs store is required')
        if peer_resolver is None:
            peer_resolver = NativePeerResolver()
        if type(peer_resolver) is not NativePeerResolver:
            raise ValueError('A trusted NativePeerResolver is required')
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError('Invalid native invocation capacity')
        self._grants = grants
        self._peer_resolver = peer_resolver
        self._capacity = capacity
        self._invocations = {}
        self._lock = threading.Lock()

    @staticmethod
    def _live(invocation, candidate=None):
        if type(invocation) is not OwnedInvocation:
            return False
        try:
            pin = invocation.candidate_sha256
            return (type(pin) is str and re.fullmatch(r'[a-f0-9]{64}', pin) is not None
                    and (candidate is None or pin == candidate) and invocation.alive() is True)
        except (OSError, ValueError, TypeError, AttributeError):
            return False

    def _remove_locked(self, invocation):
        self._invocations.pop(invocation, None)
        self._grants.revoke_invocation(invocation)

    def _prune_locked(self):
        for invocation, candidate in tuple(self._invocations.items()):
            if not self._live(invocation, candidate):
                self._remove_locked(invocation)

    def register(self, invocation):
        """Trusted controller call only; no caller PID/string attachment API."""
        if type(invocation) is not OwnedInvocation:
            raise HandoffDenied()
        with self._lock:
            self._prune_locked()
            if not self._live(invocation):
                raise HandoffDenied()
            if invocation in self._invocations:
                return
            if (len(self._invocations) >= self._capacity
                    or any(other._pid == invocation._pid for other in self._invocations)):
                raise HandoffDenied()
            self._invocations[invocation] = invocation.candidate_sha256

    def unregister(self, invocation):
        """Idempotent removal also works after exit; never terminates a process."""
        if type(invocation) is not OwnedInvocation:
            raise HandoffDenied()
        with self._lock:
            self._prune_locked()
            self._remove_locked(invocation)

    def invalidate_all(self):
        """Required on trusted authorization/candidate configuration changes."""
        with self._lock:
            self._invocations.clear()
            self._grants.invalidate_all()

    def _peer_locked(self, scope):
        self._prune_locked()
        if not self._invocations:
            raise HandoffDenied()
        try:
            invocation = self._peer_resolver.resolve(scope, tuple(self._invocations))
        except HandoffDenied:
            # A process may exit between the initial prune and the resolver's
            # identity check. Revoke it without repeating the ownership lookup.
            self._prune_locked()
            raise
        candidate = self._invocations.get(invocation)
        if candidate is None or not self._live(invocation, candidate):
            if candidate is not None:
                self._remove_locked(invocation)
            raise HandoffDenied()
        return invocation, candidate

    def redeem(self, scope, grant):
        """Redeem once for the live owned peer; no request-supplied project/PID.

        Scope and remaining lifetime come atomically from the trusted grant store.
        If identity/candidate validation fails after minting, revoke that owned
        invocation's authority before returning a generic refusal.
        """
        with self._lock:
            invocation, candidate = self._peer_locked(scope)
            return self._redeem_locked(invocation, candidate, grant)

    def _owned_locked(self, invocation):
        self._prune_locked()
        if type(invocation) is not OwnedInvocation:
            raise HandoffDenied()
        candidate = self._invocations.get(invocation)
        if candidate is None or not self._live(invocation, candidate):
            raise HandoffDenied()
        return candidate

    def redeem_owned_channel(self, invocation, grant):
        """Trusted controller only: invocation comes from its inherited channel.

        Never expose this as a route accepting a PID, object ID or request field.
        The channel owner must revoke on EOF, timeout and protocol failure.
        """
        with self._lock:
            candidate = self._owned_locked(invocation)
            return self._redeem_locked(invocation, candidate, grant)

    def _redeem_locked(self, invocation, candidate, grant):
        lease, authorized, remaining = self._grants.redeem_with_details(grant, invocation)
        if (not self._live(invocation, candidate) or type(authorized) is not CreativeScope
                or authorized.candidate_sha256 != candidate
                or type(remaining) not in (int, float) or not math.isfinite(remaining)
                or not 0 < remaining <= 300):
            self._remove_locked(invocation)
            raise HandoffDenied()
        if self._on_redeemed is not None:
            try:
                result=self._on_redeemed(invocation,lease)
                if inspect.iscoroutine(result):result.close()
                if result is not None:raise HandoffDenied()
                if not self._live(invocation,candidate):raise HandoffDenied()
            except Exception:
                self._remove_locked(invocation)
                raise HandoffDenied() from None
        return dict(lease=lease, project=authorized.project,
                    revision=authorized.opening_revision, source_sha256=authorized.source_sha256,
                    expires_in=remaining)

    def resolve(self, scope, lease, *, project, operation) -> CreativeScope:
        """Join direct ASGI peer, exact live invocation and project-scoped lease."""
        if (type(project) is not str or not project or len(project) > 256
                or any(ord(character) < 32 for character in project)
                or type(operation) is not str):
            raise HandoffDenied()
        with self._lock:
            invocation, candidate = self._peer_locked(scope)
            authorized = self._grants.authorize(lease, invocation, project=project, operation=operation)
            if not self._live(invocation, candidate):
                self._remove_locked(invocation)
                raise HandoffDenied()
            if type(authorized) is not CreativeScope or authorized.candidate_sha256 != candidate:
                raise HandoffDenied()
            return authorized

    def resolve_owned_channel(self, invocation, lease, *, project, operation) -> CreativeScope:
        """Authorize a controller-bound pipe operation; no HTTP peer bypass route."""
        if (type(project) is not str or not project or len(project) > 256
                or any(ord(character) < 32 for character in project)
                or type(operation) is not str):
            raise HandoffDenied()
        with self._lock:
            candidate = self._owned_locked(invocation)
            authorized = self._grants.authorize(lease, invocation, project=project, operation=operation)
            if not self._live(invocation, candidate):
                self._remove_locked(invocation)
                raise HandoffDenied()
            if type(authorized) is not CreativeScope or authorized.candidate_sha256 != candidate:
                raise HandoffDenied()
            return authorized
