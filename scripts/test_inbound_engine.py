import os
import sys
import json
import time
import sqlite3
import re
from pathlib import Path
from typing import Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(r"C:\AI-BS")
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
CSV_PATH = Path(r"C:\Users\footb\OneDrive\Desktop\TextBee_RecDebut_Class_of_2027.csv")

def find_athlete_by_contact(sender_phone: Optional[str] = None, sender_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_digits = re.sub(r'\D', '', sender_phone)[-10:] if sender_phone else ""
    matched = None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if clean_digits:
        cursor.execute("""
            SELECT id, name, sport, high_school, grad_year, city_state, phone, email 
            FROM rec_debut_athletes 
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', ''), '+', '') LIKE ?
        """, (f"%{clean_digits}%",))
        row = cursor.fetchone()
        if row:
            matched = dict(row)

    if not matched and sender_email:
        cursor.execute("""
            SELECT id, name, sport, high_school, grad_year, city_state, phone, email 
            FROM rec_debut_athletes 
            WHERE LOWER(email) = ?
        """, (sender_email.lower().strip(),))
        row = cursor.fetchone()
        if row:
            matched = dict(row)

    if not matched and clean_digits and CSV_PATH.exists():
        import csv
        try:
            with open(CSV_PATH, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    cp = re.sub(r'\D', '', r.get("phone", "") or r.get("phoneNumber", ""))[-10:]
                    if cp == clean_digits:
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
        except Exception as e:
            print(f"[CSV LOOKUP ERROR] {e}")

    conn.close()
    return matched

print("Testing athlete matching:")
print("9172131155 ->", find_athlete_by_contact(sender_phone="9172131155"))
print("Unknown 5551234567 ->", find_athlete_by_contact(sender_phone="5551234567"))
