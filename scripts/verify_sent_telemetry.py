import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path("saved_data/rec_debut.db")
conn = sqlite3.connect(str(db_path))
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM rec_debut_athletes")
total_athletes = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")
contacted_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")
pending_count = c.fetchone()[0]

c.execute("SELECT id, name, email, phone, last_messaged_at, status FROM rec_debut_athletes WHERE status = 'Contacted' ORDER BY last_messaged_at DESC LIMIT 10")
recent_contacted = c.fetchall()

print(f"Total Athletes in DB:   {total_athletes}")
print(f"Contacted (Verified):   {contacted_count} ({contacted_count / total_athletes * 100:.1f}%)")
print(f"Pending Remaining:      {pending_count}")
print("\nMost Recently Sent & Verified in DB:")
for r in recent_contacted:
    dt = datetime.fromtimestamp(r[4]).strftime('%Y-%m-%d %H:%M:%S') if r[4] else 'N/A'
    print(f" [OK] ID {r[0]}: {r[1]} | {r[2]} | {r[3]} | Sent: {dt} | Status: {r[5]}")

conn.close()
