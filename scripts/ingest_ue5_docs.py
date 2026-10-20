import sqlite3
import json
import time
import uuid

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
UE_DOCS_PATH = r"C:\AI-BS\scratch_ue_docs.txt"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

with open(UE_DOCS_PATH, "r", encoding="utf-8", errors="ignore") as f:
    ue_text = f.read()

now_ts = time.time()
rec_id = f"vault_ue5_{uuid.uuid4().hex[:8]}"

payload = {
    "cluster": "Master Architecture",
    "source": "scratch_ue_docs.txt",
    "title": "Unreal Engine 5.8 Virtual Production & Level Design Pipeline",
    "summary": "Core documentation and workflow principles for UE 5.8 World Partition, Pixel Streaming on Port 8888, Level Sequence generation, and Niagara VFX.",
    "body": ue_text[:3500]
}

conn.execute(
    "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
    (rec_id, now_ts, payload["source"], json.dumps(payload))
)
conn.commit()
total_vault = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

new_turns = [
    {
        "messages": [
            {"role": "user", "content": "How does AI-BS automate Unreal Engine 5.8 for virtual production?"},
            {"role": "assistant", "content": "AI-BS automates UE 5.8 via Python scripts (like BUD.py) and on-demand background execution. It creates Level Sequences, spawns CineCameraActors, sets Directional/Point lights, simulates smart physics props, and streams real-time viewports over WebRTC Pixel Streaming (Port 8888) with H.264 hardware acceleration."}
        ]
    }
]

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for t in new_turns:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_persona = sum(1 for line in f if line.strip())

print(f"[SUCCESS] stehouwer_vault.db updated to {total_vault} total heuristics!")
print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_persona} total dialogue pairs!")