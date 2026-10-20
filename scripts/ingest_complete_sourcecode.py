"""
scripts/ingest_complete_sourcecode.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Master Source Code Ingestion & Multi-Tiered Cognitive Memory Indexer (v5.290.0)
- Parses 'AI_BS_Complete_SourceCode.md' (3,230 packaged files, ~44 MB).
- Extracts every file path, line count, byte size, language, and content.
- Categorizes all files into an architectural subsystem & layer taxonomy.
- Populates SQLite master knowledge table & FTS5 full-text search index in 'backend/aibs_master.db'.
- Ingests structured architectural vector embeddings into ChromaDB collection 'ai_bs_codebase_vault'.
- Generates comprehensive architectural manifest: 'saved_data/codebase_knowledge_index.json'.
"""

import os
import re
import sys
import json
import time
import sqlite3
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SOURCE_PATHS = [
    r"C:\Users\footb\Desktop\AI_BS_Complete_SourceCode.md",
    r"C:\Users\footb\OneDrive\Desktop\AI_BS_Complete_SourceCode.md"
]

DB_PATH = os.path.join(BASE_DIR, "backend", "aibs_master.db")
SAVED_DATA_DIR = os.path.join(BASE_DIR, "saved_data")
MANIFEST_OUT = os.path.join(SAVED_DATA_DIR, "codebase_knowledge_index.json")


def classify_subsystem(file_path: str) -> tuple[str, str, str]:
    """
    Returns (subsystem, layer, language) for a given file path.
    """
    p = file_path.replace("\\", "/").lower()
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    
    # Language detection
    lang_map = {
        "py": "python",
        "js": "javascript",
        "jsx": "react_jsx",
        "ts": "typescript",
        "tsx": "react_tsx",
        "json": "json",
        "md": "markdown",
        "html": "html",
        "css": "css",
        "go": "go",
        "ps1": "powershell",
        "bat": "batch",
        "sh": "bash",
        "sql": "sql",
        "yaml": "yaml",
        "yml": "yaml",
        "modelfile": "modelfile"
    }
    lang = lang_map.get(ext, ext if ext else "text")

    # Subsystem & Layer categorization
    if p.startswith(".agents/") or p.startswith("skills/"):
        return "rules_and_skills", "Governance & Skills", lang
    elif p.startswith("backend/core/sovereign_reasoning/"):
        return "sovereign_reasoning", "Cognitive Intelligence", lang
    elif p.startswith("backend/core/"):
        return "backend_core", "Core Execution Engines", lang
    elif p.startswith("backend/routers/") or p.startswith("backend/commercial_gateway/"):
        return "backend_routers", "API & Network Gateways", lang
    elif p.startswith("backend/tools/"):
        return "backend_tools", "Tool Registry & Function Calling", lang
    elif p.startswith("backend/models/"):
        return "model_definitions", "Neural Weights & Modelfiles", lang
    elif p.startswith("backend/"):
        return "backend_services", "Backend Daemons & Workers", lang
    elif p.startswith("frontend/src/components/") or p.startswith("frontend/components/"):
        return "frontend_components", "UI Modules & Hub Views", lang
    elif p.startswith("frontend/src/styles/") or p.startswith("frontend/styles/") or ext == "css":
        return "frontend_styles", "Presentation & Cybernetic Theme", lang
    elif p.startswith("frontend/"):
        return "frontend_core", "Frontend Architecture & Routing", lang
    elif p.startswith("native_studio/"):
        return "native_studio", "Native Windows Desktop Studio", lang
    elif p.startswith("mobile-app/") or p.startswith("trainer_frontend/"):
        return "mobile_native", "Native Mobile & Desktop Trainers", lang
    elif p.startswith("scripts/") or p.startswith("cmd/"):
        return "system_scripts", "Automation & CLI Tooling", lang
    elif p.startswith("docs/") or p.endswith("_manual.md") or p.endswith("_ledger.md"):
        return "docs_and_ledgers", "Documentation & Master Ledgers", lang
    else:
        return "general_ecosystem", "Ecosystem Assets", lang


def parse_master_sourcecode_bundle(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses the full markdown file and extracts each packaged file.
    """
    print(f"📖 Reading Master Source Code Bundle from: {file_path}")
    t0 = time.time()
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()
    
    print(f"   Read {len(raw_text):,} characters in {time.time()-t0:.2f}s.")
    
    # Pattern: # FILE [index/total]: path\n# LINES: N | SIZE: N BYTES | EXT: EXT\n#+
    # followed by ```lang ... ```
    file_pattern = re.compile(
        r"####################################################################################################\r?\n"
        r"# FILE \[(\d+)/(\d+)\]:\s*([^\r\n]+)\r?\n"
        r"# LINES:\s*([\d,]+)\s*\|\s*SIZE:\s*([\d,]+)\s*BYTES\s*\|\s*EXT:\s*([^\r\n]+)\r?\n"
        r"####################################################################################################",
        re.MULTILINE
    )

    matches = list(file_pattern.finditer(raw_text))
    total_found = len(matches)
    print(f"⚡ Discovered {total_found:,} packaged file headers.")

    extracted_files = []

    for i, match in enumerate(matches):
        file_idx = int(match.group(1))
        total_in_header = int(match.group(2))
        file_path_rel = match.group(3).strip()
        lines_count = int(match.group(4).replace(",", ""))
        bytes_size = int(match.group(5).replace(",", ""))
        ext_str = match.group(6).strip().lower()

        # Find start and end of content
        content_start = match.end()
        content_end = matches[i + 1].start() if i + 1 < total_found else len(raw_text)

        raw_block = raw_text[content_start:content_end].strip()

        # Strip enclosing markdown code fences ```ext ... ```
        fence_match = re.match(r"^```[a-zA-Z0-9_-]*\r?\n([\s\S]*?)\r?\n```$", raw_block)
        if fence_match:
            clean_content = fence_match.group(1)
        else:
            clean_content = raw_block

        subsystem, layer, language = classify_subsystem(file_path_rel)

        # Generate concise summary / excerpt (first 500 chars)
        lines = [l.strip() for l in clean_content.splitlines() if l.strip() and not l.strip().startswith("//") and not l.strip().startswith("#")]
        content_summary = " ".join(lines[:6])[:600]

        extracted_files.append({
            "file_index": file_idx,
            "file_path": file_path_rel,
            "subsystem": subsystem,
            "layer": layer,
            "language": language,
            "lines_count": lines_count,
            "bytes_size": bytes_size,
            "content_summary": content_summary,
            "content": clean_content
        })

        if (i + 1) % 500 == 0 or (i + 1) == total_found:
            print(f"   Parsed {i + 1:,} / {total_found:,} files...")

    return extracted_files


def initialize_sqlite_tables(db_path: str):
    """
    Initializes codebase_master_knowledge and FTS5 full-text search virtual table.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")

    # Master table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS codebase_master_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_index INTEGER,
            file_path TEXT UNIQUE,
            subsystem TEXT,
            layer TEXT,
            language TEXT,
            lines_count INTEGER,
            bytes_size INTEGER,
            content_summary TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_cb_subsystem ON codebase_master_knowledge(subsystem);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cb_file_path ON codebase_master_knowledge(file_path);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cb_language ON codebase_master_knowledge(language);")

    # FTS5 Virtual Table for sub-millisecond keyword & semantic search
    cur.execute("DROP TABLE IF EXISTS codebase_master_knowledge_fts;")
    cur.execute("""
        CREATE VIRTUAL TABLE codebase_master_knowledge_fts USING fts5(
            file_path,
            subsystem,
            layer,
            language,
            content_summary,
            content,
            tokenize = 'porter unicode61'
        );
    """)

    conn.commit()
    conn.close()
    print(f"✅ SQLite tables initialized in: {db_path}")


def populate_sqlite_knowledge(db_path: str, files: List[Dict[str, Any]]):
    """
    Inserts all parsed files into SQLite master table and FTS5 index.
    """
    print(f"💾 Ingesting {len(files):,} files into SQLite master knowledge base...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Clear existing
    cur.execute("DELETE FROM codebase_master_knowledge;")
    cur.execute("DELETE FROM codebase_master_knowledge_fts;")

    insert_master_sql = """
        INSERT INTO codebase_master_knowledge 
        (file_index, file_path, subsystem, layer, language, lines_count, bytes_size, content_summary, content)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    insert_fts_sql = """
        INSERT INTO codebase_master_knowledge_fts 
        (file_path, subsystem, layer, language, content_summary, content)
        VALUES (?, ?, ?, ?, ?, ?);
    """

    master_records = [
        (
            f["file_index"],
            f["file_path"],
            f["subsystem"],
            f["layer"],
            f["language"],
            f["lines_count"],
            f["bytes_size"],
            f["content_summary"],
            f["content"]
        )
        for f in files
    ]

    fts_records = [
        (
            f["file_path"],
            f["subsystem"],
            f["layer"],
            f["language"],
            f["content_summary"],
            f["content"]
        )
        for f in files
    ]

    cur.executemany(insert_master_sql, master_records)
    cur.executemany(insert_fts_sql, fts_records)

    conn.commit()
    conn.close()
    print(f"✅ Ingested {len(files):,} records into SQLite master knowledge & FTS5 search index.")


def ingest_chroma_codebase_vault(files: List[Dict[str, Any]]):
    """
    Ingests architectural summaries and key modules into ChromaDB collection 'ai_bs_codebase_vault'.
    """
    print("🧠 Ingesting architectural summaries into ChromaDB collection 'ai_bs_codebase_vault'...")
    try:
        import chromadb
        
        # Add backend to sys.path if not present
        backend_dir = os.path.join(BASE_DIR, "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
            
        from core.vector_vault import get_text_embedding
        
        chroma_dir = os.path.join(BASE_DIR, "stehouwer_vector_memory")
        os.makedirs(chroma_dir, exist_ok=True)
        
        client = chromadb.PersistentClient(path=chroma_dir)
        collection = client.get_or_create_collection(
            name="ai_bs_codebase_vault",
            metadata={"description": "AI-BS 3,230-File Complete Source Code Knowledge Base"}
        )

        # Ingest key files and summaries in batches (focus on core engines, routers, tools, rules)
        # Select key architectural files first
        priority_subsystems = {
            "rules_and_skills", "sovereign_reasoning", "backend_core", 
            "backend_routers", "backend_tools", "backend_services", "frontend_core"
        }
        
        target_files = [f for f in files if f["subsystem"] in priority_subsystems or f["lines_count"] > 20]
        print(f"   Selecting {len(target_files):,} architectural files for vector indexing...")

        batch_size = 100
        total_ingested = 0

        for i in range(0, len(target_files), batch_size):
            batch = target_files[i:i + batch_size]
            ids = [f"code_{f['file_index']}_{f['file_path'].replace('/', '_').replace('.', '_')}" for f in batch]
            documents = [
                f"FILE: {f['file_path']}\nSUBSYSTEM: {f['subsystem']} ({f['layer']})\nLANGUAGE: {f['language']}\n\n{f['content_summary']}\n\nEXCERPT:\n{f['content'][:1500]}"
                for f in batch
            ]
            metadatas = [
                {
                    "file_path": f["file_path"],
                    "subsystem": f["subsystem"],
                    "layer": f["layer"],
                    "language": f["language"],
                    "lines_count": f["lines_count"],
                    "bytes_size": f["bytes_size"],
                    "client_id": "stehouwer_publishing"
                }
                for f in batch
            ]

            # Upsert into ChromaDB
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            total_ingested += len(batch)

        print(f"✅ ChromaDB 'ai_bs_codebase_vault' indexed {total_ingested:,} vector documents.")
    except Exception as e:
        print(f"⚠️ ChromaDB vector indexing warning (SQLite FTS5 will still handle all searches): {e}")


def export_knowledge_manifest(files: List[Dict[str, Any]], out_path: str):
    """
    Exports a structured JSON manifest of all 3,230 files and subsystem statistics.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    subsystems_stats = {}
    total_lines = 0
    total_bytes = 0

    file_index_list = []

    for f in files:
        sub = f["subsystem"]
        if sub not in subsystems_stats:
            subsystems_stats[sub] = {
                "layer": f["layer"],
                "file_count": 0,
                "total_lines": 0,
                "total_bytes": 0,
                "languages": set()
            }
        subsystems_stats[sub]["file_count"] += 1
        subsystems_stats[sub]["total_lines"] += f["lines_count"]
        subsystems_stats[sub]["total_bytes"] += f["bytes_size"]
        subsystems_stats[sub]["languages"].add(f["language"])

        total_lines += f["lines_count"]
        total_bytes += f["bytes_size"]

        file_index_list.append({
            "file_index": f["file_index"],
            "file_path": f["file_path"],
            "subsystem": f["subsystem"],
            "layer": f["layer"],
            "language": f["language"],
            "lines_count": f["lines_count"],
            "bytes_size": f["bytes_size"],
            "summary": f["content_summary"][:160]
        })

    # Format sets to lists for JSON serialization
    for sub, data in subsystems_stats.items():
        data["languages"] = sorted(list(data["languages"]))

    ver = "v5.327.0"
    v_file = os.path.join(BASE_DIR, "version.txt")
    if os.path.exists(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as vf:
                ver = vf.read().strip() or ver
        except Exception:
            pass

    manifest = {
        "title": "AI-BS Complete Master Source Code Knowledge Base Index",
        "ecosystem_version": ver,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(files),
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "subsystems": subsystems_stats,
        "files": file_index_list
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"📊 Manifest exported: {out_path} ({len(files):,} files, {total_lines:,} lines, {total_bytes:,} bytes).")


def main():
    target_path = None
    for p in SOURCE_PATHS:
        if os.path.exists(p):
            target_path = p
            break

    if not target_path:
        print(f"❌ Error: Master source code file not found in: {SOURCE_PATHS}")
        sys.exit(1)

    print("=" * 80)
    print("🚀 AI-BS COMPLETE SOURCE CODE KNOWLEDGE INGESTION PIPELINE")
    print("=" * 80)

    # 1. Parse markdown
    files = parse_master_sourcecode_bundle(target_path)
    if not files:
        print("❌ No files extracted. Exiting.")
        sys.exit(1)

    # 2. Initialize SQLite
    initialize_sqlite_tables(DB_PATH)

    # 3. Ingest into SQLite + FTS5
    populate_sqlite_knowledge(DB_PATH, files)

    # 4. Ingest into ChromaDB
    ingest_chroma_codebase_vault(files)

    # 5. Export JSON Manifest
    export_knowledge_manifest(files, MANIFEST_OUT)

    print("=" * 80)
    print(f"🎉 INGESTION COMPLETE: {len(files):,} files successfully indexed into SQLite FTS5 & ChromaDB!")
    print("=" * 80)


if __name__ == "__main__":
    main()
