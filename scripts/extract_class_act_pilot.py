import os
import json
import time
import uuid
import sqlite3
import fitz # PyMuPDF

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
PDF_PATH = r"C:\AI-BS\Workflows for comfy ui\S1E1-3 Class Act Pilot.pdf"

doc = fitz.open(PDF_PATH)
full_text = ""
for page in doc:
    full_text += page.get_text() + "\n"
print(f"Extracted {len(full_text)} characters from {len(doc)} pages of 'S1E1-3 Class Act Pilot.pdf'")

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()
rec_id = f"vault_pilot_{uuid.uuid4().hex[:8]}"

payload = {
    "cluster": "Screenwriting & Creative",
    "source": "Workflows for comfy ui/S1E1-3 Class Act Pilot.pdf",
    "title": "Class Act TV Pilot (Episodes 1-3) - Teleplay & Screenplay Treatment",
    "summary": "Multi-episode television pilot teleplay, character relationship dynamics, comedic banter, and dialogue sequences.",
    "body": full_text[:4000]
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
            {"role": "user", "content": "Provide the opening scene breakdown and tone for the 'Class Act' television pilot."},
            {"role": "assistant", "content": f"Opening scene and character setup for Class Act Pilot:\n\n{full_text[:1800]}"}
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