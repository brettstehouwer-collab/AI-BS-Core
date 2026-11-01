"""Installer integrity regressions: AST-only app method, fake UI/process/copy APIs.

No installed code is imported, no installer is launched, no registry/audio/GUI I/O.
All file writes are dedicated C fixtures. Destructive copies/deletes are intercepted.
"""
from __future__ import annotations
import ast
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
import uuid

ROOT = Path('C:/AI-BS')
SOURCE = Path(os.environ.get('OCTOBER7_INSTALLER_AUDIT_SOURCE', ROOT/'October7_VocalStudio_DAW'))
WORK = ROOT/'backups/october7_audit212/security/fixtures'


class Var:
    def __init__(self, value): self.value = value
    def get(self): return self.value


class Widget:
    def config(self, **kwargs): pass
    def stop(self): pass


def method_source():
    tree = ast.parse((SOURCE/'setup_installer.py').read_text(encoding='utf-8-sig'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'InstallerWizard')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'execute_installation')
    return ast.Module(body=[method], type_ignores=[])


class Installer212IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.base = WORK/uuid.uuid4().hex
        self.base.mkdir(parents=True)
        self.source = self.base/'package'
        self.source.mkdir()
        (self.source/'engine.txt').write_text('TEST ONLY, NOT AN EXECUTABLE')
        self.target = self.base/'installed'
        self.events = []
        self.commands = []
        self.messages = []
        self.logs = []
        self.finished = False
        self.subprocess_rc = 0

    def run_method(self, *, target=None, desktop=False, startmenu=False):
        owner = self
        class CopyApi:
            @staticmethod
            def rmtree(path, *args, **kwargs):
                owner.events.append(('DELETE_TREE', str(path)))
                raise RuntimeError('AUDIT_BLOCKED_DESTRUCTIVE_OPERATION')
            @staticmethod
            def copytree(src, dst, *args, **kwargs):
                owner.events.append(('COPY_TREE', str(src), str(dst)))
            @staticmethod
            def copy2(src, dst, *args, **kwargs):
                owner.events.append(('COPY_FILE', str(src), str(dst)))
        class ProcessApi:
            @staticmethod
            def run(command, **kwargs):
                owner.commands.append(command)
                return SimpleNamespace(returncode=owner.subprocess_rc, stdout='', stderr='SYNTHETIC_FAILURE' if owner.subprocess_rc else '')
        def completed(delay, callback):
            owner.finished = True
        fake = SimpleNamespace(target_path=Var(str(target or self.target)),
            opt_cert=Var(False), opt_desktop=Var(desktop), opt_startmenu=Var(startmenu),
            status_lbl=Widget(), progress=Widget(), btn_cancel=Widget(),
            append_log=self.logs.append, after=completed, show_step=lambda step: None)
        env = {'USERPROFILE': str(self.base/'profile'), 'APPDATA': str(self.base/'appdata')}
        namespace = {'Path': Path, 'SOURCE_DIR': self.source, 'BASE_DIR': self.source,
            'shutil': CopyApi, 'subprocess': ProcessApi, 'os': SimpleNamespace(environ=env),
            'messagebox': SimpleNamespace(showerror=lambda *args: owner.messages.append(args)),
            'hashlib': __import__('hashlib')}
        exec(compile(method_source(), 'audited_execute_installation212', 'exec'), namespace)
        namespace['execute_installation'](fake)
        return fake

    def test_same_source_and_destination_rejected_before_copy_or_delete(self):
        (self.source/'takes').mkdir()
        self.run_method(target=self.source)
        self.assertEqual(self.events, [], 'Must reject self-install before file operations')
        self.assertTrue(self.messages)
        self.assertFalse(self.finished)

    def test_destination_inside_source_rejected_before_creation_or_copy(self):
        nested = self.source/'nested_install'
        self.run_method(target=nested)
        self.assertFalse(nested.exists(), 'Nested target must be rejected before mkdir')
        self.assertEqual(self.events, [])
        self.assertFalse(self.finished)

    def test_upgrade_preserves_existing_recording_directories(self):
        (self.source/'takes').mkdir()
        (self.source/'takes/new.wav').write_bytes(b'TEST ONLY')
        (self.target/'takes').mkdir(parents=True)
        original = self.target/'takes/original.wav'
        original.write_bytes(b'ORIGINAL TEST TAKE')
        self.run_method()
        self.assertFalse(any(event[0] == 'DELETE_TREE' for event in self.events))
        self.assertFalse(any(event[0] == 'COPY_TREE' and Path(event[1]).name == 'takes' for event in self.events))
        self.assertEqual(original.read_bytes(), b'ORIGINAL TEST TAKE')
        self.assertTrue(self.finished, self.messages)

    def test_all_shortcut_options_off_is_valid_installation(self):
        self.run_method(desktop=False, startmenu=False)
        self.assertEqual(self.messages, [])
        self.assertTrue(self.finished)

    def test_startmenu_off_does_not_reference_unbound_path(self):
        self.run_method(desktop=True, startmenu=False)
        self.assertEqual(self.messages, [])
        self.assertTrue(self.finished)

    def test_legitimate_apostrophe_path_remains_one_powershell_literal(self):
        target = self.base/"O'Brien"
        self.run_method(target=target, desktop=True, startmenu=True)
        self.assertTrue(self.commands)
        for command in self.commands:
            if command[0].lower() != 'powershell': continue
            script = command[command.index('-Command')+1]
            matches = re.findall(r"\$Shortcut\.WorkingDirectory\s*=\s*'((?:''|[^'])*)'\s*$", script, re.MULTILINE)
            self.assertEqual([value.replace("''", "'") for value in matches], [str(target)])

    def test_shortcut_command_failure_cannot_report_install_complete(self):
        self.subprocess_rc = 1
        self.run_method(desktop=True, startmenu=True)
        self.assertTrue(self.messages, 'Failed shortcut process must produce an error')
        self.assertFalse(self.finished)

    def test_native_release_retains_preferred_shortcut_target(self):
        self.target.mkdir()
        (self.target/'October7_VocalStudio_Native.exe').write_text('PLAIN TEST FILE, NEVER EXECUTED')
        self.run_method(desktop=True)
        self.assertTrue(self.finished)
        script = self.commands[0][self.commands[0].index('-Command')+1]
        target_lines = re.findall(r"\$Shortcut\.TargetPath\s*=\s*'((?:''|[^'])*)'\s*$", script, re.MULTILINE)
        self.assertEqual(target_lines, [str(self.target/'October7_VocalStudio_Native.exe')])

    def test_certificate_trust_never_imported_by_installers(self):
        for name in ('setup_installer.py', 'Install_Wizard.ps1', 'Install_October7_DAW.bat'):
            text = (SOURCE/name).read_text(encoding='utf-8-sig')
            self.assertNotIn('-addstore', text.casefold(), name)
        tree = ast.parse((SOURCE/'setup_installer.py').read_text(encoding='utf-8-sig'))
        values = [kw.value.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Attribute) and t.attr == 'opt_cert' for t in node.targets)
            and isinstance(node.value, ast.Call) for kw in node.value.keywords if kw.arg == 'value' and isinstance(kw.value, ast.Constant)]
        self.assertEqual(values, [False])

    def test_no_installer_or_uninstaller_generates_recursive_directory_deletion(self):
        for name in ('setup_installer.py', 'Install_Wizard.ps1', 'Install_October7_DAW.bat', 'Uninstall_October7_DAW.bat'):
            text = (SOURCE/name).read_text(encoding='utf-8-sig')
            self.assertNotRegex(text.casefold(), r'\brmdir\s+/s|\brd\s+/s|shutil\.rmtree\s*\(', name)

    def test_reference_python_installer_delegates_to_repaired_root(self):
        path = SOURCE/'source/setup_installer.py'
        text = path.read_text(encoding='utf-8-sig')
        tree = ast.parse(text)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
            and node.func.value.id == 'runpy' and node.func.attr == 'run_path']
        self.assertEqual(len(calls), 1, 'Reference installer must delegate to root instead of keeping unsafe duplicate logic')
        self.assertNotIn('-addstore', text.casefold())
        self.assertNotIn('shutil.rmtree', text.casefold())
        captured = []
        # Exclude imports and substitute only the root-script runner; no GUI or installer runs.
        module = ast.Module(body=[node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))], type_ignores=[])
        exec(compile(module, str(path), 'exec'), {'Path': Path, '__file__': str(path),
            '__name__': '__main__', 'runpy': SimpleNamespace(run_path=lambda *args, **kwargs: captured.append((args, kwargs)))})
        self.assertEqual(captured, [((str(SOURCE/'setup_installer.py'),), {'run_name': '__main__'})])

    def test_reference_powershell_installer_declares_safe_root_delegation(self):
        text = (SOURCE/'source/Install_Wizard.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('$RootInstaller', text, 'Reference installer must resolve a root delegate')
        self.assertRegex(text, r'(?m)^\s*&\s+\$RootInstaller\s+@args\s*$')
        self.assertIn('Join-Path', text)
        self.assertIn('Test-Path -LiteralPath $RootInstaller', text)
        self.assertNotIn('-addstore', text.casefold())
        self.assertNotRegex(text.casefold(), r'\brmdir\s+/s|invoke-expression')

    def test_reference_batch_installer_delegates_and_retains_exit_code(self):
        text = (SOURCE/'source/Install_October7_DAW.bat').read_text(encoding='utf-8-sig')
        self.assertRegex(text.casefold(), r'(?m)^call\s+"%~dp0\.\.\\install_october7_daw\.bat"\s*$')
        self.assertIn('exit /b %ERRORLEVEL%', text)
        self.assertNotIn('-addstore', text.casefold())
        self.assertNotRegex(text.casefold(), r'\brmdir\s+/s|\bxcopy\b')


if __name__ == '__main__': unittest.main()
