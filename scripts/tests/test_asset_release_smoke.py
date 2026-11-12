"""Frozen asset acceptance guards and coordinated real-native bundle fixture."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import contextmanager

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from native_studio import asset_release_smoke as smoke

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = Path(os.environ.get('AIBS_ASSET_SMOKE_REFERENCE',
    str(ROOT / 'engine/assets/cooked/motherboard-reference')))
BINARIES = Path(os.environ.get('AIBS_ASSET_SMOKE_BIN',
    str(ROOT / 'engine/out/windows-msvc/Release')))


@contextmanager
def _fixture_directory():
    retained = os.environ.get('AIBS_ASSET_SMOKE_ARTIFACTS')
    if retained:
        root = Path(retained).resolve()
        root.mkdir(parents=True, exist_ok=False)
        yield str(root)
    else:
        with tempfile.TemporaryDirectory(prefix='aibs-asset-smoke-fixture-') as directory:
            yield directory


class AssetReleaseSmokeTests(unittest.TestCase):
    def test_source_invocation_fails_without_fallback_or_services(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'source.json'
            with patch.object(sys, 'frozen', False, create=True):
                self.assertEqual(smoke.run_asset_release_smoke(report), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('frozen bundle', data['error'])
            self.assertFalse(data['application_services_started'])
            self.assertFalse(data['actual_model_inference'])
            self.assertFalse(data['source_fallback'])
            self.assertEqual(data['observed_process_ids'], {})

    def test_missing_bundled_binary_fails_instead_of_using_checkout_sdk(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle'
            bundle.mkdir()
            report = Path(directory) / 'missing.json'
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(bundle), create=True), patch.object(smoke, '__file__', str(bundle / 'native_studio/asset_release_smoke.py')):
                self.assertEqual(smoke.run_asset_release_smoke(report), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('aibs_assetc.exe', data['error'])
            self.assertEqual(data['observed_process_ids'], {})
            self.assertFalse(data['application_services_started'])

    def test_native_gpu_receipt_requires_geometry_material_pixels_and_identity(self):
        proof = {'status': 'passed', 'asset_id': smoke.REFERENCE_ASSET_ID, 'triangles': 4788,
            'materials': 8, 'source_fallback': False, 'save_formats_changed': False,
            'metrics': {'debug_errors': 0, 'debug_layer': True, 'nonbackground_pixels': 20000,
                'asset_gpu_bytes_changed': 200, 'material_gpu_bytes_changed': 200,
                'camera_input_verified': True}}
        smoke._validate_native_proof(proof)
        for key, value in (('material_gpu_bytes_changed', 0), ('asset_gpu_bytes_changed', 0),
                           ('debug_errors', 1), ('camera_input_verified', False)):
            with self.subTest(key=key):
                damaged = dict(proof, metrics=dict(proof['metrics'], **{key: value}))
                with self.assertRaises(RuntimeError):
                    smoke._validate_native_proof(damaged)

    def test_redirected_bundle_executable_is_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            binary = bundle / 'game_assets/player'
            binary.mkdir(parents=True)
            external = root / 'outside.exe'
            external.write_bytes(b'Never execute this fixture')
            try:
                (binary / 'aibs_assetc.exe').symlink_to(external)
            except OSError as error:
                self.skipTest('Symlink creation unavailable: ' + str(error))
            report = root / 'redirected.json'
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(bundle), create=True), patch.object(smoke, '__file__', str(bundle / 'native_studio/asset_release_smoke.py')):
                self.assertEqual(smoke.run_asset_release_smoke(report), 2)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('Redirected', data['error'])
            self.assertEqual(data['observed_process_ids'], {})

    def test_asset_flag_dispatches_before_normal_application_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'early.json'
            script = '''import builtins,runpy,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name in ('native_studio.executive_cockpit_full','backend.daemon_manager','backend.zombie_node_cleaner'):
        raise RuntimeError('Normal application import reached: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=guarded
sys.argv=[sys.argv[1],'--asset-release-smoke',sys.argv[2]]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
            process = subprocess.run([sys.executable, '-c', script, str(ROOT / 'native_studio/app.py'), str(report)],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertIn('frozen bundle', data['error'])
            self.assertFalse(data['application_services_started'])

    @unittest.skipUnless(os.environ.get('AIBS_RUN_ASSET_RELEASE_GPU') == '1'
        and (BINARIES / 'aibs_assetc.exe').is_file() and (REFERENCE / 'catalog.aibcat').is_file(),
        'Real native bundle fixture requires the coordinated GPU slot and cooked sample')
    def test_actual_workspace_cook_inspect_owned_preview_and_native_gpu_fixture(self):
        with _fixture_directory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            player = bundle / 'game_assets/player'
            (player / 'shaders').mkdir(parents=True)
            for name in ('aibs_assetc.exe', 'aibs_motherboard.exe', 'aibs_capabilities.json'):
                shutil.copy2(BINARIES / name, player / name)
            for name in ('motherboard.vs.cso', 'motherboard.ps.cso'):
                shutil.copy2(BINARIES / 'shaders' / name, player / 'shaders' / name)
            shutil.copytree(REFERENCE, bundle / 'game_assets/reference_part')
            playground = bundle / 'game_assets/playground/index.html'
            playground.parent.mkdir(parents=True)
            playground.write_text('<html>Fixture only</html>', encoding='utf-8')
            report = root / 'assets.json'
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(bundle), create=True), patch.object(smoke, '__file__', str(bundle / 'native_studio/asset_release_smoke.py')):
                self.assertEqual(smoke.run_asset_release_smoke(report), 0,
                    report.read_text(encoding='utf-8') if report.exists() else 'No smoke report')
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertTrue(data['all_owned_processes_joined'])
            self.assertFalse(data['source_fallback'])
            self.assertFalse(data['actual_model_inference'])
            self.assertTrue(data['metrics']['input_bytes_unchanged'])
            self.assertTrue(data['metrics']['cooked_bytes_unchanged'])
            self.assertTrue(data['metrics']['bundled_sample_bytes_unchanged'])
            self.assertEqual(data['metrics']['reference_asset']['triangles'], 4788)
            self.assertEqual(data['metrics']['reference_asset']['materials'], 8)
            self.assertEqual(data['metrics']['native_gpu']['status'], 'passed')
            for path in data['native_executables'].values():
                self.assertTrue(Path(path).is_relative_to(player))
            for path in data['captures'].values():
                self.assertTrue(Path(path).is_file(), path)


if __name__ == '__main__':
    unittest.main()
