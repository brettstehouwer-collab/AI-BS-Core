import os
import sqlite3
import threading
from typing import Dict, Any, List, Optional

class UnifiedStorageManager:
    """
    Centralized High-Performance SQLite Manager for AI-BS Ecosystem.
    Features:
    - Thread-safe connection caching
    - Automatic PRAGMA mmap_size (256MB memory mapping) & WAL journal mode
    - Cross-database virtual querying via SQLite ATTACH
    """
    _local = threading.local()
    _db_directory = r"C:\AI-BS\database"

    @classmethod
    def get_db_path(cls, db_name: str) -> str:
        if not db_name.endswith(".db"):
            db_name = f"{db_name}.db"
        return os.path.join(cls._db_directory, db_name)

    @classmethod
    def get_connection(cls, db_name: str = "LLM_CrossCheck_Ledger.db") -> sqlite3.Connection:
        if not hasattr(cls._local, "connections"):
            cls._local.connections = {}

        path = cls.get_db_path(db_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if path not in cls._local.connections:
            conn = sqlite3.connect(path, check_same_thread=False)
            try:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                conn.execute("PRAGMA mmap_size = 268435456;") # 256MB mmap
                conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
            except Exception:
                pass
            cls._local.connections[path] = conn

        return cls._local.connections[path]

    @classmethod
    def query(cls, db_name: str, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn = cls.get_connection(db_name)
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.commit()
        return []

    @classmethod
    def list_all_databases(cls) -> List[str]:
        if not os.path.exists(cls._db_directory):
            return []
        return [f for f in os.listdir(cls._db_directory) if f.endswith(".db")]
