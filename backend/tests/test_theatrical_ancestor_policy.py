"""Synthetic descriptors and newly created native fixtures; no original data."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from backend.security.theatrical_corpus_boundary import CorpusBoundaryError
from backend.security import theatrical_ancestor_policy as policy
from backend.security import theatrical_storage_roots as roots

if os.name == 'nt':
    import pywintypes
    import win32file
    import win32security

BASE = Path('C:/AI-BS/backups/theatrical_ancestors_20261026T110600Z')


@unittest.skipUnless(os.name == 'nt', 'Windows descriptors and handles required')
class AncestorPolicyTests(unittest.TestCase):
    def setUp(self):
        self.sid = roots._current_principal()

    def assert_code(self, expected, call):
        with self.assertRaises(CorpusBoundaryError) as caught:
            call()
        self.assertEqual(str(caught.exception), expected)

    def sd(self, aces='', owner=None):
        return win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            f'O:{owner or self.sid}D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;{self.sid}){aces}', 1)

    def fresh_parent(self):
        # C:\ProgramData and the checkout have broad metadata grants here. Do not
        # repair either. Only a new, exact protected root-level test directory.
        target = Path('C:/AIBS_Ancestor_Fixture_' + uuid.uuid4().hex)
        sa = pywintypes.SECURITY_ATTRIBUTES()
        sa.SECURITY_DESCRIPTOR = self.sd()
        win32file.CreateDirectory(str(target), sa)
        with (BASE / ('fixture_' + target.name + '.json')).open('x', encoding='utf-8') as out:
            json.dump({'new_synthetic_parent': str(target), 'retained': True}, out)
        return target

    def store(self):
        parent = self.fresh_parent()
        store = policy.AncestorGuardedBlobs.create(str(parent / 'corpus'))
        self.addCleanup(store.close)
        return parent, store

    def test_exact_trusted_owners_and_trustees(self):
        for owner in [self.sid, 'S-1-5-18', 'S-1-5-32-544', policy.TRUSTED_INSTALLER]:
            policy.validate_ancestor_descriptor(self.sd(owner=owner), self.sid)

    def test_read_traverse_and_child_creation_are_not_ancestor_mutation(self):
        policy.validate_ancestor_descriptor(self.sd('(A;;GRGX;;;BU)(A;;0x6;;;AU)'), self.sid)
        policy.validate_ancestor_descriptor(self.sd('(A;OICIIO;GA;;;AU)'), self.sid)

    def test_each_untrusted_mutation_right_is_rejected(self):
        for mask in [0x10, 0x40, 0x100, 0x10000, 0x40000, 0x80000,
                     0x40000000, 0x10000000, 0x02000000, 0x01000000]:
            with self.subTest(mask=mask):
                self.assert_code('CORPUS_ANCESTOR_ACL_REFUSED', lambda:
                    policy.validate_ancestor_descriptor(self.sd(f'(A;;0x{mask:08x};;;AU)'), self.sid))

    def test_deny_does_not_cancel_unsafe_allow_in_conservative_policy(self):
        self.assert_code('CORPUS_ANCESTOR_ACL_REFUSED', lambda:
            policy.validate_ancestor_descriptor(self.sd('(D;;GA;;;AU)(A;;GW;;;AU)'), self.sid))

    def test_unknown_owner_is_rejected_even_with_owner_rights_deny(self):
        self.assert_code('CORPUS_ANCESTOR_ACL_REFUSED', lambda:
            policy.validate_ancestor_descriptor(self.sd('(D;;WDWO;;;OW)', 'S-1-5-11'), self.sid))

    def test_null_or_absent_dacl_is_not_admitted(self):
        for text in [f'O:{self.sid}', f'O:{self.sid}D:NO_ACCESS_CONTROL']:
            sd = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(text, 1)
            self.assert_code('CORPUS_ANCESTOR_ACL_REFUSED', lambda:
                policy.validate_ancestor_descriptor(sd, self.sid))

    def test_unsupported_ace_and_flags_are_rejected(self):
        real = self.sd()
        for ace in [((5, 0), 0x1, win32security.ConvertStringSidToSid('S-1-5-11')),
                    ((0, 0x40), 0x1, win32security.ConvertStringSidToSid('S-1-5-11'))]:
            fake_acl = SimpleNamespace(GetAceCount=lambda: 1, GetAce=lambda _: ace)
            fake_sd = SimpleNamespace(GetSecurityDescriptorOwner=real.GetSecurityDescriptorOwner,
                GetSecurityDescriptorControl=real.GetSecurityDescriptorControl,
                GetSecurityDescriptorDacl=lambda: fake_acl)
            self.assert_code('CORPUS_ANCESTOR_ACL_REFUSED', lambda:
                policy.validate_ancestor_descriptor(fake_sd, self.sid))

    def test_actual_checkout_ancestor_is_refused_before_leaf_creation(self):
        target = BASE / ('must_not_create_' + uuid.uuid4().hex)
        self.assert_code('CORPUS_ANCESTOR_ACL_REFUSED', lambda:
            policy.AncestorGuardedBlobs.create(str(target)))
        self.assertFalse(target.exists())

    def test_actual_protected_parent_allows_exact_roundtrip_and_retention(self):
        parent, store = self.store()
        original = 'INT. STAGE\r\nCaf\u00e9 \U0001f3ad\x00\n'.encode()
        digest = store.put(original)
        self.assertEqual(store.read(digest), original)
        store.verify()
        store.close()
        self.assertEqual((parent / 'corpus' / (digest + '.blob')).read_bytes(), original)
        self.assert_code('CORPUS_ANCESTOR_CLOSED', lambda: store.read(digest))

    def test_actual_parent_metadata_grant_causes_refusal_without_api_repair(self):
        parent, store = self.store()
        digest = store.put(b'original')
        before = win32security.GetFileSecurity(str(parent), 5)
        acl = before.GetSecurityDescriptorDacl()
        acl.AddAccessAllowedAce(2, 0x100, win32security.ConvertStringSidToSid('S-1-5-11'))
        changed = win32security.SECURITY_DESCRIPTOR()
        changed.SetSecurityDescriptorDacl(1, acl, 0)
        win32security.SetFileSecurity(str(parent), 4, changed)
        try:
            self.assert_code('CORPUS_ANCESTOR_ACL_REFUSED', lambda: store.read(digest))
            actual = win32security.GetFileSecurity(str(parent), 4).GetSecurityDescriptorDacl()
            self.assertEqual(actual.GetAceCount(), 4)
            self.assert_code('CORPUS_ANCESTOR_TAINTED', store.verify)
        finally:
            # Fixture restoration only; never performed by the implementation.
            win32security.SetFileSecurity(str(parent), 4, self.sd())

    def test_preexisting_leaf_bytes_are_not_adopted_or_changed(self):
        parent = self.fresh_parent()
        leaf = parent / 'corpus'
        leaf.write_bytes(b'original')
        self.assert_code('CORPUS_STORAGE_CREATE_REFUSED', lambda:
            policy.AncestorGuardedBlobs.create(str(leaf)))
        self.assertEqual(leaf.read_bytes(), b'original')

    def test_descriptor_read_error_is_redacted_and_taints(self):
        _, store = self.store()
        with patch.object(win32security, 'GetSecurityInfo', side_effect=OSError('private path')):
            self.assert_code('CORPUS_ANCESTOR_NATIVE_UNAVAILABLE', store.verify)
        self.assert_code('CORPUS_ANCESTOR_TAINTED', store.verify)

    def test_interrupt_taints_and_propagates(self):
        _, store = self.store()
        with patch.object(store._store, 'put', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                store.put(b'interrupted')
        self.assert_code('CORPUS_ANCESTOR_TAINTED', store.verify)


if __name__ == '__main__':
    unittest.main()
