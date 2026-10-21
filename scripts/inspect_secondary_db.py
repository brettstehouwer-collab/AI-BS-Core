import sys
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect(r"C:\Recreational-Debut\saved_data\rec_debut.db")
c = conn.cursor()
print("=== RECENT REPLIES IN SECONDARY DB ===")
for r in c.execute("SELECT id, athlete_id, athlete_name, sender_phone, reply_body, message_id_hash FROM rec_debut_athlete_replies ORDER BY id DESC LIMIT 3").fetchall():
    print(r)
conn.close()
