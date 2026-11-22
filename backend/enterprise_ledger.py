import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "west_michigan.db")


class SQLiteAgent:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    client_id TEXT DEFAULT 'stehouwer_publishing',
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action TEXT,
                    details TEXT
                )
            """)

            try:
                cursor.execute(
                    "ALTER TABLE ledger ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'"
                )
            except:
                pass

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SQLiteAgent] Init warning: {e}")

    def log_action(self, action: str, details: str = ""):
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ledger (action, details) VALUES (?, ?)", (action, details)
            )

            try:
                cursor.execute(
                    "ALTER TABLE ledger ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'"
                )
            except:
                pass

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SQLiteAgent] Log error: {e}")
