"""
scan_and_ingest_root.py — AI-BS Root Folder Ingestion Engine
Scans C:\AI-BS for newly created or modified documentation, scripts, notes,
and manuals, then ingests them into ChromaDB Vector Memory and SQLite Vault for LLM retrieval.
"""

import os
import sys
import glob
import time
import json
import hashlib
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

STATE_FILE = os.path.join(_backend_dir, "root_ingest_state.json")
MANIFEST_FILE = os.path.join(_root_dir, "ingest_manifest.json")
VAULT_DB_PATH = os.path.join(_backend_dir, "database", "stehouwer_vault.db")

CHROMA_PATHS = [
    r"E:\AI_BS_Resources\ChromaDB",
    os.path.join(_root_dir, "chroma_db")
]

INCLUDE_EXTENSIONS = {
    ".md", ".txt", ".py", ".json", ".sql", ".bat", ".ps1", ".yml", ".yaml", ".jsx", ".js"
}

IGNORE_DIRS = {
    "node_modules", ".git", ".venv", "venv", "env", "dist", "build",
    "android", "ComfyUI", "pyppeteer_env", "__pycache__", ".gradle",
    "MP4 medial screen recordings", "Audio Downloads", "Screen Shots",
    "ScreenShots", "ScreenVideoSnipping", "EXE", "InstallerEXE's",
    "temp_unzip", ".ide_audit_logs", ".pytest_cache"
}

IGNORE_FILES = {
    "package-lock.json", "active_agent_transcript.jsonl", "trainer_daemon_logs.jsonl",
    "symbol_graph.json", "py_health_audit.json", "symbol_graph.json"
}

MAX_FILE_SIZE = 500 * 1024  # 500 KB limit per file to avoid giant bundles

def get_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    chunks = []
    start = 0
    clean_text = text.strip()
    while start < len(clean_text):
        end = min(start + chunk_size, len(clean_text))
        chunk = clean_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def run_root_scan_and_ingest(force_all: bool = False) -> Dict[str, Any]:
    print("=" * 60)
    print("  AI-BS ROOT FOLDER SCAN & LLM INGESTION ENGINE")
    print(f"  Scanning Directory: {_root_dir}")
    print("=" * 60)
    start_time = time.time()

    # Load prior state
    prior_state = {}
    if os.path.exists(STATE_FILE) and not force_all:
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                prior_state = json.load(f)
        except Exception:
            prior_state = {}

    # Discover candidate files in root and top-level directories
    candidate_files = []
    
    # 1. Root level files directly in C:\AI-BS
    try:
        for item in os.listdir(_root_dir):
            fp = os.path.join(_root_dir, item)
            if os.path.isfile(fp):
                ext = os.path.splitext(item)[1].lower()
                if ext in INCLUDE_EXTENSIONS and item not in IGNORE_FILES:
                    try:
                        if os.path.getsize(fp) <= MAX_FILE_SIZE:
                            candidate_files.append(fp)
                    except Exception:
                        pass
    except Exception as e:
        print(f"[!] Error listing root: {e}")

    # 2. Key documentation and knowledge subfolders
    subfolders_to_scan = [
        "docs", "summaries", "Agent_Handoff_Summaries", 
        "Agent_Implementation_Plans_History", "Agent_Tasks_History",
        "MASTER_KNOWLEDGE_VAULT", "Heuristics"
    ]
    for sub in subfolders_to_scan:
        sub_path = os.path.join(_root_dir, sub)
        if os.path.exists(sub_path):
            for root, dirs, files in os.walk(sub_path):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in INCLUDE_EXTENSIONS and file not in IGNORE_FILES:
                        fp = os.path.join(root, file)
                        try:
                            if os.path.getsize(fp) <= MAX_FILE_SIZE:
                                candidate_files.append(fp)
                        except Exception:
                            pass

    print(f"[*] Found {len(candidate_files)} candidate documentation & code files.")

    # Filter for new or modified files
    files_to_ingest = []
    current_hashes = {}
    for fp in candidate_files:
        fhash = get_file_hash(fp)
        current_hashes[fp] = fhash
        if force_all or fp not in prior_state or prior_state[fp] != fhash:
            files_to_ingest.append(fp)

    print(f"[*] Identified {len(files_to_ingest)} new or modified files requiring ingestion.")

    if not files_to_ingest:
        print("[+] Root directory is already fully synchronized with LLM memory.")
        return {
            "status": "success",
            "message": "Root directory already up to date.",
            "total_files_scanned": len(candidate_files),
            "files_ingested": 0,
            "chunks_added": 0,
            "elapsed_sec": round(time.time() - start_time, 2)
        }

    # Setup ChromaDB collections across available Chroma paths
    chroma_clients = []
    if CHROMA_AVAILABLE:
        for cpath in CHROMA_PATHS:
            if os.path.exists(os.path.dirname(cpath)):
                os.makedirs(cpath, exist_ok=True)
                try:
                    c = chromadb.PersistentClient(path=cpath)
                    chroma_clients.append(c)
                except Exception as ex:
                    print(f"[-] Notice initializing Chroma at {cpath}: {ex}")

    # Setup SQLite Vault DB
    os.makedirs(os.path.dirname(VAULT_DB_PATH), exist_ok=True)
    vault_conn = None
    try:
        vault_conn = sqlite3.connect(VAULT_DB_PATH)
        vault_conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                collection TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        vault_conn.commit()
    except Exception as e:
        print(f"[-] SQLite vault connection notice: {e}")

    total_chunks_added = 0
    ingested_list = []

    for idx, fp in enumerate(files_to_ingest):
        fname = os.path.basename(fp)
        rel_path = os.path.relpath(fp, _root_dir)
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"[-] Skipped {fname}: {e}")
            continue

        if not content.strip():
            continue

        chunks = chunk_text(content)
        if not chunks:
            continue

        # Ingest chunks into ChromaDB
        for client in chroma_clients:
            try:
                col = client.get_or_create_collection(name="rag_root_knowledge")
                docs = []
                metas = []
                ids = []
                for c_idx, chunk in enumerate(chunks):
                    chunk_id = f"root_{hashlib.md5(fp.encode()).hexdigest()[:8]}_{c_idx}"
                    docs.append(chunk)
                    metas.append({
                        "source": rel_path,
                        "filename": fname,
                        "chunk_idx": c_idx,
                        "ingested_at": datetime.now().isoformat()
                    })
                    ids.append(chunk_id)

                if docs:
                    col.upsert(documents=docs, metadatas=metas, ids=ids)
            except Exception as ce:
                pass

        # Ingest summary into SQLite Vault
        if vault_conn:
            try:
                summary_snippet = content[:2000]
                vault_conn.execute(
                    "INSERT INTO vault_items (title, content, collection, tags) VALUES (?, ?, ?, ?);",
                    (f"Root Doc: {rel_path}", summary_snippet, "rag_root_knowledge", "root_scan,llm_context")
                )
                vault_conn.commit()
            except Exception:
                pass

        total_chunks_added += len(chunks)
        ingested_list.append({"file": rel_path, "size": len(content), "chunks": len(chunks)})
        prior_state[fp] = current_hashes[fp]

        if (idx + 1) % 15 == 0 or (idx + 1) == len(files_to_ingest):
            print(f"  [{idx+1}/{len(files_to_ingest)}] Ingested {fname} ({len(chunks)} chunks)")

    if vault_conn:
        try:
            vault_conn.close()
        except Exception:
            pass

    # Save state
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as sf:
            json.dump(prior_state, sf, indent=2)
    except Exception as e:
        print(f"[!] Warning: failed to save ingest state: {e}")

    # Update Manifest
    try:
        manifest_data = {}
        if os.path.exists(MANIFEST_FILE):
            try:
                with open(MANIFEST_FILE, "r", encoding="utf-8") as mf:
                    manifest_data = json.load(mf)
            except Exception:
                manifest_data = {}

        manifest_data["last_root_scan"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        manifest_data["total_root_docs_indexed"] = len(prior_state)
        manifest_data["recent_root_ingested"] = ingested_list[-25:]

        with open(MANIFEST_FILE, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, indent=2)
    except Exception as e:
        print(f"[!] Warning: failed to update manifest: {e}")

    elapsed = round(time.time() - start_time, 2)
    print("=" * 60)
    print(f"  INGESTION COMPLETE IN {elapsed}s")
    print(f"  Files Ingested: {len(files_to_ingest)} | Total Chunks Created: {total_chunks_added}")
    print("=" * 60)

    return {
        "status": "success",
        "total_files_scanned": len(candidate_files),
        "files_ingested": len(files_to_ingest),
        "chunks_added": total_chunks_added,
        "elapsed_sec": elapsed,
        "ingested_files": [item["file"] for item in ingested_list]
    }

if __name__ == "__main__":
    force = "--force" in sys.argv
    run_root_scan_and_ingest(force_all=force)
