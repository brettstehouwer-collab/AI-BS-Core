#!/usr/bin/env python3
r"""
ingest_antigravity_sessions.py — High-Performance Antigravity Brain Ingestor for AI-BS.
Ingests all historical session transcripts, tasks, plans, and walkthroughs from:
C:\Users\footb\OneDrive\Desktop\ingest folder
Persists to:
1. SQLite Vault: C:\AI-BS\backend\stehouwer_vault.db (vault_items)
2. Master Memory Dump: D:\AI-BS_Master_Memory\master_memory_dump.json & C:\AI-BS\master_memory_dump.json
3. Session History Archive: C:\AI-BS\backend\session_history_archive.json
"""

import os
import sys
import json
import sqlite3
import time
import hashlib
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

INGEST_DIR = r"C:\Users\footb\OneDrive\Desktop\ingest folder"
BACKEND_DIR = Path(r"C:\AI-BS\backend")
ROOT_DIR = Path(r"C:\AI-BS")
VAULT_DB_PATH = BACKEND_DIR / "stehouwer_vault.db"
SESSION_ARCHIVE_PATH = BACKEND_DIR / "session_history_archive.json"

MASTER_MEMORY_PATHS = [
    Path(r"D:\AI-BS_Master_Memory\master_memory_dump.json"),
    ROOT_DIR / "master_memory_dump.json",
    BACKEND_DIR / "master_memory_dump.json",
]


def init_vault_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            collection TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    try:
        conn.execute("ALTER TABLE vault_items ADD COLUMN item_hash TEXT;")
    except Exception:
        pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vault_collection ON vault_items(collection);")
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vault_hash ON vault_items(item_hash);")
    except Exception:
        pass
    conn.commit()


def hash_item(collection: str, title: str, content: str) -> str:
    return hashlib.sha256(f"{collection}::{title}::{content[:1000]}".encode("utf-8", errors="ignore")).hexdigest()


def ingest_all_sessions():
    start_time = time.time()
    print("======================================================================")
    print("AI-BS SOVEREIGN INGESTOR: Antigravity Session Vault & Memory Sync")
    print(f"Source Directory: {INGEST_DIR}")
    print("======================================================================")

    if not os.path.exists(INGEST_DIR):
        print(f"ERROR: Ingest directory not found: {INGEST_DIR}")
        return

    conn = sqlite3.connect(str(VAULT_DB_PATH))
    init_vault_db(conn)

    session_folders = [f for f in os.listdir(INGEST_DIR) if os.path.isdir(os.path.join(INGEST_DIR, f))]
    print(f"Found {len(session_folders)} session folders to ingest.\n")

    stats = {
        "sessions_processed": 0,
        "transcripts": 0,
        "user_messages": 0,
        "planner_responses": 0,
        "tasks": 0,
        "plans": 0,
        "walkthroughs": 0,
        "vault_records_inserted": 0,
        "master_memory_entries": 0,
    }

    vault_batch = []
    memory_dump_entries = []
    session_archive_entries = []

    for idx, folder_name in enumerate(session_folders, 1):
        folder_path = os.path.join(INGEST_DIR, folder_name)
        session_id = folder_name
        stats["sessions_processed"] += 1

        # 1. Ingest task.md
        task_path = os.path.join(folder_path, "task.md")
        if os.path.exists(task_path):
            try:
                with open(task_path, "r", encoding="utf-8", errors="ignore") as f:
                    task_content = f.read().strip()
                if task_content:
                    stats["tasks"] += 1
                    title = f"Task: {task_content.splitlines()[0][:80]}" if task_content.splitlines() else f"Task [{session_id[:8]}]"
                    item_h = hash_item("antigravity_tasks", title, task_content)
                    vault_batch.append((title, task_content, "antigravity_tasks", f"session_id:{session_id}", item_h))
            except Exception:
                pass

        # 2. Ingest implementation_plan.md
        plan_path = os.path.join(folder_path, "implementation_plan.md")
        if os.path.exists(plan_path):
            try:
                with open(plan_path, "r", encoding="utf-8", errors="ignore") as f:
                    plan_content = f.read().strip()
                if plan_content:
                    stats["plans"] += 1
                    title = f"Plan: {plan_content.splitlines()[0][:80]}" if plan_content.splitlines() else f"Plan [{session_id[:8]}]"
                    item_h = hash_item("antigravity_plans", title, plan_content)
                    vault_batch.append((title, plan_content, "antigravity_plans", f"session_id:{session_id}", item_h))
            except Exception:
                pass

        # 3. Ingest walkthrough.md
        walk_path = os.path.join(folder_path, "walkthrough.md")
        if os.path.exists(walk_path):
            try:
                with open(walk_path, "r", encoding="utf-8", errors="ignore") as f:
                    walk_content = f.read().strip()
                if walk_content:
                    stats["walkthroughs"] += 1
                    title = f"Walkthrough: {walk_content.splitlines()[0][:80]}" if walk_content.splitlines() else f"Walkthrough [{session_id[:8]}]"
                    item_h = hash_item("antigravity_walkthroughs", title, walk_content)
                    vault_batch.append((title, walk_content, "antigravity_walkthroughs", f"session_id:{session_id}", item_h))
            except Exception:
                pass

        # 4. Ingest transcripts (.system_generated/logs/transcript.jsonl or transcript.jsonl)
        trans_candidates = [
            os.path.join(folder_path, ".system_generated", "logs", "transcript.jsonl"),
            os.path.join(folder_path, "transcript.jsonl"),
            os.path.join(folder_path, ".system_generated", "logs", "transcript_full.jsonl"),
            os.path.join(folder_path, "transcript_full.jsonl"),
        ]

        found_trans = None
        for tc in trans_candidates:
            if os.path.exists(tc) and os.path.getsize(tc) > 0:
                found_trans = tc
                break

        if found_trans:
            stats["transcripts"] += 1
            try:
                current_user_prompt = ""
                with open(found_trans, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            entry_type = entry.get("type", "")
                            source = entry.get("source", "")
                            content = entry.get("content", "")

                            if entry_type == "USER_INPUT" and content:
                                current_user_prompt = str(content)
                                stats["user_messages"] += 1
                            elif (entry_type == "PLANNER_RESPONSE" or source == "MODEL") and content:
                                model_text = str(content)
                                if len(model_text) > 40:
                                    stats["planner_responses"] += 1
                                    
                                    # Create high-yield heuristic turn
                                    clean_prompt_title = (current_user_prompt[:80].replace("\n", " ").strip()) if current_user_prompt else f"Session Turn [{session_id[:8]}]"
                                    turn_text = f"User Request: {current_user_prompt}\n\nArchitectural Solution:\n{model_text}" if current_user_prompt else model_text
                                    
                                    item_h = hash_item("antigravity_transcripts", clean_prompt_title, turn_text)
                                    vault_batch.append((
                                        clean_prompt_title,
                                        turn_text,
                                        "antigravity_transcripts",
                                        f"session_id:{session_id},type:transcript_turn",
                                        item_h
                                    ))

                                    # Also record to master memory dump
                                    memory_dump_entries.append({
                                        "id": f"antigravity_{session_id[:8]}_{int(time.time()*1000)%1000000}_{len(memory_dump_entries)}",
                                        "text": turn_text[:1500],
                                        "metadata": {
                                            "session_id": session_id,
                                            "source": "antigravity_transcript",
                                            "title": clean_prompt_title
                                        },
                                        "timestamp": time.time()
                                    })

                                    # Session archive sample
                                    if len(session_archive_entries) < 1000:
                                        session_archive_entries.append({
                                            "session_id": session_id,
                                            "user_msg": current_user_prompt[:500],
                                            "ai_response": model_text[:1000],
                                            "timestamp": time.time()
                                        })
                        except Exception:
                            continue
            except Exception:
                pass

        # Batch insert to SQLite Vault periodically
        if len(vault_batch) >= 500:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO vault_items (title, content, collection, tags, item_hash)
                VALUES (?, ?, ?, ?, ?);
            """, vault_batch)
            stats["vault_records_inserted"] += cursor.rowcount
            conn.commit()
            print(f"[{idx}/{len(session_folders)}] Processed sessions... Vault items inserted so far: {stats['vault_records_inserted']}")
            vault_batch = []

    # Final vault batch commit
    if vault_batch:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR IGNORE INTO vault_items (title, content, collection, tags, item_hash)
            VALUES (?, ?, ?, ?, ?);
        """, vault_batch)
        stats["vault_records_inserted"] += cursor.rowcount
        conn.commit()

    conn.close()

    # 5. Persist Master Memory Dumps
    print(f"\nPersisting Master Memory Dumps ({len(memory_dump_entries)} entries)...")
    for mem_path in MASTER_MEMORY_PATHS:
        try:
            mem_path.parent.mkdir(parents=True, exist_ok=True)
            existing_dump = []
            if os.path.exists(mem_path):
                try:
                    with open(mem_path, "r", encoding="utf-8", errors="ignore") as f:
                        existing_dump = json.load(f)
                        if not isinstance(existing_dump, list):
                            existing_dump = [existing_dump]
                except Exception:
                    existing_dump = []

            # Combine and cap at 10,000 top entries
            combined = memory_dump_entries + existing_dump
            # Deduplicate by id or text
            seen_hashes = set()
            unique_dump = []
            for item in combined:
                t_hash = hashlib.sha256(item.get("text", "")[:200].encode("utf-8", errors="ignore")).hexdigest()
                if t_hash not in seen_hashes:
                    seen_hashes.add(t_hash)
                    unique_dump.append(item)

            if len(unique_dump) > 10000:
                unique_dump = unique_dump[:10000]

            with open(mem_path, "w", encoding="utf-8") as f:
                json.dump(unique_dump, f, indent=2)

            print(f" -> Synchronized {len(unique_dump)} blocks to {mem_path}")
            stats["master_memory_entries"] = len(unique_dump)
        except Exception as e:
            print(f"Notice: Could not write to {mem_path}: {e}")

    # 6. Persist Session History Archive
    try:
        SESSION_ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_ARCHIVE_PATH, "w", encoding="utf-8") as f:
            json.dump(session_archive_entries, f, indent=2)
        print(f" -> Synchronized session history archive ({len(session_archive_entries)} records)")
    except Exception as e:
        print(f"Notice: Session history archive write notice: {e}")

    elapsed = round(time.time() - start_time, 2)
    print("\n======================================================================")
    print(f"INGESTION COMPLETE IN {elapsed}s!")
    print(f" - Sessions Processed:       {stats['sessions_processed']}")
    print(f" - Transcripts Parsed:       {stats['transcripts']}")
    print(f" - User Prompts Ingested:    {stats['user_messages']}")
    print(f" - Model Responses Ingested: {stats['planner_responses']}")
    print(f" - Task Documents:           {stats['tasks']}")
    print(f" - Implementation Plans:     {stats['plans']}")
    print(f" - Walkthrough Summaries:    {stats['walkthroughs']}")
    print(f" - Total Vault Records Added:{stats['vault_records_inserted']}")
    print(f" - Master Memory Dump Size:  {stats['master_memory_entries']} blocks")
    print("======================================================================\n")


if __name__ == "__main__":
    ingest_all_sessions()
