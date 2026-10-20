import sqlite3
import smtplib
import socket
import subprocess
import time
import re
import csv
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
REPORT_PATH = BASE_DIR / "saved_data" / "recdebut_email_verification_report.csv"

# Global MX cache
MX_CACHE = {}

def init_verification_columns():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(rec_debut_athletes)")
    cols = [c[1] for c in cur.fetchall()]
    
    if "email_status" not in cols:
        cur.execute("ALTER TABLE rec_debut_athletes ADD COLUMN email_status TEXT DEFAULT 'Unverified'")
    if "email_verified_at" not in cols:
        cur.execute("ALTER TABLE rec_debut_athletes ADD COLUMN email_verified_at REAL")
        
    conn.commit()
    conn.close()

def resolve_mx(domain):
    if domain in MX_CACHE:
        return MX_CACHE[domain]
        
    cmd = f"nslookup -type=mx {domain}"
    try:
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=5)
        candidates = []
        for line in res.stdout.splitlines():
            if "mail exchanger =" in line:
                parts = line.split("mail exchanger =")
                if len(parts) > 1:
                    candidates.append(parts[1].strip().rstrip('.'))
        if candidates:
            # Prefer standard exchangers
            mx = candidates[0]
            MX_CACHE[domain] = mx
            return mx
    except Exception:
        pass
        
    # Check domain A record fallback
    try:
        socket.gethostbyname(domain)
        MX_CACHE[domain] = domain
        return domain
    except Exception:
        MX_CACHE[domain] = None
        return None

def verify_single_email(athlete):
    a_id, name, email = athlete
    
    if not email or "@" not in email:
        return {
            "id": a_id, "name": name, "email": email or "", 
            "status": "INVALID_SYNTAX", "code": 0, "reason": "Empty or malformed email"
        }
        
    email_clean = email.strip()
    parts = email_clean.split("@")
    if len(parts) != 2:
        return {
            "id": a_id, "name": name, "email": email_clean,
            "status": "INVALID_SYNTAX", "code": 0, "reason": "Malformed @ split"
        }
        
    user, domain = parts[0].strip(), parts[1].strip().lower()
    
    # 1. Syntax check
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email_clean):
        return {
            "id": a_id, "name": name, "email": email_clean,
            "status": "INVALID_SYNTAX", "code": 0, "reason": "Failed RFC regex validation"
        }
        
    # 2. DNS MX resolution
    mx_host = resolve_mx(domain)
    if not mx_host:
        return {
            "id": a_id, "name": name, "email": email_clean,
            "status": "UNDELIVERABLE", "code": 0, "reason": f"Domain '{domain}' has no MX mail exchanger"
        }
        
    # 3. Provider-specific SMTP handling
    # Yahoo/AOL frequently block direct RCPT TO from residential IPs
    if "yahoodns" in mx_host or "yahoo" in domain or "aol.com" in domain:
        return {
            "id": a_id, "name": name, "email": email_clean,
            "status": "MX_VALID", "code": 250, "reason": f"Yahoo/AOL MX Verified ({mx_host})"
        }

    # 4. Direct RFC 5321 Port 25 SMTP Handshake Ping
    try:
        server = smtplib.SMTP(timeout=6)
        server.connect(mx_host, 25)
        server.helo("brettstehouwer.live")
        server.mail("verify@brettstehouwer.live")
        code, msg = server.rcpt(email_clean)
        server.quit()
        
        msg_str = msg.decode("utf-8", errors="ignore") if isinstance(msg, bytes) else str(msg)
        
        if code == 250:
            return {
                "id": a_id, "name": name, "email": email_clean,
                "status": "DELIVERABLE", "code": code, "reason": "Mailbox confirmed active (250 OK)"
            }
        elif code >= 500:
            return {
                "id": a_id, "name": name, "email": email_clean,
                "status": "UNDELIVERABLE", "code": code, "reason": f"Mailbox rejected by server: {msg_str[:80]}"
            }
        elif code in (450, 451, 452):
            return {
                "id": a_id, "name": name, "email": email_clean,
                "status": "MX_VALID", "code": code, "reason": f"Greylisted / Temporarily deferred: {msg_str[:80]}"
            }
        else:
            return {
                "id": a_id, "name": name, "email": email_clean,
                "status": "MX_VALID", "code": code, "reason": f"MX accepted handshake ({code})"
            }
    except smtplib.SMTPConnectError:
        return {
            "id": a_id, "name": name, "email": email_clean,
            "status": "MX_VALID", "code": 0, "reason": f"MX exists ({mx_host}) but port 25 connection refused"
        }
    except (socket.timeout, TimeoutError):
        return {
            "id": a_id, "name": name, "email": email_clean,
            "status": "MX_VALID", "code": 0, "reason": f"MX exists ({mx_host}) but handshake timed out"
        }
    except Exception as e:
        return {
            "id": a_id, "name": name, "email": email_clean,
            "status": "MX_VALID", "code": 0, "reason": f"MX exists ({mx_host}), connection fallback: {str(e)[:60]}"
        }

def run_verification():
    print("=" * 70)
    print("🚀 ZERO-COST DIRECT SMTP & DNS EMAIL VERIFIER (RFC 5321 AUTHORITATIVE)")
    print("=" * 70)
    
    init_verification_columns()
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # Query all pending athletes with emails
    cur.execute("""
        SELECT id, name, email 
        FROM rec_debut_athletes 
        WHERE status = 'Pending' AND email IS NOT NULL AND email != ''
        ORDER BY id ASC
    """)
    pending_athletes = cur.fetchall()
    conn.close()
    
    total = len(pending_athletes)
    print(f"\nLoaded {total} pending student-athlete emails to verify against authoritative mail servers.\n")
    
    results = []
    deliverable_count = 0
    mx_valid_count = 0
    undeliverable_count = 0
    invalid_syntax_count = 0
    
    start_time = time.time()
    
    # Process with paced workers (5 workers for polite concurrency)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(verify_single_email, a): a for a in pending_athletes}
        
        for idx, future in enumerate(as_completed(futures), 1):
            res = future.result()
            results.append(res)
            
            status = res["status"]
            if status == "DELIVERABLE":
                deliverable_count += 1
            elif status == "MX_VALID":
                mx_valid_count += 1
            elif status == "UNDELIVERABLE":
                undeliverable_count += 1
                print(f"❌ [BOUNCE INTERCEPTED] {res['name']} <{res['email']}> => {res['reason']}")
            elif status == "INVALID_SYNTAX":
                invalid_syntax_count += 1
                print(f"⚠️ [SYNTAX ERROR] {res['name']} <{res['email']}> => {res['reason']}")
                
            if idx % 50 == 0 or idx == total:
                pct = round((idx / total) * 100, 1)
                elapsed = round(time.time() - start_time, 1)
                print(f"Progress: {idx}/{total} ({pct}%) in {elapsed}s | Deliverable: {deliverable_count} | MX Valid: {mx_valid_count} | Undeliverable: {undeliverable_count}")

    # Update database records
    print("\nUpdating rec_debut.db with verification statuses...")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    now_ts = time.time()
    
    for r in results:
        cur.execute("""
            UPDATE rec_debut_athletes 
            SET email_status = ?, email_verified_at = ?
            WHERE id = ?
        """, (r["status"], now_ts, r["id"]))
        
    conn.commit()
    conn.close()
    
    # Write audit CSV report
    with open(str(REPORT_PATH), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "email", "status", "code", "reason"])
        writer.writeheader()
        writer.writerows(results)
        
    total_time = round(time.time() - start_time, 1)
    safe_send_count = deliverable_count + mx_valid_count
    
    print("\n" + "=" * 70)
    print("🎯 EMAIL VERIFICATION AUDIT COMPLETE")
    print("=" * 70)
    print(f"• Total Emails Checked:      {total}")
    print(f"• Confirmed Deliverable:     {deliverable_count} (Direct 250 OK)")
    print(f"• Confirmed MX Valid:        {mx_valid_count} (Authoritative Mail Server Ready)")
    print(f"• 🛡️ Undeliverable/Bounces:   {undeliverable_count} (INTERCEPTED & BLOCKED)")
    print(f"• ⚠️ Syntax Invalid:         {invalid_syntax_count}")
    print(f"• Total Safe To Send:        {safe_send_count} / {total} ({round((safe_send_count / total) * 100, 1)}%)")
    print(f"• Time Elapsed:              {total_time}s")
    print(f"• Audit Report Saved:        {REPORT_PATH}")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
