import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

def norm_phone(p):
    if not p:
        return ""
    digits = re.sub(r"\D", "", str(p))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits

# 1. Load all excluded coach phones and names
coach_rows = cur.execute("SELECT id, name, phone, coach_type, team_name, school_name FROM rec_debut_excluded_coaches").fetchall()
coach_phones = set()
coach_names = set()
for r in coach_rows:
    p = norm_phone(r[2])
    if p:
        coach_phones.add(p)
    if r[1]:
        coach_names.add(r[1].strip().upper())

print(f"Total excluded coaches in blocklist: {len(coach_rows)}")
print(f"Unique coach phone numbers: {len(coach_phones)}")

# 2. Check athletes
athlete_rows = cur.execute("SELECT id, name, phone, email, sport, high_school, grad_year, city_state, status, notes, team_name FROM rec_debut_athletes").fetchall()
print(f"Total athletes on roster: {len(athlete_rows)}")

phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')

direct_phone_matches = []
name_matches = []
coach_keyword_athletes = []
phones_in_high_school = []
phones_in_notes = []
phones_in_team = []

coach_keywords = ["COACH", "HEAD COACH", "ASST", "ASSISTANT COACH", "DIRECTOR", "COORDINATOR", "STAFF", "TRAINER"]

for a in athlete_rows:
    aid, aname, aphone, aemail, asport, ahs, agrad, acity, astat, anotes, ateam = a
    norm_ap = norm_phone(aphone)
    
    # Direct phone collision
    if norm_ap and norm_ap in coach_phones:
        direct_phone_matches.append(a)
        
    # Name collision
    clean_name = (aname or "").strip().upper()
    if clean_name and clean_name in coach_names:
        name_matches.append(a)
        
    # Coach keyword in name
    for kw in coach_keywords:
        if kw in clean_name:
            coach_keyword_athletes.append((kw, a))
            break
            
    # Phone numbers embedded in high_school
    if ahs:
        matches = phone_regex.findall(str(ahs))
        if matches:
            phones_in_high_school.append((aid, aname, ahs, matches))

    # Phone numbers embedded in notes
    if anotes:
        matches = phone_regex.findall(str(anotes))
        if matches:
            phones_in_notes.append((aid, aname, anotes, matches))

    # Phone numbers embedded in team_name
    if ateam:
        matches = phone_regex.findall(str(ateam))
        if matches:
            phones_in_team.append((aid, aname, ateam, matches))

print(f"\n--- AUDIT FINDINGS ---")
print(f"Direct phone collisions (athlete phone == coach phone): {len(direct_phone_matches)}")
for m in direct_phone_matches[:10]:
    print(f"  COLLISION: ID={m[0]}, Name={m[1]}, Phone={m[2]}")

print(f"\nExact name collisions with coaches: {len(name_matches)}")
for m in name_matches[:10]:
    print(f"  NAME MATCH: ID={m[0]}, Name={m[1]}, Phone={m[2]}")

print(f"\nCoach keywords in athlete name: {len(coach_keyword_athletes)}")
for kw, m in coach_keyword_athletes[:10]:
    print(f"  KEYWORD '{kw}': ID={m[0]}, Name={m[1]}")

print(f"\nPhones found embedded in high_school field: {len(phones_in_high_school)}")
for p in phones_in_high_school[:10]:
    print(f"  ID={p[0]}, Athlete={p[1]}, HighSchool='{p[2]}', Extracted={p[3]}")

print(f"\nPhones found embedded in notes field: {len(phones_in_notes)}")
for p in phones_in_notes[:10]:
    print(f"  ID={p[0]}, Athlete={p[1]}, Notes='{p[2]}'")

print(f"\nPhones found embedded in team_name field: {len(phones_in_team)}")
for p in phones_in_team[:10]:
    print(f"  ID={p[0]}, Athlete={p[1]}, Team='{p[2]}'")

conn.close()
