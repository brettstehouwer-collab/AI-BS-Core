"""Asset workspace process/receipt contracts; fake children never launch a GPU."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.asset_view import AssetView

APP = QApplication.instance() or QApplication([])
UUID = '5d40817e-d515-47de-8849-55d6569b03df'
SHA = 'a' * 64


class FakeProcess(QObject):
    readyReadStandardOutput = pyqtSignal()
    readyReadStandardError = pyqtSignal()
    finished = pyqtSignal(int, object)
    errorOccurred = pyqtSignal(object)
    started = pyqtSignal()
    ProcessChannelMode = QProcess.ProcessChannelMode
    ProcessChannel = QProcess.ProcessChannel
    ProcessState = QProcess.ProcessState
    ProcessError = QProcess.ProcessError
    ExitStatus = QProcess.ExitStatus
    instances = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.instances.append(self)
        self.channel = self.ProcessChannel.StandardOutput
        self.buffers = {self.ProcessChannel.StandardOutput: bytearray(), self.ProcessChannel.StandardError: bytearray()}
        self.running = self.ProcessState.NotRunning
        self.killed = self.terminated = False

    def setWorkingDirectory(self, value): self.cwd = value
    def setProcessChannelMode(self, value): pass
    def setReadChannel(self, value): self.channel = value
    def bytesAvailable(self): return len(self.buffers[self.channel])
    def read(self, count):
        result = bytes(self.buffers[self.channel][:count])
        del self.buffers[self.channel][:count]
        return result
    def start(self, program, arguments):
        self.program, self.arguments = program, arguments
        self.running = self.ProcessState.Running
        self.started.emit()
    def state(self): return self.running
    def processId(self): return 100 + self.instances.index(self) if self.running != self.ProcessState.NotRunning else 0
    def errorString(self): return 'fixture failed to start'
    def kill(self): self.killed = True
    def terminate(self): self.terminated = True
    def waitForFinished(self, timeout): self.finish(); return True
    def feed(self, value, *, stderr=False):
        channel = self.ProcessChannel.StandardError if stderr else self.ProcessChannel.StandardOutput
        self.buffers[channel].extend(value)
        (self.readyReadStandardError if stderr else self.readyReadStandardOutput).emit()
    def finish(self, payload=None, code=0):
        if payload is not None: self.feed(json.dumps(payload).encode())
        self.running = self.ProcessState.NotRunning
        self.finished.emit(code, self.ExitStatus.NormalExit)


class AssetViewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ('assetc.exe', 'player.exe', 'part.obj', 'part.aibmat', 'LICENSE.txt'):
            (self.root / name).write_text('fixture')
        self.pack = self.root / 'existing-pack'
        self.pack.mkdir()
        FakeProcess.instances = []
        self.patch = patch('native_studio.game_engine.asset_view.QProcess', FakeProcess)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.view = AssetView(self.root / 'assetc.exe', self.root / 'player.exe', sample_pack=self.pack)
        self.addCleanup(self.view.shutdown)
        self.addCleanup(self.view.deleteLater)

    def receipt(self, **changes):
        result = {'status': 'passed', 'assets': [{'asset_id': UUID, 'name': 'Part', 'sha256': SHA, 'triangles': 1, 'materials': 1}]}
        result.update(changes)
        return result

    def inspect(self):
        self.view.inspect_pack(self.pack)
        FakeProcess.instances[-1].finish(self.receipt())

    def test_inspect_uses_native_cli_and_displays_bounded_validated_rows(self):
        self.inspect()
        self.assertEqual(FakeProcess.instances[-1].arguments, ['--inspect', str(self.pack.resolve())])
        self.assertFalse(self.view.busy)
        self.assertEqual(self.view.asset_rows[0]['asset_id'], UUID)
        self.assertEqual(self.view.tree.topLevelItemCount(), 1)
        self.assertIsNotNone(self.view.sample_button)

    def test_cook_is_fresh_and_native_inspection_follows_success(self):
        output = self.root / 'new-pack'
        self.view.cook_asset(self.root / 'part.obj', self.root / 'part.aibmat', self.root / 'LICENSE.txt', output, UUID, 'My Part')
        process = FakeProcess.instances[-1]
        self.assertEqual(process.arguments, ['--source', str((self.root / 'part.obj').resolve()), '--materials', str((self.root / 'part.aibmat').resolve()), '--asset-id', UUID, '--name', 'My Part', '--license', str((self.root / 'LICENSE.txt').resolve()), '--output', str(output.resolve())])
        self.assertFalse(output.exists(), 'The UI must not create cooker output directories')
        process.finish({'status': 'passed', 'asset_id': UUID, 'sha256': SHA, 'output_root': str(output.resolve()), 'vertices': 3, 'triangles': 1})
        self.assertEqual(FakeProcess.instances[-1].arguments, ['--inspect', str(output.resolve())])
        FakeProcess.instances[-1].finish(self.receipt())
        self.assertEqual(len(self.view.asset_rows), 1)

    def test_existing_output_and_busy_requests_are_rejected_before_launch(self):
        with self.assertRaises(ValueError):
            self.view.cook_asset(self.root / 'part.obj', self.root / 'part.aibmat', self.root / 'LICENSE.txt', self.pack, UUID)
        self.assertEqual(FakeProcess.instances, [])
        self.view.inspect_pack(self.pack)
        with self.assertRaises(RuntimeError): self.view.inspect_pack(self.pack)
        self.assertEqual(len(FakeProcess.instances), 1)

    def test_invalid_native_receipts_do_not_publish_asset_rows(self):
        for receipt in (self.receipt(assets=[self.receipt()['assets'][0]] * 65), self.receipt(status='failed'), self.receipt(assets=[dict(self.receipt()['assets'][0], triangles=-1)]), self.receipt(assets=[dict(self.receipt()['assets'][0], asset_id='wrong')])):
            with self.subTest(receipt=str(receipt)[:80]):
                self.view.inspect_pack(self.pack)
                FakeProcess.instances[-1].finish(receipt)
                self.assertEqual(self.view.asset_rows, ())
                self.assertIn('failed', self.view.status.text().lower())

    def test_process_output_is_bounded_and_failed_or_cancelled_output_is_ignored(self):
        self.view.inspect_pack(self.pack)
        process = FakeProcess.instances[-1]
        process.feed(b'x' * (65536 + 1))
        self.assertTrue(process.killed)
        process.finish(self.receipt())
        self.assertEqual(self.view.asset_rows, ())
        self.assertIn('limit', self.view.status.text().lower())
        self.view.inspect_pack(self.pack)
        process = FakeProcess.instances[-1]
        self.view.cancel_operation()
        self.assertTrue(process.killed)
        process.finish(self.receipt())
        self.assertEqual(self.view.asset_rows, ())

    def test_preview_owns_exact_selected_child_and_close_rejects_late_receipt(self):
        self.inspect()
        self.view.tree.setCurrentItem(self.view.tree.topLevelItem(0))
        self.view.preview_selected()
        preview = FakeProcess.instances[-1]
        self.assertEqual(preview.arguments, ['--asset-showcase', '--asset-root', str(self.pack.resolve()), '--asset-id', UUID])
        self.assertGreater(self.view.preview_process_id, 0)
        self.view.stop_preview()
        self.assertTrue(preview.terminated)
        preview.finish()
        self.assertEqual(self.view.preview_process_id, 0)
        self.view.inspect_pack(self.pack)
        tool = FakeProcess.instances[-1]
        callbacks = []
        self.assertFalse(self.view.prepare_close(lambda: callbacks.append(True)))
        self.assertTrue(tool.killed)
        tool.finish(self.receipt(assets=[]))
        APP.processEvents()
        self.assertEqual(callbacks, [True])
        self.assertEqual(len(self.view.asset_rows), 1, 'Late receipt cannot replace the published pack')
        with self.assertRaises(RuntimeError): self.view.inspect_pack(self.pack)

    def test_timeout_kills_only_owned_tool_and_failed_start_clears_busy(self):
        self.view.inspect_pack(self.pack)
        tool = FakeProcess.instances[-1]
        self.view._tool_timeout()
        self.assertTrue(tool.killed)
        tool.finish()
        self.assertFalse(self.view.busy)
        self.view.inspect_pack(self.pack)
        tool = FakeProcess.instances[-1]
        tool.running = tool.ProcessState.NotRunning
        tool.errorOccurred.emit(tool.ProcessError.FailedToStart)
        self.assertFalse(self.view.busy)

    def test_unrequested_preview_failure_is_reported_and_stderr_is_bounded(self):
        self.inspect()
        self.view.preview_selected()
        preview = FakeProcess.instances[-1]
        preview.feed(b'native preview rejected asset', stderr=True)
        preview.finish(code=1)
        self.assertIn('failed', self.view.status.text().lower())
        self.assertIn('rejected asset', self.view.status.text())
        self.view.inspect_pack(self.pack)
        tool = FakeProcess.instances[-1]
        tool.feed(b'x' * (65536 + 1), stderr=True)
        self.assertTrue(tool.killed)
        tool.finish()
        self.assertIn('limit', self.view.status.text().lower())


NATIVE_COOKER = Path(os.environ.get('AIBS_ASSET_UI_COOKER',
    str(Path(__file__).resolve().parents[2] / 'engine/out/windows-msvc/Release/aibs_assetc.exe')))


@unittest.skipUnless(os.environ.get('AIBS_RUN_ASSET_UI_NATIVE') == '1' and NATIVE_COOKER.is_file(),
    'Native cooker integration requires the coordinated process slot and a built assetc executable')
class NativeAssetViewTests(unittest.TestCase):
    def test_actual_native_cook_then_inspect_in_owned_fresh_folder(self):
        with tempfile.TemporaryDirectory(prefix='aibs-asset-ui-native-') as directory:
            root = Path(directory)
            source, materials, license = root / 'My asset.obj', root / 'part.aibmat', root / 'LICENSE.txt'
            source.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl copper\nf 1 2 3\n', encoding='utf-8')
            materials.write_text('AIBMAT 1\ncopper 0.8 0.35 0.05 0\n', encoding='utf-8')
            license.write_text('Owned synthetic triangle for native UI integration.', encoding='utf-8')
            output = root / 'new cooked pack'
            view = AssetView(NATIVE_COOKER, root / 'unused-player.exe')
            try:
                view.cook_asset(source, materials, license, output, UUID, 'Native UI Part')
                deadline = time.monotonic() + 35
                while view.busy and time.monotonic() < deadline:
                    APP.processEvents()
                    time.sleep(.005)
                self.assertFalse(view.busy, view.status.text())
                self.assertEqual(len(view.asset_rows), 1, view.status.text())
                self.assertEqual(view.asset_rows[0]['name'], 'Native UI Part')
                self.assertEqual(view.asset_rows[0]['triangles'], 1)
                self.assertEqual(view.tool_process_id, 0)
                original = (output / 'catalog.aibcat').read_bytes()
                with self.assertRaises(ValueError):
                    view.cook_asset(source, materials, license, output, UUID, 'Overwrite')
                self.assertEqual((output / 'catalog.aibcat').read_bytes(), original)
                view.inspect_pack(output)
                deadline = time.monotonic() + 35
                while view.busy and time.monotonic() < deadline:
                    APP.processEvents()
                    time.sleep(.005)
                self.assertFalse(view.busy, view.status.text())
                self.assertEqual(view.asset_rows[0]['asset_id'], UUID)
                self.assertTrue(view.prepare_close())
            finally:
                view.shutdown()
                view.deleteLater()


if __name__ == '__main__':
    unittest.main()
