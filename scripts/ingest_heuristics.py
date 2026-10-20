import sqlite3
import json
import time
import uuid
import os

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
RULES_PATH = r"C:\AI-BS\Heuristics\learned_rules.md"
ARCH_REPORT_PATH = r"C:\AI-BS\Documents\AI-BS_Technical_Architecture_Report_v1.2.md"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()

if os.path.exists(RULES_PATH):
    with open(RULES_PATH, "r", encoding="utf-8", errors="ignore") as f:
        rules_text = f.read()
    rec_id = f"vault_rules_{uuid.uuid4().hex[:8]}"
    payload = {
        "cluster": "Master Architecture",
        "source": "Heuristics/learned_rules.md",
        "title": "Autonomous Heuristics & Ecosystem Operating Directives",
        "summary": "Learned operational guidelines, zero-drift path safety, non-blocking developer rules, and state preservation protocols.",
        "body": rules_text[:3500]
    }
    conn.execute(
        "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
        (rec_id, now_ts, payload["source"], json.dumps(payload))
    )

if os.path.exists(ARCH_REPORT_PATH):
    with open(ARCH_REPORT_PATH, "r", encoding="utf-8", errors="ignore") as f:
        arch_text = f.read()
    rec_id2 = f"vault_arch_report_{uuid.uuid4().hex[:8]}"
    payload2 = {
        "cluster": "Master Architecture",
        "source": "Documents/AI-BS_Technical_Architecture_Report_v1.2.md",
        "title": "Technical Architecture Report v1.2",
        "summary": "Detailed technical report covering multi-tenant partitioning, WebSocket signaling, and hybrid cloud-edge topologies.",
        "body": arch_text[:3500]
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
            {"role": "user", "content": "What are the core state preservation rules enforced in AI-BS learned heuristics?"},
            {"role": "assistant", "content": "The AI-BS learned heuristics enforce strict state preservation: zero-drift path verification across C: and E: drives, atomic SQLite transactions with WAL journal mode, automatic saving of checkpoints (SAVED_CHECKPOINT.md), and continuous synchronization of master architectural ledgers without breaking active execution pipelines."}
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