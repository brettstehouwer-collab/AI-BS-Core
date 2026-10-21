import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("saved_data/rec_debut.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("PRAGMA table_info(rec_debut_dispatches)")
cols = [r["name"] for r in c.fetchall()]
print("rec_debut_dispatches columns:", cols)

c.execute("SELECT COUNT(*) FROM rec_debut_dispatches")
print("Total rows:", c.fetchone()[0])

c.execute("SELECT * FROM rec_debut_dispatches ORDER BY id DESC LIMIT 5")
for r in c.fetchall():
    print(dict(r))

conn.close()
