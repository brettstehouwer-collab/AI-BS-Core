import sqlite3
import json
import time
import uuid

VAULT_DB_PATH = r"C:\AI-BS\backend\stehouwer_vault.db"
PERSONA_DATASET_PATH = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
DIRECTOR_PATH = r"C:\AI-BS\JuliesPlace\julies_place_master_director.py"

conn = sqlite3.connect(VAULT_DB_PATH, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=10000;")

with open(DIRECTOR_PATH, "r", encoding="utf-8", errors="ignore") as f:
    director_text = f.read()

now_ts = time.time()
rec_id = f"vault_julies_place_{uuid.uuid4().hex[:8]}"

payload = {
    "cluster": "Screenwriting & Creative",
    "source": "JuliesPlace/julies_place_master_director.py",
    "title": "Julie's Place - Master World & Virtual Production Director",
    "summary": "Procedural Unreal Engine 5 virtual production director script for Julie's Place S1E1 & S1E2 (The Writing's On The Wall), camera positioning, lighting, and MetaHuman scene staging.",
    "body": director_text[:3500]
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
            {"role": "user", "content": "How does the AI-BS director build the virtual production set for Julie's Place in Unreal Engine?"},
            {"role": "assistant", "content": "The AI-BS virtual production director (julies_place_master_director.py) generates Level Sequences under /Game/JuliesPlace/Cinematics, spawns Sun DirectionalLights and SkyLights for exterior environments, configures CineCameraActors for cinematic close-ups and wide angles, places smart physics props, and injects MetaHuman facial control rigs."}
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