"""Actual isolated SQLite WAL/readback; no access to a private master database."""
from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest
from native_studio.local_source_journal import LocalSourceJournal


class SourceJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'synthetic.db'
        self.journal = LocalSourceJournal(self.db, create=True)
        self.original = b'# original\r\nvalue = 1\r\n'

    def proposal(self):
        return dict(source_path='fixture.py', original_bytes=self.original, candidate_bytes=b'value = 2\n',
                    receipt={'completion_verified': True, 'generation_verified': True, 'status': 'completed'})

    def test_snapshot_is_durable_before_proposal_and_fresh_reopen_preserves_bytes(self):
        operation = self.journal.begin('fixture.py', self.original)
        row = LocalSourceJournal(self.db).read(operation)
        self.assertEqual(row['source_bytes'], self.original)
        self.assertEqual(row['status'], 'STARTED')
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        self.journal.record_candidate(operation, self.proposal())
        row = LocalSourceJournal(self.db).read(operation)
        self.assertEqual(row['candidate_bytes'], b'value = 2\n')
        self.assertEqual(row['source_bytes'], self.original)
        self.assertEqual(row['status'], 'PROPOSAL_READY')

    def test_failed_operation_preserves_original_and_does_not_make_candidate(self):
        operation = self.journal.begin('fixture.py', self.original)
        self.journal.fail(operation, 'LocalInferenceError')
        row = self.journal.read(operation)
        self.assertEqual(row['source_bytes'], self.original)
        self.assertIsNone(row['candidate_bytes'])
        self.assertEqual(row['status'], 'FAILED')

    def test_changed_or_unverified_source_cannot_complete_journal(self):
        operation = self.journal.begin('fixture.py', self.original)
        wrong = self.proposal()
        wrong['original_bytes'] += b'# changed'
        with self.assertRaises(ValueError):
            self.journal.record_candidate(operation, wrong)
        wrong = self.proposal()
        wrong['receipt']['completion_verified'] = False
        with self.assertRaises(ValueError):
            self.journal.record_candidate(operation, wrong)
        self.assertEqual(self.journal.read(operation)['status'], 'STARTED')

    def test_missing_master_is_not_silently_created(self):
        with self.assertRaises(sqlite3.OperationalError):
            LocalSourceJournal(self.db).begin('fixture.py', self.original)
        self.assertFalse(self.db.exists())


if __name__ == '__main__':
    unittest.main()
