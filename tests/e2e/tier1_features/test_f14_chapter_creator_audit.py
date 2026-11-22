"""Tier 1 Feature 14: Chapter Creator & Native Studio Audit.

Requirement: Native GPU and unit tests passing with 0 errors across 130 CTest targets,
native DX12 viewport executable verification, and Sheltered Hub spatial verification.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner, SubprocessResult


@pytest.mark.tier1
@pytest.mark.feature(14)
@pytest.mark.feature_14
class TestF14ChapterCreatorAudit:
    """Feature 14: Chapter Creator & Native Studio Audit Test Suite."""

    def test_f14_ctest_target_inventory_count(self, platform_paths: PlatformPaths) -> None:
        """Verify that at least 130 CTest targets are registered in the native build."""
        cmake_test_file = platform_paths.base_dir / "engine" / "out" / "windows-msvc" / "CTestTestfile.cmake"
        assert cmake_test_file.exists(), f"CTestTestfile.cmake missing at {cmake_test_file}"

        content = cmake_test_file.read_text(encoding="utf-8", errors="replace")
        # Count test declarations in CTestTestfile.cmake
        add_tests = [line for line in content.splitlines() if line.strip().startswith("add_test(")]
        assert len(add_tests) >= 130, f"Expected >= 130 CTest declarations, found {len(add_tests)}"

        # Query CTest tool directly if available
        ctest_exe = Path(r"C:\Program Files\CMake\bin\ctest.exe")
        if ctest_exe.exists():
            proc = subprocess.run(
                [str(ctest_exe), "--test-dir", str(cmake_test_file.parent), "-C", "Debug", "-N"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert proc.returncode == 0, f"ctest -N failed: {proc.stderr}"
            # Extract total test count line
            match_total = [line for line in proc.stdout.splitlines() if "Total Tests:" in line]
            assert match_total, f"Could not find Total Tests in ctest output:\n{proc.stdout}"
            total_tests = int(match_total[0].split(":")[1].strip())
            assert total_tests >= 130, f"Expected >= 130 CTest targets, got {total_tests}"

    def test_f14_native_creator_viewport_binary_artifact(self, platform_paths: PlatformPaths) -> None:
        """Verify that the native DirectX 12 creator viewport executable exists and is valid."""
        exe_path = platform_paths.base_dir / "engine" / "out" / "windows-msvc" / "Debug" / "aibs_creator_viewport.exe"
        assert exe_path.exists(), f"Native viewport binary missing: {exe_path}"
        assert exe_path.is_file(), f"Path is not a regular file: {exe_path}"

        size = exe_path.stat().st_size
        assert size > 500_000, f"Executable size too small ({size} bytes), binary may be corrupt"

        # Verify Windows PE executable header
        with open(exe_path, "rb") as f:
            header = f.read(2)
            assert header == b"MZ", f"Binary header mismatch, expected 'MZ', got {header!r}"

    def test_f14_sheltered_hub_viewport_session_probe(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Run offscreen Sheltered Hub viewport session and verify telemetry JSON & BMP."""
        verify_script = platform_paths.native_studio_dir / "verify_sheltered_hub_viewport_session.py"
        assert verify_script.exists(), f"Verification script missing: {verify_script}"

        # Run script with project environment
        python_candidates = [
            r"C:\AI-BS\pyppeteer_env\Scripts\python.exe",
            r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe",
        ]
        chosen_py = next((p for p in python_candidates if Path(p).exists()), "python")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)
        env["QT_QPA_PLATFORM"] = "offscreen"

        res = subprocess_runner.run(
            [chosen_py, str(verify_script)],
            cwd=platform_paths.base_dir,
            env=env,
            timeout=120,
        )
        res.assert_success("Sheltered Hub viewport session execution failed")

        # Verify output telemetry JSON
        telemetry_json = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.json"
        assert telemetry_json.exists(), f"Telemetry JSON missing: {telemetry_json}"

        with open(telemetry_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("debug_errors") == 0, f"DirectX 12 debug errors detected: {data.get('debug_errors')}"
        assert data.get("nonbackground_pixels", 0) > 0, "No geometry rendered in viewport projection"

        # Verify output BMP
        bmp_path = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.bmp"
        assert bmp_path.exists(), f"Viewport projection BMP missing: {bmp_path}"
        assert bmp_path.stat().st_size > 100_000, "Rendered BMP too small to contain scene frame"

    def test_f14_sheltered_hub_fields_unit_suite(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Run Sheltered Hub stations and spatial zone unit tests and assert 100% pass."""
        test_file = platform_paths.native_studio_dir / "tests" / "test_sheltered_hub_fields.py"
        assert test_file.exists(), f"Unit test file missing: {test_file}"

        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)

        res = subprocess_runner.run(
            [python_exe, str(test_file)],
            cwd=platform_paths.base_dir,
            env=env,
            timeout=30,
        )
        res.assert_success("Sheltered Hub unit tests failed")
        assert "OK" in res.stderr or res.returncode == 0

    def test_f14_ctest_core_contracts_execution(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Execute core C++ contract tests via ctest CLI and verify 0 failures."""
        ctest_exe = Path(r"C:\Program Files\CMake\bin\ctest.exe")
        test_dir = platform_paths.base_dir / "engine" / "out" / "windows-msvc"
        if not ctest_exe.exists() or not test_dir.exists():
            pytest.skip("CMake ctest.exe or test_dir not available")

        res = subprocess_runner.run(
            [str(ctest_exe), "--test-dir", str(test_dir), "-C", "Debug", "-R", "asset_contracts", "-V"],
            cwd=platform_paths.base_dir,
            timeout=45,
        )
        res.assert_success("CTest execution failed")
        res.assert_stdout_contains("100% tests passed out of 2")

    def test_f14_m5_audit_native_studio_pass(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Execute the M5 subsystem audit script and verify the native_studio subsystem passes."""
        audit_script = platform_paths.base_dir / "tests" / "run_m5_subsystem_health_audit.py"
        assert audit_script.exists(), f"Audit script missing: {audit_script}"

        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)

        res = subprocess_runner.run(
            [python_exe, str(audit_script)],
            cwd=platform_paths.base_dir,
            env=env,
            timeout=120,
        )
        report_json = platform_paths.base_dir / "tests" / "m5_audit_report.json"
        assert report_json.exists(), f"Audit report missing: {report_json}"

        with open(report_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        native_sub = data.get("subsystems", {}).get("native_studio", {})
        assert native_sub.get("passed") is True, f"Native studio audit failed: {native_sub.get('failures')}"
