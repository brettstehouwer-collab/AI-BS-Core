"""Track 4: Asset Integrity Verification Suite.

Asserts 0 modifications, 0 additions, and 0 deletions across all 177 files
in C:\\AI-BS\\synced_drive_assets\\ against the frozen SHA-256 manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest


ASSETS_ROOT = Path("C:/AI-BS/synced_drive_assets")
MANIFEST_PATH = Path("C:/AI-BS/docs/synced_assets_sha256_manifest.json")

EXPECTED_CATEGORIES = {
    "01_Engineering_Backups",
    "02_Memoirs_Manuscripts",
    "03_Finance_Trading",
    "04_Real_Estate",
    "05_Music_Audio",
    "06_Health_Recovery",
    "07_Legal_Credentials",
}


def test_manifest_existence_and_schema():
    """Verify manifest file exists and matches specification schema."""
    assert MANIFEST_PATH.is_file(), f"Manifest file missing: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("schema_version") == 1
    assert manifest.get("total_files") == 177
    assert set(manifest.get("categories", [])) == EXPECTED_CATEGORIES
    assert len(manifest.get("files", {})) == 177


def test_asset_count_and_zero_additions_or_deletions():
    """Verify exactly 177 files on disk with zero added or removed assets."""
    assert ASSETS_ROOT.is_dir(), f"Assets root missing: {ASSETS_ROOT}"
    disk_files = sorted([f for f in ASSETS_ROOT.rglob("*") if f.is_file()])
    assert len(disk_files) == 177, f"Expected 177 files on disk, found {len(disk_files)}"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest_paths = set(manifest["files"].keys())
    disk_rel_paths = {f.relative_to(ASSETS_ROOT).as_posix() for f in disk_files}

    added = disk_rel_paths - manifest_paths
    deleted = manifest_paths - disk_rel_paths
    assert len(added) == 0, f"Detected unexpected additions in synced_drive_assets: {added}"
    assert len(deleted) == 0, f"Detected missing files in synced_drive_assets: {deleted}"


def test_asset_sha256_immutability():
    """Verify all 177 files match exact SHA-256 and byte sizes (0 modifications)."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    mismatches = []
    for rel_path, expected in manifest["files"].items():
        disk_file = ASSETS_ROOT / rel_path
        if not disk_file.is_file():
            mismatches.append(f"Missing file: {rel_path}")
            continue

        raw = disk_file.read_bytes()
        actual_size = len(raw)
        actual_hash = hashlib.sha256(raw).hexdigest()

        if actual_size != expected["size_bytes"] or actual_hash != expected["sha256"]:
            mismatches.append(
                f"{rel_path}: size {actual_size} (exp {expected['size_bytes']}), "
                f"sha256 {actual_hash[:8]}... (exp {expected['sha256'][:8]}...)"
            )

    assert len(mismatches) == 0, f"File integrity mismatches detected:\n" + "\n".join(mismatches)


def test_category_structure_and_no_unwanted_artifacts():
    """Verify clean directory structure with no temporary, log, or swap files."""
    for cat in EXPECTED_CATEGORIES:
        cat_dir = ASSETS_ROOT / cat
        assert cat_dir.is_dir(), f"Expected category directory missing: {cat_dir}"

    unwanted_extensions = {".tmp", ".temp", ".log", ".swp", ".bak", ".pyc"}
    unwanted_files = [
        f.as_posix()
        for f in ASSETS_ROOT.rglob("*")
        if f.is_file() and f.suffix.lower() in unwanted_extensions
    ]
    assert len(unwanted_files) == 0, f"Found unwanted temporary files: {unwanted_files}"
