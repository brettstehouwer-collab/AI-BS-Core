import sqlite3

conn = sqlite3.connect(r"C:\AI-BS\saved_data\rec_debut.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM rec_debut_athletes")
print("Total Athletes:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Pending'")
print("Pending Athletes:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted'")
print("Contacted Athletes:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches")
print("Total Excluded Coaches:", c.fetchone()[0])

c.execute("SELECT name, phone, coach_type, team_name FROM rec_debut_excluded_coaches LIMIT 5")
print("\nSample Excluded Coaches:")
for row in c.fetchall():
    print(" ", row)

c.execute("SELECT name, phone, sport, school, team_name, status FROM rec_debut_athletes LIMIT 5")
print("\nSample Athletes:")
for row in c.fetchall():
    print(" ", row)

conn.close()
