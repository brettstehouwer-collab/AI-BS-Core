"""AI-BS Sovereign Business Email Router
Handles production-ready SMTP dispatch, IMAP synchronization, dynamic mailbox stats,
and Stehouwer LLM smart reply drafting for stehouwer-publishing.com.
"""

import os
import re
import json
import time
import ssl
import smtplib
import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import requests

router = APIRouter(prefix="/api/v1/emails", tags=["Business Email"])

# File & Directory Paths
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
CACHE_FILE = os.path.join(BACKEND_DIR, "core", "emails_cache.json")
OUTBOX_FILE = os.path.join(BACKEND_DIR, "core", "email_outbox_queue.json")

# Ensure core directory exists
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)


def _load_env_credentials():
    """Extracts email credentials from .env safely."""
    credentials = {
        "IMAP_USER": "",
        "IMAP_APP_PASSWORD": "",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": 587,
        "IMAP_HOST": "imap.gmail.com",
        "IMAP_PORT": 993,
        "BUSINESS_DOMAIN": "stehouwer-publishing.com",
        "DEFAULT_SENDER": "Brett Stehouwer <brett@stehouwer-publishing.com>",
    }

    env_paths = [os.path.join(BASE_DIR, ".env"), os.path.join(BACKEND_DIR, ".env")]
    for p in env_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k in credentials:
                                credentials[k] = v
            except Exception:
                pass

    # Also check OS environment variables
    for k in credentials:
        if k in os.environ and os.environ[k]:
            credentials[k] = os.environ[k]

    # Strictly sanitize password and user strings
    if credentials.get("IMAP_APP_PASSWORD"):
        credentials["IMAP_APP_PASSWORD"] = str(credentials["IMAP_APP_PASSWORD"]).strip().strip('"').strip("'").replace(" ", "")
    if credentials.get("IMAP_USER"):
        credentials["IMAP_USER"] = str(credentials["IMAP_USER"]).strip().strip('"').strip("'")

    return credentials


def _decode_mime_str(header_val):
    """Safely decodes RFC 2047 encoded MIME strings."""
    if not header_val:
        return ""
    decoded_fragments = decode_header(header_val)
    parts = []
    for fragment, charset in decoded_fragments:
        if isinstance(fragment, bytes):
            try:
                parts.append(fragment.decode(charset or "utf-8", errors="replace"))
            except Exception:
                parts.append(fragment.decode("latin1", errors="replace"))
        else:
            parts.append(str(fragment))
    return "".join(parts).strip()


def _get_cached_emails() -> List[Dict[str, Any]]:
    """Loads all emails from disk cache."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_cached_emails(emails: List[Dict[str, Any]]):
    """Persists emails list to disk cache atomically."""
    temp_file = f"{CACHE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    os.rename(temp_file, CACHE_FILE)


# ==============================================================================
# PYDANTIC MODELS
# ==============================================================================

class SendEmailPayload(BaseModel):
    from_email: Optional[str] = "brett@stehouwer-publishing.com"
    from_name: Optional[str] = "Brett Stehouwer"
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    is_html: Optional[bool] = False


class GenerateReplyPayload(BaseModel):
    sender: str
    subject: str
    body_snippet: str
    user_notes: Optional[str] = ""
    tone_preference: Optional[str] = "Professional"


class IncomingEmailPayload(BaseModel):
    to: Optional[str] = "brett@stehouwer-publishing.com"
    from_name: Optional[str] = "External Sender"
    from_email: Optional[str] = "sender@external.com"
    subject: Optional[str] = "No Subject"
    body: Optional[str] = ""
    category: Optional[str] = "Primary"


# ==============================================================================
# 1. DIAGNOSTICS & SYSTEM STATUS
# ==============================================================================

@router.get("/status")
@router.get("/config-status")
async def get_email_status():
    """Inspects live email infrastructure readiness and connection parameters."""
    creds = _load_env_credentials()
    cached = _get_cached_emails()
    
    imap_user = creds["IMAP_USER"]
    has_app_pwd = bool(creds["IMAP_APP_PASSWORD"])
    
    # Fast non-blocking IMAP probe
    imap_connected = False
    imap_error = None
    
    if imap_user and has_app_pwd:
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(creds["IMAP_HOST"], int(creds["IMAP_PORT"]), ssl_context=context, timeout=3.0)
            mail.login(imap_user, creds["IMAP_APP_PASSWORD"])
            imap_connected = True
            mail.logout()
        except Exception as e:
            err_str = str(e)
            if "Application-specific password required" in err_str:
                imap_error = "Google 2-Step Verification requires a 16-character App Password. Generate one at myaccount.google.com/apppasswords"
            else:
                imap_error = err_str

    unread_count = sum(1 for e in cached if (e.get("folder") or "Inbox") == "Inbox" and not e.get("read", False))
    sent_count = sum(1 for e in cached if e.get("folder") == "Sent")
    trash_count = sum(1 for e in cached if e.get("folder") == "Trash")

    last_sync_time = None
    if os.path.exists(CACHE_FILE):
        last_sync_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).isoformat()

    return {
        "status": "success",
        "domain": creds["BUSINESS_DOMAIN"],
        "primary_account": "brett@stehouwer-publishing.com",
        "relay_user": imap_user or "Not Configured",
        "has_app_password": has_app_pwd,
        "imap_status": {
            "host": creds["IMAP_HOST"],
            "port": creds["IMAP_PORT"],
            "connected": imap_connected,
            "error": imap_error
        },
        "smtp_status": {
            "host": creds["SMTP_HOST"],
            "port": creds["SMTP_PORT"],
            "ready": bool(imap_user and has_app_pwd)
        },
        "mailbox_stats": {
            "total_cached": len(cached),
            "unread_inbox": unread_count,
            "sent": sent_count,
            "trash": trash_count,
            "last_sync": last_sync_time
        }
    }


# ==============================================================================
# 2. INBOX RETRIEVAL & WEBHOOK INGESTION
# ==============================================================================

@router.get("")
@router.get("/")
async def get_emails(account: Optional[str] = None, folder: Optional[str] = None):
    """Returns stored emails with normalized accounts and folder filtering."""
    emails = _get_cached_emails()
    
    # Normalize legacy "unknown" account tags to brett@stehouwer-publishing.com
    mutated = False
    for em in emails:
        acc = (em.get("account") or "").strip().lower()
        if not acc or acc == "unknown" or "stehouwerpublishing.com" in acc:
            em["account"] = "brett@stehouwer-publishing.com"
            em["label"] = "[Imap]/Brett"
            mutated = True
            
    if mutated:
        _save_cached_emails(emails)

    if account and account != "all":
        target = account.strip().lower()
        emails = [e for e in emails if e.get("account", "").lower() == target or target in e.get("account", "").lower()]
        
    if folder and folder != "All":
        emails = [e for e in emails if (e.get("folder") or "Inbox").lower() == folder.lower()]

    return {"status": "success", "data": emails, "count": len(emails)}


@router.post("/incoming")
async def receive_incoming_email(payload: IncomingEmailPayload):
    """Receives inbound messages from Cloudflare Email Workers or webhooks."""
    try:
        recipient = payload.to or "brett@stehouwer-publishing.com"
        if "@" not in recipient:
            recipient = f"{recipient}@stehouwer-publishing.com"

        name_part = recipient.split("@")[0].capitalize()
        label = f"[Imap]/{name_part}"

        new_email = {
            "id": f"em-{int(time.time() * 1000)}",
            "account": recipient,
            "sender": payload.from_name,
            "email": payload.from_email,
            "subject": payload.subject,
            "snippet": (payload.body or "")[:180],
            "body": payload.body or "",
            "time": datetime.now().strftime("%I:%M %p"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": payload.category or "Primary",
            "folder": "Inbox",
            "starred": False,
            "read": False,
            "label": label,
        }

        emails = _get_cached_emails()
        emails.insert(0, new_email)
        _save_cached_emails(emails)

        return {"status": "success", "message": "Inbound email ingested into AI-BS Inbox", "data": new_email}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ==============================================================================
# 3. LIVE IMAP SYNCHRONIZATION
# ==============================================================================

@router.post("/sync")
async def sync_emails_from_imap():
    """Performs live IMAP poll from imap.gmail.com:993 and normalizes into local cache."""
    creds = _load_env_credentials()
    imap_user = creds["IMAP_USER"]
    app_pwd = creds["IMAP_APP_PASSWORD"]

    if not imap_user or not app_pwd:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "IMAP credentials missing in .env. Please set IMAP_USER and IMAP_APP_PASSWORD.",
            },
        )

    try:
        imaplib._MAXLINE = 10000000
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(creds["IMAP_HOST"], int(creds["IMAP_PORT"]), ssl_context=context, timeout=15.0)
        mail.login(imap_user, app_pwd)
        res, count_data = mail.select("INBOX", readonly=True)
        if res != "OK" or not count_data or not count_data[0]:
            mail.logout()
            return {"status": "success", "message": "Inbox is empty or no messages found.", "synced": 0}

        total_msgs = int(count_data[0])
        if total_msgs == 0:
            mail.logout()
            return {"status": "success", "message": "Inbox is empty.", "synced": 0}

        # Retrieve the latest 50 messages via sequence range
        start_seq = max(1, total_msgs - 49)
        seq_range = f"{start_seq}:{total_msgs}"

        cached_emails = _get_cached_emails()
        existing_ids = {e.get("imap_uid") or e.get("id") for e in cached_emails}
        existing_msg_ids = {e.get("message_id") for e in cached_emails if e.get("message_id")}

        status, msg_data = mail.fetch(seq_range, "(RFC822)")
        if status != "OK" or not msg_data:
            mail.logout()
            return {"status": "success", "message": "No messages could be fetched.", "synced": 0}

        new_items = []

        for response_part in reversed(msg_data):
            if not isinstance(response_part, tuple) or len(response_part) < 2:
                continue
            seq_header = response_part[0]
            raw_email = response_part[1]
            if not raw_email or not isinstance(raw_email, bytes):
                continue

            try:
                msg_id_str = seq_header.split()[0].decode(errors="ignore")
            except Exception:
                msg_id_str = str(int(time.time() * 1000))

            if msg_id_str in existing_ids:
                continue

            msg = email.message_from_bytes(raw_email)
            message_id_header = (msg.get("Message-ID") or "").strip()
            if message_id_header and message_id_header in existing_msg_ids:
                continue

            subject = _decode_mime_str(msg.get("Subject", "No Subject"))
            sender = _decode_mime_str(msg.get("From", "Unknown Sender"))
            to_field = _decode_mime_str(msg.get("To", "brett@stehouwer-publishing.com"))
            date_str = msg.get("Date", "")

            # Parse sender name vs email
            sender_name = sender
            sender_email = sender
            if "<" in sender and ">" in sender:
                sender_name = sender.split("<")[0].strip().strip('"')
                sender_email = sender.split("<")[1].split(">")[0].strip()

            # Parse body
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                            break
                    elif content_type == "text/html" and not body_text and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            # Basic HTML stripping
                            html_str = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                            body_text = re.sub(r"<[^>]+>", " ", html_str)
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")

            # Clean and sanitize whitespace
            body_text = re.sub(r"[ \t]+", " ", body_text).strip()

            # Normalize Team Account
            account = "brett@stehouwer-publishing.com"
            to_lower = to_field.lower()
            if "sean" in to_lower:
                account = "sean@stehouwer-publishing.com"
            elif "julie" in to_lower:
                account = "julie@stehouwer-publishing.com"

            label = f"[Imap]/{account.split('@')[0].capitalize()}"

            # Format timestamp
            time_display = datetime.now().strftime("%I:%M %p")
            date_display = datetime.now().strftime("%Y-%m-%d")
            try:
                parsed_date = email.utils.parsedate_to_datetime(date_str)
                time_display = parsed_date.strftime("%I:%M %p")
                date_display = parsed_date.strftime("%Y-%m-%d")
            except Exception:
                pass

            item = {
                "id": f"em-imap-{msg_id_str}",
                "imap_uid": msg_id_str,
                "message_id": message_id_header,
                "account": account,
                "sender": sender_name or sender_email,
                "email": sender_email,
                "subject": subject,
                "snippet": body_text[:180] if body_text else "No Body Content",
                "body": body_text or "No Body Content",
                "time": time_display,
                "date": date_display,
                "category": "Primary",
                "folder": "Inbox",
                "starred": False,
                "read": False,
                "label": label,
            }

            new_items.append(item)

        mail.logout()

        if new_items:
            combined = new_items + cached_emails
            _save_cached_emails(combined)

        return {
            "status": "success",
            "message": f"Sync completed successfully. Synced {len(new_items)} new messages.",
            "synced_count": len(new_items),
            "total_messages": len(cached_emails) + len(new_items),
        }

    except Exception as e:
        err_str = str(e)
        if "Application-specific password required" in err_str:
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": "APP_PASSWORD_REQUIRED",
                    "message": "Google requires an App Password. Please generate a 16-character key at myaccount.google.com/apppasswords and update IMAP_APP_PASSWORD in .env.",
                },
            )
        return JSONResponse(status_code=500, content={"status": "error", "message": f"IMAP Sync failed: {err_str}"})


# ==============================================================================
# 4. REAL SMTP DISPATCH (/api/v1/emails/send)
# ==============================================================================

@router.post("/send")
async def send_email(payload: SendEmailPayload):
    """Transmits real outbound email via authenticated SMTP over TLS (port 587)."""
    creds = _load_env_credentials()
    imap_user = creds["IMAP_USER"]
    app_pwd = creds["IMAP_APP_PASSWORD"]

    if not imap_user or not app_pwd:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "SMTP credentials not configured. Please set IMAP_USER and IMAP_APP_PASSWORD in .env.",
            },
        )

    # Clean from/to addresses
    from_addr = payload.from_email or "brett@stehouwer-publishing.com"
    if "@" not in from_addr:
        from_addr = f"{from_addr}@stehouwer-publishing.com"

    from_name = payload.from_name or "Brett Stehouwer"
    formatted_from = f"{from_name} <{from_addr}>"

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = payload.subject
    msg["From"] = formatted_from
    msg["To"] = payload.to
    msg["Reply-To"] = from_addr
    msg["Date"] = email.utils.formatdate(localtime=True)

    if payload.cc:
        msg["Cc"] = payload.cc

    # Attach body
    text_part = MIMEText(payload.body, "plain", "utf-8")
    msg.attach(text_part)

    if payload.is_html:
        html_part = MIMEText(f"<html><body><p>{payload.body.replace(chr(10), '<br>')}</p></body></html>", "html", "utf-8")
        msg.attach(html_part)

    recipients = [payload.to]
    if payload.cc:
        recipients.extend([c.strip() for c in payload.cc.split(",") if c.strip()])
    if payload.bcc:
        recipients.extend([b.strip() for b in payload.bcc.split(",") if b.strip()])

    try:
        # Connect to SMTP server with TLS
        server = smtplib.SMTP(creds["SMTP_HOST"], int(creds["SMTP_PORT"]), timeout=15.0)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(imap_user, app_pwd)
        server.sendmail(imap_user, recipients, msg.as_string())
        server.quit()

        # Record sent email in local cache
        sent_id = f"em-sent-{int(time.time() * 1000)}"
        sent_record = {
            "id": sent_id,
            "account": from_addr,
            "sender": from_name,
            "email": payload.to,
            "subject": payload.subject,
            "snippet": payload.body[:180],
            "body": payload.body,
            "time": datetime.now().strftime("%I:%M %p"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": "Primary",
            "folder": "Sent",
            "starred": False,
            "read": True,
            "label": f"[Imap]/{from_name.split()[0]}",
        }

        emails = _get_cached_emails()
        emails.insert(0, sent_record)
        _save_cached_emails(emails)

        return {
            "status": "success",
            "message": f"Email successfully dispatched to {payload.to} from {formatted_from}",
            "data": sent_record,
        }

    except smtplib.SMTPAuthenticationError as auth_err:
        err_msg = str(auth_err)
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "code": "SMTP_AUTH_ERROR",
                "message": "SMTP Authentication Failed. Google requires a 16-character App Password. Please generate one at myaccount.google.com/apppasswords and update IMAP_APP_PASSWORD in .env.",
                "raw_error": err_msg,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"SMTP Dispatch Error: {str(e)}"},
        )


# ==============================================================================
# 5. OLLAMA STEHOUWER LLM SMART REPLY
# ==============================================================================

@router.post("/generate-reply")
async def generate_email_reply(payload: GenerateReplyPayload):
    """Uses local Ollama stehouwer_llm (port 11434) to draft a contextual business reply."""
    prompt = f"""You are Stehouwer LLM, communication director for Stehouwer Publishing (stehouwer-publishing.com).
Draft a concise, polished business email response to the following inquiry.

Target Tone: {payload.tone_preference}
User Guidance Notes: {payload.user_notes if payload.user_notes else "Politely acknowledge receipt, answer clearly, and propose next steps."}

--- Inbound Message ---
From: {payload.sender}
Subject: {payload.subject}
Content:
{payload.body_snippet[:1500]}

--- Instructions ---
- Provide ONLY the body text of the response email.
- Do NOT include markdown code fences (no ```).
- Conclude with:
  Best regards,
  Brett Stehouwer
  Stehouwer Publishing
  brett@stehouwer-publishing.com
"""

    endpoints = [
        ("http://127.0.0.1:11434/api/generate", "stehouwer_llm"),
        ("http://127.0.0.1:11435/api/generate", "qwen2.5-coder:7b"),
        ("http://127.0.0.1:11434/api/generate", "llama3.1"),
    ]

    for url, model in endpoints:
        try:
            resp = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=3.0,
            )
            if resp.status_code == 200:
                draft_text = resp.json().get("response", "").strip()
                if draft_text:
                    return {
                        "status": "success",
                        "model": model,
                        "draft": draft_text,
                    }
        except Exception:
            continue

    # Clean local deterministic fallback if Ollama is currently offline
    fallback_draft = f"""Hi {payload.sender.split()[0] if payload.sender else 'there'},

Thank you for reaching out regarding "{payload.subject}".

I have received your message and will review the details right away. We will follow up with you shortly.

Best regards,
Brett Stehouwer
Stehouwer Publishing
brett@stehouwer-publishing.com"""

    return {
        "status": "success",
        "model": "deterministic_fallback",
        "draft": fallback_draft,
    }
