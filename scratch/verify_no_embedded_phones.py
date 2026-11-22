import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

athletes = cur.execute("SELECT id, name, phone, high_school, notes FROM rec_debut_athletes").fetchall()
phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')

embedded = []
for a in athletes:
    hs = a[3] or ""
    notes = a[4] or ""
    m_hs = phone_regex.findall(hs)
    m_notes = phone_regex.findall(notes)
    if m_hs or m_notes:
        embedded.append((a[0], a[1], a[2], hs, notes))

print(f"Athlete rows with embedded phone numbers in hs/notes: {len(embedded)}")
for e in embedded:
    print(e)

conn.close()
