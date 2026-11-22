"""Tier 1 Feature Tests: Feature 5 - Legacy DirectX 8/9/10 Fallbacks.

Validates the graphics engine fallback subsystem:
- Native DirectX 12 renderer execution and validation proof (aibs_render_validation_native.exe)
- Motherboard scene and camera contracts test suite (aibs_renderer_tests.exe)
- Fallback chain hierarchy order (D3D11On12 -> FL 10_0 -> FL 9_3 -> DXVK -> D8VK -> WARP)
- WARP software rasterizer fallback availability for headless/unsupported hardware
- Translation bridges configuration schema (DXVK, D8VK, and bridge search paths)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest


@pytest.mark.tier1
@pytest.mark.feature_5
class TestLegacyDirectXFallbacksTier1:
    """Tier 1 feature test suite for Feature 5: Legacy DirectX Fallbacks."""

    def test_f05_legacy_render_validation_native_execution(
        self, platform_paths, run_cmd, tmp_path, clean_artifacts
    ):
        """Execute aibs_render_validation_native in legacy mode and verify proof report."""
        exe_path = (
            platform_paths.engine_dir
            / "out"
            / "windows-msvc"
            / "Debug"
            / "aibs_render_validation_native.exe"
        )
        shaders_dir = (
            platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "shaders"
        )
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"
        assert shaders_dir.is_dir(), f"Expected shaders directory at {shaders_dir}"

        evidence_dir = clean_artifacts(tmp_path / "legacy_render_evidence")

        cmd = [str(exe_path), "legacy", str(shaders_dir), str(evidence_dir)]
        result = run_cmd(cmd, timeout=20.0)
        result.assert_success()
        result.assert_stdout_contains("legacy actual DX12 render and validation observation passed")

        report_file = evidence_dir / "result.json"
        assert report_file.is_file(), f"Result report missing in {evidence_dir}"
        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert report["status"] == "passed"
        assert report["mode"] == "legacy"
        assert report["debug_errors"] == 0
        assert report["nonbackground_pixels"] > 0
        assert report["frames"] == 4

        frame_file = evidence_dir / "frame.bmp"
        assert frame_file.is_file(), "Rendered frame.bmp was not created"
        assert frame_file.stat().st_size > 1000

    def test_f05_render_validation_enabled_and_skip_modes(
        self, platform_paths, run_cmd, tmp_path, clean_artifacts
    ):
        """Execute aibs_render_validation_native across both 'enabled' and 'skip' modes."""
        exe_path = (
            platform_paths.engine_dir
            / "out"
            / "windows-msvc"
            / "Debug"
            / "aibs_render_validation_native.exe"
        )
        shaders_dir = (
            platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "shaders"
        )

        for mode in ("enabled", "skip"):
            evidence_dir = clean_artifacts(tmp_path / f"evidence_{mode}")
            cmd = [str(exe_path), mode, str(shaders_dir), str(evidence_dir)]
            result = run_cmd(cmd, timeout=20.0)
            result.assert_success()
            result.assert_stdout_contains(f"{mode} actual DX12 render and validation observation passed")

            report_file = evidence_dir / "result.json"
            assert report_file.is_file()
            report = json.loads(report_file.read_text(encoding="utf-8"))
            assert report["status"] == "passed"
            assert report["mode"] == mode
            assert report["debug_errors"] == 0

    def test_f05_motherboard_renderer_tests_execution(self, platform_paths, run_cmd):
        """Execute aibs_renderer_tests verifying transient draw API, camera bounds, and vertex geometry."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_renderer_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=15.0)
        result.assert_success()
        result.assert_stdout_contains("PASS: motherboard geometry and camera contracts")

    def test_f05_fallback_chain_hierarchy_order(self, platform_paths):
        """Verify the ordered fallback progression in graphics_pipeline.json."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        assert config_path.is_file(), f"Expected graphics config at {config_path}"

        config = json.loads(config_path.read_text(encoding="utf-8"))
        fallback_chain = config.get("fallback_chain", [])

        # Priority requirements from PROJECT.md:
        # D3D11On12 -> FL 10_0 -> FL 9_3 -> translation bridges -> WARP software
        assert "DirectX11On12" in fallback_chain
        assert "DirectX11_FeatureLevel_10_0" in fallback_chain
        assert "DirectX11_FeatureLevel_9_3" in fallback_chain
        assert "WARP_Software" in fallback_chain

        idx_11on12 = fallback_chain.index("DirectX11On12")
        idx_fl10 = fallback_chain.index("DirectX11_FeatureLevel_10_0")
        idx_fl93 = fallback_chain.index("DirectX11_FeatureLevel_9_3")
        idx_warp = fallback_chain.index("WARP_Software")

        assert idx_11on12 < idx_fl10 < idx_fl93 < idx_warp, (
            f"Fallback chain priority order inverted: {fallback_chain}"
        )

    def test_f05_warp_software_fallback_enabled(self, platform_paths):
        """Verify that allow_software_warp is enabled to guarantee execution on headless/virtualized CI."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert config.get("allow_software_warp") is True

    def test_f05_translation_bridges_schema(self, platform_paths):
        """Verify translation bridge configuration keys and search paths in graphics_pipeline.json."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        bridges = config.get("translation_bridges", {})
        assert isinstance(bridges, dict)
        assert "dxvk_enabled" in bridges
        assert "d8vk_enabled" in bridges
        assert "search_paths" in bridges
        assert isinstance(bridges["search_paths"], list)
        assert len(bridges["search_paths"]) >= 2
        assert "third_party/dxvk" in bridges["search_paths"]
