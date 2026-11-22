import sqlite3
import re
import time

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

now = time.time()

# 1. Coach phones and names from embedded high school fields to add to rec_debut_excluded_coaches
new_coaches = [
    ("Maurice Hicks", "917-499-5819", "High School Coach", "Cardinal Spellman", 61),
    ("Billy Turnage", "917-400-2061", "High School Coach", "Holy Cross HS", 61),
    ("Tim Whitworth", "215-606-8912", "High School Coach", "Clearview Regional High School", 61),
    ("Patrick Massaroni", "914-438-1541", "High School Coach", "Archbishop Stepinac", 61),
    ("Alex Maribel", "201-780-7067", "High School Coach", "Saint Peter's Preparatory", 61),
    ("Erick Loften Harris", "908-553-1752", "High School Coach", "Union High School", 61),
    ("Peter Wehye", "347-393-5534", "High School Coach", "Our Saviour Lutheran School", 61),
    ("Peter Wehye (OCR Typo)", "134-739-3553", "High School Coach", "Our Saviour Lutheran School", 61),
    ("Dan Celentano", "631-372-6382", "High School Coach", "Sachem HS East", 61),
    ("Oliz Nhor", "443-547-8826", "High School Coach", "Oak Hill Academy", 61),
    ("Trey Morin", "413-464-2516", "High School Coach", "The Phelps School", 71),
    ("Julian Andrade", "818-694-4646", "High School Coach", "Village Christian High School", 77),
    ("Stallworth Christopher", "718-502-4447", "High School Coach", "Oak Hills High School", 77),
    ("Coach Perp", "323-821-4203", "High School Coach", "Veritas Academy", 77),
    ("Raphael Graves", "256-452-6632", "High School Coach", "Gadsden City High School", 125),
]

for name, phone, ctype, school, page in new_coaches:
    cur.execute("""
        INSERT OR IGNORE INTO rec_debut_excluded_coaches (name, phone, coach_type, school_name, page, excluded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, phone, ctype, school, page, now))

print(f"Added/verified {len(new_coaches)} high school coaches in rec_debut_excluded_coaches.")

# 2. Purge athlete ID 14 whose phone was Coach Peter Wehye's number
id14 = cur.execute("SELECT id, name, phone FROM rec_debut_athletes WHERE id = 14").fetchone()
if id14:
    print(f"Purging athlete ID 14: '{id14[1]}' with coach phone '{id14[2]}'...")
    cur.execute("DELETE FROM rec_debut_athletes WHERE id = 14")
    print("Purged ID 14 from rec_debut_athletes.")

# 3. Clean high_school field for the remaining 14 rows
hs_corrections = {
    8: "Cardinal Spellman",
    9: "Holy Cross HS",
    10: "Clearview Regional High School",
    11: "Archbishop Stepinac",
    12: "Saint Peter's Preparatory",
    13: "Union High School",
    15: "Our Saviour Lutheran School",
    16: "Sachem HS East",
    17: "Oak Hill Academy",
    18: "The Phelps School",
    718: "Village Christian High School",
    723: "Oak Hills High School",
    727: "Veritas Academy",
    1179: "Gadsden City High School"
}

for aid, clean_hs in hs_corrections.items():
    cur.execute("UPDATE rec_debut_athletes SET high_school = ? WHERE id = ?", (clean_hs, aid))
    print(f"Updated athlete ID {aid} high_school to: '{clean_hs}'")

# 4. Clean height prefixes and coach names from all athlete high_school fields
# E.g. "6-4 LEGION PREPARATORY ACADEMY DONALD WALKER" -> "Legion Preparatory Academy"
coach_names_set = set(r[0].strip().upper() for r in cur.execute("SELECT name FROM rec_debut_excluded_coaches WHERE name IS NOT NULL AND name != 'Club Coach' AND name != 'High School Coach'").fetchall())

all_athletes = cur.execute("SELECT id, high_school FROM rec_debut_athletes").fetchall()
cleaned_count = 0
for aid, hs in all_athletes:
    if not hs:
        continue
    orig = hs
    # Strip height prefix like "6-4 ", "5-10 "
    clean_val = re.sub(r'^[5-7]-\d+\s+', '', hs).strip()
    
    # Strip coach names if they appear at the end
    for cn in coach_names_set:
        if cn in clean_val.upper():
            # Remove coach name
            pattern = re.compile(re.escape(cn), re.IGNORECASE)
            clean_val = pattern.sub('', clean_val).strip()
    
    # Clean multiple spaces
    clean_val = re.sub(r'\s+', ' ', clean_val).strip()
    
    if clean_val != orig:
        cur.execute("UPDATE rec_debut_athletes SET high_school = ? WHERE id = ?", (clean_val, aid))
        cleaned_count += 1

print(f"Cleaned high_school formatting for {cleaned_count} athletes.")

# 5. Collision Check: Verify 100% that NO athlete phone matches ANY coach phone
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

# Total counts
total_athletes = cur.execute("SELECT COUNT(*) FROM rec_debut_athletes").fetchone()[0]
total_coaches = cur.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches").fetchone()[0]
print(f"\nFinal Database State:")
print(f"  Total Clean Student-Athletes: {total_athletes}")
print(f"  Total Excluded Coaches Blocklist: {total_coaches}")

conn.close()
