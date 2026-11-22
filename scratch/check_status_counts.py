import sqlite3

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

counts = cur.execute("SELECT status, count(*) FROM rec_debut_athletes GROUP BY status").fetchall()
print(f"Athlete status counts: {counts}")

total = cur.execute("SELECT count(*) FROM rec_debut_athletes").fetchone()[0]
print(f"Total athletes: {total}")

conn.close()
