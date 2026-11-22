import sqlite3
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check all coaches in rec_debut_excluded_coaches
coach_names = set(r[0].strip().upper() for r in cur.execute("SELECT name FROM rec_debut_excluded_coaches WHERE name IS NOT NULL").fetchall())
coach_phones = set()
for r in cur.execute("SELECT phone FROM rec_debut_excluded_coaches WHERE phone IS NOT NULL").fetchall():
    d = re.sub(r'\D', '', str(r[0]))
    if len(d) >= 10:
        coach_phones.add(d[-10:])

print(f"Coach blocklist has {len(coach_names)} unique names and {len(coach_phones)} unique 10-digit phone numbers.")

# Let's inspect athletes
athletes = cur.execute("SELECT id, name, phone, email, high_school, notes, team_name, status FROM rec_debut_athletes").fetchall()

suspicious_athletes = []
for a in athletes:
    aid, aname, aphone, aemail, ahs, anotes, ateam, astat = a
    name_up = (aname or "").strip().upper()
    phone_clean = re.sub(r'\D', '', str(aphone or ""))
    phone_10 = phone_clean[-10:] if len(phone_clean) >= 10 else ""

    reasons = []
    # Check phone collision
    if phone_10 and phone_10 in coach_phones:
        reasons.append(f"Phone {phone_10} is in coach blocklist")

    # Check ID 14 specific issue (134-739-3553 matches 347-393-5534)
    if "3473935534" in phone_clean or "3935534" in phone_clean:
        reasons.append("Phone matches Coach Pete Wehye")

    # Check name match with coach blocklist
    if name_up and name_up in coach_names:
        reasons.append(f"Name '{name_up}' matches coach in blocklist")

    # Check coach keywords in name
    for kw in ["COACH", "DIR", "DIRECTOR", "COORDINATOR", "HEAD COACH", "ASST", "STAFF", "TRAINER"]:
        if re.search(r'\b' + kw + r'\b', name_up):
            reasons.append(f"Name contains keyword '{kw}'")

    if reasons:
        suspicious_athletes.append((a, reasons))

print(f"\nSuspicious athletes found: {len(suspicious_athletes)}")
for a, reasons in suspicious_athletes:
    print(f"ID={a[0]}, Name='{a[1]}', Phone='{a[2]}', HS='{a[4]}', Reasons={reasons}")

conn.close()
