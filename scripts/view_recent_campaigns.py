import sqlite3
import json

conn = sqlite3.connect('saved_data/rec_debut.db')
c = conn.cursor()
for r in c.execute('SELECT id, created_at, sender_id, total_recipients, successful_count, failed_count, substr(message_body, 1, 80), substr(delivery_details_json, 1, 150) FROM rec_debut_campaigns ORDER BY id DESC LIMIT 10').fetchall():
    print(r)
conn.close()
