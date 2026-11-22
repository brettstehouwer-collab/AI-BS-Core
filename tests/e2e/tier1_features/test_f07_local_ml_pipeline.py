"""Tier 1 Feature Coverage Tests: Feature 7 - Local ML Training Pipeline.

Tests the high-throughput multi-core ML training pipeline, 8-point assertion suite,
feature-correlated signal generation, GridSearchCV convergence, AUC >= 0.70,
and model serialization to disk.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure tests/e2e root is on sys.path
E2E_ROOT = Path(__file__).resolve().parent.parent
if str(E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_ROOT))

import pytest
from conftest import PlatformPaths, SubprocessResult


@pytest.mark.tier1
@pytest.mark.feature_7
@pytest.mark.feature(7)
class TestF07LocalMLPipeline:
    """Test suite for Feature 7: Local ML Training Pipeline."""

    @pytest.fixture(scope="class")
    def pipeline_run(self, platform_paths: PlatformPaths, python_exe: str) -> SubprocessResult:
        """Execute the local ML pipeline once for the test class with a fast sample size."""
        script = platform_paths.distributed_training_dir / "test_local_ml_pipeline.py"
        assert script.exists(), f"Local ML pipeline script missing: {script}"

        from conftest import SubprocessRunner
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=120.0)
        env = {"NUM_SAMPLES": "1000"}
        result = runner.run([python_exe, str(script)], env=env)
        return result

    def test_f07_pipeline_execution_success(self, pipeline_run: SubprocessResult) -> None:
        """Assert local ML pipeline executes successfully with exit code 0."""
        pipeline_run.assert_success(
            "Local ML pipeline failed to execute or timed out."
        )
        pipeline_run.assert_stdout_contains("ALL 8 ML PIPELINE TEST ASSERTIONS PASSED (EXIT CODE 0)")

    def test_f07_all_eight_assertions_logged(self, pipeline_run: SubprocessResult) -> None:
        """Assert that all 8 individual assertions in the suite pass and are logged."""
        for assertion_idx in range(1, 9):
            expected_tag = f"[PASS] Assertion {assertion_idx}:"
            pipeline_run.assert_stdout_contains(expected_tag)

    def test_f07_dataset_generation_and_standard_scaling(self, pipeline_run: SubprocessResult) -> None:
        """Verify dataset shape (1000, 16), binary labels, and StandardScaler zero-mean normalization."""
        pipeline_run.assert_stdout_contains("Assertion 1: Dataset shapes ((1000, 16)) and binary label validity verified")
        pipeline_run.assert_stdout_contains("Assertion 2: StandardScaler zero-mean and unit-variance normalization verified")
        pipeline_run.assert_stdout_contains("Assertion 3: Stratified split sizes verified (800 train, 200 test)")

    def test_f07_gridsearch_convergence(self, pipeline_run: SubprocessResult) -> None:
        """Verify multi-core GridSearchCV convergence on best estimator."""
        pipeline_run.assert_stdout_contains("Assertion 4: Multi-core GridSearchCV training and best estimator convergence verified")
        pipeline_run.assert_stdout_contains("Best Hyperparameters:")

    def test_f07_predictive_metric_thresholds(self, pipeline_run: SubprocessResult) -> None:
        """Verify performance metrics satisfy AUC >= 0.70 and Accuracy >= 0.50."""
        pipeline_run.assert_stdout_contains("Assertion 5: Metric bounds & performance verified")
        pipeline_run.assert_stdout_contains(">= 0.70")

    def test_f07_model_artifact_created_and_verified(
        self, pipeline_run: SubprocessResult, platform_paths: PlatformPaths
    ) -> None:
        """Verify serialized model artifact was written to disk with size > 0."""
        pipeline_run.assert_stdout_contains("Assertion 6: Model artifact serialized to disk")
        pipeline_run.assert_stdout_contains("Assertion 7: Model deserialization and round-trip inference verified")

        models_dir = platform_paths.distributed_training_dir / "local_models"
        assert models_dir.exists(), f"Models directory {models_dir} does not exist"
        pkl_files = list(models_dir.glob("rf_model_*.pkl"))
        assert len(pkl_files) > 0, "No serialized model .pkl files found in local_models"
        latest_file = max(pkl_files, key=lambda p: p.stat().st_mtime)
        assert latest_file.stat().st_size > 0, f"Latest model artifact {latest_file} is empty"

    def test_f07_pytorch_dl_architecture_pass(self, pipeline_run: SubprocessResult) -> None:
        """Verify Assertion 8 confirms local PyTorch 16->64->2 forward pass & backward step."""
        pipeline_run.assert_stdout_contains("Assertion 8: Local PyTorch 16->64->2 forward pass & backward step verified")
