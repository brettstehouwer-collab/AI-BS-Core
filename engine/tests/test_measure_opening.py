"""No timed game launch: readiness, actual immutable resources and failed reports."""
import importlib.util
from pathlib import Path
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
SPEC = importlib.util.spec_from_file_location('measure_opening', Path(__file__).parents[1] / 'tools/measure_opening.py')
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class MeasurementToolTests(unittest.TestCase):
    def test_interruption_or_wait_error_joins_only_the_retained_child(self):
        for error in (KeyboardInterrupt(), OSError('synthetic wait failure')):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);player=root/'player.exe';factory=root/'factory.exe'
                player.write_bytes(b'fixture');factory.write_bytes(b'fixture')
                class Child:
                    pid=123
                    done=False
                    waits=0
                    def poll(self):return 0 if self.done else None
                    def wait(self, timeout):
                        self.waits+=1
                        if self.waits==1:raise error
                        self.done=True
                        return 0
                child=Child()
                with patch.object(tool.sys.stdin,'isatty',return_value=True), patch('builtins.input',return_value=''), \
                     patch('builtins.print'), patch.object(tool,'SESSIONS',root/'sessions'), \
                     patch.object(tool,'resources',return_value=(player,factory,SimpleNamespace(roles=[],manifest_sha256='a'*64))), \
                     patch.object(tool.shutil,'disk_usage',return_value=SimpleNamespace(free=4*1024**3)), \
                     patch.object(tool.subprocess,'run',return_value=SimpleNamespace(returncode=0)), \
                     patch.object(tool.subprocess,'Popen',return_value=child):
                    with self.assertRaises((RuntimeError,OSError)):
                        tool.run_interactive()
                self.assertTrue(child.done)
                self.assertEqual(child.waits,2)
                session=next((root/'sessions').iterdir())
                self.assertTrue(list(session.glob('stop.*.request')))
                self.assertFalse((session/'performance.json').exists())

    def test_actual_bundled_six_pack_inspection_never_launches_a_process(self):
        with patch.object(tool.subprocess, 'Popen', side_effect=AssertionError('Unexpected launch')):
            player, factory, assets = tool.resources()
        self.assertTrue(player.is_file() and factory.is_file())
        self.assertEqual({a.role for a in assets.roles}, {'capacitor', 'adam', 'nook', 'fault', 'bypass', 'shelter'})

    def test_unattended_run_is_rejected_before_creation_or_process_launch(self):
        with patch.object(tool.sys.stdin, 'isatty', return_value=False), patch.object(tool, 'resources') as resources:
            with self.assertRaisesRegex(ValueError, 'interactive console'):
                tool.run_interactive()
            resources.assert_not_called()

    def test_rejected_measurements_never_become_fps_results(self):
        valid = {'status': 'measured', 'fps': 60., 'frame_ms': dict(mean=16.7, p50=16.6, p95=17., p99=18.),
            'actual_client_width': 1920, 'actual_client_height': 1080, 'gpu_debug_layer_observed': False,
            'frame_count': 900, 'actual_present_delta': 900, 'measured_wall_seconds': 15.,
            'synthetic_chapter_ticks_used_for_fps': False, 'engine_requested_inference': False, 'recording_enabled': False}
        self.assertEqual(tool.measured_summary(valid, 0)['fps'], 60.)
        for changed in ({'status': 'failed', 'error': 'foreground_setup_unavailable'}, {'fps': float('nan')},
                        {'frame_ms': {}}, {'actual_client_width': 1280}, {'gpu_debug_layer_observed': True},
                        {'frame_count': 0}, {'actual_present_delta': 899}, {'measured_wall_seconds': 14.},
                        {'synthetic_chapter_ticks_used_for_fps': True}, {'recording_enabled': True},
                        {'measurement_profile': 'gameplay'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                tool.measured_summary({**valid, **changed}, 0)
        with self.assertRaises(ValueError):
            tool.measured_summary(valid, 1)


if __name__ == '__main__':
    unittest.main()
