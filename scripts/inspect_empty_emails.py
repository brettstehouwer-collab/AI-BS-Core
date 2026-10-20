import sqlite3

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT id, name, phone, email, status, high_school, notes, team_name
    FROM rec_debut_athletes
    WHERE email IS NULL OR email = ''
""")
rows = cur.fetchall()
print(f"Total rows in rec_debut_athletes with missing/empty email: {len(rows)}")

phone_only = []
artifacts = []
teams_or_blanks = []

artifact_keywords = ["COACH NAME", "ADDRESS", "EMAIL PHONE", "ATHLETE NAME", "YEAR ATHLETE"]

for r in rows:
    aid, name, phone, email, status, hs, notes, team = r
    name_clean = (name or "").strip()
    phone_clean = (phone or "").strip()
    
    if any(k in name_clean.upper() for k in artifact_keywords):
        artifacts.append(r)
    elif phone_clean and len("".join(filter(str.isdigit, phone_clean))) >= 10:
        phone_only.append(r)
    else:
        teams_or_blanks.append(r)

print(f"\nArtifact rows ({len(artifacts)}):")
for a in artifacts:
    print(" ", a[:4], a[5:])

print(f"\nPhone-only athletes ({len(phone_only)}):")
for p in phone_only:
    print(" ", p[:4], p[5:])

print(f"\nTeams / Blank rows ({len(teams_or_blanks)}):")
for t in teams_or_blanks[:15]:
    print(" ", t[:4], t[5:])
print(f" ... and {len(teams_or_blanks) - 15} more.")

conn.close()
