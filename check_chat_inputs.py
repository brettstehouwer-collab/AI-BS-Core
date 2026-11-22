import sqlite3
import json
import os
from datetime import datetime

db_path = "C:/AI-BS/database/LLM_CrossCheck_Ledger.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in LLM_CrossCheck_Ledger.db: {tables}")
    
    for table in tables:
        tname = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {tname};")
        count = cursor.fetchone()[0]
        print(f"\nTable [{tname}] Total Records: {count}")
        
        cursor.execute(f"SELECT * FROM {tname} ORDER BY rowid DESC LIMIT 5;")
        rows = cursor.fetchall()
        # Get column names
        cursor.execute(f"PRAGMA table_info({tname});")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"Columns: {cols}")
        for r in rows:
            print("--- Row ---")
            for col, val in zip(cols, r):
                val_str = str(val)[:150] + ("..." if len(str(val)) > 150 else "")
                print(f"  {col}: {val_str}")
    conn.close()
else:
    print(f"Database not found at {db_path}")

# Check session history archive
archive_path = "C:/AI-BS/backend/session_history_archive.json"
if os.path.exists(archive_path):
    with open(archive_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"\nsession_history_archive.json top-level keys: {list(data.keys()) if isinstance(data, dict) else len(data)}")
