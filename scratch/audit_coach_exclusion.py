import sqlite3
import re

DB_PATH = "saved_data/rec_debut.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Fetch all coach phones
cursor.execute("SELECT id, name, phone, coach_type, school_name, team_name FROM rec_debut_excluded_coaches")
coaches = cursor.fetchall()
coach_phones_norm = {}
for cid, name, phone, ctype, school, team in coaches:
    digits = "".join(filter(str.isdigit, phone))
    if len(digits) >= 10:
        coach_phones_norm[digits[-10:]] = {"id": cid, "name": name, "phone": phone, "type": ctype}

print(f"Total Excluded Coaches Loaded: {len(coaches)}")
print(f"Unique 10-digit Coach Phone Numbers: {len(coach_phones_norm)}")

# 2. Fetch all athletes
cursor.execute("SELECT id, name, phone, high_school, team_name, status, notes FROM rec_debut_athletes")
athletes = cursor.fetchall()
print(f"Total Athletes in Roster: {len(athletes)}")

# 3. Check for phone collisions
phone_collisions = []
name_suspects = []

SUSPECT_KEYWORDS = ["coach", "head coach", "hc", "director", "trainer", "asst", "scout", "recruiter", "manager"]

for aid, name, phone, school, team, status, notes in athletes:
    digits = "".join(filter(str.isdigit, phone))
    ten = digits[-10:] if len(digits) >= 10 else digits
    if ten in coach_phones_norm:
        phone_collisions.append({
            "athlete_id": aid,
            "athlete_name": name,
            "athlete_phone": phone,
            "matched_coach": coach_phones_norm[ten]
        })
    
    # Check if athlete name looks like a coach
    name_lower = (name or "").lower()
    for kw in SUSPECT_KEYWORDS:
        # Check whole word or title
        if re.search(r'\b' + re.escape(kw) + r'\b', name_lower):
            name_suspects.append({"id": aid, "name": name, "phone": phone, "keyword": kw})
            break

print("\n--- RESULTS OF COACH CONTAMINATION AUDIT ---")
print(f"Direct Phone Number Collisions: {len(phone_collisions)}")
if phone_collisions:
    for c in phone_collisions:
        print("COLLISION:", c)
else:
    print("[OK] ZERO phone number collisions found between athletes and coaches!")

print(f"\nKeyword Suspect Names in Athletes: {len(name_suspects)}")
if name_suspects:
    for s in name_suspects:
        print("SUSPECT:", s)
else:
    print("[OK] ZERO coach keywords in athlete names!")

conn.close()
