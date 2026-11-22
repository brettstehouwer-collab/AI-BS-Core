import sqlite3
import hashlib
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")


class SemanticCache:
    def __init__(self, db_path="telemetry_checkpoint.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS semantic_cache (
                        prompt_hash TEXT PRIMARY KEY,
                        prompt_text TEXT,
                        cached_response TEXT,
                        hit_count INTEGER DEFAULT 0
                    )
                """)
                # WAL mode to prevent locking during parallel orchestrator runs
                conn.execute("PRAGMA journal_mode=WAL;")
        except Exception as e:
            logging.error(f"[SEMANTIC CACHE] DB Init failed: {e}")

    def _hash_prompt(self, prompt: str) -> str:
        # A basic hash; for true semantic, we would use Nomadic-Embeddings here.
        # To avoid heavy compute loads right now, we use deterministic SHA256
        # mapping.
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    def get(self, prompt: str):
        phash = self._hash_prompt(prompt)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cached_response FROM semantic_cache WHERE prompt_hash = ?", (phash,))
                row = cursor.fetchone()
                if row:
                    logging.info(
                        f"[SEMANTIC CACHE] Cache Hit! Saving GPU compute cycles.")
                    # Increment hit counter
                    conn.execute(
                        "UPDATE semantic_cache SET hit_count = hit_count + 1 WHERE prompt_hash = ?",
                        (phash,
                         ))
                    return json.loads(row[0])
        except Exception as e:
            logging.warning(f"[SEMANTIC CACHE] Read error: {e}")
        return None

    def set(self, prompt: str, response: dict):
        phash = self._hash_prompt(prompt)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO semantic_cache (prompt_hash, prompt_text, cached_response) VALUES (?, ?, ?)",
                    (phash, prompt, json.dumps(response))
                )
            logging.info("[SEMANTIC CACHE] Response securely cached to NVMe.")
        except Exception as e:
            logging.warning(f"[SEMANTIC CACHE] Write error: {e}")


if __name__ == "__main__":
    pass
