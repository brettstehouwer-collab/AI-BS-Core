import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all coaches
coaches = cur.execute("SELECT id, name, phone, coach_type, school_name, page FROM rec_debut_excluded_coaches").fetchall()
print(f"Total coaches in rec_debut_excluded_coaches: {len(coaches)}")

# Get all athletes
athletes = cur.execute("SELECT id, name, phone, email, high_school, notes, team_name FROM rec_debut_athletes").fetchall()
print(f"Total athletes: {len(athletes)}")

# Regex for phone numbers in any string
phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')
loose_phone_regex = re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')

# Let's find every single phone number inside high_school or notes or team_name
coach_phones_to_add = []
rows_to_clean = []

for a in athletes:
    aid, aname, aphone, aemail, ahs, anotes, ateam = a
    # check ahs
    if ahs:
        # Check if there is a phone number in ahs
        found = re.findall(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', ahs)
        if found:
            rows_to_clean.append((aid, aname, aphone, ahs, found))

print(f"Found {len(rows_to_clean)} athlete rows where high_school contains coach phone numbers:")
for r in rows_to_clean:
    print(f"  ID {r[0]}: Athlete '{r[1]}' (Phone: {r[2]}) -> HS: '{r[3]}' -> Phones found: {r[4]}")

conn.close()
