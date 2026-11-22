"""Tier 1 Feature 18: Opaque-Box E2E Test Suite Runner Self-Test.

Requirement: Master test runner harness validating multi-tier execution (Tiers 1-4),
CLI arguments (--tier, --feature, --json-report, --xml-report), pytest markers, and reporting.
"""

from __future__ import annotations

import configparser
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner, ArtifactCleaner


@pytest.mark.tier1
@pytest.mark.feature(18)
@pytest.mark.feature_18
class TestF18E2ESuiteSelfTest:
    """Feature 18: Opaque-Box E2E Test Suite Self-Test."""

    def test_f18_runner_cli_help_flag(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Verify the test runner CLI prints usage and supports all standard flags."""
        runner_py = platform_paths.base_dir / "tests" / "e2e" / "run_e2e_tests.py"
        assert runner_py.exists(), f"Runner script missing at {runner_py}"

        python_exe = r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe"
        res = subprocess_runner.run([python_exe, str(runner_py), "--help"], timeout=15)
        res.assert_success()
        res.assert_stdout_contains("--tier")
        res.assert_stdout_contains("--feature")
        res.assert_stdout_contains("--json-report")
        res.assert_stdout_contains("--xml-report")

    def test_f18_runner_feature_registry_integrity(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify FEATURE_REGISTRY contains all 18 canonical platform features."""
        from tests.e2e.run_e2e_tests import FEATURE_REGISTRY, TIER_CONFIG

        assert len(FEATURE_REGISTRY) == 18, f"Expected 18 features registered, got {len(FEATURE_REGISTRY)}"
        for fid in range(1, 19):
            assert fid in FEATURE_REGISTRY, f"Feature {fid} missing from FEATURE_REGISTRY"
            meta = FEATURE_REGISTRY[fid]
            assert "code" in meta and "name" in meta
            expected_code = f"F{fid:02d}"
            assert meta["code"] == expected_code

        assert "1" in TIER_CONFIG and "2" in TIER_CONFIG and "3" in TIER_CONFIG and "4" in TIER_CONFIG
        assert TIER_CONFIG["1"]["min_target"] == 90
        assert TIER_CONFIG["2"]["min_target"] == 90
        assert TIER_CONFIG["3"]["min_target"] == 18
        assert TIER_CONFIG["4"]["min_target"] == 9

    def test_f18_runner_scenario_feature_map_completeness(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify SCENARIO_FEATURE_MAP contains all 9 scenarios mapping to valid features."""
        from tests.e2e.run_e2e_tests import SCENARIO_FEATURE_MAP

        assert len(SCENARIO_FEATURE_MAP) == 9, f"Expected 9 scenarios, got {len(SCENARIO_FEATURE_MAP)}"
        for s_num in range(1, 10):
            s_key = f"s{s_num:02d}"
            assert s_key in SCENARIO_FEATURE_MAP, f"Scenario {s_key} missing from SCENARIO_FEATURE_MAP"
            feats = SCENARIO_FEATURE_MAP[s_key]
            assert len(feats) >= 3, f"Scenario {s_key} should exercise >=3 features, has {len(feats)}"
            for f in feats:
                assert 1 <= f <= 18, f"Invalid feature index {f} in scenario {s_key}"

    def test_f18_conftest_fixtures_availability(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify conftest.py defines all required opaque-box test fixtures."""
        conftest_path = platform_paths.base_dir / "tests" / "e2e" / "conftest.py"
        assert conftest_path.exists(), f"conftest.py missing: {conftest_path}"

        code = conftest_path.read_text(encoding="utf-8", errors="replace")
        required_fixtures = [
            "platform_paths",
            "subprocess_runner",
            "run_cmd",
            "http_client",
            "test_artifact_cleaner",
            "clean_artifacts",
        ]
        for fixture_name in required_fixtures:
            assert f"def {fixture_name}" in code, f"Fixture '{fixture_name}' not defined in conftest.py"

    def test_f18_pytest_ini_markers_registration(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify pytest.ini registers tier1..tier4 and all feature_1..feature_18 markers."""
        ini_path = platform_paths.base_dir / "tests" / "e2e" / "pytest.ini"
        assert ini_path.exists(), f"pytest.ini missing at {ini_path}"

        content = ini_path.read_text(encoding="utf-8", errors="replace")
        for tier in ["tier1", "tier2", "tier3", "tier4"]:
            assert tier in content, f"Tier marker '{tier}' missing from pytest.ini"

        for fid in range(1, 19):
            assert f"feature_{fid}:" in content, f"Marker 'feature_{fid}:' missing from pytest.ini"

    def test_f18_runner_single_feature_execution(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner, test_artifact_cleaner: ArtifactCleaner
    ) -> None:
        """Verify running master runner with --feature 17 generates valid JSON report."""
        report_file = test_artifact_cleaner.tmp_path / "test_report_f17.json"
        runner_py = platform_paths.base_dir / "tests" / "e2e" / "run_e2e_tests.py"
        python_exe = r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe"

        res = subprocess_runner.run(
            [python_exe, str(runner_py), "--tier", "1", "--feature", "17", "--json-report", str(report_file)],
            cwd=platform_paths.base_dir,
            timeout=60,
        )
        res.assert_success("Runner invocation for --tier 1 --feature 17 failed")
        assert report_file.exists(), "JSON report was not written"

        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "summary" in data
        summary = data["summary"]
        assert summary.get("total_tests", 0) > 0
        assert summary.get("passed", 0) > 0
        assert summary.get("failed") == 0
        assert "feature_coverage" in data
        f17_cov = next((f for f in data["feature_coverage"] if f["code"] == "F17"), None)
        assert f17_cov is not None and f17_cov["passed"] > 0
