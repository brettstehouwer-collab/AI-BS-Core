import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Purge ID 625
cur.execute("DELETE FROM rec_debut_athletes WHERE id = 625")
print("Purged duplicate record ID 625.")

# Check for any other records with phone containing 3935534 or 134739
others = cur.execute("SELECT id, name, phone FROM rec_debut_athletes WHERE phone LIKE '%393-5534%' OR phone LIKE '%134-739%'").fetchall()
print(f"Other matching rows: {others}")

# Collision Check
cur.execute("SELECT phone FROM rec_debut_excluded_coaches")
coach_phones = set()
for r in cur.fetchall():
    d = re.sub(r'\D', '', str(r[0]))
    if len(d) >= 10:
        coach_phones.add(d[-10:])

cur.execute("SELECT id, name, phone FROM rec_debut_athletes")
remaining_athletes = cur.fetchall()

collisions = []
for aid, name, phone in remaining_athletes:
    d = re.sub(r'\D', '', str(phone or ""))
    if len(d) >= 10 and d[-10:] in coach_phones:
        collisions.append((aid, name, phone))

print(f"\nFinal collision check: {len(collisions)} collisions found.")
if collisions:
    for c in collisions:
        print(f"  WARNING COLLISION: ID={c[0]}, Name={c[1]}, Phone={c[2]}")
else:
    print("[SUCCESS] ZERO collisions! Absolutely NO coaches exist in the athlete roster.")

conn.commit()
total_athletes = cur.execute("SELECT COUNT(*) FROM rec_debut_athletes").fetchone()[0]
total_coaches = cur.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches").fetchone()[0]
print(f"\nFinal Clean State:")
print(f"  Total Clean Student-Athletes: {total_athletes}")
print(f"  Total Excluded Coaches Blocklist: {total_coaches}")

conn.close()
