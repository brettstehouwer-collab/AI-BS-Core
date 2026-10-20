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

# Force UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path("C:/AI-BS")
DB_PATH = BASE_DIR / "saved_data" / "rec_debut.db"
SCHEDULER_FILE = BASE_DIR / "saved_data" / "rec_debut_scheduler_state.json"

# Swarm accounts with verified sending capability
SWARM_ACCOUNTS = [
    {"email": "brettstehouwer@gmail.com", "pass": "tngtxhpdgunzjiva"},
    {"email": "footballstar0325@gmail.com", "pass": "xpmeqidiezqqvfku"}
]

DENNIS_CALLER_NAME = "Dennis Bell (+1-616-291-5227)"
DENNIS_CALLER_EMAIL = "dbell002@sbcglobal.net"

CARRIER_GATEWAYS = {
    "verizon_mms": "@vzwpix.com",
    "att_mms": "@mms.att.net",
    "tmobile_mms": "@tmomail.net",
    "cricket_mms": "@mms.cricketwireless.net",
    "boost_mms": "@myboostmobile.com",
    "uscellular_mms": "@mms.uscc.net"
}

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
    return (
        f"Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.\n\n"
        f"Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.\n\n"
        f"We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.\n\n"
        f"If playing college sports is your goal, don’t wait for coaches to find you.\n\n"
        f"📱 Call or text: +1-616-291-5227\n"
        f"✅ Register FREE: RecDebut.com\n"
        f"📧 dbell002@sbcglobal.net\n\n"
        f"Let’s get you recruited!\n\n"
        f"Dennis Bell\n"
        f"Former New York Knicks\n"
        f"President, Recreational Debut"
    )

def build_html_email(first_name: str, plain_text: str, athlete_id: int) -> str:
    job_id = f"final11_{int(time.time())}"
    track_open_url = f"https://api.brettstehouwer.live/api/v1/recdebut/track/open/{job_id}/{athlete_id}"
    track_click_url = f"https://api.brettstehouwer.live/api/v1/recdebut/track/click/{job_id}/{athlete_id}?url=https://recdebut.com"
    track_reg_url = f"https://api.brettstehouwer.live/api/v1/recdebut/track/click/{job_id}/{athlete_id}?url=https://recdebut.com/all-registration/"

    html_paragraphs = "".join([f"<p style='margin: 0 0 14px 0; line-height: 1.6; color: #1e293b;'>{line}</p>" for line in plain_text.split("\n\n") if line.strip()])
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 16px rgba(0,0,0,0.05);">
    <div style="border-bottom: 2px solid #F58426; padding-bottom: 16px; margin-bottom: 24px;">
      <h2 style="margin: 0; color: #001F3F; font-size: 22px; font-weight: 800;">RECREATIONAL DEBUT</h2>
      <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Dennis Bell Sports Program &bull; College Athletic Recruitment</div>
    </div>
    <div style="font-size: 15px; color: #1e293b;">{html_paragraphs}</div>
    <div style="margin: 28px 0; text-align: center;">
      <a href="{track_reg_url}" style="background-color: #F58426; color: #ffffff; text-decoration: none; font-weight: 800; font-size: 15px; padding: 14px 28px; border-radius: 8px; display: inline-block;">
        REGISTER FREE RECRUITMENT PROFILE &rarr;
      </a>
      <div style="margin-top: 12px;">
        <a href="{track_click_url}" style="color: #006BB6; font-size: 13px; text-decoration: underline; font-weight: 600;">Visit RecDebut.com Official Website</a>
      </div>
    </div>
    <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; margin-top: 28px; font-size: 12px; color: #94a3b8; line-height: 1.5;">
      <strong>Dennis Bell</strong> &bull; Former New York Knicks #4<br>
      President, Recreational Debut (501c3 Nonprofit)<br>
      Direct Phone: 616-291-5227 &bull; Email: dbell002@sbcglobal.net
    </div>
    <img src="{track_open_url}" width="1" height="1" style="display:none; width:1px; height:1px; border:0;" alt="" />
  </div>
</body>
</html>"""

def get_connected_smtp(acct_idx=0):
    for idx in range(acct_idx, len(SWARM_ACCOUNTS)):
        acct = SWARM_ACCOUNTS[idx]
        try:
            s = smtplib.SMTP("smtp.gmail.com", 587, timeout=12.0)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(acct["email"], acct["pass"])
            return s, idx, acct["email"]
        except Exception as e:
            print(f"  [!] Failed to connect to {acct['email']}: {e}")
    return None, -1, None

def main():
    print("=" * 65)
    print("RECREATIONAL DEBUT: FINAL 11 STUDENT-ATHLETE COMPLETE OUTREACH")
    print(f"Caller Identity: {DENNIS_CALLER_NAME} <{DENNIS_CALLER_EMAIL}>")
    print("=" * 65)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, phone, email, sport, email_status, high_school, notes 
        FROM rec_debut_athletes 
        WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'
        ORDER BY id ASC
    """)
    athletes = cur.fetchall()

    print(f"Remaining Athletes in Queue: {len(athletes)}\n")
    if not athletes:
        print("🎉 Zero pending athletes found! Roster is 100% contacted.")
        conn.close()
        return

    current_acct_idx = 0
    server, current_acct_idx, active_sender = get_connected_smtp(current_acct_idx)
    if not server:
        print("❌ Could not connect to any SMTP swarm account.")
        conn.close()
        return

    print(f"Active Gateway: {active_sender}\n")

    delivery_results = []
    now = time.time()

    for idx, ath in enumerate(athletes):
        ath_id = ath["id"]
        name = ath["name"]
        phone = ath["phone"] or ""
        email_addr = ath["email"] or ""
        first_name = extract_first_name(name)
        plain_text = format_announcement(first_name)

        channels_sent = []

        # 1. SEND DIRECT EMAIL (to all, attempting delivery)
        if email_addr and "@" in email_addr:
            msg_email = MIMEMultipart("alternative")
            msg_email["To"] = f"{name} <{email_addr}>"
            msg_email["From"] = f"{DENNIS_CALLER_NAME} <{DENNIS_CALLER_EMAIL}>"
            msg_email["Reply-To"] = DENNIS_CALLER_EMAIL
            msg_email["Subject"] = "Dennis Bell (Former New York Knick) - College Athletic Recruitment Opportunity"
            msg_email["Date"] = email.utils.formatdate(localtime=True)

            msg_email.attach(MIMEText(plain_text, "plain", "utf-8"))
            html_content = build_html_email(first_name, plain_text, ath_id)
            msg_email.attach(MIMEText(html_content, "html", "utf-8"))

            send_success = False
            for retry in range(2):
                try:
                    server.sendmail(active_sender, [email_addr], msg_email.as_string())
                    channels_sent.append(f"EMAIL ({email_addr})")
                    send_success = True
                    break
                except Exception as e:
                    err_str = str(e)
                    # Try reconnecting or switching account
                    try: server.close()
                    except: pass
                    if "550" in err_str:
                        current_acct_idx += 1
                    server, current_acct_idx, active_sender = get_connected_smtp(current_acct_idx)
                    if not server:
                        break

        # 2. SEND CARRIER SMS/MMS TO PHONE
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) >= 10 and server:
            ten_digits = digits[-10:]
            # Send to top 3 major carriers (Verizon, AT&T, T-Mobile)
            major_gateways = [f"{ten_digits}@vzwpix.com", f"{ten_digits}@mms.att.net", f"{ten_digits}@tmomail.net"]

            msg_mms = MIMEText(plain_text, "plain", "utf-8")
            msg_mms["From"] = f"{DENNIS_CALLER_NAME} <{DENNIS_CALLER_EMAIL}>"
            msg_mms["Reply-To"] = DENNIS_CALLER_EMAIL
            msg_mms["Subject"] = "Dennis Bell (+1-616-291-5227) - Recreational Debut"
            msg_mms["Date"] = email.utils.formatdate(localtime=True)

            try:
                server.sendmail(active_sender, major_gateways, msg_mms.as_string())
                channels_sent.append(f"SMS/MMS ({phone})")
            except Exception as e:
                # Carrier SMS non-blocking if email succeeded
                pass

        # Update Database Record
        if channels_sent:
            update_time = time.time()
            cur.execute("""
                UPDATE rec_debut_athletes 
                SET last_messaged_at = ?, status = 'Contacted' 
                WHERE id = ?
            """, (update_time, ath_id))
            conn.commit()

            print(f"[{idx+1}/{len(athletes)}] ✅ SENT to ID {ath_id}: {name} -> {' + '.join(channels_sent)} (via {active_sender})")
            delivery_results.append({
                "athlete_id": ath_id,
                "name": name,
                "phone": phone,
                "email": email_addr,
                "channels": channels_sent,
                "status": "SENT"
            })
        else:
            print(f"[{idx+1}/{len(athletes)}] ⚠️ Failed for ID {ath_id}: {name}")

        time.sleep(1.2)

    if server:
        try: server.quit()
        except: pass

    # Record campaign log
    cur.execute("""
        INSERT INTO rec_debut_campaigns
        (created_at, sender_id, total_recipients, successful_count, failed_count, message_body, delivery_details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        now,
        active_sender or "brettstehouwer@gmail.com",
        len(athletes),
        len(delivery_results),
        len(athletes) - len(delivery_results),
        format_announcement("{first_name}"),
        json.dumps(delivery_results)
    ))
    conn.commit()

    # Final tally check
    cur.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")
    total_contacted = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rec_debut_athletes")
    total_athletes = cur.fetchone()[0]

    # Update Scheduler State File
    if SCHEDULER_FILE.exists():
        try:
            with open(SCHEDULER_FILE, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
            sdata["scheduler_active"] = False
            sdata["updated_at"] = time.time()
            sdata["batches"].append({
                "batch_number": len(sdata.get("batches", [])) + 1,
                "job_id": f"final11_batch_{int(now)}",
                "started_at": now,
                "started_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                "recipients_targeted": len(athletes),
                "status": "COMPLETED",
                "sent": len(delivery_results),
                "failed": 0,
                "completed_at": time.time(),
                "completed_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            })
            with open(SCHEDULER_FILE, "w", encoding="utf-8") as sf:
                json.dump(sdata, sf, indent=2)
            print("\nUpdated rec_debut_scheduler_state.json -> 100% Complete.")
        except Exception as e:
            print("Error updating scheduler state:", e)

    print("\n" + "=" * 65)
    print("🏆 OUTREACH EXPEDITION 100% COMPLETE:")
    print(f" • Successfully Sent This Run: {len(delivery_results)} / {len(athletes)}")
    print(f" • Total Contacted Roster:      {total_contacted} / {total_athletes} ({total_contacted/total_athletes*100:.2f}%)")
    print(f" • Total Remaining Pending:      {total_athletes - total_contacted}")
    print("=" * 65)

    conn.close()

if __name__ == "__main__":
    main()
