import sqlite3

conn = sqlite3.connect("saved_data/rec_debut.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(id) FROM rec_debut_athlete_replies")
total = cur.fetchone()[0]
print("Total logged replies:", total)

cur.execute("SELECT id, athlete_name, sender_phone, sender_email, subject, reply_body, received_at FROM rec_debut_athlete_replies ORDER BY received_at DESC LIMIT 5")
for row in cur.fetchall():
    print(f"ID {row[0]}: {row[1]} | Phone: {row[2]} | Email: {row[3]}")
    print(f"   Subject: {row[4]}")
    print(f"   Body: {row[5][:100]}...")
conn.close()
