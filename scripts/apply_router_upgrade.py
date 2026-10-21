import ast
import re
from pathlib import Path

TARGET_FILE = Path(r"C:\AI-BS\backend\routers\rec_debut_router.py")
SECONDARY_FILE = Path(r"C:\Recreational-Debut\backend\rec_debut_router.py")

NEW_BLOCK = '''def dispatch_sms_message(recipient_phone: str, message_text: str, caller_id_name: str = "RecDebut Lead Sentinel") -> Dict[str, Any]:
    """
    Dispatches SMS via the highest-reliability configured provider:
      1. TextBee Android SIM Gateway ($0.00/msg) -> TEXTBEE_API_KEY & TEXTBEE_DEVICE_ID (Samsung Galaxy S25 Ultra)
      2. Telnyx Direct Cellular API ($0.004/segment) -> TELNYX_API_KEY & TELNYX_FROM_PHONE
      3. Built-in Carrier MMS Gateway fallback for Dennis Bell's instant lead alerts
    """
    digits = "".join(filter(str.isdigit, recipient_phone))
    if len(digits) < 10:
        return {"success": False, "error": f"Invalid phone: {recipient_phone}"}
    e164_phone = f"+1{digits[-10:]}"

    textbee_key = os.environ.get("TEXTBEE_API_KEY", "").strip()
    textbee_device = os.environ.get("TEXTBEE_DEVICE_ID", "").strip()
    if textbee_key and textbee_device:
        try:
            tb_endpoint = f"https://api.textbee.dev/api/v1/gateway/devices/{textbee_device}/send-sms"
            resp = requests.post(
                tb_endpoint,
                headers={"x-api-key": textbee_key, "Content-Type": "application/json"},
                json={"recipients": [e164_phone], "message": message_text},
                timeout=12.0
            )
            if resp.status_code in (200, 201):
                return {"success": True, "provider": "textbee_sim", "phone": e164_phone}
        except Exception as e:
            print(f"[TEXTBEE SEND ERROR] {e}")

    telnyx_key = os.environ.get("TELNYX_API_KEY", "").strip()
    telnyx_from = os.environ.get("TELNYX_FROM_PHONE", "").strip()
    if telnyx_key and telnyx_from:
        try:
            resp = requests.post(
                "https://api.telnyx.com/v2/messages",
                headers={"Authorization": f"Bearer {telnyx_key}", "Content-Type": "application/json"},
                json={"from": telnyx_from, "to": e164_phone, "text": message_text},
                timeout=10.0
            )
            if resp.status_code in (200, 201, 202):
                return {"success": True, "provider": "telnyx", "phone": e164_phone}
        except Exception as e:
            print(f"[TELNYX SEND ERROR] {e}")

    return send_carrier_sms(recipient_phone, message_text, caller_id_name=caller_id_name)


def send_dennis_email_alert(
    subject: str,
    text_content: str,
    html_content: str,
    athlete_name: str = "",
    athlete_phone: str = "",
    athlete_email: str = ""
) -> Tuple[bool, str]:
    """
    Sends an instant lead alert email directly to Dennis Bell (dbell002@sbcglobal.net).
    Tries Resend API -> SendGrid API -> SMTP Gateway Pool.
    """
    to_email = "dbell002@sbcglobal.net"
    to_name = "Dennis Bell"
    reply_to = athlete_email if athlete_email else "dbell002@sbcglobal.net"

    api_settings = load_email_api_settings()
    resend_key = (api_settings.get("resend_api_key") or os.environ.get("RESEND_API_KEY") or "").strip()
    resend_from = api_settings.get("resend_from_email") or "Dennis Bell <recruiting@recdebut.com>"
    
    if resend_key:
        ok, res = send_resend_email(
            api_key=resend_key,
            from_email=resend_from,
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            reply_to=reply_to
        )
        if ok:
            return True, f"Resend: {res}"

    sendgrid_key = (api_settings.get("sendgrid_api_key") or os.environ.get("SENDGRID_API_KEY") or "").strip()
    sendgrid_from = api_settings.get("sendgrid_from_email") or "Dennis Bell <recruiting@recdebut.com>"
    if sendgrid_key:
        ok, res = send_sendgrid_email(
            api_key=sendgrid_key,
            from_email=sendgrid_from,
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            reply_to=reply_to
        )
        if ok:
            return True, f"SendGrid: {res}"

    # Fallback to SMTP Gateway Pool
    swarm = [a for a in load_smtp_swarm() if a.get("active") and a.get("email") and a.get("app_password")]
    if not swarm:
        creds = load_credentials()
        swarm = [{
            "email": creds.get("IMAP_USER", "footballstar0325@gmail.com"),
            "app_password": creds.get("IMAP_APP_PASSWORD", "dnbmziwbtrfgfeht"),
            "smtp_host": creds.get("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(creds.get("SMTP_PORT", 587))
        }]

    for acct in swarm:
        s_user = acct["email"]
        s_pwd = acct["app_password"]
        s_host = acct.get("smtp_host", "smtp.gmail.com")
        s_port = int(acct.get("smtp_port", 587))
        server = None
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"RecDebut Lead Sentinel <{s_user}>"
            msg["To"] = f"Dennis Bell <{to_email}>"
            msg["Reply-To"] = reply_to
            msg["Date"] = email.utils.formatdate(localtime=True)
            msg["Message-ID"] = email.utils.make_msgid(domain="recdebut.com")
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            server = smtplib.SMTP(s_host, s_port, timeout=10.0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(s_user, s_pwd)
            server.sendmail(s_user, [to_email], msg.as_string())
            server.quit()
            return True, f"SMTP ({s_user})"
        except Exception as e:
            if server:
                try:
                    server.close()
                except Exception:
                    pass
            print(f"[DENNIS EMAIL ALERT SMTP ERROR] {e}")
            continue

    return False, "All email dispatch channels exhausted"


def find_athlete_by_contact(sender_phone: Optional[str] = None, sender_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Looks up athlete profile in SQLite rec_debut_athletes or Class of 2027 CSV.
    """
    clean_digits = re.sub(r'\\D', '', sender_phone)[-10:] if sender_phone else ""
    matched = None

    try:
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

        conn.close()
    except Exception as e:
        print(f"[FIND ATHLETE DB ERROR] {e}")

    # Fallback to Desktop CSV
    csv_file = Path(r"C:\\Users\\footb\\OneDrive\\Desktop\\TextBee_RecDebut_Class_of_2027.csv")
    if not matched and clean_digits and csv_file.exists():
        try:
            with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    cp = re.sub(r'\\D', '', r.get("phone", "") or r.get("phoneNumber", ""))[-10:]
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

    return matched


def forward_athlete_reply_to_dennis(
    athlete_name: str,
    sender_phone: str,
    sender_email: str,
    reply_body: str,
    athlete_info: Optional[Dict[str, Any]] = None,
    received_ts: Optional[float] = None
) -> Dict[str, Any]:
    """
    Forwards an incoming student-athlete reply immediately to Dennis Bell (+1-616-291-5227 / dbell002@sbcglobal.net)
    via dual channels: Direct SMS message + Instant Rich HTML Email Alert.
    Also logs the alert in rec_debut_lead_alerts.
    """
    dennis_phone = "+1-616-291-5227"
    dennis_email = "dbell002@sbcglobal.net"
    dennis_clean = "6162915227"

    sender_clean = re.sub(r'\\D', '', sender_phone)[-10:] if sender_phone else ""
    if dennis_clean in sender_clean:
        return {"success": False, "reason": "Self-sent message from Dennis Bell ignored"}

    sport_str = (athlete_info.get("sport") if athlete_info and athlete_info.get("sport") else "Basketball")
    hs_str = (f" | {athlete_info.get('high_school')}" if athlete_info and athlete_info.get("high_school") else "")
    grad_str = (f" ('{str(athlete_info.get('grad_year'))[-2:]})" if athlete_info and athlete_info.get("grad_year") else "")
    city_str = (f" - {athlete_info.get('city_state')}" if athlete_info and athlete_info.get("city_state") else "")

    contact_display = sender_phone if sender_phone else (sender_email if sender_email else "Unknown Contact")

    # 1. Direct Live SMS payload to Dennis Bell's phone (+1-616-291-5227)
    forward_sms = (
        f"🏀 REC DEBUT ATHLETE REPLY!\\n"
        f"From: {athlete_name} ({sport_str}{hs_str}{grad_str})\\n"
        f"Phone: {contact_display}\\n\\n"
        f"\\\"{reply_body.strip()[:320]}\\\"\\n\\n"
        f"👉 Tap to call or text back: {contact_display}"
    )

    sms_res = dispatch_sms_message(dennis_phone, forward_sms, caller_id_name="RecDebut Lead Alert")

    # 2. Instant Rich HTML & Text Email Alert to Dennis Bell (dbell002@sbcglobal.net)
    email_subject = f"🏀 RecDebut Reply: {athlete_name} ({sport_str}{hs_str})"
    text_content = (
        f"NEW STUDENT-ATHLETE REPLY RECEIVED!\\n\\n"
        f"Athlete: {athlete_name}\\n"
        f"Sport: {sport_str}\\n"
        f"School: {athlete_info.get('high_school', 'N/A') if athlete_info else 'N/A'}\\n"
        f"Grad Year: {athlete_info.get('grad_year', '2027') if athlete_info else '2027'}\\n"
        f"Phone: {contact_display}\\n"
        f"Email: {sender_email if sender_email else (athlete_info.get('email', 'N/A') if athlete_info else 'N/A')}\\n\\n"
        f"Message Text:\\n"
        f"\\\"{reply_body.strip()}\\\"\\n\\n"
        f"Action: Tap {contact_display} on your phone to call or text back immediately."
    )

    call_link = f"tel:{sender_clean}" if sender_clean else "#"
    sms_link = f"sms:{sender_clean}" if sender_clean else "#"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
        .card {{ background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 24px; max-width: 600px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        .badge {{ background: linear-gradient(135deg, #f97316, #ea580c); color: white; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; margin-bottom: 12px; }}
        h2 {{ margin-top: 0; color: #ffffff; font-size: 22px; }}
        .details {{ background-color: #0f172a; border-radius: 8px; padding: 16px; margin: 16px 0; border: 1px solid #1e293b; }}
        .details p {{ margin: 6px 0; font-size: 14px; color: #94a3b8; }}
        .details strong {{ color: #f1f5f9; }}
        .msg-box {{ background-color: #27272a; border-left: 4px solid #f97316; padding: 16px; margin: 18px 0; border-radius: 4px; font-size: 16px; color: #ffffff; line-height: 1.5; font-style: italic; }}
        .btn {{ display: inline-block; padding: 12px 20px; border-radius: 8px; font-weight: bold; text-decoration: none; text-align: center; font-size: 14px; margin-right: 10px; }}
        .btn-call {{ background-color: #22c55e; color: white; }}
        .btn-text {{ background-color: #3b82f6; color: white; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="badge">🏀 New RecDebut Reply</div>
        <h2>{athlete_name} has replied!</h2>
        <div class="details">
          <p><strong>Sport / Position:</strong> {sport_str}</p>
          <p><strong>High School:</strong> {athlete_info.get('high_school', 'N/A') if athlete_info else 'N/A'}{city_str}</p>
          <p><strong>Graduation Year:</strong> {athlete_info.get('grad_year', '2027') if athlete_info else '2027'}</p>
          <p><strong>Phone Number:</strong> <a href="{call_link}" style="color: #38bdf8;">{contact_display}</a></p>
          <p><strong>Email Address:</strong> {sender_email if sender_email else (athlete_info.get('email', 'N/A') if athlete_info else 'N/A')}</p>
        </div>
        <p style="color: #cbd5e1; font-weight: bold; margin-bottom: 6px;">Athlete's Message:</p>
        <div class="msg-box">\\\"{reply_body.strip()}\\\"</div>
        <div style="margin-top: 20px;">
          <a class="btn btn-call" href="{call_link}">📞 Call {contact_display}</a>
          <a class="btn btn-text" href="{sms_link}">💬 Text Back</a>
        </div>
      </div>
    </body>
    </html>
    """

    email_ok, email_msg = send_dennis_email_alert(
        subject=email_subject,
        text_content=text_content,
        html_content=html_content,
        athlete_name=athlete_name,
        athlete_phone=contact_display,
        athlete_email=sender_email
    )

    # 3. Log into rec_debut_lead_alerts in both primary and secondary databases
    now_ts = time.time()
    athlete_id_val = athlete_info.get("id") if athlete_info else None
    alert_summary = f"Reply from {athlete_name}: {reply_body.strip()[:100]}"
    secondary_db = Path(r"C:\\Recreational-Debut\\saved_data\\rec_debut.db")

    for db_file in [DB_PATH, secondary_db]:
        if db_file.exists():
            try:
                c_conn = sqlite3.connect(str(db_file))
                c_cur = c_conn.cursor()
                c_cur.execute("""
                    INSERT INTO rec_debut_lead_alerts 
                    (athlete_id, athlete_name, event_type, target_url, alert_text, sent_to_phone, created_at, is_read)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    athlete_id_val,
                    athlete_name,
                    "sms_reply",
                    f"tel:{sender_clean}",
                    alert_summary,
                    dennis_phone,
                    now_ts
                ))
                c_conn.commit()
                c_conn.close()
            except Exception as e:
                print(f"[LEAD ALERT LOG ERROR {db_file}] {e}")

    return {
        "success": True,
        "routed_to_phone": dennis_phone,
        "sms_dispatch": sms_res,
        "routed_to_email": dennis_email,
        "email_dispatch": {"success": email_ok, "detail": email_msg}
    }


def process_inbound_reply(
    sender_phone: str,
    sender_email: str,
    reply_body: str,
    source: str = "textbee",
    raw_meta: Optional[Dict[str, Any]] = None,
    received_ts: Optional[float] = None
) -> Dict[str, Any]:
    """
    Core inbound processing engine:
    1. Filters personal exclusions (Brett personal contacts, Mom, family, shortcodes, Dennis self-loop).
    2. Matches athlete via rec_debut_athletes SQLite & Class of 2027 CSV.
    3. Guarantees persistence even if athlete isn't pre-indexed (labels as Prospective Recruit / Parent).
    4. Dedupes by message_id_hash in rec_debut_athlete_replies.
    5. Saves into both AI-BS and Recreational-Debut databases.
    6. Updates rec_debut_athletes status to 'Replied'.
    7. Forwards live SMS & Email to Dennis Bell.
    """
    raw_meta = raw_meta or {}
    reply_body = (reply_body or "").strip()
    if not reply_body:
        return {"success": False, "reason": "Empty reply body"}

    sender_phone = (sender_phone or "").strip()
    sender_email = (sender_email or "").strip().lower()

    sender_clean = re.sub(r'\\D', '', sender_phone)[-10:] if sender_phone else ""
    sender_digits_all = re.sub(r'\\D', '', sender_phone) if sender_phone else ""

    # Check shortcode (< 10 digits and no email)
    if not sender_email and sender_digits_all and len(sender_digits_all) < 10:
        return {"success": False, "reason": f"Shortcode ignored: {sender_phone}"}

    # Check exclusions
    excluded_phones, excluded_emails = get_personal_exclusion_set()
    if sender_clean and sender_clean in excluded_phones:
        return {"success": False, "reason": f"Excluded personal contact: {sender_phone}"}
    if sender_email and sender_email in excluded_emails:
        return {"success": False, "reason": f"Excluded personal email: {sender_email}"}

    # Prevent loop if Dennis replies
    if sender_clean == "6162915227" or sender_email == "dbell002@sbcglobal.net":
        return {"success": False, "reason": "Dennis Bell message ignored (loop prevention)"}

    # Match athlete
    athlete = find_athlete_by_contact(sender_phone=sender_phone, sender_email=sender_email)
    if athlete:
        athlete_id = athlete.get("id")
        athlete_name = athlete.get("name") or "Student-Athlete"
    else:
        # User requirement: Make sure ANY text back from people gets forwarded to Dennis!
        # Do not discard unmatched replies (e.g. parents texting from their own cell).
        athlete_id = None
        athlete_name = f"Prospective Recruit / Parent ({sender_phone or sender_email})"
        athlete = {
            "id": None,
            "name": athlete_name,
            "sport": "High School Basketball",
            "high_school": "Prospect Inquiry",
            "grad_year": "2027",
            "city_state": "",
            "phone": sender_phone,
            "email": sender_email
        }

    # Message hash for deduping
    m_id = raw_meta.get("messageId") or raw_meta.get("_id") or raw_meta.get("id")
    if m_id:
        msg_hash = f"{source}_{m_id}"
    else:
        msg_hash = f"{source}_{sender_clean or sender_email}_{int(received_ts or time.time())}_{len(reply_body)}"

    now_ts = time.time()
    rec_ts = received_ts or now_ts

    # Check if already processed in primary database
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM rec_debut_athlete_replies WHERE message_id_hash = ?", (msg_hash,))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "reason": f"Already processed: {msg_hash}"}
        conn.close()
    except Exception:
        pass

    # Commit to both primary and secondary SQLite databases
    saved_primary = False
    secondary_db = Path(r"C:\\Recreational-Debut\\saved_data\\rec_debut.db")
    for db_file in [DB_PATH, secondary_db]:
        if not db_file.exists():
            continue
        try:
            c_conn = sqlite3.connect(str(db_file))
            c_cur = c_conn.cursor()
            c_cur.execute("""
                INSERT INTO rec_debut_athlete_replies 
                (athlete_id, athlete_name, sender_phone, sender_email, recipient_email, subject, reply_body, received_at, is_read, created_at, message_id_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                athlete_id,
                athlete_name,
                sender_phone,
                sender_email,
                "dbell002@sbcglobal.net",
                f"SMS Reply from {athlete_name}",
                reply_body,
                rec_ts,
                now_ts,
                msg_hash
            ))
            c_conn.commit()
            if athlete_id:
                c_cur.execute("UPDATE rec_debut_athletes SET status = 'Replied' WHERE id = ?", (athlete_id,))
                c_conn.commit()
            c_conn.close()
            if db_file == DB_PATH:
                saved_primary = True
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            print(f"[REPLY DB INSERT ERROR {db_file}] {e}")

    # Forward to Dennis Bell (+1-616-291-5227 & dbell002@sbcglobal.net)
    forward_res = forward_athlete_reply_to_dennis(
        athlete_name=athlete_name,
        sender_phone=sender_phone,
        sender_email=sender_email,
        reply_body=reply_body,
        athlete_info=athlete,
        received_ts=rec_ts
    )

    return {
        "success": True,
        "athlete_id": athlete_id,
        "athlete_name": athlete_name,
        "phone": sender_phone,
        "email": sender_email,
        "forward": forward_res
    }


def sync_textbee_inbound_messages() -> Dict[str, Any]:
    """
    Polls TextBee device messages endpoint for received SMS on the Samsung Galaxy S25 Ultra gateway.
    Processes any new incoming SMS texts and forwards them to Dennis Bell.
    """
    creds = load_credentials()
    textbee_device = (os.environ.get("TEXTBEE_DEVICE_ID") or creds.get("TEXTBEE_DEVICE_ID") or "6ad7b28560b1138230badd0a").strip()
    textbee_key = (os.environ.get("TEXTBEE_API_KEY") or creds.get("TEXTBEE_API_KEY") or "txb_rAZOZNMuTEKtlxQ30hfcJd05dL2KlVRu").strip()

    if not textbee_device or not textbee_key:
        return {"success": False, "error": "TextBee credentials missing"}

    url = f"https://api.textbee.dev/api/v1/gateway/devices/{textbee_device}/messages?limit=50"
    headers = {"x-api-key": textbee_key, "Content-Type": "application/json"}

    try:
        resp = requests.get(url, headers=headers, timeout=12.0)
        if resp.status_code != 200:
            return {"success": False, "error": f"TextBee API returned HTTP {resp.status_code}"}

        data = resp.json()
        messages = data.get("data", [])
        received = [m for m in messages if m.get("type") == "RECEIVED"]

        new_replies = 0
        items = []

        for m in received:
            sender = m.get("sender") or ""
            msg_text = m.get("message") or ""
            rec_at_str = m.get("receivedAt")
            rec_ts = None
            if rec_at_str:
                try:
                    dt = datetime.fromisoformat(rec_at_str.replace("Z", "+00:00"))
                    rec_ts = dt.timestamp()
                except Exception:
                    pass

            proc = process_inbound_reply(
                sender_phone=sender,
                sender_email="",
                reply_body=msg_text,
                source="textbee",
                raw_meta=m,
                received_ts=rec_ts
            )
            if proc.get("success"):
                new_replies += 1
                items.append(proc)

        return {
            "success": True,
            "provider": "textbee",
            "received_count": len(received),
            "new_replies_forwarded": new_replies,
            "items": items
        }
    except Exception as e:
        return {"success": False, "error": f"TextBee sync failed: {str(e)}"}


def sync_imap_inbound_messages() -> Dict[str, Any]:
    """
    Connects to IMAP SSL, searches for incoming carrier gateway MMS texts and direct email replies,
    and auto-forwards them to Dennis Bell (+1-616-291-5227 / dbell002@sbcglobal.net).
    """
    creds = load_credentials()
    imap_user = creds.get("IMAP_USER", "footballstar0325@gmail.com")
    imap_pwd = creds.get("IMAP_APP_PASSWORD", "dnbmziwbtrfgfeht")

    carrier_domains = [
        "vzwpix.com", "vtext.com", "mms.att.net", "txt.att.net",
        "tmomail.net", "mms.cricketwireless.net", "myboostmobile.com",
        "mms.uscc.net", "msg.fi.google.com"
    ]

    new_replies_count = 0
    synced_items = []

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(imap_user, imap_pwd)
        mail.select("INBOX", readonly=True)

        msg_ids_set = set()

        # 1. Messages addressed to stehouwer-publishing.com
        status, res = mail.search(None, '(TO "stehouwer-publishing.com")')
        if status == "OK" and res[0]:
            for mid in res[0].split():
                msg_ids_set.add(mid)

        # 2. Messages from carrier gateways
        for gw in carrier_domains:
            status, res = mail.search(None, f'(FROM "{gw}")')
            if status == "OK" and res[0]:
                for mid in res[0].split():
                    msg_ids_set.add(mid)

        sorted_ids = sorted(list(msg_ids_set), key=lambda x: int(x), reverse=True)
        recent_candidates = sorted_ids[:50]

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
            body_text = extract_email_body(msg)

            received_ts = time.time()
            if date_raw:
                try:
                    parsed_dt = email.utils.parsedate_to_datetime(date_raw)
                    received_ts = parsed_dt.timestamp()
                except Exception:
                    pass

            sender_email_match = re.search(r'[\\w\\.-]+@[\\w\\.-]+', from_raw)
            sender_email = sender_email_match.group(0).lower() if sender_email_match else from_raw.lower()

            phone_match = re.search(r'(\\d{10})', sender_email)
            sender_phone = ""
            if phone_match:
                raw_digits = phone_match.group(1)
                sender_phone = f"{raw_digits[:3]}-{raw_digits[3:6]}-{raw_digits[6:]}"
            else:
                digits_in_from = re.sub(r'\\D', '', from_raw)
                if len(digits_in_from) >= 10:
                    d10 = digits_in_from[-10:]
                    sender_phone = f"{d10[:3]}-{d10[3:6]}-{d10[6:]}"

            full_text = body_text
            if subject_raw and subject_raw not in body_text:
                if not body_text:
                    full_text = subject_raw
                else:
                    full_text = f"{subject_raw}\\n\\n{body_text}"

            # Filter automated system emails
            if "googlecloud@google.com" in sender_email or "no-reply" in sender_email or "mailer-daemon" in sender_email or "notifications@" in sender_email:
                continue

            proc = process_inbound_reply(
                sender_phone=sender_phone,
                sender_email=sender_email,
                reply_body=full_text,
                source="imap_mms",
                raw_meta={"mid": mid.decode("utf-8") if isinstance(mid, bytes) else str(mid)},
                received_ts=received_ts
            )
            if proc.get("success"):
                new_replies_count += 1
                synced_items.append(proc)

        mail.logout()
        return {
            "success": True,
            "provider": "imap",
            "new_replies_forwarded": new_replies_count,
            "items": synced_items
        }
    except Exception as e:
        return {"success": False, "error": f"IMAP sync failed: {str(e)}"}


def sync_inbound_athlete_replies() -> Dict[str, Any]:
    """
    Combined inbound reply orchestrator:
    1. Checks TextBee cellular gateway on Samsung Galaxy S25 Ultra.
    2. Checks IMAP carrier MMS and email inbox.
    3. Dedupes and auto-forwards all candidate replies to Dennis Bell (+1-616-291-5227 / dbell002@sbcglobal.net).
    """
    tb_res = sync_textbee_inbound_messages()
    imap_res = sync_imap_inbound_messages()

    total_new = (tb_res.get("new_replies_forwarded") or 0) + (imap_res.get("new_replies_forwarded") or 0)

    total_replies = 0
    unread_replies = 0
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rec_debut_athlete_replies")
        total_replies = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rec_debut_athlete_replies WHERE is_read = 0")
        unread_replies = cursor.fetchone()[0]
        conn.close()
    except Exception:
        pass

    return {
        "success": True,
        "new_replies_count": total_new,
        "total_replies": total_replies,
        "unread_replies": unread_replies,
        "textbee_sync": tb_res,
        "imap_sync": imap_res
    }


# --- Webhooks & SMS Management Endpoints ---

@router.post("/webhooks/textbee")
@legacy_router.post("/webhooks/textbee")
@router.post("/sms/inbound")
async def handle_textbee_inbound_webhook(request: Request):
    """
    Real-time webhook receiver for incoming SMS from TextBee gateway or carrier webhooks.
    Immediately processes the reply, updates CRM, and forwards directly to Dennis Bell.
    """
    try:
        body_bytes = await request.body()
        payload = {}
        if body_bytes:
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                pass

        data_block = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        sender = data_block.get("sender") or data_block.get("from") or payload.get("sender") or ""
        msg_text = data_block.get("message") or data_block.get("text") or data_block.get("body") or payload.get("message") or ""

        if not sender or not msg_text:
            return JSONResponse(status_code=200, content={"status": "ignored", "reason": "No sender or message text in payload"})

        res = process_inbound_reply(
            sender_phone=sender,
            sender_email="",
            reply_body=msg_text,
            source="textbee_webhook",
            raw_meta=data_block
        )
        return JSONResponse(status_code=200, content={"status": "received", "result": res})
    except Exception as e:
        print(f"[TEXTBEE WEBHOOK ERROR] {e}")
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})


@router.get("/sms/replies")
async def get_athlete_sms_replies(limit: int = 100, unread_only: bool = False):
    """Retrieve all logged inbound student-athlete SMS responses and replies."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athlete_replies")
        total_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athlete_replies WHERE is_read = 0")
        unread_count = cursor.fetchone()[0]

        query = "SELECT * FROM rec_debut_athlete_replies"
        params = []
        if unread_only:
            query += " WHERE is_read = 0"
        query += " ORDER BY received_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return {
            "success": True,
            "total_count": total_count,
            "unread_count": unread_count,
            "replies": [dict(r) for r in rows]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sms/sync-replies")
async def trigger_sms_replies_sync():
    """Trigger real-time sync across TextBee Samsung gateway and IMAP to check for new athlete responses."""
    res = sync_inbound_athlete_replies()
    return res


@router.post("/sms/replies/{reply_id}/read")
async def mark_reply_as_read(reply_id: int):
    """Mark a specific athlete reply as read."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("UPDATE rec_debut_athlete_replies SET is_read = 1 WHERE id = ?", (reply_id,))
        conn.commit()
        conn.close()
        return {"success": True, "reply_id": reply_id, "is_read": 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sms/replies/{reply_id}/respond")
async def respond_to_athlete_reply(reply_id: int, payload: RespondToReplyPayload):
    """Send an outbound SMS response directly back to the student-athlete via TextBee cellular gateway or carrier fallback."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rec_debut_athlete_replies WHERE id = ?", (reply_id,))
        reply_row = cursor.fetchone()
        conn.close()

        if not reply_row:
            raise HTTPException(status_code=404, detail="Reply not found")

        phone = reply_row["sender_phone"]
        if not phone:
            raise HTTPException(status_code=400, detail="Cannot send SMS: No phone number associated with this reply.")

        res = dispatch_sms_message(
            recipient_phone=phone,
            message_text=payload.message_text.strip(),
            caller_id_name=payload.caller_id_name or "Dennis Bell (+1-616-291-5227)"
        )
        return {
            "success": res.get("success", False),
            "phone": phone,
            "caller_id": payload.caller_id_email or "dbell002@sbcglobal.net",
            "dispatch_result": res
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sms/test-route-dennis")
async def test_route_reply_to_dennis(
    sample_athlete_name: str = "Marcus Johnson (2027 Guard)",
    sample_athlete_phone: str = "616-402-3628",
    sample_reply: str = "Hey Dennis! I got your text about RecDebut. I would love to play college basketball. When can we talk?"
):
    """Simulates an incoming athlete text response and routes it live to Dennis Bell's phone (+1-616-291-5227) and email (dbell002@sbcglobal.net)."""
    res = forward_athlete_reply_to_dennis(
        athlete_name=sample_athlete_name,
        sender_phone=sample_athlete_phone,
        sender_email="athlete_test@example.com",
        reply_body=sample_reply,
        athlete_info={
            "name": sample_athlete_name,
            "sport": "Basketball",
            "high_school": "East Grand Rapids High School",
            "grad_year": "2027",
            "city_state": "Grand Rapids, MI",
            "phone": sample_athlete_phone,
            "email": "athlete_test@example.com"
        }
    )
    return {
        "success": res.get("success", False),
        "routed_to_phone": "+1-616-291-5227",
        "routed_to_email": "dbell002@sbcglobal.net",
        "sample_athlete": sample_athlete_name,
        "sample_athlete_phone": sample_athlete_phone,
        "sample_reply": sample_reply,
        "forward_result": res
    }


# --- Background Inbound Polling Sentinel Daemon ---

_inbound_sentinel_started = False
_inbound_sentinel_lock = threading.Lock()

def start_inbound_sentinel_daemon():
    """
    Launches a dedicated daemon thread that automatically polls TextBee and IMAP every 60 seconds.
    Ensures all incoming recruit texts are captured and forwarded to Dennis Bell in near-real-time.
    """
    global _inbound_sentinel_started
    with _inbound_sentinel_lock:
        if _inbound_sentinel_started:
            return
        _inbound_sentinel_started = True

    def _sentinel_loop():
        time.sleep(15)  # Stagger initial check on process boot
        while True:
            try:
                sync_inbound_athlete_replies()
            except Exception as e:
                print(f"[INBOUND SENTINEL ERROR] {e}")
            time.sleep(60)

    t = threading.Thread(target=_sentinel_loop, name="RecDebutInboundSentinel", daemon=True)
    t.start()
    print("[INBOUND SENTINEL] Background polling daemon started successfully (interval: 60s).")

# Auto-start sentinel when module loads
start_inbound_sentinel_daemon()


# --- Open & Click Telemetry Endpoints ---

TRANSPARENT_GIF_BYTES = (
    b"GIF89a\\x01\\x00\\x01\\x00\\x80\\x00\\x00\\xff\\xff\\xff\\x00\\x00\\x00"
    b"!\\xf9\\x04\\x01\\x00\\x00\\x00\\x00,\\x00\\x00\\x00\\x00\\x01\\x00\\x01\\x00\\x00\\x02\\x02D\\x01\\x00;"
)
'''

def main():
    src = TARGET_FILE.read_text(encoding="utf-8")
    
    start_marker = "def sync_inbound_athlete_replies() -> Dict[str, Any]:"
    end_marker = '@router.get("/track/open/{campaign_id}/{athlete_id}")'
    
    start_pos = src.find(start_marker)
    if start_pos == -1:
        raise ValueError(f"start_marker not found in {TARGET_FILE}")
        
    end_pos = src.find(end_marker)
    if end_pos == -1:
        raise ValueError(f"end_marker not found in {TARGET_FILE}")
        
    print(f"Replacing text from index {start_pos} to {end_pos}...")
    new_src = src[:start_pos] + NEW_BLOCK + "\n\n\n" + src[end_pos:]
    
    print("Validating Python AST syntax...")
    ast.parse(new_src)
    print("AST parse SUCCESSFUL! Valid Python syntax.")
    
    TARGET_FILE.write_text(new_src, encoding="utf-8")
    print(f"Successfully updated {TARGET_FILE}!")
    
    if SECONDARY_FILE.exists():
        SECONDARY_FILE.write_text(new_src, encoding="utf-8")
        print(f"Successfully synchronized {SECONDARY_FILE}!")

if __name__ == "__main__":
    main()
