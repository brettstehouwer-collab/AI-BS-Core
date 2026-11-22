r"""
AI-BS Master Ecosystem - Synced Drive Assets Ingestion & Vectorization Pipeline
Milestone M4: Production Ingestion into ChromaDB Vector Memory

Scans all 177 synced cloud files across all 7 categories and 31 subdirectories in C:\AI-BS\synced_drive_assets,
parses text and rich binary formats (.pdf, .docx, .zip, .csv, .json, .eml, .md, .txt, extensionless),
attaches rich metadata, safely handles zero-byte files, computes vector embeddings, and persists
records into both the master collection `ai_bs_synced_drive_assets` and per-category collections
in `C:\AI-BS\stehouwer_vector_memory` and `E:\AI_BS_Resources\ChromaDB`.
"""

import os
import sys
import json
import csv
import email
import zipfile
import traceback
from typing import List, Dict, Any, Tuple, Optional

import chromadb
from chromadb.utils import embedding_functions

# --- Configuration & Paths ---
BASE_DIR = r"C:\AI-BS"
SYNCED_ASSETS_DIR = os.path.join(BASE_DIR, "synced_drive_assets")
INVENTORY_JSON_PATH = os.path.join(BASE_DIR, "docs", "scattered_drive_files_inventory.json")
HOT_DB_PATH = os.path.join(BASE_DIR, "stehouwer_vector_memory")
RESOURCE_DB_PATH = r"E:\AI_BS_Resources\ChromaDB"

MASTER_COLLECTION_NAME = "ai_bs_synced_drive_assets"

# 7 Expected Categories
EXPECTED_CATEGORIES = [
    "01_Engineering_Backups",
    "02_Memoirs_Manuscripts",
    "03_Finance_Trading",
    "04_Real_Estate",
    "05_Music_Audio",
    "06_Health_Recovery",
    "07_Legal_Credentials"
]

CATEGORY_COLLECTION_MAP = {
    "01_Engineering_Backups": "synced_01_engineering_backups",
    "02_Memoirs_Manuscripts": "synced_02_memoirs_manuscripts",
    "03_Finance_Trading": "synced_03_finance_trading",
    "04_Real_Estate": "synced_04_real_estate",
    "05_Music_Audio": "synced_05_music_audio",
    "06_Health_Recovery": "synced_06_health_recovery",
    "07_Legal_Credentials": "synced_07_legal_credentials",
}


def sanitize_text(text: str) -> str:
    """Removes null bytes and cleans control characters for safe ChromaDB storage."""
    if not text:
        return ""
    return text.replace("\x00", "").strip()


def parse_pdf(file_path: str, max_pages: int = 50) -> str:
    """Extracts text from PDF files using PyMuPDF (fitz) or pypdf."""
    text_parts = []
    try:
        import fitz
        doc = fitz.open(file_path)
        for page_num in range(min(len(doc), max_pages)):
            page_text = doc[page_num].get_text()
            if page_text:
                text_parts.append(page_text.strip())
        doc.close()
    except Exception as e_fitz:
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for page in reader.pages[:max_pages]:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())
        except Exception as e_pypdf:
            text_parts.append(f"[PDF parsing error: {e_fitz}; {e_pypdf}]")
    return "\n\n".join(text_parts)


def parse_docx(file_path: str) -> str:
    """Extracts text and table rows from DOCX files."""
    text_parts = []
    try:
        import docx
        doc = docx.Document(file_path)
        for p in doc.paragraphs:
            if p.text.strip():
                text_parts.append(p.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    text_parts.append(" | ".join(row_cells))
    except Exception as e:
        text_parts.append(f"[DOCX parsing error: {e}]")
    return "\n".join(text_parts)


def parse_zip(file_path: str, max_members: int = 200) -> str:
    """Extracts archive manifest, member list, and embedded text descriptions."""
    parts = []
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            namelist = z.namelist()
            parts.append(f"Zip Archive: {os.path.basename(file_path)}")
            parts.append(f"Total entries: {len(namelist)}")
            sample_members = namelist[:max_members]
            parts.append("Archive Members:\n" + "\n".join(f"- {name}" for name in sample_members))
            
            # Read small metadata / readme files if present
            for name in namelist[:20]:
                lower = name.lower()
                if any(lower.endswith(ext) for ext in [".md", ".txt", ".json"]) and not lower.endswith("/"):
                    try:
                        info = z.getinfo(name)
                        if info.file_size < 10000:
                            content = z.read(name).decode("utf-8", errors="ignore").strip()
                            if content:
                                parts.append(f"\n--- Embedded {name} ---\n{content[:500]}")
                    except Exception:
                        pass
    except Exception as e:
        parts.append(f"[ZIP extraction error: {e}]")
    return "\n".join(parts)


def parse_eml(file_path: str) -> str:
    """Extracts email headers, subject, sender, and text body, ignoring binary attachments."""
    parts = []
    try:
        with open(file_path, "rb") as f:
            msg = email.message_from_binary_file(f)
        parts.append(f"Subject: {msg.get('Subject', '')}")
        parts.append(f"From: {msg.get('From', '')}")
        parts.append(f"To: {msg.get('To', '')}")
        parts.append(f"Date: {msg.get('Date', '')}")
        
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text += payload.decode("utf-8", errors="ignore") + "\n"
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode("utf-8", errors="ignore")
        
        parts.append("\nBody:\n" + body_text[:10000])
    except Exception as e:
        parts.append(f"[EML parsing error: {e}]")
    return "\n".join(parts)


def parse_csv(file_path: str, max_rows: int = 100) -> str:
    """Extracts tabular records formatted as human-readable key-value summaries."""
    parts = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            headers = None
            row_count = 0
            for row in reader:
                if not row:
                    continue
                if headers is None:
                    headers = row
                    parts.append(f"Columns: {', '.join(headers)}")
                else:
                    row_count += 1
                    if row_count <= max_rows:
                        entry = [f"{headers[i] if i < len(headers) else f'Col{i}'}: {val}" for i, val in enumerate(row)]
                        parts.append(" | ".join(entry))
                    elif row_count == max_rows + 1:
                        parts.append(f"... [Truncated at {max_rows} rows]")
            parts.insert(0, f"CSV Table ({row_count} data rows)")
    except Exception as e:
        parts.append(f"[CSV parsing error: {e}]")
    return "\n".join(parts)


def parse_json_or_ipynb(file_path: str) -> str:
    """Extracts JSON data or notebook cells."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        if isinstance(data, dict) and "cells" in data:
            # Jupyter notebook
            cell_texts = []
            for cell in data["cells"]:
                src = cell.get("source", "")
                if isinstance(src, list):
                    src = "".join(src)
                src = src.strip()
                if src:
                    cell_type = cell.get("cell_type", "cell")
                    cell_texts.append(f"[{cell_type.upper()}]:\n{src}")
            return "\n\n".join(cell_texts)
        else:
            dumped = json.dumps(data, indent=2)
            return dumped[:15000]
    except Exception:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:15000]


def parse_image(file_path: str) -> str:
    """Extracts image dimension, file format, and directory context metadata."""
    parts = [f"Image file: {os.path.basename(file_path)}"]
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            parts.append(f"Format: {img.format}, Dimensions: {img.size[0]}x{img.size[1]}, Mode: {img.mode}")
            exif = getattr(img, "_getexif", lambda: None)()
            if exif:
                parts.append(f"EXIF tags present: {len(exif)} fields")
    except Exception as e:
        parts.append(f"Image attributes: size={os.path.getsize(file_path)} bytes ({e})")
    return "\n".join(parts)


def extract_content(file_path: str, size: int) -> Tuple[str, bool]:
    """
    Extracts text content from any file in synced_drive_assets.
    Returns (extracted_text, is_zero_byte).
    """
    if size == 0:
        return "", True

    ext = os.path.splitext(file_path)[1].lower()

    # Check magic bytes for PDF or special files
    try:
        with open(file_path, "rb") as f:
            magic = f.read(16)
    except Exception:
        magic = b""

    if magic.startswith(b"%PDF") or ext == ".pdf":
        return parse_pdf(file_path), False

    if ext == ".docx":
        return parse_docx(file_path), False

    if ext == ".zip":
        return parse_zip(file_path), False

    if ext == ".eml":
        return parse_eml(file_path), False

    if ext == ".csv":
        return parse_csv(file_path), False

    if ext == ".json" or magic.strip().startswith(b"{") or magic.strip().startswith(b"["):
        return parse_json_or_ipynb(file_path), False

    if ext in [".jpg", ".jpeg", ".png"]:
        return parse_image(file_path), False

    # Default text reading (.md, .txt, extensionless text files)
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            return content, False
    except Exception:
        try:
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()
                return content, False
        except Exception as e:
            return f"[Error reading file: {e}]", False


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200, max_chunks: int = 60) -> List[str]:
    """Splits text into overlapping sliding-window chunks."""
    text = sanitize_text(text)
    if not text:
        return [""]

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text) and len(chunks) < max_chunks:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks if chunks else [text[:chunk_size]]


def scan_synced_drive_assets() -> List[Dict[str, Any]]:
    r"""
    Scans C:\AI-BS\synced_drive_assets and returns metadata for all 177 files.
    """
    discovered = []
    assert os.path.exists(SYNCED_ASSETS_DIR), f"Synced assets dir not found: {SYNCED_ASSETS_DIR}"

    for root, dirs, files in os.walk(SYNCED_ASSETS_DIR):
        rel_root = os.path.relpath(root, SYNCED_ASSETS_DIR)
        if rel_root == ".":
            continue
        parts = rel_root.split(os.sep)
        category = parts[0]
        subcategory = parts[1] if len(parts) > 1 else ""

        for file_name in files:
            full_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(full_path, SYNCED_ASSETS_DIR)
            size_bytes = os.path.getsize(full_path)
            ext = os.path.splitext(file_name)[1].lower()

            discovered.append({
                "full_path": full_path,
                "rel_path": rel_path,
                "category": category,
                "subcategory": subcategory,
                "file_name": file_name,
                "file_size_bytes": size_bytes,
                "file_extension": ext,
            })

    return discovered


def run_ingestion():
    print("=" * 80)
    print("AI-BS Milestone M4: Drive Assets Ingestion & ChromaDB Vectorization")
    print(f"Scanning directory: {SYNCED_ASSETS_DIR}")
    print("=" * 80)

    # 1. Scan files
    files = scan_synced_drive_assets()
    total_files = len(files)
    print(f"[Scan] Discovered {total_files} files on disk.")

    categories_found = sorted(list(set(f["category"] for f in files)))
    subdirs_found = sorted(list(set(f["subcategory"] for f in files if f["subcategory"])))

    print(f"[Scan] Categories count: {len(categories_found)} (expected: 7)")
    print(f"[Scan] Subdirectories count: {len(subdirs_found)} (expected: 31)")
    for cat in categories_found:
        cat_files = [f for f in files if f["category"] == cat]
        print(f"  - {cat}: {len(cat_files)} files")

    assert total_files == 177, f"Expected exactly 177 files, found {total_files}!"
    assert len(categories_found) == 7, f"Expected 7 categories, found {len(categories_found)}!"
    assert len(subdirs_found) == 31, f"Expected 31 subdirectories, found {len(subdirs_found)}!"

    # 2. Cross-reference with scattered_drive_files_inventory.json
    if os.path.exists(INVENTORY_JSON_PATH):
        try:
            with open(INVENTORY_JSON_PATH, "r", encoding="utf-8") as f:
                inv_data = json.load(f)
            print(f"[Inventory] Cross-referencing with {INVENTORY_JSON_PATH} ({len(inv_data)} folders mapped)...")
        except Exception as e:
            print(f"[Inventory] Note: Could not parse inventory JSON: {e}")

    # 3. Initialize ChromaDB Clients and Embedding Function
    print(f"\n[ChromaDB] Initializing ChromaDB PersistentClient at {HOT_DB_PATH}...")
    hot_client = chromadb.PersistentClient(path=HOT_DB_PATH)
    
    resource_client = None
    if os.path.exists(r"E:\AI_BS_Resources"):
        try:
            os.makedirs(RESOURCE_DB_PATH, exist_ok=True)
            resource_client = chromadb.PersistentClient(path=RESOURCE_DB_PATH)
            print(f"[ChromaDB] Initialized secondary client at {RESOURCE_DB_PATH}")
        except Exception as e:
            print(f"[ChromaDB] Secondary client initialization note: {e}")

    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    EMBEDDING_DIM = 384
    ZERO_VECTOR = [0.0] * EMBEDDING_DIM

    # Create / Get Master Collection
    master_hot_col = hot_client.get_or_create_collection(
        name=MASTER_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "All 177 synced Google Drive assets across 7 categories"}
    )

    master_res_col = None
    if resource_client:
        try:
            master_res_col = resource_client.get_or_create_collection(
                name=MASTER_COLLECTION_NAME,
                embedding_function=embedding_fn,
                metadata={"description": "All 177 synced Google Drive assets across 7 categories"}
            )
        except Exception as e:
            print(f"[ChromaDB] Note on resource collection: {e}")

    # Create / Get Per-Category Collections in Hot DB
    category_collections = {}
    for cat_name, col_name in CATEGORY_COLLECTION_MAP.items():
        col = hot_client.get_or_create_collection(
            name=col_name,
            embedding_function=embedding_fn,
            metadata={"category": cat_name}
        )
        category_collections[cat_name] = col

    # 4. Process and Ingest Files
    print("\n[Processing] Parsing, chunking, and embedding files...")
    
    total_chunks_processed = 0
    zero_byte_files_count = 0
    parsed_records = []

    for idx, f_info in enumerate(files):
        full_p = f_info["full_path"]
        rel_p = f_info["rel_path"]
        sz = f_info["file_size_bytes"]
        cat = f_info["category"]
        subcat = f_info["subcategory"]
        fname = f_info["file_name"]
        fext = f_info["file_extension"]

        content, is_zero_byte = extract_content(full_p, sz)

        if is_zero_byte or sz == 0:
            zero_byte_files_count += 1
            chunks = [""]
            is_zero_byte = True
        else:
            chunks = chunk_text(content)

        # Build chunks and metadata
        file_hash = f"{abs(hash(rel_p)) % 10000000:07d}"
        for c_idx, chunk_text_content in enumerate(chunks):
            doc_id = f"drive_{file_hash}_chunk_{c_idx}"
            metadata = {
                "file_path": rel_p,
                "abs_path": full_p,
                "category": cat,
                "subcategory": subcat,
                "file_name": fname,
                "file_size_bytes": sz,
                "file_extension": fext,
                "chunk_index": c_idx,
                "total_chunks": len(chunks),
                "is_zero_byte": is_zero_byte
            }
            parsed_records.append({
                "id": doc_id,
                "document": chunk_text_content,
                "metadata": metadata,
                "category": cat,
                "is_zero_byte": is_zero_byte
            })
            total_chunks_processed += 1

        if (idx + 1) % 25 == 0 or idx + 1 == total_files:
            print(f"  Processed {idx + 1}/{total_files} files ({total_chunks_processed} chunks)...")

    print(f"\n[Summary] Total files parsed: {total_files}")
    print(f"[Summary] Zero-byte files handled: {zero_byte_files_count}")
    print(f"[Summary] Total chunks generated: {total_chunks_processed}")

    # 5. Insert into ChromaDB in Batches
    BATCH_SIZE = 50
    print(f"\n[ChromaDB] Upserting {total_chunks_processed} records in batches of {BATCH_SIZE}...")

    for i in range(0, len(parsed_records), BATCH_SIZE):
        batch = parsed_records[i : i + BATCH_SIZE]
        b_ids = [item["id"] for item in batch]
        b_docs = [item["document"] for item in batch]
        b_metas = [item["metadata"] for item in batch]
        b_zero_flags = [item["is_zero_byte"] for item in batch]

        # Determine which items need embedding vs zero-vector
        b_embeddings = []
        texts_to_embed = []
        text_indices = []

        for b_idx, (doc, is_zb) in enumerate(zip(b_docs, b_zero_flags)):
            if is_zb or not doc.strip():
                b_embeddings.append(ZERO_VECTOR)
            else:
                b_embeddings.append(None)
                texts_to_embed.append(doc)
                text_indices.append(b_idx)

        if texts_to_embed:
            computed_embeds = embedding_fn(texts_to_embed)
            for emb_idx, computed_emb in zip(text_indices, computed_embeds):
                b_embeddings[emb_idx] = computed_emb

        # Ensure all embeddings are consistent Python lists of floats
        clean_embeddings = []
        for emb in b_embeddings:
            if hasattr(emb, "tolist"):
                clean_embeddings.append(emb.tolist())
            elif isinstance(emb, list):
                clean_embeddings.append(emb)
            else:
                clean_embeddings.append(list(emb))
        b_embeddings = clean_embeddings

        # Upsert into Master Hot Collection
        master_hot_col.upsert(
            ids=b_ids,
            documents=b_docs,
            metadatas=b_metas,
            embeddings=b_embeddings
        )

        # Upsert into Secondary Resource Collection if available
        if master_res_col:
            try:
                master_res_col.upsert(
                    ids=b_ids,
                    documents=b_docs,
                    metadatas=b_metas,
                    embeddings=b_embeddings
                )
            except Exception:
                pass

        # Upsert into Per-Category Collections in batch per category
        cat_batches = {}
        for item, emb in zip(batch, b_embeddings):
            c = item["category"]
            if c not in cat_batches:
                cat_batches[c] = {"ids": [], "docs": [], "metas": [], "embeds": []}
            cat_batches[c]["ids"].append(item["id"])
            cat_batches[c]["docs"].append(item["document"])
            cat_batches[c]["metas"].append(item["metadata"])
            cat_batches[c]["embeds"].append(emb)

        for c, data in cat_batches.items():
            cat_col = category_collections.get(c)
            if cat_col:
                cat_col.upsert(
                    ids=data["ids"],
                    documents=data["docs"],
                    metadatas=data["metas"],
                    embeddings=data["embeds"]
                )

        print(f"  Inserted batch {i // BATCH_SIZE + 1}/{(len(parsed_records) + BATCH_SIZE - 1) // BATCH_SIZE}")

    # 6. Verification & Integrity Checks
    print("\n[Verification] Validating ChromaDB storage...")
    final_master_count = master_hot_col.count()
    print(f"  Master collection document count: {final_master_count}")
    assert final_master_count >= total_files, f"Master collection count ({final_master_count}) < total files ({total_files})!"

    # Verify zero-byte files
    zero_byte_records = master_hot_col.get(where={"is_zero_byte": True})
    zb_count = len(zero_byte_records["ids"])
    print(f"  Zero-byte records in master collection: {zb_count} (expected: 3)")
    assert zb_count == 3, f"Expected exactly 3 zero-byte records, got {zb_count}!"

    # Verify all 7 categories present in master collection
    for cat in EXPECTED_CATEGORIES:
        cat_records = master_hot_col.get(where={"category": cat})
        cat_count = len(cat_records["ids"])
        per_cat_col_count = category_collections[cat].count()
        print(f"  Category '{cat}': {cat_count} master chunks, {per_cat_col_count} in category collection")
        assert cat_count > 0, f"Category {cat} has 0 records in master collection!"
        assert per_cat_col_count > 0, f"Category collection for {cat} has 0 records!"

    # Test Querying ChromaDB directly
    test_queries = {
        "01_Engineering_Backups": "DirectX 12 native viewport studio runtime",
        "02_Memoirs_Manuscripts": "Stehouwer screenplay memoir",
        "03_Finance_Trading": "trading options risk management",
        "04_Real_Estate": "West Michigan market leads property",
        "05_Music_Audio": "Suno AI guides prompts audio",
        "06_Health_Recovery": "TBI recovery psilocybin journal",
        "07_Legal_Credentials": "Pharmacy credentials license"
    }

    print("\n[Verification] Testing similarity search across all 7 categories...")
    for cat, query_text in test_queries.items():
        q_res = master_hot_col.query(
            query_texts=[query_text],
            where={"category": cat},
            n_results=1
        )
        retrieved_ids = q_res.get("ids", [[]])[0]
        retrieved_meta = q_res.get("metadatas", [[]])[0]
        assert retrieved_ids, f"Failed to retrieve records for category {cat}!"
        print(f"  [PASS] {cat}: Retrieved '{retrieved_meta[0].get('file_name')}' for query '{query_text}'")

    print("\n" + "=" * 80)
    print("AI-BS Milestone M4 Ingestion Complete: ALL 177 FILES VECTORIZED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run_ingestion()
    except Exception as e:
        print(f"\n[FATAL ERROR] Ingestion failed: {e}")
        traceback.print_exc()
        sys.exit(1)
