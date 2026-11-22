#!/usr/bin/env python3
"""AI-BS Platform - Master End-to-End Test Runner CLI.

Executes opaque-box test suites across Tiers 1-4, filters by Tier and Feature,
captures execution metrics, exports structured JSON and JUnit XML reports,
and prints human-readable verification summaries.

Usage:
    python tests/e2e/run_e2e_tests.py [--tier {1,2,3,4,all}] [--feature {1..18}]
                                      [--json-report <filepath>] [--xml-report <filepath>]
                                      [-v|--verbose] [--timeout <seconds>]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ==============================================================================
# Feature Registry & Canonical Metadata
# ==============================================================================

FEATURE_REGISTRY: Dict[int, Dict[str, str]] = {
    1: {"code": "F01", "name": "Sheltered Hub Stations (3)"},
    2: {"code": "F02", "name": "Spatial Trigger Zones (7)"},
    3: {"code": "F03", "name": "Adam Blend Tree Animations"},
    4: {"code": "F04", "name": "Native DX12 Viewport Session"},
    5: {"code": "F05", "name": "Legacy DirectX 8/9/10 Fallbacks"},
    6: {"code": "F06", "name": "Engine Graphics Configuration"},
    7: {"code": "F07", "name": "Local ML Training Pipeline"},
    8: {"code": "F08", "name": "Distributed Training Driver"},
    9: {"code": "F09", "name": "Dataproc Serverless Template"},
    10: {"code": "F10", "name": "Dataproc Batch Deployment Script"},
    11: {"code": "F11", "name": "Synced Drive Assets 177 Files"},
    12: {"code": "F12", "name": "ChromaDB Vector Ingestion"},
    13: {"code": "F13", "name": "Microservice Vector Retrieval"},
    14: {"code": "F14", "name": "Chapter Creator & Native Studio Audit"},
    15: {"code": "F15", "name": "FastAPI Master Engine Audit"},
    16: {"code": "F16", "name": "ComfyUI RTX 4090 Bridge Audit"},
    17: {"code": "F17", "name": "Vite Frontend Build & Dev Audit"},
    18: {"code": "F18", "name": "Opaque-Box E2E Test Suite"},
}

TIER_CONFIG = {
    "1": {
        "id": "tier1",
        "dir": "tier1_features",
        "name": "Tier 1: Feature Coverage (>=5/feature)",
        "min_target": 90,
    },
    "2": {
        "id": "tier2",
        "dir": "tier2_boundary",
        "name": "Tier 2: Boundary & Corner Cases (>=5/feature)",
        "min_target": 90,
    },
    "3": {
        "id": "tier3",
        "dir": "tier3_pairwise",
        "name": "Tier 3: Pairwise Cross-Feature Integration",
        "min_target": 18,
    },
    "4": {
        "id": "tier4",
        "dir": "tier4_scenarios",
        "name": "Tier 4: Real-World Workload Scenarios",
        "min_target": 9,
    },
    "5": {
        "id": "tier5",
        "dir": "tier5_adversarial",
        "name": "Tier 5: Adversarial, Chaos & Hardening",
        "min_target": 10,
    },
}

# Scenario to Feature Mapping for Tier 4
SCENARIO_FEATURE_MAP: Dict[str, List[int]] = {
    "s01": [1, 2, 3, 4, 6],
    "s02": [4, 5, 6, 14],
    "s03": [7, 8, 9, 10],
    "s04": [11, 12, 13, 15],
    "s05": [1, 13, 15, 16],
    "s06": [14, 15, 16, 17],
    "s07": [1, 4, 11, 12, 13],
    "s08": [5, 8, 12, 15],
    "s09": [14, 15, 17, 18],
}

# Adversarial Module to Feature Mapping for Tier 5
ADVERSARIAL_FEATURE_MAP: Dict[str, List[int]] = {
    "a01": [12, 13, 15],
    "a02": [4, 5, 6, 14],
    "a03": [4, 13, 15],
    "a04": [4, 13, 15, 18],
}


# ==============================================================================
# Data Structures
# ==============================================================================

@dataclass
class TestCaseResult:
    """Detailed record for an individual test case."""

    name: str
    classname: str
    file: str
    tier: str
    features: List[int]
    outcome: str  # passed, failed, skipped, error
    duration: float
    message: Optional[str] = None


@dataclass
class TierSummary:
    """Summary metrics for a specific test tier."""

    tier_id: str
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0

    @property
    def status(self) -> str:
        if self.failed > 0:
            return "FAILED"
        if self.total == 0:
            return "EMPTY"
        return "PASSED"


@dataclass
class FeatureCoverageRecord:
    """Coverage and execution record for a platform feature."""

    feature_id: int
    code: str
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def status(self) -> str:
        if self.failed > 0:
            return "FAILED"
        if self.total == 0:
            return "UNTESTED"
        if self.passed > 0:
            return "PASSED"
        return "SKIPPED"


# ==============================================================================
# Helper Functions
# ==============================================================================

def detect_python_interpreter() -> Tuple[str, str]:
    """Detect the optimal Python interpreter for invoking pytest.

    Prefers `C:\\AI-BS\\pyppeteer_env\\Scripts\\python.exe` where all project
    dependencies (PyQt6, torch, chromadb, etc.) and pytest are installed.
    Falls back to `sys.executable`.
    """
    env_override = os.environ.get("AIBS_TEST_PYTHON")
    if env_override and Path(env_override).exists():
        return env_override, "environment variable AIBS_TEST_PYTHON"

    pyppeteer_python = Path(r"C:\AI-BS\pyppeteer_env\Scripts\python.exe")
    if pyppeteer_python.exists():
        return str(pyppeteer_python), "dedicated project venv (pyppeteer_env)"

    return sys.executable, f"current interpreter ({sys.executable})"


def resolve_test_tier(filepath: str) -> str:
    """Map a test filepath to its corresponding tier identifier."""
    norm = filepath.replace("\\", "/").lower()
    if "tier1_features" in norm:
        return "tier1"
    if "tier2_boundary" in norm:
        return "tier2"
    if "tier3_pairwise" in norm:
        return "tier3"
    if "tier4_scenarios" in norm:
        return "tier4"
    if "tier5_adversarial" in norm:
        return "tier5"
    return "unknown"


def extract_features_from_test(test_name: str, classname: str, filepath: str) -> List[int]:
    """Identify which of the 18 platform features this test exercises."""
    features_found: set[int] = set()
    combined = f"{filepath} {classname} {test_name}".lower()

    # Pattern 1: f01 .. f18 or b01 .. b18 (accounting for underscores)
    for match in re.finditer(r"(?:^|[\W_])[fb]0?([1-9]|1[0-8])(?:[\W_]|$)", combined):
        features_found.add(int(match.group(1)))

    # Pattern 2: feature_1 .. feature_18 or feature1 .. feature18
    for match in re.finditer(r"feature[_\-]?0?([1-9]|1[0-8])(?:[\W_]|$)", combined):
        features_found.add(int(match.group(1)))

    # Pattern 3: Tier 4 scenarios (s01 .. s09)
    for sc_id, feat_list in SCENARIO_FEATURE_MAP.items():
        if f"test_{sc_id}" in combined or f"scenario_{sc_id}" in combined:
            features_found.update(feat_list)

    # Pattern 4: Tier 5 adversarial (a01 .. a04)
    for adv_id, feat_list in ADVERSARIAL_FEATURE_MAP.items():
        if f"test_{adv_id}" in combined or f"adversarial_{adv_id}" in combined or f"_{adv_id}_" in combined:
            features_found.update(feat_list)

    return sorted(list(features_found))


def parse_junit_xml(xml_path: Path) -> Tuple[List[TestCaseResult], float]:
    """Parse JUnit XML report produced by pytest into structured test records."""
    if not xml_path.exists() or xml_path.stat().st_size == 0:
        return [], 0.0

    results: List[TestCaseResult] = []
    total_duration = 0.0

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Handle either <testsuites> or single <testsuite> root
        suites = root.findall(".//testsuite") if root.tag != "testsuite" else [root]
        for suite in suites:
            total_duration += float(suite.get("time", 0.0))

        for tc in root.iter("testcase"):
            name = tc.get("name", "unknown")
            classname = tc.get("classname", "")
            file_attr = tc.get("file", "")
            duration = float(tc.get("time", 0.0))

            # Determine outcome
            failure_node = tc.find("failure")
            error_node = tc.find("error")
            skipped_node = tc.find("skipped")

            if failure_node is not None:
                outcome = "failed"
                msg = failure_node.get("message") or failure_node.text
            elif error_node is not None:
                outcome = "error"
                msg = error_node.get("message") or error_node.text
            elif skipped_node is not None:
                outcome = "skipped"
                msg = skipped_node.get("message") or skipped_node.text
            else:
                outcome = "passed"
                msg = None

            tier = resolve_test_tier(file_attr or classname)
            feats = extract_features_from_test(name, classname, file_attr)

            results.append(
                TestCaseResult(
                    name=name,
                    classname=classname,
                    file=file_attr,
                    tier=tier,
                    features=feats,
                    outcome=outcome,
                    duration=duration,
                    message=msg,
                )
            )
    except Exception as exc:
        print(f"[WARN] Error parsing JUnit XML report: {exc}", file=sys.stderr)

    return results, total_duration


def build_summary_report(
    test_results: List[TestCaseResult],
    total_duration: float,
    exit_code: int,
    selected_tier: str,
    selected_feature: Optional[int],
) -> Dict[str, Any]:
    """Construct a full structured test summary dictionary."""
    total_tests = len(test_results)
    passed = sum(1 for t in test_results if t.outcome == "passed")
    failed = sum(1 for t in test_results if t.outcome in ("failed", "error"))
    skipped = sum(1 for t in test_results if t.outcome == "skipped")

    # Tier breakdown
    tier_breakdown: Dict[str, Any] = {}
    for t_key, t_info in TIER_CONFIG.items():
        t_id = t_info["id"]
        t_tests = [t for t in test_results if t.tier == t_id]
        t_total = len(t_tests)
        t_passed = sum(1 for t in t_tests if t.outcome == "passed")
        t_failed = sum(1 for t in t_tests if t.outcome in ("failed", "error"))
        t_skipped = sum(1 for t in t_tests if t.outcome == "skipped")
        t_dur = sum(t.duration for t in t_tests)
        tier_breakdown[t_id] = {
            "tier_num": t_key,
            "name": t_info["name"],
            "total": t_total,
            "passed": t_passed,
            "failed": t_failed,
            "skipped": t_skipped,
            "duration_seconds": round(t_dur, 3),
            "status": "FAILED" if t_failed > 0 else ("PASSED" if t_total > 0 else "EMPTY"),
        }

    # Feature coverage checklist
    feature_coverage: List[Dict[str, Any]] = []
    for f_id in range(1, 19):
        f_reg = FEATURE_REGISTRY[f_id]
        f_tests = [t for t in test_results if f_id in t.features]
        f_total = len(f_tests)
        f_passed = sum(1 for t in f_tests if t.outcome == "passed")
        f_failed = sum(1 for t in f_tests if t.outcome in ("failed", "error"))
        f_skipped = sum(1 for t in f_tests if t.outcome == "skipped")

        rec = FeatureCoverageRecord(
            feature_id=f_id,
            code=f_reg["code"],
            name=f_reg["name"],
            total=f_total,
            passed=f_passed,
            failed=f_failed,
            skipped=f_skipped,
        )
        feature_coverage.append(
            {
                "feature_id": f_id,
                "code": rec.code,
                "name": rec.name,
                "total": rec.total,
                "passed": rec.passed,
                "failed": rec.failed,
                "skipped": rec.skipped,
                "status": rec.status,
            }
        )

    overall_status = "PASSED" if failed == 0 and total_tests > 0 else ("EMPTY" if total_tests == 0 else "FAILED")

    return {
        "summary": {
            "status": overall_status,
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_seconds": round(total_duration, 3),
            "exit_code": exit_code,
            "filter_tier": selected_tier,
            "filter_feature": selected_feature,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "tier_breakdown": tier_breakdown,
        "feature_coverage": feature_coverage,
        "test_cases": [asdict(t) for t in test_results],
    }


def print_summary_table(report: Dict[str, Any]) -> None:
    """Print an ASCII formatted human-readable test execution report."""
    summary = report["summary"]
    tier_breakdown = report["tier_breakdown"]
    feature_coverage = report["feature_coverage"]

    print("\n" + "=" * 80)
    print("                     AI-BS E2E TEST RUNNER EXECUTION SUMMARY")
    print("=" * 80)
    print(f" Status:             {summary['status']}")
    print(f" Total Tests Ran:    {summary['total_tests']}")
    print(f" Passed:             {summary['passed']}")
    print(f" Failed / Errors:    {summary['failed']}")
    print(f" Skipped:            {summary['skipped']}")
    print(f" Total Duration:     {summary['duration_seconds']:.2f} seconds")
    print(f" Timestamp:          {summary['timestamp']}")
    if summary["filter_tier"] != "all":
        print(f" Tier Filter:        Tier {summary['filter_tier']}")
    if summary["filter_feature"] is not None:
        print(f" Feature Filter:     Feature #{summary['filter_feature']}")
    print("-" * 80)

    print(" TIER BREAKDOWN")
    print(f" {'Tier':<8} {'Name':<42} {'Total':<7} {'Pass':<6} {'Fail':<6} {'Status':<8}")
    print(" " + "-" * 78)
    for t_id, data in tier_breakdown.items():
        print(
            f" {data['tier_num']:<8} {data['name'][:40]:<42} {data['total']:<7} "
            f"{data['passed']:<6} {data['failed']:<6} {data['status']:<8}"
        )
    print("-" * 80)

    print(" FEATURE COVERAGE CHECKLIST (18 Features)")
    print(f" {'ID':<4} {'Code':<6} {'Feature Name':<44} {'Tests':<7} {'Pass':<6} {'Status':<10}")
    print(" " + "-" * 78)
    for f in feature_coverage:
        print(
            f" {f['feature_id']:<4} {f['code']:<6} {f['name'][:42]:<44} "
            f"{f['total']:<7} {f['passed']:<6} {f['status']:<10}"
        )
    print("=" * 80 + "\n")


# ==============================================================================
# CLI Entry Point
# ==============================================================================

def build_cli_parser() -> argparse.ArgumentParser:
    """Construct command line interface arguments parser."""
    parser = argparse.ArgumentParser(
        description="Master E2E Test Runner for the AI-BS Platform.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "5", "all"],
        default="all",
        help="Filter test suites to run by Tier (1, 2, 3, 4, 5, or all). Default: all",
    )
    parser.add_argument(
        "--feature",
        type=int,
        choices=range(1, 19),
        metavar="{1..18}",
        default=None,
        help="Filter tests for a specific platform feature number (1 to 18).",
    )
    parser.add_argument(
        "--json-report",
        type=str,
        metavar="<filepath>",
        default=None,
        help="Path to write structured JSON summary report.",
    )
    parser.add_argument(
        "--xml-report",
        type=str,
        metavar="<filepath>",
        default=None,
        help="Path to export JUnit XML test report.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose pytest output.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        metavar="<seconds>",
        default=None,
        help="Per-test execution timeout in seconds.",
    )
    return parser


def main() -> int:
    """Main CLI execution routine."""
    parser = build_cli_parser()
    args = parser.parse_args()

    # Determine base directories
    base_dir = Path("C:/AI-BS").resolve()
    e2e_dir = base_dir / "tests" / "e2e"
    pytest_ini_path = e2e_dir / "pytest.ini"

    # Interpreter detection
    python_exe, interp_desc = detect_python_interpreter()
    if args.verbose:
        print(f"[INFO] Using Python interpreter: {python_exe} ({interp_desc})")
        print(f"[INFO] Base directory: {base_dir}")
        print(f"[INFO] E2E directory: {e2e_dir}")

    # Prepare JUnit XML target
    cleanup_temp_xml = False
    if args.xml_report:
        xml_report_path = Path(args.xml_report).resolve()
        xml_report_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        temp_xml = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
        temp_xml.close()
        xml_report_path = Path(temp_xml.name)
        cleanup_temp_xml = True

    # Build pytest invocation arguments
    pytest_cmd = [
        python_exe,
        "-m",
        "pytest",
        "-c",
        str(pytest_ini_path),
        f"--junitxml={str(xml_report_path)}",
        "-o",
        "junit_family=xunit2",
    ]

    if args.verbose:
        pytest_cmd.append("-v")

    if args.timeout is not None:
        pytest_cmd.append(f"--timeout={args.timeout}")

    # Target directory selection based on --tier
    target_dirs: List[Path] = []
    if args.tier == "all":
        for t_info in TIER_CONFIG.values():
            d = e2e_dir / t_info["dir"]
            if d.exists():
                target_dirs.append(d)
        if not target_dirs:
            target_dirs.append(e2e_dir)
    else:
        target_dirs.append(e2e_dir / TIER_CONFIG[args.tier]["dir"])

    # Feature filtering
    if args.feature is not None:
        feat_num = args.feature
        # Filter matching feature pattern across test files and test names
        keyword_expr = f"f{feat_num:02d} or b{feat_num:02d} or feature_{feat_num} or feature{feat_num}"
        # Add scenario matches if applicable
        for sc_id, feat_list in SCENARIO_FEATURE_MAP.items():
            if feat_num in feat_list:
                keyword_expr += f" or test_{sc_id}"
        # Add adversarial matches if applicable
        for adv_id, feat_list in ADVERSARIAL_FEATURE_MAP.items():
            if feat_num in feat_list:
                keyword_expr += f" or test_{adv_id}"
        pytest_cmd.extend(["-k", keyword_expr])

    for td in target_dirs:
        pytest_cmd.append(str(td))

    # Execute pytest child process
    start_wall_time = time.perf_counter()
    proc = subprocess.run(
        pytest_cmd,
        cwd=str(base_dir),
        capture_output=False,
    )
    wall_duration = time.perf_counter() - start_wall_time

    # Parse results from JUnit XML
    test_results, xml_duration = parse_junit_xml(xml_report_path)
    effective_duration = xml_duration if xml_duration > 0.0 else wall_duration

    # If pytest exited with code 5 (no tests collected) and 0 test cases exist,
    # we treat it as an empty test run (pass with 0 items) rather than a crash.
    raw_exit_code = proc.returncode
    has_failures = any(t.outcome in ("failed", "error") for t in test_results)
    if raw_exit_code == 5 and len(test_results) == 0:
        exit_code = 0
    elif has_failures:
        exit_code = 1
    else:
        exit_code = 0 if raw_exit_code == 0 else raw_exit_code

    # Build structured report
    report_data = build_summary_report(
        test_results=test_results,
        total_duration=effective_duration,
        exit_code=exit_code,
        selected_tier=args.tier,
        selected_feature=args.feature,
    )

    # Output JSON report if requested
    if args.json_report:
        json_path = Path(args.json_report).resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        if args.verbose:
            print(f"[INFO] JSON report written to {json_path}")

    # Clean up temporary XML if we created one
    if cleanup_temp_xml and xml_report_path.exists():
        try:
            xml_report_path.unlink(missing_ok=True)
        except Exception:
            pass

    # Print summary table
    print_summary_table(report_data)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
