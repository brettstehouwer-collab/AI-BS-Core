import sqlite3
import json

conn = sqlite3.connect("saved_data/rec_debut.db")
c = conn.cursor()
c.execute("SELECT id, created_at, sender_id, total_recipients, successful_count, failed_count, delivery_details_json FROM rec_debut_campaigns ORDER BY id DESC LIMIT 1")
row = c.fetchone()
print(f"Campaign #{row[0]} | Total: {row[3]} | Success: {row[4]} | Failed: {row[5]}")
if row[6]:
    details = json.loads(row[6])
    print(f"Total delivery details entries: {len(details)}")
    for d in details:
        print(d)

conn.close()
