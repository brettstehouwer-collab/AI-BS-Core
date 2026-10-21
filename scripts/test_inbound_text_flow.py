import re
import sys
import os
import sqlite3
import time
import requests
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path("saved_data/rec_debut.db")
ROSTER_CSV = Path(r"C:\Users\footb\OneDrive\Desktop\TextBee_RecDebut_Class_of_2027.csv")

def find_athlete_by_phone_or_email(phone=None, email=None):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    clean_digits = re.sub(r'\D', '', phone)[-10:] if phone else ""
    matched = None
    
    if clean_digits:
        c.execute("""
            SELECT id, name, sport, high_school, grad_year, city_state, phone, email 
            FROM rec_debut_athletes 
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', ''), '+', '') LIKE ?
        """, (f"%{clean_digits}%",))
        row = c.fetchone()
        if row:
            matched = dict(row)
            
    if not matched and email:
        c.execute("SELECT id, name, sport, high_school, grad_year, city_state, phone, email FROM rec_debut_athletes WHERE LOWER(email) = ?", (email.lower(),))
        row = c.fetchone()
        if row:
            matched = dict(row)
            
    # Check CSV if not in DB
    if not matched and ROSTER_CSV.exists() and clean_digits:
        import csv
        with open(ROSTER_CSV, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for r in reader:
                csv_phone = re.sub(r'\D', '', r.get("phone", "") or r.get("phoneNumber", ""))[-10:]
                if csv_phone == clean_digits:
                    matched = {
                        "id": int(r.get("athlete_id") or 0) if r.get("athlete_id") else None,
                        "name": r.get("name") or r.get("first_name"),
                        "sport": r.get("sport") or "Basketball",
                        "high_school": r.get("high_school") or "",
                        "grad_year": r.get("grad_year") or "2027",
                        "city_state": "",
                        "phone": r.get("phone"),
                        "email": r.get("email")
                    }
                    break
    conn.close()
    return matched

# Test with a sample athlete
res = find_athlete_by_phone_or_email(phone="9172131155")
print("Lookup for 9172131155:", res)

res2 = find_athlete_by_phone_or_email(phone="7184405979")
print("Lookup for 7184405979:", res2)
