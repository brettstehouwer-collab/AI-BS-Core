import sqlite3
import os
import json

DB_DIR = os.path.join(os.path.dirname(__file__), "db")


def get_sqlite_connection(db_path: str, timeout: float = 15.0) -> sqlite3.Connection:
    """
    Returns a hardened, high-throughput SQLite connection optimized for multi-process concurrency:
    - WAL Mode (Write-Ahead Logging) for concurrent reads/writes
    - NORMAL synchronous mode for NVMe write performance
    - 30GB memory mapping (mmap_size) for zero-copy queries
    - 64MB RAM page cache
    - 10-second busy timeout to eliminate 'database is locked' errors
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA mmap_size = 30000000000;")
        conn.execute("PRAGMA cache_size = -64000;")
        conn.execute("PRAGMA busy_timeout = 10000;")
    except Exception:
        pass
    return conn


def get_client_db_path(client_id: str) -> str:
    """Returns the path to the specific client's isolated database."""
    safe_id = "".join([c for c in client_id if c.isalnum()]).lower()
    return os.path.join(DB_DIR, f"client_{safe_id}.db")


def init_client_db(client_id: str):
    """Initializes the database schema for a new client."""
    db_path = get_client_db_path(client_id)
    conn = get_sqlite_connection(db_path)
    cursor = conn.cursor()

    # Store marketing campaigns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marketing_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_address TEXT,
            raw_input TEXT,
            zillow_desc TEXT,
            fb_ad TEXT,
            linkedin_post TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    return db_path


def save_marketing_campaign(
    client_id: str, property_address: str, raw_input: str, results: dict
):
    """Saves generated marketing copy into the client's isolated DB."""
    db_path = get_client_db_path(client_id)
    if not os.path.exists(db_path):
        init_client_db(client_id)

    conn = get_sqlite_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO marketing_campaigns (property_address, raw_input, zillow_desc, fb_ad, linkedin_post)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            property_address,
            raw_input,
            results.get("zillow", ""),
            results.get("facebook", ""),
            results.get("linkedin", ""),
        ),
    )
    campaign_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return campaign_id


def get_client_marketing_history(client_id: str):
    db_path = get_client_db_path(client_id)
    if not os.path.exists(db_path):
        return []

    conn = get_sqlite_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM marketing_campaigns ORDER BY created_at DESC LIMIT 50"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def safe_migrate_multitenant_schemas():
    """Safely migrate databases to include client_id without table locking crashes."""
    db_paths = [
        os.path.join(r"C:\AI-BS", "database", "ai_bs_omnidrive.db"),
        os.path.join(r"C:\AI-BS", "database", "security_events.db"),
    ]
    tables_to_check = ["advertising_leads", "file_state", "security_events"]

    for p in db_paths:
        if os.path.exists(p):
            try:
                conn = get_sqlite_connection(p, timeout=5.0)
                cursor = conn.cursor()
                for table in tables_to_check:
                    try:
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [info[1] for info in cursor.fetchall()]
                        if columns and "client_id" not in columns:
                            cursor.execute("BEGIN TRANSACTION")
                            cursor.execute(
                                f"ALTER TABLE {table} ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'"
                            )
                            conn.commit()
                            print(f"[DB_MANAGER] Added client_id to {table} in {p}")
                    except sqlite3.OperationalError as e:
                        conn.rollback()
                        print(
                            f"[DB_MANAGER] Migration skipped for {table} in {p} due to lock/error: {e}"
                        )
                conn.close()
            except Exception as e:
                print(f"[DB_MANAGER] Migration Error on {p}: {e}")
