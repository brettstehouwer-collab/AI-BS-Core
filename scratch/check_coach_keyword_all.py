import sqlite3

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

matches = cur.execute("""
    SELECT id, name, phone, high_school, notes, team_name 
    FROM rec_debut_athletes 
    WHERE UPPER(name) LIKE '%COACH%' 
       OR UPPER(high_school) LIKE '%COACH%' 
       OR UPPER(notes) LIKE '%COACH%' 
       OR UPPER(team_name) LIKE '%COACH%'
""").fetchall()

print(f"Athlete rows mentioning 'COACH': {len(matches)}")
for m in matches:
    print(m)

conn.close()
