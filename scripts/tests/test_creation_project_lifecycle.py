"""Actual route/helper bodies with an isolated synthetic project store.

No application import, real manuscript, process, model, or network request.
"""
import ast
import hashlib
import json
import os
import sys
from pathlib import Path
import tempfile
import threading
from datetime import datetime
from types import SimpleNamespace
from typing import Optional
import unittest
from unittest.mock import Mock, patch
import uuid

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class ProjectLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'projects'
        self.root.mkdir()
        self.project = self.root / 'Synthetic Fixture'
        self.project.mkdir()
        self.script = self.project / 'screenplay.fountain'
        self.script.write_bytes(b'Title: Fixture\r\n\r\nINT. LAB - DAY\r\nAn original.\r\n')
        self.scope = dict(Path=Path, HTTPException=HTTPException, hashlib=hashlib,
                          json=json, os=os, tempfile=tempfile, datetime=datetime,
                          Optional=Optional, uuid=uuid, SCREENPLAY_ROOT=self.root,
                          _PROJECT_STORE_LOCK=threading.RLock(),
                          _current_project=self.project.name, ADAPTATION_TASKS={})
        for name in ('SwitchProjectPayload', 'RestoreProjectPayload', 'WriteScreenplayPayload',
                     'BranchCreatePayload', 'BranchSwitchPayload', 'WorkflowRecoveryPayload',
                     'SprintStartPayload', 'SprintEndPayload'):
            self.scope[name] = object
        names = {'_project_directory', '_existing_project_directory', '_atomic_project_text',
                 '_screenplay_snapshot', '_require_screenplay_revision', '_require_idle_adaptation',
                 '_write_screenplay', 'read_screenplay', 'write_screenplay', '_archive_entry',
                 'delete_project', 'list_project_archives', 'restore_project', 'switch_project',
                 '_workflow_call', '_workflow_project', 'recover_workflow', 'switch_branch',
                 'list_branches', 'create_branch', 'list_sprints', 'start_sprint', 'end_sprint'}
        tree = ast.parse((ROOT / 'backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
        bodies = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        for node in bodies:
            node.decorator_list = []
        exec(compile(ast.Module(body=bodies, type_ignores=[]), '<actual-project-functions>', 'exec'), self.scope)

    def digest_map(self, directory):
        return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in directory.rglob('*') if path.is_file()}

    def test_save_then_fresh_read_uses_acknowledged_revision_and_preserves_other_project(self):
        other = self.root / 'Other'
        other.mkdir()
        (other / 'screenplay.fountain').write_bytes(b'OTHER\r\n')
        loaded = self.scope['read_screenplay'](self.project.name)
        result = self.scope['write_screenplay'](SimpleNamespace(
            project_name=self.project.name, content='INT. LAB - DAY\nAn edit.\n',
            expected_revision=loaded['revision'], preserve_unchanged_bytes=True))
        reloaded = self.scope['read_screenplay'](self.project.name)
        self.assertEqual(reloaded['content'], 'INT. LAB - DAY\nAn edit.\n')
        self.assertEqual(reloaded['revision'], result['revision'])
        self.assertNotEqual(result['revision'], loaded['revision'])
        self.assertEqual((other / 'screenplay.fountain').read_bytes(), b'OTHER\r\n')

    def test_missing_revision_and_stale_revision_leave_exact_source(self):
        before = self.script.read_bytes()
        for revision, status in [(None, 428), ('stale', 409)]:
            with self.assertRaises(HTTPException) as caught:
                self.scope['write_screenplay'](SimpleNamespace(
                    project_name=self.project.name, content='replacement',
                    expected_revision=revision, preserve_unchanged_bytes=True))
            self.assertEqual(caught.exception.status_code, status)
            self.assertEqual(self.script.read_bytes(), before)

    def test_failed_atomic_promotion_leaves_original_and_no_partial_canonical_file(self):
        before = self.script.read_bytes()
        with patch.object(os, 'replace', side_effect=PermissionError('synthetic refusal')):
            with self.assertRaises(PermissionError):
                self.scope['_atomic_project_text'](self.project, 'screenplay.fountain', b'NEW')
        self.assertEqual(self.script.read_bytes(), before)
        self.assertEqual(list(self.project.glob('.project-*.tmp')), [])

    def test_legacy_adaptation_read_does_not_create_or_rewrite_canonical_source(self):
        legacy = self.root / 'Legacy'
        legacy.mkdir()
        raw = b'INT. LEGACY\r\nText\r\n'
        (legacy / 'adaptation_output.fountain').write_bytes(raw)
        loaded = self.scope['read_screenplay']('Legacy')
        self.assertEqual(loaded['content'].encode(), raw)
        self.assertTrue(loaded['revision'].startswith('adaptation:'))
        self.assertFalse((legacy / 'screenplay.fountain').exists())

    def test_archive_list_restore_roundtrip_retains_manuscript_assets_and_history_bytes(self):
        (self.project / '.git').mkdir()
        (self.project / '.git' / 'fixture-history').write_bytes(b'opaque synthetic history\x00')
        (self.project / 'asset.bin').write_bytes(bytes(range(256)))
        before = self.digest_map(self.project)
        archived = self.scope['delete_project'](SimpleNamespace(project_name=self.project.name))
        self.assertFalse(self.project.exists())
        listing = self.scope['list_project_archives']()['archives']
        self.assertEqual([item['archive_id'] for item in listing], [archived['archive_id']])
        restored = self.scope['restore_project'](SimpleNamespace(archive_id=archived['archive_id']))
        self.assertEqual(restored['current'], self.project.name)
        self.assertEqual(self.digest_map(self.project), before)
        self.assertEqual(self.scope['list_project_archives']()['archives'], [])
        self.assertTrue((self.root.parent / 'screenplay_archive' / archived['archive_id'] / 'archive.json').exists())

    def test_restore_collision_does_not_overwrite_either_version(self):
        original = self.script.read_bytes()
        archived = self.scope['delete_project'](SimpleNamespace(project_name=self.project.name))
        self.project.mkdir()
        self.script.write_bytes(b'NEW PROJECT')
        with self.assertRaises(HTTPException) as caught:
            self.scope['restore_project'](SimpleNamespace(archive_id=archived['archive_id']))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.script.read_bytes(), b'NEW PROJECT')
        entry = self.scope['_archive_entry'](archived['archive_id'])
        self.assertEqual((entry / 'project' / 'screenplay.fountain').read_bytes(), original)

    def test_archive_refuses_active_memory_and_persisted_adaptations_before_mutation(self):
        for state in ('queued', 'starting', 'running', 'canceling', 'cancelling', 'processing'):
            self.setUp()
            before = self.digest_map(self.project)
            self.scope['ADAPTATION_TASKS'] = {self.project.name.upper(): {'status': state}}
            with self.subTest(state=state, source='memory'):
                with self.assertRaises(HTTPException) as caught:
                    self.scope['delete_project'](SimpleNamespace(project_name=self.project.name))
                self.assertEqual(caught.exception.status_code, 409)
                self.assertEqual(self.digest_map(self.project), before)
        self.setUp()
        (self.project / 'adaptation_state.json').write_text(json.dumps({'status': 'running'}))
        with self.assertRaises(HTTPException) as caught:
            self.scope['delete_project'](SimpleNamespace(project_name=self.project.name))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertTrue(self.project.exists())
        self.assertFalse((self.root.parent / 'screenplay_archive').exists())

    def test_branch_and_sprint_routes_require_explicit_project_before_mutation(self):
        calls = [('list_branches', ()), ('create_branch', (SimpleNamespace(branch_name='alt'),)),
                 ('list_sprints', ()), ('start_sprint', (SimpleNamespace(name='Fixture', target_pages=10),)),
                 ('end_sprint', (SimpleNamespace(sprint_id='fake'),))]
        before = self.digest_map(self.project)
        for name, arguments in calls:
            with self.subTest(route=name):
                with self.assertRaises(HTTPException) as caught:
                    self.scope[name](*arguments)
                self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.digest_map(self.project), before)

    def workflow_payload(self, **values):
        state = self.scope['read_screenplay'](self.project.name)
        return SimpleNamespace(project_name=self.project.name, expected_revision=state['revision'],
                               expected_workflow_revision=state['workflow_revision'], **values)

    def test_actual_routes_create_write_switch_sprint_end_and_archive_restore(self):
        initial = self.script.read_bytes()
        self.scope['create_branch'](self.workflow_payload(branch_name='Alternative'))
        state = self.scope['list_branches'](self.project.name)
        self.assertEqual(state['branches'], ['main', 'Alternative'])
        self.scope['write_screenplay'](self.workflow_payload(content='MAIN\r\n', preserve_unchanged_bytes=False))
        self.scope['switch_branch'](self.workflow_payload(branch_name='Alternative'))
        self.assertEqual(self.script.read_bytes(), initial)
        self.scope['start_sprint'](self.workflow_payload(name='Synthetic sprint', target_pages=4))
        active = self.scope['list_sprints'](self.project.name)['active_sprint']
        self.scope['end_sprint'](self.workflow_payload(sprint_id=active['id']))
        before = self.digest_map(self.project)
        archive = self.scope['delete_project'](SimpleNamespace(project_name=self.project.name))
        self.scope['restore_project'](SimpleNamespace(archive_id=archive['archive_id']))
        self.assertEqual(self.digest_map(self.project), before)
        self.assertEqual(self.scope['list_sprints'](self.project.name)['sprints'][0]['status'], 'ENDED')

    def test_branch_epoch_is_required_even_when_content_hash_is_unchanged(self):
        stale = self.workflow_payload(content=self.script.read_text(), preserve_unchanged_bytes=True)
        self.scope['create_branch'](self.workflow_payload(branch_name='Alternative'))
        self.scope['switch_branch'](self.workflow_payload(branch_name='Alternative'))
        with self.assertRaises(HTTPException) as caught:
            self.scope['write_screenplay'](stale)
        self.assertEqual(caught.exception.status_code, 409)
        del stale.expected_workflow_revision
        with self.assertRaises(HTTPException) as caught:
            self.scope['write_screenplay'](stale)
        self.assertEqual(caught.exception.status_code, 428)

    def test_pending_operation_blocks_archive_and_unrelated_edits(self):
        self.scope['create_branch'](self.workflow_payload(branch_name='Alternative'))
        before = self.script.read_bytes()
        with patch.dict(self.scope, _atomic_project_text=Mock(side_effect=OSError('synthetic interruption'))):
            with self.assertRaises(OSError):
                self.scope['write_screenplay'](self.workflow_payload(content='TARGET', preserve_unchanged_bytes=False))
        pending = self.scope['list_branches'](self.project.name)['pending_operation']
        with self.assertRaises(HTTPException) as caught:
            self.scope['delete_project'](SimpleNamespace(project_name=self.project.name))
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.script.read_bytes(), before)
        self.scope['recover_workflow'](SimpleNamespace(project_name=self.project.name,
                                                     operation_id=pending['id'], action='abort'))
        self.assertIsNone(self.scope['list_branches'](self.project.name)['pending_operation'])


if __name__ == '__main__':
    unittest.main()
