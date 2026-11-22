import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

total_athletes = cur.execute("SELECT count(*) FROM rec_debut_athletes").fetchone()[0]
pending_athletes = cur.execute("SELECT count(*) FROM rec_debut_athletes WHERE status = 'Pending' OR status = 'Selected' OR status IS NULL").fetchone()[0]
contacted_athletes = cur.execute("SELECT count(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'").fetchone()[0]
total_coaches = cur.execute("SELECT count(*) FROM rec_debut_excluded_coaches").fetchone()[0]

# Check phone collisions
coach_phones = set()
for r in cur.execute("SELECT phone FROM rec_debut_excluded_coaches").fetchall():
    d = re.sub(r'\D', '', str(r[0]))
    if len(d) >= 10:
        coach_phones.add(d[-10:])

collisions = []
for aid, name, phone in cur.execute("SELECT id, name, phone FROM rec_debut_athletes").fetchall():
    d = re.sub(r'\D', '', str(phone or ""))
    if len(d) >= 10 and d[-10:] in coach_phones:
        collisions.append((aid, name, phone))

# Check coach mentions
coach_mentions = cur.execute("""
    SELECT count(*) FROM rec_debut_athletes 
    WHERE UPPER(name) LIKE '%COACH%' 
       OR UPPER(high_school) LIKE '%COACH%' 
       OR UPPER(notes) LIKE '%COACH%' 
       OR UPPER(team_name) LIKE '%COACH%'
""").fetchone()[0]

# Check embedded phones in athlete records
phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')
embedded_phones = 0
for r in cur.execute("SELECT high_school, notes FROM rec_debut_athletes").fetchall():
    if phone_regex.search(r[0] or "") or phone_regex.search(r[1] or ""):
        embedded_phones += 1

print("================ FINAL AUDIT VERIFICATION ================")
print(f"Total Student-Athletes on Roster: {total_athletes}")
print(f"  * Pending (Needs To Be Messaged): {pending_athletes}")
print(f"  * Contacted (Already Messaged):   {contacted_athletes}")
print(f"Total Coaches Quarantined in Blocklist: {total_coaches}")
print(f"Phone Collisions between Athletes and Coaches: {len(collisions)}")
print(f"Coach Keyword Mentions in Athlete Roster: {coach_mentions}")
print(f"Embedded Phone Numbers in High School/Notes: {embedded_phones}")
print("==========================================================")

assert len(collisions) == 0, "Collisions detected!"
assert coach_mentions == 0, "Coach mentions detected!"
assert embedded_phones == 0, "Embedded phones detected!"

conn.close()
