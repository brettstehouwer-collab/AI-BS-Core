"""No-GPU guards and early-dispatch checks for frozen two-process placement proof."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from native_studio import placement_release_smoke as smoke

ROOT = Path(__file__).resolve().parents[2]


class PlacementReleaseSmokeTests(unittest.TestCase):
    def test_create_rejects_source_execution_without_starting_children_or_services(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'create.json'
            with patch.object(sys, 'frozen', False, create=True):
                self.assertEqual(smoke.run_placement_release_smoke(report), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['phase'], 'create')
            self.assertIn('frozen bundle', data['error'])
            self.assertFalse(data['application_services_started'])
            self.assertFalse(data['actual_model_inference'])
            self.assertFalse(data['model_downloads_started'])
            self.assertEqual(data['observed_process_ids'], {})

    def test_reopen_rejects_source_execution_before_accessing_a_project(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'reopen.json'
            with patch.object(sys, 'frozen', False, create=True):
                self.assertEqual(smoke.run_placement_reopen_smoke(report, Path(directory) / 'missing-create.json'), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['phase'], 'reopen')
            self.assertIn('frozen bundle', data['error'])
            self.assertEqual(data['observed_process_ids'], {})

    def test_missing_bundled_host_is_rejected_without_source_sdk_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle'
            bundle.mkdir()
            report = Path(directory) / 'missing.json'
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(bundle), create=True), \
                    patch.object(smoke, '__file__', str(bundle / 'native_studio/placement_release_smoke.py')):
                self.assertEqual(smoke.run_placement_release_smoke(report), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('aibs_content_host.exe', data['error'])
            self.assertEqual(data['observed_process_ids'], {})

    def test_reopen_source_must_describe_an_owned_first_phase_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unowned = root / 'unowned'
            unowned.mkdir()
            sentinel = unowned / 'retained.txt'
            sentinel.write_text('Do not rename or modify this folder', encoding='utf-8')
            report = root / 'create.json'
            report.write_text(json.dumps({'schema_version': 1, 'kind': 'frozen_placement_two_process',
                'status': 'passed', 'phase': 'create', 'frozen': True,
                'all_owned_processes_joined': True, 'work_directory': str(unowned),
                'project_root': str(unowned / 'project')}), encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'owned|proof|source|Source'):
                smoke._load_source_report(report)
            self.assertEqual(sentinel.read_text(), 'Do not rename or modify this folder')

    def test_existing_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'existing.json'
            original = b'{"retained_evidence":true}\n'
            report.write_bytes(original)
            self.assertEqual(smoke.run_placement_release_smoke(report), 2)
            self.assertEqual(report.read_bytes(), original)

    def test_raw_traversal_is_rejected_before_absolute_can_normalize_it(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(Path, 'absolute', return_value=Path(directory)):
                with self.assertRaisesRegex(RuntimeError, 'traversal'):
                    smoke._plain(Path('child/../safe'), exists=False)

    def test_owned_missing_pack_is_restored_even_when_the_wait_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            pack, held = Path(directory) / 'pack', Path(directory) / 'held'
            pack.mkdir(); (pack / 'retained.txt').write_bytes(b'immutable input')
            callbacks = []
            signal = SimpleNamespace(connect=callbacks.append, disconnect=callbacks.remove)
            play = SimpleNamespace(message=signal, state='closed', dependency_process_id=0, process_id=0)
            chapter = SimpleNamespace(play=play, start_play=lambda: None)
            session = SimpleNamespace(chapter=chapter, wait=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('injected wait failure')))
            data = {'metrics': {}}
            with self.assertRaisesRegex(RuntimeError, 'injected wait failure'):
                smoke._missing_dependency_probe(session, data, pack, held)
            self.assertEqual((pack / 'retained.txt').read_bytes(), b'immutable input')
            self.assertFalse(held.exists()); self.assertEqual(callbacks, [])
            self.assertTrue(data['missing_dependency_restored'])

    def test_missing_pack_probe_waits_for_pending_export_before_accepting_closed_play(self):
        with tempfile.TemporaryDirectory() as directory:
            pack, held = Path(directory) / 'pack', Path(directory) / 'held'
            pack.mkdir(); (pack / 'retained.txt').write_bytes(b'immutable input')
            callbacks = []
            signal = SimpleNamespace(connect=callbacks.append, disconnect=callbacks.remove)
            play = SimpleNamespace(message=signal, state='closed', dependency_process_id=0, process_id=0)
            chapter = SimpleNamespace(play=play, busy=False)
            chapter.start_play = lambda: setattr(chapter, 'busy', True)
            def wait(predicate, *args, **kwargs):
                self.assertFalse(predicate(), 'The still-pending chapter export must prevent premature acceptance')
                chapter.busy = False
                for callback in callbacks: callback('Asset dependency staging failed: missing immutable pack')
                self.assertTrue(predicate())
            session = SimpleNamespace(chapter=chapter, wait=wait, observe=lambda: None)
            data = {'metrics': {}}
            smoke._missing_dependency_probe(session, data, pack, held)
            self.assertTrue(data['metrics']['missing_dependency_rejected_before_player'])
            self.assertTrue(pack.exists()); self.assertFalse(held.exists())

    def test_failed_setup_and_cleanup_still_preserve_a_failed_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'failed-cleanup.json'
            session = SimpleNamespace(setup=lambda: (_ for _ in ()).throw(RuntimeError('setup failed')),
                close=lambda: (_ for _ in ()).throw(RuntimeError('cleanup failed')))
            with patch.object(smoke, '_bundle_inputs', return_value=(Path(directory), Path(directory))), \
                    patch.object(smoke, '_Session', return_value=session):
                self.assertEqual(smoke.run_placement_release_smoke(report), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'failed')
            self.assertEqual(data['error'], 'setup failed')
            self.assertIn('cleanup failed', data['cleanup_errors'])
            self.assertFalse(data['all_owned_processes_joined'])

    def test_both_flags_dispatch_before_normal_views_or_service_imports(self):
        script = '''import builtins,runpy,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name in ('native_studio.executive_cockpit_full','backend.daemon_manager','backend.zombie_node_cleaner'):
        raise RuntimeError('Normal application import reached: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=guarded
sys.argv=[sys.argv[1],*sys.argv[2:]]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        with tempfile.TemporaryDirectory() as directory:
            for flag in ('--placement-release-smoke', '--placement-reopen-smoke'):
                report = Path(directory) / (flag[2:] + '.json')
                arguments = [flag, str(report)]
                if flag == '--placement-reopen-smoke':
                    arguments += ['--placement-source-report', str(Path(directory) / 'missing-create.json')]
                completed = subprocess.run([sys.executable, '-c', script, str(ROOT / 'native_studio/app.py'), *arguments],
                    cwd=ROOT, capture_output=True, text=True, timeout=20)
                self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
                data = json.loads(report.read_text(encoding='utf-8'))
                self.assertIn('frozen bundle', data['error'])
                self.assertFalse(data['application_services_started'])


if __name__ == '__main__':
    unittest.main()
