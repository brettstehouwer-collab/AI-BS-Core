"""Combined review contract tests; fixtures are not hardware FPS measurements."""
import copy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import tempfile
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('combined_review', Path(__file__).parents[1] / 'tools/play_and_measure_opening.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def fixture():
    request = dict(world_id='world-fixture', timeline_id='timeline-fixture', invocation='invocation-fixture', definition_sha256='a'*64)
    report = dict(version=1, status='measured', error='', measurement_profile='gameplay', gameplay_includes_reading_inspection_and_saving=True,
        actual_client_width=1920, actual_client_height=1080, gpu_debug_layer_observed=False, synthetic_chapter_ticks_used_for_fps=False,
        engine_requested_inference=False, recording_enabled=False, gpu_debug_errors=0, gpu_debug_warnings=0,
        requested_measure_seconds=900, warmup_min_seconds=2, normal_player_close=True, frame_count=900, actual_present_delta=900,
        measured_wall_seconds=15., fps=60., frame_ms=dict(mean=1000/60, p50=16.6, p95=17., p99=18.),
        content_fingerprint=request['definition_sha256'], scope=dict(world_id=request['world_id'], timeline_id=request['timeline_id']),
        visible_revision=3, durable_revision=3, measured_reading_frames=30, measured_inspection_frames=0, measured_saving_frames=4,
        long_frames=dict(over16_67ms=50, over33_33ms=2, over50ms=1), instrumentation_owned_bytes=7680300,
        opening_outcomes=dict(first_route='none', shelter_secured=False, pencil_visited=False))
    for name in ['private_bytes', 'working_set_bytes', 'scene_content_gpu_bytes']:
        report[name] = dict(start=100, end=200, maximum_sampled=250)
    common = dict(schema_version=1, play_session=request['invocation'], timeline_id=request['timeline_id'], world_id=request['world_id'],
        content_fingerprint=request['definition_sha256'], context='player_world', saved=True,
        project_id='combined-opening-review', branch_id='user-gameplay-review')
    notices = [dict(common, event='aibs.saved_play.ready', durable_revision=0), dict(common, event='aibs.saved_play.stopped', durable_revision=3)]
    return report, request, notices


@contextmanager
def resource_copy():
    """Private byte copies, never executed; production resources remain read-only."""
    pins = tool.read_json(Path(tool.__file__).with_name('gameplay_review_runtime.json'))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        sdk, bundle = root/'sdk', root/'bundle'
        for name in pins['files']:
            source = Path(pins['prefix'])/name
            target = sdk/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            target = bundle/'game_assets/player'/name.removeprefix('bin/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        shutil.copytree(Path(pins['studio_bundle'])/'game_assets/opening', bundle/'game_assets/opening')
        pins.update(prefix=str(sdk), studio_bundle=str(bundle))
        pinfile = root/'pins.json'
        tool.write(pinfile, pins)
        with patch.object(tool, 'EXPECTED_SDK_PREFIX', sdk), patch.object(tool, 'EXPECTED_BUNDLE', bundle):
            yield sdk, bundle, pinfile, pins


class CombinedReviewTests(unittest.TestCase):
    def test_current_resources_execute_bundle_player_and_current_adam(self):
        with patch.object(tool.subprocess, 'Popen', side_effect=AssertionError('Unexpected launch')):
            player, factory, assets = tool.resources()
        self.assertEqual(player.parent, tool.EXPECTED_BUNDLE/'game_assets/player')
        self.assertEqual(factory.parent, player.parent)
        self.assertEqual(next(x.asset_id for x in assets.roles if x.role=='adam'), '539b6312-a9f6-4a92-a096-77f1b6c5045b')
        self.assertEqual(tool.SDK_VERSION, '0.17.0')

    def test_copied_qualified_resources_admitted_without_execution(self):
        with resource_copy() as (sdk, bundle, pinfile, pins), patch.object(tool.subprocess, 'Popen', side_effect=AssertionError('Unexpected launch')):
            player, _, assets = tool.resources(pinfile)
            self.assertEqual(player.parent, bundle/'game_assets/player')
            self.assertEqual(assets.manifest_sha256, pins['opening_manifest_sha256'])

    def test_changed_installed_runtime_rejected_even_when_sdk_is_unchanged(self):
        with resource_copy() as (sdk, bundle, pinfile, pins):
            path = bundle/'game_assets/player/aibs_motherboard.exe'
            with path.open('r+b') as stream:
                value = stream.read(1)
                stream.seek(0)
                stream.write(bytes([value[0]^1]))
            self.assertEqual(tool.digest(sdk/'bin/aibs_motherboard.exe'), pins['files']['bin/aibs_motherboard.exe']['sha256'])
            with self.assertRaisesRegex(ValueError, 'Installed review runtime differs'):
                tool.resources(pinfile)

    def test_wrong_preview_identity_or_asset_manifest_never_passes(self):
        with resource_copy() as (sdk, bundle, pinfile, pins):
            changes = [dict(sdk_version='0.16.5'), dict(sdk_version='0.16.6'), dict(studio_version='5.329.105'), dict(studio_version='5.329.103'),
                dict(prefix=str(sdk/'other')), dict(studio_bundle=str(bundle/'other')),
                dict(opening_manifest_sha256='0'*64), dict(files={})]
            for changed in changes:
                with self.subTest(changed=changed):
                    tool.write(pinfile, dict(pins, **changed))
                    with self.assertRaises(ValueError): tool.resources(pinfile)

    def test_actual_pinned_resources_inspection_never_launches_or_creates_attempt(self):
        with tempfile.TemporaryDirectory() as d, patch.object(tool, 'ATTEMPTS', Path(d)/'attempts'), patch.object(tool.subprocess, 'Popen', side_effect=AssertionError('Unexpected launch')), patch('builtins.print'):
            self.assertEqual(tool.main([]), 0)
            self.assertFalse((Path(d)/'attempts').exists())

    def test_unattended_attempt_leaves_failure_log_before_resource_access(self):
        with tempfile.TemporaryDirectory() as d, patch.object(tool, 'ATTEMPTS', Path(d)/'attempts'), patch.object(tool.sys.stdin, 'isatty', return_value=False), patch.object(tool, 'resources') as resources, patch('builtins.print'):
            self.assertEqual(tool.main(['--run']), 1)
            resources.assert_not_called()
            attempt = next((Path(d)/'attempts').iterdir())
            state = json.loads((attempt/'launch.json').read_text())
            self.assertEqual(state['status'], 'failed')
            self.assertIn('interactive console', (attempt/'failure.log').read_text())

    def test_bad_resource_preflight_is_preserved_without_game_or_save(self):
        with tempfile.TemporaryDirectory() as d, patch.object(tool, 'ATTEMPTS', Path(d)/'attempts'), patch.object(tool, 'SESSIONS', Path(d)/'sessions'), patch.object(tool.sys.stdin, 'isatty', return_value=True), patch.object(tool, 'resources', side_effect=ValueError('fixture checksum mismatch')), patch.object(tool.subprocess, 'Popen') as process, patch('builtins.print'):
            self.assertEqual(tool.main(['--run']), 1)
            process.assert_not_called()
            self.assertFalse((Path(d)/'sessions').exists())
            state = json.loads((next((Path(d)/'attempts').iterdir())/'launch.json').read_text())
            self.assertEqual(state['stopped_at_stage'], 'validating_resources')
            self.assertIn('checksum mismatch', state['error'])

    def test_cancel_before_enter_never_creates_session(self):
        with tempfile.TemporaryDirectory() as d, patch.object(tool, 'ATTEMPTS', Path(d)/'attempts'), patch.object(tool, 'SESSIONS', Path(d)/'sessions'), patch.object(tool.sys.stdin, 'isatty', return_value=True), patch.object(tool, 'resources', return_value=(None,None,None)), patch.object(tool.shutil, 'disk_usage', return_value=SimpleNamespace(free=4*1024**3)), patch('builtins.input', side_effect=KeyboardInterrupt), patch('builtins.print'):
            self.assertEqual(tool.main(['--run']), 130)
            self.assertFalse((Path(d)/'sessions').exists())
            state = json.loads((next((Path(d)/'attempts').iterdir())/'launch.json').read_text())
            self.assertEqual(state['status'], 'cancelled')

    def test_render_sample_never_becomes_chapter_or_human_acceptance(self):
        report, request, notices = fixture()
        result = tool.validate(report, 0, request, notices)
        self.assertEqual(result['fps'], 60.)
        self.assertFalse(result['human_pacing_accepted'])
        self.assertFalse(result['opening_outcomes']['shelter_secured'])

    def test_malformed_failed_or_mismatched_samples_cannot_pass(self):
        report, request, notices = fixture()
        changes = [dict(version=2), dict(version=True), dict(status='failed'), dict(measurement_profile='stationary'), dict(error='inactive'),
            dict(gpu_debug_layer_observed=True), dict(gpu_debug_errors=False), dict(recording_enabled=True),
            dict(engine_requested_inference=True), dict(actual_client_height=900), dict(frame_count=0),
            dict(actual_present_delta=True), dict(measured_wall_seconds=14.), dict(fps=float('nan')),
            dict(frame_ms={}), dict(normal_player_close=False), dict(requested_measure_seconds=15),
            dict(scope=dict(world_id='wrong', timeline_id=request['timeline_id'])), dict(content_fingerprint='b'*64),
            dict(durable_revision=2), dict(measured_reading_frames=901), dict(instrumentation_owned_bytes=9*1024**2),
            dict(long_frames=dict(over16_67ms=1,over33_33ms=2,over50ms=0)),
            dict(private_bytes=dict(start=100,end=200,maximum_sampled=150)),
            dict(opening_outcomes=dict(first_route='none',shelter_secured=False,pencil_visited=True))]
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                tool.validate(dict(copy.deepcopy(report), **changed), 0, request, notices)
        for code in [1, False]:
            with self.assertRaises(ValueError): tool.validate(report, code, request, notices)
        with self.assertRaises(ValueError): tool.validate(report, 0, request, notices[:1])
        bad = copy.deepcopy(notices); bad[-1]['saved'] = False
        with self.assertRaises(ValueError): tool.validate(report, 0, request, bad)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for text in ['{"status":"failed","status":"measured"}', '{"fps":NaN}']:
            with self.assertRaises(ValueError): tool.decode_json(text)

    def test_command_is_persistent_isolated_and_real_time(self):
        argv = tool.command(Path('player.exe'), Path('D:/test/chapter'), Path('D:/test'), 'invocation', 'timeline')
        self.assertIn('--performance-gameplay', argv)
        self.assertIn('--persistent-play', argv)
        self.assertEqual(argv[argv.index('--stop-file')+1], str(Path('D:/test/stop.invocation.request')))
        self.assertEqual(argv[argv.index('--performance-seconds')+1], '900')
        for forbidden in ['--walkthrough','--durable-step','--record-mp4']:
            self.assertNotIn(forbidden, argv)

    def test_wait_error_joins_retained_child_without_fake_result(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);player=root/'player.exe';factory=root/'factory.exe';player.write_bytes(b'fixture');factory.write_bytes(b'fixture')
            class Child:
                pid=123;returncode=None;calls=0
                def poll(self):return self.returncode
                def wait(self,timeout):
                    self.calls+=1
                    if self.calls==1:raise OSError('fixture wait failure')
                    self.returncode=0;return 0
            child=Child()
            def create(argv, **kwargs):
                project=Path(argv[argv.index('--output')+1]);project.mkdir()
                (project/'opening.aibd').write_bytes(b'fixture definition')
                tool.write(project/'opening-manifest.json',dict(opening_workshop=True,recording_bound=False,world_id='fixture-world',fingerprint=tool.digest(project/'opening.aibd')))
                return SimpleNamespace(returncode=0)
            with patch.object(tool,'ATTEMPTS',root/'attempts'),patch.object(tool,'SESSIONS',root/'sessions'),patch.object(tool.sys.stdin,'isatty',return_value=True),patch('builtins.input',return_value=''),patch('builtins.print'),patch.object(tool,'resources',return_value=(player,factory,SimpleNamespace(roles=[],manifest_sha256='a'*64))),patch.object(tool.shutil,'disk_usage',return_value=SimpleNamespace(free=4*1024**3)),patch.object(tool.subprocess,'run',side_effect=create),patch.object(tool.subprocess,'Popen',return_value=child):
                self.assertEqual(tool.main(['--run']),1)
            session=next((root/'sessions').iterdir())
            self.assertTrue(json.loads((session/'process.json').read_text())['joined'])
            self.assertEqual(child.calls,2)
            self.assertFalse((session/'result.json').exists())
            self.assertEqual(json.loads((session/'feedback.json').read_text())['review_status'],'unreviewed')


if __name__ == '__main__': unittest.main()
