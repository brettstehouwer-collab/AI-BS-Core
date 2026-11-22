"""Recoverable reorder projections, disposable projects and actual WorkflowStore."""
from contextlib import closing
import hashlib
import importlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('core.screenplay_reorder_bundle')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'Synthetic Project'
        self.project.mkdir()
        self.lock = threading.RLock()
        self.before = {'screenplay.fountain': b'Title: Fixture\r\nINT. LAB - DAY\r\nOriginal.\r\n',
                       'Synthetic Project.fdx': b'<FinalDraft>Original</FinalDraft>\r\n',
                       'project.json': b'{"title":"Fixture","word_count":6}\r\n'}
        self.after = {'screenplay.fountain': b'Title: Fixture\r\nEXT. LAB - NIGHT\r\nNew order.\r\n',
                      'Synthetic Project.fdx': b'<FinalDraft>New order</FinalDraft>\r\n',
                      'project.json': b'{"title":"Fixture","word_count":7}\r\n'}
        for name, raw in self.before.items():
            (self.project / name).write_bytes(raw)
        self.store = self.new_store()

    def new_store(self):
        return self.module.ReorderBundle(self.project, self.lock)

    def values(self):
        return {name: (self.project / name).read_bytes() if (self.project / name).exists() else None
                for name in self.before}

    def interrupted(self, fail_at):
        promote = self.store._promote
        calls = []
        def interrupt(name, expected, target, operation):
            calls.append(name)
            if len(calls) == fail_at:
                raise OSError('synthetic interrupted promotion')
            return promote(name, expected, target, operation)
        with patch.object(self.store, '_promote', side_effect=interrupt):
            with self.assertRaises(OSError):
                self.store.apply(self.after, self.before)
        return self.store.status()['pending_operation']['id'], calls

    def test_status_has_no_write_side_effect(self):
        files = {p.name: p.read_bytes() for p in self.project.iterdir()}
        self.assertIsNone(self.store.status()['pending_operation'])
        self.assertEqual(files, {p.name: p.read_bytes() for p in self.project.iterdir()})

    def test_success_publishes_derivatives_before_canonical_and_retains_journal(self):
        original = self.store._promote
        order = []
        def observe(name, expected, target, operation):
            order.append(name)
            return original(name, expected, target, operation)
        with patch.object(self.store, '_promote', side_effect=observe):
            result = self.store.apply(self.after, self.before)
        self.assertEqual(order[-1], 'screenplay.fountain')
        self.assertEqual(self.values(), self.after)
        self.assertIsNone(self.new_store().status()['pending_operation'])
        with closing(sqlite3.connect(self.store.path)) as connection:
            self.assertEqual(connection.execute('SELECT status FROM operations WHERE id=?', (result['id'],)).fetchone()[0], 'COMPLETED')
            self.assertEqual(connection.execute('SELECT count(*) FROM files').fetchone()[0], 3)

    def test_stale_bundle_refuses_before_journal_creation(self):
        (self.project / 'project.json').write_bytes(b'UNRELATED')
        with self.assertRaises(self.module.BundleError):
            self.store.apply(self.after, self.before)
        self.assertFalse(self.store.path.exists())
        self.assertEqual((self.project / 'screenplay.fountain').read_bytes(), self.before['screenplay.fountain'])

    def test_noop_preserves_every_file_mtime_and_creates_no_journal(self):
        times = {name: (self.project / name).stat().st_mtime_ns for name in self.before}
        self.assertTrue(self.store.apply(self.before, self.before)['unchanged'])
        self.assertFalse(self.store.path.exists())
        self.assertEqual(times, {name: (self.project / name).stat().st_mtime_ns for name in self.before})

    def test_restart_complete_recovers_partial_bundle_with_exact_bytes(self):
        pending, calls = self.interrupted(2)
        self.assertEqual(len(calls), 2)
        self.assertEqual((self.project / 'screenplay.fountain').read_bytes(), self.before['screenplay.fountain'])
        self.new_store().recover(pending, 'complete')
        self.assertEqual(self.values(), self.after)
        self.assertIsNone(self.new_store().status()['pending_operation'])

    def test_restart_abort_restores_exact_originals(self):
        pending, _ = self.interrupted(3)
        self.new_store().recover(pending, 'abort')
        self.assertEqual(self.values(), self.before)

    def test_fresh_mutation_cannot_replace_pending_intent(self):
        pending, _ = self.interrupted(1)
        snapshot = self.store.path.read_bytes()
        with self.assertRaises(self.module.BundleError):
            self.store.apply(self.after, self.before)
        self.assertEqual(self.store.path.read_bytes(), snapshot)
        self.assertEqual(self.store.status()['pending_operation']['id'], pending)

    def test_unknown_recovery_action_or_id_preserves_all_bytes(self):
        pending, _ = self.interrupted(2)
        before = self.values()
        for identity, action in [(pending, 'retry'), ('not-an-operation', 'complete')]:
            with self.assertRaises(self.module.BundleError):
                self.store.recover(identity, action)
        self.assertEqual(self.values(), before)

    def test_unrelated_edit_refuses_recovery_before_any_output_changes(self):
        pending, _ = self.interrupted(2)
        (self.project / 'screenplay.fountain').write_bytes(b'PRIVATE UNSAVED EXTERNAL EDIT\r\n')
        before = self.values()
        with self.assertRaises(self.module.BundleError):
            self.store.recover(pending, 'complete')
        self.assertEqual(self.values(), before)

    def test_corrupt_payload_or_manifest_never_becomes_a_write_recipe(self):
        pending, _ = self.interrupted(1)
        with closing(sqlite3.connect(self.store.path)) as connection:
            connection.execute("UPDATE files SET after_content=? WHERE name='screenplay.fountain'", (b'CORRUPTED',))
            connection.commit()
        before = self.values()
        with self.assertRaises(self.module.BundleError):
            self.store.recover(pending, 'complete')
        self.assertEqual(self.values(), before)

    def test_unexpected_file_paths_and_nonbytes_fail_before_intent(self):
        for changed in ({**self.after, '../outside': b'NO'},
                        {**self.after, 'screenplay.fountain': 'text'},
                        {'screenplay.fountain': self.after['screenplay.fountain']}):
            with self.assertRaises(self.module.BundleError):
                self.store.apply(changed, self.before)
        self.assertFalse(self.store.path.exists())
        self.assertEqual(self.values(), self.before)

    def test_logical_budget_refuses_without_canonical_mutation(self):
        with patch.object(self.module, 'MAX_RETAINED_BYTES', 1):
            with self.assertRaises(self.module.BundleError):
                self.store.apply(self.after, self.before)
        self.assertEqual(self.values(), self.before)

    def test_newly_created_members_still_consume_retained_byte_budget(self):
        for name in ('Synthetic Project.fdx', 'project.json'):
            (self.project / name).unlink()  # Synthetic fixture setup only.
            self.before[name] = None
        self.store.apply(self.after, self.before)
        next_outputs = {name: raw + b'\n' for name, raw in self.after.items()}
        retained = sum(len(self.before[name] or b'') + len(self.after[name]) for name in self.before)
        addition = sum(len(self.after[name]) + len(next_outputs[name]) for name in self.after)
        with patch.object(self.module, 'MAX_RETAINED_BYTES', retained + addition - 1):
            with self.assertRaises(self.module.BundleError):
                self.store.apply(next_outputs, self.after)
        self.assertEqual(self.values(), self.after)

    def test_edit_between_preflight_and_next_promotion_is_not_adopted(self):
        promote = self.store._promote
        def external_edit(name, expected, target, operation):
            result = promote(name, expected, target, operation)
            if name == 'Synthetic Project.fdx':
                (self.project / 'project.json').write_bytes(b'EXTERNAL EDIT AFTER PREFLIGHT')
            return result
        with patch.object(self.store, '_promote', side_effect=external_edit):
            with self.assertRaises(self.module.BundleError):
                self.store.apply(self.after, self.before)
        self.assertEqual((self.project / 'project.json').read_bytes(), b'EXTERNAL EDIT AFTER PREFLIGHT')
        self.assertEqual((self.project / 'screenplay.fountain').read_bytes(), self.before['screenplay.fountain'])
        self.assertIsNotNone(self.store.status()['pending_operation'])

    def test_missing_derivative_abort_retains_new_output_in_recovery_folder(self):
        path = self.project / 'Synthetic Project.fdx'
        # This deletion is confined to the synthetic fixture's setup.
        path.unlink()
        self.before['Synthetic Project.fdx'] = None
        pending, _ = self.interrupted(3)
        self.new_store().recover(pending, 'abort')
        self.assertIsNone(self.values()['Synthetic Project.fdx'])
        retained = self.project / '.writing-reorder-retained' / pending / 'Synthetic Project.fdx'
        self.assertEqual(retained.read_bytes(), self.after['Synthetic Project.fdx'])

    def test_unrecognized_existing_database_is_not_replaced(self):
        self.store.path.write_bytes(b'opaque retained evidence')
        with self.assertRaises(self.module.BundleError):
            self.store.apply(self.after, self.before)
        self.assertEqual(self.store.path.read_bytes(), b'opaque retained evidence')
        self.assertEqual(self.values(), self.before)

    def workflow(self):
        from core.screenplay_workflows import WorkflowStore
        def snapshot():
            raw = (self.project / 'screenplay.fountain').read_bytes()
            return dict(content=raw.decode(), revision=hashlib.sha256(raw).hexdigest())
        def write(raw):
            self.assertEqual(raw, self.after['screenplay.fountain'])
            self.store.apply(self.after, self.before)
        return WorkflowStore(self.project, snapshot, write, self.lock), snapshot

    def test_actual_workflow_write_updates_branch_epoch_after_bundle(self):
        workflow, snapshot = self.workflow()
        created = workflow.create_branch('Other', snapshot()['revision'], 0)
        result = workflow.write(self.after['screenplay.fountain'], snapshot()['revision'], created['workflow_revision'])
        self.assertEqual(result['workflow_revision'], 2)
        self.assertIsNone(result['pending_operation'])
        self.assertEqual(self.values(), self.after)
        with closing(sqlite3.connect(workflow.path)) as connection:
            self.assertEqual(connection.execute("SELECT content FROM branches WHERE key='main'").fetchone()[0], self.after['screenplay.fountain'])

    def test_interrupted_bundle_complete_then_workflow_complete(self):
        workflow, snapshot = self.workflow()
        promote = self.store._promote
        def interrupt(name, expected, target, operation):
            if name == 'screenplay.fountain':
                raise OSError('synthetic stop')
            return promote(name, expected, target, operation)
        with patch.object(self.store, '_promote', side_effect=interrupt):
            with self.assertRaises(OSError):
                workflow.write(self.after['screenplay.fountain'], snapshot()['revision'], 0)
        operation = workflow.status()['pending_operation']['id']
        self.store.recover(self.store.status()['pending_operation']['id'], 'complete')
        result = workflow.recover(operation, 'complete')
        self.assertEqual(result['workflow_revision'], 1)
        self.assertEqual(self.values(), self.after)

    def test_interrupted_bundle_abort_then_workflow_abort(self):
        workflow, snapshot = self.workflow()
        with patch.object(self.store, '_promote', side_effect=OSError('synthetic stop')):
            with self.assertRaises(OSError):
                workflow.write(self.after['screenplay.fountain'], snapshot()['revision'], 0)
        operation = workflow.status()['pending_operation']['id']
        self.store.recover(self.store.status()['pending_operation']['id'], 'abort')
        result = workflow.recover(operation, 'abort')
        self.assertEqual(result['workflow_revision'], 1)
        self.assertEqual(self.values(), self.before)

    def test_workflow_finish_failure_keeps_bundle_and_allows_explicit_completion(self):
        workflow, snapshot = self.workflow()
        with patch.object(workflow, '_finish', side_effect=OSError('synthetic workflow commit interruption')):
            with self.assertRaises(OSError):
                workflow.write(self.after['screenplay.fountain'], snapshot()['revision'], 0)
        operation = workflow.status()['pending_operation']['id']
        self.assertEqual(self.values(), self.after)
        self.assertIsNone(self.store.status()['pending_operation'])
        workflow.recover(operation, 'complete')
        self.assertIsNone(workflow.status()['pending_operation'])

    def test_all_files_promoted_before_bundle_commit_recovers_without_rewrite(self):
        workflow, snapshot = self.workflow()
        complete = self.store._complete
        def interrupt(connection, operation, action):
            complete(connection, operation, action)
            raise OSError('synthetic stop before bundle commit')
        with patch.object(self.store, '_complete', side_effect=interrupt):
            with self.assertRaises(OSError):
                workflow.write(self.after['screenplay.fountain'], snapshot()['revision'], 0)
        self.assertEqual(self.values(), self.after)
        bundle_operation = self.store.status()['pending_operation']['id']
        workflow_operation = workflow.status()['pending_operation']['id']
        stamps = {name: (self.project / name).stat().st_mtime_ns for name in self.after}
        with patch.object(self.store, '_promote', side_effect=AssertionError('must not rewrite')):
            self.store.recover(bundle_operation, 'complete')
        workflow.recover(workflow_operation, 'complete')
        self.assertEqual(stamps, {name: (self.project / name).stat().st_mtime_ns for name in self.after})
        self.assertIsNone(self.store.status()['pending_operation'])
        self.assertIsNone(workflow.status()['pending_operation'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
