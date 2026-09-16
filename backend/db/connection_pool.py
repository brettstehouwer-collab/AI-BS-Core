import os
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger("DBConnectionPool")

BASE_DB_DIR = "C:/AI-BS"

def get_sqlite_connection(db_name: str, base_dir: Optional[str] = None) -> sqlite3.Connection:
    target_dir = base_dir or BASE_DB_DIR
    if not db_name.endswith(('.db', '.sqlite', '.sqlite3')):
        db_name += '.db'
    db_path = os.path.join(target_dir, db_name) if not os.path.isabs(db_name) else db_name

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    conn.execute("PRAGMA mmap_size=268435456;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.row_factory = sqlite3.Row
    return conn
