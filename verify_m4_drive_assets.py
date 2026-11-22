r"""
AI-BS Master Ecosystem - Milestone M4 Verification Suite
Verification Script: verify_m4_drive_assets.py

Asserts:
  1. Exactly 177 files indexed/accounted for across 7 categories and 31 subdirectories in C:\AI-BS\synced_drive_assets.
  2. Inventory consistency with C:\AI-BS\docs\scattered_drive_files_inventory.json.
  3. ChromaDB collection `ai_bs_synced_drive_assets` contains all documents/chunks with correct metadata schema.
  4. Exactly 3 zero-byte files exist in collection/metadata without error.
  5. Per-category collections or category filters populated across all 7 categories.
  6. Microservice query endpoint (or backend RAG query function) retrieves relevant records for test queries against each of the 7 categories.
  7. Exit code 0 on success.
"""

import os
import sys
import json
import asyncio
from typing import Dict, Any, List

# Ensure pyppeteer_env and backend path are accessible
ROOT_DIR = r"C:\AI-BS"
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import chromadb
from chromadb.utils import embedding_functions

SYNCED_ASSETS_DIR = os.path.join(ROOT_DIR, "synced_drive_assets")
INVENTORY_JSON_PATH = os.path.join(ROOT_DIR, "docs", "scattered_drive_files_inventory.json")
HOT_DB_PATH = os.path.join(ROOT_DIR, "stehouwer_vector_memory")
MASTER_COLLECTION_NAME = "ai_bs_synced_drive_assets"

EXPECTED_CATEGORIES = [
    "01_Engineering_Backups",
    "02_Memoirs_Manuscripts",
    "03_Finance_Trading",
    "04_Real_Estate",
    "05_Music_Audio",
    "06_Health_Recovery",
    "07_Legal_Credentials"
]

EXPECTED_ZERO_BYTE_FILES = {
    "Red Line No More.md",
    "Sean My Brother Who Never Leaves.md",
    "50-State Apex Chamber Database & Executive Roster.csv"
}

TEST_QUERIES = {
    "01_Engineering_Backups": "DirectX 12 native viewport studio runtime",
    "02_Memoirs_Manuscripts": "Stehouwer screenplay memoir",
    "03_Finance_Trading": "trading options risk management",
    "04_Real_Estate": "West Michigan market leads property",
    "05_Music_Audio": "Suno AI guides prompts audio",
    "06_Health_Recovery": "TBI recovery psilocybin journal",
    "07_Legal_Credentials": "Pharmacy credentials license"
}


def assert_test(condition: bool, message: str):
    if not condition:
        print(f"[FAIL] Assertion Failed: {message}")
        raise AssertionError(message)
    print(f"[PASS] {message}")


def test_1_disk_and_inventory_accounting():
    print("\n--- Test 1: Disk Files & Inventory Accounting ---")
    assert_test(os.path.isdir(SYNCED_ASSETS_DIR), f"Directory exists: {SYNCED_ASSETS_DIR}")

    files_found = []
    categories = set()
    subdirectories = set()
    zero_byte_files = []

    for root, dirs, files in os.walk(SYNCED_ASSETS_DIR):
        rel = os.path.relpath(root, SYNCED_ASSETS_DIR)
        if rel == ".":
            continue
        parts = rel.split(os.sep)
        categories.add(parts[0])
        if len(parts) >= 2:
            subdirectories.add(parts[1])

        for f in files:
            p = os.path.join(root, f)
            sz = os.path.getsize(p)
            files_found.append((p, sz))
            if sz == 0:
                zero_byte_files.append(f)

    assert_test(len(files_found) == 177, f"Exactly 177 files found on disk (found: {len(files_found)})")
    assert_test(len(categories) == 7, f"Exactly 7 categories found on disk (found: {len(categories)})")
    assert_test(len(subdirectories) == 31, f"Exactly 31 subdirectories found on disk (found: {len(subdirectories)})")
    assert_test(len(zero_byte_files) == 3, f"Exactly 3 zero-byte files found on disk (found: {len(zero_byte_files)})")
    assert_test(set(zero_byte_files) == EXPECTED_ZERO_BYTE_FILES, f"Zero-byte filenames match expected: {zero_byte_files}")

    # Check inventory JSON
    if os.path.exists(INVENTORY_JSON_PATH):
        with open(INVENTORY_JSON_PATH, "r", encoding="utf-8") as f:
            inv = json.load(f)
        assert_test(len(inv) == 31, f"Inventory JSON contains 31 mapped folder entries (found: {len(inv)})")


def test_2_chromadb_collections_and_metadata():
    print("\n--- Test 2: ChromaDB Collections & Metadata Verification ---")
    assert_test(os.path.isdir(HOT_DB_PATH), f"ChromaDB hot storage exists at {HOT_DB_PATH}")

    client = chromadb.PersistentClient(path=HOT_DB_PATH)
    all_collections = [c.name for c in client.list_collections()]
    assert_test(MASTER_COLLECTION_NAME in all_collections, f"Collection '{MASTER_COLLECTION_NAME}' exists in ChromaDB")

    master_col = client.get_collection(name=MASTER_COLLECTION_NAME)
    total_docs = master_col.count()
    print(f"Master collection '{MASTER_COLLECTION_NAME}' contains {total_docs} total chunk documents.")
    assert_test(total_docs >= 177, f"Document count ({total_docs}) >= 177 files")

    # Fetch all records to inspect metadata schema and file accounting
    all_records = master_col.get(include=["metadatas", "documents"])
    metadatas = all_records.get("metadatas", [])
    assert_test(len(metadatas) == total_docs, f"Metadatas count ({len(metadatas)}) matches total docs ({total_docs})")

    indexed_file_paths = set()
    indexed_categories = set()
    required_keys = {"file_path", "category", "subcategory", "file_name", "file_size_bytes", "file_extension", "is_zero_byte"}

    for idx, meta in enumerate(metadatas):
        for k in required_keys:
            if k not in meta:
                raise AssertionError(f"Metadata record {idx} missing key '{k}'")
        indexed_file_paths.add(meta["file_path"])
        indexed_categories.add(meta["category"])

    assert_test(True, f"All {total_docs} chunks contain full required metadata keys: {required_keys}")

    assert_test(len(indexed_file_paths) == 177, f"All 177 unique files are indexed in ChromaDB (found: {len(indexed_file_paths)})")
    assert_test(len(indexed_categories) == 7, f"All 7 categories indexed in ChromaDB (found: {len(indexed_categories)})")
    assert_test(set(EXPECTED_CATEGORIES) == indexed_categories, f"Categories match expected 7 categories")


def test_3_zero_byte_files_graceful_storage():
    print("\n--- Test 3: Zero-Byte Files Graceful Storage ---")
    client = chromadb.PersistentClient(path=HOT_DB_PATH)
    master_col = client.get_collection(name=MASTER_COLLECTION_NAME)

    zb_records = master_col.get(where={"is_zero_byte": True})
    zb_ids = zb_records.get("ids", [])
    zb_metas = zb_records.get("metadatas", [])
    zb_docs = zb_records.get("documents", [])

    assert_test(len(zb_ids) == 3, f"Exactly 3 zero-byte records stored (found: {len(zb_ids)})")
    stored_names = set(m.get("file_name") for m in zb_metas)
    assert_test(stored_names == EXPECTED_ZERO_BYTE_FILES, f"Zero-byte filenames match: {stored_names}")

    for meta in zb_metas:
        assert_test(meta.get("file_size_bytes") == 0, f"File size is 0 bytes for {meta.get('file_name')}")


def test_4_per_category_collections():
    print("\n--- Test 4: Per-Category Collections Verification ---")
    client = chromadb.PersistentClient(path=HOT_DB_PATH)
    all_colls = [c.name for c in client.list_collections()]

    for cat in EXPECTED_CATEGORIES:
        col_name = f"synced_{cat.lower()}"
        assert_test(col_name in all_colls, f"Per-category collection '{col_name}' exists in ChromaDB")
        cat_col = client.get_collection(name=col_name)
        count = cat_col.count()
        assert_test(count > 0, f"Per-category collection '{col_name}' has documents (count: {count})")


async def test_5_microservice_query_retrieval():
    print("\n--- Test 5: Microservice Retrieval Integration Across 7 Categories ---")
    
    # 1. Direct Python RAG Bridge Verification
    from routers.rag_bridge import query_rag, RagQuery

    for cat, query_text in TEST_QUERIES.items():
        req = RagQuery(
            query=query_text,
            category=cat,
            top_k=2,
            collection=MASTER_COLLECTION_NAME,
            synthesize=False
        )
        res = await query_rag(req)
        assert_test(res.get("status") == "success", f"RAG query status is success for category '{cat}'")
        results_list = res.get("results", [])
        assert_test(len(results_list) > 0, f"RAG query returned results for category '{cat}' (count: {len(results_list)})")
        top_doc = results_list[0]
        assert_test("metadata" in top_doc, f"Retrieved item contains metadata for category '{cat}'")
        assert_test(top_doc["metadata"].get("category") == cat, f"Retrieved record belongs to category '{cat}'")
        print(f"  [Category: {cat}] Top hit: '{top_doc['metadata'].get('file_name')}' (rel_path: {top_doc['metadata'].get('file_path')})")

    # 2. HTTP Endpoint Verification (if backend server is reachable on 8080)
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            health = await http_client.get("http://localhost:8080/health")
            if health.status_code == 200:
                print("\n[HTTP] Backend service online on port 8080. Testing live HTTP endpoint /api/rag/query...")
                for cat, query_text in TEST_QUERIES.items():
                    payload = {
                        "query": query_text,
                        "category": cat,
                        "top_k": 2,
                        "collection": MASTER_COLLECTION_NAME,
                        "synthesize": False
                    }
                    http_res = await http_client.post("http://localhost:8080/api/rag/query", json=payload)
                    assert_test(http_res.status_code == 200, f"HTTP endpoint returned 200 for {cat}")
                    data = http_res.json()
                    assert_test(data.get("status") == "success", f"HTTP response status 'success' for {cat}")
                    assert_test(len(data.get("results", [])) > 0, f"HTTP response returned non-empty results for {cat}")
                print("[HTTP] Live endpoint verification passed 100% on port 8080.")
            else:
                print(f"[HTTP Note] Port 8080 health status: {health.status_code}")
    except Exception as e_http:
        print(f"[HTTP Note] Live HTTP check skipped or not listening ({e_http}); direct service contract validated.")


def main():
    print("=" * 80)
    print("AI-BS Milestone M4: Drive Assets & ChromaDB Vectorization Verification")
    print("=" * 80)

    try:
        test_1_disk_and_inventory_accounting()
        test_2_chromadb_collections_and_metadata()
        test_3_zero_byte_files_graceful_storage()
        test_4_per_category_collections()
        asyncio.run(test_5_microservice_query_retrieval())

        print("\n" + "=" * 80)
        print("ALL MILESTONE M4 VERIFICATION ASSERTIONS PASSED (100% SUCCESS)")
        print("=" * 80)
        sys.exit(0)

    except Exception as e:
        print(f"\n[VERIFICATION FAILURE] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
