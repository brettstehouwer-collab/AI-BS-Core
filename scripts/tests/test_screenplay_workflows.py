"""Durable workflow contracts using synthetic temporary projects only."""
import hashlib
import importlib
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'Synthetic Project'
        self.project.mkdir()
        self.script = self.project / 'screenplay.fountain'
        self.original = 'Title: Synthetic\r\n\r\nINT. LAB - DAY\r\nCafé.\r\n'.encode()
        self.script.write_bytes(self.original)
        self.lock = threading.RLock()

    def store(self, directory=None):
        module_path = ROOT / 'backend/core/screenplay_workflows.py'
        self.assertTrue(module_path.exists(), 'Durable project workflow implementation is missing')
        self.module = importlib.import_module('core.screenplay_workflows')
        directory = directory or self.project

        def snapshot():
            path = directory / 'screenplay.fountain'
            if path.exists():
                raw = path.read_bytes()
                return dict(content=raw.decode(), revision=hashlib.sha256(raw).hexdigest(), screenplay_exists=True)
            fallback = directory / 'adaptation_output.fountain'
            if fallback.exists():
                raw = fallback.read_bytes()
                return dict(content=raw.decode(), revision='adaptation:' + hashlib.sha256(raw).hexdigest(), screenplay_exists=False)
            return dict(content='', revision='missing', screenplay_exists=False)

        def write(raw):
            target = directory / 'screenplay.fountain'
            temporary = directory / 'synthetic-staging.tmp'
            with temporary.open('wb') as stream:
                stream.write(raw)
                stream.flush()
                __import__('os').fsync(stream.fileno())
            __import__('os').replace(temporary, target)

        return self.module.WorkflowStore(directory, snapshot, write, self.lock)

    def revision(self):
        return hashlib.sha256(self.script.read_bytes()).hexdigest()

    def create(self, store, name='Alternative'):
        return store.create_branch(name, self.revision(), store.status()['workflow_revision'])

    def assert_error(self, status, function, *arguments):
        with self.assertRaises(self.module.WorkflowError) as caught:
            function(*arguments)
        self.assertEqual(caught.exception.status, status)

    def test_read_is_non_mutating_and_project_scoped(self):
        store = self.store()
        before = self.script.stat().st_mtime_ns
        state = store.status()
        self.assertEqual(state['branches'], ['main'])
        self.assertEqual(state['workflow_revision'], 0)
        self.assertFalse(state['initialized'])
        self.assertEqual(list(self.project.iterdir()), [self.script])
        self.assertEqual(self.script.stat().st_mtime_ns, before)

    def test_corrupt_pending_operation_is_refused_before_any_recovery_write(self):
        for column, value in [('before_content', b'CORRUPT'), ('source_branch', 'missing'),
                              ('target_branch', 'missing'), ('kind', 'UNKNOWN')]:
            with self.subTest(column=column):
                directory = self.project / column
                directory.mkdir()
                script = directory / 'screenplay.fountain'
                script.write_bytes(self.original)
                store = self.store(directory)
                revision = hashlib.sha256(self.original).hexdigest()
                with patch.object(store, '_write', side_effect=OSError('synthetic interruption')):
                    with self.assertRaises(OSError):
                        store.write(b'TARGET\n', revision, 0)
                pending = store.status()['pending_operation']['id']
                with closing(sqlite3.connect(store.path)) as connection:
                    connection.execute(f'UPDATE operations SET {column}=? WHERE id=?', (value, pending))
                    connection.commit()
                before = store.path.read_bytes()
                self.assert_error(409, store.recover, pending, 'complete')
                self.assertEqual(script.read_bytes(), self.original)
                self.assertEqual(store.path.read_bytes(), before)

    def test_create_and_restart_preserve_exact_original_and_other_project(self):
        store = self.store()
        other = self.project.parent / 'Other'
        other.mkdir()
        (other / 'screenplay.fountain').write_bytes(b'OTHER\r\n')
        stamp = self.script.stat().st_mtime_ns
        self.create(store)
        state = self.store().status()
        self.assertEqual(state['branches'], ['main', 'Alternative'])
        self.assertEqual(state['active_branch'], 'main')
        self.assertEqual(self.script.read_bytes(), self.original)
        self.assertEqual(self.script.stat().st_mtime_ns, stamp)
        self.assertFalse(self.store(other).status()['initialized'])

    def test_write_switch_and_return_restore_each_branch_byte_for_byte(self):
        store = self.store()
        self.create(store)
        store.write(b'MAIN EDIT\n', self.revision(), 1)
        store.switch_branch('Alternative', self.revision(), 2)
        self.assertEqual(self.script.read_bytes(), self.original)
        store.write(b'ALT\r\n\nTAIL\r', self.revision(), 3)
        store.switch_branch('main', self.revision(), 4)
        self.assertEqual(self.script.read_bytes(), b'MAIN EDIT\n')
        self.store().switch_branch('Alternative', self.revision(), 5)
        self.assertEqual(self.script.read_bytes(), b'ALT\r\n\nTAIL\r')

    def test_stale_revision_and_equal_text_branch_aba_are_rejected(self):
        store = self.store()
        self.create(store)
        revision = self.revision()
        store.switch_branch('Alternative', revision, 1)
        self.assert_error(409, store.write, b'STALE', revision, 1)
        self.assert_error(409, store.write, b'STALE', 'wrong-revision', 2)
        self.assert_error(428, store.write, b'STALE', revision, None)
        self.assertEqual(self.script.read_bytes(), self.original)

    def test_invalid_and_duplicate_names_do_not_mutate_store(self):
        store = self.store()
        for name in ('../elsewhere', 'bad/name', ' trailing ', '', 'x' * 81):
            self.assert_error(400, store.create_branch, name, self.revision(), 0)
        self.assertFalse(store.status()['initialized'])
        self.create(store, 'Älternative')
        self.assert_error(409, store.create_branch, 'älternative', self.revision(), 1)
        self.assertEqual(store.status()['workflow_revision'], 1)

    def test_read_does_not_create_database_and_unknown_database_is_preserved(self):
        store = self.store()
        path = self.project / '.writing-workflows.sqlite3'
        path.write_bytes(b'not a sqlite database')
        before = path.read_bytes()
        self.assert_error(409, store.status)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.script.read_bytes(), self.original)

    def test_foreign_sqlite_database_is_not_adopted(self):
        store = self.store()
        path = self.project / '.writing-workflows.sqlite3'
        with closing(sqlite3.connect(path)) as connection:
            connection.execute('CREATE TABLE unrelated(value TEXT)')
            connection.commit()
        before = path.read_bytes()
        self.assert_error(409, self.create, store)
        self.assertEqual(path.read_bytes(), before)

    def test_prepare_failure_preserves_original_and_can_abort_after_restart(self):
        store = self.store()
        self.create(store)
        with patch.object(store, '_write', side_effect=PermissionError('synthetic refusal')):
            with self.assertRaises(PermissionError):
                store.write(b'REPLACEMENT', self.revision(), 1)
        reopened = self.store()
        pending = reopened.status()['pending_operation']
        self.assertIsNotNone(pending)
        self.assertEqual(self.script.read_bytes(), self.original)
        self.assert_error(409, reopened.write, b'OTHER', self.revision(), 1)
        reopened.recover(pending['id'], 'abort')
        self.assertEqual(reopened.status()['workflow_revision'], 2)
        self.assertIsNone(reopened.status()['pending_operation'])
        self.assertEqual(self.script.read_bytes(), self.original)

    def test_interruption_after_replace_recovers_without_rewriting_or_duplicate_effect(self):
        store = self.store()
        self.create(store)
        with patch.object(store, '_finish', side_effect=OSError('synthetic interrupted commit')):
            with self.assertRaises(OSError):
                store.write(b'COMMITTED BYTES\r\n', self.revision(), 1)
        stamp = self.script.stat().st_mtime_ns
        reopened = self.store()
        pending = reopened.status()['pending_operation']
        self.assert_error(409, reopened.recover, pending['id'], 'abort')
        result = reopened.recover(pending['id'], 'complete')
        self.assertEqual(result['workflow_revision'], 2)
        self.assertEqual(self.script.stat().st_mtime_ns, stamp)
        self.assert_error(409, reopened.recover, pending['id'], 'complete')

    def test_recovery_refuses_unrelated_external_edits_and_preserves_journal(self):
        store = self.store()
        self.create(store)
        with patch.object(store, '_write', side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(OSError):
                store.write(b'TARGET', self.revision(), 1)
        pending = store.status()['pending_operation']
        self.script.write_bytes(b'EXTERNAL EDIT\r\n')
        for action in ('complete', 'abort'):
            self.assert_error(409, store.recover, pending['id'], action)
        self.assertEqual(self.script.read_bytes(), b'EXTERNAL EDIT\r\n')
        self.assertEqual(store.status()['pending_operation'], pending)

    def test_pending_switch_recovers_before_replace_and_preserves_both_branches(self):
        store = self.store()
        self.create(store)
        store.write(b'MAIN', self.revision(), 1)
        with patch.object(store, '_write', side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(OSError):
                store.switch_branch('Alternative', self.revision(), 2)
        pending = store.status()['pending_operation']
        reopened = self.store()
        reopened.recover(pending['id'], 'complete')
        self.assertEqual(self.script.read_bytes(), self.original)
        reopened.switch_branch('main', self.revision(), 3)
        self.assertEqual(self.script.read_bytes(), b'MAIN')

    def test_sprint_restart_end_is_persistent_and_metrics_are_actual_word_counts(self):
        store = self.store()
        initial_words = len(self.original.decode().split())
        started = store.start_sprint('Draft scene', 10, self.revision(), 0)
        sprint = started['active_sprint']
        reopened = self.store()
        self.assertEqual(reopened.status()['active_sprint'], sprint)
        reopened.write(b'one two three', self.revision(), 1)
        result = reopened.end_sprint(sprint['id'], self.revision(), 2)
        ended = result['sprints'][0]
        self.assertIsNone(result['active_sprint'])
        self.assertEqual(ended['word_delta'], 3 - initial_words)
        self.assertEqual(ended['target_pages'], 10)
        self.assertNotIn('pages_written', ended)
        self.assertGreaterEqual(ended['elapsed_seconds'], 0)
        self.assertEqual(self.store().status()['sprints'][0], ended)
        self.assert_error(409, reopened.end_sprint, sprint['id'], self.revision(), 3)

    def test_one_active_sprint_blocks_branch_switch_and_duplicate_start(self):
        store = self.store()
        self.create(store)
        store.start_sprint('Draft', 5, self.revision(), 1)
        self.assert_error(409, store.switch_branch, 'Alternative', self.revision(), 2)
        self.assert_error(409, store.start_sprint, 'Other', 5, self.revision(), 2)
        self.assertEqual(self.script.read_bytes(), self.original)

    def test_sprint_validation_does_not_initialize_store(self):
        store = self.store()
        for name, target in [('', 10), ('Draft', 0), ('Draft', 10001), ('Draft', True)]:
            self.assert_error(400, store.start_sprint, name, target, self.revision(), 0)
        self.assertFalse(store.status()['initialized'])

    def test_legacy_fallback_snapshot_is_preserved_without_creating_canonical_on_create(self):
        store = self.store()
        self.script.rename(self.project / 'adaptation_output.fountain')
        revision = 'adaptation:' + hashlib.sha256(self.original).hexdigest()
        store.create_branch('Alternative', revision, 0)
        self.assertFalse(self.script.exists())
        store.switch_branch('Alternative', revision, 1)
        self.assertEqual(self.script.read_bytes(), self.original)
        self.assertEqual((self.project / 'adaptation_output.fountain').read_bytes(), self.original)

    def test_resource_bound_refuses_new_snapshot_without_changing_source(self):
        store = self.store()
        self.create(store)
        with patch.object(self.module, 'MAX_STORED_BYTES', len(self.original)):
            self.assert_error(409, store.write, b'OVER BUDGET', self.revision(), 1)
        self.assertEqual(self.script.read_bytes(), self.original)
        self.assertIsNone(store.status()['pending_operation'])

    def test_two_stale_clients_cannot_both_create_same_epoch(self):
        store = self.store()
        self.create(store)
        revision = self.revision()
        results = []

        def create(name):
            try:
                self.store().create_branch(name, revision, 1)
                results.append('success')
            except self.module.WorkflowError as error:
                results.append(error.status)

        threads = [threading.Thread(target=create, args=(name,)) for name in ('A', 'B')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(results, ['success', 409])
        self.assertEqual(self.script.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
