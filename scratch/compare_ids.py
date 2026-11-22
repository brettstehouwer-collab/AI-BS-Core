import os
import sqlite3

db_path = r'C:\Users\footb\.gemini\antigravity\conversation_summaries.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cids_db = [r[0] for r in cur.execute("SELECT conversation_id FROM conversations_fts WHERE title != '';").fetchall()]
conn.close()

brain_dir = r'C:\Users\footb\.gemini\antigravity-ide\brain'
dirs_brain = [d for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d))]

print("Sample DB cid:", cids_db[:3])
print("Sample Brain dir:", dirs_brain[:3])

common = set(cids_db).intersection(set(dirs_brain))
print(f"Intersection count: {len(common)} out of {len(cids_db)} DB and {len(dirs_brain)} Brain dirs")

in_brain_not_db = set(dirs_brain) - set(cids_db)
print("In brain not in DB:", len(in_brain_not_db), list(in_brain_not_db)[:5])

in_db_not_brain = set(cids_db) - set(dirs_brain)
print("In DB not in brain:", len(in_db_not_brain), list(in_db_not_brain)[:5])
