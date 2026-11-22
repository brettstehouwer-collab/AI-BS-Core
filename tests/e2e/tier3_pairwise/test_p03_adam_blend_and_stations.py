"""Tier 3 Pairwise Test P03: Adam Blend Tree (F03) + Sheltered Hub Stations (F01).

Validates coordination between Adam guide character likeness/animation blend trees
and Sheltered Hub station interaction states.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner


@pytest.mark.tier3
class TestP03AdamBlendAndStations:
    """Pairwise F03 x F01: Adam Blend Tree Animations and Sheltered Hub Stations."""

    def test_p03_adam_podium_node_creation_and_attributes(self, platform_paths: PlatformPaths) -> None:
        """Verify Adam guide station node carries valid blend weights and podium tracking."""
        from native_studio.verify_sheltered_hub_viewport_session import create_station_nodes

        entities, selected_id = create_station_nodes()
        adam_nodes = [e for e in entities if "podium" in e.alias.lower() or "adam" in e.name.lower()]
        assert len(adam_nodes) >= 1, "No Adam guide podium entity created in station graph"

        adam_node = adam_nodes[0]
        field_dict = dict(adam_node.fields)
        assert "adam_blend_weight" in field_dict
        assert 0.0 <= field_dict["adam_blend_weight"] <= 1.0
        assert "adam_gaze_track" in field_dict
        assert field_dict["adam_gaze_track"] == 1.0

    def test_p03_adam_blend_tree_native_test_executable(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Verify compiled native binary aibs_adam_blend_tree_tests.exe exists and executes."""
        bin_path = platform_paths.base_dir / "engine" / "out" / "windows-msvc" / "Debug" / "aibs_adam_blend_tree_tests.exe"
        if not bin_path.exists():
            pytest.skip("aibs_adam_blend_tree_tests.exe binary not found")

        res = subprocess_runner.run([str(bin_path)], cwd=platform_paths.base_dir, timeout=30)
        res.assert_success("Adam blend tree native tests failed")
