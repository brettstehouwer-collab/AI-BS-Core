import sqlite3
import os

db1 = os.path.join(os.path.dirname(__file__), "west_michigan.db")
db2 = os.path.join(os.path.dirname(os.path.dirname(__file__)), "leads_store.db")

print("Checking properties database:", db1)
if os.path.exists(db1):
    conn = sqlite3.connect(db1)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    try:
        count = conn.execute("SELECT count(*) FROM properties").fetchone()[0]
        print(f"Properties count: {count}")
    except Exception as e:
        print("Error reading properties:", e)
    conn.close()
else:
    print("Not found.")

print("\nChecking leads database:", db2)
if os.path.exists(db2):
    conn = sqlite3.connect(db2)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    try:
        count = conn.execute("SELECT count(*) FROM joey_enriched_leads").fetchone()[0]
        print(f"Enriched leads count: {count}")
    except Exception as e:
        print("Error reading leads:", e)
    conn.close()
else:
    print("Not found.")
