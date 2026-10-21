import re
import sqlite3
import time
import requests
from pathlib import Path

DB_PATH = Path("saved_data/rec_debut.db")

def test_athlete_lookup(phone_digits):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    clean_digits = re.sub(r'\D', '', phone_digits)[-10:]
    c.execute("""
        SELECT id, name, sport, high_school, grad_year, city_state, phone, email 
        FROM rec_debut_athletes 
        WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', ''), '+', '') LIKE ?
    """, (f"%{clean_digits}%",))
    ath = c.fetchone()
    conn.close()
    return dict(ath) if ath else None

print("Checking test lookup for athlete...")
# Let's see some phone numbers in rec_debut_athletes
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, name, phone, sport, high_school FROM rec_debut_athletes LIMIT 5")
for r in c.fetchall():
    print("Sample athlete in DB:", dict(r))
    matched = test_athlete_lookup(r["phone"])
    print("Match result:", matched["name"] if matched else "None")

conn.close()
