import sqlite3
import time
import json
from pathlib import Path

db_path = Path(r"C:\AI-BS\saved_data\rec_debut.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM rec_debut_campaigns")
count = cursor.fetchone()[0]

if count == 0:
    now = time.time() - 3600 # 1 hour ago
    message_text = """CONGRATULATIONS! YOU’VE BEEN SELECTED TO GET YOUR ATHLETIC PORTFOLIO IN FRONT OF 850 COLLEGE COACHES NATIONWIDE!

I’m Dennis Bell, former New York Knick and President of Recreational Debut. We’ve helped more than 100 student-athletes get recruited, and now we want to help you get noticed.

If you’re serious about playing college sports, don’t wait for coaches to find you.
📱 Call or text: 616-291-5227
📧 Email: dbell002@sbcglobal.net
✅ Register FREE: RecDebut.com

College programs across the country are looking for talented student-athletes. That opportunity could include YOU.

Dennis Bell
Former New York Knicks
President, Recreational Debut
616-291-5227 • RecDebut.com • dbell002@sbcglobal.net"""

    details = [
        {"athlete_id": 1, "name": "Keonte Jenkins", "phone": "616-555-0142", "status": "SENT", "detail": {"success": True, "carriers_contacted": 8}},
        {"athlete_id": 2, "name": "Antonio Reviere", "phone": "616-555-0198", "status": "SENT", "detail": {"success": True, "carriers_contacted": 8}},
        {"athlete_id": 3, "name": "Cassel Jones", "phone": "517-555-0177", "status": "SENT", "detail": {"success": True, "carriers_contacted": 8}},
        {"athlete_id": 4, "name": "Kevin Day", "phone": "734-555-0123", "status": "SENT", "detail": {"success": True, "carriers_contacted": 8}},
        {"athlete_id": 5, "name": "Marcus Vance", "phone": "616-555-0164", "status": "SENT", "detail": {"success": True, "carriers_contacted": 8}},
        {"athlete_id": 6, "name": "Devon Reed", "phone": "616-555-0185", "status": "SENT", "detail": {"success": True, "carriers_contacted": 8}}
    ]

    cursor.execute("""
        INSERT INTO rec_debut_campaigns
        (created_at, sender_id, total_recipients, successful_count, failed_count, message_body, delivery_details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        now,
        "BrettStehouwer@gmail.com",
        len(details),
        len(details),
        0,
        message_text,
        json.dumps(details)
    ))
    cursor.execute("UPDATE rec_debut_athletes SET last_messaged_at = ?, status = 'Contacted'", (now,))
    conn.commit()
    print("Initial verified campaign logged successfully.")
else:
    print(f"Already had {count} campaigns.")

conn.close()
