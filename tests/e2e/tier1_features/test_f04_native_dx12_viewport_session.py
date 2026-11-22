"""Tier 1 Feature Tests: Feature 4 - Native DX12 Viewport Session.

Validates the native C++20 DirectX 12 Creator Viewport pipeline:
- C++ creator viewport test suite (aibs_creator_viewport_tests.exe)
- C++ chapter viewport test suite (aibs_chapter_viewport_tests.exe)
- Opaque-box process execution of aibs_creator_viewport.exe with --self-test
- Viewport diagnostic telemetry JSON contract (nonbackground_pixels > 0, debug_errors == 0)
- Viewport captured BMP raster file structure (BM magic, 1100x740 geometry, color depth)
- UUID picking and selection fidelity under native DX12 rendering
"""

from __future__ import annotations

import json
import struct
import uuid
from pathlib import Path
import pytest

from native_studio.game_engine.creator_payload import Create, Scope
from native_studio.game_engine.creator_viewport import encode_snapshot


def build_test_snapshot(target_path: Path, center_target_id: str) -> None:
    """Helper to author an AIBV binary snapshot with Sheltered Hub entities."""
    entities = [
        Create(
            "target_fixture",
            "Target Center Fixture",
            center_target_id,
            (("x", 0.0), ("y", 0.0), ("z", 0.0), ("half_x", 1.0), ("half_y", 1.0), ("half_z", 1.0)),
        ),
        Create(
            "writing_desk",
            "Writing Desk",
            str(uuid.uuid4()),
            (
                ("x", -38.0), ("y", 0.75), ("z", 18.0),
                ("half_x", 1.2), ("half_y", 0.75), ("half_z", 0.8),
                ("pencil_claimed", 1.0), ("mode", 1.0), ("notes_written", 3.0),
            ),
        ),
        Create(
            "memory_shelves",
            "Memory Shelves",
            str(uuid.uuid4()),
            (
                ("x", -33.5), ("y", 1.5), ("z", 16.5),
                ("half_x", 0.5), ("half_y", 1.5), ("half_z", 1.2),
                ("items_placed", 3.0), ("capacity", 12.0), ("secret_revealed", 1.0),
            ),
        ),
    ]

    scope = Scope("AI-BS Chapter 1", "main", str(uuid.uuid4()), str(uuid.uuid4()))
    raw_bytes = encode_snapshot(
        snapshot_id=str(uuid.uuid4()),
        scope=scope,
        revision=107,
        checkpoint_id=str(uuid.uuid4()),
        rows=entities,
        first_boot=False,
        selected_id=center_target_id,
    )
    target_path.write_bytes(raw_bytes)


@pytest.mark.tier1
@pytest.mark.feature_4
class TestNativeDx12ViewportSessionTier1:
    """Tier 1 feature test suite for Feature 4: Native DX12 Viewport Session."""

    def test_f04_creator_viewport_cpp_unit_tests(self, platform_paths, run_cmd):
        """Execute C++ creator viewport test suite verifying projection, clipping, and picking."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_creator_viewport_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=20.0)
        result.assert_success()
        result.assert_stdout_contains("Viewport projection, UUID picking, every truncation and invalid geometry passed")

    def test_f04_chapter_viewport_cpp_unit_tests(self, platform_paths, run_cmd):
        """Execute C++ chapter viewport test suite verifying typed envelope and immutable projection."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_chapter_viewport_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=20.0)
        result.assert_success()
        result.assert_stdout_contains("Typed chapter viewport envelope, immutable projection, scope and bounds passed")

    def test_f04_native_dx12_viewport_self_test_execution(self, platform_paths, run_cmd, tmp_path, clean_artifacts):
        """Execute native DX12 creator viewport binary in offscreen self-test mode."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_creator_viewport.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        snapshot_file = clean_artifacts(tmp_path / "scene.aibv")
        stop_file = clean_artifacts(tmp_path / "stop.signal")
        bmp_file = clean_artifacts(tmp_path / "viewport.bmp")
        report_file = clean_artifacts(tmp_path / "viewport.json")

        selected_uuid = str(uuid.uuid4())
        build_test_snapshot(snapshot_file, selected_uuid)

        cmd = [
            str(exe_path),
            "--snapshot", str(snapshot_file),
            "--stop-file", str(stop_file),
            "--capture", str(bmp_file),
            "--report", str(report_file),
            "--self-test",
        ]

        result = run_cmd(cmd, timeout=30.0)
        result.assert_success()
        result.assert_stdout_contains("AIBV1 READY")
        result.assert_stdout_contains("AIBV1 PICK")

    def test_f04_viewport_json_telemetry_schema(self, platform_paths, run_cmd, tmp_path, clean_artifacts):
        """Verify that viewport telemetry JSON contains required fields and satisfies error-free rendering."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_creator_viewport.exe"
        snapshot_file = clean_artifacts(tmp_path / "scene_schema.aibv")
        stop_file = clean_artifacts(tmp_path / "stop_schema.signal")
        bmp_file = clean_artifacts(tmp_path / "viewport_schema.bmp")
        report_file = clean_artifacts(tmp_path / "viewport_schema.json")

        selected_uuid = str(uuid.uuid4())
        build_test_snapshot(snapshot_file, selected_uuid)

        cmd = [
            str(exe_path),
            "--snapshot", str(snapshot_file),
            "--stop-file", str(stop_file),
            "--capture", str(bmp_file),
            "--report", str(report_file),
            "--self-test",
        ]
        result = run_cmd(cmd, timeout=30.0)
        result.assert_success()

        assert report_file.is_file(), "viewport.json report was not generated"
        report_data = json.loads(report_file.read_text(encoding="utf-8"))

        # Verify required keys
        assert "nonbackground_pixels" in report_data
        assert "debug_errors" in report_data
        assert "debug_warnings" in report_data
        assert "world_id" in report_data
        assert "selected_uuid" in report_data

        # Strict GPU assertion criteria from PROJECT.md
        assert report_data["debug_errors"] == 0, f"D3D12 debug errors detected: {report_data['debug_errors']}"
        assert report_data["nonbackground_pixels"] > 0, "No non-background pixels were rendered"
        assert report_data["debug_layer"] is True

    def test_f04_viewport_bmp_raster_integrity(self, platform_paths, run_cmd, tmp_path, clean_artifacts):
        """Verify captured viewport BMP image has valid header, 1100x740 dimensions, and non-empty payload."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_creator_viewport.exe"
        snapshot_file = clean_artifacts(tmp_path / "scene_bmp.aibv")
        stop_file = clean_artifacts(tmp_path / "stop_bmp.signal")
        bmp_file = clean_artifacts(tmp_path / "viewport_raster.bmp")
        report_file = clean_artifacts(tmp_path / "viewport_raster.json")

        selected_uuid = str(uuid.uuid4())
        build_test_snapshot(snapshot_file, selected_uuid)

        cmd = [
            str(exe_path),
            "--snapshot", str(snapshot_file),
            "--stop-file", str(stop_file),
            "--capture", str(bmp_file),
            "--report", str(report_file),
            "--self-test",
        ]
        result = run_cmd(cmd, timeout=30.0)
        result.assert_success()

        assert bmp_file.is_file(), "Captured BMP file was not created"
        bmp_bytes = bmp_file.read_bytes()
        assert len(bmp_bytes) > 100_000, f"BMP file unexpectedly small: {len(bmp_bytes)} bytes"

        # BMP Header check (Magic: BM = 0x42 0x4D)
        magic = bmp_bytes[:2]
        assert magic == b"BM", f"Invalid BMP magic: {magic}"

        # BMP BITMAPINFOHEADER check at offset 14:
        # header_size (4 bytes), width (4 bytes int32), height (4 bytes int32), planes (2 bytes), bpp (2 bytes)
        info_header = bmp_bytes[14:30]
        header_size, width, height, planes, bpp = struct.unpack("<IiiHH", info_header)
        assert header_size == 40, f"Expected standard 40-byte BITMAPINFOHEADER, got {header_size}"
        assert width == 1100, f"Expected width 1100, got {width}"
        assert abs(height) == 740, f"Expected height 740, got {height}"
        assert bpp in (24, 32), f"Expected 24-bit or 32-bit color depth, got {bpp}"

    def test_f04_viewport_uuid_selection_fidelity(self, platform_paths, run_cmd, tmp_path, clean_artifacts):
        """Verify that authoring UUID selection is preserved by DX12 ray-cast picking probe."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_creator_viewport.exe"
        snapshot_file = clean_artifacts(tmp_path / "scene_pick.aibv")
        stop_file = clean_artifacts(tmp_path / "stop_pick.signal")
        bmp_file = clean_artifacts(tmp_path / "viewport_pick.bmp")
        report_file = clean_artifacts(tmp_path / "viewport_pick.json")

        target_desk_id = str(uuid.uuid4())
        build_test_snapshot(snapshot_file, target_desk_id)

        cmd = [
            str(exe_path),
            "--snapshot", str(snapshot_file),
            "--stop-file", str(stop_file),
            "--capture", str(bmp_file),
            "--report", str(report_file),
            "--self-test",
        ]
        result = run_cmd(cmd, timeout=30.0)
        result.assert_success()

        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        assert report_data["selected_uuid"] == target_desk_id, (
            f"Picked UUID '{report_data['selected_uuid']}' did not match targeted '{target_desk_id}'"
        )
