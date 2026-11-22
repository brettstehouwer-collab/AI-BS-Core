import sqlite3
conn = sqlite3.connect(r'C:\AI-BS\backend\aibs_master.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in c.fetchall()]
print("Tables:", tables)
