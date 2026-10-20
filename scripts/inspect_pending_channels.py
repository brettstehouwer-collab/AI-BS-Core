import sqlite3

conn = sqlite3.connect("saved_data/rec_debut.db")
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE (status IS NULL OR status = 'Pending' OR status = 'Selected')")
total_pending = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE (status IS NULL OR status = 'Pending' OR status = 'Selected') AND email IS NOT NULL AND email LIKE '%@%'")
pending_with_email = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE (status IS NULL OR status = 'Pending' OR status = 'Selected') AND (email IS NULL OR email NOT LIKE '%@%')")
pending_no_email = c.fetchone()[0]

print(f"Total Pending Remaining: {total_pending}")
print(f"Pending WITH Email:      {pending_with_email}")
print(f"Pending WITHOUT Email:   {pending_no_email}")

conn.close()
