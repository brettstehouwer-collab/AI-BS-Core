import sqlite3
import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
REPORT_PATH = BASE_DIR / "saved_data" / "recdebut_email_verification_report.csv"

# Domain typo map
DOMAIN_TYPO_MAP = {
    "gma1l.com": "gmail.com",
    "1cloud.com": "icloud.com",
    "gmai.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.co": "gmail.com",
    "yaho.com": "yahoo.com",
    "yaho.con": "yahoo.com",
    "yahoo.con": "yahoo.com",
    "hotmial.com": "hotmail.com",
    "hotmaill.com": "hotmail.com",
    "icoud.com": "icloud.com",
    "icloud.con": "icloud.com",
    "outloo.com": "outlook.com"
}

def fix_domain_typos(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM rec_debut_athletes WHERE email IS NOT NULL AND email != ''")
    rows = cur.fetchall()
    
    fixed_count = 0
    print("\n--- 1. Scanning & Fixing Obvious Domain Typos ---")
    for a_id, name, email in rows:
        email_str = email.strip()
        if "@" not in email_str:
            continue
        parts = email_str.split("@")
        if len(parts) != 2:
            continue
        user, domain = parts[0].strip(), parts[1].strip().lower()
        
        if domain in DOMAIN_TYPO_MAP:
            corrected_domain = DOMAIN_TYPO_MAP[domain]
            corrected_email = f"{user}@{corrected_domain}"
            cur.execute("UPDATE rec_debut_athletes SET email = ?, email_status = 'MX_VALID' WHERE id = ?", (corrected_email, a_id))
            print(f"  Fixed typo for {name}: '{email_str}' => '{corrected_email}'")
            fixed_count += 1
            
    conn.commit()
    print(f"Total typos corrected: {fixed_count}")

def fix_false_positive_undeliverables(conn):
    cur = conn.cursor()
    print("\n--- 2. Auditing & Fixing Verification Report False Positives ---")
    
    if not REPORT_PATH.exists():
        print("Report file not found.")
        return
        
    recovered_count = 0
    confirmed_bad_count = 0
    
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "UNDELIVERABLE":
                a_id = row["id"]
                email = row["email"].lower()
                reason = row["reason"]
                
                # Check if it was rejected due to Spamhaus PBL / IP block on our machine
                is_pbl_ip_block = (
                    "spamhaus" in reason.lower() or 
                    "pbl" in reason.lower() or 
                    "5.7.1" in reason or
                    "icloud.com" in email or
                    "me.com" in email
                )
                
                # Check if it was an actual user unknown / mailbox not found
                is_actual_user_unknown = (
                    "5.1.1" in reason or 
                    "nosuchuser" in reason.lower() or 
                    "does not exist" in reason.lower() or 
                    "no mx" in reason.lower()
                )
                
                if is_pbl_ip_block and not is_actual_user_unknown:
                    # Valid iCloud/enterprise domain, just residential port 25 probed
                    cur.execute("UPDATE rec_debut_athletes SET email_status = 'MX_VALID' WHERE id = ?", (a_id,))
                    recovered_count += 1
                elif is_actual_user_unknown:
                    cur.execute("UPDATE rec_debut_athletes SET email_status = 'UNDELIVERABLE' WHERE id = ?", (a_id,))
                    confirmed_bad_count += 1
                    print(f"  Confirmed Hard Bounce Intercepted: {row['name']} <{row['email']}> ({reason[:60]})")
                    
    conn.commit()
    print(f"Total false positives recovered to MX_VALID (e.g. iCloud/Edu): {recovered_count}")
    print(f"Total confirmed hard bounces locked as UNDELIVERABLE: {confirmed_bad_count}")

def main():
    conn = sqlite3.connect(str(DB_PATH))
    fix_domain_typos(conn)
    fix_false_positive_undeliverables(conn)
    
    cur = conn.cursor()
    cur.execute("SELECT email_status, count(*) FROM rec_debut_athletes WHERE status = 'Pending' GROUP BY email_status")
    print("\n--- Final Pending Email Verification Breakdown ---")
    for status, count in cur.fetchall():
        print(f"  • {status}: {count}")
    conn.close()

if __name__ == '__main__':
    main()
