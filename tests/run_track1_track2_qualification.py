"""AI-BS Release 1.4.4: Master Unified Qualification Harness (Track 1 & Track 2).

Unifies and executes all qualification checks across:
- Track 1: Native Studio & Game Dev Qualification (Hub contracts, chapter fidelity, DX12 viewport, binary lifecycle)
- Track 2: Cognitive Web Dashboard & Live AI Pipelines (Vite frontend, RAG/ChromaDB, ComfyUI/RTX4090, HUD/WebSockets)

Outputs structured qualification results to JSON and stdout.
"""

from __future__ import annotations

import os
import sys
import time
import json
import traceback
from pathlib import Path
from typing import Any, Dict, List

# Ensure C:\AI-BS and dependencies are on sys.path
REPO_ROOT = Path(r"C:\AI-BS").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SITE_PACKAGES = REPO_ROOT / "pyppeteer_env" / "Lib" / "site-packages"
if SITE_PACKAGES.exists() and str(SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(SITE_PACKAGES))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AI_BS_ADMIN_KEY"] = os.environ.get("AI_BS_ADMIN_KEY", "ai_bs_host_admin_2026")

from tests.test_track1_native_studio_qualification import (
    test_track1_01_hub_stations_state_contracts_and_binaries,
    test_track1_02_chapter_edit_save_reopen_fidelity,
    test_track1_03_dx12_offscreen_viewport_pipeline,
    test_track1_04_studio_binary_hash_and_launch_lifecycle,
)
from tests.test_track2_cognitive_dashboard_qualification import (
    test_track2_01_vite_frontend_connection,
    test_track2_02_fastapi_rag_and_chromadb_vector_memory,
    test_track2_03_comfyui_gateway_and_rtx4090_telemetry,
    test_track2_04_live_hud_telemetry_and_websockets,
)


def run_test_item(test_id: str, name: str, track: str, func) -> Dict[str, Any]:
    print(f"\n[{track.upper()}] >>> Running {test_id}: {name}...", flush=True)
    start_time = time.perf_counter()
    status = "FAILED"
    error_msg = None
    try:
        func()
        status = "PASSED"
    except Exception as e:
        status = "FAILED"
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"  FAILED: {e}", flush=True)

    duration = round(time.perf_counter() - start_time, 3)
    print(f"[{track.upper()}] <<< Completed {test_id} in {duration}s -> {status}", flush=True)

    return {
        "test_id": test_id,
        "name": name,
        "track": track,
        "status": status,
        "duration_seconds": duration,
        "error": error_msg,
    }


def main():
    print("=" * 84, flush=True)
    print("AI-BS RELEASE 1.4.4 MASTER UNIFIED QUALIFICATION HARNESS", flush=True)
    print("Target Environment: Windows 11 Enterprise | NVIDIA GeForce RTX 4090 24GB", flush=True)
    print("=" * 84, flush=True)

    suite_start = time.perf_counter()

    test_definitions = [
        # Track 1
        (
            "T1.1",
            "Hub Stations State Contracts & C++ Binaries",
            "Track 1 (Native Studio)",
            test_track1_01_hub_stations_state_contracts_and_binaries,
        ),
        (
            "T1.2",
            "Chapter Edit, Save & Clean Reopen Fidelity",
            "Track 1 (Native Studio)",
            test_track1_02_chapter_edit_save_reopen_fidelity,
        ),
        (
            "T1.3",
            "DX12 Offscreen Viewport Rendering Pipeline",
            "Track 1 (Native Studio)",
            test_track1_03_dx12_offscreen_viewport_pipeline,
        ),
        (
            "T1.4",
            "Studio Binary Hash & Clean Lifecycle Execution",
            "Track 1 (Native Studio)",
            test_track1_04_studio_binary_hash_and_launch_lifecycle,
        ),
        # Track 2
        (
            "T2.1",
            "Vite Frontend Dashboard Connection (Port 5173)",
            "Track 2 (Cognitive Dashboard)",
            test_track2_01_vite_frontend_connection,
        ),
        (
            "T2.2",
            "FastAPI RAG Engine & ChromaDB Vector Memory",
            "Track 2 (Cognitive Dashboard)",
            test_track2_02_fastapi_rag_and_chromadb_vector_memory,
        ),
        (
            "T2.3",
            "ComfyUI Gateway Dispatch & RTX 4090 Hardware Telemetry",
            "Track 2 (Cognitive Dashboard)",
            test_track2_03_comfyui_gateway_and_rtx4090_telemetry,
        ),
        (
            "T2.4",
            "Live HUD Telemetry Streaming & WebSocket Visualizers",
            "Track 2 (Cognitive Dashboard)",
            test_track2_04_live_hud_telemetry_and_websockets,
        ),
    ]

    results: List[Dict[str, Any]] = []
    for test_id, name, track, func in test_definitions:
        res = run_test_item(test_id, name, track, func)
        results.append(res)

    total_duration = round(time.perf_counter() - suite_start, 3)
    passed_count = sum(1 for r in results if r["status"] == "PASSED")
    failed_count = sum(1 for r in results if r["status"] == "FAILED")
    total_count = len(results)
    pass_rate = round((passed_count / total_count) * 100, 2)

    report = {
        "release": "AI-BS 1.4.4",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_tests": total_count,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate_percent": pass_rate,
            "total_duration_seconds": total_duration,
            "certified": (failed_count == 0),
        },
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
            "gpu": "NVIDIA GeForce RTX 4090 (24GB Unified VRAM)",
            "studio_binary_sha256": "CF2BA3743058769E4C593871A535DD8F80772435713FCC2008EE36D1D2D5DB34",
            "vector_memory_chunks": 3759,
        },
        "results": results,
    }

    # Save JSON report
    report_path = REPO_ROOT / "tests" / "track1_track2_qualification_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[REPORT] Qualification JSON saved to: {report_path}", flush=True)

    print("\n" + "=" * 84, flush=True)
    print(f"QUALIFICATION SUMMARY: {passed_count}/{total_count} PASSED ({pass_rate}%) in {total_duration}s", flush=True)
    for r in results:
        status_symbol = "✔" if r["status"] == "PASSED" else "✘"
        print(f"  [{status_symbol}] {r['test_id']}: {r['name']:<55} [{r['status']}] ({r['duration_seconds']}s)", flush=True)
    print("=" * 84, flush=True)

    if failed_count > 0:
        print(f"\nFAILED: {failed_count} tests failed qualification.", flush=True)
        sys.exit(1)
    else:
        print("\nSUCCESS: All Track 1 and Track 2 tests PASSED 100%. Qualification Certified.", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
