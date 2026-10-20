import sqlite3
import smtplib
import socket
import subprocess
import time
import re

# MX Cache to avoid redundant DNS lookups
MX_CACHE = {}

def get_mx_server(domain):
    if domain in MX_CACHE:
        return MX_CACHE[domain]
    
    cmd = f"nslookup -type=mx {domain}"
    try:
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=5)
        mx_candidates = []
        for line in res.stdout.splitlines():
            if "mail exchanger =" in line:
                parts = line.split("mail exchanger =")
                if len(parts) > 1:
                    mx_candidates.append(parts[1].strip().rstrip('.'))
        
        if mx_candidates:
            # Sort to prefer primary or alt
            mx_host = mx_candidates[0]
            MX_CACHE[domain] = mx_host
            return mx_host
    except Exception:
        pass
        
    try:
        socket.gethostbyname(domain)
        MX_CACHE[domain] = domain
        return domain
    except Exception:
        MX_CACHE[domain] = None
        return None

def verify_email_smtp(email):
    if not email or "@" not in email:
        return {"status": "INVALID_SYNTAX", "code": 0, "msg": "Missing or malformed email"}
    
    parts = email.strip().split("@")
    if len(parts) != 2:
        return {"status": "INVALID_SYNTAX", "code": 0, "msg": "Malformed email address"}
        
    user, domain = parts[0].strip(), parts[1].strip().lower()
    
    # 1. Syntax check
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return {"status": "INVALID_SYNTAX", "code": 0, "msg": "RFC Syntax failure"}
        
    # 2. MX check
    mx_host = get_mx_server(domain)
    if not mx_host:
        return {"status": "NO_MX_RECORDS", "code": 0, "msg": f"Domain {domain} has no valid mail exchanger"}
        
    # 3. Direct SMTP Ping (RCPT TO)
    try:
        server = smtplib.SMTP(timeout=8)
        server.connect(mx_host, 25)
        server.helo("brettstehouwer.live")
        server.mail("verify@brettstehouwer.live")
        code, msg = server.rcpt(email)
        server.quit()
        
        msg_str = msg.decode("utf-8", errors="ignore") if isinstance(msg, bytes) else str(msg)
        
        if code == 250:
            return {"status": "DELIVERABLE", "code": code, "msg": msg_str, "mx": mx_host}
        elif code >= 500:
            return {"status": "UNDELIVERABLE", "code": code, "msg": msg_str, "mx": mx_host}
        else:
            return {"status": "RISKY_DEFERRED", "code": code, "msg": msg_str, "mx": mx_host}
    except smtplib.SMTPConnectError as e:
        return {"status": "CONNECTION_REFUSED", "code": 0, "msg": str(e), "mx": mx_host}
    except socket.timeout:
        return {"status": "TIMEOUT", "code": 0, "msg": "Connection timed out", "mx": mx_host}
    except Exception as e:
        return {"status": "ERROR", "code": 0, "msg": str(e), "mx": mx_host}

def test_sample():
    conn = sqlite3.connect("saved_data/rec_debut.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM rec_debut_athletes WHERE status = 'Pending' AND email IS NOT NULL AND email != '' LIMIT 10")
    sample = cur.fetchall()
    conn.close()
    
    print(f"Testing direct email verification on {len(sample)} sample pending athletes...\n")
    for a_id, name, email in sample:
        t0 = time.time()
        res = verify_email_smtp(email)
        elapsed = round(time.time() - t0, 2)
        print(f"[{res['status']}] {name} <{email}> (Code: {res['code']}) in {elapsed}s | MX: {res.get('mx', 'None')}")
        time.sleep(0.5)

if __name__ == "__main__":
    test_sample()
