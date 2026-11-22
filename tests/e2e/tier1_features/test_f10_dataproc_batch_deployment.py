"""Tier 1 Feature Coverage Tests: Feature 10 - Dataproc Batch Deployment Script.

Tests deploy_serverless_spark.py with --validate schema verification,
serverless Terraform HCL generation, Dataproc REST Batch JSON output,
and CLI options handling.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure tests/e2e root is on sys.path
E2E_ROOT = Path(__file__).resolve().parent.parent
if str(E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_ROOT))

import pytest
from conftest import PlatformPaths, SubprocessRunner


@pytest.mark.tier1
@pytest.mark.feature_10
@pytest.mark.feature(10)
class TestF10DataprocBatchDeployment:
    """Test suite for Feature 10: Dataproc Batch Deployment Script."""

    def test_f10_validate_exits_zero(self, platform_paths: PlatformPaths, python_exe: str) -> None:
        """Verify that deploy_serverless_spark.py --validate completes with exit code 0."""
        script = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        assert script.exists(), f"Deployment script missing: {script}"

        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=30.0)
        res = runner.run([python_exe, str(script), "--validate"])
        res.assert_success("Dataproc batch deployment validation failed.")
        res.assert_stdout_contains("ALL DATAPROC SERVERLESS CONFIGURATION CHECKS PASSED (EXIT CODE 0)")

    def test_f10_validate_all_eight_points_logged(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify that all 8 validation checks pass and are logged."""
        script = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=30.0)
        res = runner.run([python_exe, str(script), "--validate"])
        res.assert_success()
        for check_idx in range(1, 9):
            res.assert_stdout_contains(f"[PASS] {check_idx}.")

    def test_f10_terraform_hcl_output(self, platform_paths: PlatformPaths, python_exe: str) -> None:
        """Verify --terraform generates serverless resource blocks and no legacy clusters."""
        script = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=30.0)
        res = runner.run([python_exe, str(script), "--terraform"])
        res.assert_success()
        res.assert_stdout_contains("resource \"google_dataproc_session_template\"")
        res.assert_stdout_contains("resource \"google_dataproc_batch\"")
        assert "google_dataproc_cluster" not in res.stdout, "Terraform HCL must not include legacy cluster"

    def test_f10_batch_json_schema(self, platform_paths: PlatformPaths, python_exe: str) -> None:
        """Verify --batch-json outputs a valid Dataproc REST Batch JSON payload."""
        script = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=30.0)
        res = runner.run([python_exe, str(script), "--batch-json"])
        res.assert_success()

        payload = json.loads(res.stdout)
        assert "name" in payload
        assert "pysparkBatch" in payload
        assert payload["pysparkBatch"]["mainPythonFileUri"].endswith("distributed_training_driver.py")
        assert payload["pysparkBatch"]["args"] == ["--framework", "both"]
        assert payload["runtimeConfig"]["version"] == "2.2"

    def test_f10_show_cli_gcloud_command(self, platform_paths: PlatformPaths, python_exe: str) -> None:
        """Verify --show-cli outputs the verified gcloud Dataproc submission command."""
        script = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=30.0)
        res = runner.run([python_exe, str(script), "--show-cli"])
        res.assert_success()
        res.assert_stdout_contains("gcloud dataproc batches submit pyspark")
        res.assert_stdout_contains("--framework both")

    def test_f10_custom_project_region_flags(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify custom --project and --region flags propagate to generated payloads."""
        script = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=30.0)
        res = runner.run([
            python_exe, str(script),
            "--project", "test-aibs-custom",
            "--region", "europe-west1",
            "--batch-json"
        ])
        res.assert_success()
        payload = json.loads(res.stdout)
        assert "projects/test-aibs-custom/locations/europe-west1" in payload["name"]
