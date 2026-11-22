"""Offline regressions: actual writer methods/routes, disposable sources only."""
import ast
import asyncio
import contextlib
import dataclasses
from datetime import datetime
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import types
from typing import Any, Dict, List, Optional
import unittest
from unittest.mock import patch
import uuid

from fastapi import BackgroundTasks, HTTPException, UploadFile

ROOT = Path(os.environ.get('AIBS_TEST_ROOT', r'C:\AI-BS'))
sys.path.insert(0, str(ROOT / 'backend'))


def extract_functions(path, names, scope):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            found.append(node)
    if {node.name for node in found} != set(names):
        raise AssertionError('Requested actual implementation not found')
    exec(compile(ast.Module(body=found, type_ignores=[]), str(path), 'exec'), scope)
    return scope


def parser_module():
    scope = dict(Path=Path, dataclass=dataclasses.dataclass, datetime=datetime,
                 json=json, html=html, re=re, subprocess=subprocess, BytesIO=io.BytesIO,
                 Optional=Optional, Dict=Dict, List=List, Any=Any)
    tree = ast.parse((ROOT / 'backend/core/matrix_docs.py').read_text(encoding='utf-8'))
    names = {'FountainElement', 'FountainParser', 'ScreenplayProject'}
    exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node, ast.ClassDef)
                                 and node.name in names], type_ignores=[]),
                 '<actual-matrix-classes>', 'exec'), scope)
    module = types.ModuleType('core.matrix_docs')
    module.FountainParser = scope['FountainParser']
    module.ScreenplayProject = scope['ScreenplayProject']
    return module


class Label:
    def __init__(self, value=''):
        self.value = value
    def setText(self, value):
        self.value = value


class SceneList:
    def __init__(self):
        self.items = []
    def clear(self):
        self.items.clear()
    def addItem(self, item):
        self.items.append(item)


class NativeAdaptationTests(unittest.TestCase):
    def poll(self, state):
        errors, loaded, statuses = [], [], []
        timer = types.SimpleNamespace(stop=lambda: setattr(timer, 'stopped', True), stopped=False)
        result = {'job_id': 'a' * 32, 'status': state, 'progress': 100}
        view = types.SimpleNamespace(
            _writer_busy=False, _adapt_job={'project': 'Synthetic', 'job_id': 'a' * 32},
            _adapt_timer=timer, _writer_error=errors.append, _writer_status=statuses.append,
            _writer_client=types.SimpleNamespace(adaptation_status=lambda project: result),
            _flush_native_transition=lambda callback: callback(),
            _read_native_project=loaded.append)
        view._native_io = lambda work, success, failure=None: success(work())
        scope = extract_functions('native_studio/screenwriting_view.py', {'_poll_native_adaptation'}, {})
        scope['_poll_native_adaptation'](view)
        return view, errors, loaded

    def test_worker_complete_stops_monitoring_and_opens_converted_project(self):
        view, errors, loaded = self.poll('complete')
        self.assertTrue(view._adapt_timer.stopped)
        self.assertIsNone(view._adapt_job)
        self.assertEqual(loaded, ['Synthetic'])
        self.assertEqual(errors, [])

    def test_interrupted_worker_stops_without_loading_an_incomplete_project(self):
        view, errors, loaded = self.poll('interrupted')
        self.assertTrue(view._adapt_timer.stopped)
        self.assertIsNone(view._adapt_job)
        self.assertEqual(loaded, [])
        self.assertEqual(len(errors), 1)
        self.assertIn('retained', errors[0].lower())

    def metrics(self, content):
        view = types.SimpleNamespace(
            editor=types.SimpleNamespace(toPlainText=lambda: content),
            _current_page=1, _current_project='Synthetic',
            lbl_telemetry=Label(), lbl_page_count=Label(), lbl_scenes_title=Label('SCENES (272)'),
            scene_list=SceneList(), beat_board=types.SimpleNamespace(populate_beats=lambda beats: None))
        scope = extract_functions('native_studio/screenwriting_view.py', {'_parse_scenes_and_metrics'},
                                  {'math': math, 're': re, 'QListWidgetItem': lambda value: value})
        scope['_parse_scenes_and_metrics'](view)
        return view

    def test_unstructured_import_does_not_invent_sample_scenes_or_beats(self):
        view = self.metrics('A prose manuscript without any screenplay headings.')
        self.assertEqual(view._parsed_beats, [])
        self.assertEqual(view.scene_list.items, [])
        self.assertIn('SCENES (0)', view.lbl_scenes_title.value)

    def test_scene_heading_matches_actual_parsed_scene_count(self):
        view = self.metrics('INT. LAB - DAY\nA fixture.\n\nEXT. LAKE - NIGHT\nAnother fixture.')
        self.assertEqual(len(view._parsed_beats), 2)
        self.assertEqual(len(view.scene_list.items), 2)
        self.assertIn('SCENES (2)', view.lbl_scenes_title.value)
        self.assertIn('2 Scenes', view.lbl_telemetry.value)


class PdfImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aibs-pdf-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'projects'
        self.root.mkdir()
        self.module = parser_module()

    def make_pdf(self):
        import fitz
        source = self.base / 'synthetic.pdf'
        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((72, 72), 'A synthetic manuscript for offline adaptation.')
            document.save(source)
        return source

    def test_actual_pdf_extractor_reads_synthetic_pdf_and_preserves_source(self):
        import fitz
        source = self.make_pdf()
        before = source.read_bytes()
        scope = extract_functions('backend/core/ai_adapter.py', {'_extract_text_from_file'},
                                  {'Path': Path, 'fitz': fitz})
        extracted = scope['_extract_text_from_file'](source)
        self.assertIn('A synthetic manuscript', extracted)
        self.assertEqual(source.read_bytes(), before)

    def test_actual_upload_route_queues_pdf_with_retained_source(self):
        from core import adaptation_store
        source = self.make_pdf()
        original = source.read_bytes()
        previous = (adaptation_store._root_provider, adaptation_store._store_mutex,
                    adaptation_store._parser_factory, dict(adaptation_store.ADAPTATION_TASKS))
        self.addCleanup(lambda: adaptation_store.configure_adaptation_store(*previous[:3]))
        self.addCleanup(lambda: (adaptation_store.ADAPTATION_TASKS.clear(),
                                 adaptation_store.ADAPTATION_TASKS.update(previous[3])))
        adaptation_store.configure_adaptation_store(lambda: self.root, threading.RLock(),
                                                   self.module.FountainParser)
        async def background_worker(*args):
            raise AssertionError('Queued background worker must not execute in admission test')
        scope = dict(Path=Path, BackgroundTasks=BackgroundTasks, UploadFile=UploadFile,
                     File=lambda *args, **kwargs: None, Form=lambda *args, **kwargs: None,
                     _adaptation_directory=adaptation_store.project_directory,
                     reserve_adaptation=adaptation_store.reserve_adaptation,
                     cancel_adaptation=adaptation_store.cancel_adaptation,
                     adapt_book_to_screenplay=background_worker)
        extract_functions('backend/routers/screenwriting_router.py',
                          {'_reserved_adaptation_response', 'start_book_adaptation'}, scope)
        tasks = BackgroundTasks()
        memory_file = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
        self.addCleanup(memory_file.close)
        memory_file.write(original)
        memory_file.seek(0)
        upload = UploadFile(filename='synthetic.pdf', file=memory_file)
        with patch.object(adaptation_store, '_git_checkpoint',
                          side_effect=RuntimeError('synthetic optional checkpoint unavailable')):
            request = scope['start_book_adaptation'](
                tasks, upload, 'New Adaptation', 'Feature Film', 'Fiction Narrative', False)
            try:
                request.send(None)
            except StopIteration as complete:
                result = complete.value
            else:
                request.close()
                self.fail('Offline upload admission unexpectedly requested an event loop')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['contract'], 'create-only-v1')
        self.assertEqual(result['task']['status'], 'queued')
        self.assertEqual(len(tasks.tasks), 1)
        retained = self.root / 'New Adaptation' / result['task']['source_path']
        self.assertEqual(retained.read_bytes(), original)
        self.assertEqual(result['task']['source_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(source.read_bytes(), original)

    def import_scope(self):
        scope = dict(Path=Path, HTTPException=HTTPException, ImportProjectPayload=object,
                     _PROJECT_STORE_LOCK=threading.RLock(), SCREENPLAY_ROOT=self.root,
                     tempfile=tempfile, os=os, json=json, shutil=shutil, uuid=uuid,
                     datetime=datetime, subprocess=subprocess,
                     _project_directory=lambda name: self.root / name)
        extract_functions('backend/routers/screenwriting_router.py',
                          {'do_import_project', '_atomic_project_text', '_write_project_metadata'}, scope)
        return scope

    def test_duplicate_import_refuses_without_changing_existing_files(self):
        existing = self.root / 'Existing'
        existing.mkdir()
        original = existing / 'screenplay.fountain'
        original.write_bytes(b'ORIGINAL\r\n')
        scope = self.import_scope()
        with patch.dict(sys.modules, {'core.matrix_docs': self.module}):
            with self.assertRaises(HTTPException) as error:
                scope['do_import_project'](types.SimpleNamespace(project_name='Existing', content='replacement'))
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(original.read_bytes(), b'ORIGINAL\r\n')
        self.assertFalse((self.base / 'saved_data').exists())

    def test_failed_import_retains_prepared_bytes_outside_catalog(self):
        scope = self.import_scope()
        atomic = scope['_atomic_project_text']
        content = 'INT. LAB - DAY\r\nSynthetic partial preparation.\r\n'
        def interrupted(directory, name, raw):
            if name == 'project.json':
                raise OSError('Synthetic metadata storage failure')
            return atomic(directory, name, raw)
        with patch.dict(sys.modules, {'core.matrix_docs': self.module}), \
                patch.dict(scope, {'_atomic_project_text': interrupted}):
            with self.assertRaises(HTTPException) as error:
                scope['do_import_project'](types.SimpleNamespace(project_name='Failed Fixture', content=content))
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(list(self.root.iterdir()), [])
        retained = list((self.base / 'saved_data/screenplay_import_recovery').rglob('screenplay.fountain'))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_bytes(), content.encode('utf-8'))

    def test_linked_recovery_ancestor_is_refused_before_source_write(self):
        from core import adaptation_store
        linked_ancestor = self.base / 'saved_data'
        linked_ancestor.mkdir()
        existing = self.root / 'Existing'
        existing.mkdir()
        original = existing / 'screenplay.fountain'
        original.write_bytes(b'ORIGINAL\r\n')
        scope = self.import_scope()
        original_junction = Path.is_junction
        def junction(path):
            return path == linked_ancestor or original_junction(path)
        with patch.dict(sys.modules, {'core.matrix_docs': self.module}), \
                patch.object(Path, 'is_junction', junction), \
                patch.object(adaptation_store, '_git_checkpoint', side_effect=RuntimeError('synthetic checkpoint unavailable')), \
                patch.dict(scope, {'_atomic_project_text': lambda *args: self.fail('Linked recovery ancestor must refuse before manuscript write')}):
            with self.assertRaises(HTTPException) as error:
                scope['do_import_project'](types.SimpleNamespace(project_name='Linked Fixture', content='new source'))
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(original.read_bytes(), b'ORIGINAL\r\n')
        self.assertEqual(list(linked_ancestor.iterdir()), [])
        self.assertFalse((self.root / 'Linked Fixture').exists())

    def test_recovery_parent_permission_failure_is_unavailable_without_publish(self):
        scope = self.import_scope()
        retained_root = self.base / 'saved_data/screenplay_import_recovery'
        original_mkdir = Path.mkdir
        def protected_parent(path, *args, **kwargs):
            if path == retained_root:
                raise PermissionError('Synthetic recovery parent permission denial')
            return original_mkdir(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', protected_parent):
            with self.assertRaises(HTTPException) as error:
                scope['do_import_project'](types.SimpleNamespace(project_name='Denied Fixture', content='new source'))
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_import_publishes_exact_text_even_when_optional_git_checkpoint_fails(self):
        from core import adaptation_store
        source = self.make_pdf()
        source_before = source.read_bytes()
        other = self.root / 'Existing'
        other.mkdir()
        existing = other / 'screenplay.fountain'
        existing.write_bytes(b'ORIGINAL\r\n')
        content = 'INT. LAB - DAY\r\nA synthetic PDF extraction.\r\n'
        scope = dict(Path=Path, HTTPException=HTTPException, ImportProjectPayload=object,
                     _PROJECT_STORE_LOCK=threading.RLock(), SCREENPLAY_ROOT=self.root,
                     tempfile=tempfile, os=os, json=json, shutil=shutil, uuid=uuid,
                     datetime=datetime, subprocess=subprocess,
                     _project_directory=lambda name: self.root / name)
        extract_functions('backend/routers/screenwriting_router.py',
                          {'do_import_project', '_atomic_project_text', '_write_project_metadata'}, scope)
        def legacy_git_failure(args, **kwargs):
            if 'add' in args:
                raise subprocess.CalledProcessError(128, args)
            return subprocess.CompletedProcess(args, 0, b'', b'')
        with patch.dict(sys.modules, {'core.matrix_docs': self.module}), \
                patch.object(adaptation_store, '_git_checkpoint', side_effect=RuntimeError('synthetic Git checkpoint failure')), \
                patch.object(subprocess, 'run', side_effect=legacy_git_failure), \
                contextlib.redirect_stdout(io.StringIO()):
            result = scope['do_import_project'](types.SimpleNamespace(project_name='Imported', content=content))
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['project'], 'Imported')
        self.assertEqual(result['git_status'], 'failed')
        self.assertEqual((self.root / 'Imported/screenplay.fountain').read_bytes(), content.encode('utf-8'))
        self.assertTrue((self.root / 'Imported/Imported.fdx').is_file())
        self.assertEqual(existing.read_bytes(), b'ORIGINAL\r\n')
        self.assertEqual(source.read_bytes(), source_before)


if __name__ == '__main__':
    unittest.main()
