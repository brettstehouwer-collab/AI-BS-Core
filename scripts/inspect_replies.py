import sqlite3
import sys
from datetime import datetime

conn = sqlite3.connect(r"C:\AI-BS\saved_data\rec_debut.db")
c = conn.cursor()
print("=== ATHLETE REPLIES ===")
for r in c.execute("SELECT id, athlete_id, athlete_name, sender_phone, reply_body, received_at FROM rec_debut_athlete_replies").fetchall():
    dt = datetime.fromtimestamp(r[5]).strftime("%Y-%m-%d %I:%M:%S %p")
    print(f"ID {r[0]}: Athlete #{r[1]} ({r[2]}) - {r[3]}")
    print(f"  Time: {dt}")
    print(f"  Message: {r[4]}")
    print()
conn.close()
