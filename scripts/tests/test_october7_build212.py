"""Offline build contracts: no compiler, signing script, or app is executed."""

import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "October7_VocalStudio_DAW" / "source"
NATIVE_NAME = "October7_VocalStudio_Native"
SPEC_NAME = NATIVE_NAME + ".spec"


@pytest.fixture
def builder(tmp_path, monkeypatch):
    # This helper only imports standard-library modules; never load app_native.
    spec = importlib.util.spec_from_file_location(
        "october7_build_contract212", SOURCE / "build_windows_app.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    (tmp_path / SPEC_NAME).write_text((SOURCE / SPEC_NAME).read_text(), encoding="utf-8")
    (tmp_path / "native_version_info.txt").write_text((SOURCE / "native_version_info.txt").read_text(), encoding="utf-8")
    (tmp_path / "app_native.py").write_text("# Never executed by this test.\n", encoding="utf-8")
    calls = []

    def fake_compiler(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_compiler)
    return module, tmp_path, calls


def make_output(root, name=NATIVE_NAME):
    executable = root / "dist" / name / (name + ".exe")
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"test-only compiler output")
    return executable


def test_build_uses_canonical_native_spec_and_output(builder):
    module, root, calls = builder
    make_output(root)
    assert module.build() is True, "Build must recognize the Native.exe artifact."
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command[:3] == [module.sys.executable, "-m", "PyInstaller"]
    assert command[-1] == str(root / SPEC_NAME)
    assert kwargs["cwd"] == str(root)
    assert "october7_core.py" not in " ".join(command)


def test_native_spec_matches_native_source_and_artifact():
    tree = ast.parse((SOURCE / SPEC_NAME).read_text(encoding="utf-8"))
    calls = {
        node.func.id: node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert ast.literal_eval(calls["Analysis"].args[0]) == ["app_native.py"]
    for constructor in ("EXE", "COLLECT"):
        names = [kw.value for kw in calls[constructor].keywords if kw.arg == "name"]
        assert len(names) == 1 and ast.literal_eval(names[0]) == NATIVE_NAME


def test_build_never_bundles_user_recordings_or_signs_implicitly(builder):
    module, root, calls = builder
    native = make_output(root)
    # Also expose the legacy artifact so the old recipe reaches its unsafe copies.
    legacy = make_output(root, "October7_VocalStudio_DAW")
    (root / "stems").mkdir()
    (root / "stems" / "private_take.wav").write_bytes(b"private audio fixture")
    (root / "October7_ACE_Generated.wav").write_bytes(b"private generated fixture")
    (root / "sign_release_binary.ps1").write_text("throw 'must never execute'\n")
    assert module.build() is True
    assert len(calls) == 1, "Signing must remain an explicit release action."
    assert calls[0][0][-1].endswith(SPEC_NAME)
    for target in (native.parent, legacy.parent):
        assert not (target / "stems").exists()
        assert not (target / "October7_ACE_Generated.wav").exists()


def test_missing_native_entrypoint_prevents_compiler_dispatch(builder):
    module, root, calls = builder
    (root / "app_native.py").unlink()
    assert module.build() is False
    assert calls == []


def test_compiler_failure_is_reported_without_accepting_stale_output(builder, monkeypatch):
    module, root, calls = builder
    make_output(root)

    def failing_compiler(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(module.subprocess, "run", failing_compiler)
    assert module.build() is False
    assert len(calls) == 1


def test_missing_output_is_not_success(builder):
    module, _root, calls = builder
    assert module.build() is False
    assert len(calls) == 1


def test_native_release_has_explicit_windows_version_identity():
    tree = ast.parse((SOURCE / SPEC_NAME).read_text(encoding="utf-8"))
    exe = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name) and node.func.id == "EXE")
    assert any(kw.arg == "version" for kw in exe.keywords)
    version_file = SOURCE / "native_version_info.txt"
    assert version_file.is_file()
    version_tree = ast.parse(version_file.read_text(encoding="utf-8"))
    fixed = next(node for node in ast.walk(version_tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "FixedFileInfo")
    fields = {kw.arg: ast.literal_eval(kw.value) for kw in fixed.keywords}
    assert fields["filevers"] == fields["prodvers"] == (1, 0, 212, 0)
    literals = {node.value for node in ast.walk(version_tree) if isinstance(node, ast.Constant)
                and isinstance(node.value, str)}
    assert "October7_VocalStudio_Native.exe" in literals
    assert "1.0.212.0" in literals


def test_native_spec_excludes_ambient_ai_and_disables_upx():
    tree = ast.parse((SOURCE / SPEC_NAME).read_text(encoding="utf-8"))
    calls = {node.func.id: node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name)}
    excludes = next(kw.value for kw in calls["Analysis"].keywords if kw.arg == "excludes")
    assert {"backend", "core", "openai", "ccxt", "transformers", "yt_dlp"} <= set(ast.literal_eval(excludes))
    for constructor in ("EXE", "COLLECT"):
        upx = next(kw.value for kw in calls[constructor].keywords if kw.arg == "upx")
        assert ast.literal_eval(upx) is False


def test_native_manifest_never_requires_administrator_for_audio():
    tree = ast.parse((SOURCE / SPEC_NAME).read_text(encoding="utf-8"))
    exe = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name) and node.func.id == "EXE")
    elevation = next(kw.value for kw in exe.keywords if kw.arg == "uac_admin")
    assert ast.literal_eval(elevation) is False


def test_missing_version_resource_prevents_compiler_dispatch(builder):
    module, root, calls = builder
    (root / "native_version_info.txt").unlink()
    assert module.build() is False
    assert calls == []
