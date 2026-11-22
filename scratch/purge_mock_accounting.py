import sqlite3
import os

db_paths = [
    r"C:\AI-BS\backend\aibs_master.db",
    r"C:\AI-BS\backend\stehouwer_accounting.db"
]

for p in db_paths:
    if os.path.exists(p):
        conn = sqlite3.connect(p)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM crypto_transfers")
            print(f"Purged {c.rowcount} row(s) from {p}")
            conn.commit()
        except Exception as e:
            print(f"Notice for {p}: {e}")
        conn.close()

print("ZERO-MOCK PURGE COMPLETE.")
