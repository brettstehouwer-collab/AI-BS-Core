import sqlite3
import os

db_path = r'C:\AI-BS\saved_data\rec_debut.db'
if os.path.exists(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    total = cur.execute("SELECT COUNT(1) FROM rec_debut_athletes").fetchone()[0]
    contacted = cur.execute("SELECT COUNT(1) FROM rec_debut_athletes WHERE status = 'Contacted'").fetchone()[0]
    pending = cur.execute("SELECT COUNT(1) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending'").fetchone()[0]
    print(f"RecDebut DB verified: Total={total}, Contacted={contacted}, Pending={pending}")
else:
    print(f"File not found: {db_path}")
