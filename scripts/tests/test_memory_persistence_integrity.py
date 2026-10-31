"""Offline memory regressions; disposable files and injected stores only."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]


def load_memory():
    chroma = types.ModuleType('chromadb')
    chroma.HttpClient = Mock(side_effect=RuntimeError('offline fixture'))
    chroma.PersistentClient = Mock(side_effect=AssertionError('original vector store forbidden'))
    utils = types.ModuleType('chromadb.utils')
    utils.embedding_functions = object()
    spec = importlib.util.spec_from_file_location('backend.core._audit_memory_bank', ROOT/'backend/core/memory_bank.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'chromadb': chroma, 'chromadb.utils': utils}):
        spec.loader.exec_module(module)
    return module, chroma


class MemoryPersistenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='memory_integrity_')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.memory, self.chroma = load_memory()
        self.memory._root_dir = self.folder
        self.memory._backend_dir = self.folder
        self.memory.MASTER_MEMORY_CANDIDATES = [str(self.folder/'master_memory_dump.json')]
        self.memory.VAULT_DB_PATH = str(self.folder/'vault.db')
        self.memory._ensure_collections = Mock(return_value=False)
        self.check_fixture_integrity()
        self.addCleanup(self.check_fixture_integrity)

    def check_fixture_integrity(self):
        conn = self.memory.sqlite3.connect(self.memory.VAULT_DB_PATH)
        try:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        finally:
            conn.close()

    def test_import_never_connects_or_opens_local_chroma(self):
        self.chroma.HttpClient.assert_not_called()
        self.chroma.PersistentClient.assert_not_called()

    def test_unavailable_http_retries_after_bounded_backoff_only(self):
        memory, chroma = load_memory()
        with patch.dict(sys.modules, {'chromadb': chroma}), patch.object(memory.time, 'monotonic', side_effect=[100.0, 101.0, 131.0]):
            self.assertFalse(memory._ensure_collections())
            self.assertFalse(memory._ensure_collections())
            self.assertFalse(memory._ensure_collections())
        self.assertEqual(chroma.HttpClient.call_count, 2)
        chroma.PersistentClient.assert_not_called()

    def test_path_lookup_is_read_only(self):
        self.memory._root_dir = self.folder
        self.assertEqual(self.memory.get_master_memory_path(), str(self.folder/'master_memory_dump.json'))
        self.assertFalse((self.folder/'master_memory_dump.json').exists())

    def test_corrupt_original_is_preserved_and_new_record_journaled(self):
        source = self.folder/'master_memory_dump.json'
        original = b'[{"historic": "complete original source", broken tail'
        source.write_bytes(original)
        self.assertTrue(self.memory.store_heuristic('new evidence'))
        self.assertEqual(source.read_bytes(), original)
        lines = (self.folder/'master_memory_dump.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(json.loads(lines[-1])['text'], 'new evidence')

    def test_more_than_500_records_are_never_evicted(self):
        source = self.folder/'master_memory_dump.json'
        original = json.dumps([{'text': str(i)} for i in range(601)]).encode()
        source.write_bytes(original)
        self.assertTrue(self.memory.store_heuristic('retained new evidence'))
        self.assertEqual(source.read_bytes(), original)

    def test_all_store_failures_are_reported(self):
        with patch.object(self.memory.sqlite3, 'connect', side_effect=OSError('fixture blocked')), \
                patch('builtins.open', side_effect=OSError('fixture blocked')), \
                patch.object(Path, 'open', side_effect=OSError('fixture blocked')):
            self.assertFalse(self.memory.store_heuristic('not durable'))

    def test_case_without_store_does_not_claim_success(self):
        self.assertFalse(self.memory.store_case_resolution('trace', 'resolution'))

    def test_metadata_is_not_modified(self):
        metadata = {'source': 'fixture'}
        self.assertTrue(self.memory.store_heuristic('retain metadata', metadata))
        self.assertEqual(metadata, {'source': 'fixture'})

    def test_sqlite_integrity_and_handle_release(self):
        conn = self.memory.sqlite3.connect(self.memory.VAULT_DB_PATH)
        try:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        finally:
            conn.close()
        self.assertTrue(self.memory.store_heuristic('durable record'))
        conn = self.memory.sqlite3.connect(self.memory.VAULT_DB_PATH)
        try:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(conn.execute('SELECT content FROM vault_items').fetchone()[0], 'durable record')
        finally:
            conn.close()

    def test_status_never_opens_original_vector_sqlite(self):
        self.memory.VECTOR_DB_DIR = str(self.folder/'vector')
        vector = self.folder/'vector/chroma.sqlite3'
        vector.parent.mkdir()
        vector.write_bytes(b'original recovery source')
        with patch.object(self.memory.sqlite3, 'connect', side_effect=AssertionError('vector DB forbidden')) as connect:
            self.memory.get_memory_bank_status()
        self.assertFalse(any('chroma.sqlite3' in str(call.args) for call in connect.call_args_list))

    def test_status_includes_new_journal_records(self):
        self.assertTrue(self.memory.store_heuristic('journal evidence'))
        status = self.memory.get_memory_bank_status()
        self.assertEqual(status.get('master_memory_journal_blocks'), 1)


if __name__ == '__main__':
    unittest.main()
