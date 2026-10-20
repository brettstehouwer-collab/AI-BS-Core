import sqlite3
import json
import time
import uuid
import os

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
TRANSCRIPT_PATH = r"C:\AI-BS\MASTER_KNOWLEDGE_VAULT\Full_Chat_Transcript_2026-07-22.md"
TECH_SPEC_PATH = r"C:\AI-BS\MASTER_KNOWLEDGE_VAULT\AI_BS_Master_History_and_Tech_Spec.txt"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()

if os.path.exists(TECH_SPEC_PATH):
    with open(TECH_SPEC_PATH, "r", encoding="utf-8", errors="ignore") as f:
        spec_text = f.read()
    rec_id = f"vault_spec_{uuid.uuid4().hex[:8]}"
    payload = {
        "cluster": "Master Architecture",
        "source": "MASTER_KNOWLEDGE_VAULT/AI_BS_Master_History_and_Tech_Spec.txt",
        "title": "AI-BS Matrix Master History & Core Tech Specs",
        "summary": "Full technical specifications, port assignments, shared memory architecture, and foundational system design principles.",
        "body": spec_text[:3500]
    }
    conn.execute(
        "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
        (rec_id, now_ts, payload["source"], json.dumps(payload))
    )

if os.path.exists(TRANSCRIPT_PATH):
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as f:
        chat_text = f.read(50000)
    rec_id = f"vault_chat_{uuid.uuid4().hex[:8]}"
    payload = {
        "cluster": "Historical Reasoning",
        "source": "MASTER_KNOWLEDGE_VAULT/Full_Chat_Transcript_2026-07-22.md",
        "title": "Early Architecture Development & Problem-Solving Chains",
        "summary": "Conversational problem-solving chains from July 2026 establishing the AI-BS ecosystem foundations.",
        "body": chat_text[:3500]
    }
    conn.execute(
        "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
        (rec_id, now_ts, payload["source"], json.dumps(payload))
    )

conn.commit()
total_vault = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

new_dialogues = [
    {
        "messages": [
            {"role": "user", "content": "What are the core design principles of the AI-BS shared memory ring and zero-copy architecture?"},
            {"role": "assistant", "content": "The AI-BS shared memory architecture utilizes Windows memory-mapped files (SHM Ring Buffers) and named pipes for sub-millisecond IPC. This eliminates JSON serialization overhead between Python FastAPI (Port 8080), Go Gateway (Port 8000), Rust Master Worker, and the React UI."}
        ]
    }
]

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for d in new_dialogues:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_persona = sum(1 for line in f if line.strip())

print(f"[SUCCESS] stehouwer_vault.db updated to {total_vault} total heuristics!")
print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_persona} total dialogue pairs!")