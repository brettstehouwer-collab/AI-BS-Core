import os
import sys
import time
import json
import sqlite3
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path("C:/AI-BS")
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
SWARM_FILE = BASE_DIR / "saved_data" / "rec_debut_smtp_swarm.json"

CARRIER_GATEWAYS = {
    "verizon": "@vtext.com",
    "att": "@txt.att.net",
    "tmobile": "@tmomail.net",
    "cricket": "@mms.cricketwireless.net",
    "boost": "@myboostmobile.com",
    "us_cellular": "@email.uscc.net",
    "google_fi": "@msg.fi.google.com",
    "sprint": "@pm.sprint.com"
}

DENNIS_CALLER_NAME = "Dennis Bell (+1-616-291-5227)"
DENNIS_CALLER_EMAIL = "dbell002@sbcglobal.net"
DENNIS_CALLER_PHONE = "616-291-5227"

def extract_first_name(full_name: str) -> str:
    if not full_name:
        return "Student-Athlete"
    parts = full_name.strip().split()
    if not parts:
        return "Student-Athlete"
    first = parts[0].strip().title()
    first = "".join(c for c in first if c.isalpha())
    return first if first else "Student-Athlete"

def format_announcement(first_name: str) -> str:
    return f"""Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.

Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.

We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.

If playing college sports is your goal, don’t wait for coaches to find you.

📱 Call or text: 616-291-5227
✅ Register FREE: RecDebut.com
📧 dbell002@sbcglobal.net

Let’s get you recruited!

Dennis Bell
Former New York Knicks
President, Recreational Debut"""

def load_swarm():
    if SWARM_FILE.exists():
        try:
            with open(SWARM_FILE, "r", encoding="utf-8") as f:
                return [a for a in json.load(f) if a.get("active") and a.get("email") and a.get("app_password")]
        except Exception:
            pass
    return []

def send_carrier_sms_single(phone: str, message_text: str, swarm: list) -> tuple:
    digits = "".join(filter(str.isdigit, phone))
    if len(digits) < 10:
        return False, "Invalid phone", None
    ten_digits = digits[-10:]
    target_addresses = [f"{ten_digits}{gw}" for gw in CARRIER_GATEWAYS.values()]

    msg = MIMEText(message_text, "plain", "utf-8")
    msg["From"] = f"{DENNIS_CALLER_NAME} <{DENNIS_CALLER_EMAIL}>"
    msg["Reply-To"] = DENNIS_CALLER_EMAIL
    msg["Subject"] = "Dennis Bell (+1-616-291-5227) - Recreational Debut"
    msg["Date"] = email.utils.formatdate(localtime=True)

    for acct in swarm:
        s_user = acct["email"]
        s_pwd = acct["app_password"]
        s_host = acct.get("smtp_host", "smtp.gmail.com")
        s_port = int(acct.get("smtp_port", 587))
        server = None
        try:
            server = smtplib.SMTP(s_host, s_port, timeout=10.0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(s_user, s_pwd)
            server.sendmail(s_user, target_addresses, msg.as_string())
            server.quit()
            return True, "SENT_SMS", s_user
        except Exception as e:
            if server:
                try: server.close()
                except Exception: pass
            err_str = str(e)
            if "550" in err_str or "daily user sending limit" in err_str.lower():
                continue
            # For transient errors, try next
            continue

    return False, "All swarm accounts hit SMS carrier limit", None

def send_direct_email_single(target_email: str, target_name: str, message_text: str, swarm: list) -> tuple:
    if not target_email or "@" not in target_email:
        return False, "No valid email", None

    first_name = extract_first_name(target_name)
    plain_text = message_text
    html_paragraphs = "".join([f"<p style='margin: 0 0 14px 0; line-height: 1.6; color: #1e293b;'>{line}</p>" for line in plain_text.split("\n\n") if line.strip()])
    html_body = f"""<!DOCTYPE html>
<html>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px;">
    <div style="border-bottom: 2px solid #F58426; padding-bottom: 16px; margin-bottom: 24px;">
      <h2 style="margin: 0; color: #001F3F; font-size: 22px; font-weight: 800;">RECREATIONAL DEBUT</h2>
      <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Dennis Bell Sports Program &bull; College Athletic Recruitment</div>
    </div>
    <div style="font-size: 15px; color: #1e293b;">{html_paragraphs}</div>
    <div style="margin: 28px 0; text-align: center;">
      <a href="https://recdebut.com/all-registration/" style="background-color: #F58426; color: #ffffff; text-decoration: none; font-weight: 800; font-size: 15px; padding: 14px 28px; border-radius: 8px; display: inline-block;">REGISTER FREE RECRUITMENT PROFILE &rarr;</a>
    </div>
    <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; margin-top: 28px; font-size: 12px; color: #94a3b8; line-height: 1.5;">
      <strong>Dennis Bell</strong> &bull; Former New York Knicks #4<br>
      President, Recreational Debut (501c3 Nonprofit)<br>
      Direct Phone: 616-291-5227 &bull; Email: dbell002@sbcglobal.net
    </div>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["To"] = f"{target_name} <{target_email}>"
    msg["From"] = f"{DENNIS_CALLER_NAME} <{DENNIS_CALLER_EMAIL}>"
    msg["Reply-To"] = DENNIS_CALLER_EMAIL
    msg["Subject"] = "Dennis Bell (Former New York Knick) - College Athletic Recruitment Opportunity"
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    for acct in swarm:
        s_user = acct["email"]
        s_pwd = acct["app_password"]
        s_host = acct.get("smtp_host", "smtp.gmail.com")
        s_port = int(acct.get("smtp_port", 587))
        server = None
        try:
            server = smtplib.SMTP(s_host, s_port, timeout=10.0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(s_user, s_pwd)
            server.sendmail(s_user, [target_email], msg.as_string())
            server.quit()
            return True, "SENT_EMAIL", s_user
        except Exception as e:
            if server:
                try: server.close()
                except Exception: pass
            err_str = str(e)
            if "550" in err_str or "daily user sending limit" in err_str.lower():
                continue
            continue

    return False, "All swarm accounts hit direct email limit", None

def main():
    print("=" * 60)
    print("RECREATIONAL DEBUT: FINAL ROSTER OUTREACH DISPATCHER")
    print(f"Caller Identity: {DENNIS_CALLER_NAME} <{DENNIS_CALLER_EMAIL}>")
    print(f"Direct Phone:    {DENNIS_CALLER_PHONE}")
    print("=" * 60)

    swarm = load_swarm()
    print(f"Active Swarm Accounts Loaded: {len(swarm)}")
    for a in swarm:
        print(f" • {a['email']} (Limit: {a.get('daily_limit', 400)})")

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Load coaches for exclusion
    c.execute("SELECT phone FROM rec_debut_excluded_coaches")
    coach_phones = set()
    for row in c.fetchall():
        d = "".join(filter(str.isdigit, row[0] or ""))
        if len(d) >= 10:
            coach_phones.add(d[-10:])
    print(f"Loaded {len(coach_phones)} excluded coach phone signatures.")

    # Load remaining pending athletes
    c.execute("""
        SELECT id, name, phone, email, sport 
        FROM rec_debut_athletes 
        WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'
        ORDER BY id ASC
    """)
    athletes = c.fetchall()
    print(f"Pending Athletes in Queue: {len(athletes)}\n")

    if not athletes:
        print("🎉 No pending athletes remaining! The entire roster is 100% contacted!")
        conn.close()
        return

    sent_count = 0
    skipped_coaches = 0
    delivery_logs = []
    start_time = time.time()

    for idx, (ath_id, name, phone, email_addr, sport) in enumerate(athletes):
        # Coach check
        phone_digits = "".join(filter(str.isdigit, phone or ""))
        if len(phone_digits) >= 10 and phone_digits[-10:] in coach_phones:
            print(f"[{idx+1}/{len(athletes)}] 🛡️ SKIPPED (Coach Quarantined): ID {ath_id} - {name} ({phone})")
            skipped_coaches += 1
            continue

        first_name = extract_first_name(name)
        msg_body = format_announcement(first_name)

        # Primary Channel: Carrier SMS
        ok, channel, acct = send_carrier_sms_single(phone, msg_body, swarm)

        # Fallback Channel: Direct Email if carrier SMS quota is full
        if not ok and email_addr and "@" in email_addr:
            ok, channel, acct = send_direct_email_single(email_addr, name, msg_body, swarm)

        now = time.time()
        if ok:
            sent_count += 1
            c.execute("UPDATE rec_debut_athletes SET last_messaged_at = ?, status = 'Contacted' WHERE id = ?", (now, ath_id))
            conn.commit()
            target_str = phone if channel == "SENT_SMS" else email_addr
            print(f"[{idx+1}/{len(athletes)}] ✅ {channel}: ID {ath_id} | {name} ({first_name}) -> {target_str} (via {acct})")
            delivery_logs.append({
                "athlete_id": ath_id,
                "name": name,
                "first_name": first_name,
                "target": target_str,
                "channel": channel,
                "account": acct,
                "status": "SENT"
            })
            time.sleep(1.2)  # Gentle pacing between sends
        else:
            print(f"[{idx+1}/{len(athletes)}] ⚠️ PAUSED: ID {ath_id} | {name} -> Quota reached across available accounts: {channel}")
            delivery_logs.append({
                "athlete_id": ath_id,
                "name": name,
                "first_name": first_name,
                "target": phone,
                "status": "FAILED",
                "error": channel
            })
            break  # Stop if all channels/accounts are exhausted

    # Record campaign log
    if delivery_logs:
        c.execute("""
            INSERT INTO rec_debut_campaigns
            (created_at, sender_id, total_recipients, successful_count, failed_count, message_body, delivery_details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            start_time,
            DENNIS_CALLER_EMAIL,
            len(delivery_logs),
            sent_count,
            len(delivery_logs) - sent_count,
            format_announcement("{first_name}"),
            json.dumps(delivery_logs)
        ))
        conn.commit()

    # Final tally
    c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")
    total_contacted = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rec_debut_athletes")
    total_roster = c.fetchone()[0]
    pending_now = total_roster - total_contacted

    print("\n" + "=" * 60)
    print(f"DISPATCH BATCH COMPLETE:")
    print(f" • Successfully Sent This Run: {sent_count}")
    print(f" • Total Contacted & Verified:  {total_contacted} / {total_roster} ({total_contacted/total_roster*100:.1f}%)")
    print(f" • Remaining Pending:           {pending_now}")
    print("=" * 60)

    conn.close()

if __name__ == "__main__":
    main()
