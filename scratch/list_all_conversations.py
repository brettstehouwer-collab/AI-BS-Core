import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

db_path = r'C:\Users\footb\.gemini\antigravity\conversation_summaries.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Let's inspect rows where title is not empty
query = """
SELECT conversation_id, title, workspace, project, step_count, chunk_index
FROM conversations_fts
WHERE title != '';
"""
rows = cur.execute(query).fetchall()
print(f"Total conversations with non-empty title: {len(rows)}")
for r in rows:
    print(r)

conn.close()
