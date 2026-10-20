import sqlite3
import json
import time
import uuid

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

# Ingest Tony Noto Letter
noto_letter_path = r"C:\AI-BS\shared_cloud_drive\Noto\New_Document.md"
with open(noto_letter_path, "r", encoding="utf-8") as f:
    letter_text = f.read()

entry_id = f"vault_noto_{uuid.uuid4().hex[:8]}"
now_ts = time.time()

entry_payload = {
    "cluster": "Business & Hospitality",
    "source": "shared_cloud_drive/Noto/New_Document.md",
    "title": "Tony Noto Proposal - Real-Time Multi-Bar Inventory & Mobile POS Sync",
    "body": letter_text,
    "summary": "Personal pitch from Brett Stehouwer to Tony Noto explaining real-time bottle and keg inventory tracking across multiple bars."
}

conn.execute(
    "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
    (entry_id, now_ts, entry_payload["source"], json.dumps(entry_payload))
)
conn.commit()
v_count = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

# Append to Stehouwer Persona Dataset
new_pairs = [
    {
        "messages": [
            {"role": "user", "content": "How did you propose solving the bar stock and inventory problem to Tony Noto?"},
            {"role": "assistant", "content": "Here is the exact proposal I shared with Tony Noto:\n\n" + letter_text}
        ]
    },
    {
        "messages": [
            {"role": "user", "content": "What is the core feature of the Noto's bar management software module?"},
            {"role": "assistant", "content": "The core feature is real-time multi-bar bottle and keg inventory tracking. When a bartender or barback grabs a bottle (like Tito's upstairs or downstairs), they log it on their phone or bar screen. It instantly syncs stock levels and sends notifications to staff, eliminating the 20-minute search across stockrooms."}
        ]
    }
]

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for p in new_pairs:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_lines = sum(1 for line in f if line.strip())

print(f"[SUCCESS] stehouwer_vault.db updated to {v_count} records!")
print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_lines} dialogue pairs!")