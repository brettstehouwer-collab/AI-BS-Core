"""Tier 3 Pairwise Test P02: Sheltered Hub Stations (F01) + Spatial Zones (F02).

Validates that station locations in Sheltered Hub map directly into expected
spatial containment boundaries and audio trigger cues.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths


@pytest.mark.tier3
class TestP02HubStationsSpatialZones:
    """Pairwise F01 x F02: Sheltered Hub Stations and Spatial Trigger Zones."""

    def test_p02_writing_desk_inside_pencil_room_zone(self, platform_paths: PlatformPaths) -> None:
        """Verify Writing Desk coordinates (-38.0, 0.75, 18.0) resolve inside pencil_room zone."""
        from native_studio.game_engine.sheltered_hub_fields import find_spatial_zone

        desk_pos = (-38.0, 0.75, 18.0)
        zone = find_spatial_zone(desk_pos)
        assert zone == "pencil_room", f"Expected writing desk in 'pencil_room', resolved to '{zone}'"

    def test_p02_shared_play_inside_sheltered_hub_zone(self, platform_paths: PlatformPaths) -> None:
        """Verify Shared Play corner coordinates (-36.0, 0.6, 10.0) resolve inside sheltered_hub zone."""
        from native_studio.game_engine.sheltered_hub_fields import find_spatial_zone

        play_pos = (-36.0, 0.6, 10.0)
        zone = find_spatial_zone(play_pos)
        assert zone == "sheltered_hub", f"Expected shared play in 'sheltered_hub', resolved to '{zone}'"

    def test_p02_memory_shelves_inside_pencil_room_zone(self, platform_paths: PlatformPaths) -> None:
        """Verify Memory Shelves coordinates (-33.5, 1.5, 16.5) resolve inside pencil_room zone."""
        from native_studio.game_engine.sheltered_hub_fields import find_spatial_zone

        shelves_pos = (-33.5, 1.5, 16.5)
        zone = find_spatial_zone(shelves_pos)
        assert zone == "pencil_room", f"Expected memory shelves in 'pencil_room', resolved to '{zone}'"
