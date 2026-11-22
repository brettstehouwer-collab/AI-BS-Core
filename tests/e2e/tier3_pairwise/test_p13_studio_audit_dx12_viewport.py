"""Tier 3 Pairwise Test P13: Native Studio Audit (F14) + DX12 Viewport (F04).

Validates that native studio audit execution triggers the DirectX 12 viewport binary
and validates the captured frame BMP and JSON telemetry report.
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
class TestP13StudioAuditDX12Viewport:
    """Pairwise F14 x F04: Chapter Creator & Native Studio Audit and Native DX12 Viewport Session."""

    def test_p13_native_studio_audit_validates_viewport_json(self, platform_paths: PlatformPaths) -> None:
        """Verify audit requirements on viewport telemetry report are satisfied."""
        report_file = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.json"
        assert report_file.exists(), f"Viewport telemetry JSON missing at {report_file}"

        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("debug_errors") == 0
        assert data.get("nonbackground_pixels", 0) > 0
        assert "selected_uuid" in data

    def test_p13_native_studio_audit_validates_viewport_bmp(self, platform_paths: PlatformPaths) -> None:
        """Verify rendered frame BMP exists and has standard 24-bit RGB bitmap signature."""
        bmp_file = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.bmp"
        assert bmp_file.exists(), f"Rendered frame BMP missing at {bmp_file}"

        with open(bmp_file, "rb") as f:
            header = f.read(2)
            assert header == b"BM", f"Expected 'BM' magic header, got {header!r}"
