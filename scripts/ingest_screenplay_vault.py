import sqlite3
import json
import time
import uuid
import os

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
SCREENPLAY_DIR = r"C:\AI-BS\screenplay_projects"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()
new_dialogue_turns = []

projects = [
    ("The Judge Made Him Go!", "The Judge Made Him Go! (Screenplay Adaptation)", "Dramatic screenplay treatment and character progression adapted for screen production."),
    ("THE BOOK- The Sagal's", "The Book - The Sagals (Narrative Treatment)", "Historical character arcs, dialogue exchanges, and cinematic scene transitions."),
    ("NTY-PDF BOOK TO SCRIPT TEST", "NTY Screenplay Treatment & Book Adaptation", "Comprehensive multi-scene script adaptation from literary source text to FinalDraft structure.")
]

for pdir, title, desc in projects:
    fountain_path = os.path.join(SCREENPLAY_DIR, pdir, "screenplay.fountain")
    if os.path.exists(fountain_path):
        with open(fountain_path, "r", encoding="utf-8", errors="ignore") as f:
            script_text = f.read()
        
        entry = {
            "cluster": "Screenwriting & Creative",
            "source": f"screenplay_projects/{pdir}/screenplay.fountain",
            "title": title,
            "summary": desc,
            "body": script_text[:3500]
        }
        
        rec_id = f"vault_script_{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
            (rec_id, now_ts, entry["source"], json.dumps(entry))
        )
        
        new_dialogue_turns.append({
            "messages": [
                {"role": "user", "content": f"How is the scene and character dynamic structured in '{title}'?"},
                {"role": "assistant", "content": f"Here is the screenplay breakdown and scene progression for '{title}':\n\n{script_text[:1800]}"}
            ]
        })

conn.commit()
total_vault = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for turn in new_dialogue_turns:
        f.write(json.dumps(turn, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_persona = sum(1 for line in f if line.strip())

print(f"[SUCCESS] stehouwer_vault.db updated to {total_vault} total heuristics!")
print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_persona} total dialogue pairs!")