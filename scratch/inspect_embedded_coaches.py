import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("--- ALL 15 ROWS WITH EMBEDDED PHONES IN HIGH SCHOOL ---")
rows = cur.execute("SELECT id, name, phone, email, high_school, notes, team_name FROM rec_debut_athletes").fetchall()
phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')

embedded_rows = []
for r in rows:
    hs = r[4] or ""
    if phone_regex.search(hs):
        embedded_rows.append(r)
        print(f"ID={r[0]}: Name='{r[1]}', Athlete Phone='{r[2]}', HS='{r[4]}', Notes='{r[5]}'")

print(f"\nTotal: {len(embedded_rows)}")

print("\n--- SEARCHING FOR 'COACH' ANYWHERE IN rec_debut_athletes ---")
coach_mentions = cur.execute("""
    SELECT id, name, phone, high_school, notes, team_name 
    FROM rec_debut_athletes 
    WHERE UPPER(name) LIKE '%COACH%' 
       OR UPPER(high_school) LIKE '%COACH%' 
       OR UPPER(notes) LIKE '%COACH%' 
       OR UPPER(team_name) LIKE '%COACH%'
""").fetchall()

print(f"Total rows mentioning 'COACH': {len(coach_mentions)}")
for cm in coach_mentions:
    print(f"ID={cm[0]}: Name='{cm[1]}', Phone='{cm[2]}', HS='{cm[3]}', Notes='{cm[4]}', Team='{cm[5]}'")

conn.close()
