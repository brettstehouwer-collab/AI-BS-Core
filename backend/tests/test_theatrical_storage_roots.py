"""Native Windows synthetic fixtures retained under a new evidence directory."""
import os
from pathlib import Path
import subprocess
import threading
import unittest
import uuid
from unittest.mock import patch

from backend.security.theatrical_corpus_boundary import CorpusBoundaryError
from backend.security.theatrical_storage_roots import ProtectedCorpusRoot, _validate_descriptor

if os.name == 'nt':
    import win32api
    import win32con
    import win32file
    import win32security

BASE = Path('C:/AI-BS/backups/theatrical_storage_20261026T104441Z/native')


@unittest.skipUnless(os.name == 'nt', 'actual Windows handles required')
class StorageRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BASE.mkdir(exist_ok=True)
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        try:
            cls.sid = win32security.ConvertSidToStringSid(
                win32security.GetTokenInformation(token, win32security.TokenUser)[0])
        finally:
            token.Close()

    def target(self, suffix='corpus'):
        parent = BASE / ('case_' + uuid.uuid4().hex)
        parent.mkdir()
        return parent / suffix

    def assert_code(self, code, call):
        with self.assertRaises(CorpusBoundaryError) as caught:
            call()
        self.assertEqual(str(caught.exception), code)

    def descriptor(self, dacl, owner=None):
        return win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            'O:' + (owner or self.sid) + dacl, 1)

    def test_actual_owner_protected_acl_and_child_inheritance(self):
        target = self.target()
        with ProtectedCorpusRoot.create(str(target)) as root:
            self.assertEqual(root.broker_sid, self.sid)
            self.assertEqual(root.path, str(target))
            self.assertRegex(root.identity, r'^[a-f0-9]{8}:[a-f0-9]{16}$')
            root.verify()
            child = target / 'synthetic.txt'
            child.write_bytes(b'INT. STAGE\r\nOriginal synthetic bytes.\r\n')
            sd = win32security.GetFileSecurity(str(child),
                win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
            acl = sd.GetSecurityDescriptorDacl()
            self.assertEqual({win32security.ConvertSidToStringSid(acl.GetAce(i)[2])
                              for i in range(acl.GetAceCount())},
                             {self.sid, 'S-1-5-18', 'S-1-5-32-544'})
            # Native creation copied the inheritable policy without setting the
            # historical INHERITED_ACE bit. Check effective rights, not that bit.
            self.assertTrue(all(acl.GetAce(i)[0] == (0, 0) and acl.GetAce(i)[1] == 0x1F01FF
                                for i in range(acl.GetAceCount())))
            nested = target / 'nested'
            nested.mkdir()
            (nested / 'grandchild.txt').write_bytes(b'fixture')
            sd_nested = win32security.GetFileSecurity(str(nested / 'grandchild.txt'),
                                                    win32security.DACL_SECURITY_INFORMATION)
            nested_acl = sd_nested.GetSecurityDescriptorDacl()
            self.assertEqual([nested_acl.GetAce(i) for i in range(nested_acl.GetAceCount())],
                             [acl.GetAce(i) for i in range(acl.GetAceCount())])
        self.assertTrue(target.exists())
        self.assertEqual(child.read_bytes(), b'INT. STAGE\r\nOriginal synthetic bytes.\r\n')
        self.assert_code('CORPUS_STORAGE_CLOSED', root.verify)

    def test_existing_directory_file_and_contents_are_never_repaired(self):
        for kind in ('directory', 'file'):
            target = self.target()
            if kind == 'directory':
                target.mkdir()
                (target / 'keep.txt').write_bytes(b'KEEP\r\n')
            else:
                target.write_bytes(b'KEEP\r\n')
            sd_before = win32security.GetFileSecurity(str(target),
                win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl().GetAceCount()
            self.assert_code('CORPUS_STORAGE_CREATE_REFUSED',
                             lambda: ProtectedCorpusRoot.create(str(target)))
            self.assertEqual(win32security.GetFileSecurity(str(target),
                win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl().GetAceCount(), sd_before)
            self.assertEqual((target / 'keep.txt' if kind == 'directory' else target).read_bytes(), b'KEEP\r\n')

    def test_root_and_ancestor_cannot_be_renamed_while_handles_are_held(self):
        target = self.target()
        with ProtectedCorpusRoot.create(str(target)) as root:
            for old in (target, target.parent):
                with self.subTest(path=old.name), self.assertRaises(OSError):
                    old.rename(old.with_name(old.name + '_moved'))
            root.verify()
        target.rename(target.with_name('released'))

    def test_concurrent_creation_has_only_one_winner(self):
        target = self.target()
        barrier = threading.Barrier(2)
        roots, errors = [], []
        def attempt():
            barrier.wait(timeout=5)
            try:
                roots.append(ProtectedCorpusRoot.create(str(target)))
            except CorpusBoundaryError as exc:
                errors.append(str(exc))
        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        try:
            self.assertEqual(len(roots), 1)
            self.assertEqual(errors, ['CORPUS_STORAGE_CREATE_REFUSED'])
            roots[0].verify()
        finally:
            for root in roots:
                root.close()

    def test_noncanonical_alias_and_private_path_forms_refused_before_open(self):
        base = str(self.target())
        for value in [None, Path(base), '', 'corpus', '\\\\server\\share\\corpus',
                      '\\\\?\\' + base, base + '\\', base.replace('\\', '/'),
                      base + ':stream', base + '.', base + ' ',
                      base + '\\..\\other', base + '\\NUL', base + '\\COM1.txt',
                      'C:\\corpus', 'C:\\' + 'a'*97 + '\\corpus']:
            with self.subTest(value=value):
                self.assert_code('INVALID_CORPUS_STORAGE_PATH', lambda: ProtectedCorpusRoot.create(value))

    def test_closed_handle_is_idempotent_and_cannot_be_reused(self):
        root = ProtectedCorpusRoot.create(str(self.target()))
        root.close()
        root.close()
        self.assert_code('CORPUS_STORAGE_CLOSED', root.verify)
        self.assert_code('CORPUS_STORAGE_CLOSED', lambda: root.__enter__())

    def test_caller_identity_is_revalidated_on_each_use(self):
        with ProtectedCorpusRoot.create(str(self.target())) as root:
            with patch('backend.security.theatrical_storage_roots._current_principal',
                       return_value='S-1-5-21-1-2-3-999'):
                self.assert_code('CORPUS_STORAGE_CALLER_CHANGED', root.verify)
            root.verify()

    def test_protected_exact_acl_required_including_inheritance_and_owner(self):
        valid = f'D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;{self.sid})'
        _validate_descriptor(self.descriptor(valid), self.sid)
        variants = [valid.replace('D:P', 'D:'), valid.replace('OICI', 'OICIIO', 1),
                    valid.replace('OICI', '', 1), valid.replace('FA', 'FR', 1),
                    valid + '(A;OICI;FA;;;WD)', valid + '(A;OICI;FA;;;OW)',
                    valid + '(A;OICI;FA;;;CO)', valid + '(D;;FW;;;WD)',
                    valid + f'(A;OICI;FA;;;{self.sid})',
                    'D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)', 'D:P', 'D:NO_ACCESS_CONTROL']
        for dacl in variants:
            with self.subTest(dacl=dacl):
                self.assert_code('CORPUS_STORAGE_ACL_REFUSED',
                                 lambda: _validate_descriptor(self.descriptor(dacl), self.sid))
        self.assert_code('CORPUS_STORAGE_ACL_REFUSED',
                         lambda: _validate_descriptor(self.descriptor(valid, 'SY'), self.sid))

    def test_actual_permission_change_is_detected_without_repair(self):
        target = self.target()
        root = ProtectedCorpusRoot.create(str(target))
        self.addCleanup(root.close)
        original = win32security.GetFileSecurity(str(target), win32security.DACL_SECURITY_INFORMATION)
        weak = self.descriptor('D:P(A;OICI;FA;;;WD)')
        try:
            win32security.SetFileSecurity(str(target),
                win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION, weak)
            self.assert_code('CORPUS_STORAGE_ACL_REFUSED', root.verify)
            actual = win32security.GetFileSecurity(str(target), win32security.DACL_SECURITY_INFORMATION)
            self.assertEqual(win32security.ConvertSidToStringSid(actual.GetSecurityDescriptorDacl().GetAce(0)[2]),
                             'S-1-1-0')
        finally:
            # Restore ONLY this freshly created synthetic fixture after proving
            # verify() did not repair it. Production/existing paths are untouched.
            win32security.SetFileSecurity(str(target),
                win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION, original)

    def test_actual_thread_impersonation_is_refused(self):
        with ProtectedCorpusRoot.create(str(self.target())) as root:
            win32security.ImpersonateSelf(win32security.SecurityIdentification)
            try:
                self.assert_code('CORPUS_STORAGE_IMPERSONATION_REFUSED', root.verify)
            finally:
                win32security.RevertToSelf()
            root.verify()

    def test_actual_directory_junction_is_not_followed(self):
        target = self.target()
        destination = target.parent / 'destination'
        destination.mkdir()
        junction = target.parent / 'junction'
        result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(junction), str(destination)],
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, 'synthetic junction fixture creation failed')
        self.assert_code('CORPUS_STORAGE_REPARSE_OR_TYPE_REFUSED',
                         lambda: ProtectedCorpusRoot.create(str(junction / 'leaf')))
        self.assertFalse((destination / 'leaf').exists())

    def test_postcreation_failure_retains_leaf_and_releases_handles(self):
        target = self.target()
        with patch('backend.security.theatrical_storage_roots._validate_descriptor',
                   side_effect=CorpusBoundaryError('CORPUS_STORAGE_ACL_REFUSED')):
            self.assert_code('CORPUS_STORAGE_ACL_REFUSED',
                             lambda: ProtectedCorpusRoot.create(str(target)))
        self.assertTrue(target.is_dir())
        self.assert_code('CORPUS_STORAGE_CREATE_REFUSED',
                         lambda: ProtectedCorpusRoot.create(str(target)))
        target.rename(target.with_name('retained_after_failure'))

    def test_revalidation_observes_all_retained_ancestors(self):
        with ProtectedCorpusRoot.create(str(self.target())) as root:
            from backend.security import theatrical_storage_roots as module
            original = module._details
            first = root._handles[0]
            calls = []
            def changed(handle):
                calls.append(handle)
                if handle is first:
                    raise CorpusBoundaryError('CORPUS_STORAGE_REPARSE_OR_TYPE_REFUSED')
                return original(handle)
            with patch.object(module, '_details', changed):
                self.assert_code('CORPUS_STORAGE_REPARSE_OR_TYPE_REFUSED', root.verify)
            self.assertEqual(calls, [first])
            root.verify()

    def test_missing_parent_never_auto_creates_ancestor_tree(self):
        target = self.target() / 'missing' / 'leaf'
        self.assert_code('CORPUS_STORAGE_OPEN_REFUSED', lambda: ProtectedCorpusRoot.create(str(target)))
        self.assertFalse(target.parent.exists())


if __name__ == '__main__':
    unittest.main()
