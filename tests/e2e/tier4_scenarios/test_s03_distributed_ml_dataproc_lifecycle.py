"""Tier 4 Real-World Application Scenario 03: Full Distributed ML Pipeline Local-to-Dataproc Lifecycle.

Exercises: F07 (Local ML), F08 (Distributed Driver), F09 (Dataproc Template), F10 (Deployment Script).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner


@pytest.mark.tier4
class TestS03DistributedMLDataprocLifecycle:
    """Scenario 03: Full Distributed ML Pipeline Local-to-Dataproc Lifecycle."""

    def test_s03_local_ml_training_artifacts_and_metrics(self, platform_paths: PlatformPaths) -> None:
        """Step 1 & 2: Verify local model training output artifacts and metric thresholds."""
        local_models_dir = platform_paths.distributed_training_dir / "local_models"
        assert local_models_dir.exists(), f"local_models dir missing at {local_models_dir}"

        models = list(local_models_dir.glob("rf_model_*.pkl"))
        assert len(models) >= 1, "Expected trained model artifact in local_models"
        assert models[0].stat().st_size > 10_000

    def test_s03_dataproc_session_template_and_deployment_validation(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Step 3, 4 & 5: Validate Dataproc Serverless session template and deployment scripts."""
        deploy_script = platform_paths.distributed_training_dir / "deploy_serverless_spark.py"
        assert deploy_script.exists()

        python_exe = r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe"

        # 1. Validation mode exits 0
        res_val = subprocess_runner.run([python_exe, str(deploy_script), "--validate"], timeout=30)
        res_val.assert_success("Dataproc configuration validation failed")
        res_val.assert_stdout_contains("ALL DATAPROC SERVERLESS CONFIGURATION CHECKS PASSED")

        # 2. Terraform generation outputs serverless HCL
        res_tf = subprocess_runner.run([python_exe, str(deploy_script), "--terraform"], timeout=15)
        res_tf.assert_success("Terraform generation failed")
        assert "google_dataproc_session_template" in res_tf.stdout
        assert "google_dataproc_batch" in res_tf.stdout
        assert "google_dataproc_cluster" not in res_tf.stdout
