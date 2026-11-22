"""Tier 1 Feature Coverage Tests: Feature 12 - ChromaDB Vector Ingestion.

Tests document ingestion, chunking, vector embedding, and insertion of all 177 files
into master collection `ai_bs_synced_drive_assets` and per-category collections
without data loss.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure tests/e2e root is on sys.path
E2E_ROOT = Path(__file__).resolve().parent.parent
if str(E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_ROOT))

import pytest
from conftest import PlatformPaths, SubprocessRunner


EXPECTED_CATEGORIES = [
    "01_Engineering_Backups",
    "02_Memoirs_Manuscripts",
    "03_Finance_Trading",
    "04_Real_Estate",
    "05_Music_Audio",
    "06_Health_Recovery",
    "07_Legal_Credentials",
]


@pytest.mark.tier1
@pytest.mark.feature_12
@pytest.mark.feature(12)
class TestF12ChromaDBVectorIngestion:
    """Test suite for Feature 12: ChromaDB Vector Ingestion."""

    @pytest.fixture(scope="class")
    def chromadb_state(self, platform_paths: PlatformPaths, python_exe: str) -> dict:
        """Inspect persistent ChromaDB storage and extract collection statistics."""
        hot_db_path = platform_paths.base_dir / "stehouwer_vector_memory"
        assert hot_db_path.exists(), f"ChromaDB directory missing: {hot_db_path}"

        inspect_script = f"""
import json, chromadb
client = chromadb.PersistentClient(path=r'{hot_db_path}')
collections = [c.name for c in client.list_collections()]
master = client.get_collection('ai_bs_synced_drive_assets')
recs = master.get(include=['metadatas'])
metas = recs.get('metadatas', [])

unique_paths = set(m.get('file_path') for m in metas if 'file_path' in m)
categories = set(m.get('category') for m in metas if 'category' in m)

# Required keys check
req_keys = ['file_path', 'category', 'subcategory', 'file_name', 'file_size_bytes', 'file_extension', 'is_zero_byte']
all_keys_valid = all(all(k in m for k in req_keys) for m in metas[:50])

# Per-category counts
per_cat_counts = {{}}
for cat in {EXPECTED_CATEGORIES!r}:
    col_name = f'synced_{{cat.lower()}}'
    if col_name in collections:
        per_cat_counts[col_name] = client.get_collection(col_name).count()

print(json.dumps({{
    'collections': collections,
    'total_docs': master.count(),
    'unique_paths_count': len(unique_paths),
    'categories': list(categories),
    'all_keys_valid': all_keys_valid,
    'sample_metas_count': len(metas),
    'per_cat_counts': per_cat_counts
}}))
"""
        runner = SubprocessRunner(default_cwd=platform_paths.base_dir, default_timeout=30.0)
        res = runner.run([python_exe, "-c", inspect_script])
        res.assert_success(f"ChromaDB inspection query failed: {res.stderr}")
        return json.loads(res.stdout.strip().splitlines()[-1])

    def test_f12_chromadb_storage_directory_exists(self, platform_paths: PlatformPaths) -> None:
        """Verify stehouwer_vector_memory and chroma.sqlite3 exist on disk."""
        hot_db = platform_paths.base_dir / "stehouwer_vector_memory"
        assert hot_db.is_dir(), f"ChromaDB directory does not exist: {hot_db}"
        sqlite_file = hot_db / "chroma.sqlite3"
        assert sqlite_file.is_file(), f"ChromaDB SQLite file missing: {sqlite_file}"
        assert sqlite_file.stat().st_size > 0, "ChromaDB SQLite file is 0 bytes"

    def test_f12_master_collection_exists(self, chromadb_state: dict) -> None:
        """Verify master collection 'ai_bs_synced_drive_assets' exists in ChromaDB."""
        collections = chromadb_state["collections"]
        assert "ai_bs_synced_drive_assets" in collections, (
            f"Master collection 'ai_bs_synced_drive_assets' not in collections: {collections}"
        )

    def test_f12_master_collection_chunk_count_gte_177(self, chromadb_state: dict) -> None:
        """Verify master collection document/chunk count is >= 177."""
        total_docs = chromadb_state["total_docs"]
        assert total_docs >= 177, f"Master document count ({total_docs}) is less than 177"

    def test_f12_all_177_unique_files_indexed(self, chromadb_state: dict) -> None:
        """Verify exactly 177 unique file paths are indexed in ChromaDB."""
        unique_paths = chromadb_state["unique_paths_count"]
        assert unique_paths == 177, f"Expected 177 unique files indexed, found {unique_paths}"

    def test_f12_metadata_schema_contract(self, chromadb_state: dict) -> None:
        """Verify metadata conforms to schema (file_path, category, subcategory, file_name, file_size_bytes, etc.)."""
        assert chromadb_state["all_keys_valid"] is True, "Metadata schema keys validation failed"

    def test_f12_all_seven_categories_represented(self, chromadb_state: dict) -> None:
        """Verify all 7 canonical categories are indexed in ChromaDB."""
        indexed_cats = set(chromadb_state["categories"])
        assert set(EXPECTED_CATEGORIES) == indexed_cats, (
            f"Categories mismatch: {indexed_cats} != {set(EXPECTED_CATEGORIES)}"
        )

    def test_f12_per_category_collections_populated(self, chromadb_state: dict) -> None:
        """Verify per-category collections exist and each has count > 0."""
        per_cat = chromadb_state["per_cat_counts"]
        for cat in EXPECTED_CATEGORIES:
            col_name = f"synced_{cat.lower()}"
            assert col_name in per_cat, f"Per-category collection '{col_name}' missing"
            assert per_cat[col_name] > 0, f"Collection '{col_name}' is empty (0 records)"
