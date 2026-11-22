import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Tables found: {tables}")

for t in tables:
    cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"Table {t}: {cnt} rows")

# Check schema of rec_debut_athletes and rec_debut_excluded_coaches
for t in ['rec_debut_athletes', 'rec_debut_excluded_coaches']:
    if t in tables:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f"Columns in {t}: {cols}")

conn.close()
