import sqlite3
import os

db_path = r"C:\AI-BS\leads_store.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    status = conn.execute("PRAGMA quick_check;").fetchone()[0]
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print(f"leads_store.db: Status = {status} | Mode = {mode} | Tables = {tables}")
    for t in tables:
        cnt = conn.execute(f"SELECT count(*) FROM {t};").fetchone()[0]
        print(f"  Table '{t}': {cnt} records")
    conn.close()