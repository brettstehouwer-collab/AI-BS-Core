"""New synthetic files only. Native handles, not project/private corpus data."""
import hashlib
import os
from pathlib import Path
import threading
import unittest
import uuid
from unittest.mock import patch

from backend.security.theatrical_corpus_boundary import CorpusBoundaryError
from backend.security import theatrical_storage_blobs as blobs

if os.name == 'nt':
    import pywintypes
    import win32con
    import win32file
    import win32security

BASE = Path('C:/AI-BS/backups/theatrical_blobs_20261026T105600Z/native')


@unittest.skipUnless(os.name == 'nt', 'Windows native file handles required')
class BlobStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BASE.mkdir(exist_ok=True)

    def target(self):
        parent = BASE / ('case_' + uuid.uuid4().hex)
        parent.mkdir()
        return parent / 'corpus'

    def store(self, target=None):
        store = blobs.ImmutableCorpusBlobs.create(str(target or self.target()))
        self.addCleanup(store.close)
        return store

    def assert_code(self, code, call):
        with self.assertRaises(CorpusBoundaryError) as caught:
            call()
        self.assertEqual(str(caught.exception), code)

    def test_original_unicode_nul_crlf_empty_and_exact_maximum_roundtrip(self):
        store = self.store()
        originals = [b'', 'INT. STAGE\r\nCaf\u00e9 \U0001f3ad\x00\n'.encode(), b'x' * (2 * 1024 * 1024)]
        for data in originals:
            digest = store.put(data)
            self.assertEqual(digest, hashlib.sha256(data).hexdigest())
            self.assertEqual(store.read(digest), data)
            self.assertEqual(store.put(data), digest)
        self.assertEqual(len(store._entries), len(originals))
        store.verify()

    def test_actual_file_owner_and_protected_exact_dacl(self):
        store = self.store()
        digest = store.put(b'fixture')
        handle = store._entries[digest]['handle']
        sd = win32security.GetSecurityInfo(handle, win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
        self.assertEqual(win32security.ConvertSidToStringSid(sd.GetSecurityDescriptorOwner()), store._root.broker_sid)
        self.assertTrue(sd.GetSecurityDescriptorControl()[0] & 0x1000)
        acl = sd.GetSecurityDescriptorDacl()
        self.assertEqual(acl.GetAceCount(), 3)
        self.assertEqual({win32security.ConvertSidToStringSid(acl.GetAce(i)[2]) for i in range(3)},
                         {store._root.broker_sid, 'S-1-5-18', 'S-1-5-32-544'})
        self.assertTrue(all(acl.GetAce(i)[:2] == ((0, 0), 0x1F01FF) for i in range(3)))

    def test_native_data_sharing_rename_refusal_and_actual_hardlink_detection(self):
        target = self.target()
        store = self.store(target)
        digest = store.put(b'held original')
        path = target / (digest + '.blob')
        for access in (win32con.GENERIC_READ, win32con.GENERIC_WRITE):
            with self.subTest(access=access), self.assertRaises(pywintypes.error) as caught:
                handle = win32file.CreateFile(str(path), access, 7, None, 3, 0, None)
                handle.Close()
            self.assertEqual(caught.exception.winerror, 32)
        with self.assertRaises(OSError) as caught:
            path.rename(target / 'unexpected_move')
        self.assertEqual(caught.exception.winerror, 32)
        self.assertEqual(store.read(digest), b'held original')
        # Windows allows metadata-only hardlink creation by this trusted user
        # even with zero data sharing. Validate and refuse it; never assert
        # the sharing mode is a hardlink prevention or independent-user gate.
        os.link(path, target / 'retained_hardlink')
        self.assertEqual(path.stat().st_nlink, 2)
        self.assert_code('CORPUS_BLOB_METADATA_CHANGED', lambda: store.read(digest))
        self.assert_code('CORPUS_BLOB_TAINTED', store.verify)
        store.close()
        self.assertEqual(path.read_bytes(), b'held original')
        self.assertEqual(path.stat().st_nlink, 2)

    def test_existing_file_is_preserved_not_adopted_or_overwritten(self):
        target = self.target()
        store = self.store(target)
        digest = hashlib.sha256(b'proposed').hexdigest()
        path = target / (digest + '.blob')
        path.write_bytes(b'PREEXISTING\r\n')
        self.assert_code('CORPUS_BLOB_CREATE_REFUSED', lambda: store.put(b'proposed'))
        self.assertEqual(path.read_bytes(), b'PREEXISTING\r\n')
        self.assert_code('CORPUS_BLOB_TAINTED', store.verify)

    def test_existing_hardlink_is_not_followed_and_unknown_file_never_opened(self):
        target = self.target()
        external = target.parent / 'synthetic_external.txt'
        external.write_bytes(b'KEEP')
        store = self.store(target)
        digest = hashlib.sha256(b'proposed').hexdigest()
        os.link(external, target / (digest + '.blob'))
        self.assert_code('UNKNOWN_CORPUS_BLOB', lambda: store.read(digest))
        self.assert_code('CORPUS_BLOB_CREATE_REFUSED', lambda: store.put(b'proposed'))
        self.assertEqual(external.read_bytes(), b'KEEP')

    def test_invalid_inputs_are_rejected_before_native_creation(self):
        store = self.store()
        with patch.object(blobs, '_create_blob', side_effect=AssertionError('must not open')):
            for value in ('text', bytearray(b'x'), memoryview(b'x'), None, b'x' * (2*1024*1024 + 1)):
                self.assert_code('INVALID_CORPUS_BLOB_BYTES', lambda: store.put(value))
            for digest in ('', 'A'*64, '../secret', '0'*64 + ':stream', None, 1):
                self.assert_code('INVALID_CORPUS_BLOB_ID', lambda: store.read(digest))
        store.verify()

    def test_byte_and_count_caps_precede_file_creation(self):
        store = self.store()
        for index in range(4):
            store.put(bytes([index]) * (2*1024*1024))
        with patch.object(blobs, '_create_blob', side_effect=AssertionError('quota must precede I/O')):
            self.assert_code('CORPUS_BLOB_QUOTA', lambda: store.put(b'additional'))
        other = self.store()
        for index in range(32):
            other.put(bytes([index]))
        with patch.object(blobs, '_create_blob', side_effect=AssertionError('quota must precede I/O')):
            self.assert_code('CORPUS_BLOB_QUOTA', lambda: other.put(b'33rd'))
        other.verify()

    def test_concurrent_duplicate_put_serializes_and_retains_one_file(self):
        store = self.store()
        barrier = threading.Barrier(3)
        results, errors = [], []
        def put():
            try:
                barrier.wait(timeout=5)
                results.append(store.put(b'same original'))
            except Exception as exc:
                errors.append(type(exc).__name__)
        threads = [threading.Thread(target=put) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(len(store._entries), 1)

    def test_data_mutation_on_held_handle_is_detected_and_store_tainted(self):
        store = self.store()
        digest = store.put(b'original')
        handle = store._entries[digest]['handle']
        win32file.SetFilePointer(handle, 0, 0)
        win32file.WriteFile(handle, b'changed!')
        self.assert_code('CORPUS_BLOB_HASH_CHANGED', lambda: store.read(digest))
        self.assert_code('CORPUS_BLOB_TAINTED', lambda: store.put(b'further'))

    def test_actual_file_acl_change_is_refused_without_repair(self):
        target = self.target()
        store = self.store(target)
        digest = store.put(b'fixture')
        path = str(target / (digest + '.blob'))
        original = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
        weak = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor('D:P(A;;FA;;;WD)', 1)
        try:
            win32security.SetFileSecurity(path,
                win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION, weak)
            self.assert_code('CORPUS_BLOB_ACL_REFUSED', lambda: store.read(digest))
            actual = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
            self.assertEqual(win32security.ConvertSidToStringSid(actual.GetSecurityDescriptorDacl().GetAce(0)[2]), 'S-1-1-0')
        finally:
            win32security.SetFileSecurity(path,
                win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION, original)

    def test_file_identity_link_count_reparse_and_size_are_measured(self):
        for index, value in ((0, 0x400), (0, 0x10), (7, 2), (6, 1), (4, 0)):
            store = self.store()
            digest = store.put(b'fixture')
            real = win32file.GetFileInformationByHandle
            target = store._entries[digest]['handle']
            def changed(handle):
                info = list(real(handle))
                if handle is target:
                    info[index] = value
                return tuple(info)
            with patch.object(win32file, 'GetFileInformationByHandle', changed):
                self.assert_code('CORPUS_BLOB_METADATA_CHANGED', lambda: store.read(digest))

    def test_failure_after_creation_retains_partial_and_blocks_further_io(self):
        target = self.target()
        store = self.store(target)
        with patch.object(blobs, '_write_bytes', side_effect=OSError('private native details')):
            self.assert_code('CORPUS_BLOB_IO_UNAVAILABLE', lambda: store.put(b'original'))
        self.assert_code('CORPUS_BLOB_TAINTED', store.verify)
        store.close()
        path = target / (hashlib.sha256(b'original').hexdigest() + '.blob')
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), b'')
        self.assert_code('CORPUS_STORAGE_CREATE_REFUSED', lambda: blobs.ImmutableCorpusBlobs.create(str(target)))

    def test_control_interrupts_propagate_and_taint_lease(self):
        for operation in ('put', 'read', 'verify'):
            with self.subTest(operation=operation):
                store = self.store()
                digest = store.put(b'original')
                point = '_write_bytes' if operation == 'put' else '_read_bytes'
                with patch.object(blobs, point, side_effect=KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        if operation == 'put':
                            store.put(b'new partial')
                        elif operation == 'read':
                            store.read(digest)
                        else:
                            store.verify()
                self.assert_code('CORPUS_BLOB_TAINTED', lambda: store.put(b'next'))

    def test_flush_failure_and_short_read_never_claim_success(self):
        store = self.store()
        with patch.object(win32file, 'FlushFileBuffers', side_effect=OSError('private')):
            self.assert_code('CORPUS_BLOB_IO_UNAVAILABLE', lambda: store.put(b'fixture'))
        other = self.store()
        digest = other.put(b'original')
        with patch.object(blobs, '_read_bytes', return_value=b''):
            self.assert_code('CORPUS_BLOB_HASH_CHANGED', lambda: other.read(digest))

    def test_all_blob_io_is_handle_relative_and_ignores_diagnostic_path(self):
        target = self.target()
        store = self.store(target)
        store._root._path = 'Z:\\not_an_admitted_path\\corpus'
        with patch('builtins.open', side_effect=AssertionError('no pathname I/O')):
            digest = store.put(b'held root')
            self.assertEqual(store.read(digest), b'held root')
        store.close()
        self.assertEqual((target / (digest + '.blob')).read_bytes(), b'held root')

    def test_close_serializes_with_active_read_and_retains_bytes(self):
        target = self.target()
        store = self.store(target)
        digest = store.put(b'fixture')
        entered, release, closing, done = (threading.Event() for _ in range(4))
        results, errors = [], []
        real = blobs._read_bytes
        def wait_read(*args):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('test deadline')
            return real(*args)
        def read():
            try:
                results.append(store.read(digest))
            except Exception as exc:
                errors.append(type(exc).__name__)
        def close():
            closing.set()
            store.close()
            done.set()
        with patch.object(blobs, '_read_bytes', wait_read):
            reader = threading.Thread(target=read)
            reader.start()
            self.assertTrue(entered.wait(5))
            closer = threading.Thread(target=close)
            closer.start()
            try:
                self.assertTrue(closing.wait(5))
                self.assertFalse(done.is_set())
            finally:
                release.set()
            reader.join(10)
            closer.join(10)
            self.assertFalse(reader.is_alive())
            self.assertFalse(closer.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results, [b'fixture'])
        self.assertTrue(done.is_set())
        store.close()
        self.assert_code('CORPUS_BLOB_CLOSED', lambda: store.read(digest))
        self.assertEqual((target / (digest + '.blob')).read_bytes(), b'fixture')


if __name__ == '__main__':
    unittest.main()
