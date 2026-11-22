"""Actual editor method bodies with isolated files/journal and inert UI adapters."""
import ast
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from native_studio.editor_file_store import durable_write_source, read_source_checkpoint, EditorFileStoreError

ROOT = Path(__file__).resolve().parents[2]


class EditorSaveAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / 'example.py'
        self.original = b'# coding: latin-1\r\nname = "caf\xe9"\r\n'
        self.path.write_bytes(self.original)
        self.database = self.root / 'synthetic.db'
        sqlite3.connect(self.database).close()
        self.messages = []
        self.saved = []
        self.editor_text = ''
        methods = {'_open_file_in_editor', '_save_scratchpad_to_file', '_save_last_code_to_file'}
        tree = ast.parse((ROOT / 'native_studio/bs_chat_ide_full.py').read_text(encoding='utf-8'))
        view = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BsChatIdeFullView')
        bodies = [n for n in view.body if isinstance(n, ast.FunctionDef) and n.name in methods]
        self.assertEqual({n.name for n in bodies}, methods)
        scope = {'os': os, 're': re, 'Path': Path, 'hashlib': hashlib,
                 'QLineEdit': SimpleNamespace(EchoMode=SimpleNamespace(Normal=0)),
                 'QInputDialog': SimpleNamespace(getText=lambda *a: (str(self.path), True)),
                 'QMessageBox': SimpleNamespace(**{kind: self.message(kind) for kind in ('information', 'warning', 'critical')})}
        exec(compile(ast.fix_missing_locations(ast.Module(body=bodies, type_ignores=[])), '<actual-editor-save>', 'exec'), scope)
        self.view = SimpleNamespace(_current_editor_file=None, _current_editor_loaded_sha256=None,
            _current_editor_encoding='utf-8', _split_active=True, _is_streaming=False,
            _extract_last_code_block=lambda: ('python', 'value = 7\n'),
            code_editor=SimpleNamespace(set_current_file=lambda value: None,
                setPlainText=self.set_text, toPlainText=lambda: self.editor_text),
            lbl_canvas=SimpleNamespace(setText=lambda value: None, setToolTip=lambda value: None),
            chat_display=SimpleNamespace(appendPlainText=lambda value: None))
        self.methods = scope
        def save(target, raw, **kwargs):
            result = durable_write_source(target, raw, database=self.database, **kwargs)
            self.saved.append(result)
            return result
        self.save_patch = patch('native_studio.editor_file_store.durable_write_source', side_effect=save)
        self.save_patch.start()
        self.addCleanup(self.save_patch.stop)

    def message(self, kind):
        return lambda *args: self.messages.append((kind, args[1:]))

    def set_text(self, value):
        self.editor_text = value

    def call(self, method, *args):
        return self.methods[method](self.view, *args)

    def test_loaded_encoding_and_bytes_are_preserved_before_editor_save(self):
        self.call('_open_file_in_editor', str(self.path))
        self.assertIn('café', self.editor_text)
        self.editor_text += '# changed\r\n'
        expected = self.editor_text.encode(self.view._current_editor_encoding)
        self.call('_save_scratchpad_to_file')
        self.assertEqual(self.path.read_bytes(), expected)
        row = read_source_checkpoint(self.saved[0]['operation_id'], database=self.database)
        self.assertEqual(row['original_bytes'], self.original)
        self.assertEqual(row['draft_bytes'], expected)
        self.assertEqual(self.view._current_editor_loaded_sha256, hashlib.sha256(expected).hexdigest())

    def test_external_source_change_is_not_overwritten(self):
        self.call('_open_file_in_editor', str(self.path))
        self.editor_text += '# local draft\n'
        changed = b'# external change\n'
        self.path.write_bytes(changed)
        self.call('_save_scratchpad_to_file')
        self.assertEqual(self.path.read_bytes(), changed)
        self.assertIn('local draft', self.editor_text)
        self.assertTrue(any(kind == 'critical' for kind, _ in self.messages))

    def test_code_block_save_uses_real_prewrite_journal(self):
        self.call('_save_last_code_to_file')
        self.assertEqual(self.path.read_bytes(), b'value = 7\n')
        row = read_source_checkpoint(self.saved[0]['operation_id'], database=self.database)
        self.assertEqual(row['original_bytes'], self.original)
        self.assertEqual(row['draft_bytes'], b'value = 7\n')

    def test_postpromotion_ack_failure_is_not_reported_as_no_write(self):
        self.call('_open_file_in_editor', str(self.path))
        self.editor_text += '# draft\n'
        self.save_patch.stop()
        with patch('native_studio.editor_file_store.durable_write_source',
                side_effect=EditorFileStoreError('journal_ack_failed', operation_id='synthetic', written=True)) as save:
            self.call('_save_scratchpad_to_file')
        self.assertEqual(save.call_count, 1)
        self.assertTrue(any(kind == 'warning' and 'promoted' in str(text) for kind, text in self.messages))
        self.assertFalse(any(kind == 'critical' for kind, _ in self.messages))


if __name__ == '__main__':
    unittest.main()
