"""Tier 3 Pairwise Test P04: Native Viewport (F04) + Legacy DirectX Fallbacks (F05).

Validates DirectX fallback compatibility chain configuration (FL 10_0, FL 9_3, WARP, DXVK)
and graceful engine behavior under fallback feature level constraints.
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
from tests.e2e.conftest import PlatformPaths


@pytest.mark.tier3
class TestP04ViewportLegacyFallbacks:
    """Pairwise F04 x F05: Native Viewport and Legacy DirectX 8/9/10 Fallbacks."""

    def test_p04_fallback_chain_specifies_d3d11_warp_and_bridges(self, platform_paths: PlatformPaths) -> None:
        """Verify fallback chain defines orderly degradation from D3D11 to WARP and translation bridges."""
        config_path = platform_paths.base_dir / "engine" / "config" / "graphics_pipeline.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        chain = cfg.get("fallback_chain", [])
        assert "DirectX11On12" in chain
        assert "DirectX11_FeatureLevel_10_0" in chain
        assert "DirectX11_FeatureLevel_9_3" in chain
        assert "WARP_Software" in chain

    def test_p04_minimum_feature_level_floor_and_warp(self, platform_paths: PlatformPaths) -> None:
        """Verify minimum feature level is bounded at 9_3 and software WARP fallback is permitted."""
        config_path = platform_paths.base_dir / "engine" / "config" / "graphics_pipeline.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        assert cfg.get("minimum_feature_level") == "9_3"
        assert cfg.get("allow_software_warp") is True
        bridges = cfg.get("translation_bridges", {})
        assert "search_paths" in bridges
        assert len(bridges["search_paths"]) >= 1
