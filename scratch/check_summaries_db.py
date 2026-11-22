import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

db_path = r'C:\Users\footb\.gemini\antigravity\conversation_summaries.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
for row in cur.fetchall():
    print("TABLE:", row[0])
    print(row[1])
    print('-'*40)

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
for t in tables:
    cur.execute(f"SELECT count(*) FROM {t};")
    cnt = cur.fetchone()[0]
    print(f"Table {t} has {cnt} rows")
    cur.execute(f"SELECT * FROM {t} LIMIT 5;")
    cols = [d[0] for d in cur.description]
    print("Columns:", cols)
    for r in cur.fetchall():
        # print truncated representation
        row_str = {cols[i]: (str(r[i])[:80] + '...' if len(str(r[i])) > 80 else str(r[i])) for i in range(len(cols))}
        print("Row:", row_str)
    print('='*50)

conn.close()
