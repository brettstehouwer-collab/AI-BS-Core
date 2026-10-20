#!/usr/bin/env python3
"""
apply_rec_debut_upgrade.py
Production patch script for backend/routers/rec_debut_router.py.
Adds:
  1. {short_url}, {tracking_url}, and {id} tag replacement in format_personalized_message()
  2. Multi-provider SMS dispatcher (TextBee SIM / Telnyx API / Carrier MMS Fallback)
  3. Instant SMS alert to Dennis Bell (+1-616-291-5227) on first email open
  4. 36-character short tracking route (/r/{athlete_id}) for single-segment SMS campaigns
  5. Pre-flight AST syntax validation and automatic timestamped backup
"""

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Auto-detect AI-BS backend path or fall back to standard structure
BACKEND_DIR = Path(__file__).resolve().parent if "routers" in str(Path(__file__).resolve()) else Path(r"C:\AI-BS\backend")
ROUTER_PATH = BACKEND_DIR / "routers" / "rec_debut_router.py"
if not ROUTER_PATH.exists():
    ROUTER_PATH = Path(r"C:\AI-BS\backend\routers\rec_debut_router.py")


def patch_rec_debut_router() -> bool:
    if not ROUTER_PATH.exists():
        print(f"[ERROR] Target file not found: {ROUTER_PATH}")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = ROUTER_PATH.with_name(f"{ROUTER_PATH.name}.bak_{timestamp}")
    shutil.copy2(ROUTER_PATH, backup_path)
    print(f"[BACKUP] Created backup at: {backup_path}")

    src = ROUTER_PATH.read_text(encoding="utf-8")

    # 1. Patch format_personalized_message() with {id} and {short_url}
    old_fmt_anchor = (
        "    formatted = re.sub(r'\\{(?i:grad[\\s_-]*year|graduation[\\s_-]*year|gradyear|class[\\s_-]*of|class|year)\\}|"
        "\\[(?i:grad[\\s_-]*year|graduation[\\s_-]*year|gradyear|class[\\s_-]*of|class|year)\\]', grad_year, formatted)"
    )

    proto = "https://"
    short_host = "stehouwerproductions.com"
    new_fmt_block = (
        "    formatted = re.sub(r'\\{(?i:grad[\\s_-]*year|graduation[\\s_-]*year|gradyear|class[\\s_-]*of|class|year)\\}|"
        "\\[(?i:grad[\\s_-]*year|graduation[\\s_-]*year|gradyear|class[\\s_-]*of|class|year)\\]', grad_year, formatted)\n"
        "    athlete_id_str = str(recipient.get(\"id\") or \"0\")\n"
        f"    short_link = f\"{proto}{short_host}/r/{{athlete_id_str}}\"\n"
        "    formatted = re.sub(r'\\{(?i:id|athlete_id)\\}', athlete_id_str, formatted)\n"
        "    formatted = re.sub(r'\\{(?i:short_url|tracking_url|link)\\}', short_link, formatted)"
    )

    if "short_link =" not in src:
        if old_fmt_anchor in src:
            src = src.replace(old_fmt_anchor, new_fmt_block, 1)
            print("[PATCH 1/2] Injected {short_url}, {tracking_url}, and {id} into format_personalized_message().")
        else:
            print("[WARNING] Could not locate format_personalized_message() anchor; skipping Patch 1.")
    else:
        print("[SKIP 1/2] format_personalized_message() already contains short_link support.")

    # 2. Patch Open & Click Telemetry Section
    start_marker = "# --- Open & Click Telemetry Endpoints ---"
    end_marker = '@router.get("/outreach-analytics")'

    if start_marker not in src or end_marker not in src:
        print("[ERROR] Could not locate telemetry section markers in rec_debut_router.py.")
        return False

    before_section = src.split(start_marker, 1)[0]
    after_section = end_marker + src.split(end_marker, 1)[1]

    tb_base = "https://api.textbee.dev/api/v1/gateway/devices"
    tx_base = "https://api.telnyx.com/v2/messages"
    rd_reg = "https://recdebut.com/all-registration/"

    upgraded_telemetry_section = f'''# --- Open & Click Telemetry Endpoints ---

TRANSPARENT_GIF_BYTES = (
    b"GIF89a\\x01\\x00\\x01\\x00\\x80\\x00\\x00\\xff\\xff\\xff\\x00\\x00\\x00"
    b"!\\xf9\\x04\\x01\\x00\\x00\\x00\\x00,\\x00\\x00\\x00\\x00\\x01\\x00\\x01\\x00\\x00\\x02\\x02D\\x01\\x00;"
)

def dispatch_sms_message(recipient_phone: str, message_text: str, caller_id_name: str = "RecDebut Lead Sentinel") -> Dict[str, Any]:
    """
    Dispatches SMS via the lowest-cost configured provider:
      1. TextBee Android SIM Gateway ($0.00/msg) -> TEXTBEE_API_KEY & TEXTBEE_DEVICE_ID
      2. Telnyx Direct Cellular API ($0.004/segment) -> TELNYX_API_KEY & TELNYX_FROM_PHONE
      3. Built-in Carrier MMS Gateway fallback for Dennis Bell's instant lead alerts
    """
    digits = "".join(filter(str.isdigit, recipient_phone))
    if len(digits) < 10:
        return {{"success": False, "error": f"Invalid phone: {{recipient_phone}}"}}
    e164_phone = f"+1{{digits[-10:]}}"

    textbee_key = os.environ.get("TEXTBEE_API_KEY", "").strip()
    textbee_device = os.environ.get("TEXTBEE_DEVICE_ID", "").strip()
    if textbee_key and textbee_device:
        try:
            tb_endpoint = "{tb_base}/" + textbee_device + "/send-sms"
            resp = requests.post(
                tb_endpoint,
                headers={{"x-api-key": textbee_key, "Content-Type": "application/json"}},
                json={{"recipients": [e164_phone], "message": message_text}},
                timeout=10.0
            )
            if resp.status_code in (200, 201):
                return {{"success": True, "provider": "textbee_sim", "phone": e164_phone}}
        except Exception as e:
            print(f"[TEXTBEE ERROR] {{e}}")

    telnyx_key = os.environ.get("TELNYX_API_KEY", "").strip()
    telnyx_from = os.environ.get("TELNYX_FROM_PHONE", "").strip()
    if telnyx_key and telnyx_from:
        try:
            resp = requests.post(
                "{tx_base}",
                headers={{"Authorization": f"Bearer {{telnyx_key}}", "Content-Type": "application/json"}},
                json={{"from": telnyx_from, "to": e164_phone, "text": message_text}},
                timeout=10.0
            )
            if resp.status_code in (200, 201, 202):
                return {{"success": True, "provider": "telnyx", "phone": e164_phone}}
        except Exception as e:
            print(f"[TELNYX ERROR] {{e}}")

    return send_carrier_sms(recipient_phone, message_text, caller_id_name=caller_id_name)


@router.get("/track/open/{{campaign_id}}/{{athlete_id}}")
@legacy_router.get("/track/open/{{campaign_id}}/{{athlete_id}}")
async def track_email_open(campaign_id: str, athlete_id: int, request: Request):
    """
    1x1 transparent GIF tracking pixel.
    Records open timestamp, increments athlete open count, and alerts Dennis Bell (+1-616-291-5227) on first open.
    """
    now = time.time()
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")
    user_agent = request.headers.get("user-agent") or ""

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name, sport, high_school, city_state, phone, email, COALESCE(open_count, 0) FROM rec_debut_athletes WHERE id = ?",
            (athlete_id,)
        )
        ath_row = cursor.fetchone()
        prev_opens = ath_row[6] if ath_row else 0

        cursor.execute("""
            INSERT INTO rec_debut_tracking_events
            (campaign_id, athlete_id, event_type, target_url, ip_address, user_agent, created_at)
            VALUES (?, ?, 'OPEN', NULL, ?, ?, ?)
        """, (campaign_id, athlete_id, client_ip, user_agent, now))

        cursor.execute("""
            UPDATE rec_debut_athletes
            SET open_count = COALESCE(open_count, 0) + 1, last_opened_at = ?
            WHERE id = ?
        """, (now, athlete_id))

        # Alert Dennis Bell on first open (prev_opens == 0)
        if ath_row and prev_opens == 0:
            ath_name = ath_row[0] or f"Athlete #{{athlete_id}}"
            ath_sport = ath_row[1] or "Basketball"
            ath_school = ath_row[2] or ""
            ath_city = ath_row[3] or ""
            ath_phone = ath_row[4] or "N/A"
            ath_email = ath_row[5] or "N/A"
            loc_str = f" - {{ath_school}} ({{ath_city}})" if ath_school or ath_city else ""

            alert_body = (
                f"👀 EMAIL OPENED: {{ath_name}} ({{ath_sport}}{{loc_str}}) just opened the campaign email!\\n"
                f"📱 Phone: {{ath_phone}}\\n"
                f"📧 Email: {{ath_email}}\\n"
                f"Dennis, keep an eye out for their registration click!"
            )

            cursor.execute("""
                INSERT INTO rec_debut_lead_alerts
                (athlete_id, athlete_name, event_type, target_url, alert_text, sent_to_phone, created_at, is_read)
                VALUES (?, ?, 'OPEN', 'EMAIL_PIXEL', ?, '+1-616-291-5227', ?, 0)
            """, (athlete_id, ath_name, alert_body, now))

            threading.Thread(
                target=dispatch_sms_message,
                args=("+1-616-291-5227", alert_body, "RecDebut Open Sentinel"),
                daemon=True
            ).start()

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[TRACKING ERROR] Open pixel logging failed: {{e}}")

    return Response(
        content=TRANSPARENT_GIF_BYTES,
        media_type="image/gif",
        headers={{
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }}
    )


@router.get("/track/click/{{campaign_id}}/{{athlete_id}}")
@legacy_router.get("/track/click/{{campaign_id}}/{{athlete_id}}")
async def track_email_click(campaign_id: str, athlete_id: int, request: Request, url: Optional[str] = "{rd_reg}"):
    """
    Click redirect wrapper for outreach emails and short SMS links.
    Logs click event, increments athlete click counter, alerts Dennis Bell, and redirects to destination URL.
    """
    now = time.time()
    dest_url = url or "{rd_reg}"
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")
    user_agent = request.headers.get("user-agent") or ""

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rec_debut_tracking_events
            (campaign_id, athlete_id, event_type, target_url, ip_address, user_agent, created_at)
            VALUES (?, ?, 'CLICK', ?, ?, ?, ?)
        """, (campaign_id, athlete_id, dest_url, client_ip, user_agent, now))

        cursor.execute("""
            UPDATE rec_debut_athletes
            SET click_count = COALESCE(click_count, 0) + 1, last_clicked_at = ?
            WHERE id = ?
        """, (now, athlete_id))

        cursor.execute("SELECT name, sport, high_school, city_state, phone, email FROM rec_debut_athletes WHERE id = ?", (athlete_id,))
        ath_row = cursor.fetchone()
        ath_name = ath_row[0] if ath_row and ath_row[0] else f"Athlete #{{athlete_id}}"
        ath_sport = ath_row[1] if ath_row and ath_row[1] else "Basketball"
        ath_school = ath_row[2] if ath_row and ath_row[2] else ""
        ath_city = ath_row[3] if ath_row and ath_row[3] else ""
        ath_phone = ath_row[4] if ath_row and ath_row[4] else ""
        ath_email = ath_row[5] if ath_row and ath_row[5] else ""

        loc_str = f" - {{ath_school}} ({{ath_city}})" if ath_school or ath_city else ""
        alert_body = (
            f"🔥 HOT RECRUIT LEAD: {{ath_name}} ({{ath_sport}}{{loc_str}}) clicked registration link {{dest_url}}!\\n"
            f"📱 Phone: {{ath_phone}}\\n"
            f"📧 Email: {{ath_email}}\\n"
            f"Dennis, call while they are active!"
        )

        cursor.execute("""
            INSERT INTO rec_debut_lead_alerts
            (athlete_id, athlete_name, event_type, target_url, alert_text, sent_to_phone, created_at, is_read)
            VALUES (?, ?, 'CLICK', ?, ?, '+1-616-291-5227', ?, 0)
        """, (athlete_id, ath_name, dest_url, alert_body, now))

        conn.commit()
        conn.close()

        threading.Thread(
            target=dispatch_sms_message,
            args=("+1-616-291-5227", alert_body, "RecDebut Open Sentinel"),
            daemon=True
        ).start()

    except Exception as e:
        print(f"[TRACKING ERROR] Click logging failed: {{e}}")

    return RedirectResponse(url=dest_url, status_code=302)


@router.get("/r/{{athlete_id}}")
@legacy_router.get("/r/{{athlete_id}}")
async def short_sms_tracking_redirect(athlete_id: int, request: Request, url: Optional[str] = "{rd_reg}"):
    """
    36-character short tracking endpoint: /r/{{athlete_id}}
    Logs click, alerts Dennis Bell (+1-616-291-5227), and redirects to registration.
    """
    return await track_email_click(
        campaign_id="sms_shortlink",
        athlete_id=athlete_id,
        request=request,
        url=url or "{rd_reg}"
    )

'''

    new_src = before_section + upgraded_telemetry_section + after_section

    # 3. Validate Python AST Syntax before writing
    try:
        ast.parse(new_src)
        print("[AST CHECK] Syntax verified cleanly.")
    except SyntaxError as syn_err:
        print(f"[AST ERROR] Syntax validation failed: {syn_err}")
        return False

    ROUTER_PATH.write_text(new_src, encoding="utf-8")
    print(f"[SUCCESS] Updated {ROUTER_PATH} successfully.")
    return True


if __name__ == "__main__":
    ok = patch_rec_debut_router()
    sys.exit(0 if ok else 1)
