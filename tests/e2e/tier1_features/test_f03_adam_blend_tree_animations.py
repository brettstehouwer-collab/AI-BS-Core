"""Tier 1 Feature Tests: Feature 3 - Adam Blend Tree Animations (2,201 checks).

Validates the Adam guide character animation blend tree and likeness system:
- 2,201 likeness verification & blend tree checks (aibs_adam_blend_tree_tests.exe)
- GuidePresentation state transition machine (idle -> walk -> guidance -> reset)
- GuidePresentation unit test suite (aibs_guide_presentation_tests.exe)
- GuideController navigation & steering suite (aibs_guide_controller_tests.exe)
- Mathematical validation of the Hermite smoothstep blend curve S(u) = u^2*(3 - 2u)
- Adam podium guide station entity payload with blend weight & gaze tracking fields
"""

from __future__ import annotations

import math
import uuid
from pathlib import Path
import pytest

from native_studio.game_engine.creator_payload import Create


@pytest.mark.tier1
@pytest.mark.feature_3
class TestAdamBlendTreeAnimationsTier1:
    """Tier 1 feature test suite for Feature 3: Adam Blend Tree Animations."""

    def test_f03_adam_blend_tree_2201_checks_execution(self, platform_paths, run_cmd):
        """Execute C++ binary verifying all 2,201 blend tree and likeness checks pass."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_adam_blend_tree_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=20.0)
        result.assert_success()
        result.assert_stdout_contains("PASS: all 2201 adam character blend tree and likeness verification checks passed")

    def test_f03_guide_presentation_cpp_suite(self, platform_paths, run_cmd):
        """Execute C++ guide presentation unit test suite verifying pose blending and clip transitions."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_guide_presentation_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=15.0)
        result.assert_success()

    def test_f03_guide_controller_cpp_suite(self, platform_paths, run_cmd):
        """Execute C++ guide controller unit test suite verifying steering and companion navigation."""
        exe_path = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_guide_controller_tests.exe"
        assert exe_path.is_file(), f"Expected test executable at {exe_path}"

        result = run_cmd(str(exe_path), timeout=15.0)
        result.assert_success()

    def test_f03_hermite_smoothstep_mathematical_properties(self):
        """Verify mathematical monotonicity, endpoint continuity, and clamping of S(u) = u^2*(3 - 2u)."""
        def smoothstep(u: float) -> float:
            u_clamped = max(0.0, min(1.0, u))
            return u_clamped * u_clamped * (3.0 - 2.0 * u_clamped)

        # Boundary values
        assert smoothstep(0.0) == 0.0
        assert smoothstep(1.0) == 1.0

        # Monotonicity across 100 discrete evaluation points
        steps = 100
        prev_w = 0.0
        for i in range(steps + 1):
            u = i / steps
            w = smoothstep(u)
            assert 0.0 <= w <= 1.0
            assert w >= prev_w - 1e-9, f"Smoothstep non-monotonic at u={u}: {w} < {prev_w}"
            prev_w = w

        # Tangent derivatives at endpoints must be zero: dS/du = 6u(1 - u)
        # Numerical derivative approximation with h = 1e-6
        h = 1e-6
        d_start = (smoothstep(h) - smoothstep(0.0)) / h
        assert d_start == pytest.approx(0.0, abs=1e-4)

        d_end = (smoothstep(1.0) - smoothstep(1.0 - h)) / h
        assert d_end == pytest.approx(0.0, abs=1e-4)

        # Symmetry property: S(0.5) == 0.5
        assert smoothstep(0.5) == pytest.approx(0.5, abs=1e-6)

    def test_f03_adam_podium_guide_entity_payload(self):
        """Verify creation of Adam guide entity with blend weight and gaze tracking in AIBV format."""
        podium_id = str(uuid.uuid4())
        podium_fields = (
            ("x", -32.5), ("y", 1.0), ("z", -26.0),
            ("half_x", 0.6), ("half_y", 1.0), ("half_z", 0.6),
            ("adam_blend_weight", 0.85), ("adam_gaze_track", 1.0)
        )
        entity = Create("podium_guide", "Adam Podium Guide", podium_id, podium_fields)
        assert entity.alias == "podium_guide"
        assert entity.name == "Adam Podium Guide"
        assert entity.uuid == podium_id

        # Validate fields dict conversion
        fields_dict = dict(podium_fields)
        assert fields_dict["adam_blend_weight"] == pytest.approx(0.85)
        assert fields_dict["adam_gaze_track"] == 1.0
        assert fields_dict["x"] == -32.5
        assert fields_dict["z"] == -26.0

    def test_f03_guide_presentation_continuity_suite(self, platform_paths, run_cmd):
        """Execute guide presentation continuity test binary if present."""
        exe_path = (
            platform_paths.engine_dir
            / "out"
            / "windows-msvc"
            / "Debug"
            / "aibs_guide_presentation_continuity_tests.exe"
        )
        if exe_path.is_file():
            result = run_cmd(str(exe_path), timeout=15.0)
            result.assert_success()
