"""Versioned review admission checks; no player process or FPS claim."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).parents[1] / 'tools'
spec = importlib.util.spec_from_file_location('review107_test_subject', TOOLS / 'play_and_measure_opening_studio107.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
fixture_spec = importlib.util.spec_from_file_location('legacy_review_contract_fixtures', Path(__file__).with_name('test_play_and_measure_opening.py'))
fixtures = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixtures)


class Studio107Admission(unittest.TestCase):
    def test_inspection_uses_installed107_without_starting_any_process(self):
        with patch.object(tool.subprocess, 'Popen', side_effect=AssertionError('unexpected launch')), patch('builtins.print') as output:
            self.assertEqual(tool.main([]), 0)
        row = json.loads(output.call_args.args[0])
        self.assertEqual((row['studio'], row['sdk']), ('5.329.107', '0.17.1'))
        self.assertFalse(row['window_started'])
        self.assertEqual(Path(row['player']).parent, tool.EXPECTED_BUNDLE / 'game_assets/player')
        self.assertEqual(set(row['asset_roles']), {'adam', 'capacitor', 'nook', 'fault', 'bypass', 'shelter'})

    def test_old106_entry_and_pins_still_select106(self):
        legacy = fixtures.tool
        self.assertEqual((legacy.STUDIO_VERSION, legacy.SDK_VERSION), ('5.329.106', '0.17.0'))
        player, _, _ = legacy.resources()
        self.assertEqual(player.parent, legacy.EXPECTED_BUNDLE / 'game_assets/player')

    def test_wrong_sdk_bundle_and_digest_rejected(self):
        original = tool.read_json(TOOLS / 'gameplay_review_runtime_studio107.json')
        mutations = [('sdk_version', '0.17.0'), ('studio_version', '5.329.106'),
                     ('studio_bundle', str(fixtures.tool.EXPECTED_BUNDLE)),
                     ('opening_manifest_sha256', '0' * 64)]
        with tempfile.TemporaryDirectory() as directory:
            pinfile = Path(directory) / 'pins.json'
            for key, value in mutations:
                with self.subTest(key=key):
                    pins = dict(original, **{key: value})
                    tool.write(pinfile, pins)
                    with self.assertRaises(ValueError):
                        tool.resources(pinfile)

    def test_missing_or_changed_player_identity_rejected(self):
        original = tool.read_json(TOOLS / 'gameplay_review_runtime_studio107.json')
        with tempfile.TemporaryDirectory() as directory:
            pinfile = Path(directory) / 'pins.json'
            for missing in [False, True]:
                pins = json.loads(json.dumps(original))
                if missing:
                    del pins['files']['bin/aibs_motherboard.exe']
                else:
                    pins['files']['bin/aibs_motherboard.exe']['sha256'] = '0' * 64
                tool.write(pinfile, pins)
                with self.subTest(missing=missing), self.assertRaises(ValueError):
                    tool.resources(pinfile)

    def test_user_play_command_uses_actual_gameplay_measurement_without_tour_or_recording(self):
        command = tool.command(Path('player.exe'), Path('chapter'), Path('session'), 'invocation', 'timeline')
        self.assertIn('--performance-gameplay', command)
        self.assertNotIn('--walkthrough', command)
        self.assertNotIn('--record-video', command)
        self.assertEqual(command[command.index('--width') + 1], '1920')
        self.assertEqual(command[command.index('--height') + 1], '1080')
        self.assertEqual(command[command.index('--performance-seconds') + 1], '900')

    def test_render_sample_does_not_imply_human_pacing_acceptance(self):
        report, request, notices = fixtures.fixture()
        row = tool.validate(report, 0, request, notices)
        self.assertFalse(row['human_pacing_accepted'])
        self.assertFalse(row['opening_outcomes']['pencil_visited'])
        self.assertEqual(row['status'], 'valid_gameplay_render_sample')

    def test_inactive_wrong_dimensions_and_synthetic_samples_fail(self):
        for mutation in [dict(error='inactive'), dict(actual_client_height=1000),
                         dict(synthetic_chapter_ticks_used_for_fps=True), dict(frame_count=0),
                         dict(engine_requested_inference=True), dict(recording_enabled=True)]:
            report, request, notices = fixtures.fixture()
            report.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                tool.validate(report, 0, request, notices)


if __name__ == '__main__':
    unittest.main()
