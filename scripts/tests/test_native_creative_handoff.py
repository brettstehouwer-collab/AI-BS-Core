import concurrent.futures
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from security.native_creative_handoff import CreativeHandoffs, CreativeScope, HandoffDenied


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.
        self.store = CreativeHandoffs(clock=lambda: self.now, capacity=2)
        self.scope = CreativeScope('firebase:test:owner-a', 'project-a', 'revision-a', 'a'*64, 'b'*64)
        self.invocation = object()

    def issue(self, deadline=1000):
        return self.store.issue(self.scope, self.invocation, auth_deadline=deadline)

    def test_once_under_concurrent_redemption(self):
        grant = self.issue()
        def redeem(_):
            try: return self.store.redeem(grant, self.invocation)
            except HandoffDenied: return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            leases = list(pool.map(redeem, range(16)))
        self.assertEqual(sum(value is not None for value in leases), 1)
        self.assertNotIn(grant, repr(self.store.__dict__))

    def test_exact_invocation_resource_and_operations(self):
        grant = self.issue()
        with self.assertRaises(HandoffDenied): self.store.redeem(grant, object())
        lease = self.store.redeem(grant, self.invocation)
        for operation in self.store.OPERATIONS:
            self.assertIs(self.store.authorize(lease, self.invocation, project='project-a', operation=operation), self.scope)
        for project, operation, invocation in [('other', 'read', self.invocation), ('project-a', 'import', self.invocation), ('project-a', 'read', object())]:
            with self.assertRaises(HandoffDenied): self.store.authorize(lease, invocation, project=project, operation=operation)

    def test_grant_and_lease_expire_at_boundary_and_auth_cap(self):
        grant = self.issue()
        self.now = 130
        with self.assertRaises(HandoffDenied): self.store.redeem(grant, self.invocation)
        grant = self.issue(deadline=135)
        lease = self.store.redeem(grant, self.invocation)
        self.now = 135
        with self.assertRaises(HandoffDenied): self.store.authorize(lease, self.invocation, project='project-a', operation='read')

    def test_lease_never_exceeds_five_minutes(self):
        grant = self.issue()
        self.now = 129
        lease = self.store.redeem(grant, self.invocation)
        self.now = 400
        with self.assertRaises(HandoffDenied): self.store.authorize(lease, self.invocation, project='project-a', operation='save')

    def test_no_local_owner_or_unverified_lifetime(self):
        with self.assertRaises(HandoffDenied): CreativeScope('local_admin', 'p', 'r', 'a'*64, 'b'*64)
        for value in (None, float('inf'), float('nan'), 99, True):
            with self.assertRaises(HandoffDenied): self.issue(value)

    def test_rate_capacity_revocation_and_restart(self):
        grant = self.issue()
        with self.assertRaises(HandoffDenied): self.issue()
        lease = self.store.redeem(grant, self.invocation)
        self.store.revoke_invocation(self.invocation)
        with self.assertRaises(HandoffDenied): self.store.authorize(lease, self.invocation, project='project-a', operation='read')
        self.now += 1
        grant = self.issue()
        with self.assertRaises(HandoffDenied): CreativeHandoffs().redeem(grant, self.invocation)
        self.store.invalidate_all()
        with self.assertRaises(HandoffDenied): self.store.redeem(grant, self.invocation)

    def test_distinct_owners_and_bounded_pending_grants(self):
        self.issue()
        scope_b = CreativeScope('firebase:test:owner-b', 'project-b', 'r', 'a'*64, 'b'*64)
        self.store.issue(scope_b, object(), auth_deadline=1000)
        scope_c = CreativeScope('firebase:test:owner-c', 'project-c', 'r', 'a'*64, 'b'*64)
        with self.assertRaises(HandoffDenied): self.store.issue(scope_c, object(), auth_deadline=1000)


    def test_response_lifetime_uses_original_authorization_deadline(self):
        grant=self.issue(deadline=145)
        self.now=125
        lease=self.store.redeem(grant,self.invocation)
        scope,ttl=self.store.authorize_with_lifetime(lease,self.invocation,project='project-a',operation='read')
        self.assertIs(scope,self.scope)
        self.assertEqual(ttl,20)
        self.now=145
        with self.assertRaises(HandoffDenied):
            self.store.authorize_with_lifetime(lease,self.invocation,project='project-a',operation='read')

    def test_redemption_details_are_atomic_and_server_scoped(self):
        grant=self.issue(deadline=145)
        self.now=125
        lease,scope,ttl=self.store.redeem_with_details(grant,self.invocation)
        self.assertIs(scope,self.scope)
        self.assertEqual(ttl,20)
        self.assertIs(self.store.authorize(lease,self.invocation,project=scope.project,operation='read'),scope)
        with self.assertRaises(HandoffDenied):self.store.redeem_with_details(grant,self.invocation)

if __name__ == '__main__': unittest.main()
