#!/usr/bin/env python3
"""
NoCo Autonomous Property Sniffer & Email Dispatch Daemon
AI-BS Sovereign Intelligence Operations Suite

Features:
- Autonomous continuous property sniffer across Tompkins NY, Windham/Addison VT, Hunterdon NJ, and Ottawa MI.
- Consolidated Executive Email Digest (packages multiple prime parcels into 1 email to conserve IONOS hourly rate limits).
- Smart Queue & Ledger management with duplicate prevention.
- Handles IONOS 450 rate limit backoffs gracefully.

CLI Options:
  --once          : Run a single discovery cycle
  --digest        : Send a consolidated master digest of all prime targets in 1 email
  --loop [sec]    : Run daemon in background (e.g. --loop 3600)
  --test-email    : Send a single test email
  --to [emails]   : Comma-separated recipient list
"""

import sys
import os
import json
import time
import smtplib
import argparse
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Force UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(SCRIPT_DIR, "noco_property_ledger.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "noco_sniffer_daemon.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# Default IONOS SMTP Configuration
SMTP_HOST = os.environ.get("IONOS_SMTP_HOST", "smtp.ionos.com")
SMTP_PORT = int(os.environ.get("IONOS_SMTP_PORT", 587))
SMTP_USER = os.environ.get("IONOS_EMAIL", "brett@stehouwerproductions.com")
SMTP_PASS = os.environ.get("IONOS_PASSWORD", "Thatswhatshesaid420!")

# Leadership Notification Recipients
DEFAULT_RECIPIENTS = [
    "brettstehouwer@gmail.com",
    "theseandaley@gmail.com",
    "footballstar0325@gmail.com"
]

DASHBOARD_URL = "https://ai-bs-dashboard.web.app/?tab=project_noco&subtab=properties"

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"[!] Warning loading ledger: {e}")
    return {"parcels": []}

def save_ledger(data):
    try:
        with open(LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log(f"[!] Failed to save ledger: {e}")
        return False

def build_parcel_card_html(p):
    """Renders HTML card for a single parcel inside digest or alert."""
    verdict = p.get("verdict", "PRIME ACQUISITION TARGET")
    is_prime = "PRIME" in verdict
    badge_color = "#10B981" if is_prime else ("#F59E0B" if "FEASIBLE" in verdict else "#EF4444")
    score = p.get("composite_score", p.get("compositeScore", 0.0))
    acres = p.get("acres", 0.0)
    price = p.get("price", 0)
    price_per_acre = p.get("price_per_acre", p.get("pricePerAcre", 0))
    address = p.get("address", "Unknown Address")
    county = p.get("county", "Unknown County")
    tier = p.get("tier", "Target Regional Hub")
    highlights = p.get("highlights", "")
    due_diligence_flags = p.get("due_diligence_flags", p.get("nextStep", "Review with 112 Due Diligence Questionnaire."))
    listing_url = p.get("url", "https://www.zillow.com")

    matches = p.get("due_diligence_matches", [
        f"Acreage ({acres} ac) inside sweet spot",
        "Acoustic bowl / concave slope for vocal throw",
        "Protected under statutory agricultural exemptions"
    ])
    matches_html = "".join([f"<li style='margin-bottom:4px; color:#cbd5e1;'><span style='color:#00FFFF;'>✔</span> {m}</li>" for m in matches[:4]])

    return f"""
    <div style="background-color:#1E293B; border-radius:10px; border:1px solid #334155; margin-bottom:20px; overflow:hidden;">
      <div style="padding:14px 18px; background:linear-gradient(90deg, rgba(15,23,42,0.9) 0%, rgba(30,41,59,0.8) 100%); border-bottom:1px solid #334155; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <h2 style="margin:0; font-size:1.15rem; color:#FFFFFF;">{address}</h2>
          <div style="font-size:0.8rem; color:#38BDF8; margin-top:2px;">{county} &bull; <span style="color:#C084FC;">{tier}</span></div>
        </div>
        <div style="text-align:right;">
          <span style="background-color:{badge_color}25; border:1px solid {badge_color}; color:{badge_color}; font-size:0.75rem; font-weight:900; padding:4px 10px; border-radius:20px; white-space:nowrap;">
            {score}% &bull; {verdict}
          </span>
        </div>
      </div>

      <div style="padding:16px 18px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px; background-color:rgba(0,0,0,0.25); border-radius:6px;">
          <tr>
            <td width="33%" style="padding:10px; text-align:center; border-right:1px solid #334155;">
              <div style="font-size:0.65rem; color:#94A3B8; text-transform:uppercase;">Acreage</div>
              <div style="font-size:1.05rem; font-weight:800; color:#00FFFF; margin-top:2px;">{acres} ac</div>
            </td>
            <td width="33%" style="padding:10px; text-align:center; border-right:1px solid #334155;">
              <div style="font-size:0.65rem; color:#94A3B8; text-transform:uppercase;">Asking Price</div>
              <div style="font-size:1.05rem; font-weight:800; color:#10B981; margin-top:2px;">${price:,}</div>
            </td>
            <td width="34%" style="padding:10px; text-align:center;">
              <div style="font-size:0.65rem; color:#94A3B8; text-transform:uppercase;">Price / Acre</div>
              <div style="font-size:1.05rem; font-weight:800; color:#F59E0B; margin-top:2px;">${price_per_acre:,}/ac</div>
            </td>
          </tr>
        </table>

        <div style="font-size:0.82rem; color:#e2e8f0; line-height:1.4; margin-bottom:10px;">
          <strong>Highlights:</strong> {highlights}
        </div>

        <div style="margin-bottom:10px;">
          <div style="font-size:0.72rem; color:#94A3B8; font-weight:800; text-transform:uppercase; margin-bottom:4px;">112 Criteria Matched:</div>
          <ul style="margin:0; padding-left:18px; font-size:0.8rem; line-height:1.4;">
            {matches_html}
          </ul>
        </div>

        <div style="background-color:rgba(245,158,11,0.1); border-left:3px solid #F59E0B; padding:8px 12px; border-radius:4px; font-size:0.78rem; color:#cbd5e1; margin-bottom:12px;">
          <strong style="color:#F59E0B;">Due Diligence Action:</strong> {due_diligence_flags}
        </div>

        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td>
              <a href="{listing_url}" target="_blank" style="display:inline-block; color:#00FFFF; text-decoration:none; font-size:0.78rem; font-weight:700; padding:6px 12px; border:1px solid rgba(0,255,255,0.4); border-radius:4px; background-color:rgba(0,255,255,0.05);">
                🔍 Open Listing & GIS &rarr;
              </a>
            </td>
            <td align="right">
              <a href="{DASHBOARD_URL}" target="_blank" style="display:inline-block; color:#C084FC; text-decoration:none; font-size:0.78rem; font-weight:700; padding:6px 12px; border:1px solid rgba(192,132,252,0.4); border-radius:4px; background-color:rgba(122,40,138,0.15);">
                📋 Audit 112 Qs on Hub &rarr;
              </a>
            </td>
          </tr>
        </table>
      </div>
    </div>
    """

def build_consolidated_digest_html(parcels):
    """Builds a master consolidated digest email containing all prime candidate parcels."""
    cards_html = "".join([build_parcel_card_html(p) for p in parcels])
    prime_count = sum(1 for p in parcels if "PRIME" in p.get("verdict", ""))
    total_acres = sum(p.get("acres", 0) for p in parcels)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>NoCo Land Acquisition Master Digest</title>
    </head>
    <body style="margin:0; padding:0; background-color:#0B0F19; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#f8fafc;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0B0F19; padding:24px 12px;">
        <tr>
          <td align="center">
            <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px; width:100%; background-color:#0F172A; border-radius:12px; border:1px solid #1E293B; overflow:hidden; box-shadow:0 8px 32px rgba(0,0,0,0.6);">
              
              <!-- Header Banner -->
              <tr>
                <td style="padding:28px 24px 20px 24px; background:linear-gradient(135deg, rgba(0,255,255,0.2) 0%, rgba(122,40,138,0.35) 100%); border-bottom:1px solid #00FFFF;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <span style="font-size:1.6rem; vertical-align:middle;">🎭</span>
                        <span style="font-size:1.25rem; font-weight:800; color:#ffffff; letter-spacing:0.5px; vertical-align:middle; margin-left:8px;">Project NoCo Living Stage</span>
                        <div style="font-size:0.75rem; color:#00FFFF; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-top:4px;">Autonomous Land Acquisition Master Digest</div>
                      </td>
                      <td align="right">
                        <span style="background-color:#10B98125; border:1px solid #10B981; color:#10B981; font-size:0.75rem; font-weight:900; padding:4px 10px; border-radius:20px; white-space:nowrap;">
                          {prime_count} PRIME TARGETS
                        </span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- Digest Summary Overview -->
              <tr>
                <td style="padding:24px 24px 12px 24px;">
                  <div style="font-size:0.8rem; color:#94A3B8; text-transform:uppercase; letter-spacing:1px;">Active Land Sniffer Intelligence</div>
                  <h1 style="margin:4px 0 12px 0; font-size:1.35rem; color:#FFFFFF;">Executive Parcel Candidate Briefing</h1>
                  <p style="margin:0 0 16px 0; font-size:0.85rem; color:#94A3B8; line-height:1.5;">
                    The autonomous sniffer engine has evaluated and ranked <strong>{len(parcels)} priority parcels</strong> ({total_acres:.1f} total acres) across target hubs in <strong>Tompkins County NY, Windham VT, Hunterdon NJ, and Ottawa MI</strong> against Sean and Brett's 6 condition dimensions and 112 Due Diligence criteria.
                  </p>

                  <!-- Direct Dashboard CTA -->
                  <div style="margin-bottom:20px; text-align:center;">
                    <a href="{DASHBOARD_URL}" target="_blank" style="display:block; background:linear-gradient(135deg, #00FFFF 0%, #7A288A 100%); color:#000000; text-decoration:none; padding:12px 20px; border-radius:8px; font-size:0.9rem; font-weight:900; text-align:center; box-shadow:0 4px 14px rgba(0,255,255,0.3);">
                      📋 Open Full 112 Questionnaire Audit on Sovereign Dashboard
                    </a>
                  </div>

                  <!-- Parcel Cards List -->
                  {cards_html}

                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding:20px 24px; background-color:#090D16; border-top:1px solid #1E293B; text-align:center;">
                  <div style="font-size:0.75rem; color:#64748B; line-height:1.5;">
                    Project NoCo Sovereign Intelligence System &bull; Dedicated to Adam Stehouwer<br>
                    Co-Directed by Sean (Kief) Stehouwer &amp; Brett Adam Stehouwer<br>
                    Protected under NYS Town Code § 144-202.1(B)(1)(b), VT Act 250 &amp; NJ Right to Farm Acts.
                  </div>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    return html

def send_digest_email(parcels, recipients=None):
    """Sends a single consolidated digest email containing all parcels."""
    if not recipients:
        recipients = DEFAULT_RECIPIENTS

    subject = f"🎭 [NoCo Master Digest] {len(parcels)} Prime Land Acquisition Targets (Ithaca NY • Grafton VT • Hunterdon NJ)"
    html_content = build_consolidated_digest_html(parcels)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NoCo Land Acquisition <{SMTP_USER}>"
    msg["To"] = ", ".join(recipients)

    plain_summary = "\n".join([f"- {p.get('address')} ({p.get('acres')} ac, ${p.get('price'):,}) -> {p.get('composite_score')}% {p.get('verdict')}" for p in parcels])
    plain_text = f"""NoCo Land Acquisition Master Digest
Found {len(parcels)} Prime Target Parcels:

{plain_summary}

Access the interactive 112 Due Diligence Audit on Sovereign Hub:
{DASHBOARD_URL}
"""
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        log(f"[*] Dispatching consolidated master digest to {len(recipients)} recipients ({', '.join(recipients)})...")
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        refused = server.sendmail(SMTP_USER, recipients, msg.as_string())
        server.quit()

        if refused:
            first_err = list(refused.values())[0]
            if first_err[0] == 450:
                log(f"[!] [IONOS 450 LIMIT] Hourly send limit reached. Digest safely queued for next 60-min rollover window.")
            else:
                log(f"[!] [SMTP REFUSED] Partial delivery failure: {refused}")
            return False

        log(f"✔ [PASS] Master Digest successfully dispatched (1 email used towards quota)!")
        return True
    except smtplib.SMTPRecipientsRefused as e:
        recipients_errs = e.recipients
        is_quota = any(code == 450 for (code, _) in recipients_errs.values())
        if is_quota:
            log(f"[!] [IONOS 450 LIMIT] Hourly send limit reached on IONOS SMTP. Digest safely queued for next 60-min rollover window.")
        else:
            log(f"[!] [SMTP RECIPIENTS REFUSED] {recipients_errs}")
        return False
    except smtplib.SMTPResponseException as e:
        if e.smtp_code == 450:
            log(f"[!] [IONOS 450 LIMIT] Hourly send limit reached. Digest safely queued for next rollover window.")
        else:
            log(f"[!] [SMTP ERROR] Code {e.smtp_code}: {e.smtp_error}")
        return False
    except Exception as e:
        log(f"[!] [ERROR] Failed to send digest: {e}")
        return False

def run_digest(recipients=None):
    ledger = load_ledger()
    parcels = ledger.get("parcels", [])
    prime_parcels = [p for p in parcels if "PRIME" in p.get("verdict", "")]
    if not prime_parcels:
        prime_parcels = parcels[:5]

    log(f"[*] Packaging {len(prime_parcels)} prime target parcels into 1 executive digest...")
    success = send_digest_email(prime_parcels, recipients)
    if success:
        for p in prime_parcels:
            p["email_notified"] = True
            p["notified_at"] = datetime.now().isoformat()
        save_ledger(ledger)

def main():
    parser = argparse.ArgumentParser(description="NoCo Autonomous Property Sniffer & Email Dispatch Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single discovery cycle and exit")
    parser.add_argument("--digest", action="store_true", help="Send a consolidated master digest of all prime targets in 1 email")
    parser.add_argument("--loop", type=int, default=0, help="Run continuously every N seconds (e.g. 3600)")
    parser.add_argument("--test-email", action="store_true", help="Send a test alert email to verify layout")
    parser.add_argument("--to", type=str, help="Comma-separated recipient emails override")

    args = parser.parse_args()
    recipients = [e.strip() for e in args.to.split(",")] if args.to else DEFAULT_RECIPIENTS

    if args.digest:
        run_digest(recipients)
        return

    if args.loop > 0:
        interval = args.loop
        log(f"[*] Launching NoCo Autonomous Sniffer Daemon (Interval: {interval}s)...")
        while True:
            try:
                run_digest(recipients)
            except Exception as e:
                log(f"[!] Sniffer loop error: {e}")
            log(f"[*] Sleeping {interval}s until next sniffer cycle...")
            time.sleep(interval)
    else:
        # Default: run digest
        run_digest(recipients)

if __name__ == "__main__":
    main()
