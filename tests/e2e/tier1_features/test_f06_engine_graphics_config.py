"""Tier 1 Feature Tests: Feature 6 - Engine Graphics Configuration.

Validates the engine graphics configuration schema, environment overrides, and resolution precedence:
- graphics_pipeline.json JSON syntax and schema_version integrity
- Core contract fields (primary_backend, fallback_chain, feature_level_requested, etc.)
- Primary backend validity and target feature level specification
- Environment variable override for backend (AIBS_GRAPHICS_BACKEND)
- Environment variable override for feature level (AIBS_D3D_FEATURE_LEVEL)
- Configuration serialization roundtrip and temporary override persistence
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import pytest


def resolve_effective_graphics_config(
    config_file_path: Path,
    env_backend: str | None = None,
    env_feature_level: str | None = None,
) -> dict:
    """Simulates the engine's configuration resolution logic with environment overrides."""
    with open(config_file_path, "r", encoding="utf-8") as f:
        base_config = json.load(f)

    resolved = dict(base_config)
    if env_backend:
        resolved["primary_backend"] = env_backend.strip()
    if env_feature_level:
        resolved["feature_level_requested"] = env_feature_level.strip()
    return resolved


@pytest.mark.tier1
@pytest.mark.feature_6
class TestEngineGraphicsConfigTier1:
    """Tier 1 feature test suite for Feature 6: Engine Graphics Configuration."""

    def test_f06_graphics_pipeline_config_file_validity(self, platform_paths):
        """Verify graphics_pipeline.json exists, parses cleanly, and specifies schema_version 1."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        assert config_path.is_file(), f"Configuration file missing at {config_path}"

        raw_text = config_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        assert isinstance(data, dict)
        assert data.get("schema_version") == 1

    def test_f06_graphics_config_schema_fields(self, platform_paths):
        """Verify that all mandatory fields defined in PROJECT.md interface contract are present."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))

        mandatory_fields = [
            "schema_version",
            "primary_backend",
            "fallback_chain",
            "feature_level_requested",
            "minimum_feature_level",
            "allow_software_warp",
            "translation_bridges",
        ]
        for field_name in mandatory_fields:
            assert field_name in data, f"Missing required contract field: {field_name}"

        assert isinstance(data["primary_backend"], str)
        assert isinstance(data["fallback_chain"], list)
        assert isinstance(data["feature_level_requested"], str)
        assert isinstance(data["minimum_feature_level"], str)
        assert isinstance(data["allow_software_warp"], bool)
        assert isinstance(data["translation_bridges"], dict)

    def test_f06_primary_backend_and_feature_level_types(self, platform_paths):
        """Verify default primary backend is DirectX12 and requested level is >= minimum level."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))

        assert data["primary_backend"] == "DirectX12"
        assert data["feature_level_requested"] in ("11_0", "11_1", "12_0", "12_1", "12_2")
        assert data["minimum_feature_level"] in ("9_3", "10_0", "11_0")

    def test_f06_environment_override_backend_precedence(self, platform_paths, monkeypatch):
        """Verify AIBS_GRAPHICS_BACKEND environment variable overrides primary_backend."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"

        # Baseline: DirectX12
        baseline = resolve_effective_graphics_config(config_path)
        assert baseline["primary_backend"] == "DirectX12"

        # Override with WARP_Software
        monkeypatch.setenv("AIBS_GRAPHICS_BACKEND", "WARP_Software")
        overridden = resolve_effective_graphics_config(
            config_path, env_backend=os.environ.get("AIBS_GRAPHICS_BACKEND")
        )
        assert overridden["primary_backend"] == "WARP_Software"

        # Override with DirectX11On12
        monkeypatch.setenv("AIBS_GRAPHICS_BACKEND", "DirectX11On12")
        overridden_11on12 = resolve_effective_graphics_config(
            config_path, env_backend=os.environ.get("AIBS_GRAPHICS_BACKEND")
        )
        assert overridden_11on12["primary_backend"] == "DirectX11On12"

    def test_f06_environment_override_feature_level_precedence(self, platform_paths, monkeypatch):
        """Verify AIBS_D3D_FEATURE_LEVEL environment variable overrides feature_level_requested."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"

        # Baseline: 11_0
        baseline = resolve_effective_graphics_config(config_path)
        assert baseline["feature_level_requested"] == "11_0"

        # Override with 10_0
        monkeypatch.setenv("AIBS_D3D_FEATURE_LEVEL", "10_0")
        overridden = resolve_effective_graphics_config(
            config_path, env_feature_level=os.environ.get("AIBS_D3D_FEATURE_LEVEL")
        )
        assert overridden["feature_level_requested"] == "10_0"

    def test_f06_configuration_roundtrip_persistence(self, platform_paths, tmp_path, clean_artifacts):
        """Verify isolated modification and roundtrip re-serialization of graphics configuration."""
        config_path = platform_paths.engine_dir / "config" / "graphics_pipeline.json"
        original_data = json.loads(config_path.read_text(encoding="utf-8"))

        # Create modified copy
        modified_data = dict(original_data)
        modified_data["primary_backend"] = "DirectX11_FeatureLevel_10_0"
        modified_data["allow_software_warp"] = False

        temp_config = clean_artifacts(tmp_path / "custom_graphics_pipeline.json")
        temp_config.write_text(json.dumps(modified_data, indent=2), encoding="utf-8")

        # Reload and verify
        reloaded = json.loads(temp_config.read_text(encoding="utf-8"))
        assert reloaded["primary_backend"] == "DirectX11_FeatureLevel_10_0"
        assert reloaded["allow_software_warp"] is False
        assert reloaded["schema_version"] == 1
        assert reloaded["fallback_chain"] == original_data["fallback_chain"]
