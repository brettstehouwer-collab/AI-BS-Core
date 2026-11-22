import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

athletes = cur.execute("SELECT id, name, phone, email, sport, high_school, grad_year, city_state, status, notes, team_name FROM rec_debut_athletes").fetchall()

print(f"Total athletes: {len(athletes)}")

# 1. Check for any phone numbers in high_school, notes, or name
phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')

embedded_phones = []
for a in athletes:
    aid, aname, aphone, aemail, asport, ahs, agrad, acity, astat, anotes, ateam = a
    for field_name, field_val in [('high_school', ahs), ('notes', anotes), ('name', aname), ('team_name', ateam)]:
        if field_val:
            m = phone_regex.findall(str(field_val))
            if m:
                embedded_phones.append((aid, aname, aphone, field_name, field_val, m))

print(f"Fields with embedded phone numbers: {len(embedded_phones)}")
for ep in embedded_phones:
    print(f"  ID {ep[0]}: Athlete '{ep[1]}' (Phone: {ep[2]}) in {ep[3]}: '{ep[4]}' -> Found: {ep[5]}")

# 2. Check for coach keywords across ALL fields
coach_kws = ['COACH', 'HEAD COACH', 'ASST', 'ASSISTANT', 'DIRECTOR', 'TRAINER', 'STAFF', 'COORDINATOR']
kw_matches = []
for a in athletes:
    aid, aname, aphone, aemail, asport, ahs, agrad, acity, astat, anotes, ateam = a
    for field_name, field_val in [('name', aname), ('high_school', ahs), ('notes', anotes), ('team_name', ateam)]:
        if field_val:
            val_upper = str(field_val).upper()
            for kw in coach_kws:
                if re.search(r'\b' + kw + r'\b', val_upper):
                    kw_matches.append((aid, aname, aphone, field_name, kw, field_val))
                    break

print(f"\nFields matching coach keywords: {len(kw_matches)}")
for km in kw_matches:
    print(f"  ID {km[0]}: Athlete '{km[1]}' in {km[3]} (keyword '{km[4]}'): '{km[5]}'")

conn.close()
