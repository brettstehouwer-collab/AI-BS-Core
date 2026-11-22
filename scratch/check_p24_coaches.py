import sqlite3

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check coaches from page 24
p24_coaches = cur.execute("SELECT * FROM rec_debut_excluded_coaches WHERE page = 24").fetchall()
print(f"Coaches from page 24 ({len(p24_coaches)}):")
for c in p24_coaches:
    print(c)

conn.close()
