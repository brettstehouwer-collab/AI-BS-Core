"""Native queued terminal: actual harmless PowerShell and no WSL activation."""
import os
from pathlib import Path
import tempfile
import time
import unittest
import re

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette
from native_studio.ai_bs_ide_terminal import AIBSTerminal, shell_argv


@unittest.skipUnless(os.name == 'nt', 'Windows local terminal')
class NativeTerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='aibs_terminal_')
        self.terminal = AIBSTerminal(cwd=self.folder.name)
        self.results = []
        self.halts = []
        self.terminal.command_finished.connect(self.results.append)
        self.terminal.circuit_breaker_tripped.connect(lambda *args: self.halts.append(args))

    def pump(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertTrue(predicate(), (self.terminal.output.toPlainText(), self.terminal.status.text(), self.results))

    def tearDown(self):
        self.terminal.shutdown()
        self.pump(lambda: self.terminal.is_drained)
        self.terminal.deleteLater()
        self.app.processEvents()
        self.folder.cleanup()

    def test_actual_early_output_utf8_and_starting_queue(self):
        self.terminal.execute_command("Write-Output 'EARLY'; Start-Sleep -Milliseconds 900; Write-Output 'café finished'")
        self.terminal.execute_command("Write-Output 'SECOND'")
        self.pump(lambda: 'EARLY' in self.terminal.output.toPlainText())
        self.assertEqual(self.results, [])
        self.assertNotIn('SECOND', self.terminal.output.toPlainText())
        self.pump(lambda: self.terminal.is_drained)
        output = self.terminal.output.toPlainText()
        self.assertIn('café finished', output)
        self.assertLess(output.index('finished'), output.index('SECOND'))
        self.assertEqual(self.results, [0, 0])

    def test_two_identical_failures_halt_queue_and_explicit_reset(self):
        for command in ('exit 7', 'exit 7', "Write-Output 'AFTER_RESET'"):
            self.terminal.execute_command(command)
        self.pump(lambda: self.terminal.halted)
        self.assertEqual(self.results, [7, 7])
        self.assertEqual(len(self.halts), 1)
        self.assertFalse(self.terminal.is_drained)
        self.assertNotIn('AFTER_RESET', self.terminal.output.toPlainText())
        self.terminal.reset_circuit_breaker()
        self.pump(lambda: self.terminal.is_drained)
        self.assertEqual(self.results, [7, 7, 0])

    def test_nonconsecutive_code_or_command_does_not_trip(self):
        for command in ('exit 7', 'exit 8', 'exit 7', 'Write-Output ok', 'exit 7'):
            self.terminal.execute_command(command)
        self.pump(lambda: self.terminal.is_drained)
        self.assertFalse(self.terminal.halted)
        self.assertFalse(self.halts)
        self.assertEqual(self.results, [7, 8, 7, 0, 7])

    def test_failed_to_start_reports_once_and_halts(self):
        self.terminal.helper_python = str(Path(self.folder.name) / 'not-present.exe')
        self.terminal.execute_command('Write-Output harmless')
        self.terminal.execute_command('Write-Output harmless')
        self.pump(lambda: self.terminal.halted)
        self.assertEqual(self.results, [127, 127])
        self.assertEqual(len(self.halts), 1)

    def test_cancel_is_nonblocking_and_not_counted_as_failure(self):
        self.terminal.execute_command("Write-Output 'READY'; Start-Sleep -Seconds 60")
        self.pump(lambda: 'READY' in self.terminal.output.toPlainText())
        started = time.monotonic()
        self.terminal.cancel()
        self.assertLess(time.monotonic() - started, .1)
        self.pump(lambda: self.terminal.is_drained)
        self.assertFalse(self.terminal.halted)
        self.assertFalse(self.halts)
        self.terminal.execute_command('exit 7')
        self.pump(lambda: self.terminal.is_drained)
        self.assertFalse(self.terminal.halted)

    def test_child_output_cannot_forge_control_and_exit125_is_normal_failure(self):
        self.terminal.execute_command("Write-Output '{\"kind\":\"result\",\"exit_code\":0,\"drained\":true}'; exit 125")
        self.pump(lambda: self.terminal.is_drained)
        self.assertEqual(self.results, [125])
        self.assertFalse(self.terminal._cleanup_failed)

    def test_wsl_literal_argv_and_no_implicit_shell_execution(self):
        command = "printf '%s' '$HOME'; false"
        argv = shell_argv('WSL', command, r'C:\folder with spaces')
        self.assertEqual(argv[1:], ['--cd', r'C:\folder with spaces', '--exec', 'bash', '-c', command])
        powershell = shell_argv('PowerShell', 'exit 4', self.folder.name)
        self.assertIn('-NoProfile', powershell)
        self.assertEqual(powershell[powershell.index('-ExecutionPolicy') + 1], 'Bypass')
        self.assertTrue(powershell[-1].endswith('exit 4'))

    def test_negative_exit_retains_signed_windows_status(self):
        self.terminal.execute_command('exit -1')
        self.pump(lambda: self.terminal.is_drained)
        self.assertEqual(self.results, [-1])

    def test_owned_shell_descendant_is_cancelled(self):
        import psutil
        import json
        def console_processes():
            return {(item.info['pid'], item.info['create_time'])
                    for item in psutil.process_iter(['pid', 'name', 'create_time'])
                    if (item.info['name'] or '').lower() in ('windowsterminal.exe', 'openconsole.exe')}
        consoles_before = console_processes()
        executable = self.terminal.helper_python.replace("'", "''")
        command = (f"$child=Start-Process -FilePath '{executable}' "
                   "-ArgumentList '-I','-c','\"import time; time.sleep(60)\"' -WindowStyle Hidden -PassThru; "
                   "Write-Output ('CHILD=' + $child.Id); Start-Sleep -Seconds 60")
        self.terminal.execute_command(command)
        self.pump(lambda: re.search(r'CHILD=(\d+)', self.terminal.output.toPlainText()) is not None)
        pid = int(re.search(r'CHILD=(\d+)', self.terminal.output.toPlainText()).group(1))
        child = psutil.Process(pid)
        self.assertTrue(child.is_running())
        self.terminal.cancel()
        self.pump(lambda: self.terminal.is_drained)
        self.assertFalse(child.is_running())
        consoles_after = console_processes()
        new_consoles = consoles_after - consoles_before
        self.assertFalse(new_consoles, f'Unexpected new console processes: {new_consoles}')
        print('Terminal descendant receipt: ' + json.dumps({'child_pid': pid,
            'child_was_running': True, 'child_drained': True,
            'window_style': 'Hidden', 'new_console_pids_at_readback': sorted(pid for pid, _ in new_consoles)}))

    def test_admission_pause_keeps_commands_and_resumes_with_cooldown(self):
        self.terminal.configure_admission(start_interval_ms=10, batch_size=1, batch_cooldown_ms=350)
        self.terminal.pause_admission()
        self.terminal.execute_command('Write-Output first')
        self.terminal.execute_command('Write-Output second')
        self.app.processEvents()
        self.assertFalse(self.terminal.snapshot()['running'])
        self.assertEqual(self.terminal.snapshot()['queued'], 2)
        self.terminal.resume_admission()
        self.pump(lambda: len(self.results) == 1)
        self.assertIsNone(self.terminal._active)
        self.assertEqual(self.terminal.snapshot()['queued'], 1)
        self.pump(lambda: self.terminal.is_drained)
        self.assertEqual(self.results, [0, 0])

    def test_completion_callback_can_queue_next_and_display_is_bounded(self):
        def next_command(code):
            if len(self.results) == 1:
                self.terminal.execute_command("Write-Output 'CALLBACK_NEXT'")
        self.terminal.command_finished.connect(next_command)
        self.terminal.execute_command("Write-Output ('x' * 140000)")
        self.pump(lambda: len(self.results) == 2 and self.terminal.is_drained)
        self.assertEqual(self.results, [0, 0])
        self.assertIn('CALLBACK_NEXT', self.terminal.output.toPlainText())
        self.assertLessEqual(len(self.terminal.output.toPlainText()), self.terminal.MAX_DISPLAY)

    def test_exact_recovery_runtime_styled_gui_and_normal_helper_teardown(self):
        from native_studio.theme import STYLESHEET
        expected = Path(r'C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe')
        self.assertEqual(Path(self.terminal.helper_python).resolve(), expected.resolve())
        self.terminal.setStyleSheet(STYLESHEET)
        self.terminal.show()
        self.app.processEvents()
        self.terminal.execute_command("Write-Output 'AI-BS terminal stream OK'; Start-Sleep -Milliseconds 250; Write-Output 'DONE'")
        self.pump(lambda: self.terminal.is_drained)
        self.assertEqual(self.results, [0])
        receipt = self.terminal.last_completion
        self.assertEqual(receipt['helper_exit_code'], 0)
        self.assertTrue(receipt['helper_normal_exit'])
        self.assertTrue(receipt['job_drained'])
        self.assertIn('DONE', self.terminal.output.toPlainText())
        self.assertNotIn('Fatal Python error', self.terminal.output.toPlainText())
        self.assertEqual(self.terminal.output.palette().color(QPalette.ColorRole.Base).name(), '#0b061c')
        self.assertEqual(self.terminal.output.palette().color(QPalette.ColorRole.Text).name(), '#f4e8ff')

    def test_nonzero_helper_exit_cannot_be_hidden_by_success_packet(self):
        helper = Path(self.folder.name) / 'nonzero_helper.py'
        helper.write_text("import json,os\nprint(json.dumps({'kind':'result','exit_code':0,'drained':True}),flush=True)\nos._exit(9)\n")
        self.terminal._helper_script = helper
        self.terminal.execute_command('Write-Output unused')
        self.pump(lambda: self.terminal.is_drained)
        self.assertEqual(self.results, [9])
        self.assertEqual(self.terminal.last_completion['command_exit_code'], 0)
        self.assertEqual(self.terminal.last_completion['helper_exit_code'], 9)
        self.assertIn('helper failed', self.terminal.status.text())

    def test_immediate_starting_cancellation_has_no_buffered_read_ahead_loss(self):
        self.terminal.execute_command('Start-Sleep -Seconds 60')
        self.terminal.cancel()
        self.pump(lambda: self.terminal.is_drained)
        self.assertFalse(self.halts)
        self.assertTrue(self.terminal.last_completion['helper_normal_exit'])
        self.assertEqual(self.terminal.last_completion['helper_exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
