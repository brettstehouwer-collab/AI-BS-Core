"""Tier 1 Feature Tests: Feature 1 - Sheltered Hub Stations (3).

Validates the three Sheltered Hub interactive stations:
- Writing Desk (pencil claim, writing modes: record/trace/sketch, notes journaling)
- Memory Shelves (keepsake placement, capacity bounds, secret compartment unlock)
- Shared Play Corner (restored power display dependency, interactive play session)
- Native C++ Sheltered Hub station contracts (aibs_sheltered_hub_contracts_tests.exe)
"""

from __future__ import annotations

import uuid
from pathlib import Path
import pytest

from native_studio.game_engine.sheltered_hub_fields import (
    SHELTERED_HUB_CAPABILITY,
    WRITING_DESK_TYPE,
    MEMORY_SHELVES_TYPE,
    SHARED_PLAY_TYPE,
    STATION_TYPES,
    PENCIL_MODES,
    validate_writing_desk,
    validate_memory_shelves,
    validate_shared_play,
)
from native_studio.game_engine.creator_payload import Create


@pytest.mark.tier1
@pytest.mark.feature_1
class TestShelteredHubStationsTier1:
    """Tier 1 feature test suite for Feature 1: Sheltered Hub Stations."""

    def test_f01_cpp_contracts_validation(self, platform_paths, run_cmd):
        """Verify native C++ contract test binary passes all 34 checks."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_sheltered_hub_contracts_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=15.0)
        result.assert_success()
        result.assert_stdout_contains("PASS: all 34 sheltered hub station contract checks passed successfully")

    def test_f01_writing_desk_state_transitions(self):
        """Verify writing desk state contract transitions from unclaimed to active journaling."""
        # Initial un-claimed state: pencil not claimed, 0 notes written, valid coordinates
        initial_fields = {
            "pencil_claimed": False,
            "mode": "record",
            "notes_written": 0,
            "x": -38.0,
            "y": 0.75,
            "z": 18.0,
        }
        res_initial = validate_writing_desk(initial_fields)
        assert res_initial["pencil_claimed"] is False
        assert res_initial["mode"] == "record"
        assert res_initial["notes_written"] == 0

        # Pencil claimed, switch to 'trace' mode
        claimed_fields = {
            "pencil_claimed": True,
            "mode": "trace",
            "notes_written": 0,
            "x": -38.0,
            "y": 0.75,
            "z": 18.0,
        }
        res_claimed = validate_writing_desk(claimed_fields)
        assert res_claimed["pencil_claimed"] is True
        assert res_claimed["mode"] == "trace"

        # Journaling notes with 'sketch' mode
        journal_fields = {
            "pencil_claimed": True,
            "mode": "sketch",
            "notes_written": 5,
            "x": -38.0,
            "y": 0.75,
            "z": 18.0,
        }
        res_journal = validate_writing_desk(journal_fields)
        assert res_journal["pencil_claimed"] is True
        assert res_journal["mode"] == "sketch"
        assert res_journal["notes_written"] == 5

    def test_f01_memory_shelves_capacity_and_secret(self):
        """Verify memory shelves item placement progression and secret reveal contract."""
        # Empty shelves initial state
        empty_fields = {
            "items_placed": 0,
            "capacity": 12,
            "secret_revealed": False,
            "x": -33.5,
            "y": 1.5,
            "z": 16.5,
        }
        res_empty = validate_memory_shelves(empty_fields)
        assert res_empty["items_placed"] == 0
        assert res_empty["capacity"] == 12
        assert res_empty["secret_revealed"] is False

        # Place 2 items: below secret threshold (threshold is >= 3)
        two_items = {
            "items_placed": 2,
            "capacity": 12,
            "secret_revealed": False,
            "x": -33.5,
            "y": 1.5,
            "z": 16.5,
        }
        res_two = validate_memory_shelves(two_items)
        assert res_two["items_placed"] == 2
        assert res_two["secret_revealed"] is False

        # Place 3 items and reveal secret compartment
        secret_fields = {
            "items_placed": 3,
            "capacity": 12,
            "secret_revealed": True,
            "x": -33.5,
            "y": 1.5,
            "z": 16.5,
        }
        res_secret = validate_memory_shelves(secret_fields)
        assert res_secret["items_placed"] == 3
        assert res_secret["secret_revealed"] is True

        # Fill to full capacity
        full_fields = {
            "items_placed": 12,
            "capacity": 12,
            "secret_revealed": True,
            "x": -33.5,
            "y": 1.5,
            "z": 16.5,
        }
        res_full = validate_memory_shelves(full_fields)
        assert res_full["items_placed"] == 12

    def test_f01_shared_play_power_and_session(self):
        """Verify shared play corner power prerequisite and interactive session activation."""
        # Unpowered display state
        unpowered_fields = {
            "display_powered": False,
            "session_active": False,
            "x": -36.0,
            "y": 0.6,
            "z": 10.0,
        }
        res_unpowered = validate_shared_play(unpowered_fields)
        assert res_unpowered["display_powered"] is False
        assert res_unpowered["session_active"] is False

        # Power restored to display
        powered_fields = {
            "display_powered": True,
            "session_active": False,
            "x": -36.0,
            "y": 0.6,
            "z": 10.0,
        }
        res_powered = validate_shared_play(powered_fields)
        assert res_powered["display_powered"] is True
        assert res_powered["session_active"] is False

        # Active play session when display is powered
        active_fields = {
            "display_powered": True,
            "session_active": True,
            "x": -36.0,
            "y": 0.6,
            "z": 10.0,
        }
        res_active = validate_shared_play(active_fields)
        assert res_active["display_powered"] is True
        assert res_active["session_active"] is True

    def test_f01_hub_entities_payload_construction(self):
        """Verify constructing Create entity rows for all three stations with UUIDs."""
        desk_id = str(uuid.uuid4())
        desk_fields = (
            ("x", -38.0), ("y", 0.75), ("z", 18.0),
            ("half_x", 1.2), ("half_y", 0.75), ("half_z", 0.8),
            ("pencil_claimed", 1.0), ("mode", 1.0), ("notes_written", 3.0)
        )
        entity_desk = Create("writing_desk", "Writing Desk", desk_id, desk_fields)
        assert entity_desk.alias == "writing_desk"
        assert entity_desk.name == "Writing Desk"
        assert entity_desk.uuid == desk_id

        shelves_id = str(uuid.uuid4())
        shelves_fields = (
            ("x", -33.5), ("y", 1.5), ("z", 16.5),
            ("half_x", 0.5), ("half_y", 1.5), ("half_z", 1.2),
            ("items_placed", 3.0), ("capacity", 12.0), ("secret_revealed", 1.0)
        )
        entity_shelves = Create("memory_shelves", "Memory Shelves", shelves_id, shelves_fields)
        assert entity_shelves.alias == "memory_shelves"
        assert entity_shelves.uuid == shelves_id

        play_id = str(uuid.uuid4())
        play_fields = (
            ("x", -36.0), ("y", 0.6), ("z", 10.0),
            ("half_x", 1.5), ("half_y", 0.6), ("half_z", 1.5),
            ("power_restored", 1.0), ("circuit_bridged", 1.0), ("stage", 2.0)
        )
        entity_play = Create("shared_play", "Shared Play Corner", play_id, play_fields)
        assert entity_play.alias == "shared_play"
        assert entity_play.uuid == play_id

    def test_f01_station_type_constants_and_capabilities(self):
        """Verify station type constants, pencil modes, and Sheltered Hub capability strings."""
        assert SHELTERED_HUB_CAPABILITY == "chapter-sheltered-hub-stations-v1"
        assert WRITING_DESK_TYPE == "firstboot.WritingDesk"
        assert MEMORY_SHELVES_TYPE == "firstboot.MemoryShelves"
        assert SHARED_PLAY_TYPE == "firstboot.SharedPlay"
        assert set(STATION_TYPES) == {WRITING_DESK_TYPE, MEMORY_SHELVES_TYPE, SHARED_PLAY_TYPE}
        assert set(PENCIL_MODES) == {"record", "trace", "sketch"}
