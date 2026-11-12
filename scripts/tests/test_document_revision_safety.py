"""Actual document handler contracts, isolated synthetic files only.

The production backend is AST-extracted; importing it would start unrelated systems.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import multiprocessing
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from scripts.tests import test_creation_document_save as document_fixture


def _process_save(path, content, revision, ready, start, results):
    fixture = document_fixture.DocumentSaveTests()
    fixture.setUp()
    try:
        # Each process builds its own handler namespace, with the same synthetic drive.
        import sys
        sys.modules['routers.shared_drive_router'].DRIVE_ROOT = Path(path).parent
        ready.put(True)
        start.wait(15)
        try:
            request = fixture.scope['DocumentSaveRequest'](
                path=path, content=content, expected_revision=revision)
            response = asyncio.run(fixture.scope['save_document_file_alias'](request))
            results.put(('saved', response.get('revision')))
        except HTTPException as error:
            results.put(('refused', error.status_code))
    finally:
        fixture.doCleanups()


class DocumentRevisionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = document_fixture.DocumentSaveTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.drive, self.scope = self.fixture.drive, self.fixture.scope
        self.target = self.drive / 'synthetic.txt'

    def read(self, path=None):
        return asyncio.run(self.scope['read_document_file_alias'](path=str(path or self.target)))

    def save(self, content, path=None, **options):
        request = self.scope['DocumentSaveRequest'](path=str(path or self.target), content=content, **options)
        return asyncio.run(self.scope['save_document_file_alias'](request))

    def assert_status(self, status, operation):
        with self.assertRaises(HTTPException) as caught:
            operation()
        self.assertEqual(caught.exception.status_code, status)

    def seed(self, raw=b'BASE\r\n'):
        self.target.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_read_returns_exact_byte_revision_with_normalized_text(self):
        raw = b'\xef\xbb\xbfA\rB\nC\r\n'
        revision = self.seed(raw)
        snapshot = self.read()
        self.assertEqual(snapshot.get('revision'), revision)
        self.assertEqual(snapshot['content'], 'A\nB\nC\n')
        self.assertEqual(self.target.read_bytes(), raw)

    def test_stale_save_preserves_newer_bytes_and_mtime(self):
        revision = self.seed()
        saved = self.save('NEWER\n', expected_revision=revision)
        before = self.target.read_bytes(), self.target.stat().st_mtime_ns
        self.assert_status(409, lambda: self.save('OLDER EDIT\n', expected_revision=revision))
        self.assertEqual((self.target.read_bytes(), self.target.stat().st_mtime_ns), before)
        self.assertEqual(saved.get('revision'), hashlib.sha256(before[0]).hexdigest())

    def test_existing_file_requires_revision_even_for_same_text(self):
        self.seed()
        self.assert_status(428, lambda: self.save('BASE\n'))

    def test_new_file_requires_create_only_and_stale_update_cannot_recreate_missing_file(self):
        self.assert_status(428, lambda: self.save('NEW'))
        self.assertFalse(self.target.exists())
        self.assert_status(409, lambda: self.save('NEW', expected_revision='0' * 64))
        self.assertFalse(self.target.exists())
        created = self.save('CREATED\n', create_only=True)
        self.assertEqual(created.get('revision'), hashlib.sha256(self.target.read_bytes()).hexdigest())

    def test_malformed_revision_refuses_before_mutation(self):
        original = self.seed()
        for invalid in ('bad', '', 'g' * 64, '0' * 65):
            with self.subTest(revision=invalid):
                self.assert_status(400, lambda: self.save('BAD', expected_revision=invalid))
        self.assertEqual(hashlib.sha256(self.target.read_bytes()).hexdigest(), original)

    def test_revision_model_rejects_non_strings_without_coercion(self):
        for invalid in (0, False, b'0' * 64, ['0' * 64]):
            with self.subTest(value_type=type(invalid).__name__):
                with self.assertRaises(ValidationError):
                    self.scope['DocumentSaveRequest'](path=str(self.target), content='BAD', expected_revision=invalid)

    def test_revision_admission_precedes_same_text_noop_and_lost_ack_retry(self):
        revision = self.seed()
        self.save('ACK LOST\n', expected_revision=revision)
        before = self.target.read_bytes(), self.target.stat().st_mtime_ns
        # A retry must not claim success based only on equal text after another write.
        self.assert_status(409, lambda: self.save('ACK LOST\n', expected_revision=revision))
        self.assertEqual((self.target.read_bytes(), self.target.stat().st_mtime_ns), before)

    def test_matching_same_text_keeps_bytes_mtime_and_revision(self):
        raw = b'\xef\xbb\xbfA\rB\n'
        revision = self.seed(raw)
        mtime = self.target.stat().st_mtime_ns
        saved = self.save('A\nB\n', expected_revision=revision)
        self.assertTrue(saved.get('unchanged'))
        self.assertEqual(saved.get('revision'), revision)
        self.assertEqual((self.target.read_bytes(), self.target.stat().st_mtime_ns), (raw, mtime))

    def test_create_collision_and_retention_precede_revision_admission(self):
        revision = self.seed()
        self.assert_status(409, lambda: self.save('BASE\n', create_only=True, expected_revision='invalid'))
        self.assertEqual(hashlib.sha256(self.target.read_bytes()).hexdigest(), revision)
        protected = self.drive / 'Documents/Drive_Intake/Fixture/Originals/original.txt'
        protected.parent.mkdir(parents=True)
        protected.write_bytes(b'ORIGINAL\r\n')
        self.assert_status(403, lambda: self.save('ORIGINAL\n', path=protected, expected_revision='invalid'))
        self.assertEqual(protected.read_bytes(), b'ORIGINAL\r\n')

    def test_failed_promotion_preserves_original_and_never_returns_success(self):
        revision = self.seed()
        before = self.target.read_bytes(), self.target.stat().st_mtime_ns
        with patch.object(self.scope['os'], 'replace', side_effect=PermissionError('synthetic promotion denied')):
            with self.assertRaises(PermissionError):
                self.save('UNSAVED', expected_revision=revision)
        self.assertEqual((self.target.read_bytes(), self.target.stat().st_mtime_ns), before)
        retained = list(self.drive.glob('.document-*.tmp'))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_bytes(), b'UNSAVED')

    def test_parallel_threads_with_same_revision_have_one_winner(self):
        revision = self.seed()
        start = threading.Barrier(2)

        def attempt(content):
            start.wait(5)
            try:
                return 'saved', self.save(content, expected_revision=revision)
            except HTTPException as error:
                return 'refused', error.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, text) for text in ('THREAD A', 'THREAD B')]
            outcomes = [future.result(10) for future in futures]
        self.assertEqual(sorted(item[0] for item in outcomes), ['refused', 'saved'])
        self.assertIn(('refused', 409), outcomes)

    def test_read_waits_for_admitted_save_and_pairs_text_with_revision(self):
        revision = self.seed()
        promotion_entered, allow_promotion, read_finished = threading.Event(), threading.Event(), threading.Event()
        real_replace = os.replace

        def delayed_replace(source, target):
            promotion_entered.set()
            if not allow_promotion.wait(5):
                raise TimeoutError('synthetic promotion barrier')
            return real_replace(source, target)

        def reader():
            snapshot = self.read()
            read_finished.set()
            return snapshot

        with ThreadPoolExecutor(max_workers=2) as pool:
            with patch.object(self.scope['os'], 'replace', side_effect=delayed_replace):
                saving = pool.submit(self.save, 'NEW', expected_revision=revision)
                self.assertTrue(promotion_entered.wait(5))
                reading = pool.submit(reader)
                try:
                    self.assertFalse(read_finished.wait(.1), 'read escaped save admission lock')
                finally:
                    allow_promotion.set()
                saved, snapshot = saving.result(10), reading.result(10)
        self.assertEqual(snapshot['content'], 'NEW')
        self.assertEqual(snapshot.get('revision'), saved.get('revision'))

    @unittest.skipUnless(os.name == 'nt', 'Windows named-mutex worker acceptance')
    def test_parallel_processes_with_same_revision_have_one_winner(self):
        revision = self.seed()
        context = multiprocessing.get_context('spawn')
        ready, results, start = context.Queue(), context.Queue(), context.Event()
        processes = [context.Process(target=_process_save,
                      args=(str(self.target), text, revision, ready, start, results))
                     for text in ('PROCESS A', 'PROCESS B')]
        for process in processes:
            process.start()
        try:
            for _ in processes:
                self.assertTrue(ready.get(timeout=15))
            start.set()
            outcomes = [results.get(timeout=15) for _ in processes]
            self.assertEqual(sorted(item[0] for item in outcomes), ['refused', 'saved'])
            self.assertIn(('refused', 409), outcomes)
        finally:
            start.set()
            for process in processes:
                process.join(15)
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            ready.close()
            results.close()


if __name__ == '__main__':
    unittest.main()
