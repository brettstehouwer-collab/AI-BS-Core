import sqlite3
import re

DB_PATH = "saved_data/rec_debut.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Load all coaches
cursor.execute("SELECT id, name, phone, coach_type, school_name, team_name FROM rec_debut_excluded_coaches")
coaches = cursor.fetchall()
coach_phones_norm = set()
coach_names_norm = set()

for cid, name, phone, ctype, school, team in coaches:
    digits = "".join(filter(str.isdigit, phone or ""))
    if len(digits) >= 10:
        coach_phones_norm.add(digits[-10:])
    if name:
        clean_n = name.strip().lower()
        if len(clean_n) > 3:
            coach_names_norm.add(clean_n)

print(f"Total Excluded Coaches: {len(coaches)}")
print(f"Unique 10-digit Coach Phones: {len(coach_phones_norm)}")
print(f"Unique Coach Names: {len(coach_names_norm)}")

# 2. Check all athletes
cursor.execute("SELECT id, name, phone, email, sport, high_school, grad_year, notes FROM rec_debut_athletes")
athletes = cursor.fetchall()
print(f"Total Athletes Currently on Roster: {len(athletes)}")

COACH_KEYWORDS = [
    r'\bcoach\b', r'\bcoaches\b', r'\bhead coach\b', r'\bhc\b', r'\basst\b',
    r'\bassistant\b', r'\bdirector\b', r'\btrainer\b', r'\bad\b', r'\bathletic director\b',
    r'\bprogram director\b', r'\bcoordinator\b', r'\bmanager\b', r'\bstaff\b'
]

purged_by_phone = []
purged_by_name_match = []
purged_by_keyword = []

for aid, name, phone, email, sport, school, grad_year, notes in athletes:
    digits = "".join(filter(str.isdigit, phone or ""))
    ten = digits[-10:] if len(digits) >= 10 else digits
    name_clean = (name or "").strip().lower()

    # Check 1: Phone number matches a coach
    if ten in coach_phones_norm:
        purged_by_phone.append((aid, name, phone, "Phone matched excluded coach"))
        continue

    # Check 2: Exact name match with a known coach
    if name_clean in coach_names_norm:
        purged_by_name_match.append((aid, name, phone, f"Exact name match with coach '{name}'"))
        continue

    # Check 3: Name or notes contains coach keyword
    is_kw_match = False
    for kw in COACH_KEYWORDS:
        if re.search(kw, name_clean):
            purged_by_keyword.append((aid, name, phone, f"Name keyword match: '{kw}'"))
            is_kw_match = True
            break
        if notes and re.search(kw, notes.lower()):
            # Only if notes explicitly say coach and not just 'Imported'
            if "head coach" in notes.lower() or "club coach" in notes.lower():
                purged_by_keyword.append((aid, name, phone, f"Notes keyword match: '{kw}'"))
                is_kw_match = True
                break
    if is_kw_match:
        continue

all_to_purge = purged_by_phone + purged_by_name_match + purged_by_keyword
print(f"\n--- AUDIT & PURGE SUMMARY ---")
print(f"Athletes to remove due to phone match: {len(purged_by_phone)}")
print(f"Athletes to remove due to exact coach name match: {len(purged_by_name_match)}")
print(f"Athletes to remove due to coach title/keyword: {len(purged_by_keyword)}")
print(f"Total Records to Purge from Athletes: {len(all_to_purge)}")

if all_to_purge:
    for item in all_to_purge:
        aid, name, phone, reason = item
        print(f"Purging Athlete ID {aid}: '{name}' ({phone}) - Reason: {reason}")
        # Insert into excluded coaches if not already there
        cursor.execute("""
            INSERT INTO rec_debut_excluded_coaches (name, phone, coach_type, school_name, excluded_at)
            VALUES (?, ?, 'Purged from Athletes List', 'Deep Scrubber', ?)
        """, (name, phone, 2026.0))
        # Delete from athletes
        cursor.execute("DELETE FROM rec_debut_athletes WHERE id = ?", (aid,))
    conn.commit()
    print(f"\nSuccessfully purged {len(all_to_purge)} records from rec_debut_athletes!")
else:
    print("\n[OK] Roster is 100% clean. Zero coaches found in the athletes table.")

# Final verification count
cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes")
remaining_athletes = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")
contacted_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")
pending_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches")
total_coaches = cursor.fetchone()[0]

print(f"\n--- FINAL VERIFIED COUNTS ---")
print(f"Total Clean Athletes on Roster: {remaining_athletes}")
print(f"  - Pending (Needs Message): {pending_count}")
print(f"  - Contacted (Already Messaged): {contacted_count}")
print(f"Total Excluded Coaches Quarantined: {total_coaches}")

conn.close()
