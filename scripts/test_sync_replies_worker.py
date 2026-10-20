import sqlite3
import imaplib
import email
from email.header import decode_header
import re
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"

CARRIER_DOMAINS = [
    "vzwpix.com", "vtext.com", "mms.att.net", "txt.att.net",
    "tmomail.net", "mms.cricketwireless.net", "myboostmobile.com",
    "mms.uscc.net", "msg.fi.google.com"
]

def init_replies_table():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rec_debut_athlete_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            athlete_name TEXT,
            sender_phone TEXT,
            sender_email TEXT,
            recipient_email TEXT,
            subject TEXT,
            reply_body TEXT,
            received_at REAL,
            is_read INTEGER DEFAULT 0,
            created_at REAL,
            message_id_hash TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def decode_mime_words(s):
    if not s:
        return ""
    decoded = []
    try:
        parts = decode_header(s)
        for text, encoding in parts:
            if isinstance(text, bytes):
                decoded.append(text.decode(encoding or "utf-8", errors="ignore"))
            else:
                decoded.append(str(text))
        return "".join(decoded)
    except Exception:
        return str(s)

def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in cdispo:
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="ignore")
                    if body:
                        break
                except Exception:
                    pass
        if not body:
            # Fallback to html stripped or any text part
            for part in msg.walk():
                ctype = part.get_content_type()
                if "text" in ctype:
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        body = part.get_payload(decode=True).decode(charset, errors="ignore")
                        if body:
                            break
                    except Exception:
                        pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        except Exception:
            body = str(msg.get_payload())
    return (body or "").strip()

def run_sync():
    init_replies_table()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Connecting to IMAP as footballstar0325@gmail.com...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login("footballstar0325@gmail.com", "dnbmziwbtrfgfeht")
    mail.select("INBOX", readonly=True)

    # Search criteria:
    # 1. Any message addressed to stehouwer-publishing.com
    # 2. Any message from carrier domains
    msg_ids_set = set()
    
    # Search TO stehouwer-publishing.com
    status, res = mail.search(None, '(TO "stehouwer-publishing.com")')
    if status == "OK" and res[0]:
        for mid in res[0].split():
            msg_ids_set.add(mid)

    # Search FROM carrier domains
    for gw in CARRIER_DOMAINS:
        status, res = mail.search(None, f'(FROM "{gw}")')
        if status == "OK" and res[0]:
            for mid in res[0].split():
                msg_ids_set.add(mid)

    print(f"Total candidate incoming messages to inspect: {len(msg_ids_set)}")

    # Sort descending by ID (most recent first)
    sorted_ids = sorted(list(msg_ids_set), key=lambda x: int(x), reverse=True)
    # Check up to 50 most recent candidate messages
    recent_candidates = sorted_ids[:50]

    new_replies_count = 0
    synced_items = []

    for mid in recent_candidates:
        status, data = mail.fetch(mid, "(RFC822)")
        if status != "OK" or not data or not data[0]:
            continue
        
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        from_raw = decode_mime_words(msg.get("From", ""))
        to_raw = decode_mime_words(msg.get("To", ""))
        subject_raw = decode_mime_words(msg.get("Subject", ""))
        date_raw = msg.get("Date", "")
        body_text = extract_body(msg)

        # Parse date to timestamp
        received_ts = time.time()
        if date_raw:
            try:
                parsed_dt = email.utils.parsedate_to_datetime(date_raw)
                received_ts = parsed_dt.timestamp()
            except Exception:
                pass

        # Extract sender email and phone digits
        sender_email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_raw)
        sender_email = sender_email_match.group(0).lower() if sender_email_match else from_raw.lower()

        # Check for 10-digit phone number in sender address or body
        phone_match = re.search(r'(\d{10})', sender_email)
        sender_phone = ""
        if phone_match:
            raw_digits = phone_match.group(1)
            sender_phone = f"{raw_digits[:3]}-{raw_digits[3:6]}-{raw_digits[6:]}"
        else:
            # Check if from header has phone number
            digits_in_from = re.sub(r'\D', '', from_raw)
            if len(digits_in_from) >= 10:
                d10 = digits_in_from[-10:]
                sender_phone = f"{d10[:3]}-{d10[3:6]}-{d10[6:]}"

        # Combine subject and body for full message text
        full_text = body_text
        if subject_raw and subject_raw not in body_text:
            if not body_text:
                full_text = subject_raw
            else:
                full_text = f"{subject_raw}\n\n{body_text}"

        # Filter out system notifications like Google Cloud cohort emails if not from an athlete
        if "googlecloud@google.com" in sender_email or "no-reply" in sender_email or "mailer-daemon" in sender_email:
            continue

        # Correlation with rec_debut_athletes
        athlete_id = None
        athlete_name = None

        if sender_phone:
            clean_digits = re.sub(r'\D', '', sender_phone)
            cursor.execute("""
                SELECT id, name, sport, high_school, phone, email 
                FROM rec_debut_athletes 
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', '') LIKE ?
            """, (f"%{clean_digits}%",))
            matched_athlete = cursor.fetchone()
            if matched_athlete:
                athlete_id = matched_athlete["id"]
                athlete_name = matched_athlete["name"]

        if not athlete_id and sender_email:
            cursor.execute("SELECT id, name FROM rec_debut_athletes WHERE LOWER(email) = ?", (sender_email,))
            matched_athlete = cursor.fetchone()
            if matched_athlete:
                athlete_id = matched_athlete["id"]
                athlete_name = matched_athlete["name"]

        if not athlete_name:
            # Fallback to name from From header or sender phone
            athlete_name = from_raw.split("<")[0].strip().strip('"') if "<" in from_raw else (sender_phone or sender_email)

        # Hash for deduplication
        msg_hash = f"{sender_email}_{int(received_ts)}_{len(full_text)}"

        try:
            cursor.execute("""
                INSERT INTO rec_debut_athlete_replies 
                (athlete_id, athlete_name, sender_phone, sender_email, recipient_email, subject, reply_body, received_at, is_read, created_at, message_id_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                athlete_id,
                athlete_name,
                sender_phone,
                sender_email,
                to_raw,
                subject_raw,
                full_text,
                received_ts,
                time.time(),
                msg_hash
            ))
            conn.commit()
            new_replies_count += 1
            if athlete_id:
                cursor.execute("UPDATE rec_debut_athletes SET status = 'Replied' WHERE id = ?", (athlete_id,))
                conn.commit()
            synced_items.append({
                "athlete_name": athlete_name,
                "phone": sender_phone,
                "email": sender_email,
                "text": full_text[:100],
                "date": datetime.fromtimestamp(received_ts).strftime("%Y-%m-%d %H:%M:%S")
            })
        except sqlite3.IntegrityError:
            # Already exists in table
            pass

    mail.logout()
    conn.close()

    print(f"\nSync complete! New replies logged: {new_replies_count}")
    for item in synced_items:
        print(f" -> [{item['date']}] {item['athlete_name']} ({item['phone'] or item['email']}): {item['text']}")

if __name__ == "__main__":
    run_sync()
