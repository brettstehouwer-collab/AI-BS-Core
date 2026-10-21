import os
import sys
import json
import time
import sqlite3
import re
import requests
import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Set, List
import threading

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(r"C:\AI-BS")
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
SECONDARY_DB_PATH = Path(r"C:\Recreational-Debut\saved_data\rec_debut.db")
CSV_PATH = Path(r"C:\Users\footb\OneDrive\Desktop\TextBee_RecDebut_Class_of_2027.csv")

TEXTBEE_DEVICE_ID = os.getenv("TEXTBEE_DEVICE_ID", "6ad7b28560b1138230badd0a")
TEXTBEE_API_KEY = os.getenv("TEXTBEE_API_KEY", "txb_rAZOZNMuTEKtlxQ30hfcJd05dL2KlVRu")

DENNIS_PHONE = "+1-616-291-5227"
DENNIS_EMAIL = "dbell002@sbcglobal.net"

def get_personal_exclusion_set() -> Tuple[Set[str], Set[str]]:
    excluded_phones = {
        "6164023628",  # Brett Stehouwer personal cell
        "6164067993",  # Mom personal cell
        "6162915227",  # Dennis Bell (prevent routing loop)
        "6168027774",  # Adam Stehouwer
    }
    excluded_emails = {
        "brettstehouwer@gmail.com",
        "brett.noco.letsgo.stehouwer@gmail.com",
        "footballstar0325@gmail.com",
        "adamstehouwer24@gmail.com",
        "brett@stehouwer-publishing.com",
        "account@nvidia.com",
        "dbell002@sbcglobal.net",
    }
    contacts_path = Path(r"C:\Users\footb\OneDrive\Desktop\MyPhoneContacts.csv")
    if contacts_path.exists():
        try:
            with open(contacts_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    p_indices = [i for i, h in enumerate(header) if "Phone" in h]
                    e_indices = [i for i, h in enumerate(header) if "E-mail" in h]
                    for row in reader:
                        for pi in p_indices:
                            if pi < len(row) and row[pi]:
                                digits = re.sub(r'\D', '', row[pi])
                                if len(digits) >= 10:
                                    excluded_phones.add(digits[-10:])
                        for ei in e_indices:
                            if ei < len(row) and row[ei]:
                                clean_em = row[ei].strip().lower()
                                if "@" in clean_em:
                                    excluded_emails.add(clean_em)
        except Exception as e:
            print(f"[EXCLUSION SET] Note: Error reading MyPhoneContacts.csv: {e}")
    return excluded_phones, excluded_emails

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

print("find_athlete_by_contact defined")
