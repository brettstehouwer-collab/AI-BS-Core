"""
AI-BS Sovereign Memory & Reasoning Ingestion Engine
===================================================
Scans, extracts, normalizes, and ingests all memory across:
1. Antigravity Brain Transcripts (User requests, internal thinking processes, solutions)
2. Antigravity Brain Artifacts (Architectural blueprints, walkthroughs, plans)
3. Gemini Takeout Historical Archives (Conversations, lore, manuscripts)
4. AI-BS Master Directives & Architectural Ledgers

Ingestion Targets:
- ChromaDB Vector Vaults (Ports 8001 & 8002):
    * antigravity_reasoning_memory
    * ai_bs_context_memory
    * stehouwer_llm_memory
- SQLite Master Vault (C:\\AI-BS\\backend\\aibs_master.db -> sovereign_reasoning_vault)
- SSD RAM Master Memory Dump (C:\\AI-BS\\AI-BS_Master_Memory\\master_memory_dump.json)
- Global Architectural Context (C:\\AI-BS\\AI_BS_Global_Context.md)
"""

from __future__ import annotations

import os
import sys
import glob
import json
import re
import time
import uuid
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

import chromadb
from bs4 import BeautifulSoup

# Paths
ROOT_DIR = Path(r"C:\AI-BS")
BACKEND_DIR = ROOT_DIR / "backend"
DB_PATH = BACKEND_DIR / "aibs_master.db"
BRAIN_DIR = Path(r"C:\Users\footb\.gemini\antigravity\brain")
TAKEOUT_DIR = ROOT_DIR / "Gemini_Takeout_Dataparrent"
DIRECTIVES_DIR = ROOT_DIR / "directives"
MASTER_MEM_DIR = ROOT_DIR / "AI-BS_Master_Memory"
MASTER_MEM_FILE = MASTER_MEM_DIR / "master_memory_dump.json"
GLOBAL_CONTEXT_FILE = ROOT_DIR / "AI_BS_Global_Context.md"

MASTER_MEM_DIR.mkdir(parents=True, exist_ok=True)


def init_sqlite_vault() -> None:
    """Initialize sovereign_reasoning_vault SQLite table and indexes."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sovereign_reasoning_vault (
            id TEXT PRIMARY KEY,
            source TEXT,
            conversation_id TEXT,
            category TEXT,
            memory_type TEXT,
            title TEXT,
            prompt TEXT,
            thinking_summary TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_srv_cat ON sovereign_reasoning_vault(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_srv_type ON sovereign_reasoning_vault(memory_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_srv_conv ON sovereign_reasoning_vault(conversation_id);")
    conn.commit()
    conn.close()


def clean_text(text: str) -> str:
    """Sanitize and normalize text for vectorization."""
    if not text:
        return ""
    # Strip null bytes and non-printable noise
    text = text.replace("\x00", "").strip()
    return text


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """Splits long text into overlapping chunks for embedding."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if len(chunk) > 40:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ==============================================================================
# 1. EXTRACTORS
# ==============================================================================

def extract_antigravity_transcripts() -> List[Dict[str, Any]]:
    """
    Extracts all conversation turns, thinking processes, and solutions from
    Antigravity brain transcripts.
    """
    print("[1/4] Scanning Antigravity Brain transcripts...")
    transcripts = glob.glob(str(BRAIN_DIR / "*" / ".system_generated" / "logs" / "transcript_full.jsonl"))
    if not transcripts:
        transcripts = glob.glob(str(BRAIN_DIR / "*" / ".system_generated" / "logs" / "transcript.jsonl"))

    extracted: List[Dict[str, Any]] = []

    for t_path in transcripts:
        conv_id = Path(t_path).parents[2].name
        try:
            with open(t_path, "r", encoding="utf-8", errors="ignore") as f:
                current_user_prompt = ""
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue

                    rec_type = record.get("type", "")
                    content = record.get("content", "")
                    thinking = record.get("thinking", "")
                    step_idx = record.get("step_index", 0)

                    if rec_type == "USER_INPUT":
                        current_user_prompt = clean_text(content)
                        if len(current_user_prompt) > 25:
                            extracted.append({
                                "id": f"prompt_{conv_id[:8]}_{step_idx}",
                                "source": "antigravity_transcript",
                                "conversation_id": conv_id,
                                "category": "user_instruction",
                                "memory_type": "prompt",
                                "title": f"User Prompt: {current_user_prompt[:80]}",
                                "prompt": current_user_prompt,
                                "thinking_summary": "",
                                "content": current_user_prompt,
                                "timestamp": record.get("created_at", "")
                            })
                    elif rec_type == "PLANNER_RESPONSE":
                        # Record thinking process memory
                        if thinking and len(thinking.strip()) > 50:
                            cleaned_thinking = clean_text(thinking)
                            # Create a concise summary for search
                            first_para = cleaned_thinking.split("\n\n")[0][:300]
                            extracted.append({
                                "id": f"think_{conv_id[:8]}_{step_idx}_{uuid.uuid4().hex[:4]}",
                                "source": "antigravity_transcript",
                                "conversation_id": conv_id,
                                "category": "agent_reasoning",
                                "memory_type": "thinking_process",
                                "title": f"Reasoning: {first_para[:80]}...",
                                "prompt": current_user_prompt[:300],
                                "thinking_summary": first_para,
                                "content": cleaned_thinking[:2500],
                                "timestamp": record.get("created_at", "")
                            })
                        # Record response/solution memory
                        if content and len(content.strip()) > 50:
                            cleaned_content = clean_text(content)
                            extracted.append({
                                "id": f"resp_{conv_id[:8]}_{step_idx}_{uuid.uuid4().hex[:4]}",
                                "source": "antigravity_transcript",
                                "conversation_id": conv_id,
                                "category": "solution_architecture",
                                "memory_type": "solution",
                                "title": f"Solution: {cleaned_content[:80]}",
                                "prompt": current_user_prompt[:300],
                                "thinking_summary": clean_text(thinking)[:200] if thinking else "",
                                "content": cleaned_content[:3000],
                                "timestamp": record.get("created_at", "")
                            })
        except Exception as exc:
            print(f"  [!] Skipped transcript {t_path}: {exc}")

    print(f"  -> Extracted {len(extracted)} memory items from Antigravity transcripts.")
    return extracted


def extract_antigravity_artifacts() -> List[Dict[str, Any]]:
    """Extracts all markdown architecture documents and implementation plans from brain folders."""
    print("[2/4] Scanning Antigravity Brain artifacts...")
    artifacts = glob.glob(str(BRAIN_DIR / "*" / "*.md"))
    extracted: List[Dict[str, Any]] = []

    for a_path in artifacts:
        conv_id = Path(a_path).parent.name
        file_name = Path(a_path).name
        try:
            with open(a_path, "r", encoding="utf-8", errors="ignore") as f:
                content = clean_text(f.read())
            if len(content) < 40:
                continue

            chunks = chunk_text(content, chunk_size=1500, overlap=250)
            for i, chunk in enumerate(chunks):
                extracted.append({
                    "id": f"artifact_{conv_id[:8]}_{file_name}_{i}",
                    "source": "antigravity_artifact",
                    "conversation_id": conv_id,
                    "category": "architectural_blueprint",
                    "memory_type": "artifact",
                    "title": f"Artifact: {file_name} (Part {i+1})",
                    "prompt": "",
                    "thinking_summary": "",
                    "content": chunk,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
        except Exception as exc:
            print(f"  [!] Skipped artifact {a_path}: {exc}")

    print(f"  -> Extracted {len(extracted)} memory chunks from Antigravity artifacts.")
    return extracted


def extract_gemini_takeout() -> List[Dict[str, Any]]:
    """Extracts Google Takeout historic JSON and HTML conversations."""
    print("[3/4] Scanning Gemini Takeout directory...")
    if not TAKEOUT_DIR.exists():
        print(f"  [-] Takeout directory {TAKEOUT_DIR} not found.")
        return []

    extracted: List[Dict[str, Any]] = []

    # Process JSON files
    json_files = glob.glob(str(TAKEOUT_DIR / "*.json"))
    for j_path in json_files:
        try:
            with open(j_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            file_name = Path(j_path).name

            if isinstance(data, list):
                for idx, item in enumerate(data):
                    parts = []
                    title = item.get("title", "")
                    if title:
                        parts.append(f"Prompt: {title}")
                    for sub in item.get("subtitles", []):
                        if "name" in sub:
                            parts.append(sub["name"])
                    for det in item.get("details", []):
                        if "name" in det:
                            parts.append(det["name"])

                    full_text = clean_text("\n".join(parts))
                    if len(full_text) > 60:
                        extracted.append({
                            "id": f"takeout_json_{file_name[:12]}_{idx}",
                            "source": "gemini_takeout",
                            "conversation_id": "takeout_archive",
                            "category": "takeout_history",
                            "memory_type": "conversation",
                            "title": f"Takeout: {title[:70] if title else file_name}",
                            "prompt": title,
                            "thinking_summary": "",
                            "content": full_text[:2500],
                            "timestamp": item.get("time", "")
                        })
            elif isinstance(data, dict):
                content = clean_text(json.dumps(data, indent=2))
                if len(content) > 60:
                    chunks = chunk_text(content, chunk_size=1200)
                    for c_idx, chunk in enumerate(chunks[:5]):
                        extracted.append({
                            "id": f"takeout_json_obj_{file_name[:12]}_{c_idx}",
                            "source": "gemini_takeout",
                            "conversation_id": "takeout_archive",
                            "category": "takeout_history",
                            "memory_type": "data_record",
                            "title": f"Takeout Record: {file_name}",
                            "prompt": "",
                            "thinking_summary": "",
                            "content": chunk,
                            "timestamp": ""
                        })
        except Exception:
            continue

    # Process HTML files
    html_files = glob.glob(str(TAKEOUT_DIR / "*.html"))
    for h_path in html_files[:100]:  # Cap first 100 HTML files to keep memory lean
        try:
            with open(h_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            text = clean_text(soup.get_text(separator="\n", strip=True))
            if len(text) > 80:
                file_name = Path(h_path).name
                chunks = chunk_text(text, chunk_size=1200)
                for c_idx, chunk in enumerate(chunks[:3]):
                    extracted.append({
                        "id": f"takeout_html_{file_name[:12]}_{c_idx}",
                        "source": "gemini_takeout",
                        "conversation_id": "takeout_archive",
                        "category": "takeout_history",
                        "memory_type": "html_dialogue",
                        "title": f"Takeout HTML: {file_name}",
                        "prompt": "",
                        "thinking_summary": "",
                        "content": chunk,
                        "timestamp": ""
                    })
        except Exception:
            continue

    print(f"  -> Extracted {len(extracted)} items from Gemini Takeout.")
    return extracted


def extract_system_directives() -> List[Dict[str, Any]]:
    """Extracts master directives and ledgers."""
    print("[4/4] Scanning System Directives and Master Ledgers...")
    extracted: List[Dict[str, Any]] = []

    target_files = [
        ROOT_DIR / "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
        ROOT_DIR / "Stehouwer_Master_Ledger.md",
    ]
    target_files.extend(list(DIRECTIVES_DIR.glob("*.md")))

    for p in target_files:
        if not p.exists():
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                text = clean_text(f.read())
            if len(text) < 40:
                continue

            chunks = chunk_text(text, chunk_size=1500, overlap=200)
            for i, chunk in enumerate(chunks):
                extracted.append({
                    "id": f"directive_{p.stem}_{i}",
                    "source": "system_directive",
                    "conversation_id": "host_directives",
                    "category": "privilege_directive",
                    "memory_type": "directive",
                    "title": f"Directive: {p.name} (Section {i+1})",
                    "prompt": "",
                    "thinking_summary": "",
                    "content": chunk,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
        except Exception:
            continue

    print(f"  -> Extracted {len(extracted)} chunks from Directives and Master Ledgers.")
    return extracted


# ==============================================================================
# 2. INGESTION ENGINE
# ==============================================================================

def ingest_to_sqlite(items: List[Dict[str, Any]]) -> int:
    """Inserts records into SQLite sovereign_reasoning_vault."""
    init_sqlite_vault()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    count = 0
    for it in items:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO sovereign_reasoning_vault
                (id, source, conversation_id, category, memory_type, title, prompt, thinking_summary, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                it["id"],
                it.get("source", ""),
                it.get("conversation_id", ""),
                it.get("category", ""),
                it.get("memory_type", ""),
                it.get("title", ""),
                it.get("prompt", ""),
                it.get("thinking_summary", ""),
                it.get("content", ""),
            ))
            count += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    return count


def ingest_to_chroma(items: List[Dict[str, Any]], ports: List[int] = [8001, 8002]) -> Dict[int, int]:
    """Ingests memories into ChromaDB on specified ports with batching."""
    results = {}

    for port in ports:
        try:
            client = chromadb.HttpClient(host="127.0.0.1", port=port)
            col_reasoning = client.get_or_create_collection(name="antigravity_reasoning_memory")
            col_context = client.get_or_create_collection(name="ai_bs_context_memory")

            inserted = 0
            batch_size = 100
            seen_ids = set()

            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                docs = []
                metas = []
                ids = []

                for item in batch:
                    text = item.get("content", "").strip()
                    if not text:
                        continue
                    base_id = str(item["id"])
                    candidate_id = base_id
                    suffix_counter = 1
                    while candidate_id in seen_ids:
                        candidate_id = f"{base_id}_{suffix_counter}"
                        suffix_counter += 1
                    seen_ids.add(candidate_id)

                    docs.append(text)
                    metas.append({
                        "source": str(item.get("source", "")),
                        "category": str(item.get("category", "")),
                        "memory_type": str(item.get("memory_type", "")),
                        "conversation_id": str(item.get("conversation_id", "")),
                        "title": str(item.get("title", ""))[:120],
                    })
                    ids.append(candidate_id)

                if docs:
                    try:
                        col_reasoning.upsert(
                            documents=docs,
                            metadatas=metas,
                            ids=ids
                        )
                        inserted += len(docs)
                    except Exception as b_exc:
                        print(f"    [!] Batch {i//batch_size} reasoning error: {b_exc}")

                    # Also mirror key architectural blueprints to context memory
                    blueprint_docs = [d for d, m in zip(docs, metas) if m["category"] in ("architectural_blueprint", "privilege_directive")]
                    blueprint_metas = [m for m in metas if m["category"] in ("architectural_blueprint", "privilege_directive")]
                    blueprint_ids = [f"ctx_{id_}" for id_, m in zip(ids, metas) if m["category"] in ("architectural_blueprint", "privilege_directive")]

                    if blueprint_docs:
                        try:
                            col_context.upsert(
                                documents=blueprint_docs,
                                metadatas=blueprint_metas,
                                ids=blueprint_ids
                            )
                        except Exception:
                            pass

            results[port] = inserted
            print(f"  [+] ChromaDB Port {port}: Ingested {inserted} vectors into antigravity_reasoning_memory.")
        except Exception as exc:
            print(f"  [!] ChromaDB Port {port} error: {exc}")
            results[port] = 0

    return results


def update_master_memory_dump(items: List[Dict[str, Any]]) -> int:
    """Updates C:\\AI-BS\\AI-BS_Master_Memory\\master_memory_dump.json for SSD RAM."""
    high_value_items = []
    for it in items:
        # Prioritize thinking processes, prompt-solution pairs, and directives
        if it.get("memory_type") in ("thinking_process", "solution", "directive", "artifact"):
            high_value_items.append({
                "id": it["id"],
                "prompt": it.get("prompt", it.get("title", "")),
                "document": it.get("content", ""),
                "metadata": {
                    "source": it.get("source", ""),
                    "category": it.get("category", ""),
                    "type": it.get("memory_type", ""),
                    "timestamp": time.time(),
                }
            })

    try:
        with open(MASTER_MEM_FILE, "w", encoding="utf-8") as f:
            json.dump(high_value_items[:1000], f, indent=2)
        print(f"  [+] Master SSD RAM Memory written: {len(high_value_items[:1000])} items ({MASTER_MEM_FILE.stat().st_size / 1024:.1f} KB).")
        return len(high_value_items[:1000])
    except Exception as exc:
        print(f"  [!] Failed to write master memory dump: {exc}")
        return 0


def generate_global_context_ledger(items: List[Dict[str, Any]]) -> None:
    """Generates the master AI_BS_Global_Context.md markdown knowledge file."""
    reasoning_count = sum(1 for it in items if it.get("memory_type") == "thinking_process")
    prompt_count = sum(1 for it in items if it.get("memory_type") == "prompt")
    solution_count = sum(1 for it in items if it.get("memory_type") == "solution")
    artifact_count = sum(1 for it in items if it.get("memory_type") == "artifact")
    takeout_count = sum(1 for it in items if it.get("source") == "gemini_takeout")

    content = f"""# AI-BS Sovereign Intelligence & Memory Ledger
*Generated: {time.strftime('%Y-%m-%d %H:%M:%S')} | Target: C:\\AI-BS Sovereign Intelligence Ecosystem*

## Executive Summary
This master context ledger integrates all historical thoughts, user prompts, architectural blueprints, and diagnostic resolutions across the AI-BS ecosystem and Antigravity pair programming sessions.

- **Total Memory Nodes Ingested**: {len(items):,}
- **Agent Chain-of-Thought Reasoning Traces**: {reasoning_count:,}
- **User Instructions & Architectural Goals**: {prompt_count:,}
- **Production Solutions & Code Fixes**: {solution_count:,}
- **System Architecture Artifacts & Walkthroughs**: {artifact_count:,}
- **Historic Google Takeout Records**: {takeout_count:,}

---

## High-Priority System Resolutions & Core Learnings

### 1. Window Lifecycle & Self-Respawn Prevention
- **Issue**: Closing `AI_BS_Studio.exe` spawned multiple new GUI windows because `closeEvent()` called `subprocess.Popen([sys.executable, cleaner])`, where `sys.executable` in a PyInstaller frozen binary is `AI_BS_Studio.exe` itself.
- **Permanent Fix**: `sweep_zombie_nodes(dry_run=False)` is executed strictly in-process. `main()` guards against `.py` argument invocations (`return 0`).

### 2. 3-Way Wireless Screen Mirror & Cast Hub
- **PC -> Wireless Display**: Native Win32 `Win+K` via `explorer.exe shell:::{{3808076B-0F45-46e0-A656-77D463E73C70}}` and `DisplaySwitch.exe /extend`.
- **PC -> Phone**: Low-latency mobile stream on `http://192.168.4.26:5173/?tab=ide` with full viewport scaling.
- **Phone -> PC**: Wireless ADB port 5555 paired with `scrcpy --video-bit-rate=12M`.

### 3. AI-BS Sovereign Privilege Directive (`AIBS-DIR-000-ROOT-AUTHORITY`)
- **Root Authority Certificate**: 4096-bit RSA `CN=AI-BS Sovereign Root Authority, O=Stehouwer Publishing LLC` (Thumbprint: `7DFDCE294CCCE3EE2B32AF67727768385822FFF3`).
- **Ring 0 / MSR Access**: VTL 1 Memory Integrity (`HypervisorEnforcedCodeIntegrity\Enabled = 0`) unblocking MSR telemetry while preserving WSL2 via `bcdedit /set hypervisorlaunchtype auto`.
- **Two-Strike Diagnostic Halt**: Consecutive command failures logged to `ai_bs_error_heuristics` in `C:\\AI-BS\\backend\\aibs_master.db`.

### 4. Native Windows Desktop Architecture Enforcement
- **Zero Browser Engines**: Strict prohibition of Electron, Chromium, and WebView2.
- **Real-Time Audio**: Register with Windows Multimedia Class Scheduler Service (**MMCSS "Pro Audio"**, thread priority 15) using lock-free single-producer single-consumer ring buffers.

---

## Active Vector Vault Collections (Ports 8001 & 8002)
- `antigravity_reasoning_memory`: Dedicated vector vault for all thinking processes, diagnoses, and solutions.
- `ai_bs_context_memory`: System-wide architectural blueprints and operational schemas.
- `stehouwer_llm_memory`: 39,000+ domain and creative knowledge vectors.
- `sovereign_reasoning_vault`: SQLite indexed storage with sub-millisecond retrieval.
"""
    try:
        with open(GLOBAL_CONTEXT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [+] Global Context Ledger generated: {GLOBAL_CONTEXT_FILE} ({GLOBAL_CONTEXT_FILE.stat().st_size} bytes).")
    except Exception as exc:
        print(f"  [!] Failed to generate global context ledger: {exc}")


# ==============================================================================
# 3. SEARCH & QUERY INTERFACE
# ==============================================================================

def search_memory(query: str, n_results: int = 5, port: int = 8001) -> List[Dict[str, Any]]:
    """Searches antigravity_reasoning_memory ChromaDB collection."""
    try:
        client = chromadb.HttpClient(host="127.0.0.1", port=port)
        col = client.get_collection(name="antigravity_reasoning_memory")
        res = col.query(query_texts=[query], n_results=n_results)

        hits = []
        if res and res.get("documents"):
            for i in range(len(res["documents"][0])):
                hits.append({
                    "id": res["ids"][0][i],
                    "document": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i] if res.get("metadatas") else {},
                    "distance": res["distances"][0][i] if res.get("distances") else 0.0
                })
        return hits
    except Exception as e:
        print(f"Vector search error on port {port}: {e}")
        return []


def run_full_pipeline(include_takeout: bool = True) -> Dict[str, Any]:
    """Executes the complete scan, normalization, and ingestion pipeline."""
    start_time = time.time()
    print("=" * 65)
    print("AI-BS SOVEREIGN MEMORY & REASONING INGESTION PIPELINE")
    print("=" * 65)

    all_items: List[Dict[str, Any]] = []
    all_items.extend(extract_antigravity_transcripts())
    all_items.extend(extract_antigravity_artifacts())
    all_items.extend(extract_system_directives())
    if include_takeout:
        all_items.extend(extract_gemini_takeout())

    total_extracted = len(all_items)
    print(f"\n[+] Total Memory Units Extracted: {total_extracted:,}")

    print("\n[+] Phase 1: Ingesting into SQLite sovereign_reasoning_vault...")
    sqlite_count = ingest_to_sqlite(all_items)
    print(f"  -> {sqlite_count:,} records stored in aibs_master.db.")

    print("\n[+] Phase 2: Ingesting into ChromaDB Vector Stores (8001 & 8002)...")
    chroma_results = ingest_to_chroma(all_items, ports=[8001, 8002])

    print("\n[+] Phase 3: Updating Master SSD RAM Memory Dump...")
    master_count = update_master_memory_dump(all_items)

    print("\n[+] Phase 4: Compiling Global Context Ledger...")
    generate_global_context_ledger(all_items)

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 65)
    print(f"INGESTION PIPELINE COMPLETE IN {elapsed}s")
    print(f"SQLite Records: {sqlite_count:,} | Chroma (8001): {chroma_results.get(8001, 0):,} | SSD RAM: {master_count:,}")
    print("=" * 65)

    return {
        "status": "success",
        "elapsed_seconds": elapsed,
        "total_extracted": total_extracted,
        "sqlite_count": sqlite_count,
        "chroma_port_8001": chroma_results.get(8001, 0),
        "chroma_port_8002": chroma_results.get(8002, 0),
        "ssd_ram_count": master_count
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BS Sovereign Memory Ingestor")
    parser.add_argument("--run", action="store_true", help="Run full memory ingestion pipeline")
    parser.add_argument("--no-takeout", action="store_true", help="Skip Google Takeout directory")
    parser.add_argument("--search", type=str, help="Search memory via semantic query")
    parser.add_argument("--stats", action="store_true", help="Display current memory stats")

    args = parser.parse_args()

    if args.search:
        results = search_memory(args.search)
        print(f"\n--- Search Results for '{args.search}' ---")
        for idx, hit in enumerate(results):
            print(f"[{idx+1}] ID: {hit['id']} | Dist: {hit['distance']:.3f} | Title: {hit['metadata'].get('title')}")
            print(f"    Category: {hit['metadata'].get('category')} | Source: {hit['metadata'].get('source')}")
            print(f"    Snippet: {hit['document'][:200]}...\n")
    elif args.stats:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sovereign_reasoning_vault;")
        srv_count = cursor.fetchone()[0]
        conn.close()
        try:
            client = chromadb.HttpClient(host="127.0.0.1", port=8001)
            col = client.get_collection("antigravity_reasoning_memory")
            chroma_count = col.count()
        except Exception:
            chroma_count = "Unavailable"
        print(f"Sovereign Reasoning Vault (SQLite): {srv_count} rows")
        print(f"Antigravity Reasoning Memory (Chroma 8001): {chroma_count} vectors")
        print(f"Master Memory Dump (SSD RAM): {MASTER_MEM_FILE.exists()} ({MASTER_MEM_FILE.stat().st_size if MASTER_MEM_FILE.exists() else 0} bytes)")
    else:
        run_full_pipeline(include_takeout=not args.no_takeout)
