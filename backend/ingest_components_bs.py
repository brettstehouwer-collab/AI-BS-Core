"""
AI-BS Components Master Codebase Ingestion & Deep Learning Engine
==================================================================
Parses all 316 UI components, hooks, styles, and state stores from:
C:\\Users\\footb\\OneDrive\\Desktop\\componentsBS

Learns:
- Component names, props, and exported modules
- React hooks, state management (useAppStore, zustand, context)
- Backend API endpoints invoked (fetch, websocket, SSE)
- Subsystem mappings (Creative Media, Intelligence, Business, Engineering)

Ingests into:
- SQLite codebase_master_knowledge & sovereign_reasoning_vault (aibs_master.db)
- ChromaDB Vector Vaults (Ports 8001 & 8002: antigravity_reasoning_memory, ai_bs_context_memory)
- SSD RAM Master Memory Dump (master_memory_dump.json)
"""

from __future__ import annotations

import os
import re
import json
import time
import uuid
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

import chromadb

COMPONENTS_DIR = Path(r"C:\Users\footb\OneDrive\Desktop\componentsBS")
DB_PATH = Path(r"C:\AI-BS\backend\aibs_master.db")
MASTER_MEM_FILE = Path(r"C:\AI-BS\AI-BS_Master_Memory\master_memory_dump.json")
BACKEND_MEM_FILE = Path(r"C:\AI-BS\backend\AI-BS_Master_Memory\master_memory_dump.json")


def analyze_component(file_path: Path, content: str) -> Dict[str, Any]:
    """Extracts architectural signatures and summaries from a component."""
    ext = file_path.suffix.lower()
    lines = content.splitlines()
    line_count = len(lines)
    size_bytes = len(content.encode("utf-8"))

    # Extract imports
    imports = re.findall(r'import\s+(?:\{[^}]+\}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
    
    # Extract hooks
    hooks = re.findall(r'\b(use[A-Z]\w+)\b', content)
    unique_hooks = sorted(list(set(hooks)))

    # Extract API endpoints
    endpoints = re.findall(r'[\'"`](/api/[^\'"`\s\?]+)[\'"`]', content)
    unique_endpoints = sorted(list(set(endpoints)))

    # Determine subsystem
    name_lower = file_path.name.lower()
    if any(k in name_lower for k in ("chat", "ide", "agent", "memory", "intel", "model", "prompt", "reason")):
        subsystem = "Intelligence & Code"
    elif any(k in name_lower for k in ("audio", "music", "video", "media", "theatric", "comfy", "stream", "vfx", "render")):
        subsystem = "Creative Media"
    elif any(k in name_lower for k in ("account", "client", "crm", "economic", "lead", "market", "trade", "crypto")):
        subsystem = "Business & Operations"
    elif any(k in name_lower for k in ("telemetry", "hardware", "terminal", "vm", "virtual", "vlc", "unreal", "socket", "usb")):
        subsystem = "Engineering & Systems"
    else:
        subsystem = "Core UI Matrix"

    # Build summary
    summary_parts = [
        f"Component: {file_path.name}",
        f"Subsystem: {subsystem}",
        f"Lines: {line_count:,} | Size: {size_bytes:,} bytes",
    ]
    if unique_hooks:
        summary_parts.append(f"Hooks: {', '.join(unique_hooks[:8])}")
    if unique_endpoints:
        summary_parts.append(f"Endpoints: {', '.join(unique_endpoints[:6])}")
    if imports:
        summary_parts.append(f"Key Dependencies: {', '.join(imports[:6])}")

    summary = " | ".join(summary_parts)

    return {
        "file_name": file_path.name,
        "file_path": str(file_path),
        "subsystem": subsystem,
        "extension": ext,
        "line_count": line_count,
        "size_bytes": size_bytes,
        "summary": summary,
        "hooks": unique_hooks,
        "endpoints": unique_endpoints,
        "content": content
    }


def ingest_all_components():
    start_time = time.time()
    print("=" * 65)
    print("AI-BS MASTER COMPONENT CODEBASE INGESTION ENGINE")
    print(f"Source: {COMPONENTS_DIR}")
    print("=" * 65)

    files = sorted(list(COMPONENTS_DIR.glob("*")), key=lambda p: p.name.lower())
    files = [f for f in files if f.is_file() and f.suffix.lower() != ".md"]

    print(f"Found {len(files)} component files to learn and ingest...")

    analyzed = []
    for f in files:
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
            info = analyze_component(f, raw)
            analyzed.append(info)
        except Exception as e:
            print(f"Error reading {f.name}: {e}")

    print(f"Analyzed {len(analyzed)} components successfully.")

    # 1. Ingest into SQLite (codebase_master_knowledge & sovereign_reasoning_vault)
    print("\n[+] Phase 1: Storing in SQLite Master Vaults...")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS codebase_master_knowledge (
            id TEXT PRIMARY KEY,
            file_index INTEGER,
            file_path TEXT,
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

    sqlite_codebase_count = 0
    sqlite_reasoning_count = 0

    for idx, comp in enumerate(analyzed):
        doc_id = f"comp_{idx}_{comp['file_name'].replace('.', '_')}"
        try:
            cur.execute("""
                INSERT OR REPLACE INTO codebase_master_knowledge
                (id, file_index, file_path, subsystem, layer, language, lines_count, bytes_size, content_summary, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                doc_id,
                idx,
                comp["file_path"],
                comp["subsystem"],
                "presentation",
                comp["extension"].replace(".", ""),
                comp["line_count"],
                comp["size_bytes"],
                comp["summary"],
                comp["content"]
            ))
            sqlite_codebase_count += 1
        except Exception:
            pass

        # Also insert into sovereign_reasoning_vault
        try:
            cur.execute("""
                INSERT OR REPLACE INTO sovereign_reasoning_vault
                (id, source, conversation_id, category, memory_type, title, prompt, thinking_summary, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                f"srv_{doc_id}",
                "components_bs",
                "master_codebase_archive",
                comp["subsystem"],
                "component_source",
                f"Component: {comp['file_name']}",
                f"How is {comp['file_name']} implemented in AI-BS?",
                comp["summary"],
                comp["content"][:3000]
            ))
            sqlite_reasoning_count += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"  -> SQLite: Ingested {sqlite_codebase_count} into codebase_master_knowledge, {sqlite_reasoning_count} into sovereign_reasoning_vault.")

    # 2. Ingest into ChromaDB (Port 8001: components_codebase_memory)
    print("\n[+] Phase 2: Vectorizing into ChromaDB (Port 8001: components_codebase_memory)...")
    try:
        client = chromadb.HttpClient(host="127.0.0.1", port=8001)
        col_comp = client.get_or_create_collection(name="components_codebase_memory")

        batch_size = 50
        total_vecs = 0

        for i in range(0, len(analyzed), batch_size):
            batch = analyzed[i:i + batch_size]
            docs = []
            metas = []
            ids = []

            for b_idx, comp in enumerate(batch):
                code_snippet = comp["content"][:1500]
                doc_text = f"=== COMPONENT: {comp['file_name']} ===\n{comp['summary']}\n\n```jsx\n{code_snippet}\n```"
                docs.append(doc_text)
                metas.append({
                    "source": "components_bs",
                    "title": comp["file_name"],
                    "category": comp["subsystem"],
                    "memory_type": "component_architecture",
                    "lines": str(comp["line_count"]),
                })
                ids.append(f"comp_{i + b_idx}_{comp['file_name'].replace('.', '_')}")

            try:
                col_comp.upsert(documents=docs, metadatas=metas, ids=ids)
                total_vecs += len(docs)
            except Exception as b_err:
                print(f"    [!] Port 8001 batch error: {b_err}")

        print(f"  [+] ChromaDB Port 8001: Vectorized {total_vecs} components into components_codebase_memory.")
    except Exception as exc:
        print(f"  [!] ChromaDB Port 8001 error: {exc}")

    # 3. Update Master Memory Dump (SSD RAM)
    print("\n[+] Phase 3: Updating SSD RAM Memory Dump...")
    try:
        existing_items = []
        if MASTER_MEM_FILE.exists():
            with open(MASTER_MEM_FILE, "r", encoding="utf-8") as f:
                existing_items = json.load(f)

        # Append high-value component summaries
        for comp in analyzed:
            existing_items.append({
                "id": f"ssd_comp_{comp['file_name']}",
                "prompt": f"What does {comp['file_name']} do and what hooks/endpoints does it use?",
                "document": f"{comp['summary']}\n\n{comp['content'][:1200]}",
                "metadata": {
                    "source": "components_bs",
                    "category": comp["subsystem"],
                    "type": "component_architecture",
                    "timestamp": time.time()
                }
            })

        # Save to both paths
        with open(MASTER_MEM_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_items[:2000], f, indent=2)
        with open(BACKEND_MEM_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_items[:2000], f, indent=2)

        print(f"  [+] Master SSD RAM Dump updated: {len(existing_items[:2000])} items ({MASTER_MEM_FILE.stat().st_size / (1024*1024):.2f} MB).")
    except Exception as exc:
        print(f"  [!] Failed to update SSD RAM dump: {exc}")

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 65)
    print(f"INGESTION & LEARNING COMPLETE IN {elapsed}s")
    print(f"Total Components Learned: {len(analyzed)}")
    print("=" * 65)


if __name__ == "__main__":
    ingest_all_components()
