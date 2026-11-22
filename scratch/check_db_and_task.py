import sqlite3

conn = sqlite3.connect(r"C:\AI-BS\saved_data\rec_debut.db")
c = conn.cursor()
try:
    c.execute("SELECT COUNT(*) FROM rec_debut_athletes")
    print("Athletes:", c.fetchone()[0])
except Exception as e:
    print("Athletes err:", e)

try:
    c.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches")
    print("Excluded coaches:", c.fetchone()[0])
except Exception as e:
    print("Coaches err:", e)
conn.close()
