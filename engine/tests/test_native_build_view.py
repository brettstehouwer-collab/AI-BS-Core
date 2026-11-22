import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.game_build_view import GameBuildNativeView, GAME_PROJECT_ROOT
from native_studio.game_build_monitor import read_build_progress
import native_studio.game_build_view as game_view
from native_studio.navigation_registry import get_all_subtabs_flat
from native_studio.theme import STYLESHEET


class NativeBuildViewTests(unittest.TestCase):
    def test_current_sdk_precedes_retained_sdk_and_bundle_stays_authoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for version in ('0.16.3','0.16.4','0.16.5','0.16.6','0.17.0','0.17.1','0.17.2'):
                binary=root/f'engine/install/{version}/runtime-release/bin';binary.mkdir(parents=True)
                for name in ('aibs_assetc.exe','aibs_motherboard.exe'):(binary/name).write_bytes(b'MZ fixture')
            with patch.object(game_view,'_bundle_root',return_value=None):
                expected=root/'engine/install/0.17.2/runtime-release/bin'
                self.assertEqual(game_view._native_player_path(root),expected/'aibs_motherboard.exe')
                self.assertEqual(game_view._asset_workspace_paths(root)[:2],(expected/'aibs_assetc.exe',expected/'aibs_motherboard.exe'))
            bundle=root/'frozen';binary=bundle/'game_assets/player';binary.mkdir(parents=True)
            (binary/'aibs_motherboard.exe').write_bytes(b'MZ bundled fixture')
            with patch.object(game_view,'_bundle_root',return_value=bundle):
                self.assertEqual(game_view._native_player_path(root),binary/'aibs_motherboard.exe')
                self.assertEqual(game_view._asset_workspace_paths(root)[:2],(binary/'aibs_assetc.exe',binary/'aibs_motherboard.exe'))

    def test_verified_development_asset_sdk_precedes_retained_legacy_sdk(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(game_view,'_bundle_root',return_value=None):
            root=Path(directory)
            for version in ('0.10.0','0.11.0'):
                binary=root/f'engine/install/{version}/release/bin';binary.mkdir(parents=True)
                for name in ('aibs_assetc.exe','aibs_motherboard.exe'):(binary/name).write_bytes(b'MZ fixture')
            cooker,player,_=game_view._asset_workspace_paths(root)
            self.assertEqual(cooker,root/'engine/install/0.11.0/release/bin/aibs_assetc.exe')
            self.assertEqual(player,cooker.with_name('aibs_motherboard.exe'))

    def test_persistent_placement_claim_uses_its_own_report_and_displays_limits(self):
        app=QApplication.instance() or QApplication([]);bus=EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);view=GameBuildNativeView(bus,root=root)
            try:
                view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('PERSISTENT ASSET PLACEMENT',text)
                self.assertIn('Persistent placement verification: not_run.',text)
                self.assertNotIn('Persistent chapter asset placements verified.',text)
                report=root/'engine/out/persistent_placement_verification.json';report.parent.mkdir(parents=True)
                fixture={'schema_version':1,'status':'passed','verified_at':'2026-11-02T01:00:00+00:00',
                    'sdk_version':'0.10.0','studio_version':'5.329.97',
                    'checks':['Explicit Preview, history and fresh-owner reopen'],
                    'limitations':['Presentation-only placements retain existing collision ownership'],
                    'proof_paths':['engine/out/placement-proof.json']}
                report.write_text(json.dumps(fixture),encoding='utf-8')
                view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('Persistent chapter asset placements verified.',text)
                for value in fixture['checks']+fixture['limitations']+fixture['proof_paths']+[fixture['verified_at'],'0.10.0','5.329.97',str(report)]:self.assertIn(value,text)
                self.assertIn('Asset pipeline verification: not_run.',text)
                report.write_text(json.dumps({**fixture,'status':'failed'}),encoding='utf-8')
                view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('Persistent placement verification: failed.',text)
                self.assertNotIn('Persistent chapter asset placements verified.',text)
            finally:view.close();bus.shutdown();app.processEvents()

    def test_asset_rendering_claim_requires_asset_report(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                self.assertIn('ASSET AND MATERIAL PIPELINE', view.details.toPlainText())
                self.assertNotIn('Cooked mesh/material rendering verified.', view.details.toPlainText())
                report = root / 'engine/out/asset_pipeline_verification.json'
                report.parent.mkdir(parents=True)
                report.write_text(json.dumps({'schema_version': 1, 'status': 'passed',
                    'completed_at': '2026-11-01T23:50:00+00:00',
                    'checks': ['Actual cooked geometry and named materials changed GPU pixels'],
                    'metrics': {'triangles': 4788, 'materials': 8}}), encoding='utf-8')
                view._render(read_build_progress(root))
                text = view.details.toPlainText()
                for value in ('Cooked mesh/material rendering verified.', '4788',
                              'Opaque base color and emission', 'Texture maps and PBR remain planned'):
                    self.assertIn(value, text)
            finally:
                view.close()
                bus.shutdown()
                app.processEvents()

    def test_assets_workspace_is_lazy_and_separate_from_chapter(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            view = GameBuildNativeView(bus, root=Path(directory))
            try:
                self.assertEqual(view.workspace_tabs.count(), 4)
                self.assertEqual(view.workspace_tabs.tabText(3), 'Assets')
                self.assertIsNone(view.asset_view)
                view.workspace_tabs.setCurrentIndex(3)
                self.assertIsNotNone(view.asset_view)
                self.assertIsNone(view.creator_view)
                self.assertIsNone(view.content_view)
                self.assertFalse(view.asset_view.busy)
                self.assertTrue(view.asset_view.status.text())
                self.assertEqual(view.asset_view.tool_process_id, 0)
                self.assertEqual(view.asset_view.preview_process_id, 0)
            finally:
                view.close()
                bus.shutdown()
                app.processEvents()

    def test_live_ai_authoring_claim_requires_its_own_report_and_keeps_field_boundaries(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                text = view.details.toPlainText()
                self.assertIn('LIVE LOCAL AI AUTHORING VERIFICATION', text)
                self.assertIn('AI authoring verification: not_run.', text)
                self.assertNotIn('Live selected-model inference and field proposals verified.', text)
                report = root / 'engine/out/ai_authoring_verification.json'
                report.parent.mkdir(parents=True)
                fixture = {'schema_version': 1, 'status': 'passed',
                    'completed_at': '2026-11-02T01:00:00+00:00',
                    'checks': ['Selected local model proposes a field edit for explicit native Preview and Apply'],
                    'metrics': {'selected_model': 'fixture:local', 'endpoint': 'http://127.0.0.1:11434',
                        'actual_model_runs': 1, 'python_tests': 152}}
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                text = view.details.toPlainText()
                self.assertIn('Live selected-model inference and field proposals verified.', text)
                self.assertIn('Live selected-model authoring evidence appears below; broader tools remain planned.', text)
                self.assertNotIn('Live model-provider inference and chapter viewport/Play integration remain unfinished.', text)
                self.assertIn('Native chapter preview/Play verification: not_run.', text)
                self.assertIn('Chapter creator verification: not_run.', text)
                for value in fixture['checks'] + [fixture['completed_at'], str(report), 'fixture:local',
                        'http://127.0.0.1:11434', 'actual_model_runs', 'python_tests']:
                    self.assertIn(value, text)
                for boundary in ('one selected installed local model', 'Exposed text, number and boolean fields only',
                        'explicit Apply', 'Save is separate', 'session metadata', 'durable provenance',
                        'original memories', 'generated wording is a draft'):
                    self.assertIn(boundary, text)
                play = report.with_name('chapter_play_verification.json')
                play.write_text(json.dumps({**fixture, 'checks': ['Pinned native Play proof']}), encoding='utf-8')
                for status in ('failed', 'unreadable'):
                    report.write_text(json.dumps({**fixture, 'status': 'failed'}) if status == 'failed'
                        else '{broken', encoding='utf-8')
                    view._render(read_build_progress(root))
                    text = view.details.toPlainText()
                    self.assertIn(f'AI authoring verification: {status}.', text)
                    self.assertNotIn('Live selected-model inference and field proposals verified.', text)
                    self.assertIn('Live model-provider inference remains unfinished;', text)
                    self.assertIn('Native chapter export/preview and isolated Play verified.', text)
            finally:
                view.close()
                bus.shutdown()

    def test_chapter_play_proof_controls_its_own_native_scope_without_claiming_inference(self):
        app=QApplication.instance() or QApplication([]);bus=EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);view=GameBuildNativeView(bus,root=root)
            try:
                view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('NATIVE CHAPTER EXPORT / PREVIEW / ISOLATED PLAY VERIFICATION',text)
                self.assertIn('Native chapter preview/Play verification: not_run.',text)
                self.assertIn('Live model-provider inference and chapter viewport/Play integration remain unfinished.',text)
                self.assertNotIn('Native chapter export/preview and isolated Play verified.',text)
                report=root/'engine/out/chapter_play_verification.json';report.parent.mkdir(parents=True)
                fixture={'schema_version':1,'status':'passed','completed_at':'2026-11-02T00:30:00+00:00',
                    'checks':['Actual typed native preview pixels and PICK','Stop joins native Play after its temporary save drain'],
                    'metrics':{'native_play':True,'temporary_play':True}}
                report.write_text(json.dumps(fixture),encoding='utf-8');view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('Native chapter export/preview and isolated Play verified.',text)
                self.assertIn('Live model-provider inference remains unfinished; native chapter preview/Play evidence appears below.',text)
                self.assertNotIn('Live model-provider inference and chapter viewport/Play integration remain unfinished.',text)
                self.assertIn('Test gameplay resets when Play stops; creator edits remain.',text)
                for value in fixture['checks']+[fixture['completed_at'],str(report)]:self.assertIn(value,text)
                self.assertIn('Native First Boot chapter verification: not_run.',text)
                self.assertNotIn('Native typed endpoint/client/GUI and proposal-job admission verified.',text)
                fixture['checks']=[];report.write_text(json.dumps(fixture),encoding='utf-8')
                view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('Native chapter preview/Play verification: unreadable.',text)
                self.assertNotIn('Native chapter export/preview and isolated Play verified.',text)
                self.assertIn('Live model-provider inference and chapter viewport/Play integration remain unfinished.',text)
            finally:
                view.close();bus.shutdown()

    def test_chapter_creator_report_displays_verified_scope_and_unfinished_boundaries(self):
        app=QApplication.instance() or QApplication([])
        bus=EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);view=GameBuildNativeView(bus,root=root)
            try:
                view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('CHAPTER CREATOR / PROPOSAL JOB VERIFICATION',text)
                self.assertIn('Chapter creator verification: not_run.',text)
                self.assertNotIn('Native typed endpoint/client/GUI and proposal-job admission verified.',text)
                report=root/'engine/out/chapter_creator_verification.json';report.parent.mkdir(parents=True)
                fixture={'schema_version':1,'status':'passed','completed_at':'2026-11-01T22:00:00+00:00',
                    'checks':['Actual native typed inspector edit/save/reopen','Scoped proposal Preview then explicit Apply'],
                    'metrics':{'widget_tests':5,'live_inference':False}}
                report.write_text(json.dumps(fixture),encoding='utf-8');view._render(read_build_progress(root))
                text=view.details.toPlainText()
                self.assertIn('Native typed endpoint/client/GUI and proposal-job admission verified.',text)
                for value in fixture['checks']+[fixture['completed_at'],str(report)]:self.assertIn(value,text)
                self.assertIn('Live model-provider inference and chapter viewport/Play integration remain unfinished.',text)
                self.assertIn('widget_tests',text)
                for prior in ('CREATOR WORKSPACE VERIFICATION','TYPED AUTHORING / STRUCTURED PROPOSAL VERIFICATION','M3 NATIVE FIRST BOOT CHAPTER VERIFICATION'):
                    self.assertIn(prior,text)
                self.assertEqual([view.workspace_tabs.tabText(i) for i in range(view.workspace_tabs.count())],['Build progress','Creator','Chapter creator','Assets'])
                self.assertIsNone(view.creator_view);self.assertIsNone(view.content_view)
                fixture['checks']=[];report.write_text(json.dumps(fixture),encoding='utf-8')
                view._render(read_build_progress(root));text=view.details.toPlainText()
                self.assertIn('Chapter creator verification: unreadable.',text)
                self.assertNotIn('Native typed endpoint/client/GUI and proposal-job admission verified.',text)
            finally:
                view.close();bus.shutdown()

    def test_native_chapter_proof_is_recorded_separately_with_exact_executable_identity(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        coverage = ('native_gpu', 'actual_player_pov', 'actual_hud_fits', 'repair_route', 'bypass_route',
                    'occupied_door_close', 'optional_help', 'optional_decline', 'depart_return',
                    'feed_build_dismantle', 'latched_unpowered_return', 'restart_pixels_identity',
                    'actual_f9_reload', 'hazard_pause', 'hazard_recovery', 'critical_backpressure',
                    'recovery_consumes_old_input', 'stale_activation_rejected', 'empty_socket_survives',
                    'remote_node_reach', 'translated_board_supported', 'reload_failure_retains_live',
                    'live_f5_held_contact', 'close_drains_held_contact', 'explicit_m2_upgrade',
                    'm2_history_preserved', 'original_import_preserved')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                text = view.details.toPlainText()
                self.assertIn('M3 NATIVE FIRST BOOT CHAPTER VERIFICATION', text)
                self.assertIn('Native First Boot chapter verification: not_run.', text)
                self.assertNotIn('Native First Boot chapter checks passed', text)
                report = root / 'engine/out/first_boot_chapter_verification.json'
                report.parent.mkdir(parents=True)
                fixture = {'schema_version': 1, 'status': 'passed',
                           'executablePath': 'C:/chapter/proof/aibs_motherboard.exe', 'executableSha256': 'b2' * 32,
                           'work_directory': 'C:/chapter/proof/run', 'completed_at': '2026-11-01T13:22:42.195016+00:00',
                           'checks': ['Actual player POV and chapter retry proof'],
                           'metrics': {**{key: True for key in coverage}, 'processes': 36,
                                       'debug_layer': False, 'debug_errors': 0}}
                report.write_text(json.dumps(fixture), encoding='utf-8')
                data = read_build_progress(root)
                data['source_changed_since_build'] = True
                view._render(data)
                text = view.details.toPlainText()
                self.assertIn('Native First Boot chapter checks passed', text)
                self.assertIn('Source changed after this build; verification is stale.', view.summary.text())
                for value in (str(report), fixture['completed_at'], fixture['executablePath'],
                              fixture['executableSha256'], fixture['work_directory'], fixture['checks'][0]):
                    self.assertIn(value, text)
                self.assertIn('D3D12 debug layer observed: false', text)
                self.assertIn('M2 NATIVE DURABLE WORLD VERIFICATION', text)
                self.assertIn('REGISTRY MIGRATION VERIFICATION', text)
                self.assertIn('Native durable world verification: not_run.', text)
                self.assertNotIn('Native gameplay and durable restart checks passed', text)
                self.assertNotIn('M3 complete', text)
                fixture['metrics']['actual_hud_fits'] = False
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Native First Boot chapter verification: unreadable.', view.details.toPlainText())
                self.assertNotIn('Native First Boot chapter checks passed', view.details.toPlainText())
                fixture.update(status='failed', error='Actual HUD fit failed')
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Native First Boot chapter verification: failed.', view.details.toPlainText())
                self.assertIn('Actual HUD fit failed', view.details.toPlainText())
                self.assertTrue(view.chapter_button.text().startswith('Play First Boot chapter'))
            finally:
                view.close()
                bus.shutdown()

    def test_chapter_launcher_skips_old_bundle_and_uses_first_known_capable_player(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'package/_internal'
            bundled = bundle / 'game_assets/player/aibs_motherboard.exe'
            installed = root / 'engine/install/release/bin/aibs_motherboard.exe'
            source = root / 'engine/out/windows-msvc/Release/aibs_motherboard.exe'
            fixture = {'schema_version': 1, 'sdk_version': '0.8.0', 'features': {'first_boot_chapter': True}}
            for binary in (bundled, installed, source):
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b'fixture-not-executed')
            for binary in (installed, source):
                binary.with_name('aibs_capabilities.json').write_text(json.dumps(fixture), encoding='utf-8')
            with patch.object(game_view.sys, 'frozen', True, create=True), patch.object(game_view.sys, '_MEIPASS', str(bundle), create=True):
                view = GameBuildNativeView(bus, root=root)
                try:
                    self.assertEqual(view.chapter_button.text(), 'Play First Boot chapter (legacy blockout)')
                    self.assertTrue(view.chapter_button.isEnabled())
                    self.assertEqual(view.native_player_path, bundled)
                    self.assertEqual(view.chapter_player_path, installed)
                    with patch.object(game_view.QProcess, 'startDetached', return_value=(True, 123)) as launch:
                        view.chapter_button.click()
                        launch.assert_called_once_with(str(installed), ['--durable-world', '--chapter'], str(installed.parent))
                        self.assertIn('First Boot chapter launched.', view.launch_status.text())
                        launch.reset_mock()
                        view.durable_world_button.click()
                        launch.assert_called_once_with(str(bundled), ['--durable-world'], str(bundled.parent))
                        launch.reset_mock()
                        installed.with_name('aibs_capabilities.json').unlink()
                        view.chapter_button.click()
                        launch.assert_called_once_with(str(source), ['--durable-world', '--chapter'], str(source.parent))
                        launch.reset_mock()
                        bundled.with_name('aibs_capabilities.json').write_text(json.dumps(fixture), encoding='utf-8')
                        view.chapter_button.click()
                        launch.assert_called_once_with(str(bundled), ['--durable-world', '--chapter'], str(bundled.parent))
                finally:
                    view.close()
                    bus.shutdown()

    def test_chapter_launcher_disables_false_or_malformed_capabilities_and_reports_launch_errors(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'engine/install/release/bin/aibs_motherboard.exe'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'fixture-not-executed')
            # A descriptor cannot redirect the allowlist to this arbitrary executable.
            foreign = root / 'unrelated.exe'
            foreign.write_bytes(b'never-executed')
            view = GameBuildNativeView(bus, root=root)
            try:
                self.assertFalse(view.chapter_button.isEnabled())
                with patch.object(game_view.QProcess, 'startDetached') as launch:
                    view.chapter_button.click()
                    launch.assert_not_called()
                    view._launch_chapter()
                    self.assertIn('chapter has not been built or packaged', view.launch_status.text())
                    launch.assert_not_called()
                descriptor = binary.with_name('aibs_capabilities.json')
                for content in ('{broken', json.dumps({'schema_version': 1, 'sdk_version': '0.8.0',
                    'features': {'first_boot_chapter': False}, 'executable': str(foreign)})):
                    descriptor.write_text(content, encoding='utf-8')
                    view._update_launch_targets()
                    self.assertFalse(view.chapter_button.isEnabled())
                    self.assertIsNone(view.chapter_player_path)
                descriptor.write_text(json.dumps({'schema_version': 1, 'sdk_version': '0.8.0',
                    'features': {'first_boot_chapter': True}, 'executable': str(foreign)}), encoding='utf-8')
                view._update_launch_targets()
                self.assertTrue(view.chapter_button.isEnabled())
                with patch.object(game_view.QProcess, 'startDetached', return_value=(False, 0)) as launch:
                    view.chapter_button.click()
                    launch.assert_called_once_with(str(binary), ['--durable-world', '--chapter'], str(binary.parent))
                    self.assertIn('Could not start the First Boot chapter.', view.launch_status.text())
                with patch.object(game_view.QProcess, 'startDetached', side_effect=OSError('Fixture launch failure')):
                    view.chapter_button.click()
                    self.assertIn('Could not start the First Boot chapter: Fixture launch failure', view.launch_status.text())
            finally:
                view.close()
                bus.shutdown()

    def test_registry_migration_evidence_does_not_certify_native_chapter(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        coverage = ('before_commit_recovery', 'after_commit_recovery', 'atomic_registry_receipts',
                    'preserved_m2_evidence', 'exact_migration_retry', 'conflicting_migration_rejected',
                    'stale_registry_connection')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                self.assertIn('REGISTRY MIGRATION VERIFICATION', view.details.toPlainText())
                self.assertIn('Registry migration verification: not_run.', view.details.toPlainText())
                report = root / 'engine/out/registry_migration_verification.json'
                report.parent.mkdir(parents=True)
                fixture = {'schema_version': 1, 'status': 'passed',
                    'completed_at': '2026-11-01T12:23:44.210688+00:00',
                    'checks': ['Migration COMMIT leaves original M2 evidence intact'],
                    'scope': {'project_id': 'registry-proof', 'world_id': 'registry-world',
                              'branch_id': 'main', 'timeline_id': 'registry-timeline', 'context': 'player_world'},
                    'revision': 3, 'original_checkpoint_id': 'original-checkpoint',
                    'metrics': {**{key: True for key in coverage}, 'old_studio92_rejected': True}}
                report.write_text(json.dumps(fixture), encoding='utf-8')
                data = read_build_progress(root)
                data['source_changed_since_build'] = True
                view._render(data)
                text = view.details.toPlainText()
                self.assertIn('Registry migration checks passed', text)
                self.assertIn('Source changed after this build; verification is stale.', view.summary.text())
                self.assertIn(str(report), text)
                self.assertIn(fixture['completed_at'], text)
                self.assertIn('registry-timeline', text)
                self.assertIn('original-checkpoint', text)
                self.assertIn('optional compatibility observation): true', text)
                self.assertIn('does not verify the native chapter or M3 completion', text)
                self.assertIn('Native durable world verification: not_run.', text)
                self.assertNotIn('Native gameplay and durable restart checks passed', text)
                del fixture['metrics']['old_studio92_rejected']
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertNotIn('optional compatibility observation):', view.details.toPlainText())
                fixture['metrics']['stale_registry_connection'] = False
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Registry migration verification: unreadable.', view.details.toPlainText())
                self.assertNotIn('Registry migration checks passed', view.details.toPlainText())
                fixture.update(status='failed', error='Stale connection was not rejected')
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Registry migration verification: failed.', view.details.toPlainText())
                self.assertIn(fixture['error'], view.details.toPlainText())
            finally:
                view.close()
                bus.shutdown()

    def test_durable_world_button_uses_fixed_mode_and_preserves_other_launches(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                self.assertFalse(view.durable_world_button.isEnabled())
                with patch.object(game_view.QProcess, 'startDetached', return_value=(True, 123)) as launch:
                    view.durable_world_button.click()
                    launch.assert_not_called()
                    binary = root / 'engine/install/release/bin/aibs_motherboard.exe'
                    binary.parent.mkdir(parents=True)
                    binary.write_bytes(b'fixture-not-executed')
                    view._update_launch_targets()
                    self.assertTrue(view.durable_world_button.isEnabled())
                    for button, arguments in ((view.durable_world_button, ['--durable-world']),
                                              (view.obstacle_course_button, ['--obstacle-course']),
                                              (view.native_player_button, [])):
                        button.click()
                        launch.assert_called_once_with(str(binary), arguments, str(binary.parent))
                        launch.reset_mock()
            finally:
                view.close()
                bus.shutdown()

    def test_durable_native_evidence_is_distinct_and_honest_in_view(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        coverage = ('native_gpu', 'repair_build_dismantle', 'restart_pixels_identical', 'stable_uuids',
                    'semantic_event_equality', 'tombstone_persistence', 'before_commit_recovery',
                    'after_commit_recovery', 'exact_retry', 'live_retry', 'close_drained', 'import_preserves_original')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                text = view.details.toPlainText()
                self.assertIn('M2 NATIVE DURABLE WORLD VERIFICATION', text)
                self.assertIn('Native durable world verification: not_run.', text)
                self.assertNotIn('Native gameplay and durable restart checks passed', text)
                report = root / 'engine/out/durable_world_verification.json'
                report.parent.mkdir(parents=True)
                fixture = {'schema_version': 1, 'status': 'passed',
                    'completed_at': '2026-11-01T19:00:00+00:00',
                    'checks': ['Native repair/build/dismantle and actual GPU restart', 'Original source is preserved'],
                    'scope': {'project_id': 'first-boot-world', 'world_id': 'fixture-durable-world',
                              'branch_id': 'main', 'timeline_id': 'fixture-timeline', 'context': 'player_world'},
                    'revision': 3, 'durable_events': 3,
                    'metrics': {**{key: True for key in coverage}, 'processes': 23, 'debug_errors': 0}}
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                text = view.details.toPlainText()
                self.assertIn('M2 SQLITE PROCESS RECOVERY', text)
                self.assertIn('M2 NATIVE DURABLE WORLD VERIFICATION', text)
                self.assertIn('Native gameplay and durable restart checks passed', text)
                self.assertIn('Native repair/build/dismantle', text)
                self.assertIn('fixture-durable-world', text)
                self.assertIn('fixture-timeline', text)
                self.assertIn('2026-11-01T19:00:00+00:00', text)
                self.assertNotIn('native gameplay save/HUD integration remains pending', text)
                fixture['metrics']['close_drained'] = False
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Native durable world verification: unreadable.', view.details.toPlainText())
                self.assertNotIn('Native gameplay and durable restart checks passed', view.details.toPlainText())
                fixture['status'] = 'failed'
                fixture['error'] = 'Close drain failed'
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Native durable world verification: failed.', view.details.toPlainText())
                self.assertIn('Close drain failed', view.details.toPlainText())
            finally:
                view.close()
                bus.shutdown()

    def test_gameplay_store_evidence_is_separate_from_native_save_integration(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                self.assertIn('M2 SQLITE PROCESS RECOVERY', view.details.toPlainText())
                self.assertIn('Status: not_run', view.details.toPlainText())
                output = root / 'engine/out'
                output.mkdir(parents=True)
                fixture = {'schema_version': 1, 'status': 'passed',
                    'completed_at': '2026-11-01T16:00:00+00:00', 'checks': ['Killed process after COMMIT'],
                    'world_id': 'durable-fixture-world', 'revision': 2,
                    'metrics': {**{key: True for key in ('process_recovery', 'atomic_components_events',
                        'exact_retry', 'stale_writer', 'scope_isolation')}, 'durable_events': 2}}
                report = output / 'gameplay_store_verification.json'
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                text = view.details.toPlainText()
                self.assertIn('Killed process after COMMIT', text)
                self.assertIn('durable-fixture-world', text)
                self.assertIn('Headless storage proof; native gameplay evidence is reported separately.', text)
                fixture['metrics']['process_recovery'] = False
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Status: unreadable', view.details.toPlainText())
            finally:
                view.close()
                bus.shutdown()

    def test_obstacle_course_button_uses_only_known_native_binary_and_fixed_mode(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'engine/install/release/bin/aibs_motherboard.exe'
            view = GameBuildNativeView(bus, root=root)
            try:
                self.assertFalse(view.obstacle_course_button.isEnabled())
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b'fixture-not-executed')
                view._update_launch_targets()
                self.assertTrue(view.obstacle_course_button.isEnabled())
                with patch.object(game_view.QProcess, 'startDetached', return_value=(True, 123)) as launch:
                    view.obstacle_course_button.click()
                    launch.assert_called_once_with(str(binary), ['--obstacle-course'], str(binary.parent))
                    self.assertIn('obstacle course launched', view.launch_status.text())
                    launch.reset_mock()
                    view.native_player_button.click()
                    launch.assert_called_once_with(str(binary), [], str(binary.parent))
            finally:
                view.close()
                bus.shutdown()

    def test_obstacle_course_reports_scope_and_rejects_false_pass_in_native_view(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                self.assertIn('NATIVE OBSTACLE COURSE VERIFICATION', view.details.toPlainText())
                self.assertIn('Obstacle course verification: not_run.', view.details.toPlainText())
                output = root / 'engine/out'
                output.mkdir(parents=True)
                fixture = {
                    'schema_version': 1, 'status': 'passed',
                    'completed_at': '2026-11-01T16:00:00+00:00',
                    'checks': ['20-degree climb and 60-degree refusal rendered on native GPU'],
                    'adapter': 'Fixture course GPU', 'world_id': 'course-world', 'checkpoint_id': 'course-save',
                    'metrics': {key: True for key in ('steps', 'slopes', 'walls', 'falls', 'focus', 'restart', 'interaction')}
                }
                report = output / 'obstacle_course_verification.json'
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                details = view.details.toPlainText()
                self.assertIn('Obstacle course checks passed', details)
                self.assertIn('20-degree climb and 60-degree refusal', details)
                self.assertIn('Fixture course GPU', details)
                self.assertIn('course-save', details)
                self.assertIn('2026-11-01T16:00:00+00:00', details)
                fixture['metrics']['slopes'] = False
                report.write_text(json.dumps(fixture), encoding='utf-8')
                view._render(read_build_progress(root))
                self.assertIn('Obstacle course verification: unreadable.', view.details.toPlainText())
                self.assertNotIn('Obstacle course checks passed', view.details.toPlainText())
            finally:
                view.close()
                bus.shutdown()

    def test_queue_displays_declared_current_milestone_and_pending_slices(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'engine').mkdir()
            (root / 'engine/milestone_queue.json').write_text(json.dumps({
                'schema_version': 1, 'updated_at': '2026-11-01T12:00:00+00:00',
                'current_milestone': 'M1',
                'milestones': [{'id': 'M1', 'title': 'Grounded BS', 'status': 'in_progress', 'gates': [
                    {'id': 'M1-G01', 'status': 'UNVERIFIED', 'description': 'Course acceptance', 'evidence': []}]}],
                'next_slices': [{'id': 'S1', 'milestone': 'M1', 'title': 'Movement capsule', 'status': 'in_progress'},
                                {'id': 'S2', 'milestone': 'M1', 'title': 'Event durability', 'status': 'planned'},
                                {'id': 'S3', 'milestone': 'M1', 'title': 'Power fault route', 'status': 'planned'}]
            }), encoding='utf-8')
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                details = view.details.toPlainText()
                self.assertIn('M1: Grounded BS', view.summary.text())
                self.assertIn('NEXT THREE PENDING SLICES', details)
                self.assertIn('S1 [in_progress] Movement capsule', details)
                self.assertIn('S2 [planned] Event durability', details)
                self.assertIn('S3 [planned] Power fault route', details)
                self.assertIn('M1-G01: UNVERIFIED', details)
                self.assertIn('Declared plan', details)
                self.assertIn('Grounded movement verification: not_run.', details)
            finally:
                view.close()
                bus.shutdown()

    def test_movement_report_is_presented_with_status_and_timestamp(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = GameBuildNativeView(bus, root=root)
            try:
                view._render(read_build_progress(root))
                self.assertIn('MOVEMENT / COLLISION VERIFICATION', view.details.toPlainText())
                self.assertIn('Grounded movement verification: not_run.', view.details.toPlainText())
                output = root / 'engine/out'
                output.mkdir(parents=True)
                (output / 'movement_verification.json').write_text(json.dumps({
                    'schema_version': 1, 'status': 'passed',
                    'checks': ['Wall prevents capsule crossing'],
                    'completed_at': '2026-11-01T11:30:00+00:00',
                    'engine': 'Jolt', 'engine_version': 'fixture', 'fixed_hz': 60,
                    'metrics': {'ticks': 180}
                }), encoding='utf-8')
                view._render(read_build_progress(root))
                details = view.details.toPlainText()
                self.assertIn('Grounded movement and collision checks passed', details)
                self.assertIn('Jolt fixture', details)
                self.assertIn('60 Hz', details)
                self.assertIn('2026-11-01T11:30:00+00:00', details)
                self.assertIn('Wall prevents capsule crossing', details)
            finally:
                view.close()
                bus.shutdown()

    def test_packaged_assets_take_priority_without_launching(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'package/_internal'
            playground = bundle / 'game_assets/playground/index.html'
            binary = bundle / 'game_assets/player/aibs_motherboard.exe'
            playground.parent.mkdir(parents=True)
            binary.parent.mkdir(parents=True)
            playground.write_text('<!doctype html>', encoding='utf-8')
            binary.write_bytes(b'fixture-not-executed')
            with patch.object(game_view.sys, 'frozen', True, create=True), patch.object(game_view.sys, '_MEIPASS', str(bundle), create=True):
                view = GameBuildNativeView(bus, root=root)
                try:
                    self.assertEqual(view.playground_path, playground)
                    self.assertEqual(view.native_player_path, binary)
                    self.assertTrue(view.native_player_button.isEnabled())
                    self.assertTrue(view.durable_world_button.isEnabled())
                    with patch.object(game_view.QProcess, 'startDetached', return_value=(True, 123)) as launch:
                        view.durable_world_button.click()
                        launch.assert_called_once_with(str(binary), ['--durable-world'], str(binary.parent))
                finally:
                    view.close()
                    bus.shutdown()

    def test_local_hosted_playground_and_native_player_targets(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            playground = root / 'frontend/public/bs-game/index.html'
            playground.parent.mkdir(parents=True)
            playground.write_text('<!doctype html>', encoding='utf-8')
            view = GameBuildNativeView(bus, root=root)
            try:
                self.assertEqual(view.playground_path, playground)
                self.assertFalse(view.native_player_button.isEnabled())
                binary = root / 'engine/install/release/bin/aibs_motherboard.exe'
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b'fixture-not-executed')
                view._update_launch_targets()
                self.assertTrue(view.native_player_button.isEnabled())
                self.assertEqual(view.native_player_path, binary)
                self.assertNotIn('Internet is required', view.playground_button.toolTip())
            finally:
                view.close()
                bus.shutdown()

    def test_default_root_follows_active_checkout(self):
        self.assertEqual(GAME_PROJECT_ROOT, Path(__file__).resolve().parents[2])

    def test_concept_playground_button_uses_optional_local_file(self):
        app = QApplication.instance() or QApplication([])
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'docs/game_engine/concept_playground/first_boot_playground.html'
            missing = GameBuildNativeView(bus, root=root)
            try:
                self.assertEqual(missing.playground_path, path)
                self.assertEqual(missing.playground_button.text(), 'Open Concept Playground (browser)')
                self.assertFalse(missing.playground_button.isEnabled())
            finally:
                missing.close()
            path.parent.mkdir(parents=True)
            path.write_text('<!DOCTYPE html><title>Test concept fixture</title>', encoding='utf-8')
            present = GameBuildNativeView(bus, root=root)
            try:
                self.assertEqual(present.playground_path, path)
                self.assertTrue(present.playground_button.isEnabled())
                self.assertGreater(present.playground_button.receivers(present.playground_button.clicked), 0)
            finally:
                present.close()
                bus.shutdown()

    def test_real_worker_refresh_and_navigation(self):
        app = QApplication.instance() or QApplication([])
        # The offscreen Windows platform does not enumerate system fonts.
        font = Path('C:/Windows/Fonts/segoeui.ttf')
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
            app.setFont(QFont('Segoe UI', 10))
        app.setStyleSheet(STYLESHEET)
        bus = EngineBus(max_threads=1)
        with tempfile.TemporaryDirectory() as directory:
            view = GameBuildNativeView(bus, root=Path(directory))
            try:
                view.resize(1100, 860)
                view.show()
                deadline = time.monotonic() + 8
                while view.pending and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.01)
                self.assertFalse(view.pending)
                self.assertIn('not_run', view.summary.text())
                self.assertIn('LOCAL DRIVE SPACE', view.details.toPlainText())
                self.assertIn('Checkpoint verification: not_run.', view.details.toPlainText())
                self.assertIn('Persistent world-to-render verification: not_run.', view.details.toPlainText())
                self.assertNotIn('Persistent world edits and restart rendering verified', view.details.toPlainText())
                output = Path(directory) / 'engine/out'
                output.mkdir(parents=True)
                (output / 'checkpoint_verification.json').write_text(json.dumps({
                    'schema_version': 1, 'status': 'passed', 'checks': ['separate-process restart'],
                    'completed_at': '2026-11-01T06:00:00+00:00'
                }), encoding='utf-8')
                view.refresh()
                deadline = time.monotonic() + 8
                while view.pending and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.01)
                self.assertFalse(view.pending)
                self.assertIn('Checkpoint tests passed', view.details.toPlainText())
                self.assertIn('separate-process restart', view.details.toPlainText())
                self.assertIn('ENGINE OUTPUT STORAGE', view.details.toPlainText())
                (output / 'site-verification').mkdir()
                (output / 'renderer_verification.json').write_text(json.dumps({
                    'schema_version': 1, 'status': 'passed', 'checks': ['Real native draw'],
                    'completed_at': '2026-11-01T06:00:00+00:00', 'adapter': 'Fixture GPU'
                }), encoding='utf-8')
                (output / 'site-verification/hosting_verification.json').write_text(json.dumps({
                    'schema_version': 1, 'status': 'passed', 'checks': ['Hosting verified'],
                    'verified_at': '2026-11-01T06:00:00+00:00',
                    'origin': 'https://example.test', 'version': 'fixture-version'
                }), encoding='utf-8')
                view.refresh()
                deadline = time.monotonic() + 8
                while view.pending and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.01)
                self.assertIn('Native motherboard renderer verified', view.details.toPlainText())
                self.assertIn('Fixture GPU', view.details.toPlainText())
                self.assertIn('https://example.test', view.details.toPlainText())
                self.assertIn('fixture-version', view.details.toPlainText())
                (output / 'world_scene_verification.json').write_text(json.dumps({
                    'schema_version': 1, 'status': 'passed',
                    'checks': ['Visible repair survives restart'],
                    'completed_at': '2026-11-01T07:30:00+00:00',
                    'world_id': 'fixture-world-id', 'revision': 4,
                    'entity_count': 12, 'adapter': 'Fixture GPU'
                }), encoding='utf-8')
                view.refresh()
                deadline = time.monotonic() + 8
                while view.pending and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.01)
                details = view.details.toPlainText()
                self.assertIn('Persistent world edits and restart rendering verified', details)
                self.assertIn('Visible repair survives restart', details)
                self.assertIn('World: fixture-world-id', details)
                self.assertIn('Revision: 4', details)
                self.assertIn('Entities: 12', details)
                self.assertTrue(any(tab.key == 'game_build' for tab in get_all_subtabs_flat()))
                self.assertTrue(view.timer.isActive())
                view.hide()
                self.assertFalse(view.timer.isActive())
            finally:
                view.close()
                bus.shutdown()


if __name__ == '__main__':
    unittest.main()
