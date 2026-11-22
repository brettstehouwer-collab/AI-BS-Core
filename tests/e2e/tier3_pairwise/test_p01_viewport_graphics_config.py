"""Tier 3 Pairwise Test P01: Native Viewport (F04) + Graphics Configuration (F06).

Validates that engine graphics pipeline configuration correctly informs
the native viewport execution parameters and fallback chain.
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


@pytest.mark.tier3
class TestP01ViewportGraphicsConfig:
    """Pairwise F04 x F06: Native Viewport and Engine Graphics Configuration."""

    def test_p01_viewport_config_schema_compatibility(self, platform_paths: PlatformPaths) -> None:
        """Verify graphics_pipeline.json config defines DirectX12 primary and valid fallback chain."""
        config_path = platform_paths.base_dir / "engine" / "config" / "graphics_pipeline.json"
        assert config_path.exists(), f"Configuration missing at {config_path}"

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        assert cfg.get("primary_backend") == "DirectX12"
        assert "fallback_chain" in cfg
        assert isinstance(cfg["fallback_chain"], list)
        assert len(cfg["fallback_chain"]) >= 3
        assert cfg.get("allow_software_warp") is True

    def test_p01_viewport_execution_with_config_env_override(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Verify native viewport session executes successfully under DirectX12 config override."""
        verify_script = platform_paths.native_studio_dir / "verify_sheltered_hub_viewport_session.py"
        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["AIBS_GRAPHICS_BACKEND"] = "DirectX12"
        env["AIBS_D3D_FEATURE_LEVEL"] = "11_0"

        res = subprocess_runner.run([python_exe, str(verify_script)], cwd=platform_paths.base_dir, env=env, timeout=120)
        res.assert_success("Viewport failed with graphics environment overrides")

        telemetry_file = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.json"
        assert telemetry_file.exists()
        with open(telemetry_file, "r", encoding="utf-8") as f:
            t = json.load(f)
        assert t.get("debug_errors") == 0
        assert t.get("nonbackground_pixels", 0) > 0
