from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from security import firebase_auth as auth
from security.native_creative_handoff import CreativeHandoffs, CreativeScope, HandoffDenied


class VerifiedContextTests(unittest.TestCase):
    def setUp(self):
        auth._token_cache.clear()
        self.environment = patch.dict(auth.os.environ, {'AI_BS_ADMIN_EMAILS':'owner@example.invalid'})
        self.environment.start()
        self.claims = dict(email='owner@example.invalid', email_verified=True, sub='original-owner', exp=1050)
        self.sdk = patch.object(auth.id_token, 'verify_firebase_token', return_value=self.claims)
        self.verify = self.sdk.start()
        self.wall = patch.object(auth.time, 'time', return_value=1000)
        self.wall.start()
        self.mono = patch.object(auth.time, 'monotonic', return_value=500)
        self.mono.start()

    def tearDown(self):
        self.mono.stop(); self.wall.stop(); self.sdk.stop(); self.environment.stop()
        auth._token_cache.clear()

    def test_sdk_expiry_caps_monotonic_context_and_no_secret_repr(self):
        context = auth.verified_firebase_context('synthetic-test-token')
        self.assertEqual(context.principal, 'firebase:ai-bs-dashboard:original-owner')
        self.assertEqual(context.valid_until_monotonic, 550)
        self.assertNotIn('original-owner', repr(context))

    def test_monotonic_sample_precedes_wall_sample_for_conservative_deadline(self):
        order=[]
        with patch.object(auth.time,'monotonic',side_effect=lambda:(order.append('monotonic') or 500)), \
             patch.object(auth.time,'time',side_effect=lambda:(order.append('wall') or 1000)):
            self.assertIsNotNone(auth.verified_firebase_context('synthetic-test-token'))
        self.assertEqual(order[:2],['monotonic','wall'])

    def test_cached_principal_does_not_replace_fresh_sdk_verification(self):
        auth.firebase_admin_principal('synthetic-test-token')
        self.verify.side_effect = ValueError('synthetic verification failure')
        self.assertIsNone(auth.verified_firebase_context('synthetic-test-token'))
        self.assertEqual(self.verify.call_count, 2)

    def test_verified_context_issues_only_matching_owner_scope(self):
        context = auth.verified_firebase_context('synthetic-test-token')
        store = CreativeHandoffs(clock=lambda:500)
        invocation = object()
        wrong = CreativeScope('firebase:ai-bs-dashboard:other', 'p', 'r', 'a'*64, 'b'*64)
        with self.assertRaises(HandoffDenied): store.issue_verified(wrong, invocation, context)
        matching = CreativeScope(context.principal, 'p', 'r', 'a'*64, 'b'*64)
        lease = store.redeem(store.issue_verified(matching, invocation, context), invocation)
        self.assertEqual(store.authorize(lease, invocation, project='p', operation='read').owner, context.principal)

    def test_local_key_and_unverified_claims_cannot_delegate(self):
        for updates in ({'email_verified':False}, {'exp':True}, {'exp':999}, {'email':'other@example.invalid'}):
            self.verify.return_value = dict(self.claims, **updates)
            self.assertIsNone(auth.verified_firebase_context('synthetic-local-key'))

    def test_lifetime_is_bounded_and_verification_latency_does_not_renew(self):
        self.claims['exp'] = 9000
        context = auth.verified_firebase_context('synthetic-test-token')
        self.assertEqual(context.valid_until_monotonic, 800)
        self.mono.stop()
        with patch.object(auth.time, 'monotonic', side_effect=[500, 801]):
            self.assertIsNone(auth.verified_firebase_context('synthetic-test-token'))


if __name__ == '__main__': unittest.main()
