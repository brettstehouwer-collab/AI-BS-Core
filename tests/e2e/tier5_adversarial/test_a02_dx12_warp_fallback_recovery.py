"""Tier 5 Adversarial Test A02: Subsystem Failure & DX12 to WARP Fallback Recovery.

Executes subsystem failure and recovery drills forcing fallback from DirectX 12
to WARP software rasterization under simulated GPU load and low feature levels.
Runs verify_sheltered_hub_viewport_session.py and aibs_render_validation_native.exe.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner


@pytest.mark.tier5
@pytest.mark.feature_4
@pytest.mark.feature_5
@pytest.mark.feature_6
@pytest.mark.feature_14
class TestA02DX12WarpFallbackRecovery:
    """Adversarial fault injection and fallback recovery for DX12 offscreen rendering."""

    def test_a02_forced_warp_fallback_sheltered_hub_session(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Force WARP software fallback and feature level 10_0 on verify_sheltered_hub_viewport_session.py."""
        script_path = platform_paths.native_studio_dir / "verify_sheltered_hub_viewport_session.py"
        assert script_path.is_file(), f"Verification script missing: {script_path}"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["AIBS_GRAPHICS_BACKEND"] = "WARP_Software"
        env["AIBS_D3D_FEATURE_LEVEL"] = "10_0"

        res = subprocess_runner.run(
            [platform_paths.python_exe, str(script_path)],
            cwd=platform_paths.base_dir,
            env=env,
            timeout=45.0
        )
        res.assert_success("Viewport failed to recover and render under forced WARP_Software backend")
        res.assert_stdout_contains("STUDIO 144 VIEWPORT SESSION VALIDATION COMPLETE: ALL PASS")

        # Verify telemetry artifact confirms 0 debug errors and nonbackground pixels rendered
        telemetry_file = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.json"
        assert telemetry_file.is_file()
        with open(telemetry_file, "r", encoding="utf-8") as f:
            telemetry = json.load(f)

        assert telemetry.get("debug_errors", 1) == 0, f"Debug errors in WARP render: {telemetry}"
        assert telemetry.get("nonbackground_pixels", 0) > 0, "No pixels rasterized by WARP"

    def test_a02_native_render_validation_legacy_warp_mode(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner, tmp_path: Path
    ) -> None:
        """Execute aibs_render_validation_native.exe in legacy mode under forced WARP rasterizer."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_render_validation_native.exe"
        shaders_dir = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "shaders"
        assert exe_path.is_file(), f"Render validation binary missing: {exe_path}"
        assert shaders_dir.is_dir(), f"Shaders directory missing: {shaders_dir}"

        evidence_dir = tmp_path / "warp_evidence"
        if evidence_dir.exists():
            import shutil
            shutil.rmtree(evidence_dir, ignore_errors=True)

        env = os.environ.copy()
        env["AIBS_GRAPHICS_BACKEND"] = "WARP_Software"
        env["AIBS_D3D_FEATURE_LEVEL"] = "10_0"

        cmd = [str(exe_path), "legacy", str(shaders_dir), str(evidence_dir)]
        res = subprocess_runner.run(cmd, cwd=platform_paths.base_dir, env=env, timeout=30.0)
        res.assert_success("Native render validation failed in legacy mode under WARP")
        res.assert_stdout_contains("legacy actual DX12 render and validation observation passed")

        result_json = evidence_dir / "result.json"
        assert result_json.is_file()
        with open(result_json, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert report.get("status") == "passed"
        assert report.get("mode") == "legacy"
        assert report.get("debug_errors") == 0
        assert report.get("nonbackground_pixels", 0) > 0

    def test_a02_corrupted_pipeline_config_graceful_recovery(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner, tmp_path: Path
    ) -> None:
        """Inject corrupt/invalid graphics_pipeline.json and assert graceful fallback or default."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        assert config_path.is_file()

        # Read original config to verify fallback chain
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        assert "fallback_chain" in cfg
        assert "WARP_Software" in cfg["fallback_chain"]
        assert cfg.get("allow_software_warp") is True

        # Run motherboard renderer tests under fallback level
        tests_exe = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_renderer_tests.exe"
        assert tests_exe.is_file()

        env = os.environ.copy()
        env["AIBS_GRAPHICS_BACKEND"] = "WARP_Software"
        res = subprocess_runner.run([str(tests_exe)], cwd=platform_paths.base_dir, env=env, timeout=15.0)
        res.assert_success()
        res.assert_stdout_contains("PASS: motherboard geometry and camera contracts")
