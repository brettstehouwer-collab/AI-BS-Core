import json
import os
from pathlib import Path
import tempfile
import unittest
import shutil
import sys
import subprocess
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from native_studio.game_release_smoke import run_game_release_smoke
from native_studio import game_release_smoke


class GameReleaseSmokeTests(unittest.TestCase):
    def test_real_native_game_workspace_can_render_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'native-smoke.json'
            self.assertEqual(run_game_release_smoke(report), 0)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'passed')
            self.assertTrue(data['playground_available'])
            self.assertTrue(report.with_suffix('.png').is_file())

    def test_creator_smoke_rejects_source_fallback_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'creator.json'
            with patch.object(sys, 'frozen', False, create=True):
                self.assertEqual(game_release_smoke.run_creator_release_smoke(report), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('frozen bundle', data['error'])
            self.assertFalse(data['application_services_started'])
            self.assertFalse(data['actual_model_inference'])

    def test_creator_smoke_runs_real_bundled_hosts_qtnetwork_fixture_and_owned_children(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            bundle = target / 'bundle'
            player = bundle / 'game_assets/player'
            shutil.copytree(root / 'engine/install/release/bin', player)
            playground = bundle / 'game_assets/playground/index.html'
            playground.parent.mkdir(parents=True)
            playground.write_text('<html>Bundled fixture playground</html>', encoding='utf-8')
            report = target / 'creator.json'
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(bundle), create=True):
                self.assertEqual(game_release_smoke.run_creator_release_smoke(report), 0,
                    report.read_text(encoding='utf-8') if report.exists() else 'No report')
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'passed')
            self.assertEqual(data['provider_origin'], 'deterministic_loopback_http_fixture')
            self.assertFalse(data['actual_model_inference'])
            self.assertTrue(data['fixture_thread_joined'])
            self.assertEqual(data['http_paths'], ['/api/tags', '/api/show', '/api/chat'])
            self.assertTrue(data['all_owned_processes_joined'])
            self.assertTrue(data['play_scratch_removed'])
            self.assertEqual(set(data['native_executables']), {'numeric_host', 'content_host', 'numeric_viewport', 'chapter_viewport', 'chapter_player'})
            for path in data['native_executables'].values():
                self.assertTrue(Path(path).is_relative_to(player))
            self.assertTrue(data['metrics']['numeric_preview_private'])
            self.assertTrue(data['metrics']['typed_preview_private'])
            self.assertTrue(data['metrics']['ai_preview_private'])
            self.assertTrue(data['metrics']['saved_reopen_matches'])
            self.assertEqual(data['metrics']['typed_fields_verified'], ['number', 'text', 'boolean'])
            self.assertEqual(data['metrics']['play_stop']['graceful'], True)
            self.assertEqual(data['metrics']['play_stop']['saved'], True)
            for path in data['captures'].values():
                self.assertTrue(Path(path).is_file(), path)

    def test_explicit_live_provider_requires_explicit_model_without_starting_a_service(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'creator.json'
            self.assertEqual(game_release_smoke.run_creator_release_smoke(report, provider='ollama'), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('explicit model', data['error'])
            self.assertFalse(data['application_services_started'])
            self.assertFalse(data['actual_model_inference'])

    def test_smoke_cli_dispatches_before_normal_application_view_or_service_imports(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'early.json'
            script = '''import builtins, runpy, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name in ('native_studio.executive_cockpit_full', 'backend.daemon_manager',
                'backend.zombie_node_cleaner'):
        raise RuntimeError('Normal application import reached: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
sys.argv = [sys.argv[1], '--creator-release-smoke', sys.argv[2]]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
            completed = subprocess.run([sys.executable, '-c', script,
                str(root / 'native_studio/app.py'), str(report)], cwd=root,
                capture_output=True, text=True, timeout=20)
            self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('frozen bundle', data['error'])
            self.assertFalse(data['application_services_started'])


if __name__ == '__main__':
    unittest.main()
