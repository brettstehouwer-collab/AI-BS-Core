import sqlite3
import json
import time
import uuid
import re

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
GEMINI_WORD_PATH = r"C:\AI-BS\Brett's gemini word.md"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

now_ts = time.time()
new_dialogues = []

with open(GEMINI_WORD_PATH, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read(500000) # Read first 500KB of rich entries

entries = re.split(r"\n###\s+Entry\s+\d+", text)
print(f"Parsed {len(entries)} deep research entries from Brett's Gemini Word.")

for i, entry in enumerate(entries[1:25]):
    lines = [l.strip() for l in entry.strip().splitlines() if l.strip()]
    if not lines:
        continue
    title = lines[0][:80]
    body = "\n".join(lines[1:30])
    
    rec_id = f"vault_gemini_{uuid.uuid4().hex[:8]}"
    payload = {
        "cluster": "Historical Reasoning",
        "source": "Brett's gemini word.md",
        "title": f"Gemini Research - {title}",
        "summary": f"Analytical research extract on {title} covering macroeconomic and technical frameworks.",
        "body": body[:2000]
    }
    
    conn.execute(
        "INSERT OR REPLACE INTO vault_data (id, timestamp, source, data) VALUES (?, ?, ?, ?);",
        (rec_id, now_ts, payload["source"], json.dumps(payload))
    )
    
    new_dialogues.append({
        "messages": [
            {"role": "user", "content": f"Summarize the analytical findings on '{title}' from our research archives."},
            {"role": "assistant", "content": f"Analytical summary for '{title}':\n\n{body[:1200]}"}
        ]
    })

conn.commit()
total_vault = conn.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
conn.close()

with open(PERSONA_DATASET_PATH, "a", encoding="utf-8") as f:
    for d in new_dialogues:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

with open(PERSONA_DATASET_PATH, "r", encoding="utf-8") as f:
    total_persona = sum(1 for line in f if line.strip())

print(f"[SUCCESS] stehouwer_vault.db updated to {total_vault} total heuristics!")
print(f"[SUCCESS] Stehouwer_Persona_Dataset.jsonl updated to {total_persona} total dialogue pairs!")