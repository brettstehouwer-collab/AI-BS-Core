"""Tier 4 Real-World Application Scenario 02: Legacy DirectX Fallback Degradation & Recovery.

Exercises: F04 (DX12 Viewport), F05 (DirectX Fallbacks), F06 (Graphics Config), F14 (Studio Audit).
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
class TestS02LegacyDXFallbackRecovery:
    """Scenario 02: Legacy DirectX Fallback Degradation & Recovery."""

    def test_s02_graphics_fallback_chain_and_translation_bridges(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Step 1 & 2: Verify fallback chain includes FL 10_0, FL 9_3, WARP and bridge paths."""
        config_file = platform_paths.base_dir / "engine" / "config" / "graphics_pipeline.json"
        assert config_file.exists()

        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        chain = cfg.get("fallback_chain", [])
        expected_fallbacks = ["DirectX11On12", "DirectX11_FeatureLevel_10_0", "DirectX11_FeatureLevel_9_3", "WARP_Software"]
        for fb in expected_fallbacks:
            assert fb in chain, f"Fallback '{fb}' missing from fallback_chain"

        bridges = cfg.get("translation_bridges", {})
        assert "search_paths" in bridges
        assert "third_party/dxvk" in bridges["search_paths"] or "bin/bridges" in bridges["search_paths"]

    def test_s02_native_viewport_survives_fallback_configuration(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Step 3 & 4: Execute viewport with simulated fallback feature level without crash."""
        verify_script = platform_paths.native_studio_dir / "verify_sheltered_hub_viewport_session.py"
        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["AIBS_GRAPHICS_BACKEND"] = "DirectX11On12"
        env["AIBS_D3D_FEATURE_LEVEL"] = "10_0"

        res = subprocess_runner.run([python_exe, str(verify_script)], cwd=platform_paths.base_dir, env=env, timeout=120)
        res.assert_success("Engine failed to degrade gracefully under fallback feature level")

        # Telemetry should confirm execution passed
        telemetry = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.json"
        assert telemetry.exists()
        with open(telemetry, "r", encoding="utf-8") as f:
            t = json.load(f)
        assert t.get("debug_errors") == 0
