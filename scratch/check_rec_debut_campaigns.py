import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('saved_data/rec_debut.db')
cursor = conn.cursor()

print("--- CAMPAIGNS ---")
cursor.execute("SELECT id, created_at, sender_id, total_recipients, successful_count, failed_count, delivery_details_json FROM rec_debut_campaigns ORDER BY created_at DESC LIMIT 5")
campaigns = cursor.fetchall()
for c in campaigns:
    dt = datetime.fromtimestamp(c[1]).strftime('%Y-%m-%d %H:%M:%S') if c[1] else "N/A"
    print(f"Campaign #{c[0]} at {dt} | Sender: {c[2]} | Total: {c[3]} | Sent: {c[4]} | Failed: {c[5]}")
    try:
        details = json.loads(c[6])
        print(f"  First 3 details: {details[:3]}")
    except Exception:
        pass

print("\n--- RECENT ATHLETES CONTACTED ---")
cursor.execute("SELECT id, name, phone, status, last_messaged_at FROM rec_debut_athletes WHERE last_messaged_at IS NOT NULL ORDER BY last_messaged_at DESC LIMIT 10")
athletes = cursor.fetchall()
for a in athletes:
    dt = datetime.fromtimestamp(a[4]).strftime('%Y-%m-%d %H:%M:%S') if a[4] else "N/A"
    print(f"ID {a[0]}: {a[1]} ({a[2]}) - Status: {a[3]} - Messaged At: {dt}")

print("\n--- TOTAL ATHLETE STATUS COUNTS ---")
cursor.execute("SELECT status, count(*) FROM rec_debut_athletes GROUP BY status")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
