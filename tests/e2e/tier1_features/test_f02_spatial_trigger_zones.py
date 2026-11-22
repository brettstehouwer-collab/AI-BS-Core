"""Tier 1 Feature Tests: Feature 2 - Spatial Trigger Zones (7 zones).

Validates the 7 narrative audio cue trigger zones spanning from
awakening through the pencil room:
- nook_awakening, corridor_approach, fault_trench, relay_bypass_socket,
  threshold_aperture, sheltered_hub, pencil_room
- 3D spatial containment math and narrative trajectory resolution
- C++ podium spatial captions map contracts (aibs_podium_captions_map_tests.exe)
- Zone bounding geometry and AIBV scene entity volume construction
- Narrative route continuity along the longitudinal z-axis (-31m to +22m)
"""

from __future__ import annotations

import uuid
from pathlib import Path
import pytest

from native_studio.game_engine.sheltered_hub_fields import (
    SPATIAL_ZONES,
    ZONE_BOUNDS,
    find_spatial_zone,
)
from native_studio.game_engine.creator_payload import Create


@pytest.mark.tier1
@pytest.mark.feature_2
class TestSpatialTriggerZonesTier1:
    """Tier 1 feature test suite for Feature 2: Spatial Trigger Zones."""

    def test_f02_spatial_zones_catalog_and_bounds_registered(self):
        """Verify that exactly 7 spatial trigger zones are defined with valid 3D bounding extents."""
        assert len(SPATIAL_ZONES) == 7
        expected_zones = (
            "nook_awakening",
            "corridor_approach",
            "fault_trench",
            "relay_bypass_socket",
            "threshold_aperture",
            "sheltered_hub",
            "pencil_room",
        )
        assert SPATIAL_ZONES == expected_zones

        for zone in expected_zones:
            assert zone in ZONE_BOUNDS, f"Zone {zone} missing from ZONE_BOUNDS"
            min_pt, max_pt = ZONE_BOUNDS[zone]
            assert len(min_pt) == 3 and len(max_pt) == 3
            # Check strict min < max on each coordinate axis
            assert min_pt[0] < max_pt[0], f"Zone {zone} x min >= max ({min_pt[0]} >= {max_pt[0]})"
            assert min_pt[1] < max_pt[1], f"Zone {zone} y min >= max ({min_pt[1]} >= {max_pt[1]})"
            assert min_pt[2] < max_pt[2], f"Zone {zone} z min >= max ({min_pt[2]} >= {max_pt[2]})"

    def test_f02_narrative_route_sequential_containment(self):
        """Verify that points sampled along the narrative path resolve to each expected zone."""
        narrative_path_points = {
            "nook_awakening": (-32.5, 0.0, -26.0),
            "corridor_approach": (-36.5, 0.0, -15.0),
            "fault_trench": (-33.0, 0.0, -4.5),
            "relay_bypass_socket": (-42.0, 0.0, -4.5),
            "threshold_aperture": (-37.0, 0.0, 2.5),
            "sheltered_hub": (-36.5, 0.0, 9.5),
            "pencil_room": (-36.5, 0.0, 18.0),
        }

        for expected_zone, point in narrative_path_points.items():
            resolved = find_spatial_zone(point)
            assert resolved == expected_zone, (
                f"Narrative position {point} resolved to '{resolved}', expected '{expected_zone}'"
            )

    def test_f02_podium_spatial_captions_map_cpp_execution(self, platform_paths, run_cmd):
        """Execute C++ native binary validating 516 podium spatial audio triggers and route mapping."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_podium_captions_map_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=15.0)
        result.assert_success()
        result.assert_stdout_contains("PASS: all 516 podium spatial captions map checks passed successfully")

    def test_f02_zone_centers_and_extents_derivation(self):
        """Verify computation of center points and half-extents for AIBV trigger volume entities."""
        for zone_name in SPATIAL_ZONES:
            min_pt, max_pt = ZONE_BOUNDS[zone_name]
            cx = (min_pt[0] + max_pt[0]) / 2.0
            cy = (min_pt[1] + max_pt[1]) / 2.0
            cz = (min_pt[2] + max_pt[2]) / 2.0

            hx = (max_pt[0] - min_pt[0]) / 2.0
            hy = (max_pt[1] - min_pt[1]) / 2.0
            hz = (max_pt[2] - min_pt[2]) / 2.0

            # Centers must be inside their own zones
            assert find_spatial_zone((cx, cy, cz)) == zone_name
            # Extents must be non-zero positive
            assert hx >= 0.5
            assert hy >= 0.5
            assert hz >= 0.5

            # Construct valid AIBV entity row
            zone_id = str(uuid.uuid4())
            entity = Create(
                f"zone_{zone_name}",
                f"Zone: {zone_name}",
                zone_id,
                (("x", cx), ("y", cy), ("z", cz), ("half_x", hx), ("half_y", hy), ("half_z", hz)),
            )
            assert entity.alias == f"zone_{zone_name}"
            assert entity.uuid == zone_id

    def test_f02_route_z_continuity_and_ordering(self):
        """Verify longitudinal (z-axis) continuity along the player journey from z=-31 to z=+22."""
        # Nook: [-31, -21], Corridor: [-21, -9], Fault/Relay: [-9, 0], Aperture: [0, 5], Hub: [5, 14], Pencil: [14, 22]
        route_sequence = [
            "nook_awakening",
            "corridor_approach",
            "fault_trench",
            "threshold_aperture",
            "sheltered_hub",
            "pencil_room",
        ]

        for i in range(len(route_sequence) - 1):
            curr_zone = route_sequence[i]
            next_zone = route_sequence[i + 1]
            curr_z_max = ZONE_BOUNDS[curr_zone][1][2]
            next_z_min = ZONE_BOUNDS[next_zone][0][2]
            assert curr_z_max == pytest.approx(next_z_min, abs=1e-5), (
                f"Z-axis gap or overlap between {curr_zone} (z_max={curr_z_max}) and {next_zone} (z_min={next_z_min})"
            )

        # Full journey span
        total_z_min = ZONE_BOUNDS["nook_awakening"][0][2]
        total_z_max = ZONE_BOUNDS["pencil_room"][1][2]
        assert total_z_min == -31.0
        assert total_z_max == 22.0
        assert (total_z_max - total_z_min) == 53.0  # 53 meters total traversable narrative length

    def test_f02_podium_key_route_waypoints(self):
        """Verify key spatial waypoints along the physical route matching podium captions queries."""
        # Nook spawn
        assert find_spatial_zone((-32.5, 0.2, -25.0)) == "nook_awakening"
        # Fault trench
        assert find_spatial_zone((-33.0, 0.2, -5.2)) == "fault_trench"
        # Relay bypass socket (different X branch)
        assert find_spatial_zone((-42.0, 0.2, -5.2)) == "relay_bypass_socket"
        # Door aperture
        assert find_spatial_zone((-33.0, 0.2, 5.0)) == "threshold_aperture"
        # Hub interior
        assert find_spatial_zone((-37.0, 0.2, 8.0)) == "sheltered_hub"
        # Pencil room
        assert find_spatial_zone((-37.0, 0.2, 15.0)) == "pencil_room"
