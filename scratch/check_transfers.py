import sqlite3
conn = sqlite3.connect(r'C:\AI-BS\backend\aibs_master.db')
c = conn.cursor()
c.execute("SELECT * FROM crypto_transfers")
rows = c.fetchall()
for r in rows:
    print(r)
