"""Tier 4 Real-World Application Scenario 01: Chapter 1 Studio & Native Viewport Complete Walkthrough.

Exercises: F01 (Sheltered Hub Stations), F02 (Spatial Trigger Zones), F03 (Adam Blend Tree),
F04 (Native DX12 Viewport Session), F06 (Engine Graphics Configuration).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths, SubprocessRunner


@pytest.mark.tier4
class TestS01AuthoringToViewportE2E:
    """Scenario 01: Complete Chapter 1 Authoring to Native DX12 Viewport Projection."""

    def test_s01_chapter1_stations_and_spatial_containment_walkthrough(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Step 1 & 2: Author Chapter 1 stations and verify player trajectory spatial containment."""
        from native_studio.game_engine.sheltered_hub_fields import (
            ZONE_BOUNDS,
            SPATIAL_ZONES,
            find_spatial_zone,
            validate_writing_desk,
            validate_memory_shelves,
            validate_shared_play,
        )

        # 1. Author and validate stations
        desk = validate_writing_desk({
            "pencil_claimed": True, "mode": "sketch", "notes_written": 3,
            "x": -38.0, "y": 0.75, "z": 18.0
        })
        shelves = validate_memory_shelves({
            "items_placed": 4, "capacity": 12, "secret_revealed": True,
            "x": -33.5, "y": 1.5, "z": 16.5
        })
        play = validate_shared_play({
            "display_powered": True, "session_active": True,
            "x": -36.0, "y": 0.6, "z": 10.0
        })

        assert desk["pencil_claimed"] is True
        assert shelves["secret_revealed"] is True
        assert play["display_powered"] is True

        # 2. Verify complete spatial progression: 7 sequential zones
        player_walkthrough_waypoints = [
            ("nook_awakening", (-32.5, 0.0, -26.0)),
            ("corridor_approach", (-36.5, 0.0, -15.0)),
            ("fault_trench", (-33.0, 0.0, -4.5)),
            ("relay_bypass_socket", (-42.0, 0.0, -4.5)),
            ("threshold_aperture", (-37.0, 0.0, 2.5)),
            ("sheltered_hub", (-36.5, 0.0, 9.5)),
            ("pencil_room", (-36.5, 0.0, 18.0)),
        ]

        for expected_zone, coord in player_walkthrough_waypoints:
            resolved_zone = find_spatial_zone(coord)
            assert resolved_zone == expected_zone, f"Waypoint {coord} expected {expected_zone}, got {resolved_zone}"

    def test_s01_dx12_native_viewport_projection_execution(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Step 3, 4 & 5: Configure graphics engine and execute offscreen DX12 viewport projection."""
        verify_script = platform_paths.native_studio_dir / "verify_sheltered_hub_viewport_session.py"
        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["AIBS_GRAPHICS_BACKEND"] = "DirectX12"

        res = subprocess_runner.run([python_exe, str(verify_script)], cwd=platform_paths.base_dir, env=env, timeout=120)
        res.assert_success("DX12 native viewport execution failed")

        # Verify output artifacts
        telemetry_path = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.json"
        bmp_path = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.bmp"

        assert telemetry_path.exists(), "Viewport telemetry report missing"
        assert bmp_path.exists(), "Viewport frame BMP missing"

        with open(telemetry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("debug_errors") == 0, "D3D12 debug errors detected"
        assert data.get("nonbackground_pixels", 0) > 0, "No nonbackground pixels rendered"
        assert bmp_path.stat().st_size > 500_000, "Rendered BMP size unexpectedly small"
