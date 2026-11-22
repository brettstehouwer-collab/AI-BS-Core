import sqlite3
import concurrent.futures
import time
import os

MASTER_DB = "C:/AI-BS/backend/aibs_master.db"

def test_integrity():
    print(f"[*] Testing {MASTER_DB} Integrity...")
    conn = sqlite3.connect(MASTER_DB, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    cur = conn.cursor()
    
    # 1. PRAGMA integrity check
    cur.execute("PRAGMA integrity_check;")
    res = cur.fetchone()[0]
    assert res == "ok", f"Integrity check failed: {res}"
    print(f"    [+] PRAGMA integrity_check: {res}")
    
    # 2. Table count & row validation
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"    [+] Verified {len(tables)} tables exist in master DB.")
    assert len(tables) >= 20, f"Expected >= 20 tables, got {len(tables)}"
    
    # 3. Verify client_id in all tables
    for t in tables:
        cur.execute(f"PRAGMA table_info('{t}')")
        cols = [c[1] for c in cur.fetchall()]
        assert "client_id" in cols, f"Table {t} missing client_id column!"
    print(f"    [+] All {len(tables)} tables enforce client_id schema attribute.")
    
    conn.close()

def worker_read(i):
    conn = sqlite3.connect(MASTER_DB, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM assets")
    cnt1 = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM properties")
    cnt2 = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM accounting_entries")
    cnt3 = cur.fetchone()[0]
    conn.close()
    return (i, cnt1, cnt2, cnt3)

def worker_write(i):
    conn = sqlite3.connect(MASTER_DB, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    cur = conn.cursor()
    # Insert a temporary test entry into accounting_entries and remove it
    now = time.time()
    cur.execute("""
        INSERT INTO accounting_entries (date, category, description, entry_type, amount, created_at, updated_at, client_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (f"2026-09-07", "Test", f"Concurrency Test Thread {i}", "expense", 1.00, now, now, "test_client"))
    row_id = cur.lastrowid
    conn.commit()
    
    # Clean up test row
    cur.execute("DELETE FROM accounting_entries WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
    return (i, row_id)

def test_concurrency():
    print(f"\n[*] Testing Multi-Threaded Read/Write Concurrency...")
    start_t = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        read_futures = [executor.submit(worker_read, i) for i in range(20)]
        write_futures = [executor.submit(worker_write, i) for i in range(10)]
        
        for f in concurrent.futures.as_completed(read_futures + write_futures):
            f.result()
            
    dur = time.perf_counter() - start_t
    print(f"    [+] 30 parallel read/write threads completed in {dur:.2f}s with 0 lock errors.")

if __name__ == "__main__":
    test_integrity()
    test_concurrency()
    print("\n[SUCCESS] Unified aibs_master.db validation complete.")
