"""Trusted updater functions/dialog with temporary fixtures and fake process/Qt APIs."""
import ast
import copy
from pathlib import Path
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForbiddenSourceRoot:
    def __init__(self):
        self.accesses = 0

    def __truediv__(self, value):
        self.accesses += 1
        raise AssertionError("Actual source-root IO forbidden")

    def __str__(self):
        self.accesses += 1
        return "forbidden-source-placeholder"


class FakeProcesses:
    CREATE_NEW_PROCESS_GROUP = 512

    def __init__(self):
        self.calls = []
        self.behind = "2"
        self.dirty = True
        self.pull_code = 0

    def run(self, args, **kwargs):
        self.calls.append(("run", list(args), kwargs))
        command = args[1:]
        stdout, stderr, code = "", "", 0
        if command == ["rev-parse", "--short", "HEAD"]:
            stdout = "fixture-head"
        elif command == ["rev-parse", "--abbrev-ref", "HEAD"]:
            stdout = "fixture-branch"
        elif command == ["rev-parse", "--abbrev-ref", "@{u}"]:
            stdout = "origin/fixture-branch"
        elif command and command[0] == "rev-list":
            stdout = self.behind
        elif command and command[0] == "log":
            stdout = "fixture-a Synthetic change\nfixture-b Synthetic fix"
        elif command == ["status", "--porcelain"]:
            stdout = " M synthetic.txt" if self.dirty else ""
        elif command and command[0] == "pull":
            stdout, stderr, code = "Synthetic pull output", "Synthetic pull refusal" if self.pull_code else "", self.pull_code
        return types.SimpleNamespace(stdout=stdout, stderr=stderr, returncode=code)

    def Popen(self, args, **kwargs):
        self.calls.append(("Popen", list(args), kwargs))
        return object()


class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class Widget:
    text_values = []

    def __init__(self, *args, **kwargs):
        self.text = args[0] if args and isinstance(args[0], str) else ""
        self.enabled = True
        self.clicked = Signal()
        if self.text:
            self.text_values.append(self.text)

    def setText(self, value):
        self.text = value

    def setPlainText(self, value):
        self.text = value

    def setEnabled(self, value):
        self.enabled = value

    def setWindowTitle(self, value):
        self.text_values.append(value)

    def setPlaceholderText(self, value):
        self.text_values.append(value)

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeBus:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def submit(self, worker, **kwargs):
        self.calls.append((worker, kwargs))


def load_controlled(frozen, bundle, source):
    path = ROOT / "native_studio/updater.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    # Import no application modules. Keep actual functions/class and only
    # literal module constants, never the real AI_BS_ROOT assignment.
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            nodes.append(copy.deepcopy(node))
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            nodes.append(copy.deepcopy(node))
    unit = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(unit)
    processes, bus = FakeProcesses(), FakeBus()
    app = types.SimpleNamespace(quit=lambda: setattr(app, "quit_called", True), quit_called=False)
    fake_sys = types.SimpleNamespace(frozen=frozen, _MEIPASS=str(bundle), executable=str(bundle / "Studio.exe"), platform="win32")
    names = ["QDialog", "QFrame", "QHBoxLayout", "QLabel", "QProgressBar", "QPushButton", "QScrollArea", "QTextEdit", "QVBoxLayout", "QWidget", "QFont", "QColor"]
    namespace = {
        "Path": Path, "sys": fake_sys, "subprocess": processes,
        "AI_BS_ROOT": source, "EngineBus": lambda: bus,
        "QApplication": app, "PALETTE": {"panel": "#000000", "text": "#ffffff"},
        "apply_dark_titlebar": lambda widget: None,
        **{name: Widget for name in names},
    }
    exec(compile(unit, str(path), "exec"), namespace)
    return namespace, processes, bus, fake_sys, app


class FrozenUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aibs-updater-controlled-")
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / "bundle"
        self.source = Path(self.temp.name) / "synthetic-source"
        self.bundle.mkdir()
        self.source.mkdir()
        (self.bundle / "version.txt").write_text("v1.2.3\n", encoding="utf-8")
        (self.source / "version.txt").write_text("v9.8.7\n", encoding="utf-8")
        Widget.text_values = []

    def frozen(self):
        forbidden = ForbiddenSourceRoot()
        return (*load_controlled(True, self.bundle, forbidden), forbidden)

    def test_packaged_version_is_independent_of_mutable_source(self):
        ns, _, _, _, _ = load_controlled(True, self.bundle, self.source)
        self.assertEqual(ns["get_local_version"](), "v1.2.3")
        (self.source / "version.txt").write_text("v8.0.0", encoding="utf-8")
        self.assertEqual(ns["get_local_version"](), "v1.2.3")

    def test_packaged_missing_version_never_reads_source_or_claims_legacy_version(self):
        (self.bundle / "version.txt").unlink()
        ns, _, _, _, _, forbidden = self.frozen()
        self.assertEqual(ns["get_local_version"](), "unknown")
        self.assertEqual(forbidden.accesses, 0)

    def test_packaged_empty_version_reports_unknown(self):
        (self.bundle / "version.txt").write_text(" \n", encoding="utf-8")
        ns, _, _, _, _, forbidden = self.frozen()
        self.assertEqual(ns["get_local_version"](), "unknown")
        self.assertEqual(forbidden.accesses, 0)

    def test_packaged_missing_bundle_root_never_uses_working_directory(self):
        ns, _, _, fake_sys, _, forbidden = self.frozen()
        del fake_sys._MEIPASS
        self.assertEqual(ns["get_local_version"](), "unknown")
        self.assertEqual(forbidden.accesses, 0)

    def test_packaged_check_is_installer_required_without_git(self):
        ns, processes, _, _, _, forbidden = self.frozen()
        result = ns["check_for_updates_worker"]()
        self.assertTrue(result.get("installer_required"))
        self.assertFalse(result["has_updates"])
        self.assertFalse(result.get("update_check_performed", True))
        self.assertEqual(result["version"], "v1.2.3")
        self.assertEqual(result["incoming_commits"], [])
        self.assertIn("installer", result["status_message"].lower())
        self.assertEqual(processes.calls, [])
        self.assertEqual(forbidden.accesses, 0)

    def test_packaged_apply_refuses_without_subprocess_or_repository_io(self):
        ns, processes, _, _, _, forbidden = self.frozen()
        result = ns["apply_update_worker"]()
        self.assertFalse(result["success"])
        self.assertTrue(result.get("installer_required"))
        self.assertIn("installer", result["message"].lower())
        self.assertEqual(result["output"], "")
        self.assertEqual(processes.calls, [])
        self.assertEqual(forbidden.accesses, 0)

    def test_packaged_dialog_has_installer_copy_and_no_sync_promise(self):
        ns, _, bus, _, _, _ = self.frozen()
        dialog = ns["UpdateDialog"](bus=bus)
        shown = " ".join(Widget.text_values + [dialog.lbl_status.text, dialog.lbl_details.text, dialog.txt_log.text]).lower()
        self.assertIn("installer", shown)
        for forbidden in ("git", "origin/main", "hot-reload", "hot-restart", "no rebuild", "zero pyinstaller", "probing origin", "fully synced"):
            self.assertNotIn(forbidden, shown)
        self.assertEqual(bus.calls, [])
        self.assertFalse(dialog.btn_update.enabled)

    def test_packaged_check_handler_ignores_malformed_available_update_payload(self):
        ns, _, bus, _, _, forbidden = self.frozen()
        dialog = ns["UpdateDialog"](bus=bus)
        dialog._on_check_result({"has_updates": True, "version": "untrusted-version", "commits_behind": 99, "incoming_commits": ["untrusted-change"]})
        self.assertFalse(dialog.btn_update.enabled)
        self.assertIn("v1.2.3", dialog.badge_version.text)
        self.assertNotIn("untrusted", dialog.badge_version.text + dialog.txt_log.text)
        self.assertIn("installer", dialog.lbl_status.text.lower())
        self.assertEqual(forbidden.accesses, 0)

    def test_packaged_apply_handler_never_claims_reload_from_malformed_success(self):
        ns, processes, bus, _, _, _ = self.frozen()
        dialog = ns["UpdateDialog"](bus=bus)
        dialog.start_update()
        dialog._on_update_result({"success": True, "output": "untrusted-output", "message": "untrusted-success"})
        self.assertIn("installer", dialog.lbl_status.text.lower())
        self.assertFalse(dialog.btn_update.enabled)
        self.assertNotIn("untrusted", dialog.lbl_details.text + dialog.txt_log.text)
        self.assertEqual(bus.calls, [])
        self.assertEqual(processes.calls, [])

    def test_packaged_restart_uses_installed_executable_directory(self):
        ns, processes, _, fake_sys, app, forbidden = self.frozen()
        ns["restart_studio"]()
        self.assertEqual(len(processes.calls), 1)
        kind, args, options = processes.calls[0]
        self.assertEqual((kind, args, options["cwd"]), ("Popen", [fake_sys.executable], str(self.bundle)))
        self.assertTrue(app.quit_called)
        self.assertEqual(forbidden.accesses, 0)

    def test_source_check_preserves_fake_git_contract(self):
        ns, processes, _, _, _ = load_controlled(False, self.bundle, self.source)
        result = ns["check_for_updates_worker"]()
        self.assertEqual(result["version"], "v9.8.7")
        self.assertTrue(result["has_updates"])
        self.assertTrue(result["has_local_changes"])
        self.assertEqual(result["commits_behind"], 2)
        self.assertEqual(len(result["incoming_commits"]), 2)
        self.assertEqual(len(processes.calls), 7)
        self.assertTrue(any(args == ["git", "fetch", "origin"] for _, args, _ in processes.calls))
        self.assertTrue(all(options["cwd"] == str(self.source) for _, _, options in processes.calls))

    def test_source_apply_preserves_explicit_autostash_and_result(self):
        ns, processes, _, _, _ = load_controlled(False, self.bundle, self.source)
        result = ns["apply_update_worker"]()
        self.assertTrue(result["success"])
        self.assertIn("v9.8.7", result["message"])
        self.assertEqual(processes.calls[0][1], ["git", "pull", "--autostash", "origin", "main"])
        processes.pull_code = 1
        result = ns["apply_update_worker"]()
        self.assertFalse(result["success"])
        self.assertIn("Synthetic pull refusal", result["message"])

    def test_source_dialog_and_restart_behavior_remain_available(self):
        ns, processes, bus, fake_sys, app = load_controlled(False, self.bundle, self.source)
        dialog = ns["UpdateDialog"](bus=bus)
        self.assertEqual(len(bus.calls), 1)
        self.assertEqual(bus.calls[0][0], ns["check_for_updates_worker"])
        self.assertIn("git fetch", dialog.lbl_details.text)
        dialog._on_check_result({"version": "v9.8.7", "has_updates": True, "commits_behind": 2, "incoming_commits": []})
        self.assertTrue(dialog.btn_update.enabled)
        dialog.start_update()
        self.assertEqual(bus.calls[-1][0], ns["apply_update_worker"])
        ns["restart_studio"]()
        self.assertEqual(processes.calls[-1][1], [fake_sys.executable, str(self.source / "native_studio/app.py")])
        self.assertEqual(processes.calls[-1][2]["cwd"], str(self.source))
        self.assertTrue(app.quit_called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
