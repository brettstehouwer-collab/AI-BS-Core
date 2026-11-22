"""Tier 3 Pairwise Test P05: Local ML Pipeline (F07) + Distributed Training Driver (F08).

Validates alignment between local model training serialization contracts and
distributed training driver model ingestion and feature schema.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner


@pytest.mark.tier3
class TestP05MLPipelineDistributedDriver:
    """Pairwise F07 x F08: Local ML Training Pipeline and Distributed Training Driver."""

    def test_p05_driver_cli_supports_mllib_and_pytorch(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Verify distributed training driver CLI exposes both MLlib and PyTorch frameworks."""
        driver_script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        assert driver_script.exists()

        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
        res = subprocess_runner.run([python_exe, str(driver_script), "--help"], timeout=15)
        res.assert_success()
        res.assert_stdout_contains("--framework")
        res.assert_stdout_contains("mllib")
        res.assert_stdout_contains("pytorch")

    def test_p05_local_ml_pipeline_model_export_directory(self, platform_paths: PlatformPaths) -> None:
        """Verify local_models output directory exists and holds serialized model artifacts."""
        local_models_dir = platform_paths.distributed_training_dir / "local_models"
        assert local_models_dir.exists(), f"local_models dir missing at {local_models_dir}"

        pkl_models = list(local_models_dir.glob("rf_model_*.pkl"))
        assert len(pkl_models) >= 1, "No serialized random forest model found in local_models"
        assert pkl_models[0].stat().st_size > 10_000, "Serialized model file unexpectedly small"
