"""Tier 4 Real-World Application Scenario 09: Autonomous E2E Test Suite Self-Verification & Telemetry Export.

Exercises: F14 (Native Studio Audit), F15 (FastAPI Audit), F17 (Frontend Build),
F18 (Opaque-Box E2E Test Suite Runner).
"""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner, ArtifactCleaner


@pytest.mark.tier4
class TestS09TestSuiteTelemetryExport:
    """Scenario 09: Autonomous E2E Test Suite Self-Verification & Telemetry Export."""

    def test_s09_execute_runner_with_json_and_xml_reporting(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner, test_artifact_cleaner: ArtifactCleaner
    ) -> None:
        """Run E2E test runner on feature 16, exporting both JSON and JUnit XML reports."""
        json_report = test_artifact_cleaner.tmp_path / "scenario_report.json"
        xml_report = test_artifact_cleaner.tmp_path / "scenario_report.xml"
        runner_py = platform_paths.base_dir / "tests" / "e2e" / "run_e2e_tests.py"
        python_exe = r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe"

        res = subprocess_runner.run(
            [
                python_exe,
                str(runner_py),
                "--tier",
                "1",
                "--feature",
                "16",
                "--json-report",
                str(json_report),
                "--xml-report",
                str(xml_report),
            ],
            cwd=platform_paths.base_dir,
            timeout=90,
        )
        res.assert_success("Runner execution failed for scenario 09")

        # 1. Verify JSON report contents
        assert json_report.exists()
        with open(json_report, "r", encoding="utf-8") as f:
            jdata = json.load(f)

        assert "summary" in jdata
        summary = jdata["summary"]
        assert summary.get("total_tests", 0) > 0
        assert summary.get("passed", 0) > 0
        assert summary.get("failed") == 0
        assert summary.get("status") == "PASSED"

        # 2. Verify JUnit XML report structure
        assert xml_report.exists()
        tree = ET.parse(xml_report)
        root = tree.getroot()
        testcases = root.findall(".//testcase")
        assert len(testcases) > 0, "JUnit XML contains no <testcase> elements"

        # 3. Verify clean artifact isolation
        assert json_report.stat().st_size > 100
        assert xml_report.stat().st_size > 100
