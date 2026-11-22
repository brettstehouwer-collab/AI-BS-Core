"""Pin extracted mechanics and exercise real owned Windows children only."""
import ast
import hashlib
import os
from pathlib import Path
import queue
import sys
import threading
import time
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from native_studio import owned_process as owned


class OwnedProcessSourceTests(unittest.TestCase):
    def test_reviewed_class_is_exact_and_backend_file_unchanged(self):
        original_bytes = (ROOT / 'backend/core/opencode_worker.py').read_bytes()
        original = original_bytes.decode('utf-8-sig').replace('\r\n', '\n')
        extracted = (ROOT / 'native_studio/owned_process.py').read_text(encoding='utf-8')
        def block(text):
            node = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef)
                        and n.name == '_WinProcess')
            return ast.get_source_segment(text, node)
        self.assertEqual(block(original), block(extracted))
        self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), owned.BACKEND_SOURCE_SHA256)
        self.assertEqual(hashlib.sha256(block(original).encode()).hexdigest(), owned.EXTRACTED_CLASS_SHA256)

    def test_all_imports_are_stdlib_and_no_backend_provider_dependency(self):
        source = (ROOT / 'native_studio/owned_process.py').read_text(encoding='utf-8')
        imports = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module.split('.')[0])
        self.assertLessEqual(imports, {'__future__', 'ctypes', 'os', 'subprocess', 'time', '_winapi', 'msvcrt'})
        self.assertIs(owned.OwnedProcess, owned._WinProcess)

    def test_frozen_terminal_uses_bundled_helpers_and_never_studio_as_python(self):
        from PyQt6.QtWidgets import QApplication
        from native_studio.ai_bs_ide_terminal import AIBSTerminal
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, '_MEIPASS', str(root / 'bundle'), create=True), \
                    patch.dict(os.environ, {'AI_BS_ROOT': str(root)}):
                terminal = AIBSTerminal(cwd=directory)
                try:
                    self.assertEqual(terminal._helper_script,
                                     root / 'bundle/native_helpers/ai_bs_ide_terminal.py')
                    self.assertEqual(Path(terminal.helper_python), root.resolve() / 'runtime/recovery-20261110/Scripts/python.exe')
                    self.assertNotEqual(terminal.helper_python, sys.executable)
                finally:
                    terminal.shutdown()
                    terminal.deleteLater()
                    app.processEvents()


@unittest.skipUnless(os.name == 'nt', 'Actual Windows JobObject test')
class OwnedProcessWindowsTests(unittest.TestCase):
    def create(self, code):
        process = owned.OwnedProcess((sys.executable, '-I', '-B', '-c', code),
                                     str(ROOT), dict(os.environ))
        self.addCleanup(process.close)
        return process

    def wait(self, process, timeout=5):
        deadline = time.monotonic() + timeout
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertIsNotNone(process.poll())
        return process.poll()

    def test_actual_pipe_bytes_exit_code_and_idempotent_drain(self):
        process = self.create("import sys;sys.stdout.buffer.write(sys.stdin.buffer.read().upper());"
                              "sys.stdout.flush();sys.stderr.write('diagnostic');sys.exit(7)")
        payload = 'café synthetic\n'.encode('utf-8')
        process.stdin.write(payload)
        process.stdin.close()
        process.stdin = None
        self.assertEqual(self.wait(process), 7)
        self.assertEqual(process.stdout.read(), payload.upper())
        self.assertEqual(process.stderr.read(), b'diagnostic')
        self.assertTrue(process.close())
        self.assertTrue(process.close())
        self.assertIsNone(process.hp)
        self.assertIsNone(process.job)
        self.assertIsNone(process.stdout)

    def test_owned_close_drains_actual_parent_and_spawned_descendant(self):
        import psutil
        process = self.create("import subprocess,sys,time;"
            "child=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(60)']);"
            "print(child.pid,flush=True);time.sleep(60)")
        process.stdin.close()
        process.stdin = None
        lines = queue.Queue()
        reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=False)
        reader.start()
        try:
            line = lines.get(timeout=5)
        except queue.Empty:
            process.close()
            reader.join(5)
            self.fail('Owned parent did not report its synthetic child')
        reader.join(5)
        self.assertFalse(reader.is_alive())
        child = psutil.Process(int(line.strip()))
        parent = psutil.Process(process.pid)
        self.assertTrue(child.is_running())
        self.assertTrue(parent.is_running())
        self.assertTrue(process.close())
        self.assertFalse(child.is_running())
        self.assertFalse(parent.is_running())


if __name__ == '__main__':
    unittest.main(verbosity=2)
