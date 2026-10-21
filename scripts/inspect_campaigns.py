import sys
import sqlite3
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("saved_data/rec_debut.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM rec_debut_campaigns ORDER BY id DESC LIMIT 10")
for r in c.fetchall():
    dt = datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else "N/A"
    print(f"Campaign ID: {r['id']} | Time: {dt} | Total: {r['total_recipients']} | Success: {r['successful_count']} | Fail: {r['failed_count']}")
    print(f"Message snippet: {r['message_body'][:150]}...\n")

if "rec_debut_dispatches" in [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    c.execute("SELECT * FROM rec_debut_dispatches ORDER BY id DESC LIMIT 10")
    print("Recent dispatches:")
    for d in c.fetchall():
        print(dict(d))

conn.close()
