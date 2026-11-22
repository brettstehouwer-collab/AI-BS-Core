"""Isolated SQLite/filesystem evidence for native editor pre-write preservation."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native_studio import editor_file_store as store


class SimulatedCrash(BaseException):
    pass


class EditorFileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'isolated-master.db'
        with self.db() as connection:
            connection.execute('CREATE TABLE retained_fixture(value BLOB)')
            connection.execute('INSERT INTO retained_fixture VALUES (?)', (b'preserve existing data',))
        self.target = self.root / 'source.py'
        self.original = b'\xff\x00original\r\n'
        self.draft = b'edited\x00bytes\r\n\xff'
        self.target.write_bytes(self.original)

    def save(self, **kwargs):
        return store.durable_write_source(self.target, self.draft, database=self.database, **kwargs)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.database)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def rows(self):
        with self.db() as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute('SELECT * FROM native_editor_writes')]

    def assert_preserved(self, row):
        self.assertEqual(row['original_bytes'], self.original)
        self.assertEqual(row['draft_bytes'], self.draft)
        self.assertEqual(row['original_sha256'], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(row['draft_sha256'], hashlib.sha256(self.draft).hexdigest())

    def test_existing_write_preserves_exact_binary_bytes_and_records_written(self):
        result = self.save(expected_sha256=hashlib.sha256(self.original).hexdigest())
        self.assertTrue(result['written'])
        self.assertEqual(result['source_sha256'], hashlib.sha256(self.draft).hexdigest())
        self.assertEqual(self.target.read_bytes(), self.draft)
        row = store.read_source_checkpoint(result['operation_id'], database=self.database)
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'WRITTEN')
        self.assertEqual(row['file_written'], 1)
        self.assertEqual(Path(row['original_backup_path']).read_bytes(), self.original)
        with self.db() as connection:
            self.assertEqual(connection.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
            self.assertEqual(connection.execute('SELECT value FROM retained_fixture').fetchone()[0],
                             b'preserve existing data')

    def test_checkpoint_is_visible_to_another_reader_before_staging(self):
        original_stage = store._stage
        def stage(path, data, mode):
            rows = self.rows()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['phase'], 'CHECKPOINTED')
            self.assert_preserved(rows[0])
            self.assertEqual(self.target.read_bytes(), self.original)
            self.assertFalse(path.exists())
            original_stage(path, data, mode)
        with patch.object(store, '_stage', stage):
            self.save()

    def test_new_file_and_parent_created_only_after_checkpoint(self):
        target = self.root / 'new' / 'nested' / 'source.py'
        original_mkdir = Path.mkdir
        def mkdir(path, *args, **kwargs):
            if path == target.parent:
                self.assertFalse(target.exists())
                self.assertEqual(self.rows()[0]['phase'], 'CHECKPOINTED')
            return original_mkdir(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', mkdir):
            result = store.durable_write_source(target, self.draft, database=self.database,
                                               expected_sha256=None)
        row = store.read_source_checkpoint(result['operation_id'], database=self.database)
        self.assertIsNone(row['original_bytes'])
        self.assertIsNone(row['original_sha256'])
        self.assertEqual(target.read_bytes(), self.draft)
        self.assertEqual(target.stat().st_nlink, 1)

    def test_missing_database_never_created_and_no_target_parent_changes(self):
        target = self.root / 'uncreated' / 'source.py'
        missing = self.root / 'missing.db'
        with self.assertRaises(store.EditorFileStoreError) as caught:
            store.durable_write_source(target, self.draft, database=missing)
        self.assertIsNone(caught.exception.operation_id)
        self.assertFalse(missing.exists())
        self.assertFalse(target.parent.exists())

    def test_loaded_hash_conflict_retains_current_original_and_draft(self):
        with self.assertRaises(store.EditorWriteConflict) as caught:
            self.save(expected_sha256='0' * 64)
        self.assertFalse(caught.exception.written)
        row = store.read_source_checkpoint(caught.exception.operation_id, database=self.database)
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'CONFLICT')
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_postcheckpoint_external_change_is_not_overwritten(self):
        original_stage = store._stage
        external = b'other editor changed this file'
        def changed(path, data, mode):
            original_stage(path, data, mode)
            self.target.write_bytes(external)
        with patch.object(store, '_stage', changed):
            with self.assertRaises(store.EditorWriteConflict) as caught:
                self.save()
        row = store.read_source_checkpoint(caught.exception.operation_id, database=self.database)
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'CONFLICT')
        self.assertEqual(self.target.read_bytes(), external)
        self.assertTrue(Path(row['staged_path']).is_file())

    def test_failed_replace_keeps_both_checkpoint_payloads_and_staging(self):
        with patch.object(store, '_promote_existing', side_effect=PermissionError('synthetic denial')):
            with self.assertRaises(store.EditorFileStoreError) as caught:
                self.save()
        row = store.read_source_checkpoint(caught.exception.operation_id, database=self.database)
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'FAILED')
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(Path(row['staged_path']).read_bytes(), self.draft)

    @unittest.skipUnless(os.name == 'nt', 'Windows metadata contract')
    def test_windows_replace_preserves_original_ads_and_protected_dacl_and_backup(self):
        security = ctypes.WinDLL('advapi32.dll', use_last_error=True, winmode=0x00000800)
        get = security.GetFileSecurityW
        get.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID,
                        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        get.restype = wintypes.BOOL
        control = security.GetSecurityDescriptorControl
        control.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.WORD),
                            ctypes.POINTER(wintypes.DWORD)]
        control.restype = wintypes.BOOL
        dacl = security.GetSecurityDescriptorDacl
        dacl.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.BOOL),
                         ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.BOOL)]
        dacl.restype = wintypes.BOOL
        set_security = security.SetNamedSecurityInfoW
        set_security.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID]
        set_security.restype = wintypes.DWORD

        def descriptor(path):
            required = wintypes.DWORD()
            get(str(path), 4, None, 0, ctypes.byref(required))
            self.assertGreater(required.value, 0)
            self.assertLess(required.value, 1024 * 1024)
            buffer = ctypes.create_string_buffer(required.value)
            self.assertTrue(get(str(path), 4, buffer, required.value, ctypes.byref(required)))
            bits, revision = wintypes.WORD(), wintypes.DWORD()
            self.assertTrue(control(buffer, ctypes.byref(bits), ctypes.byref(revision)))
            present, defaulted, pointer = wintypes.BOOL(), wintypes.BOOL(), wintypes.LPVOID()
            self.assertTrue(dacl(buffer, ctypes.byref(present), ctypes.byref(pointer), ctypes.byref(defaulted)))
            self.assertTrue(present.value)
            self.assertTrue(pointer.value)
            size = ctypes.c_ushort.from_address(pointer.value + 2).value
            return buffer, bits.value, ctypes.string_at(pointer, size)

        current, _, _ = descriptor(self.target)
        # Preserve every existing access entry; protect only this disposable
        # fixture from inheritance so its descriptor differs from staging.
        present, defaulted, acl_pointer = wintypes.BOOL(), wintypes.BOOL(), wintypes.LPVOID()
        self.assertTrue(dacl(current, ctypes.byref(present), ctypes.byref(acl_pointer), ctypes.byref(defaulted)))
        self.assertEqual(set_security(str(self.target), 1, 4 | 0x80000000,
                                      None, None, acl_pointer, None), 0)
        before, before_bits, before_acl = descriptor(self.target)
        self.assertTrue(before_bits & 0x1000)
        stream_path = str(self.target) + ':aibs_editor_fixture'
        with open(stream_path, 'wb') as stream:
            stream.write(b'original named stream')
        birth = getattr(self.target.stat(), 'st_birthtime_ns', None)
        result = self.save()
        backup = Path(result['original_backup_path'])
        _, after_bits, after_acl = descriptor(self.target)
        _, backup_bits, backup_acl = descriptor(backup)
        self.assertEqual(after_acl, before_acl)
        self.assertEqual(backup_acl, before_acl)
        self.assertEqual(after_bits & 0x1000, before_bits & 0x1000)
        self.assertEqual(backup_bits & 0x1000, before_bits & 0x1000)
        with open(str(self.target) + ':aibs_editor_fixture', 'rb') as stream:
            self.assertEqual(stream.read(), b'original named stream')
        with open(str(backup) + ':aibs_editor_fixture', 'rb') as stream:
            self.assertEqual(stream.read(), b'original named stream')
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertEqual(self.target.read_bytes(), self.draft)
        if birth is not None:
            self.assertEqual(self.target.stat().st_birthtime_ns, birth)

    def test_partial_windows_replace_1177_retains_metadata_backup_without_replay(self):
        def partial(staged, target, backup):
            # Simulate the documented failure boundary using owned fixtures;
            # do not claim to have forced this Windows kernel failure in vivo.
            os.replace(target, backup)
            error = OSError('synthetic documented partial replacement failure')
            error.winerror = 1177
            raise error
        with patch.object(store, '_promote_existing', partial):
            with self.assertRaises(store.EditorFileStoreError) as caught:
                self.save()
        self.assertEqual(caught.exception.code, 'windows_replace_1177')
        self.assertFalse(caught.exception.written)
        row = store.read_source_checkpoint(caught.exception.operation_id, database=self.database)
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'FAILED')
        self.assertFalse(self.target.exists())
        self.assertEqual(Path(row['original_backup_path']).read_bytes(), self.original)
        self.assertEqual(Path(row['staged_path']).read_bytes(), self.draft)

    def test_windows_replace_1176_keeps_original_and_staging_without_fallback(self):
        error = OSError('synthetic replacement rename failure')
        error.winerror = 1176
        with patch.object(store, '_promote_existing', side_effect=error) as promote:
            with self.assertRaises(store.EditorFileStoreError) as caught:
                self.save()
        self.assertEqual(promote.call_count, 1)
        self.assertEqual(caught.exception.code, 'windows_replace_1176')
        row = store.read_source_checkpoint(caught.exception.operation_id, database=self.database)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(Path(row['original_backup_path']).exists())
        self.assertEqual(Path(row['staged_path']).read_bytes(), self.draft)

    def test_crash_after_staging_leaves_committed_checkpoint_without_replay(self):
        original_stage = store._stage
        def crashed(path, data, mode):
            original_stage(path, data, mode)
            raise SimulatedCrash()
        with patch.object(store, '_stage', crashed):
            with self.assertRaises(SimulatedCrash):
                self.save()
        row = self.rows()[0]
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'CHECKPOINTED')
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(store.read_source_checkpoint(row['operation_id'], database=self.database)['phase'],
                         'CHECKPOINTED')

    def test_crash_after_promotion_preserves_original_and_draft_without_false_phase(self):
        with patch.object(store, '_phase', side_effect=SimulatedCrash()):
            with self.assertRaises(SimulatedCrash):
                self.save()
        row = self.rows()[0]
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'CHECKPOINTED')
        self.assertEqual(self.target.read_bytes(), self.draft)

    def test_postpromotion_record_failure_reports_written_without_automatic_retry(self):
        original_phase = store._phase
        def failed_phase(connection, operation_id, phase, **kwargs):
            if phase == 'WRITTEN':
                raise sqlite3.OperationalError('synthetic final-record failure')
            return original_phase(connection, operation_id, phase, **kwargs)
        with patch.object(store, '_phase', failed_phase):
            with self.assertRaises(store.EditorFileStoreError) as caught:
                self.save()
        self.assertTrue(caught.exception.written)
        row = store.read_source_checkpoint(caught.exception.operation_id, database=self.database)
        self.assert_preserved(row)
        self.assertEqual(row['phase'], 'FAILED')
        self.assertEqual(row['file_written'], 1)
        self.assertEqual(self.target.read_bytes(), self.draft)

    def test_checkpoint_reader_detects_corruption_without_replaying_source(self):
        result = self.save()
        with self.db() as connection:
            connection.execute('UPDATE native_editor_writes SET draft_bytes=? WHERE operation_id=?',
                               (b'tampered', result['operation_id']))
        with self.assertRaises(store.EditorFileStoreError) as caught:
            store.read_source_checkpoint(result['operation_id'], database=self.database)
        self.assertEqual(caught.exception.code, 'checkpoint_hash_mismatch')
        self.assertEqual(self.target.read_bytes(), self.draft)

    def test_new_file_exclusive_promotion_never_clobbers_racing_creator(self):
        target = self.root / 'new.py'
        original_link = os.link
        external = b'another creator won'
        def racing_link(source, destination):
            with Path(destination).open('xb') as stream:
                stream.write(external)
            return original_link(source, destination)
        with patch.object(store.os, 'link', racing_link):
            with self.assertRaises(store.EditorWriteConflict) as caught:
                store.durable_write_source(target, self.draft, database=self.database,
                                           expected_sha256=None)
        self.assertEqual(target.read_bytes(), external)
        row = store.read_source_checkpoint(caught.exception.operation_id, database=self.database)
        self.assertEqual(row['phase'], 'CONFLICT')
        self.assertIsNone(row['original_bytes'])
        self.assertEqual(row['draft_bytes'], self.draft)

    def test_two_cooperating_writers_do_not_overwrite_each_others_change(self):
        # Exercise concurrent file CAS against an already established WAL
        # database, not a simultaneous first-time journal-mode transition.
        with self.db() as connection:
            self.assertEqual(connection.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
        barrier = threading.Barrier(2)
        original_open = store._open
        expected = hashlib.sha256(self.original).hexdigest()
        def open_db(database):
            connection = original_open(database)
            try:
                barrier.wait(timeout=5)
            except BaseException:
                connection.close()
                raise
            return connection
        def write(data):
            try:
                return store.durable_write_source(self.target, data, database=self.database,
                                                  expected_sha256=expected)['written']
            except store.EditorWriteConflict:
                return False
        with patch.object(store, '_open', open_db):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(write, data) for data in (b'first writer', b'second writer')]
                outcomes = [future.result(timeout=10) for future in futures]
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(sorted(row['phase'] for row in self.rows()), ['CONFLICT', 'WRITTEN'])
        self.assertIn(self.target.read_bytes(), (b'first writer', b'second writer'))

    def test_existing_incompatible_checkpoint_schema_is_preserved_and_rejected(self):
        with self.db() as connection:
            connection.execute('CREATE TABLE native_editor_writes(operation_id TEXT PRIMARY KEY)')
            connection.execute("INSERT INTO native_editor_writes VALUES ('retain-old-schema')")
        with self.assertRaises(store.EditorFileStoreError) as caught:
            self.save()
        self.assertEqual(caught.exception.code, 'checkpoint_schema_mismatch')
        self.assertEqual(self.target.read_bytes(), self.original)
        with self.db() as connection:
            self.assertEqual(connection.execute('SELECT * FROM native_editor_writes').fetchall(),
                             [('retain-old-schema',)])

    def test_links_are_rejected_without_changing_originals(self):
        hardlink = self.root / 'hardlink.py'
        os.link(self.target, hardlink)
        with self.assertRaises(store.EditorFileStoreError):
            self.save()
        hardlink.unlink()
        alias = self.root / 'alias.py'
        try:
            alias.symlink_to(self.target)
        except OSError:
            self.skipTest('Test account cannot create an isolated symbolic link')
        try:
            with self.assertRaises(store.EditorFileStoreError) as caught:
                store.durable_write_source(alias, self.draft, database=self.database)
            self.assertEqual(caught.exception.code, 'redirected_path')
        finally:
            alias.unlink()
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_invalid_or_oversized_payload_fails_before_checkpoint(self):
        for value in ('text is not bytes', b'x' * (store.MAX_SOURCE_BYTES + 1)):
            with self.assertRaises(store.EditorFileStoreError):
                store.durable_write_source(self.target, value, database=self.database)
        with self.db() as connection:
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name='native_editor_writes'").fetchone())
        self.assertEqual(self.target.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
