import os
import sys
import json
import time
import sqlite3
import re
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Set

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(r"C:\AI-BS")
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
CSV_PATH = Path(r"C:\Users\footb\OneDrive\Desktop\TextBee_RecDebut_Class_of_2027.csv")
SECONDARY_DB_PATH = Path(r"C:\Recreational-Debut\saved_data\rec_debut.db")

TEXTBEE_DEVICE_ID = os.getenv("TEXTBEE_DEVICE_ID", "6ad7b28560b1138230badd0a")
TEXTBEE_API_KEY = os.getenv("TEXTBEE_API_KEY", "txb_rAZOZNMuTEKtlxQ30hfcJd05dL2KlVRu")

DENNIS_PHONE = "+1-616-291-5227"
DENNIS_EMAIL = "dbell002@sbcglobal.net"

def get_exclusion_set() -> Tuple[Set[str], Set[str]]:
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
            import csv
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

def sync_textbee_inbound() -> Dict[str, Any]:
    url = f"https://api.textbee.dev/api/v1/gateway/devices/{TEXTBEE_DEVICE_ID}/messages?limit=50"
    headers = {"x-api-key": TEXTBEE_API_KEY, "Content-Type": "application/json"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"success": False, "error": f"TextBee API returned {r.status_code}"}
        
        data = r.json()
        messages = data.get("data", [])
        received = [m for m in messages if m.get("type") == "RECEIVED"]
        
        excluded_phones, excluded_emails = get_exclusion_set()
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        processed = []
        for m in received:
            m_id = m.get("_id")
            sender = m.get("sender") or ""
            msg_text = m.get("message") or ""
            rec_at_str = m.get("receivedAt") or ""
            
            clean_digits = re.sub(r'\D', '', sender)[-10:] if sender else ""
            
            # Check exclusions
            if len(clean_digits) < 10:
                print(f"[SKIP SHORTCODE] {sender}: {msg_text[:30]}")
                continue
            if clean_digits in excluded_phones:
                print(f"[SKIP PERSONAL EXCLUSION] {sender}: {msg_text[:30]}")
                continue
                
            hash_key = f"textbee_{m_id}"
            c.execute("SELECT id FROM rec_debut_athlete_replies WHERE message_id_hash = ?", (hash_key,))
            existing = c.fetchone()
            
            athlete = find_athlete_by_contact(sender_phone=sender)
            ath_name = athlete["name"] if athlete else f"Prospective Recruit ({sender})"
            
            print(f"[QUALIFIED INBOUND TEXT] ID: {m_id} | From: {sender} ({ath_name}) | Text: '{msg_text}' | Already In DB: {bool(existing)}")
            processed.append({
                "id": m_id,
                "sender": sender,
                "athlete_name": ath_name,
                "message": msg_text,
                "already_in_db": bool(existing)
            })
            
        conn.close()
        return {"success": True, "qualified_count": len(processed), "items": processed}
    except Exception as e:
        return {"success": False, "error": str(e)}

print("Testing TextBee Inbound Processor:")
res = sync_textbee_inbound()
print("Result:", json.dumps(res, indent=2))
