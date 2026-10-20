import sqlite3

conn = sqlite3.connect(r'C:\AI-BS\saved_data\rec_debut.db')
c = conn.cursor()
c.execute('SELECT phone FROM rec_debut_excluded_coaches')
coach_phones = set()
for r in c.fetchall():
    digits = ''.join(filter(str.isdigit, r[0]))
    if len(digits) >= 10:
        coach_phones.add(digits[-10:])

c.execute("SELECT id, name, phone, email FROM rec_debut_athletes WHERE email IS NOT NULL AND email != '' AND (status IS NULL OR status = 'Pending' OR status = 'Selected')")
rows = c.fetchall()
colliding = []
clean = []
for r in rows:
    digits = ''.join(filter(str.isdigit, r[2] or ''))
    if len(digits) >= 10 and digits[-10:] in coach_phones:
        colliding.append(r)
    else:
        clean.append(r)

print(f"Total pending with email: {len(rows)}")
print(f"Colliding with coach phone: {len(colliding)}")
print(f"Clean without coach phone collision: {len(clean)}")
if colliding:
    print("Sample colliding athletes:")
    for a in colliding[:5]:
        print("  ", a)
