import sqlite3
import os

db_path = r'C:\Users\footb\.gemini\antigravity-ide\conversations\bdf800f8-ece2-4bc1-b8d9-4ef4471e6d56.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
for row in cur.fetchall():
    print("TABLE:", row[0])
    print(row[1])
    print('-'*40)
conn.close()
