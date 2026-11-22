import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

athletes = cur.execute("SELECT id, name, phone, high_school FROM rec_debut_athletes").fetchall()

height_pattern = re.compile(r'^[5-7]-\d+\s+')
with_height = []
for a in athletes:
    hs = a[3] or ""
    if height_pattern.match(hs):
        with_height.append((a[0], a[1], a[2], hs))

print(f"Total rows with height prefix in high_school: {len(with_height)}")
for r in with_height[:15]:
    print(f"ID={r[0]}, Name='{r[1]}', HS='{r[3]}'")

conn.close()
