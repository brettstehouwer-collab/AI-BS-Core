import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Let's inspect rows 1 to 25 to see how they look
rows = cur.execute("SELECT id, name, phone, email, high_school, notes, team_name FROM rec_debut_athletes WHERE id <= 25").fetchall()
for r in rows:
    print(r)

conn.close()
