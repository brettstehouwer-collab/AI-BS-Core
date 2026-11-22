import sqlite3

db_path = r"C:\AI-BS\backend\database\aibs_personal_intelligence.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", tables)
for t in tables:
    cursor.execute(f"PRAGMA table_info({t[0]})")
    print(f"Schema of {t[0]}:", cursor.fetchall())
conn.close()
