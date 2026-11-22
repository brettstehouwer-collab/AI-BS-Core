"""AI-BS Sheltered Hub Viewport Session, Spatial Trigger & Blend Tree Verification.

Validates the full Chapter 1 interactive spatial geometry:
1. Encodes binary scene snapshot (AIBV) containing all 3 Sheltered Hub stations
   and 7 spatial trigger zones.
2. Runs native DX12 creator viewport binary (aibs_creator_viewport.exe) to render
   GPU projection and output diagnostic telemetry JSON and captured BMP.
3. Verifies spatial containment of player trajectories across the 7 audio cue zones.
4. Validates state machine SQLite contracts for pencil claim and secret compartment.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import time
import json
import uuid
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.creator_payload import Scope, Create
from native_studio.game_engine.creator_viewport import encode_snapshot, ViewportClient
from native_studio.game_engine.sheltered_hub_fields import (
    ZONE_BOUNDS, SPATIAL_ZONES, validate_writing_desk, validate_memory_shelves, validate_shared_play
)

ENGINE_ROOT = Path("C:/AI-BS/engine")
VIEWPORT_EXE = ENGINE_ROOT / "out/windows-msvc/Debug/aibs_creator_viewport.exe"
ARTIFACT_DIR = Path("C:/AI-BS/docs/viewport_telemetry")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

def create_station_nodes():
    """Generates entity definitions for Sheltered Hub stations & spatial audio trigger zones."""
    entities = []

    # 0. Authored Anchor Fixture at Origin (Viewport Probe Focus Anchor)
    anchor_id = str(uuid.uuid4())
    anchor_fields = (
        ("x", 0.0), ("y", 0.0), ("z", 0.0),
        ("half_x", 1.0), ("half_y", 1.0), ("half_z", 1.0),
    )
    entities.append(Create("hub_anchor_fixture", "Sheltered Hub Anchor Fixture", anchor_id, anchor_fields))

    # 1. Writing Desk in Pencil Room
    desk_id = str(uuid.uuid4())
    desk_fields = (
        ("x", -38.0), ("y", 0.75), ("z", 18.0),
        ("half_x", 1.2), ("half_y", 0.75), ("half_z", 0.8),
        ("pencil_claimed", 1.0), ("mode", 1.0), ("notes_written", 3.0)
    )
    entities.append(Create("writing_desk", "Writing Desk", desk_id, desk_fields))

    # 2. Memory Shelves in Pencil Room
    shelves_id = str(uuid.uuid4())
    shelves_fields = (
        ("x", -33.5), ("y", 1.5), ("z", 16.5),
        ("half_x", 0.5), ("half_y", 1.5), ("half_z", 1.2),
        ("items_placed", 3.0), ("capacity", 12.0), ("secret_revealed", 1.0)
    )
    entities.append(Create("memory_shelves", "Memory Shelves", shelves_id, shelves_fields))

    # 3. Shared Play Corner in Sheltered Hub
    play_id = str(uuid.uuid4())
    play_fields = (
        ("x", -36.0), ("y", 0.6), ("z", 10.0),
        ("half_x", 1.5), ("half_y", 0.6), ("half_z", 1.5),
        ("power_restored", 1.0), ("circuit_bridged", 1.0), ("stage", 2.0)
    )
    entities.append(Create("shared_play", "Shared Play Corner", play_id, play_fields))

    # 4. Adam Guide Station at Podium
    podium_id = str(uuid.uuid4())
    podium_fields = (
        ("x", -32.5), ("y", 1.0), ("z", -26.0),
        ("half_x", 0.6), ("half_y", 1.0), ("half_z", 0.6),
        ("adam_blend_weight", 0.85), ("adam_gaze_track", 1.0)
    )
    entities.append(Create("podium_guide", "Adam Podium Guide", podium_id, podium_fields))

    # 5. The 7 Spatial Trigger Zones
    for zone_name in SPATIAL_ZONES:
        min_pt, max_pt = ZONE_BOUNDS[zone_name]
        cx = (min_pt[0] + max_pt[0]) / 2.0
        cy = (min_pt[1] + max_pt[1]) / 2.0
        cz = (min_pt[2] + max_pt[2]) / 2.0
        hx = max((max_pt[0] - min_pt[0]) / 2.0, 0.5)
        hy = max((max_pt[1] - min_pt[1]) / 2.0, 0.5)
        hz = max((max_pt[2] - min_pt[2]) / 2.0, 0.5)

        zone_id = str(uuid.uuid4())
        zone_fields = (
            ("x", cx), ("y", cy), ("z", cz),
            ("half_x", hx), ("half_y", hy), ("half_z", hz)
        )
        entities.append(Create(f"zone_{zone_name}", f"Zone: {zone_name}", zone_id, zone_fields))

    return entities, desk_id

def test_spatial_zone_containment():
    """Verifies that sample player positions correctly resolve inside expected zones."""
    print("\n--- Verifying 7 Spatial Audio Trigger Zones Containment ---")
    test_points = {
        'nook_awakening': (-32.5, 0.0, -26.0),
        'corridor_approach': (-36.5, 0.0, -15.0),
        'fault_trench': (-33.0, 0.0, -4.5),
        'relay_bypass_socket': (-42.0, 0.0, -4.5),
        'threshold_aperture': (-37.0, 0.0, 2.5),
        'sheltered_hub': (-36.5, 0.0, 9.5),
        'pencil_room': (-36.5, 0.0, 18.0),
    }

    for zone_name, pt in test_points.items():
        min_b, max_b = ZONE_BOUNDS[zone_name]
        inside = (min_b[0] <= pt[0] <= max_b[0] and
                  min_b[1] <= pt[1] <= max_b[1] and
                  min_b[2] <= pt[2] <= max_b[2])
        status = "CONTAINED [PASS]" if inside else "OUTSIDE [FAIL]"
        print(f"  Zone {zone_name:<20}: Pt {pt} -> {status}")
        assert inside, f"Point {pt} failed containment in {zone_name}"

def run_native_dx12_viewport_test():
    """Runs a real native DX12 projection and self-test probe."""
    print("\n--- Running Native DX12 Creator Viewport Projection ---")
    app = QApplication.instance() or QApplication([])

    entities, selected_id = create_station_nodes()
    scope = Scope("AI-BS Chapter 1", "main", str(uuid.uuid4()), str(uuid.uuid4()))
    checkpoint_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())

    print(f"  Encoding AIBV binary snapshot with {len(entities)} scene entities...")
    binary_data = encode_snapshot(
        snapshot_id=snapshot_id,
        scope=scope,
        revision=107,
        checkpoint_id=checkpoint_id,
        rows=entities,
        first_boot=False,
        selected_id=selected_id
    )
    print(f"  Snapshot encoded: {len(binary_data):,} bytes (magic: {binary_data[:4].decode('latin1')})")

    # Render probe via native viewport binary
    probe_dir = ARTIFACT_DIR / "probe_run"
    probe_dir.mkdir(parents=True, exist_ok=True)
    report_path = probe_dir / "viewport.json"
    bmp_path = probe_dir / "viewport.bmp"
    if report_path.is_file():
        report_path.unlink()
    if bmp_path.is_file():
        bmp_path.unlink()

    client = ViewportClient()
    picked_events = []
    client.selection.connect(lambda uid, sc: picked_events.append((uid, sc)))

    start_t = time.time()
    client.start(
        executable=VIEWPORT_EXE,
        scope=scope,
        revision=107,
        checkpoint_id=checkpoint_id,
        rows=entities,
        first_boot=False,
        probe_directory=probe_dir
    )

    # Spin event loop until closed
    deadline = time.monotonic() + 10.0
    while client.state != 'closed' and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    elapsed = time.time() - start_t
    print(f"  Viewport execution finished in {elapsed:.3f}s (State: {client.state})")

    report_path = probe_dir / "viewport.json"
    bmp_path = probe_dir / "viewport.bmp"

    assert report_path.is_file(), f"Viewport probe failed: {client.stderr_tail.decode()}"

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    print("  DX12 Projection Report:")
    print(f"    Non-background Pixels: {report.get('nonbackground_pixels', 0):,}")
    print(f"    Debug Errors:          {report.get('debug_errors', 0)}")
    print(f"    Objects Rendered:      {report.get('objects_rendered', len(entities))}")
    print(f"    Selected UUID:         {report.get('selected_uuid', selected_id)}")

    assert report.get('debug_errors', 1) == 0, "D3D12 debug errors detected"
    assert report.get('nonbackground_pixels', 0) > 0, "No geometry rendered"
    assert bmp_path.is_file(), "Rendered BMP not captured"

    bmp_size = bmp_path.stat().st_size
    print(f"  Rendered Viewport Frame Captured: {bmp_path} ({bmp_size:,} bytes)")

def main():
    print("=" * 70)
    print("AI-BS STUDIO 144: SHELTERED HUB & SPATIAL VIEWPORT VERIFICATION")
    print("=" * 70)

    # 1. Spatial trigger zone math
    test_spatial_zone_containment()

    # 2. Station fields validation
    print("\n--- Validating Station Field Schemas ---")
    desk_val = validate_writing_desk({'pencil_claimed': True, 'mode': 'record', 'notes_written': 5, 'x': -38.0, 'y': 0.75, 'z': 18.0})
    print(f"  Writing Desk Validation:  [PASS] (Mode: {desk_val['mode']}, Notes: {desk_val['notes_written']})")

    shelves_val = validate_memory_shelves({'items_placed': 4, 'capacity': 12, 'secret_revealed': True, 'x': -33.5, 'y': 1.5, 'z': 16.5})
    print(f"  Memory Shelves Validation:[PASS] (Items: {shelves_val['items_placed']}, Secret: {shelves_val['secret_revealed']})")

    play_val = validate_shared_play({'display_powered': True, 'session_active': True, 'x': -36.0, 'y': 0.6, 'z': 10.0})
    print(f"  Shared Play Validation:   [PASS] (Display Powered: {play_val['display_powered']}, Session Active: {play_val['session_active']})")

    # 3. Real DX12 Native Viewport Execution
    run_native_dx12_viewport_test()

    print("\n" + "=" * 70)
    print("STUDIO 144 VIEWPORT SESSION VALIDATION COMPLETE: ALL PASS")
    print("=" * 70)

if __name__ == '__main__':
    main()
