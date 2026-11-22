import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cols = [c[1] for c in cur.execute("PRAGMA table_info(rec_debut_campaigns)").fetchall()]
print(f"Columns in rec_debut_campaigns: {cols}")

campaigns = cur.execute("SELECT * FROM rec_debut_campaigns ORDER BY id DESC").fetchall()
print(f"Total campaigns: {len(campaigns)}")
for c in campaigns:
    print(dict(zip(cols, c)))

status_counts = cur.execute("SELECT status, count(*) FROM rec_debut_athletes GROUP BY status").fetchall()
print(f"\nAthlete status counts: {status_counts}")

total_messaged = cur.execute("SELECT count(*) FROM rec_debut_athletes WHERE last_messaged_at IS NOT NULL").fetchone()[0]
print(f"Total messaged athletes: {total_messaged}")

conn.close()
