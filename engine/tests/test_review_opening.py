"""Manual review must preserve save isolation and never claim automatic acceptance."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('review_opening', Path(__file__).parents[1] / 'tools/review_opening.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class ReviewOpeningTests(unittest.TestCase):
    def test_inspection_verifies_actual_resources_without_launch(self):
        with patch.object(tool.subprocess, 'Popen', side_effect=AssertionError('Unexpected launch')), patch('builtins.print'):
            self.assertEqual(tool.main([]), 0)

    def test_unattended_launch_rejected_before_resource_or_save_access(self):
        with patch.object(tool.sys.stdin, 'isatty', return_value=False), patch.object(tool.baseline, 'resources') as resources:
            with self.assertRaises(ValueError):
                tool.run_interactive()
            resources.assert_not_called()

    def test_play_command_uses_explicit_retained_test_slot_without_proof_or_timer(self):
        cmd = tool.play_command(Path('P/player.exe'), Path('D:/test/chapter'), Path('D:/test'), 'invocation', 'timeline')
        self.assertIn('--persistent-play', cmd)
        self.assertEqual(cmd[cmd.index('--database') + 1], str(Path('D:/test/world.sqlite')))
        self.assertEqual(cmd[cmd.index('--stop-file') + 1], str(Path('D:/test/stop.invocation.request')))
        for flag in ['--performance-report', '--durable-step', '--walkthrough', '--record-mp4']:
            self.assertNotIn(flag, cmd)

    def test_wait_failure_joins_only_retained_child_and_preserves_unreviewed_feedback(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); player = root / 'player.exe'; factory = root / 'factory.exe'
            player.write_bytes(b'owned fixture'); factory.write_bytes(b'owned fixture')
            class Child:
                pid = 123
                returncode = None
                calls = 0
                def poll(self): return self.returncode
                def wait(self, timeout):
                    self.calls += 1
                    if self.calls == 1: raise OSError('wait failure')
                    self.returncode = 0
                    return 0
            child = Child()
            with patch.object(tool.sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value=''), patch('builtins.print'), \
                 patch.object(tool, 'SESSIONS', root / 'sessions'), patch.object(tool.baseline, 'resources', return_value=(player, factory, SimpleNamespace(roles=[], manifest_sha256='a'*64))), \
                 patch.object(tool.shutil, 'disk_usage', return_value=SimpleNamespace(free=4*1024**3)), \
                 patch.object(tool.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), patch.object(tool.subprocess, 'Popen', return_value=child):
                with self.assertRaisesRegex(OSError, 'wait failure'): tool.run_interactive()
            session = next((root / 'sessions').iterdir())
            self.assertTrue(json.loads((session / 'process.json').read_text())['joined'])
            self.assertEqual(json.loads((session / 'feedback.json').read_text())['review_status'], 'unreviewed')
            self.assertEqual(child.calls, 2)


if __name__ == '__main__': unittest.main()
