import sys
from pathlib import Path
import sqlite3

# Step A: Verify C:/AI-BS/backend/aibs_master.db
backend_db = Path("C:/AI-BS/backend/aibs_master.db")
conn_b = sqlite3.connect(backend_db)
backend_mode = conn_b.execute("PRAGMA journal_mode;").fetchone()[0]
backend_qc = conn_b.execute("PRAGMA quick_check;").fetchall()
conn_b.close()
print(f"Backend DB journal_mode: {backend_mode}, quick_check: {backend_qc}")
assert backend_mode.lower() == "wal", f"Expected wal, got {backend_mode}"
assert backend_qc == [("ok",)], f"Expected ok, got {backend_qc}"

# Step B: Source pre-check C:/AI-BS/database/aibs_master.db
cdz_db = Path("C:/AI-BS/database/aibs_master.db")
conn_c = sqlite3.connect(cdz_db)
cdz_mode_pre = conn_c.execute("PRAGMA journal_mode;").fetchone()[0]
cdz_qc_pre = conn_c.execute("PRAGMA quick_check;").fetchall()
conn_c.close()
print(f"CDZ DB pre-activation journal_mode: {cdz_mode_pre}, quick_check: {cdz_qc_pre}")
assert cdz_qc_pre == [("ok",)], f"Expected ok, got {cdz_qc_pre}"

# Step C: Use SQLiteStore to safely activate WAL with backup
sys.path.insert(0, "C:/AI-BS")
sys.path.insert(0, "C:/AI-BS/backend")
from backend.db.swarm_sqlite import SQLiteStore, SQLitePolicy

backup_path = Path("C:/AI-BS/database/aibs_master_backup_pre_wal.db")
if backup_path.exists():
    print(f"Warning: backup {backup_path} already exists")

store = SQLiteStore(Path("C:/AI-BS"), "cdz_audit")
created_backup = store.activate(backup_path, allow_activation=True)
print(f"Backup created at: {created_backup}")

# Check metrics
metrics = store.metrics()
print(f"Store metrics: {metrics}")
assert metrics["journal_mode"].lower() == "wal"

# Close store cleanly
drained = store.close(timeout=10)
print(f"Store drained & closed: {drained}")

# Step D: Verify post-activation independently
conn_post = sqlite3.connect(cdz_db)
post_mode = conn_post.execute("PRAGMA journal_mode;").fetchone()[0]
post_qc = conn_post.execute("PRAGMA quick_check;").fetchall()
post_tables = conn_post.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
conn_post.close()
print(f"CDZ DB post-activation journal_mode: {post_mode}, quick_check: {post_qc}, tables: {post_tables}")
assert post_mode.lower() == "wal"
assert post_qc == [("ok",)]

# Step E: Verify backup integrity independently
conn_bak = sqlite3.connect(backup_path)
bak_mode = conn_bak.execute("PRAGMA journal_mode;").fetchone()[0]
bak_qc = conn_bak.execute("PRAGMA quick_check;").fetchall()
bak_tables = conn_bak.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
conn_bak.close()
print(f"Backup DB journal_mode: {bak_mode}, quick_check: {bak_qc}, tables: {bak_tables}")
assert bak_qc == [("ok",)]
assert bak_tables == post_tables

print("WAL activation on database/aibs_master.db completed with 100% integrity!")
