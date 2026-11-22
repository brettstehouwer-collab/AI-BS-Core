"""Registry joins with controlled identities, not real processes or OS tables.

These construct exact OwnedInvocation objects while mocking only their low-level
identity observation; NativePeerResolver and CreativeHandoffs logic remain real.
Actual Windows peer ownership is qualified separately, including retained flake.
"""
import concurrent.futures
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from core.opencode_worker import _WinProcess
from security.native_creative_adapter import NativeCreativeAdapter
from security.native_creative_handoff import CreativeHandoffs, CreativeScope, HandoffDenied
from security.native_creative_peer import NativePeerResolver, OwnedInvocation


@unittest.skipUnless(os.name == 'nt', 'Exact Windows OwnedInvocation constructor')
class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.
        self.next_pid = 800000
        self.identity = patch.object(OwnedInvocation, '_identity', autospec=True,
                                     side_effect=self._controlled_identity)
        self.identity.start()
        self.addCleanup(self.identity.stop)
        self.no_close = patch.object(_WinProcess, 'close',
                                     side_effect=AssertionError('Authority must not terminate editors'))
        self.close_mock = self.no_close.start()
        self.addCleanup(self.no_close.stop)
        self.grants = CreativeHandoffs(clock=lambda: self.now, capacity=256)
        self.peer = NativePeerResolver(endpoint=('127.0.0.1', 8080))
        self.owner_pid = None
        lookup = patch.object(self.peer, '_owner', side_effect=lambda peer: self.owner_pid)
        self.lookup = lookup.start()
        self.addCleanup(lookup.stop)
        self.adapter = NativeCreativeAdapter(self.grants, peer_resolver=self.peer)
        self.http = dict(type='http', client=('127.0.0.1', 32123),
                         server=('127.0.0.1', 8080), headers=[])

    @staticmethod
    def _controlled_identity(invocation):
        process = invocation._process
        if (not process.fixture_alive or process.hp != invocation._handle
                or process.pid != invocation._pid):
            return None
        return process.fixture_birth

    def _invocation(self, *, process=None, candidate='b' * 64):
        if process is None:
            self.next_pid += 1
            process = object.__new__(_WinProcess)
            process.pid = self.next_pid
            process.hp = self.next_pid + 1000000
            process.fixture_alive = True
            process.fixture_birth = self.next_pid * 100
        return OwnedInvocation(process, candidate_sha256=candidate)

    def _lease(self, invocation, *, owner='owner-a', project='project-a', candidate=None):
        self.now += 1
        scope = CreativeScope('firebase:fixture:' + owner, project, 'revision-a',
                              'a' * 64, candidate or invocation.candidate_sha256)
        grant = self.grants.issue(scope, invocation, auth_deadline=self.now + 1000)
        return self.grants.redeem(grant, invocation), scope

    def _resolve(self, lease, *, project='project-a', operation='read'):
        return self.adapter.resolve(self.http, lease, project=project, operation=operation)

    def test_real_peer_and_store_join_all_explicit_creative_operations(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, expected = self._lease(invocation)
        self.owner_pid = invocation._pid
        with patch.object(self.grants, 'authorize', wraps=self.grants.authorize) as authorized:
            for operation in ('read', 'save', 'export_fdx', 'export_pdf'):
                self.assertIs(self._resolve(lease, operation=operation), expected)
                authorized.assert_called_with(lease, invocation, project='project-a', operation=operation)
        self.assertEqual(self.lookup.call_count, 8)  # Resolver keeps both real sampling stages.

    def test_only_exact_live_owned_objects_can_register_or_unregister(self):
        for value in (None, 123, 'pid:123', {}, object()):
            with self.assertRaises(HandoffDenied): self.adapter.register(value)
            with self.assertRaises(HandoffDenied): self.adapter.unregister(value)
        invocation = self._invocation()
        invocation._process.fixture_alive = False
        with self.assertRaises(HandoffDenied): self.adapter.register(invocation)
        self.assertFalse(self.close_mock.called)

    def test_empty_or_unregistered_invocation_cannot_use_a_valid_store_lease(self):
        invocation = self._invocation()
        lease, _ = self._lease(invocation)
        self.owner_pid = invocation._pid
        with patch.object(self.grants, 'authorize', wraps=self.grants.authorize) as authorized:
            with self.assertRaises(HandoffDenied): self._resolve(lease)
            self.adapter.register(self._invocation())
            with self.assertRaises(HandoffDenied): self._resolve(lease)
            authorized.assert_not_called()

    def test_same_project_different_owner_and_process_remain_isolated(self):
        first, second = self._invocation(), self._invocation()
        for invocation in (first, second): self.adapter.register(invocation)
        first_lease, _ = self._lease(first)
        second_lease, second_scope = self._lease(second, owner='owner-b')
        self.owner_pid = second._pid
        with self.assertRaises(HandoffDenied): self._resolve(first_lease)
        self.assertIs(self._resolve(second_lease), second_scope)
        self.assertEqual(second_scope.owner, 'firebase:fixture:owner-b')

    def test_project_operation_and_missing_lease_never_fall_back(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, _ = self._lease(invocation)
        self.owner_pid = invocation._pid
        for project, operation, token in (
            ('other-project', 'read', lease), ('project-a', 'import', lease),
            ('project-a', 'model', lease), ('project-a', 'tool', lease),
            ('project-a', 'export_text', lease), ('project-a', 'read', None),
            ('project-a', 'read', 'local_admin'), ([], 'read', lease),
            ('project-a', [], lease), ('', 'read', lease),
        ):
            with self.assertRaises(HandoffDenied):
                self._resolve(token, project=project, operation=operation)
        self.now += 301
        with self.assertRaises(HandoffDenied): self._resolve(lease)

    def test_forwarding_or_peer_refusal_precedes_grant_authorization(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, _ = self._lease(invocation)
        self.owner_pid = invocation._pid
        with patch.object(self.grants, 'authorize', wraps=self.grants.authorize) as authorized:
            for name in (b'forwarded', b'x-forwarded-for'):
                with self.assertRaises(HandoffDenied):
                    self.adapter.resolve({**self.http, 'headers': [(name, b'fixture')]}, lease,
                                         project='project-a', operation='read')
            with patch.object(self.peer, '_owner', side_effect=HandoffDenied()):
                with self.assertRaises(HandoffDenied): self._resolve(lease)
            authorized.assert_not_called()

    def test_candidate_scope_must_match_registered_owned_binary(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, _ = self._lease(invocation, candidate='c' * 64)
        self.owner_pid = invocation._pid
        with self.assertRaises(HandoffDenied): self._resolve(lease)

    def test_changed_candidate_is_pruned_and_all_its_authority_revoked(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, _ = self._lease(invocation)
        self.owner_pid = invocation._pid
        invocation._candidate_sha256 = 'c' * 64
        with self.assertRaises(HandoffDenied): self._resolve(lease)
        invocation._candidate_sha256 = 'b' * 64
        self.adapter.register(invocation)
        with self.assertRaises(HandoffDenied): self._resolve(lease)

    def test_register_is_idempotent_but_duplicate_process_wrapper_is_denied(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        self.adapter.register(invocation)
        self.assertEqual(len(self.adapter._invocations), 1)
        duplicate = self._invocation(process=invocation._process)
        with self.assertRaises(HandoffDenied): self.adapter.register(duplicate)

    def test_capacity_is_max64_and_concurrent_admission_is_atomic(self):
        for value in (0, 65, True, 1.5):
            with self.assertRaises(ValueError): NativeCreativeAdapter(self.grants, capacity=value)
        for _ in range(64): self.adapter.register(self._invocation())
        with self.assertRaises(HandoffDenied): self.adapter.register(self._invocation())
        small = NativeCreativeAdapter(self.grants, peer_resolver=self.peer, capacity=2)
        invocations = [self._invocation() for _ in range(8)]
        barrier = threading.Barrier(8)
        def register(invocation):
            barrier.wait(timeout=3)
            try: small.register(invocation); return True
            except HandoffDenied: return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            accepted = list(pool.map(register, invocations))
        self.assertEqual(sum(accepted), 2)
        self.assertEqual(len(small._invocations), 2)

    def test_exited_or_changed_handle_is_pruned_revoked_and_capacity_reclaimed(self):
        for mutation in ('exit', 'handle', 'birth'):
            with self.subTest(mutation=mutation):
                adapter = NativeCreativeAdapter(self.grants, peer_resolver=self.peer, capacity=1)
                invocation = self._invocation()
                adapter.register(invocation)
                lease, _ = self._lease(invocation)
                if mutation == 'exit': invocation._process.fixture_alive = False
                elif mutation == 'handle': invocation._process.hp += 1
                else: invocation._process.fixture_birth += 1
                adapter.register(self._invocation())
                with self.assertRaises(HandoffDenied):
                    self.grants.authorize(lease, invocation, project='project-a', operation='read')
                self.assertEqual(len(adapter._invocations), 1)

    def test_unregister_and_configuration_invalidation_revoke_without_killing_editor(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, _ = self._lease(invocation)
        self.owner_pid = invocation._pid
        self.adapter.unregister(invocation)
        self.adapter.unregister(invocation)
        self.adapter.register(invocation)
        with self.assertRaises(HandoffDenied): self._resolve(lease)
        lease, scope = self._lease(invocation)
        self.now += 1
        pending = self.grants.issue(scope, invocation, auth_deadline=self.now + 1000)
        self.adapter.invalidate_all()
        self.assertEqual(len(self.adapter._invocations), 0)
        self.adapter.register(invocation)
        with self.assertRaises(HandoffDenied): self._resolve(lease)
        with self.assertRaises(HandoffDenied): self.grants.redeem(pending, invocation)
        self.assertTrue(invocation.alive())
        self.close_mock.assert_not_called()

    def test_exit_during_authorize_cannot_return_a_scope(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, _ = self._lease(invocation)
        self.owner_pid = invocation._pid
        original = self.grants.authorize
        def authorize(*args, **kwargs):
            scope = original(*args, **kwargs)
            invocation._process.fixture_alive = False
            return scope
        with patch.object(self.grants, 'authorize', side_effect=authorize):
            with self.assertRaises(HandoffDenied): self._resolve(lease)
        with self.assertRaises(HandoffDenied):
            original(lease, invocation, project='project-a', operation='read')

    def test_exit_during_peer_check_revokes_without_repeating_os_lookup(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, scope = self._lease(invocation)
        self.now += 1
        pending = self.grants.issue(scope, invocation, auth_deadline=self.now + 1000)
        def lookup(peer):
            invocation._process.fixture_alive = False
            return invocation._pid
        with patch.object(self.peer, '_owner', side_effect=lookup) as reader:
            with self.assertRaises(HandoffDenied): self._resolve(lease)
            reader.assert_called_once()
        self.assertEqual(len(self.adapter._invocations), 0)
        with self.assertRaises(HandoffDenied):
            self.grants.authorize(lease, invocation, project='project-a', operation='read')
        with self.assertRaises(HandoffDenied): self.grants.redeem(pending, invocation)
        self.adapter.register(self._invocation())
        self.assertEqual(len(self.adapter._invocations), 1)
        self.close_mock.assert_not_called()

    def test_unregister_waits_for_current_resolution_and_next_request_is_denied(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, scope = self._lease(invocation)
        entered, release, unregister_started = threading.Event(), threading.Event(), threading.Event()
        def lookup(peer):
            entered.set()
            if not release.wait(timeout=3): raise AssertionError('Bounded fixture gate timed out')
            return invocation._pid
        def unregister():
            unregister_started.set()
            self.adapter.unregister(invocation)
        with patch.object(self.peer, '_owner', side_effect=lookup):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                resolving = pool.submit(self._resolve, lease)
                try:
                    self.assertTrue(entered.wait(timeout=3))
                    removing = pool.submit(unregister)
                    self.assertTrue(unregister_started.wait(timeout=3))
                    with self.assertRaises(concurrent.futures.TimeoutError): removing.result(timeout=.05)
                finally:
                    release.set()
                self.assertIs(resolving.result(timeout=3), scope)
                removing.result(timeout=3)
        with self.assertRaises(HandoffDenied): self._resolve(lease)

    def test_redeem_joins_peer_and_returns_only_authoritative_client_contract(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        self.owner_pid = invocation._pid
        expected = CreativeScope('firebase:fixture:original-owner', 'original-project', 'revision-r',
                                 'c' * 64, invocation.candidate_sha256)
        grant = self.grants.issue(expected, invocation, auth_deadline=140)
        self.now = 120
        response = self.adapter.redeem(self.http, grant)
        self.assertEqual(set(response), {'lease', 'project', 'revision', 'source_sha256', 'expires_in'})
        self.assertEqual({key: value for key, value in response.items() if key != 'lease'},
                         dict(project='original-project', revision='revision-r',
                              source_sha256='c' * 64, expires_in=20))
        self.assertIs(self._resolve(response['lease'], project='original-project'), expected)
        with self.assertRaises(HandoffDenied): self.adapter.redeem(self.http, grant)
        self.now = 140
        with self.assertRaises(HandoffDenied): self._resolve(response['lease'], project='original-project')

    def test_wrong_peer_cannot_redeem_or_consume_another_invocations_grant(self):
        first, second = self._invocation(), self._invocation()
        self.adapter.register(first)
        self.adapter.register(second)
        scope = CreativeScope('firebase:fixture:first', 'project-a', 'r', 'a' * 64, first.candidate_sha256)
        grant = self.grants.issue(scope, first, auth_deadline=1000)
        self.owner_pid = second._pid
        with self.assertRaises(HandoffDenied): self.adapter.redeem(self.http, grant)
        self.owner_pid = first._pid
        self.assertEqual(self.adapter.redeem(self.http, grant)['project'], 'project-a')

    def test_redeem_candidate_mismatch_revokes_minted_and_existing_owned_authority(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        self.owner_pid = invocation._pid
        existing, _ = self._lease(invocation)
        self.now += 1
        wrong = CreativeScope('firebase:fixture:owner-a', 'project-a', 'r', 'a' * 64, 'c' * 64)
        grant = self.grants.issue(wrong, invocation, auth_deadline=1000)
        with self.assertRaises(HandoffDenied): self.adapter.redeem(self.http, grant)
        self.assertEqual(len(self.adapter._invocations), 0)
        with self.assertRaises(HandoffDenied):
            self.grants.authorize(existing, invocation, project='project-a', operation='read')

    def test_exit_after_atomic_store_redemption_revokes_the_unreturned_lease(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        self.owner_pid = invocation._pid
        scope = CreativeScope('firebase:fixture:owner-a', 'project-a', 'r', 'a' * 64, 'b' * 64)
        grant = self.grants.issue(scope, invocation, auth_deadline=1000)
        minted = []
        original = self.grants.redeem_with_details
        def redeem(*args):
            result = original(*args)
            minted.append(result[0])
            invocation._process.fixture_alive = False
            return result
        with patch.object(self.grants, 'redeem_with_details', side_effect=redeem):
            with self.assertRaises(HandoffDenied): self.adapter.redeem(self.http, grant)
        self.assertEqual(len(minted), 1)
        with self.assertRaises(HandoffDenied):
            self.grants.authorize(minted[0], invocation, project='project-a', operation='read')
        self.close_mock.assert_not_called()

    def test_concurrent_adapter_redemption_yields_one_lease_without_retries(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        self.owner_pid = invocation._pid
        scope = CreativeScope('firebase:fixture:owner-a', 'project-a', 'r', 'a' * 64, 'b' * 64)
        grant = self.grants.issue(scope, invocation, auth_deadline=1000)
        barrier = threading.Barrier(4)
        def redeem(_):
            barrier.wait(timeout=3)
            try: return self.adapter.redeem(self.http, grant)
            except HandoffDenied: return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(redeem, range(4)))
        self.assertEqual(sum(value is not None for value in outcomes), 1)
        response = next(value for value in outcomes if value is not None)
        self.assertIs(self._resolve(response['lease']), scope)


    def test_owned_channel_uses_exact_registered_invocation_not_http_lookup(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        expected = CreativeScope('firebase:fixture:owner-a', 'project-a', 'r', 'a'*64, 'b'*64)
        grant = self.grants.issue(expected, invocation, auth_deadline=1000)
        response = self.adapter.redeem_owned_channel(invocation, grant)
        self.lookup.assert_not_called()
        for operation in ('read', 'save', 'export_fdx', 'export_pdf'):
            self.assertIs(self.adapter.resolve_owned_channel(invocation, response['lease'],
                project='project-a', operation=operation), expected)
        with self.assertRaises(HandoffDenied):
            self.adapter.redeem_owned_channel(invocation, grant)
        other = self._invocation()
        self.adapter.register(other)
        for supplied in (None, invocation._pid, str(invocation._pid), other):
            with self.assertRaises(HandoffDenied):
                self.adapter.resolve_owned_channel(supplied, response['lease'],
                    project='project-a', operation='read')
        self.adapter.unregister(invocation)
        with self.assertRaises(HandoffDenied):
            self.adapter.resolve_owned_channel(invocation, response['lease'],
                project='project-a', operation='read')
        self.close_mock.assert_not_called()

    def test_owned_channel_scope_expiry_and_identity_changes_fail_closed(self):
        invocation = self._invocation()
        self.adapter.register(invocation)
        lease, _ = self._lease(invocation)
        for project, operation in (('other', 'read'), ('project-a', 'model'), ('', 'read')):
            with self.assertRaises(HandoffDenied):
                self.adapter.resolve_owned_channel(invocation, lease, project=project, operation=operation)
        self.now += 301
        with self.assertRaises(HandoffDenied):
            self.adapter.resolve_owned_channel(invocation, lease, project='project-a', operation='read')
        lease, _ = self._lease(invocation)
        invocation._process.fixture_birth += 1
        with self.assertRaises(HandoffDenied):
            self.adapter.resolve_owned_channel(invocation, lease, project='project-a', operation='read')
        self.assertNotIn(invocation, self.adapter._invocations)
        self.close_mock.assert_not_called()

    def test_trusted_acknowledgement_runs_before_response(self):
        seen=[]
        def acknowledge(invocation,lease):
            seen.append(self.grants.authorize(lease,invocation,project='project-a',operation='read').owner)
        self.adapter=NativeCreativeAdapter(self.grants,peer_resolver=self.peer,on_redeemed=acknowledge)
        invocation=self._invocation();self.adapter.register(invocation);self.owner_pid=invocation._pid
        scope=CreativeScope('firebase:fixture:owner-a','project-a','r','a'*64,'b'*64)
        grant=self.grants.issue(scope,invocation,auth_deadline=1000)
        response=self.adapter.redeem(self.http,grant)
        self.assertEqual(seen,[scope.owner]);self.assertTrue(response['lease'])

    def test_failed_acknowledgement_revokes_before_refusal(self):
        leases=[]
        def reject(invocation,lease):leases.append(lease);raise RuntimeError('synthetic private detail')
        self.adapter=NativeCreativeAdapter(self.grants,peer_resolver=self.peer,on_redeemed=reject)
        invocation=self._invocation();self.adapter.register(invocation);self.owner_pid=invocation._pid
        scope=CreativeScope('firebase:fixture:owner-a','project-a','r','a'*64,'b'*64)
        grant=self.grants.issue(scope,invocation,auth_deadline=1000)
        with self.assertRaises(HandoffDenied):self.adapter.redeem(self.http,grant)
        with self.assertRaises(HandoffDenied):self.grants.authorize(leases[0],invocation,project='project-a',operation='read')
        self.assertNotIn(invocation,self.adapter._invocations)

if __name__ == '__main__':
    unittest.main(verbosity=2)
