"""Tier 3 Pairwise Test P18: Opaque-Box E2E Runner (F18) + Subsystem Health Audits (F14..F17).

Validates that the master runner successfully executes and captures health metrics
across Native Studio, FastAPI, ComfyUI, and Vite frontend.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import PlatformPaths


@pytest.mark.tier3
class TestP18E2ERunnerSubsystemAudits:
    """Pairwise F18 x (F14, F15, F16, F17): E2E Test Runner and Subsystem Health Audits."""

    def test_p18_all_four_subsystems_pass_in_m5_audit_report(self, platform_paths: PlatformPaths) -> None:
        """Verify M5 health audit report marks native_studio, fastapi, comfyui, vite all PASS."""
        report_file = platform_paths.base_dir / "tests" / "m5_audit_report.json"
        assert report_file.exists(), f"M5 report missing: {report_file}"

        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("overall_passed") is True, f"Audit report overall_passed not True: {data}"
        subsystems = data.get("subsystems", {})
        for name in ("native_studio", "fastapi", "comfyui", "vite"):
            assert name in subsystems, f"Subsystem '{name}' missing from audit report"
            assert subsystems[name].get("passed") is True, f"Subsystem '{name}' did not pass: {subsystems[name]}"

    def test_p18_all_subsystem_ports_verified_active(self, platform_paths: PlatformPaths) -> None:
        """Verify that backend (8080), comfyui (8188/8189), and vite (5173) are active."""
        import socket

        for port in (8080, 8188, 8189, 5173):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            res = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            assert res == 0, f"Port {port} is not listening"
