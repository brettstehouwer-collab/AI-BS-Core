import sqlite3

conn = sqlite3.connect("saved_data/rec_debut.db")
c = conn.cursor()
c.execute("SELECT id, name, phone, email, email_status FROM rec_debut_athletes WHERE (status IS NULL OR status = 'Pending' OR status = 'Selected') AND email_status = 'UNDELIVERABLE'")
rows = c.fetchall()
print(f"Total undeliverable emails: {len(rows)}")
for r in rows:
    print(r)
conn.close()
