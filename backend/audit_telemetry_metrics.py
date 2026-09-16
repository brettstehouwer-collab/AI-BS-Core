import sqlite3
import os
import glob
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Search for sqlite db files
db_files = glob.glob(r'C:\AI-BS\**\*.sqlite*', recursive=True) + glob.glob(r'C:\AI-BS\**\*.db', recursive=True)
print("Database files found:", len(db_files))

for db in db_files:
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        if tables:
            print(f"\nDB: {db}")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                print(f"  -> Table `{table}`: {count} records")
                if count > 0:
                    cursor.execute(f"PRAGMA table_info(`{table}`)")
                    cols = [c[1] for c in cursor.fetchall()]
                    print(f"     Columns: {cols}")
                    cursor.execute(f"SELECT * FROM `{table}` ORDER BY rowid DESC LIMIT 2")
                    rows = cursor.fetchall()
                    for r in rows:
                        print(f"     Sample: {str(r)[:100]}")
        conn.close()
    except Exception as e:
        print(f"Error reading {db}: {e}")
