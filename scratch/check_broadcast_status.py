import sqlite3
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. Check campaigns
campaigns = cur.execute("SELECT id, name, target_count, successful_count, failed_count, caller_id, created_at, status FROM rec_debut_campaigns ORDER BY id DESC").fetchall()
print(f"Total campaigns recorded: {len(campaigns)}")
for c in campaigns:
    print(f"Campaign: {c}")

# 2. Check athletes status distribution
status_counts = cur.execute("SELECT status, count(*) FROM rec_debut_athletes GROUP BY status").fetchall()
print(f"\nAthlete status counts: {status_counts}")

# 3. Check recently messaged athletes
recent_messaged = cur.execute("SELECT id, name, phone, status, last_messaged_at FROM rec_debut_athletes WHERE last_messaged_at IS NOT NULL ORDER BY last_messaged_at DESC LIMIT 20").fetchall()
print(f"\nRecently messaged athletes ({len(recent_messaged)}):")
for r in recent_messaged:
    print(r)

# 4. Total athletes with last_messaged_at
total_messaged = cur.execute("SELECT count(*) FROM rec_debut_athletes WHERE last_messaged_at IS NOT NULL").fetchone()[0]
print(f"\nTotal athletes with last_messaged_at populated: {total_messaged}")

conn.close()
