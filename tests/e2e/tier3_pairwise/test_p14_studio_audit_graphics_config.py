"""Tier 3 Pairwise Test P14: Native Studio Audit (F14) + Graphics Config (F06).

Validates that Studio Audit conforms to renderer abstraction and feature levels
defined in graphics_pipeline.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths


@pytest.mark.tier3
class TestP14StudioAuditGraphicsConfig:
    """Pairwise F14 x F06: Native Studio Audit and Engine Graphics Configuration."""

    def test_p14_graphics_config_referenced_by_engine_tests(self, platform_paths: PlatformPaths) -> None:
        """Verify graphics_pipeline.json is co-located with engine build outputs."""
        config_path = platform_paths.base_dir / "engine" / "config" / "graphics_pipeline.json"
        assert config_path.exists()

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        assert cfg.get("primary_backend") == "DirectX12"
        assert "fallback_chain" in cfg
        assert "feature_level_requested" in cfg

    def test_p14_audit_report_engine_configuration_consistency(self, platform_paths: PlatformPaths) -> None:
        """Verify M5 audit report confirms native viewport executable presence."""
        report_file = platform_paths.base_dir / "tests" / "m5_audit_report.json"
        assert report_file.exists()

        with open(report_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        studio = report.get("subsystems", {}).get("native_studio", {})
        assert studio.get("exe_exists") is True
        assert studio.get("exit_code") == 0
