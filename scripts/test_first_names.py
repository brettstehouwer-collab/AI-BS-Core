import sqlite3

conn = sqlite3.connect("saved_data/rec_debut.db")
c = conn.cursor()

def extract_first_name(full_name: str) -> str:
    if not full_name:
        return "Student-Athlete"
    parts = full_name.strip().split()
    if not parts:
        return "Student-Athlete"
    first = parts[0].strip().title()
    first = "".join(c for c in first if c.isalpha())
    return first if first else "Student-Athlete"

c.execute("SELECT id, name, phone, email FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected' ORDER BY id ASC")
rows = c.fetchall()

print(f"Total remaining players to dispatch: {len(rows)}")
print("\nSample first 10 personalized names:")
for r in rows[:10]:
    fn = extract_first_name(r[1])
    print(f"ID {r[0]}: Raw: '{r[1]}' -> Personalized First Name: '{fn}' | Phone: {r[2]} | Email: {r[3]}")

conn.close()
