import os
import sys
import time
import json
import sqlite3
import smtplib
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from pathlib import Path

DB_PATH = Path(r"C:\AI-BS\saved_data\rec_debut.db")
SWARM_PATH = Path(r"C:\AI-BS\saved_data\rec_debut_smtp_swarm.json")
LOG_PATH = Path(r"C:\AI-BS\logs\recdebut_email_dispatch.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

DENNIS_EMAIL = "dbell002@sbcglobal.net"
MAILING_ADDRESS = "Recreational Debut - Dennis Bell (Former NY Knick), 1475 Edgeknoll Dr SE, Kentwood, MI 49508"

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def load_swarm():
    with open(SWARM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def format_email_body(first_name: str, athlete_id: int):
    name = first_name.strip() if first_name else "Student-Athlete"
    text = f"""Hi {name},

WHICH EMAIL WOULD YOU OPEN FIRST?
1. "Former NBA Player Recommends Outstanding Student-Athlete"
2. "Coach Johnson Recommends Outstanding Student-Athlete"

In recruiting, getting noticed FIRST matters.

You can spend thousands with other recruiting organizations-but if their email never gets opened, what are you really paying for?

At Recreational Debut, we use our experience, relationships and credibility to help your portfolio STAND OUT in a crowded inbox.

Don't just send emails. GET NOTICED.

Go to https://recdebut.com/all-registration/ and register free today. If you're serious about getting recruited, become part of the Recreational Debut family.
Dennis Bell
NY KNICKS

Watch the Recreational Debut video:
https://youtu.be/YJoPHIWmvnQ

---
{MAILING_ADDRESS}
To stop receiving recruitment updates, reply UNSUBSCRIBE.
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 16px rgba(0,0,0,0.05);">
    <div style="border-bottom: 2px solid #F58426; padding-bottom: 16px; margin-bottom: 24px;">
      <h2 style="margin: 0; color: #001F3F; font-size: 22px; font-weight: 800; letter-spacing: 0.5px;">RECREATIONAL DEBUT</h2>
      <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Dennis Bell Sports Program &bull; College Athletic Recruitment</div>
    </div>
    <div style="font-size: 15px; color: #1e293b; line-height: 1.6;">
      <p style="margin: 0 0 14px 0;">Hi {name},</p>
      <p style="margin: 0 0 14px 0; font-weight: 700; color: #001F3F;">WHICH EMAIL WOULD YOU OPEN FIRST?<br>
      1. &ldquo;Former NBA Player Recommends Outstanding Student-Athlete&rdquo;<br>
      2. &ldquo;Coach Johnson Recommends Outstanding Student-Athlete&rdquo;</p>
      <p style="margin: 0 0 14px 0;">In recruiting, getting noticed <strong>FIRST</strong> matters.</p>
      <p style="margin: 0 0 14px 0;">You can spend thousands with other recruiting organizations&mdash;but if their email never gets opened, what are you really paying for?</p>
      <p style="margin: 0 0 14px 0;">At Recreational Debut, we use our experience, relationships and credibility to help your portfolio <strong>STAND OUT</strong> in a crowded inbox.</p>
      <p style="margin: 0 0 14px 0; font-size: 17px; font-weight: 800; color: #F58426;">Don&rsquo;t just send emails. GET NOTICED.</p>
      <div style="margin: 24px 0; text-align: center;">
        <a href="https://recdebut.com/all-registration/" style="background-color: #F58426; color: #ffffff; text-decoration: none; font-weight: 800; font-size: 15px; padding: 14px 28px; border-radius: 8px; display: inline-block; box-shadow: 0 4px 12px rgba(245, 132, 38, 0.35);">
          REGISTER FREE RECRUITMENT PROFILE &rarr;
        </a>
      </div>
      <p style="margin: 0 0 14px 0;">If you&rsquo;re serious about getting recruited, become part of the Recreational Debut family.<br>
      <strong>Dennis Bell</strong><br>
      NY KNICKS</p>
      <p style="margin: 14px 0 0 0;">
        <strong>Watch Dennis Bell's Video:</strong><br>
        <a href="https://youtu.be/YJoPHIWmvnQ" style="color: #006BB6; text-decoration: underline; font-weight: 600;">https://youtu.be/YJoPHIWmvnQ</a>
      </p>
    </div>
    <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; margin-top: 28px; font-size: 12px; color: #94a3b8; line-height: 1.5;">
      <strong>Dennis Bell</strong> &bull; Former New York Knicks #4<br>
      President, Recreational Debut (501c3 Nonprofit)<br>
      Direct Phone: 616-291-5227 &bull; Email: dbell002@sbcglobal.net<br>
      {MAILING_ADDRESS}<br>
      <span style="color: #cbd5e1;">To stop receiving recruitment updates, reply UNSUBSCRIBE.</span>
    </div>
  </div>
</body>
</html>"""
    return text, html

def connect_worker(worker):
    server = smtplib.SMTP(worker["smtp_host"], worker.get("smtp_port", 587), timeout=20)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(worker["email"], worker["app_password"])
    return server

def send_dispatch(batch_limit: int = 750, dry_run: bool = False):
    start_time = time.time()
    log(f"=== Starting RecDebut Email Dispatch (Batch Limit: {batch_limit}, Dry Run: {dry_run}) ===")
    swarm = load_swarm()
    active_workers = [w for w in swarm if w.get("active")]
    if not active_workers:
        log("[ERROR] No active SMTP workers found in swarm.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, phone, sport, high_school, grad_year, city_state
        FROM rec_debut_athletes
        WHERE email IS NOT NULL AND email != ''
          AND email_status != 'UNDELIVERABLE'
          AND (status IS NULL OR status = 'Pending' OR status = 'Selected')
        ORDER BY id ASC
        LIMIT ?
    """, (batch_limit,))
    athletes = cursor.fetchall()

    total_queue = len(athletes)
    log(f"Fetched {total_queue} eligible athletes for dispatch.")
    if not athletes:
        log("No eligible pending athletes found.")
        conn.close()
        return

    smtp_servers = {}
    session_counts = {}

    def get_smtp(worker):
        email_addr = worker["email"]
        # Refresh connection after 20 sends to prevent session limits on Ionos/Gmail
        if session_counts.get(email_addr, 0) >= 20:
            if email_addr in smtp_servers:
                try:
                    smtp_servers[email_addr].quit()
                except Exception:
                    pass
                smtp_servers.pop(email_addr, None)
            session_counts[email_addr] = 0

        if email_addr in smtp_servers:
            try:
                status = smtp_servers[email_addr].noop()[0]
                if status == 250:
                    return smtp_servers[email_addr]
            except Exception:
                try:
                    smtp_servers[email_addr].quit()
                except Exception:
                    pass
                smtp_servers.pop(email_addr, None)
        
        server = connect_worker(worker)
        smtp_servers[email_addr] = server
        session_counts[email_addr] = 0
        return server

    worker_idx = 0
    delivered_count = 0
    failed_count = 0

    for idx, ath in enumerate(athletes, 1):
        ath_id = ath["id"]
        ath_name = (ath["name"] or "").strip()
        first_name = ath_name.split()[0] if ath_name else "Student-Athlete"
        ath_email = ath["email"].strip()
        ath_sport = ath["sport"] or "Basketball"
        ath_school = ath["high_school"] or ""
        ath_grad = ath["grad_year"] or ""

        if "@" not in ath_email:
            log(f"[SKIP] Invalid email format: {ath_email} (Athlete #{ath_id})")
            continue

        worker = active_workers[worker_idx % len(active_workers)]
        worker_idx += 1
        worker_email = worker["email"]

        plain_text, html_body = format_email_body(first_name, ath_id)

        # 1. Prepare athlete email
        msg = MIMEMultipart("alternative")
        msg["To"] = f"{ath_name} <{ath_email}>"
        msg["From"] = f"Dennis Bell <{worker_email}>"
        msg["Reply-To"] = DENNIS_EMAIL
        msg["Subject"] = "Get Noticed - Recreational Debut"
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["List-Unsubscribe"] = f"<mailto:{DENNIS_EMAIL}?subject=unsubscribe>"
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if dry_run:
            log(f"[{idx}/{total_queue}] [DRY-RUN] To: {ath_name} <{ath_email}> via {worker_email} + forward to Dennis.")
            delivered_count += 1
            continue

        sent_to_athlete = False
        retry_count = 0
        while retry_count < 2 and not sent_to_athlete:
            try:
                # Update From header to match the current worker
                del msg["From"]
                msg["From"] = f"Dennis Bell <{worker_email}>"

                server = get_smtp(worker)
                server.sendmail(worker_email, [ath_email], msg.as_string())
                session_counts[worker_email] = session_counts.get(worker_email, 0) + 1
                sent_to_athlete = True
                log(f"[{idx}/{total_queue}] [DELIVERED] Sent athlete email #{ath_id} ({ath_name} <{ath_email}>) via {worker_email}")
            except Exception as e:
                err_str = str(e)
                log(f"[WARN] Send to {ath_email} failed via {worker_email}: {err_str} (attempt {retry_count+1})")
                smtp_servers.pop(worker_email, None)
                session_counts[worker_email] = 0
                retry_count += 1
                if "quota" in err_str.lower() or "550" in err_str:
                    log(f"[QUOTA] Worker {worker_email} hit daily quota; rotating away.")
                    if worker in active_workers and len(active_workers) > 1:
                        active_workers.remove(worker)
                        worker = active_workers[worker_idx % len(active_workers)]
                        worker_email = worker["email"]
                time.sleep(1.0)

        if not sent_to_athlete:
            failed_count += 1
            log(f"[{idx}/{total_queue}] [FAILED] Athlete #{ath_id} ({ath_email}) could not be delivered.")
            continue

        # 2. Forward delivery copy to Dennis Bell
        try:
            fwd = MIMEMultipart("alternative")
            fwd["To"] = f"Dennis Bell <{DENNIS_EMAIL}>"
            fwd["From"] = f"RecDebut Dispatch Sentinel <{worker_email}>"
            fwd["Reply-To"] = ath_email
            fwd["Subject"] = f"[Delivered to {ath_name}] Get Noticed - Recreational Debut"
            fwd["Date"] = email.utils.formatdate(localtime=True)

            fwd_header_text = f"""=== RECREATIONAL DEBUT DISPATCH RECEIPT ===
Athlete Name: {ath_name}
Athlete Email: {ath_email}
High School: {ath_school}
Sport: {ath_sport} | Class of {ath_grad}
Delivered At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: Successfully Delivered to Athlete

--- EXACT MESSAGE DELIVERED ---
"""
            fwd_full_text = fwd_header_text + plain_text
            fwd.attach(MIMEText(fwd_full_text, "plain", "utf-8"))

            server = get_smtp(worker)
            server.sendmail(worker_email, [DENNIS_EMAIL], fwd.as_string())
            session_counts[worker_email] = session_counts.get(worker_email, 0) + 1
            log(f"   -> [FORWARDED] Delivery receipt forwarded to Dennis ({DENNIS_EMAIL}) for {ath_name}")
        except Exception as fe:
            log(f"   -> [WARN] Forward to Dennis failed for {ath_name}: {fe}")
            smtp_servers.pop(worker_email, None)
            session_counts[worker_email] = 0

        # 3. Update Database record immediately
        now_ts = time.time()
        cursor.execute("""
            UPDATE rec_debut_athletes
            SET last_messaged_at = ?, status = 'Contacted'
            WHERE id = ?
        """, (now_ts, ath_id))
        conn.commit()
        delivered_count += 1

        # Periodic Progress Checkpoint
        if delivered_count % 25 == 0:
            elapsed = time.time() - start_time
            log(f"--- [CHECKPOINT] {delivered_count}/{total_queue} delivered ({elapsed:.1f}s elapsed, {failed_count} failed) ---")

        # Rate smoothing: 2.0s per athlete
        time.sleep(2.0)

    # 4. Close SMTP connections
    for s in smtp_servers.values():
        try:
            s.quit()
        except Exception:
            pass

    # 5. Record Campaign History entry in database
    end_time = time.time()
    try:
        cursor.execute("""
            INSERT INTO rec_debut_campaigns
            (created_at, sender_id, total_recipients, successful_count, failed_count, message_body, delivery_details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            end_time,
            "Swarm-MultiGateway",
            total_queue,
            delivered_count,
            failed_count,
            "Get Noticed - Recreational Debut (Dennis Bell)",
            json.dumps({"elapsed_seconds": round(end_time - start_time, 2), "delivered": delivered_count, "failed": failed_count})
        ))
        conn.commit()
        log(f"[CAMPAIGN] Saved broadcast audit entry into rec_debut_campaigns.")
    except Exception as ce:
        log(f"[WARN] Failed to insert campaign audit: {ce}")

    conn.close()
    elapsed_total = end_time - start_time
    log(f"=== Daily Quota Dispatch Complete! Delivered: {delivered_count}/{total_queue}, Failed: {failed_count}, Elapsed: {elapsed_total:.1f}s ===")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=750)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    send_dispatch(batch_limit=args.limit, dry_run=args.dry_run)
