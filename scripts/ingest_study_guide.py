import sqlite3
import json
import time
import uuid

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
STUDY_GUIDE_PATH = r"C:\AI-BS\Stehouwer_LLM_Upgrade_Study_Guide.md"
REACT_PATH = r"C:\AI-BS\ReAct_Agent_Architecture.md"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()

with open(STUDY_GUIDE_PATH, "r", encoding="utf-8", errors="ignore") as f:
    guide_text = f.read()

rec_id = f"vault_guide_{uuid.uuid4().hex[:8]}"
payload = {
    "cluster": "Master Architecture",
    "source": "Stehouwer_LLM_Upgrade_Study_Guide.md",
    "title": "Stehouwer LLM Phased Upgrade & 200GB SQLite Integration Guide",
    "summary": "Core local LLM tool calling architecture, 6 master tool categories, living learning memory, and 200GB SQLite WAL optimizations.",
    "body": guide_text[:3500]
}
conn.execute(
    "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
    (rec_id, now_ts, payload["source"], json.dumps(payload))
)

with open(REACT_PATH, "r", encoding="utf-8", errors="ignore") as f:
    react_text = f.read()

rec_id2 = f"vault_react_{uuid.uuid4().hex[:8]}"
payload2 = {
    "cluster": "Master Architecture",
    "source": "ReAct_Agent_Architecture.md",
    "title": "Autonomous ReAct Agent Loop & Self-Healing Execution",
    "summary": "Polyglot execution sandbox, feedback loops, living learning memory, and cloud UI remote tunneling architecture.",
    "body": react_text[:3500]
}
conn.execute(
    "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
    (rec_id2, now_ts, payload2["source"], json.dumps(payload2))
)

conn.commit()
total_vault = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

new_dialogues = [
    {
        "messages": [
            {"role": "user", "content": "Explain the 6 master tool categories implemented in the AI-BS ReAct agent architecture."},
            {"role": "assistant", "content": "The AI-BS agent architecture implements 6 master tool categories:\n1. Data Retrieval & Knowledge (query_master_memory, discover_and_inspect_databases)\n2. Computation & Logic (execute_sandbox_script Python polyglot sandbox)\n3. File & System Operations (read_sandbox_file, write_sandbox_file)\n4. Enterprise Connectors (Firebase, Cloudflare)\n5. Multimodal Generation (generate_comfy_image on Port 8189, LLaVA vision analysis)\n6. Meta-Cognitive Self-Correction (ScavengerToolAgent auto-healing loops)."}
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