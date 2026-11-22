"""Tier 1 Feature Coverage Tests: Feature 8 - Distributed Training Driver.

Tests the dual-framework distributed training driver supporting PySpark MLlib
and PyTorch/TorchDistributor with MLP architecture (16->64->2).
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
from conftest import PlatformPaths, SubprocessRunner, SubprocessResult


@pytest.mark.tier1
@pytest.mark.feature_8
@pytest.mark.feature(8)
class TestF08DistributedTrainingDriver:
    """Test suite for Feature 8: Distributed Training Driver."""

    def test_f08_cli_help_options(self, platform_paths: PlatformPaths, python_exe: str) -> None:
        """Verify driver CLI flags via --help."""
        script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        assert script.exists(), f"Driver script missing: {script}"

        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=30.0)
        res = runner.run([python_exe, str(script), "--help"])
        res.assert_success()
        res.assert_stdout_contains("--framework")
        res.assert_stdout_contains("--num-samples")
        res.assert_stdout_contains("--num-features")
        res.assert_stdout_contains("--num-torch-processes")
        res.assert_stdout_contains("--use-gpu")
        res.assert_stdout_contains("--model-export-uri")

    def test_f08_pytorch_training_execution(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Execute distributed driver in PyTorch mode and verify exit code 0."""
        script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=60.0)
        res = runner.run([python_exe, str(script), "--framework", "pytorch", "--num-samples", "200"])
        res.assert_success("PyTorch distributed training driver execution failed.")
        res.assert_stdout_contains("PYTORCH DEEP LEARNING (16->64->2) TRAINING")
        res.assert_stdout_contains("Target Framework(s): PYTORCH")

    def test_f08_pytorch_epoch_progression_and_loss(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify epoch loss logging across all 5 training epochs."""
        script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=60.0)
        res = runner.run([python_exe, str(script), "--framework", "pytorch", "--num-samples", "200"])
        res.assert_success()
        for epoch in range(1, 6):
            res.assert_stdout_contains(f"[PyTorch Epoch {epoch}/5] Worker Loss:")

    def test_f08_framework_choice_flag_validation(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify execution completion banner matches target framework."""
        script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=60.0)
        res = runner.run([python_exe, str(script), "--framework", "pytorch", "--num-samples", "100"])
        res.assert_success()
        res.assert_stdout_contains("DISTRIBUTED TRAINING EXECUTION COMPLETE FOR FRAMEWORK: PYTORCH")

    def test_f08_driver_custom_num_samples_arg(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify driver correctly handles custom sample count argument."""
        script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=60.0)
        res = runner.run([python_exe, str(script), "--framework", "pytorch", "--num-samples", "500"])
        res.assert_success()
        res.assert_stdout_contains("DISTRIBUTED TRAINING EXECUTION COMPLETE FOR FRAMEWORK: PYTORCH")

    def test_f08_driver_custom_export_uri_arg(
        self, platform_paths: PlatformPaths, python_exe: str, tmp_path: Path
    ) -> None:
        """Verify driver accepts custom --model-export-uri flag without error."""
        export_target = tmp_path / "custom_rf_export"
        script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        runner = SubprocessRunner(default_cwd=platform_paths.distributed_training_dir, default_timeout=60.0)
        res = runner.run([
            python_exe, str(script),
            "--framework", "pytorch",
            "--num-samples", "100",
            "--model-export-uri", str(export_target)
        ])
        res.assert_success()
        res.assert_stdout_contains("DISTRIBUTED TRAINING EXECUTION COMPLETE FOR FRAMEWORK: PYTORCH")
