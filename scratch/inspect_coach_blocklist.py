import sqlite3

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

rows = cur.execute("SELECT id, name, phone, coach_type, team_name, school_name FROM rec_debut_excluded_coaches LIMIT 20").fetchall()
for r in rows:
    print(r)

null_names = cur.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches WHERE name IS NULL OR name = ''").fetchone()[0]
print(f"Coaches with NULL or empty name: {null_names}")

sample_non_null = cur.execute("SELECT id, name, phone, coach_type, team_name, school_name FROM rec_debut_excluded_coaches WHERE name IS NOT NULL AND name != '' LIMIT 20").fetchall()
print(f"Sample non-null names ({len(sample_non_null)}):")
for r in sample_non_null:
    print(r)

conn.close()
