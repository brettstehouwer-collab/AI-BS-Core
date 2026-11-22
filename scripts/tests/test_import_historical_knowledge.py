import importlib.util
from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('historical_import', Path(__file__).resolve().parents[1] / 'import_historical_knowledge.py')
imp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(imp)


class SourceCardTests(unittest.TestCase):
    def test_prose_boundaries_preserve_all_characters_and_historical_chunking(self):
        text = ('An observable test fixture has precise acceptance criteria and retained evidence. ' * 9 + '\n\n') * 5
        parts = list(imp.prose_chunks(text))
        self.assertEqual(''.join(part for _, part in parts), text)
        self.assertTrue(all(len(part) <= 1800 for _, part in parts))
        self.assertTrue(all(part.endswith('\n\n') for _, part in parts[:-1]))
        self.assertEqual(list(imp.chunks(text))[0], (0, text[:1800]))

    def cli(self, root, card, output, reviewed=None):
        args = ['import_historical_knowledge.py', '--source-card', str(card), '--output', str(output)]
        if reviewed is not None:
            args += ['--apply-local-admin', '--reviewed-manifest', str(reviewed)]
        with patch.object(imp, 'ROOT', root), patch.object(sys, 'argv', args), \
                patch.object(imp, 'build', side_effect=AssertionError('archive must not be scanned')), \
                redirect_stdout(io.StringIO()):
            imp.main()

    def make_card(self, root):
        card = root / 'evaluation_card.md'
        card.write_text('Observable evaluation guidance: preserve actual executable test evidence, score grounded final answers against fixed rubrics, and report unmeasured quality honestly.\n', encoding='utf-8')
        return card

    def test_only_selected_card_is_catalogued(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card = self.make_card(root)
            (root / 'unrelated.md').write_text('UNRELATED_SENTINEL' * 10, encoding='utf-8')
            self.cli(root, card, root / 'review')
            manifest = json.loads((root / 'review/manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['source_mode'], 'single_card')
            self.assertEqual(manifest['source_card'], str(card.resolve()))
            self.assertEqual(len(manifest['files']), 1)
            self.assertNotIn('UNRELATED_SENTINEL', (root / 'review/records.jsonl').read_text(encoding='utf-8'))
            self.assertFalse((root / 'backend').exists())

    def test_changed_card_aborts_before_auth_or_database_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card = self.make_card(root)
            self.cli(root, card, root / 'review')
            card.write_text(card.read_text(encoding='utf-8') + 'Changed evidence must be reviewed again.\n', encoding='utf-8')
            with patch.object(imp.sqlite3, 'connect') as connect:
                with self.assertRaisesRegex(ValueError, 'changed since review'):
                    self.cli(root, card, root / 'attempt', root / 'review/manifest.json')
            connect.assert_not_called()

    def test_unverified_principal_cannot_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card = self.make_card(root)
            self.cli(root, card, root / 'review')
            with patch('security.firebase_auth.get_admin_principal', return_value=None), \
                    patch.object(imp.sqlite3, 'connect') as connect:
                with self.assertRaises(PermissionError):
                    self.cli(root, card, root / 'attempt', root / 'review/manifest.json')
            connect.assert_not_called()

    def test_backup_readback_retry_and_existing_hidden_foreign_rows_preserved(self):
        from core.owned_vault import store_record, hide_record, read_record
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'backend').mkdir()
            db = root / 'backend/stehouwer_vault.db'
            with closing(sqlite3.connect(db)) as conn:
                conn.execute('CREATE TABLE vault_items(id INTEGER PRIMARY KEY, title TEXT, content TEXT, collection TEXT, tags TEXT, item_hash TEXT)')
                conn.commit()
            first = store_record(db, 'local_admin', 'prior hidden', 'preserve original hidden bytes')
            hide_record(db, 'local_admin', first['id'])
            store_record(db, 'firebase:project:other', 'foreign', 'foreign original bytes')
            with closing(sqlite3.connect(db)) as conn:
                before = conn.execute('SELECT * FROM vault_items ORDER BY id').fetchall()
            card = self.make_card(root)
            self.cli(root, card, root / 'review')
            with patch('security.firebase_auth.get_admin_principal', return_value='local_admin'):
                self.cli(root, card, root / 'apply', root / 'review/manifest.json')
                self.cli(root, card, root / 'retry', root / 'review/manifest.json')
            with closing(sqlite3.connect(root / 'apply/vault_before.sqlite3')) as backup:
                self.assertEqual(backup.execute('SELECT * FROM vault_items ORDER BY id').fetchall(), before)
            with closing(sqlite3.connect(db)) as conn:
                after = conn.execute('SELECT * FROM vault_items ORDER BY id').fetchall()
                self.assertEqual(after[:len(before)], before)
                self.assertEqual(len(after), len(before) + 1)
            receipt = json.loads((root / 'apply/import_receipt.json').read_text(encoding='utf-8'))
            repeated = json.loads((root / 'retry/import_receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt, repeated)
            actual = read_record(db, 'local_admin', receipt['records'][0]['id'], include_legacy=False)
            self.assertIn(card.read_text(encoding='utf-8').strip(), actual['content'])
            self.assertEqual(actual['content_sha256'], receipt['records'][0]['content_sha256'])

    def test_nonprose_empty_and_filtered_cards_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, text in [('program.exe', 'not prose' * 50), ('empty.md', ''),
                               ('private.md', 'api_key = SECRET_FIXTURE_VALUE ' * 10)]:
                card = root / name
                card.write_text(text, encoding='utf-8')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    imp.build_source_card(imp.Corpus(), card)


class HistoricalImportTests(unittest.TestCase):
    def test_only_visible_events_and_fields_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp)
            logs = brain / 'session/.system_generated/logs'
            logs.mkdir(parents=True)
            visible = 'Explicit engineering result: the renderer preserves original screenplay bytes. ' * 3
            records = [
                {'type': 'USER_INPUT', 'content': visible, 'thinking': 'PRIVATE_THOUGHT_SENTINEL'},
                {'type': 'PLANNER_RESPONSE', 'content': visible, 'tool_calls': ['TOOL_CALL_SENTINEL']},
                {'type': 'GENERIC', 'content': 'TOOL_RESULT_SENTINEL' * 10},
            ]
            (logs / 'transcript.jsonl').write_text('\n'.join(json.dumps(x) for x in records), encoding='utf-8')
            corpus = imp.Corpus()
            corpus.antigravity(brain)
            data = json.dumps(list(corpus.records.values()))
            self.assertNotIn('PRIVATE_THOUGHT_SENTINEL', data)
            self.assertNotIn('TOOL_CALL_SENTINEL', data)
            self.assertNotIn('TOOL_RESULT_SENTINEL', data)
            self.assertEqual(len(corpus.records), 1)
            self.assertEqual(len(next(iter(corpus.records.values()))['sources']), 2)

    def test_function_results_and_thought_parts_cannot_be_imported(self):
        parts = [{'text': 'user visible'}, {'functionResponse': {'result': 'private'}},
                 {'text': 'hidden', 'thought': True}, {'functionCall': {'name': 'shell'}}]
        self.assertEqual(imp.plain_parts(parts), 'user visible')

    def test_privacy_filter_rejects_secrets_and_removes_contacts(self):
        self.assertIsNone(imp.sanitize('An architecture record with api_key = SECRET_TEST_VALUE and more prose. ' * 2)[0])
        self.assertIsNone(imp.sanitize('Patient diagnosis and prescription details should remain private. ' * 3)[0])
        cleaned, reason = imp.sanitize('Contact example@example.com or 616-555-0123 for the renderer documentation. ' * 3)
        self.assertIsNone(reason)
        self.assertNotIn('example@example.com', cleaned)
        self.assertNotIn('616-555-0123', cleaned)
        cleaned, reason = imp.sanitize('Renderer documentation contact: 6165550123 or +16165550123. ' * 3)
        self.assertIsNone(reason)
        self.assertNotIn('6165550123', cleaned)
        self.assertIsNone(imp.sanitize('My medication and therapy history is private. ' * 4)[0])

    def test_private_document_classes_are_excluded(self):
        for name in ('Resume (3).pdf.html', 'Contact List and Codes.pdf.html',
                     'Publishing Contract signed.pdf.html', 'Employment Agreement.md',
                     'leads.csv.html', 'West_Michigan_Leads.md.html', 'Financial Orientation.pdf.html'):
            with self.subTest(name=name):
                corpus = imp.Corpus()
                self.assertIsNone(corpus.read(Path(name), 'historical_document'))
                self.assertEqual(corpus.files[0]['disposition'], 'excluded_private_filename')

    def test_html_scripts_and_hidden_head_are_excluded(self):
        parser = imp.VisibleHTML()
        parser.feed('<head>HIDDEN_HEAD</head><script>HIDDEN_SCRIPT</script><p>Visible reference</p>')
        self.assertNotIn('HIDDEN', ''.join(parser.out))
        self.assertIn('Visible reference', ''.join(parser.out))

    def test_import_idempotency_owner_isolation_and_actual_llm_context(self):
        from core.owned_vault import search_records
        from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
        from core import historical_reference_context as references
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'vault.db'
            with sqlite3.connect(db) as conn:
                conn.execute('CREATE TABLE vault_items(id INTEGER PRIMARY KEY, title TEXT, content TEXT, collection TEXT, tags TEXT, item_hash TEXT)')
            conn.close()
            corpus = imp.Corpus()
            corpus.add('Screenplay pagination should preserve source bytes; use acceptance evidence to validate renderer behavior. ' * 3,
                       Path('source.md'), 'explicit_artifact', 'document', 'a' * 64)
            records = list(corpus.records.values())
            first = imp.import_records(records, db, 'local_admin')
            second = imp.import_records(records, db, 'local_admin')
            self.assertEqual(first, second)
            self.assertEqual(len(search_records(db, 'local_admin', 'pagination')), 1)
            self.assertEqual(search_records(db, 'firebase:project:another-user', 'pagination'), [])
            prior = references.VAULT_DB_PATH
            references.VAULT_DB_PATH = db
            token = bind_memory_principal('local_admin')
            try:
                context = references.historical_reference_context('screenplay pagination')
                self.assertIn('source.md', context)
                self.assertIn('Historical unverified source data', context)
                self.assertIn('preserve source bytes', context)
            finally:
                reset_memory_principal(token)
                references.VAULT_DB_PATH = prior


if __name__ == '__main__':
    unittest.main()
