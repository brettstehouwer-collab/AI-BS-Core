import sqlite3
import sys
from datetime import datetime

conn = sqlite3.connect(r"C:\AI-BS\saved_data\rec_debut.db")
c = conn.cursor()
for r in c.execute("SELECT id, athlete_id, ip_address, target_url, created_at FROM rec_debut_tracking_events WHERE athlete_id IN (28, 42)").fetchall():
    dt = datetime.fromtimestamp(r[4]).strftime("%Y-%m-%d %I:%M:%S %p")
    print(r[0], "Athlete:", r[1], "IP:", r[2], "URL:", r[3], "Time:", dt)
conn.close()
