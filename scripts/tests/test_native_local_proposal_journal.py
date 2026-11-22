"""Check the proposal/inference durability ordering using an isolated WAL database."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from native_studio.local_source_journal import LocalSourceJournal
from native_studio.local_refactor_view import prepare_local_proposal


class ProposalJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'example.py'
        self.original = b'def answer():\r\n    return 42\r\n'
        self.source.write_bytes(self.original)
        self.database = self.root / 'synthetic.db'
        self.journal = LocalSourceJournal(self.database, create=True)
        self.calls = 0

    async def infer(self, **kwargs):
        self.calls += 1
        with closing(sqlite3.connect(self.database)) as connection:
            row = connection.execute('SELECT status,source_bytes FROM native_refactor_runs').fetchone()
            self.assertEqual(row, ('STARTED', self.original))
            self.assertEqual(connection.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        return {'text': 'def answer():\n    return 6 * 7\n', 'receipt': {
            'provider': 'local', 'status': 'completed', 'generation_verified': True,
            'completion_verified': True, 'completion_reason': 'stop',
            'requested_model': 'fixture', 'model': 'fixture:latest',
            'actual_model': 'fixture:latest', 'endpoint': 'http://127.0.0.1:11434'}}

    def test_source_is_durable_before_inference_and_candidate_durable_before_export(self):
        result = prepare_local_proposal(self.source, self.root, endpoint='http://127.0.0.1:11434',
            model='fixture', journal=self.journal, infer=self.infer)
        self.assertEqual(self.calls, 1)
        row = LocalSourceJournal(self.database).read(result['operation_id'])
        self.assertEqual(row['status'], 'PROPOSAL_READY')
        self.assertEqual(row['source_bytes'], self.original)
        self.assertEqual(row['candidate_bytes'], result['proposal']['candidate_bytes'])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_inference_failure_is_recorded_without_losing_source(self):
        async def failing(**kwargs):
            await self.infer(**kwargs)
            raise RuntimeError('synthetic transport failure')
        with self.assertRaises(RuntimeError):
            prepare_local_proposal(self.source, self.root, endpoint='http://127.0.0.1:11434',
                model='fixture', journal=self.journal, infer=failing)
        with closing(sqlite3.connect(self.database)) as connection:
            row = connection.execute('SELECT status,source_bytes,candidate_bytes FROM native_refactor_runs').fetchone()
        self.assertEqual(row, ('FAILED', self.original, None))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_failed_snapshot_prevents_any_model_request(self):
        with self.assertRaises(sqlite3.OperationalError):
            prepare_local_proposal(self.source, self.root, endpoint='http://127.0.0.1:11434',
                model='fixture', journal=LocalSourceJournal(self.database), infer=self.infer)
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_source_change_after_snapshot_is_rejected_before_inference(self):
        original_begin = self.journal.begin
        changed = b'def answer():\n    return 99\n'
        def begin_and_modify(path, raw):
            operation = original_begin(path, raw)
            self.source.write_bytes(changed)
            return operation
        self.journal.begin = begin_and_modify
        with self.assertRaises(ValueError):
            prepare_local_proposal(self.source, self.root, endpoint='http://127.0.0.1:11434',
                model='fixture', journal=self.journal, infer=self.infer)
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.source.read_bytes(), changed)
        with closing(sqlite3.connect(self.database)) as connection:
            row = connection.execute('SELECT status,source_bytes FROM native_refactor_runs').fetchone()
        self.assertEqual(row, ('FAILED', self.original))


if __name__ == '__main__':
    unittest.main()
