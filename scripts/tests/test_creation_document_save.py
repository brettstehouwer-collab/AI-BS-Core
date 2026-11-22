"""Document alias functions against synthetic files and actual retention checks."""
import ast
import asyncio
import importlib.util
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Optional
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import BaseModel, StrictStr

ROOT = Path(__file__).resolve().parents[2]


class DocumentSaveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.drive = Path(self.temp.name) / 'drive'
        self.drive.mkdir()
        package = ModuleType('routers')
        package.__path__ = []
        drive_module = ModuleType('routers.shared_drive_router')
        drive_module.DRIVE_ROOT = self.drive
        security_package = ModuleType('security')
        security_package.__path__ = []
        spec = importlib.util.spec_from_file_location('security.document_retention', ROOT / 'backend/security/document_retention.py')
        retention = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retention)
        store_spec = importlib.util.spec_from_file_location('security.document_store', ROOT / 'backend/security/document_store.py')
        store = importlib.util.module_from_spec(store_spec)
        store_spec.loader.exec_module(store)
        module_patch = patch.dict(sys.modules, {'routers': package, 'routers.shared_drive_router': drive_module,
                                              'security': security_package, 'security.document_retention': retention,
                                              'security.document_store': store})
        module_patch.start()
        self.addCleanup(module_patch.stop)
        names = {'_document_text_extensions', '_document_file_path', 'DocumentSaveRequest',
                 'read_document_file_alias', 'save_document_file_alias'}
        tree = ast.parse((ROOT / 'backend/AI_BS_Backend.py').read_text(encoding='utf-8'))
        bodies = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in names]
        for node in bodies:
            node.decorator_list = []
        self.scope = dict(Path=Path, Optional=Optional, HTTPException=HTTPException, BaseModel=BaseModel, StrictStr=StrictStr, os=os)
        exec(compile(ast.Module(body=bodies, type_ignores=[]), '<actual-document-aliases>', 'exec'), self.scope)

    def save(self, path, content, **options):
        if path.is_file() and not options.get('create_only'):
            options.setdefault('expected_revision', hashlib.sha256(path.read_bytes()).hexdigest())
        payload = self.scope['DocumentSaveRequest'](path=str(path), content=content, **options)
        return asyncio.run(self.scope['save_document_file_alias'](payload))

    def test_same_text_save_preserves_crlf_bom_revision_bytes_and_mtime(self):
        target = self.drive / 'fixture.fountain'
        for raw in (b'TITLE\r\nINT. ROOM\r\n', b'\xef\xbb\xbfTITLE\r\nINT. ROOM\r\n', b'A\rB\nC\r\n'):
            target.write_bytes(raw)
            before = (hashlib.sha256(raw).hexdigest(), target.stat().st_mtime_ns)
            loaded = asyncio.run(self.scope['read_document_file_alias'](path=str(target)))
            result = self.save(target, loaded['content'])
            self.assertTrue(result.get('unchanged'))
            self.assertEqual(target.read_bytes(), raw)
            self.assertEqual((hashlib.sha256(target.read_bytes()).hexdigest(), target.stat().st_mtime_ns), before)

    def test_real_edit_is_saved_and_reloaded_and_explicit_newline_conversion_can_be_requested(self):
        target = self.drive / 'fixture.txt'
        target.write_bytes(b'OLD\r\n')
        self.save(target, 'NEW\n')
        loaded = asyncio.run(self.scope['read_document_file_alias'](path=str(target)))
        self.assertEqual(loaded['content'], 'NEW\n')
        # Windows text writes retain their existing newline convention; an explicit
        # format request still performs a write instead of taking the no-op path.
        result = self.save(target, 'NEW\n', preserve_unchanged_bytes=False)
        self.assertFalse(result.get('unchanged', False))

    def test_create_only_collision_preserves_existing_bytes_even_when_text_matches(self):
        target = self.drive / 'fixture.txt'
        target.write_bytes(b'EXISTING\r\n')
        with self.assertRaises(HTTPException) as caught:
            self.save(target, 'EXISTING\n', create_only=True)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(target.read_bytes(), b'EXISTING\r\n')

    def test_original_retention_checks_happen_before_same_text_noop(self):
        target = self.drive / 'Documents/Drive_Intake/Fixture/Originals/fixture.txt'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'ORIGINAL\r\n')
        with self.assertRaises(HTTPException) as caught:
            self.save(target, 'ORIGINAL\n')
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(target.read_bytes(), b'ORIGINAL\r\n')

    def test_save_rejects_binary_and_outside_paths_before_writes(self):
        for target, status in ((self.drive / 'fixture.docx', 415), (self.drive.parent / 'outside.txt', 403)):
            with self.assertRaises(HTTPException) as caught:
                self.save(target, 'new')
            self.assertEqual(caught.exception.status_code, status)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
