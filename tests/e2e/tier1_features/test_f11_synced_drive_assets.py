"""Tier 1 Feature Coverage Tests: Feature 11 - Synced Drive Assets 177 Files.

Tests disk presence, directory hierarchy across 7 categories and 31 subdirectories,
exact 177 file count, exactly 3 zero-byte files, inventory JSON consistency,
and 0 I/O errors across all files.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure tests/e2e root is on sys.path
E2E_ROOT = Path(__file__).resolve().parent.parent
if str(E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_ROOT))

import pytest
from conftest import PlatformPaths


EXPECTED_CATEGORIES = [
    "01_Engineering_Backups",
    "02_Memoirs_Manuscripts",
    "03_Finance_Trading",
    "04_Real_Estate",
    "05_Music_Audio",
    "06_Health_Recovery",
    "07_Legal_Credentials",
]

EXPECTED_ZERO_BYTE_FILES = {
    "Red Line No More.md",
    "Sean My Brother Who Never Leaves.md",
    "50-State Apex Chamber Database & Executive Roster.csv",
}


@pytest.mark.tier1
@pytest.mark.feature_11
@pytest.mark.feature(11)
class TestF11SyncedDriveAssets:
    """Test suite for Feature 11: Synced Drive Assets 177 Files."""

    @pytest.fixture(scope="class")
    def asset_inventory(self, platform_paths: PlatformPaths) -> dict:
        """Scan synced_drive_assets on disk and return aggregated counts and lists."""
        assets_dir = platform_paths.synced_drive_assets_dir
        assert assets_dir.exists(), f"synced_drive_assets directory missing: {assets_dir}"

        files_found = []
        categories = set()
        subdirectories = set()
        zero_byte_files = []

        for root, dirs, files in os.walk(assets_dir):
            rel = os.path.relpath(root, assets_dir)
            if rel == ".":
                continue
            parts = rel.split(os.sep)
            categories.add(parts[0])
            if len(parts) >= 2:
                subdirectories.add(parts[1])

            for f in files:
                p = Path(root) / f
                sz = p.stat().st_size
                files_found.append((p, sz))
                if sz == 0:
                    zero_byte_files.append(f)

        return {
            "files": files_found,
            "categories": categories,
            "subdirectories": subdirectories,
            "zero_byte_files": zero_byte_files,
        }

    def test_f11_directory_structure_exists(self, platform_paths: PlatformPaths) -> None:
        """Verify synced_drive_assets directory exists and is a directory."""
        assert platform_paths.synced_drive_assets_dir.is_dir(), (
            f"Directory does not exist: {platform_paths.synced_drive_assets_dir}"
        )

    def test_f11_exact_177_files_count(self, asset_inventory: dict) -> None:
        """Verify exactly 177 regular files exist across the directory tree."""
        file_count = len(asset_inventory["files"])
        assert file_count == 177, f"Expected exactly 177 files on disk, found {file_count}"

    def test_f11_exact_seven_categories_present(self, asset_inventory: dict) -> None:
        """Verify exactly the 7 expected categories are present."""
        categories = asset_inventory["categories"]
        assert len(categories) == 7, f"Expected 7 categories, found {len(categories)}"
        assert set(EXPECTED_CATEGORIES) == categories, f"Categories mismatch: {categories}"

    def test_f11_exact_thirty_one_subdirectories(self, asset_inventory: dict) -> None:
        """Verify exactly 31 distinct subdirectories exist under the 7 categories."""
        subdirs = asset_inventory["subdirectories"]
        assert len(subdirs) == 31, f"Expected 31 subdirectories, found {len(subdirs)}"

    def test_f11_exact_three_zero_byte_files(self, asset_inventory: dict) -> None:
        """Verify exactly 3 files are zero-byte and match expected filenames."""
        zb_files = asset_inventory["zero_byte_files"]
        assert len(zb_files) == 3, f"Expected 3 zero-byte files, found {len(zb_files)}: {zb_files}"
        assert set(zb_files) == EXPECTED_ZERO_BYTE_FILES, (
            f"Zero-byte filenames mismatch: {set(zb_files)} != {EXPECTED_ZERO_BYTE_FILES}"
        )

    def test_f11_inventory_json_parity(self, platform_paths: PlatformPaths) -> None:
        """Verify docs/scattered_drive_files_inventory.json contains 31 directory entries."""
        inv_path = platform_paths.docs_dir / "scattered_drive_files_inventory.json"
        assert inv_path.exists(), f"Inventory JSON missing: {inv_path}"
        with open(inv_path, "r", encoding="utf-8") as f:
            inv = json.load(f)
        assert len(inv) == 31, f"Expected 31 inventory entries, found {len(inv)}"

    def test_f11_all_files_readable_zero_io_errors(self, asset_inventory: dict) -> None:
        """Verify all 177 files can be opened and read without I/O exceptions."""
        io_errors = []
        for file_path, sz in asset_inventory["files"]:
            try:
                with open(file_path, "rb") as f:
                    _ = f.read(min(sz, 4096))
            except Exception as e:
                io_errors.append((str(file_path), str(e)))

        assert len(io_errors) == 0, f"Encountered {len(io_errors)} I/O errors reading assets: {io_errors}"
