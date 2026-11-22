import sqlite3
import glob
import os

db_files = glob.glob(r'C:\Users\footb\.gemini\antigravity-ide\conversations\*.db')
print(f"Total conversation db files: {len(db_files)}")

# Check one db
sample = db_files[0]
print("Sample db:", sample)
conn = sqlite3.connect(sample)
cur = conn.cursor()
try:
    cur.execute("SELECT * FROM trajectory_meta;")
    print("trajectory_meta:", cur.fetchall())
except Exception as e:
    print("trajectory_meta err:", e)

try:
    cur.execute("SELECT id, length(data) FROM trajectory_metadata_blob;")
    print("trajectory_metadata_blob:", cur.fetchall())
except Exception as e:
    print("trajectory_metadata_blob err:", e)

# Check first step
try:
    cur.execute("SELECT idx, step_type, status, length(step_payload) FROM steps LIMIT 5;")
    print("steps sample:", cur.fetchall())
except Exception as e:
    print("steps err:", e)

conn.close()
