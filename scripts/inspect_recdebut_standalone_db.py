import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_path = r"C:\Recreational-Debut\recdebut_athletes.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r["name"] for r in c.fetchall()]
print("Tables in C:\\Recreational-Debut\\recdebut_athletes.db:", tables)

for t in tables:
    c.execute(f"SELECT COUNT(*) FROM {t}")
    print(f" - {t}: {c.fetchone()[0]} rows")

if "rec_debut_athlete_replies" in tables:
    c.execute("SELECT * FROM rec_debut_athlete_replies")
    for r in c.fetchall():
        print("Reply:", dict(r))

conn.close()
