"""Tier 3 Pairwise Test P07: Dataproc Template (F09) + Batch Deployment Script (F10).

Validates that deploy_serverless_spark.py --validate verifies the Dataproc Serverless
session template against Google Cloud Dataproc v1 REST schema.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner


@pytest.mark.tier3
class TestP07DataprocTemplateDeployScript:
    """Pairwise F09 x F10: Dataproc Serverless Template and Batch Deployment Script."""

    def test_p07_deployment_script_validation_mode_passes(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Verify deploy_serverless_spark.py --validate exits 0 and reports all 8 checks passed."""
        script_path = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        assert script_path.exists()

        python_exe = r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe"
        res = subprocess_runner.run([python_exe, str(script_path), "--validate"], timeout=30)
        res.assert_success("Dataproc template validation failed")
        res.assert_stdout_contains("ALL DATAPROC SERVERLESS CONFIGURATION CHECKS PASSED")

    def test_p07_terraform_generation_contract(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Verify deploy_serverless_spark.py --terraform generates serverless HCL (no legacy clusters)."""
        script_path = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        python_exe = r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe"
        res = subprocess_runner.run([python_exe, str(script_path), "--terraform"], timeout=15)
        res.assert_success()
        hcl = res.stdout
        assert "google_dataproc_cluster" not in hcl, "Terraform HCL must not use legacy cluster resources"
        assert "google_dataproc_session_template" in hcl, "Terraform HCL missing session template"
        assert "google_dataproc_batch" in hcl, "Terraform HCL missing batch resource"
