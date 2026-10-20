import sqlite3

conn = sqlite3.connect("saved_data/rec_debut.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")
pending = c.fetchone()[0]
print(f"Total Pending Athletes ready for dispatch: {pending}")

c.execute("SELECT id, name, phone, email FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected' LIMIT 5")
print("\nFirst 5 athletes in next batch queue:")
for r in c.fetchall():
    print(f"ID {r[0]}: {r[1]} | Phone: {r[2]} | Email: {r[3]}")

conn.close()
