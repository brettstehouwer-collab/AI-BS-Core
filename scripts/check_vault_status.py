import sqlite3
import os
import requests

vault_db = r"C:\AI-BS\backend\stehouwer_vault.db"
conn = sqlite3.connect(vault_db)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
print("=== STEHOUWER VAULT DB STATUS ===")
print(f"Database: {vault_db}")
for t in tables:
    count = conn.execute(f"SELECT count(*) FROM {t};").fetchone()[0]
    print(f"  Table '{t}': {count} records")
conn.close()

print("\n=== CHROMADB VECTOR STORE STATUS (Port 8002) ===")
try:
    res = requests.get("http://127.0.0.1:8002/api/v1/collections", timeout=2.0)
    if res.status_code == 200:
        cols = res.json()
        print(f"Collections count: {len(cols)}")
        for c in cols:
            print(f"  Collection: {c.get('name')} (ID: {c.get('id')})")
    else:
        print(f"ChromaDB returned status {res.status_code}")
except Exception as e:
    print(f"ChromaDB check note: {e}")

persona_dataset = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
if os.path.exists(persona_dataset):
    with open(persona_dataset, "r", encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    print(f"\nStehouwer_Persona_Dataset.jsonl: {len(lines)} training dialogue pairs")