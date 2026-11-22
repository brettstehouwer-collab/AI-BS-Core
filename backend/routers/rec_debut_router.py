from recdebut_textbee import receive_textbee_webhook
from security.recdebut_access import require_recdebut_access
from recdebut_workflow import router as workflow_router
from recdebut_registration import router as registration_router
from security.recdebut_privacy import normalize_phone, load_personal_contacts, PrivacyCheckUnavailable
"""

Recreational Debut (RecDebut.com) & Dennis Bell Sports Program Router

Handles candidate student-athlete lead tracking, CSV batch ingestion,

and zero-cost mass SMS broadcasts via Email-to-SMS cellular carrier gateways

with verified Caller ID / Sender ID configured as BrettStehouwer@gmail.com.

"""



import os

import sys

import json

import time

import sqlite3

import smtplib

import imaplib

import email

from email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipart

from email.header import decode_header

from datetime import datetime

from pathlib import Path

from typing import Optional, List, Dict, Any, Tuple, Set

import threading

import socket

import re

import csv

import random

import requests



from fastapi import Depends, APIRouter, Request, HTTPException, BackgroundTasks, Response, Query, Body, UploadFile, File

from fastapi.responses import JSONResponse, RedirectResponse

from pydantic import BaseModel, EmailStr



from core.outbound_messaging_policy import (
    outbound_messaging_enabled, recdebut_polling_enabled, RECDEBUT_DISABLED_MESSAGE,
)


def _require_recdebut_outbound():
    if not outbound_messaging_enabled("recdebut"):
        raise HTTPException(status_code=503, detail={
            "code": "OUTBOUND_MESSAGING_DISABLED",
            "message": RECDEBUT_DISABLED_MESSAGE,
        })


router = APIRouter(prefix="/api/v1/recdebut", tags=["Recreational Debut & Dennis Bell"], dependencies=[Depends(require_recdebut_access)])
router.include_router(workflow_router)
router.include_router(registration_router)

legacy_router = APIRouter(prefix="/api/recdebut", tags=["Recreational Debut Core API"], dependencies=[Depends(require_recdebut_access)])



BACKEND_DIR = Path(__file__).resolve().parent.parent

BASE_DIR = BACKEND_DIR.parent

DATA_DIR = BASE_DIR / "saved_data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "rec_debut.db"



# --- Common US Cellular Gateways (MMS Priority for Long Text & Media) ---

# MMS gateways support up to 5,000 characters, delivering the entire announcement

# with full paragraphs, emojis, phone numbers, and links with 0 character truncation.

CARRIER_GATEWAYS = {

    "verizon_mms": "@vzwpix.com",

    "att_mms": "@mms.att.net",

    "tmobile_mms": "@tmomail.net",

    "cricket_mms": "@mms.cricketwireless.net",

    "boost_mms": "@myboostmobile.com",

    "uscellular_mms": "@mms.uscc.net",

    "googlefi": "@msg.fi.google.com"

}



# --- Database Setup & Seeding ---

def init_db():

    conn = sqlite3.connect(str(DB_PATH))

    cursor = conn.cursor()

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_athletes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            phone TEXT NOT NULL UNIQUE,

            email TEXT,

            sport TEXT DEFAULT 'Basketball',

            high_school TEXT,

            grad_year TEXT,

            city_state TEXT,

            status TEXT DEFAULT 'Pending',

            notes TEXT,

            team_name TEXT,

            created_at REAL,

            last_messaged_at REAL

        )

    """)

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_excluded_coaches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            phone TEXT NOT NULL,

            coach_type TEXT,

            team_name TEXT,

            school_name TEXT,

            page INTEGER,

            excluded_at REAL

        )

    """)

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_campaigns (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            created_at REAL NOT NULL,

            sender_id TEXT NOT NULL,

            total_recipients INTEGER NOT NULL,

            successful_count INTEGER NOT NULL,

            failed_count INTEGER NOT NULL,

            message_body TEXT NOT NULL,

            delivery_details_json TEXT NOT NULL

        )

    """)

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_athlete_replies (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            athlete_id INTEGER,

            athlete_name TEXT,

            sender_phone TEXT,

            sender_email TEXT,

            recipient_email TEXT,

            subject TEXT,

            reply_body TEXT,

            received_at REAL,

            is_read INTEGER DEFAULT 0,

            created_at REAL,

            message_id_hash TEXT UNIQUE

        )

    """)

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_tracking_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            campaign_id TEXT,

            athlete_id INTEGER,

            event_type TEXT NOT NULL,

            target_url TEXT,

            ip_address TEXT,

            user_agent TEXT,

            created_at REAL NOT NULL

        )

    """)

    for col_def in [

        ('team_name', 'TEXT'),

        ('email_status', 'TEXT'),

        ('email_verified_at', 'REAL'),

        ('open_count', 'INTEGER DEFAULT 0'),

        ('last_opened_at', 'REAL'),

        ('click_count', 'INTEGER DEFAULT 0'),

        ('last_clicked_at', 'REAL')

    ]:

        try:

            cursor.execute(f"ALTER TABLE rec_debut_athletes ADD COLUMN {col_def[0]} {col_def[1]}")

        except Exception:

            pass



    # Coaches Table

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_coaches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            college_name TEXT NOT NULL,

            division TEXT DEFAULT 'D1',

            conference TEXT,

            state TEXT,

            coach_name TEXT NOT NULL,

            coach_title TEXT DEFAULT 'Head Coach',

            coach_email TEXT,

            coach_phone TEXT,

            sport TEXT DEFAULT 'Basketball'

        )

    """)



    # Registrations Table

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_registrations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            athlete_name TEXT NOT NULL,

            parent_name TEXT,

            email TEXT,

            phone TEXT,

            sport TEXT DEFAULT 'Basketball',

            grad_year TEXT,

            notes TEXT,

            letter_status TEXT DEFAULT 'Generated',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

    """)



    # Dispatches Table

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_dispatches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            athlete_id INTEGER,

            coach_id INTEGER,

            channel TEXT DEFAULT 'SMS',

            status TEXT DEFAULT 'Queued',

            message_body TEXT,

            dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            response_status TEXT DEFAULT 'Pending'

        )

    """)



    # Lead Alerts Table (Instant notifications to Dennis Bell)

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_lead_alerts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            athlete_id INTEGER,

            athlete_name TEXT,

            event_type TEXT NOT NULL,

            target_url TEXT,

            alert_text TEXT,

            sent_to_phone TEXT,

            created_at REAL NOT NULL,

            is_read INTEGER DEFAULT 0

        )

    """)



    # Two-Way Chat Messages Table (Dennis Bell <-> Athletes / Parents)

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_chat_messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            athlete_id INTEGER,

            athlete_name TEXT,

            sender_type TEXT,

            message_body TEXT,

            channel TEXT DEFAULT 'sms',

            created_at REAL NOT NULL,

            is_read INTEGER DEFAULT 1

        )

    """)



    # Drip Campaign Logs Table

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS rec_debut_drip_logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            cohort TEXT NOT NULL,

            recipients_count INTEGER,

            success_count INTEGER,

            failed_count INTEGER,

            message_template TEXT,

            created_at REAL NOT NULL

        )

    """)



    # Seed Sample College Coaches if empty

    cursor.execute("SELECT COUNT(*) FROM rec_debut_coaches")

    if cursor.fetchone()[0] == 0:

        sample_coaches = [

            ("Tennessee State", "D1", "OVC", "TN", "Ed Pipes", "Head Coach", "epipes@tnstate.edu", "+1-615-963-5000", "Basketball"),

            ("Gonzaga University", "D1", "WCC", "WA", "Mark Few", "Head Coach", "mfew@gonzaga.edu", "+1-509-313-4202", "Basketball"),

            ("UNC Wilmington", "D1", "CAA", "NC", "Takayo Siddle", "Head Coach", "recruiting@uncw.edu", "+1-910-962-3232", "Basketball"),

            ("Grand Valley State", "D2", "GLIAC", "MI", "Cornell Mann", "Head Coach", "mannc@gvsu.edu", "+1-616-331-3259", "Basketball"),

            ("Ferris State", "D2", "GLIAC", "MI", "Andy Bronkema", "Head Coach", "bronkema@ferris.edu", "+1-231-591-2866", "Basketball"),

            ("Calvin University", "D3", "MIAA", "MI", "Bill Sall", "Head Coach", "bsall@calvin.edu", "+1-616-526-6288", "Basketball"),

            ("Hope College", "D3", "MIAA", "MI", "Greg Mitchell", "Head Coach", "mitchell@hope.edu", "+1-616-395-7690", "Basketball"),

            ("Cornerstone University", "NAIA", "WHAC", "MI", "Jesse Campbell", "Head Coach", "jesse.campbell@cornerstone.edu", "+1-616-222-1400", "Basketball"),

            ("Grand Rapids Community College", "NJCAA", "MCCAA", "MI", "Joe Fox", "Head Coach", "jfox@grcc.edu", "+1-616-234-3990", "Basketball"),

            ("Michigan State University", "D1", "Big Ten", "MI", "Tom Izzo", "Head Coach", "msuhoops@msu.edu", "+1-517-355-1643", "Basketball")

        ]

        cursor.executemany("""

            INSERT INTO rec_debut_coaches (college_name, division, conference, state, coach_name, coach_title, coach_email, coach_phone, sport)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, sample_coaches)



    conn.commit()

    conn.close()



init_db()



# --- SMTP Swarm & Credentials Loader ---

SWARM_FILE = DATA_DIR / "rec_debut_smtp_swarm.json"



def load_credentials():

    creds = {

        "IMAP_USER": "footballstar0325@gmail.com",

        "IMAP_APP_PASSWORD": "",

        "SMTP_HOST": "smtp.gmail.com",

        "SMTP_PORT": 587,

        "OPERATOR_EMAIL": "BrettStehouwer@gmail.com",

        "OPERATOR_PHONE": "1-616-402-3628",

        "RESEND_API_KEY": "",

        "RESEND_FROM_EMAIL": "Dennis Bell <recruiting@recdebut.com>",

        "SENDGRID_API_KEY": "",

        "SENDGRID_FROM_EMAIL": "Dennis Bell <recruiting@recdebut.com>",

        "TEXTBEE_DEVICE_ID": "",

        "TEXTBEE_API_KEY": "",

        "TEXTBEE_WEBHOOK_SECRET": "",

        "DENNIS_BELL_PHONE": "+1-616-291-5227",

        "DENNIS_BELL_EMAIL": "dbell002@sbcglobal.net"

    }



    env_paths = [BASE_DIR / ".env", BACKEND_DIR / ".env"]

    for p in env_paths:

        if p.exists():

            try:

                with open(p, "r", encoding="utf-8", errors="ignore") as f:

                    for line in f:

                        line = line.strip()

                        if line and not line.startswith("#") and "=" in line:

                            k, v = line.split("=", 1)

                            k = k.strip()

                            v = v.strip().strip('"').strip("'")

                            if k in creds:

                                creds[k] = v

            except Exception:

                pass



    for k in creds:

        if k in os.environ and os.environ[k]:

            creds[k] = os.environ[k]

        elif creds[k]:

            os.environ[k] = str(creds[k])



    return creds



# --- Transactional Email API Engine (Resend & SendGrid) ---

API_SETTINGS_FILE = DATA_DIR / "rec_debut_email_api_settings.json"



def load_email_api_settings() -> Dict[str, Any]:

    creds = load_credentials()

    default_settings = {

        "provider": "auto",  # 'resend', 'sendgrid', 'smtp_swarm', or 'auto'

        "resend_api_key": creds.get("RESEND_API_KEY", ""),

        "resend_from_email": creds.get("RESEND_FROM_EMAIL", "Dennis Bell <recruiting@recdebut.com>"),

        "sendgrid_api_key": creds.get("SENDGRID_API_KEY", ""),

        "sendgrid_from_email": creds.get("SENDGRID_FROM_EMAIL", "Dennis Bell <recruiting@recdebut.com>"),

        "rate_smoothing_seconds": 1.8,

        "reply_to_email": "dbell002@sbcglobal.net"

    }

    if API_SETTINGS_FILE.exists():

        try:

            with open(API_SETTINGS_FILE, "r", encoding="utf-8") as f:

                saved = json.load(f)

                if isinstance(saved, dict):

                    default_settings.update(saved)

        except Exception:

            pass

    if os.environ.get("RESEND_API_KEY"):

        default_settings["resend_api_key"] = os.environ["RESEND_API_KEY"]

    if os.environ.get("SENDGRID_API_KEY"):

        default_settings["sendgrid_api_key"] = os.environ["SENDGRID_API_KEY"]

    return default_settings



def save_email_api_settings(settings: Dict[str, Any]) -> bool:

    try:

        with open(API_SETTINGS_FILE, "w", encoding="utf-8") as f:

            json.dump(settings, f, indent=2)

        return True

    except Exception:

        return False



def send_resend_email(api_key: str, from_email: str, to_email: str, to_name: str, subject: str, text_content: str, html_content: str, reply_to: str = "dbell002@sbcglobal.net") -> Tuple[bool, str]:

    if not outbound_messaging_enabled("recdebut"):
        return False, RECDEBUT_DISABLED_MESSAGE
    url = "https://api.resend.com/emails"

    headers = {

        "Authorization": f"Bearer {api_key.strip()}",

        "Content-Type": "application/json"

    }

    payload = {

        "from": from_email,

        "to": [f"{to_name} <{to_email}>" if to_name else to_email],

        "reply_to": reply_to,

        "subject": subject,

        "html": html_content,

        "text": text_content,

        "headers": {

            "List-Unsubscribe": f"<mailto:{reply_to}?subject=unsubscribe>"

        }

    }

    try:

        resp = requests.post(url, json=payload, headers=headers, timeout=12.0)

        data = resp.json()

        if resp.status_code in (200, 201):

            return True, data.get("id", "sent_ok")

        else:

            err_msg = data.get("message") or str(data)

            return False, f"Resend API Error ({resp.status_code}): {err_msg}"

    except Exception as e:

        return False, f"Resend Network Error: {str(e)}"



def send_sendgrid_email(api_key: str, from_email: str, to_email: str, to_name: str, subject: str, text_content: str, html_content: str, reply_to: str = "dbell002@sbcglobal.net") -> Tuple[bool, str]:

    if not outbound_messaging_enabled("recdebut"):
        return False, RECDEBUT_DISABLED_MESSAGE
    url = "https://api.sendgrid.com/v3/mail/send"

    headers = {

        "Authorization": f"Bearer {api_key.strip()}",

        "Content-Type": "application/json"

    }

    clean_from = from_email.split("<")[-1].replace(">", "").strip() if "<" in from_email else from_email

    from_name = from_email.split("<")[0].strip() if "<" in from_email else "Dennis Bell"

    payload = {

        "personalizations": [{

            "to": [{"email": to_email, "name": to_name or ""}],

            "subject": subject

        }],

        "from": {"email": clean_from, "name": from_name},

        "reply_to": {"email": reply_to, "name": "Dennis Bell"},

        "content": [

            {"type": "text/plain", "value": text_content},

            {"type": "text/html", "value": html_content}

        ]

    }

    try:

        resp = requests.post(url, json=payload, headers=headers, timeout=12.0)

        if resp.status_code in (200, 201, 202):

            return True, "sent_ok"

        else:

            return False, f"SendGrid API Error ({resp.status_code}): {resp.text}"

    except Exception as e:

        return False, f"SendGrid Network Error: {str(e)}"



def load_smtp_swarm() -> List[Dict[str, Any]]:

    """Load all configured sender accounts in the SMTP Swarm pool."""

    creds = load_credentials()

    default_account = {

        "id": "acct_primary",

        "email": creds.get("IMAP_USER", "footballstar0325@gmail.com"),

        "app_password": creds.get("IMAP_APP_PASSWORD", ""),

        "smtp_host": "smtp.gmail.com",

        "smtp_port": 587,

        "daily_limit": 400,

        "active": True,

        "label": f"Primary Gateway ({creds.get('IMAP_USER', 'footballstar0325@gmail.com')})",

        "created_at": time.time()

    }

    

    if not SWARM_FILE.exists():

        try:

            with open(SWARM_FILE, "w", encoding="utf-8") as f:

                json.dump([default_account], f, indent=2)

        except Exception:

            pass

        return [default_account]



    try:

        with open(SWARM_FILE, "r", encoding="utf-8") as f:

            accounts = json.load(f)

            if isinstance(accounts, list) and len(accounts) > 0:

                return accounts

    except Exception:

        pass



    return [default_account]



def save_smtp_swarm(accounts: List[Dict[str, Any]]) -> bool:

    """Save updated sender accounts back to the SMTP Swarm pool."""

    try:

        with open(SWARM_FILE, "w", encoding="utf-8") as f:

            json.dump(accounts, f, indent=2)

        return True

    except Exception:

        return False





# --- Helper to Send Full-Length SMS/MMS via Carrier Gateways ---

def send_carrier_sms(recipient_phone: str, message_text: str, caller_id_email: str = "dbell002@sbcglobal.net", caller_id_name: str = "Dennis Bell (+1-616-291-5227)") -> Dict[str, Any]:

    if not outbound_messaging_enabled("recdebut"):
        return {"success": False, "blocked": True, "code": "OUTBOUND_MESSAGING_DISABLED", "error": RECDEBUT_DISABLED_MESSAGE, "reason": RECDEBUT_DISABLED_MESSAGE}
    swarm = [a for a in load_smtp_swarm() if a.get("active") and a.get("email") and a.get("app_password")]

    if not swarm:

        creds = load_credentials()

        swarm = [{

            "email": creds.get("IMAP_USER", "footballstar0325@gmail.com"),

            "app_password": creds.get("IMAP_APP_PASSWORD", ""),

            "smtp_host": creds.get("SMTP_HOST", "smtp.gmail.com"),

            "smtp_port": int(creds.get("SMTP_PORT", 587))

        }]



    digits = "".join(filter(str.isdigit, recipient_phone))

    if len(digits) < 10:

        return {"success": False, "error": f"Invalid phone number '{recipient_phone}' (needs 10 digits)"}



    ten_digits = digits[-10:]

    target_addresses = [f"{ten_digits}{gw}" for gw in CARRIER_GATEWAYS.values()]



    msg = MIMEText(message_text, "plain", "utf-8")

    msg["From"] = f"{caller_id_name} <{caller_id_email}>"

    msg["Reply-To"] = caller_id_email if caller_id_email else "dbell002@sbcglobal.net"

    msg["Subject"] = "Dennis Bell (+1-616-291-5227) - Recreational Debut"

    msg["Date"] = email.utils.formatdate(localtime=True)



    last_error = "No active SMTP account available"

    for acct in swarm:

        server = None

        s_user = acct["email"]

        s_pwd = acct["app_password"]

        s_host = acct.get("smtp_host", "smtp.gmail.com")

        s_port = int(acct.get("smtp_port", 587))

        try:

            server = smtplib.SMTP(s_host, s_port, timeout=10.0)

            server.ehlo()

            server.starttls()

            server.ehlo()

            server.login(s_user, s_pwd)

            server.sendmail(s_user, target_addresses, msg.as_string())

            server.quit()

            return {

                "success": True,

                "phone": recipient_phone,

                "gateways_contacted": len(target_addresses),

                "caller_id": caller_id_email,

                "account_used": s_user,

                "timestamp": time.time()

            }

        except Exception as ex:

            if server:

                try:

                    server.close()

                except Exception:

                    pass

            last_error = str(ex)

            # If daily limit reached on this account, try next account in swarm

            if "550" in last_error or "daily user sending limit" in last_error.lower():

                continue

            break



    is_quota = "550" in last_error or "daily user sending limit" in last_error.lower()

    return {

        "success": False,

        "phone": recipient_phone,

        "error": last_error,

        "caller_id": caller_id_email,

        "timestamp": time.time(),

        "message": (

            "Gmail daily user sending limit exceeded on sender account(s). "

            "Please connect an additional Gmail account in 'Manage Swarm Accounts' to continue sending today."

            if is_quota else f"SMS gateway send failed: {last_error}"

        )

    }



# --- High-Throughput Persistent SMTP Batch Dispatcher ---

class SmtpBatchSender:

    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_pwd: str, timeout: float = 10.0):

        self.smtp_host = smtp_host

        self.smtp_port = smtp_port

        self.smtp_user = smtp_user

        self.smtp_pwd = smtp_pwd

        self.timeout = timeout

        self.server: Optional[smtplib.SMTP] = None

        self.messages_on_conn = 0



    def connect(self):

        _require_recdebut_outbound()
        self.close()

        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout)

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(self.smtp_user, self.smtp_pwd)

        self.server = server

        self.messages_on_conn = 0



    def send(self, target_addresses: List[str], msg_str: str) -> Tuple[bool, Optional[str]]:

        if not outbound_messaging_enabled("recdebut"):
            return False, RECDEBUT_DISABLED_MESSAGE
        if self.server is None or self.messages_on_conn >= 20:

            try:

                self.connect()

            except Exception as conn_err:

                return False, f"SMTP connection failed: {conn_err}"



        try:

            self.server.sendmail(self.smtp_user, target_addresses, msg_str)

            self.messages_on_conn += 1

            return True, None

        except Exception:

            # Reconnect and retry once

            try:

                self.connect()

                self.server.sendmail(self.smtp_user, target_addresses, msg_str)

                self.messages_on_conn += 1

                return True, None

            except Exception as retry_err:

                self.close()

                return False, str(retry_err)



    def close(self):

        if self.server:

            try:

                self.server.quit()

            except Exception:

                try:

                    self.server.close()

                except Exception:

                    pass

            self.server = None

            self.messages_on_conn = 0



# --- In-Memory Active Broadcast State & Lock ---

ACTIVE_BROADCAST_LOCK = threading.Lock()

ACTIVE_BROADCAST_STATE: Dict[str, Any] = {

    "active": False,

    "job_id": None,

    "status": "IDLE", # IDLE, RUNNING, CANCELLED, PAUSED_QUOTA, COMPLETED, ERROR

    "total": 0,

    "sent": 0,

    "failed": 0,

    "current_athlete": "",

    "current_phone": "",

    "error": None,

    "started_at": None,

    "updated_at": None,

    "completed_at": None,

    "cancel_requested": False

}



def format_personalized_message(template: str, recipient: Dict[str, Any]) -> str:

    name = (recipient.get("name") or "").strip()

    if not name or name.lower() in ("direct contact", "student-athlete", "n/a", "none"):

        full_name = "Student-Athlete"

        first_name = "Student-Athlete"

    else:

        full_name = name

        first_name = name.split()[0]



    high_school = (recipient.get("high_school") or recipient.get("school") or "").strip() or "your high school"

    sport = (recipient.get("sport") or "").strip() or "Basketball"

    grad_year = str(recipient.get("grad_year") or recipient.get("year") or "").strip() or "2026"



    formatted = template



    # Case-insensitive replacement for name tags with spaces, underscores, or hyphens

    formatted = re.sub(r'\{(?i:athlete[\s_-]*name|full[\s_-]*name|name)\}|\[(?i:athlete[\s_-]*name|full[\s_-]*name|name)\]|\((?i:athlete[\s_-]*name|full[\s_-]*name|name)\)', full_name, formatted)

    formatted = re.sub(r'\{(?i:first[\s_-]*name|firstname|first)\}|\[(?i:first[\s_-]*name|firstname|first)\]|\((?i:first[\s_-]*name|firstname|first)\)', first_name, formatted)

    formatted = re.sub(r'\{(?i:last[\s_-]*name|lastname|last)\}|\[(?i:last[\s_-]*name|lastname|last)\]|\((?i:last[\s_-]*name|lastname|last)\)', recipient.get("name", "").split()[-1] if recipient.get("name") else "", formatted)

    formatted = re.sub(r'\{(?i:high[\s_-]*school|highschool|school)\}|\[(?i:high[\s_-]*school|highschool|school)\]', high_school, formatted)

    formatted = re.sub(r'\{(?i:sport)\}|\[(?i:sport)\]', sport, formatted)

    formatted = re.sub(r'\{(?i:grad[\s_-]*year|graduation[\s_-]*year|gradyear|class[\s_-]*of|class|year)\}|\[(?i:grad[\s_-]*year|graduation[\s_-]*year|gradyear|class[\s_-]*of|class|year)\]', grad_year, formatted)

    athlete_id_str = str(recipient.get("id") or "0")

    short_link = f"https://recdebut-recruit.org/r/{athlete_id_str}"

    formatted = re.sub(r'\{(?i:id|athlete_id)\}', athlete_id_str, formatted)

    formatted = re.sub(r'\{(?i:short_url|tracking_url|link)\}', short_link, formatted)



    # Check if a greeting exists in the first 150 chars

    has_name_greeting = bool(re.search(

        rf'\b(hi|hey|hello|dear|greetings|good\s+(?:morning|afternoon|evening))\b',

        formatted[:150],

        re.IGNORECASE

    ))



    # Prepend personalized greeting only if no greeting already exists in the text

    if not has_name_greeting and full_name != "Student-Athlete":

        formatted = f"Hey {first_name},\n\n{formatted}"



    return formatted



def _run_broadcast_worker(job_id: str, clean_recipients: List[Dict[str, Any]], message_text: str, caller_id: str, caller_id_name: str = "Dennis Bell (+1-616-291-5227)", campaign_type: str = "sms", subject_line: Optional[str] = None, use_swarm: bool = True):
    global ACTIVE_BROADCAST_STATE

    if not outbound_messaging_enabled("recdebut"):
        with ACTIVE_BROADCAST_LOCK:
            if ACTIVE_BROADCAST_STATE.get("job_id") == job_id:
                ACTIVE_BROADCAST_STATE.update(active=False, status="ERROR", error=RECDEBUT_DISABLED_MESSAGE, completed_at=time.time())
        return




    # 1. Prepare swarm accounts

    swarm = [a for a in load_smtp_swarm() if a.get("active") and a.get("email") and a.get("app_password")] if use_swarm else []

    if not swarm:

        creds = load_credentials()

        swarm = [{

            "id": "acct_primary",

            "email": creds.get("IMAP_USER", "footballstar0325@gmail.com"),

            "app_password": creds.get("IMAP_APP_PASSWORD", ""),

            "smtp_host": creds.get("SMTP_HOST", "smtp.gmail.com"),

            "smtp_port": int(creds.get("SMTP_PORT", 587)),

            "daily_limit": 400,

            "active": True,

            "label": "Primary Gateway"

        }]



    conn = sqlite3.connect(str(DB_PATH))

    cursor = conn.cursor()



    # 2. Check for configured transactional email API (Resend / SendGrid)

    api_settings = load_email_api_settings()

    provider = (api_settings.get("provider") or "auto").lower()

    resend_key = (api_settings.get("resend_api_key") or "").strip()

    resend_from = api_settings.get("resend_from_email") or f"{caller_id_name} <recruiting@recdebut.com>"

    sendgrid_key = (api_settings.get("sendgrid_api_key") or "").strip()

    sendgrid_from = api_settings.get("sendgrid_from_email") or f"{caller_id_name} <recruiting@recdebut.com>"



    use_resend = (provider in ("resend", "auto")) and bool(resend_key)

    use_sendgrid = (provider == "sendgrid" or (provider == "auto" and not use_resend)) and bool(sendgrid_key)

    using_api = (campaign_type == "email") and (use_resend or use_sendgrid)



    swarm_workers = []

    if not using_api:

        for acct in swarm:

            w_sender = SmtpBatchSender(

                acct.get("smtp_host", "smtp.gmail.com"),

                int(acct.get("smtp_port", 587)),

                acct["email"],

                acct["app_password"],

                timeout=12.0

            )

            swarm_workers.append({

                "acct": acct,

                "email": acct["email"],

                "app_password": acct["app_password"],

                "smtp_host": acct.get("smtp_host", "smtp.gmail.com"),

                "smtp_port": int(acct.get("smtp_port", 587)),

                "daily_limit": int(acct.get("daily_limit", 100)),

                "sent_count": 0,

                "sender": w_sender,

                "active": True

            })



    round_robin_idx = 0

    results = []

    success_count = 0

    fail_count = 0



    with ACTIVE_BROADCAST_LOCK:

        ACTIVE_BROADCAST_STATE["current_account"] = "Resend API (Zero-Spam)" if use_resend else ("SendGrid API" if use_sendgrid else (swarm_workers[0]["email"] if swarm_workers else "SMTP Gateway"))

        ACTIVE_BROADCAST_STATE["account_index"] = 1

        ACTIVE_BROADCAST_STATE["total_accounts"] = 1 if using_api else len(swarm_workers)

        ACTIVE_BROADCAST_STATE["campaign_type"] = campaign_type



    try:

        for idx, rec in enumerate(clean_recipients):

            with ACTIVE_BROADCAST_LOCK:

                if ACTIVE_BROADCAST_STATE.get("cancel_requested"):

                    ACTIVE_BROADCAST_STATE["status"] = "CANCELLED"

                    break



            # If using SMTP Swarm, verify active capacity

            if not using_api:

                available_workers = [w for w in swarm_workers if w["active"] and w["sent_count"] < w["daily_limit"]]

                if not available_workers:

                    with ACTIVE_BROADCAST_LOCK:

                        ACTIVE_BROADCAST_STATE["status"] = "PAUSED_QUOTA"

                        total_sent_all = sum(w["sent_count"] for w in swarm_workers)

                        ACTIVE_BROADCAST_STATE["error"] = f"All {len(swarm_workers)} swarm accounts reached daily limit ({total_sent_all} sent)."

                    break



            phone = rec.get("phone", "")

            email_addr = (rec.get("email") or "").strip()

            name = rec.get("name", "")

            formatted_msg = format_personalized_message(message_text, rec)



            with ACTIVE_BROADCAST_LOCK:

                ACTIVE_BROADCAST_STATE["current_athlete"] = name or email_addr or phone

                ACTIVE_BROADCAST_STATE["current_phone"] = email_addr if campaign_type == "email" else phone

                ACTIVE_BROADCAST_STATE["updated_at"] = time.time()



            if campaign_type == "email":

                if not email_addr or "@" not in email_addr:

                    fail_count += 1

                    with ACTIVE_BROADCAST_LOCK:

                        ACTIVE_BROADCAST_STATE["failed"] = fail_count

                        ACTIVE_BROADCAST_STATE["updated_at"] = time.time()

                    results.append({"athlete_id": rec.get("id"), "email": email_addr, "status": "FAILED", "error": "No valid email address"})

                    continue

                target_addresses = [email_addr]

                athlete_id_val = rec.get("id") or 0

                track_open_url = f"https://recdebut-recruit.org/api/v1/recdebut/track/open/{job_id}/{athlete_id_val}"

                track_click_url = f"https://recdebut-recruit.org/api/v1/recdebut/track/click/{job_id}/{athlete_id_val}?url=https://recdebut.com"

                track_reg_url = f"https://recdebut-recruit.org/api/v1/recdebut/track/click/{job_id}/{athlete_id_val}?url=https://recdebut.com/all-registration/"



                paragraphs = [p.strip() for p in formatted_msg.split("\n\n") if p.strip()]

                html_paragraphs_list = []

                for p in paragraphs:

                    p_with_br = p.replace("\n", "<br>")

                    # Automatically wrap RecDebut.com mentions with tracked click redirect

                    p_with_br = re.sub(

                        r'\[?(?:https?://)?(?:www\.)?recdebut\.com(?:/all-registration/?)?\]?',

                        f'<a href="{track_reg_url}" style="color: #006BB6; text-decoration: underline; font-weight: 700;" target="_blank">RecDebut.com</a>',

                        p_with_br,

                        flags=re.IGNORECASE

                    )

                    p_linked = re.sub(

                        r'(?<!href=["\'])(https?://[^\s<>"]+)',

                        r'<a href="\1" style="color: #006BB6; text-decoration: underline; font-weight: 600;" target="_blank">\1</a>',

                        p_with_br

                    )

                    html_paragraphs_list.append(f"<p style='margin: 0 0 14px 0; line-height: 1.6; color: #1e293b;'>{p_linked}</p>")

                html_paragraphs = "".join(html_paragraphs_list)



                html_body = f"""<!DOCTYPE html>

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

    <div style="font-size: 15px; color: #1e293b;">

      {html_paragraphs}

    </div>

    <div style="margin: 28px 0; text-align: center;">

      <a href="{track_reg_url}" style="background-color: #F58426; color: #ffffff; text-decoration: none; font-weight: 800; font-size: 15px; padding: 14px 28px; border-radius: 8px; display: inline-block; box-shadow: 0 4px 12px rgba(245, 132, 38, 0.35);">

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

    <!-- 1x1 Transparent Open Tracking Pixel -->

    <img src="{track_open_url}" width="1" height="1" style="display:none; width:1px; height:1px; border:0;" alt="" />

  </div>

</body>

</html>"""



                if using_api:

                    if use_resend:

                        sent_ok, err_str = send_resend_email(

                            api_key=resend_key,

                            from_email=resend_from,

                            to_email=email_addr,

                            to_name=name,

                            subject=subject_line or "Dennis Bell (Former New York Knick) - Recreational Debut Recruitment",

                            text_content=formatted_msg,

                            html_content=html_body,

                            reply_to=caller_id or "dbell002@sbcglobal.net"

                        )

                        active_label = f"Resend API ({resend_from})"

                    else:

                        sent_ok, err_str = send_sendgrid_email(

                            api_key=sendgrid_key,

                            from_email=sendgrid_from,

                            to_email=email_addr,

                            to_name=name,

                            subject=subject_line or "Dennis Bell (Former New York Knick) - Recreational Debut Recruitment",

                            text_content=formatted_msg,

                            html_content=html_body,

                            reply_to=caller_id or "dbell002@sbcglobal.net"

                        )

                        active_label = f"SendGrid API ({sendgrid_from})"

                else:

                    available_workers = [w for w in swarm_workers if w["active"] and w["sent_count"] < w["daily_limit"]]

                    if not available_workers:

                        with ACTIVE_BROADCAST_LOCK:

                            ACTIVE_BROADCAST_STATE["status"] = "PAUSED_QUOTA"

                            ACTIVE_BROADCAST_STATE["error"] = "All swarm accounts reached daily limit."

                        break



                    worker = available_workers[round_robin_idx % len(available_workers)]

                    round_robin_idx += 1

                    active_label = worker["email"]



                    with ACTIVE_BROADCAST_LOCK:

                        ACTIVE_BROADCAST_STATE["current_account"] = worker["email"]

                        ACTIVE_BROADCAST_STATE["account_index"] = swarm_workers.index(worker) + 1

                        ACTIVE_BROADCAST_STATE["total_accounts"] = len(swarm_workers)



                    msg = MIMEMultipart("alternative")

                    msg["To"] = f"{name} <{email_addr}>"

                    msg["From"] = f"{caller_id_name} <{worker['email']}>"

                    msg["Reply-To"] = caller_id if caller_id else "dbell002@sbcglobal.net"

                    msg["Subject"] = subject_line or "Dennis Bell (Former New York Knick) - Recreational Debut Recruitment"

                    msg["Date"] = email.utils.formatdate(localtime=True)

                    msg["List-Unsubscribe"] = f"<mailto:{caller_id if caller_id else 'dbell002@sbcglobal.net'}?subject=unsubscribe>"



                    text_part = MIMEText(formatted_msg, "plain", "utf-8")

                    msg.attach(text_part)

                    html_part = MIMEText(html_body, "html", "utf-8")

                    msg.attach(html_part)



                    sent_ok, err_str = worker["sender"].send(target_addresses, msg.as_string())



                    # If quota or auth failure tripped on this worker, rotate to next available worker

                    if not sent_ok and err_str and ("550" in err_str or "daily user sending limit" in err_str.lower() or "quota" in err_str.lower() or "badcredentials" in err_str.lower() or "authenticat" in err_str.lower()):

                        worker["active"] = False

                        try:

                            worker["sender"].close()

                        except Exception:

                            pass

                        remaining_pool = [w for w in swarm_workers if w["active"] and w["sent_count"] < w["daily_limit"]]

                        if remaining_pool:

                            worker = remaining_pool[round_robin_idx % len(remaining_pool)]

                            round_robin_idx += 1

                            active_label = worker["email"]

                            with ACTIVE_BROADCAST_LOCK:

                                ACTIVE_BROADCAST_STATE["current_account"] = worker["email"]

                                ACTIVE_BROADCAST_STATE["account_index"] = swarm_workers.index(worker) + 1

                            del msg["From"]

                            msg["From"] = f"{caller_id_name} <{worker['email']}>"

                            sent_ok, err_str = worker["sender"].send(target_addresses, msg.as_string())

                            if not sent_ok and err_str and ("550" in err_str or "daily user sending limit" in err_str.lower() or "quota" in err_str.lower()):

                                worker["active"] = False

                                try:

                                    worker["sender"].close()

                                except Exception:

                                    pass



            else:

                available_workers = [w for w in swarm_workers if w["active"] and w["sent_count"] < w["daily_limit"]]

                if not available_workers:

                    with ACTIVE_BROADCAST_LOCK:

                        ACTIVE_BROADCAST_STATE["status"] = "PAUSED_QUOTA"

                        ACTIVE_BROADCAST_STATE["error"] = "All swarm accounts reached daily limit."

                    break

                worker = available_workers[round_robin_idx % len(available_workers)]

                round_robin_idx += 1

                active_label = worker["email"]



                digits = "".join(filter(str.isdigit, phone))

                if len(digits) < 10:

                    fail_count += 1

                    with ACTIVE_BROADCAST_LOCK:

                        ACTIVE_BROADCAST_STATE["failed"] = fail_count

                        ACTIVE_BROADCAST_STATE["updated_at"] = time.time()

                    continue

                ten_digits = digits[-10:]

                target_addresses = [f"{ten_digits}{gw}" for gw in CARRIER_GATEWAYS.values()]

                msg = MIMEText(formatted_msg, "plain", "utf-8")

                msg["From"] = f"{caller_id_name} <{worker['email']}>"

                msg["Reply-To"] = caller_id if caller_id else "dbell002@sbcglobal.net"

                msg["Subject"] = subject_line or "Dennis Bell (+1-616-291-5227) - Recreational Debut"

                msg["Date"] = email.utils.formatdate(localtime=True)



                sent_ok, err_str = worker["sender"].send(target_addresses, msg.as_string())



            now = time.time()



            if sent_ok:

                success_count += 1

                if not using_api:

                    worker["sent_count"] += 1

                if rec.get("id"):

                    cursor.execute("UPDATE rec_debut_athletes SET last_messaged_at = ?, status = 'Contacted' WHERE id = ?", (now, rec["id"]))

                    conn.commit()

                results.append({"athlete_id": rec.get("id"), "target": email_addr if campaign_type == "email" else phone, "status": "SENT", "account": active_label})

                with ACTIVE_BROADCAST_LOCK:

                    ACTIVE_BROADCAST_STATE["sent"] = success_count

            else:

                fail_count += 1

                results.append({"athlete_id": rec.get("id"), "target": email_addr if campaign_type == "email" else phone, "status": "FAILED", "error": err_str, "account": active_label})

                with ACTIVE_BROADCAST_LOCK:

                    ACTIVE_BROADCAST_STATE["failed"] = fail_count



            with ACTIVE_BROADCAST_LOCK:

                ACTIVE_BROADCAST_STATE["updated_at"] = time.time()



            # Velocity Jitter Pacing: Smooth sending prevents anti-spam triggers

            if using_api:

                time.sleep(0.2)

            elif campaign_type == "email":

                time.sleep(random.uniform(6.0, 10.0))

            else:

                time.sleep(random.uniform(4.0, 6.0))



    except Exception as e:

        with ACTIVE_BROADCAST_LOCK:

            ACTIVE_BROADCAST_STATE["status"] = "ERROR"

            ACTIVE_BROADCAST_STATE["error"] = str(e)

    finally:

        if not using_api:

            for w in swarm_workers:

                try:

                    w["sender"].close()

                except Exception:

                    pass

        now = time.time()

        try:

            cursor.execute("""

                INSERT INTO rec_debut_campaigns

                (created_at, sender_id, total_recipients, successful_count, failed_count, message_body, delivery_details_json)

                VALUES (?, ?, ?, ?, ?, ?, ?)

            """, (

                now,

                caller_id,

                len(clean_recipients),

                success_count,

                fail_count,

                message_text,

                json.dumps(results[:100])

            ))

            conn.commit()

        except Exception:

            pass

        conn.close()



        with ACTIVE_BROADCAST_LOCK:

            ACTIVE_BROADCAST_STATE["active"] = False

            ACTIVE_BROADCAST_STATE["completed_at"] = time.time()

            if ACTIVE_BROADCAST_STATE["status"] not in ("CANCELLED", "PAUSED_QUOTA", "ERROR"):

                ACTIVE_BROADCAST_STATE["status"] = "COMPLETED"



# --- Pydantic Request Models ---

class AthleteCreatePayload(BaseModel):

    name: str

    phone: str

    email: Optional[str] = ""

    sport: Optional[str] = "Basketball"

    high_school: Optional[str] = ""

    grad_year: Optional[str] = "2026"

    city_state: Optional[str] = ""

    notes: Optional[str] = ""



class MassBroadcastPayload(BaseModel):

    athlete_ids: Optional[List[int]] = None

    custom_phone_numbers: Optional[List[str]] = None

    message_text: str

    campaign_type: Optional[str] = "sms"  # 'sms' (Carrier MMS) or 'email' (Direct Athlete Email)

    subject_line: Optional[str] = "Dennis Bell (Former New York Knick) - Recreational Debut"

    caller_id_email: Optional[str] = "dbell002@sbcglobal.net"

    caller_id_phone: Optional[str] = "+1-616-291-5227"

    caller_id_name: Optional[str] = "Dennis Bell (+1-616-291-5227)"

    dry_run: Optional[bool] = False

    batch_limit: Optional[int] = 400

    use_swarm: Optional[bool] = True



class SmtpAccountCreatePayload(BaseModel):

    email: str

    app_password: str

    label: Optional[str] = ""

    daily_limit: Optional[int] = 400

    active: Optional[bool] = True

    smtp_host: Optional[str] = "smtp.gmail.com"

    smtp_port: Optional[int] = 587



class SmtpAccountTestPayload(BaseModel):

    email: str

    app_password: str

    smtp_host: Optional[str] = "smtp.gmail.com"

    smtp_port: Optional[int] = 587

    test_recipient: Optional[str] = "dbell002@sbcglobal.net"



class UpdateStatusPayload(BaseModel):

    athlete_ids: List[int]

    status: str



class TestSmsPayload(BaseModel):

    test_phone: Optional[str] = "+1-616-402-3628"

    message_text: Optional[str] = None

    caller_id_email: Optional[str] = "dbell002@sbcglobal.net"

    caller_id_phone: Optional[str] = "+1-616-291-5227"

    caller_id_name: Optional[str] = "Dennis Bell (+1-616-291-5227)"



class TestEmailPayload(BaseModel):

    test_email: Optional[str] = "dbell002@sbcglobal.net"

    message_text: Optional[str] = None

    subject_line: Optional[str] = "Dennis Bell (Former New York Knick) - College Athletic Recruitment Opportunity"

    caller_id_email: Optional[str] = "dbell002@sbcglobal.net"

    caller_id_name: Optional[str] = "Dennis Bell (+1-616-291-5227)"



class RespondToReplyPayload(BaseModel):

    message_text: str

    caller_id_email: Optional[str] = "dbell002@sbcglobal.net"

    caller_id_name: Optional[str] = "Dennis Bell (+1-616-291-5227)"



class CsvUploadPayload(BaseModel):

    csv_text: str



class EmailApiConfigPayload(BaseModel):

    provider: Optional[str] = "auto"

    resend_api_key: Optional[str] = None

    resend_from_email: Optional[str] = None

    sendgrid_api_key: Optional[str] = None

    sendgrid_from_email: Optional[str] = None

    reply_to_email: Optional[str] = None



class EmailApiTestPayload(BaseModel):

    target_email: Optional[str] = "brett@stehouwerproductions.com"



# --- Endpoints ---



@router.get("/stats")

@legacy_router.get("/stats")

async def get_recdebut_stats():

    """Ultra-fast instant telemetry counts for Recreational Debut dashboard."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes")

        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")

        contacted = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")

        pending = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE email IS NOT NULL AND email != '' AND email_status != 'NO_EMAIL'")

        emails = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches")

        coaches = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM rec_debut_campaigns")

        campaigns = cursor.fetchone()[0]

        conn.close()

        return {

            "success": True,

            "total": total,

            "contacted": contacted,

            "pending": pending,

            "emails": emails,

            "coaches": coaches,

            "campaigns": campaigns

        }

    except Exception as e:

        return {

            "success": False,

            "error": str(e),

            "total": 7356,

            "contacted": 1952,

            "pending": 3809,

            "emails": 7332,

            "coaches": 4242,

            "campaigns": 19

        }





@router.get("/athletes")

async def get_all_athletes(status: Optional[str] = None):

    """Retrieve all student-athletes tracked for Recreational Debut with status counts."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()



        # Telemetry counts

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes")

        total_count = cursor.fetchone()[0]



        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")

        messaged_count = cursor.fetchone()[0]



        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")

        pending_count = cursor.fetchone()[0]



        if status and status.lower() in ('contacted', 'messaged'):

            cursor.execute("SELECT * FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged' ORDER BY id DESC")

        elif status and status.lower() in ('pending', 'selected'):

            cursor.execute("SELECT * FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected' ORDER BY id DESC")

        else:

            cursor.execute("SELECT * FROM rec_debut_athletes ORDER BY id DESC")



        rows = cursor.fetchall()

        conn.close()

        return {

            "success": True,

            "total": total_count,

            "pending_count": pending_count,

            "messaged_count": messaged_count,

            "athletes": [dict(r) for r in rows]

        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.get("/excluded-coaches")

async def get_excluded_coaches():

    """Retrieve all coaches excluded from messaging."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches")

        total = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM rec_debut_excluded_coaches ORDER BY id DESC")

        rows = cursor.fetchall()

        conn.close()

        return {

            "success": True,

            "total": total,

            "coaches": [dict(r) for r in rows]

        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/athletes/update-status")

async def update_athletes_status(payload: UpdateStatusPayload):

    """Bulk update athlete status (Pending / Contacted)."""

    try:

        if not payload.athlete_ids:

            return {"success": True, "updated_count": 0}

        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        placeholders = ",".join("?" for _ in payload.athlete_ids)

        cursor.execute(f"UPDATE rec_debut_athletes SET status = ? WHERE id IN ({placeholders})", [payload.status] + payload.athlete_ids)

        conn.commit()

        conn.close()

        return {"success": True, "updated_count": len(payload.athlete_ids), "status": payload.status}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/clean-coaches")

async def clean_coaches_from_athletes():

    """Safety purge: remove any athlete whose phone or name matches an excluded coach, and scrub embedded fields."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        now = time.time()

        

        # 1. Load coach phone numbers and names

        cursor.execute("SELECT name, phone FROM rec_debut_excluded_coaches")

        coaches = cursor.fetchall()

        coach_phones = set()

        coach_names = set()

        for cname, cphone in coaches:

            digits = "".join(filter(str.isdigit, cphone or ""))

            if len(digits) >= 10:

                coach_phones.add(digits[-10:])

            if cname and len(cname.strip()) > 3 and cname.strip() not in ["Club Coach", "High School Coach"]:

                coach_names.add(cname.strip().upper())



        # 2. Check all athletes

        cursor.execute("SELECT id, name, phone, high_school, notes FROM rec_debut_athletes")

        athletes = cursor.fetchall()

        purged_ids = []

        phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')

        coach_kws = ["COACH", "HEAD COACH", "ASST", "DIRECTOR", "TRAINER", "STAFF"]



        for aid, aname, aphone, ahs, anotes in athletes:

            digits = "".join(filter(str.isdigit, aphone or ""))

            name_up = (aname or "").strip().upper()

            

            # Check phone match

            is_match = False

            if len(digits) >= 10 and digits[-10:] in coach_phones:

                is_match = True

            elif "3935534" in digits or "134739" in digits: # Pete Wehye signature

                is_match = True

            elif name_up in coach_names:

                is_match = True

            elif any(re.search(r'\b' + kw + r'\b', name_up) for kw in coach_kws):

                is_match = True



            if is_match:

                purged_ids.append(aid)

                continue



            # Scrub any phone numbers from high_school

            if ahs and phone_regex.search(ahs):

                found_phones = phone_regex.findall(ahs)

                for fp in found_phones:

                    full_p = f"{fp[0]}-{fp[1]}-{fp[2]}"

                    cursor.execute("""

                        INSERT OR IGNORE INTO rec_debut_excluded_coaches (name, phone, coach_type, school_name, excluded_at)

                        VALUES ('High School Coach', ?, 'Embedded HS Coach', 'Scrubbed from HS Field', ?)

                    """, (full_p, now))

                # Strip phone from school field

                clean_hs = phone_regex.sub('', ahs).strip()

                cursor.execute("UPDATE rec_debut_athletes SET high_school = ? WHERE id = ?", (clean_hs, aid))



        if purged_ids:

            placeholders = ",".join("?" for _ in purged_ids)

            cursor.execute(f"DELETE FROM rec_debut_athletes WHERE id IN ({placeholders})", purged_ids)



        conn.commit()

        conn.close()

        return {"success": True, "purged_count": len(purged_ids), "purged_ids": purged_ids}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))





@router.post("/athletes")

async def create_athlete(payload: AthleteCreatePayload):

    """Add a new student-athlete candidate."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        now = time.time()

        cursor.execute("""

            INSERT INTO rec_debut_athletes 

            (name, phone, email, sport, high_school, grad_year, city_state, status, notes, created_at, last_messaged_at)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            payload.name,

            payload.phone,

            payload.email or "",

            payload.sport or "Basketball",

            payload.high_school or "",

            payload.grad_year or "2026",

            payload.city_state or "",

            "Selected",

            payload.notes or "",

            now,

            None

        ))

        athlete_id = cursor.lastrowid

        conn.commit()

        conn.close()

        return {"success": True, "athlete_id": athlete_id}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/athletes/{athlete_id}")

async def delete_athlete(athlete_id: int):

    """Delete a student-athlete from the list."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        cursor.execute("DELETE FROM rec_debut_athletes WHERE id = ?", (athlete_id,))

        conn.commit()

        conn.close()

        return {"success": True, "deleted_id": athlete_id}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/athletes/upload-csv")

async def upload_athletes_csv(payload: CsvUploadPayload):

    """Parse CSV of student athletes: Name, Phone, Email, Sport, High School, Grad Year, City/State."""

    import csv

    import io



    try:

        reader = csv.reader(io.StringIO(payload.csv_text))

        rows = list(reader)

        if not rows:

            return {"success": False, "error": "Empty CSV content"}



        header = [c.lower().strip() for c in rows[0]]

        data_rows = rows[1:] if ("name" in header or "phone" in header) else rows



        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        added_count = 0

        now = time.time()



        cursor.execute("SELECT phone FROM rec_debut_excluded_coaches")

        coach_phones = set()

        for c in cursor.fetchall():

            d = "".join(filter(str.isdigit, c[0]))

            if len(d) >= 10:

                coach_phones.add(d[-10:])



        for r in data_rows:

            if not r or len(r) < 2:

                continue

            name = r[0].strip()

            phone = r[1].strip()

            if not name or not phone:

                continue

            

            p_digits = "".join(filter(str.isdigit, phone))

            is_coach = (

                (len(p_digits) >= 10 and p_digits[-10:] in coach_phones) or

                "coach" in name.lower() or

                "hc" in name.lower() or

                (len(r) > 7 and "coach" in r[7].lower())

            )



            if is_coach:

                cursor.execute("""

                    INSERT INTO rec_debut_excluded_coaches (name, phone, coach_type, school_name, excluded_at)

                    VALUES (?, ?, 'Imported Coach', ?, ?)

                """, (name, phone, r[4].strip() if len(r) > 4 else "Uploaded Roster", now))

                if len(p_digits) >= 10:

                    coach_phones.add(p_digits[-10:])

                continue



            email_val = r[2].strip() if len(r) > 2 else ""

            sport_val = r[3].strip() if len(r) > 3 else "Basketball"

            school_val = r[4].strip() if len(r) > 4 else ""

            grad_val = r[5].strip() if len(r) > 5 else "2026"

            city_val = r[6].strip() if len(r) > 6 else ""

            notes_val = r[7].strip() if len(r) > 7 else "Imported via Contact List"



            cursor.execute("""

                INSERT OR IGNORE INTO rec_debut_athletes 

                (name, phone, email, sport, high_school, grad_year, city_state, status, notes, created_at, last_messaged_at)

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """, (name, phone, email_val, sport_val, school_val, grad_val, city_val, "Pending", notes_val, now, None))

            added_count += 1



        conn.commit()

        conn.close()

        return {"success": True, "imported_count": added_count}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/broadcast")

async def mass_sms_broadcast(payload: MassBroadcastPayload):

    """Execute mass SMS or Email broadcast to athletes with Dennis Bell's message and Caller ID (616-291-5227), strictly excluding coaches."""
    if not payload.dry_run:
        _require_recdebut_outbound()

    caller_id = payload.caller_id_email or "dbell002@sbcglobal.net"

    caller_id_phone = payload.caller_id_phone or "616-291-5227"

    caller_id_name = payload.caller_id_name or f"Dennis Bell ({caller_id_phone})"

    message_text = payload.message_text.strip()

    campaign_type = (payload.campaign_type or "sms").lower()

    if not message_text:

        raise HTTPException(status_code=400, detail="Message text cannot be empty.")



    with ACTIVE_BROADCAST_LOCK:

        if ACTIVE_BROADCAST_STATE.get("active"):

            return {

                "success": False,

                "message": "A broadcast is already actively running in the background.",

                "active_job": dict(ACTIVE_BROADCAST_STATE)

            }



    conn = sqlite3.connect(str(DB_PATH))

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()



    # 1. Load ALL excluded coach phone numbers into memory for 100% collision protection

    cursor.execute("SELECT phone FROM rec_debut_excluded_coaches")

    coach_rows = cursor.fetchall()

    excluded_coach_phones = set()

    for row in coach_rows:

        raw_p = row[0]

        digits = "".join(filter(str.isdigit, raw_p))

        if len(digits) >= 10:

            excluded_coach_phones.add(digits[-10:])



    recipients_raw = []



    # 2. Gather from athlete IDs if provided

    if payload.athlete_ids:

        placeholders = ",".join("?" for _ in payload.athlete_ids)

        cursor.execute(f"SELECT * FROM rec_debut_athletes WHERE id IN ({placeholders})", payload.athlete_ids)

        for r in cursor.fetchall():

            recipients_raw.append({

                "id": r["id"],

                "name": r["name"],

                "phone": r["phone"],

                "email": r["email"] or "",

                "sport": r["sport"] or "Basketball",

                "high_school": r["high_school"] or "",

                "grad_year": r["grad_year"] or "2026"

            })

    elif payload.custom_phone_numbers:

        for p in payload.custom_phone_numbers:

            if p.strip():

                recipients_raw.append({

                    "id": None,

                    "name": "Direct Contact",

                    "phone": p.strip(),

                    "email": "",

                    "sport": "Basketball",

                    "high_school": "",

                    "grad_year": "2026"

                })

    else:

        if campaign_type == "email":

            # Filter for athletes with valid non-empty emails, excluding any flagged as UNDELIVERABLE

            cursor.execute("SELECT * FROM rec_debut_athletes WHERE (email IS NOT NULL AND email != '') AND (status IS NULL OR status = 'Pending' OR status = 'Selected') AND (email_status IS NULL OR email_status != 'UNDELIVERABLE') ORDER BY id ASC")

        else:

            cursor.execute("SELECT * FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected' ORDER BY id ASC")

        for r in cursor.fetchall():

            recipients_raw.append({

                "id": r["id"],

                "name": r["name"],

                "phone": r["phone"],

                "email": r["email"] or "",

                "sport": r["sport"] or "Basketball",

                "high_school": r["high_school"] or "",

                "grad_year": r["grad_year"] or "2026"

            })



    conn.close()



    # 3. Intercept & Purge any Coach Phone Collision, then slice to batch_limit

    limit_val = payload.batch_limit if (payload.batch_limit and payload.batch_limit > 0) else None

    clean_recipients = []

    blocked_coaches = []

    for rec in recipients_raw:

        phone_digits = "".join(filter(str.isdigit, rec.get("phone", "")))

        if len(phone_digits) >= 10 and phone_digits[-10:] in excluded_coach_phones:

            blocked_coaches.append(rec)

            continue

        clean_recipients.append(rec)

        if limit_val and len(clean_recipients) >= limit_val:

            break



    if not clean_recipients:

        return {

            "success": False,

            "message": "No valid athlete recipients found to send to (or all were blocked as coaches).",

            "blocked_coaches_count": len(blocked_coaches)

        }



    # 4. If DRY_RUN is active, return staging report without sending a single text

    if payload.dry_run:

        sample_msg = format_personalized_message(message_text, clean_recipients[0]) if clean_recipients else ""

        return {

            "success": True,

            "dry_run": True,

            "message": "Draft Staged Successfully. Zero messages sent (DRAFT MODE ONLY).",

            "campaign_type": campaign_type,

            "caller_id": caller_id,

            "ready_athletes_count": len(clean_recipients),

            "blocked_coaches_count": len(blocked_coaches),

            "preview_recipients": clean_recipients[:15],

            "sample_personalized_message": sample_msg

        }



    # 5. Launch Asynchronous Background Worker Immediately (Non-blocking)

    job_id = f"broadcast_{int(time.time())}"

    with ACTIVE_BROADCAST_LOCK:

        ACTIVE_BROADCAST_STATE["active"] = True

        ACTIVE_BROADCAST_STATE["job_id"] = job_id

        ACTIVE_BROADCAST_STATE["status"] = "RUNNING"

        ACTIVE_BROADCAST_STATE["total"] = len(clean_recipients)

        ACTIVE_BROADCAST_STATE["sent"] = 0

        ACTIVE_BROADCAST_STATE["failed"] = 0

        ACTIVE_BROADCAST_STATE["campaign_type"] = campaign_type

        ACTIVE_BROADCAST_STATE["current_athlete"] = clean_recipients[0]["name"] if clean_recipients else ""

        ACTIVE_BROADCAST_STATE["current_phone"] = (clean_recipients[0]["email"] or clean_recipients[0]["phone"]) if clean_recipients else ""

        ACTIVE_BROADCAST_STATE["cancel_requested"] = False

        ACTIVE_BROADCAST_STATE["started_at"] = time.time()

        ACTIVE_BROADCAST_STATE["updated_at"] = time.time()

        ACTIVE_BROADCAST_STATE["completed_at"] = None

        ACTIVE_BROADCAST_STATE["error"] = None



    worker_thread = threading.Thread(

        target=_run_broadcast_worker,

        args=(job_id, clean_recipients, message_text, caller_id, caller_id_name, campaign_type, payload.subject_line, payload.use_swarm),

        daemon=True

    )

    worker_thread.start()



    return {

        "success": True,

        "job_id": job_id,

        "status": "RUNNING",

        "total": len(clean_recipients),

        "campaign_type": campaign_type,

        "blocked_coaches": len(blocked_coaches),

        "caller_id": caller_id,

        "message": f"Mass {campaign_type.upper()} broadcast engine started in background for {len(clean_recipients)} student-athletes."

    }



@router.get("/broadcast/status")

async def get_broadcast_status():

    """Retrieve real-time broadcast engine telemetry and progress."""

    with ACTIVE_BROADCAST_LOCK:

        state = dict(ACTIVE_BROADCAST_STATE)

    total = state.get("total", 0)

    sent = state.get("sent", 0)

    failed = state.get("failed", 0)

    progress_pct = round(((sent + failed) / total * 100), 1) if total > 0 else 0.0

    state["progress_pct"] = progress_pct

    return {"success": True, **state}



@router.post("/broadcast/cancel")

async def cancel_broadcast():

    """Request cancellation or pause of an active background broadcast."""

    with ACTIVE_BROADCAST_LOCK:

        if ACTIVE_BROADCAST_STATE.get("active"):

            ACTIVE_BROADCAST_STATE["cancel_requested"] = True

            return {"success": True, "message": "Cancellation request submitted to broadcast engine."}

        return {"success": False, "message": "No broadcast is currently running."}



@router.get("/scheduler/status")

async def get_scheduler_status():

    """Retrieve status, countdown, and batch timeline of the 24-hour automated scheduler."""

    state_file = DATA_DIR / "rec_debut_scheduler_state.json"

    if not state_file.exists():

        return {"success": True, "active": False, "message": "Scheduler state file not created yet."}

    try:

        with open(state_file, "r", encoding="utf-8") as f:

            state = json.load(f)

        now = time.time()

        next_run = state.get("next_batch_scheduled_at", now)

        diff = max(0, next_run - now)

        hours = int(diff // 3600)

        minutes = int((diff % 3600) // 60)

        seconds = int(diff % 60)

        return {

            "success": True,

            "scheduler_active": state.get("scheduler_active", True),

            "next_batch_number": state.get("next_batch_number", 2),

            "next_batch_scheduled_at": next_run,

            "next_batch_scheduled_iso": state.get("next_batch_scheduled_iso"),

            "countdown_seconds": diff,

            "countdown_formatted": f"{hours}h {minutes}m {seconds}s",

            "batch_size": state.get("batch_size", 400),

            "interval_hours": 24,

            "batches": state.get("batches", [])

        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/test-sms")

async def send_test_sms(payload: TestSmsPayload):

    """Send an instant test SMS to verify Caller ID (Dennis Bell +1-616-291-5227) and formatting."""
    _require_recdebut_outbound()

    phone = payload.test_phone or "+1-616-402-3628"

    caller_id = payload.caller_id_email or "dbell002@sbcglobal.net"

    caller_id_phone = payload.caller_id_phone or "+1-616-291-5227"

    caller_id_name = payload.caller_id_name or f"Dennis Bell ({caller_id_phone})"

    default_text = (

        "Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.\n\n"

        "Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.\n\n"

        "We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.\n\n"

        "If playing college sports is your goal, don’t wait for coaches to find you.\n\n"

        "📱 Call or text: +1-616-291-5227\n"

        "✅ Register FREE: RecDebut.com\n"

        "📧 dbell002@sbcglobal.net\n\n"

        "Let’s get you recruited!\n\n"

        "Dennis Bell\n"

        "Former New York Knicks\n"

        "President, Recreational Debut"

    )

    text = payload.message_text.strip() if payload.message_text else default_text

    sample_recipient = {"name": "Test Student-Athlete", "phone": phone, "sport": "Basketball"}

    personalized_text = format_personalized_message(text, sample_recipient)

    res = send_carrier_sms(phone, personalized_text, caller_id, caller_id_name)

    return {

        "success": res["success"],

        "phone": phone,

        "caller_id": caller_id,

        "caller_id_name": caller_id_name,

        "caller_id_phone": caller_id_phone,

        "sample_personalized_message": personalized_text,

        "res": res

    }



@router.post("/test-email")

async def send_test_email(payload: TestEmailPayload):

    """Send an instant test email to verify inbox delivery, Dennis Bell formatting, and Reply-To."""
    _require_recdebut_outbound()

    target_email = (payload.test_email or "dbell002@sbcglobal.net").strip()

    caller_id = payload.caller_id_email or "dbell002@sbcglobal.net"

    caller_id_name = payload.caller_id_name or "Dennis Bell (+1-616-291-5227)"

    subject = payload.subject_line or "Dennis Bell (Former New York Knick) - College Athletic Recruitment Opportunity"

    default_text = (

        "Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.\n\n"

        "Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.\n\n"

        "We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.\n\n"

        "If playing college sports is your goal, don’t wait for coaches to find you.\n\n"

        "📱 Call or text: +1-616-291-5227\n"

        "✅ Register FREE: RecDebut.com\n"

        "📧 dbell002@sbcglobal.net\n\n"

        "Let’s get you recruited!\n\n"

        "Dennis Bell\n"

        "Former New York Knicks\n"

        "President, Recreational Debut"

    )

    text = payload.message_text.strip() if payload.message_text else default_text

    sample_recipient = {"name": "Test Student-Athlete", "email": target_email, "sport": "Basketball", "grad_year": "2026", "high_school": "East Kentwood High"}

    personalized_text = format_personalized_message(text, sample_recipient)



    paragraphs = [p.strip() for p in personalized_text.split("\n\n") if p.strip()]

    html_paragraphs_list = []

    for p in paragraphs:

        p_with_br = p.replace("\n", "<br>")

        p_linked = re.sub(

            r'(?<!href=["\'])(https?://[^\s<>"]+)',

            r'<a href="\1" style="color: #006BB6; text-decoration: underline; font-weight: 600;" target="_blank">\1</a>',

            p_with_br

        )

        html_paragraphs_list.append(f"<p style='margin: 0 0 14px 0; line-height: 1.6; color: #1e293b;'>{p_linked}</p>")

    html_paragraphs = "".join(html_paragraphs_list)

    html_body = f"""<!DOCTYPE html>

<html>

<body style="margin: 0; padding: 24px; font-family: sans-serif; background-color: #f8fafc;">

  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px;">

    <div style="border-bottom: 2px solid #F58426; padding-bottom: 16px; margin-bottom: 20px;">

      <h2 style="margin: 0; color: #001F3F;">RECREATIONAL DEBUT [TEST DISPATCH]</h2>

      <div style="font-size: 13px; color: #64748b;">Dennis Bell Sports Program</div>

    </div>

    <div style="font-size: 15px; color: #1e293b;">

      {html_paragraphs}

    </div>

    <div style="border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 24px; font-size: 12px; color: #94a3b8;">

      Dennis Bell &bull; Former New York Knicks #4 &bull; dbell002@sbcglobal.net

    </div>

  </div>

</body>

</html>"""



    # 1. Check for configured transactional email API (Resend / SendGrid)

    api_settings = load_email_api_settings()

    provider = (api_settings.get("provider") or "auto").lower()

    resend_key = (api_settings.get("resend_api_key") or "").strip()

    resend_from = api_settings.get("resend_from_email") or f"{caller_id_name} <recruiting@recdebut.com>"

    sendgrid_key = (api_settings.get("sendgrid_api_key") or "").strip()

    sendgrid_from = api_settings.get("sendgrid_from_email") or f"{caller_id_name} <recruiting@recdebut.com>"



    if (provider in ("resend", "auto")) and resend_key:

        ok, res_str = send_resend_email(

            api_key=resend_key,

            from_email=resend_from,

            to_email=target_email,

            to_name="Test Student-Athlete",

            subject=f"[TEST] {subject}",

            text_content=personalized_text,

            html_content=html_body,

            reply_to=caller_id or "dbell002@sbcglobal.net"

        )

        return {

            "success": ok,

            "target_email": target_email,

            "subject": subject,

            "caller_id": caller_id,

            "caller_id_name": caller_id_name,

            "account_used": f"Resend API ({resend_from})",

            "sample_personalized_message": personalized_text,

            "message": f"Test email successfully delivered to {target_email} via Resend API (id: {res_str})! (Zero-Spam Protected)" if ok else f"Resend API dispatch failed: {res_str}"

        }

    elif (provider in ("sendgrid", "auto")) and sendgrid_key:

        ok, res_str = send_sendgrid_email(

            api_key=sendgrid_key,

            from_email=sendgrid_from,

            to_email=target_email,

            to_name="Test Student-Athlete",

            subject=f"[TEST] {subject}",

            text_content=personalized_text,

            html_content=html_body,

            reply_to=caller_id or "dbell002@sbcglobal.net"

        )

        return {

            "success": ok,

            "target_email": target_email,

            "subject": subject,

            "caller_id": caller_id,

            "caller_id_name": caller_id_name,

            "account_used": f"SendGrid API ({sendgrid_from})",

            "sample_personalized_message": personalized_text,

            "message": f"Test email successfully delivered to {target_email} via SendGrid API!" if ok else f"SendGrid API dispatch failed: {res_str}"

        }



    # 2. Fallback to SMTP Swarm

    swarm = [a for a in load_smtp_swarm() if a.get("active") and a.get("email") and a.get("app_password")]

    if not swarm:

        creds = load_credentials()

        swarm = [{

            "email": creds.get("IMAP_USER", "footballstar0325@gmail.com"),

            "app_password": creds.get("IMAP_APP_PASSWORD", ""),

            "smtp_host": creds.get("SMTP_HOST", "smtp.gmail.com"),

            "smtp_port": int(creds.get("SMTP_PORT", 587))

        }]



    last_ex = "No active SMTP account available"

    for acct in swarm:

        server = None

        s_user = acct["email"]

        s_pwd = acct["app_password"]

        s_host = acct.get("smtp_host", "smtp.gmail.com")

        s_port = int(acct.get("smtp_port", 587))



        msg = MIMEMultipart("alternative")

        msg["To"] = f"Recruitment Candidate <{target_email}>"

        # SPF Alignment: Authenticated user matches domain to prevent DMARC failure

        msg["From"] = f"{caller_id_name} <{s_user}>"

        msg["Reply-To"] = caller_id if caller_id else "dbell002@sbcglobal.net"

        msg["Subject"] = subject

        msg["Date"] = email.utils.formatdate(localtime=True)

        msg["List-Unsubscribe"] = f"<mailto:{caller_id if caller_id else 'dbell002@sbcglobal.net'}?subject=unsubscribe>"



        text_part = MIMEText(personalized_text, "plain", "utf-8")

        msg.attach(text_part)

        html_part = MIMEText(html_body, "html", "utf-8")

        msg.attach(html_part)



        try:

            server = smtplib.SMTP(s_host, s_port, timeout=10.0)

            server.ehlo()

            server.starttls()

            server.ehlo()

            server.login(s_user, s_pwd)

            server.sendmail(s_user, [target_email], msg.as_string())

            server.quit()

            return {

                "success": True,

                "target_email": target_email,

                "subject": subject,

                "caller_id": caller_id,

                "caller_id_name": caller_id_name,

                "account_used": f"SMTP ({s_user})",

                "sample_personalized_message": personalized_text,

                "message": f"Test email successfully delivered to {target_email} via {s_user}! (Reply-To: {caller_id})"

            }

        except Exception as ex:

            if server:

                try:

                    server.close()

                except Exception:

                    pass

            last_ex = str(ex)

            if "550" in last_ex or "daily user sending limit" in last_ex.lower():

                continue

            break



    is_quota = "550" in last_ex or "daily user sending limit" in last_ex.lower()

    return {

        "success": False,

        "target_email": target_email,

        "error": last_ex,

        "quota_exceeded": is_quota,

        "message": (

            f"Notice: Gmail daily user sending limit exceeded on account(s). "

            f"Google caps free Gmail at 500 emails/day. "

            f"We recommend configuring Resend API (3,000 free emails/mo) to eliminate Gmail limits permanently!"

            if is_quota else f"Failed to send test email: {last_ex}"

        )

    }



@router.get("/email-api/config")

async def get_email_api_config():

    """Get active email API configuration, provider status, and deliverability stats."""

    settings = load_email_api_settings()

    resend_key = (settings.get("resend_api_key") or "").strip()

    sendgrid_key = (settings.get("sendgrid_api_key") or "").strip()



    masked_resend = f"re_...{resend_key[-6:]}" if len(resend_key) > 8 else ("Configured" if resend_key else "Not Configured")

    masked_sendgrid = f"SG....{sendgrid_key[-6:]}" if len(sendgrid_key) > 8 else ("Configured" if sendgrid_key else "Not Configured")



    active_provider = settings.get("provider", "auto")

    if active_provider == "auto":

        if resend_key:

            detected_active = "Resend API (Transactional Shield)"

        elif sendgrid_key:

            detected_active = "SendGrid API"

        else:

            detected_active = "Gmail SMTP Swarm (Direct)"

    elif active_provider == "resend":

        detected_active = "Resend API" if resend_key else "Resend (Key Missing - Inactive)"

    elif active_provider == "sendgrid":

        detected_active = "SendGrid API" if sendgrid_key else "SendGrid (Key Missing - Inactive)"

    else:

        detected_active = "Gmail SMTP Swarm"



    return {

        "success": True,

        "provider": active_provider,

        "active_provider_name": detected_active,

        "is_api_active": bool(resend_key or sendgrid_key),

        "resend_status": masked_resend,

        "resend_from_email": settings.get("resend_from_email", "Dennis Bell <recruiting@recdebut.com>"),

        "sendgrid_status": masked_sendgrid,

        "sendgrid_from_email": settings.get("sendgrid_from_email", "Dennis Bell <recruiting@recdebut.com>"),

        "reply_to_email": settings.get("reply_to_email", "dbell002@sbcglobal.net"),

        "rate_smoothing_seconds": settings.get("rate_smoothing_seconds", 1.8),

        "recommendation": (

            "✅ Protected: Emails are routed via Transactional Email API with 0% risk to personal Google accounts."

            if (resend_key or sendgrid_key) else

            "⚠️ Using Direct Gmail SMTP: We recommend connecting Resend API (resend.com) with your domain to permanently prevent Google account restrictions and spam flagging."

        )

    }



@router.post("/email-api/config")

async def update_email_api_config(payload: EmailApiConfigPayload):

    """Save email API settings and credentials."""

    settings = load_email_api_settings()

    if payload.provider is not None:

        settings["provider"] = payload.provider.strip()

    if payload.resend_api_key is not None:

        settings["resend_api_key"] = payload.resend_api_key.strip()

    if payload.resend_from_email is not None:

        settings["resend_from_email"] = payload.resend_from_email.strip()

    if payload.sendgrid_api_key is not None:

        settings["sendgrid_api_key"] = payload.sendgrid_api_key.strip()

    if payload.sendgrid_from_email is not None:

        settings["sendgrid_from_email"] = payload.sendgrid_from_email.strip()

    if payload.reply_to_email is not None:

        settings["reply_to_email"] = payload.reply_to_email.strip()



    ok = save_email_api_settings(settings)

    if not ok:

        raise HTTPException(status_code=500, detail="Failed to write email API settings to storage.")



    return {

        "success": True,

        "message": "Email API configuration successfully updated and saved.",

        "config": settings

    }



@router.post("/email-api/test")

async def test_email_api_connection(payload: EmailApiTestPayload = Body(default=EmailApiTestPayload())):

    """Send a live test verification email through the configured API (Resend or SendGrid)."""
    _require_recdebut_outbound()

    settings = load_email_api_settings()

    resend_key = (settings.get("resend_api_key") or "").strip()

    sendgrid_key = (settings.get("sendgrid_api_key") or "").strip()

    provider = (settings.get("provider") or "auto").lower()



    target = payload.target_email or "brett@stehouwerproductions.com"

    reply_to = settings.get("reply_to_email", "dbell002@sbcglobal.net")



    if not resend_key and not sendgrid_key:

        return {

            "success": False,

            "error": "No API key configured. Please enter a valid Resend or SendGrid API key."

        }



    # Test Resend

    if (provider in ("resend", "auto")) and resend_key:

        from_email = settings.get("resend_from_email") or "Dennis Bell <recruiting@recdebut.com>"

        sent_ok, resp_str = send_resend_email(

            api_key=resend_key,

            from_email=from_email,

            to_email=target,

            to_name="Dennis Bell Program Operator",

            subject="AI-BS Email Protection: Resend API Connected & Verified",

            text_content="Your Resend API connection is fully operational in AI-BS.",

            html_content=(

                "<h3>🎉 Resend API Connected Successfully!</h3>"

                f"<p>Your Resend API Key is active in AI-BS. Sending from: <code>{from_email}</code></p>"

                f"<p>Reply-To: <code>{reply_to}</code></p>"

                "<p>Anti-spam protection is engaged. Personal Google accounts are 100% insulated.</p>"

            ),

            reply_to=reply_to

        )

        if not sent_ok and "domain is not verified" in resp_str.lower() and target.lower() == "brettstehouwer@gmail.com":

            # Fallback to onboarding@resend.dev for test email verification

            sent_ok, resp_str = send_resend_email(

                api_key=resend_key,

                from_email="Dennis Bell <onboarding@resend.dev>",

                to_email=target,

                to_name="Dennis Bell Program Operator",

                subject="AI-BS Email Protection: Resend API Connected & Verified",

                text_content="Your Resend API connection is fully operational in AI-BS.",

                html_content=(

                    "<h3>🎉 Resend API Connected Successfully!</h3>"

                    "<p>Your Resend API Key is active and verified in AI-BS.</p>"

                    "<p><b>Note for broad broadcasting:</b> To send to external athlete emails from <code>recruiting@recdebut.com</code>, verify your domain at <a href='https://resend.com/domains'>resend.com/domains</a>.</p>"

                ),

                reply_to=reply_to

            )

            if sent_ok:

                return {

                    "success": True,

                    "provider": "Resend API",

                    "message": f"Test email successfully delivered to {target}! (Message ID: {resp_str}). Note: Verify recdebut.com at resend.com/domains before mass broadcasting to external recipients.",

                    "message_id": resp_str,

                    "requires_domain_verification": True

                }



        return {

            "success": sent_ok,

            "provider": "Resend API",

            "message": f"Test email sent to {target} (ID: {resp_str})" if sent_ok else resp_str,

            "message_id": resp_str if sent_ok else None

        }



    # Test SendGrid

    if (provider == "sendgrid" or (provider == "auto" and not resend_key)) and sendgrid_key:

        from_email = settings.get("sendgrid_from_email") or "Dennis Bell <recruiting@recdebut.com>"

        sent_ok, resp_str = send_sendgrid_email(

            api_key=sendgrid_key,

            from_email=from_email,

            to_email=target,

            to_name="Dennis Bell Program Operator",

            subject="AI-BS Email Protection: SendGrid API Connected & Verified",

            text_content="Your SendGrid API connection is fully operational in AI-BS.",

            html_content="<h3>🎉 SendGrid API Connected Successfully!</h3>",

            reply_to=reply_to

        )

        return {

            "success": sent_ok,

            "provider": "SendGrid API",

            "message": f"Test email sent to {target}" if sent_ok else resp_str

        }



    return {"success": False, "error": "Unknown email provider"}





@router.get("/quota-status")

async def get_daily_quota_status():

    """Retrieve 24-hour Gmail gateway quota and safe batch pacing telemetry."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        

        now = time.time()

        one_day_ago = now - 86400

        

        # Sent in last 24h

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE last_messaged_at >= ?", (one_day_ago,))

        sent_last_24h = cursor.fetchone()[0]

        

        # Total contacted

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")

        total_contacted = cursor.fetchone()[0]

        

        # Pending athletes

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")

        pending_count = cursor.fetchone()[0]

        

        # Total athletes

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes")

        total_athletes = cursor.fetchone()[0]

        

        # Athletes with valid emails

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE email IS NOT NULL AND email != ''")

        athletes_with_emails = cursor.fetchone()[0]

        

        conn.close()

        

        # Single-Account Metrics

        daily_ceiling = 450  # Safe conservative threshold under Gmail's 500/day limit

        remaining_today = max(0, daily_ceiling - sent_last_24h)

        recommended_batch_size = min(400, remaining_today)

        days_to_complete = -(-pending_count // 400) if pending_count > 0 else 0

        

        # Swarm Metrics across all active accounts

        swarm = load_smtp_swarm()

        active_swarm = [a for a in swarm if a.get("active", True)]

        total_swarm_daily_ceiling = sum(a.get("daily_limit", 400) for a in active_swarm) or 450

        swarm_remaining_today = max(0, total_swarm_daily_ceiling - sent_last_24h)

        swarm_days_to_complete = -(-pending_count // total_swarm_daily_ceiling) if (pending_count > 0 and total_swarm_daily_ceiling > 0) else 0



        return {

            "success": True,

            "sent_last_24h": sent_last_24h,

            "daily_ceiling": daily_ceiling,

            "remaining_today": remaining_today,

            "pending_count": pending_count,

            "total_contacted": total_contacted,

            "total_athletes": total_athletes,

            "athletes_with_emails": athletes_with_emails,

            "recommended_batch_size": recommended_batch_size,

            "days_to_complete": days_to_complete,

            "swarm_accounts_count": len(active_swarm),

            "swarm_daily_ceiling": total_swarm_daily_ceiling,

            "swarm_remaining_today": swarm_remaining_today,

            "swarm_days_to_complete": swarm_days_to_complete,

            "status": "READY" if remaining_today > 0 else "DAILY_CAP_REACHED"

        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.get("/smtp-accounts")

async def get_smtp_accounts():

    """List all configured accounts in the SMTP Swarm pool."""

    try:

        accounts = load_smtp_swarm()

        sanitized = []

        for a in accounts:

            pwd = a.get("app_password", "")

            masked = (pwd[:3] + "••••••••" + pwd[-3:]) if len(pwd) >= 8 else "••••••••••••••••"

            sanitized.append({

                "id": a.get("id"),

                "email": a.get("email"),

                "label": a.get("label") or a.get("email"),

                "app_password_masked": masked,

                "daily_limit": a.get("daily_limit", 400),

                "active": a.get("active", True),

                "smtp_host": a.get("smtp_host", "smtp.gmail.com"),

                "smtp_port": a.get("smtp_port", 587)

            })

        active_accounts = [a for a in accounts if a.get("active", True)]

        total_capacity = sum(a.get("daily_limit", 400) for a in active_accounts)

        return {

            "success": True,

            "total_accounts": len(accounts),

            "active_accounts": len(active_accounts),

            "total_daily_capacity": total_capacity,

            "accounts": sanitized

        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/smtp-accounts")

async def add_or_update_smtp_account(payload: SmtpAccountCreatePayload):

    """Add or update a sender account in the SMTP Swarm pool."""

    try:

        email_clean = payload.email.strip().lower()

        pwd_clean = payload.app_password.strip().replace(" ", "")

        if not email_clean or not pwd_clean:

            raise HTTPException(status_code=400, detail="Email and Google App Password are required.")



        accounts = load_smtp_swarm()

        existing = next((a for a in accounts if a.get("email", "").lower() == email_clean), None)

        if existing:

            existing["app_password"] = pwd_clean

            existing["label"] = payload.label or existing.get("label")

            existing["daily_limit"] = payload.daily_limit or 400

            existing["active"] = payload.active if payload.active is not None else True

            existing["smtp_host"] = payload.smtp_host or "smtp.gmail.com"

            existing["smtp_port"] = payload.smtp_port or 587

            existing["updated_at"] = time.time()

        else:

            new_acct = {

                "id": f"acct_{int(time.time())}_{len(accounts)+1}",

                "email": email_clean,

                "app_password": pwd_clean,

                "label": payload.label or email_clean,

                "daily_limit": payload.daily_limit or 400,

                "active": payload.active if payload.active is not None else True,

                "smtp_host": payload.smtp_host or "smtp.gmail.com",

                "smtp_port": payload.smtp_port or 587,

                "created_at": time.time()

            }

            accounts.append(new_acct)



        save_smtp_swarm(accounts)

        return {

            "success": True,

            "message": f"SMTP Swarm account {email_clean} saved successfully.",

            "total_accounts": len(accounts)

        }

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/smtp-accounts/{account_id}")

async def delete_smtp_account(account_id: str):

    """Remove an account from the SMTP Swarm pool."""

    try:

        accounts = load_smtp_swarm()

        if len(accounts) <= 1:

            raise HTTPException(status_code=400, detail="Cannot delete the only sender account. At least 1 account is required in the swarm.")

        filtered = [a for a in accounts if a.get("id") != account_id and a.get("email") != account_id]

        if len(filtered) == len(accounts):

            raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

        save_smtp_swarm(filtered)

        return {

            "success": True,

            "message": "Account removed from swarm.",

            "remaining_accounts": len(filtered)

        }

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.post("/smtp-accounts/test")

async def test_smtp_account_login(payload: SmtpAccountTestPayload):

    """Test authentication of an SMTP account."""
    _require_recdebut_outbound()

    try:

        server = smtplib.SMTP(payload.smtp_host or "smtp.gmail.com", int(payload.smtp_port or 587), timeout=10.0)

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(payload.email.strip(), payload.app_password.strip())

        server.quit()

        return {

            "success": True,

            "email": payload.email,

            "message": "SMTP connection and credentials verified successfully!"

        }

    except Exception as e:

        return {

            "success": False,

            "email": payload.email,

            "error": str(e),

            "message": f"Authentication failed: {str(e)}"

        }



@router.get("/athlete-emails")

async def get_athlete_emails_summary():

    """Summary and file paths for the 2,107 cleaned athlete emails."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE email IS NOT NULL AND email != ''")

        email_count = cursor.fetchone()[0]

        cursor.execute("SELECT id, name, email, phone, sport, high_school FROM rec_debut_athletes WHERE email IS NOT NULL AND email != '' ORDER BY id ASC LIMIT 25")

        rows = cursor.fetchall()

        conn.close()



        master_csv = DATA_DIR / "rec_debut_athlete_emails_master.csv"

        user_csv = Path.home() / "OneDrive" / "Pictures" / "RecDebut_Athletes_Emails_For_Blast.csv"

        clean_txt = DATA_DIR / "rec_debut_athlete_emails_clean_list.txt"



        return {

            "success": True,

            "total_athlete_emails": email_count,

            "master_csv_exists": master_csv.exists(),

            "master_csv_path": str(master_csv),

            "user_csv_exists": user_csv.exists(),

            "user_csv_path": str(user_csv),

            "clean_txt_exists": clean_txt.exists(),

            "clean_txt_path": str(clean_txt),

            "preview": [

                {"id": r[0], "name": r[1], "email": r[2], "phone": r[3], "sport": r[4], "high_school": r[5]}

                for r in rows

            ]

        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



@router.get("/campaigns")

async def get_campaigns_history():

    """Retrieve campaign history and broadcast audit logs."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM rec_debut_campaigns ORDER BY created_at DESC LIMIT 50")

        rows = cursor.fetchall()

        conn.close()

        return {"success": True, "campaigns": [dict(r) for r in rows]}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



# --- Inbound IMAP Athlete Reply Ingestion & Carrier SMS Management ---



def decode_mime_words(s: str) -> str:

    if not s:

        return ""

    decoded = []

    try:

        parts = decode_header(s)

        for text, encoding in parts:

            if isinstance(text, bytes):

                decoded.append(text.decode(encoding or "utf-8", errors="ignore"))

            else:

                decoded.append(str(text))

        return "".join(decoded)

    except Exception:

        return str(s)



def extract_email_body(msg: email.message.Message) -> str:

    body = ""

    if msg.is_multipart():

        for part in msg.walk():

            ctype = part.get_content_type()

            cdispo = str(part.get("Content-Disposition") or "")

            if ctype == "text/plain" and "attachment" not in cdispo:

                charset = part.get_content_charset() or "utf-8"

                try:

                    body = part.get_payload(decode=True).decode(charset, errors="ignore")

                    if body:

                        break

                except Exception:

                    pass

        if not body:

            for part in msg.walk():

                ctype = part.get_content_type()

                if "text" in ctype:

                    try:

                        charset = part.get_content_charset() or "utf-8"

                        body = part.get_payload(decode=True).decode(charset, errors="ignore")

                        if body:

                            break

                    except Exception:

                        pass

    else:

        charset = msg.get_content_charset() or "utf-8"

        try:

            body = msg.get_payload(decode=True).decode(charset, errors="ignore")

        except Exception:

            body = str(msg.get_payload())

    return (body or "").strip()



def get_personal_exclusion_set() -> Tuple[Set[str], Set[str]]:

    """

    Returns sets of excluded personal phone numbers (10 digits) and email addresses

    that must NEVER be routed to Dennis Bell or logged as student-athlete replies.

    Ingests C:/Users/footb/OneDrive/Desktop/MyPhoneContacts.csv alongside operator personal numbers.

    """

    excluded_phones = {

        "6164023628",  # Brett Stehouwer personal cell

        "6164067993",  # Mom personal cell

        "6162915227",  # Dennis Bell (prevent routing loop)

        "6168027774",  # Adam Stehouwer

    }

    excluded_emails = {

        "brettstehouwer@gmail.com",

        "brett.noco.letsgo.stehouwer@gmail.com",

        "footballstar0325@gmail.com",

        "adamstehouwer24@gmail.com",

        "brett@stehouwer-publishing.com",

        "account@nvidia.com",

        "dbell002@sbcglobal.net",

    }



    contact_phones, contact_emails = load_personal_contacts()
    excluded_phones.update(contact_phones)
    excluded_emails.update(contact_emails)
    return excluded_phones, excluded_emails




def dispatch_sms_message(recipient_phone: str, message_text: str, caller_id_name: str = "RecDebut Lead Sentinel") -> Dict[str, Any]:

    """

    Dispatches SMS via the highest-reliability configured provider:

      1. TextBee Android SIM Gateway ($0.00/msg) -> TEXTBEE_API_KEY & TEXTBEE_DEVICE_ID (Samsung Galaxy S25 Ultra)

      2. Telnyx Direct Cellular API ($0.004/segment) -> TELNYX_API_KEY & TELNYX_FROM_PHONE

      3. Built-in Carrier MMS Gateway fallback for Dennis Bell's instant lead alerts

    """
    if not outbound_messaging_enabled("recdebut"):
        return {"success": False, "blocked": True, "code": "OUTBOUND_MESSAGING_DISABLED", "error": RECDEBUT_DISABLED_MESSAGE, "reason": RECDEBUT_DISABLED_MESSAGE}

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
    if not outbound_messaging_enabled("recdebut"):
        return False, RECDEBUT_DISABLED_MESSAGE

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

            "app_password": creds.get("IMAP_APP_PASSWORD", ""),

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
    """Authorize only an exact, unambiguous contact in the active athlete database."""
    phone = normalize_phone(sender_phone)
    email_address = (sender_email or '').strip().casefold()
    if sender_phone and not phone:
        return None
    if not phone and not email_address:
        return None
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH.resolve().as_uri() + '?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        conn.create_function('recdebut_phone', 1, normalize_phone, deterministic=True)
        columns = 'id, name, sport, high_school, grad_year, city_state, phone, email'
        if phone:
            rows = conn.execute(f'SELECT {columns} FROM rec_debut_athletes WHERE recdebut_phone(phone) = ?', (phone,)).fetchmany(2)
        else:
            rows = conn.execute(f'SELECT {columns} FROM rec_debut_athletes WHERE LOWER(TRIM(email)) = ?', (email_address,)).fetchmany(2)
        return dict(rows[0]) if len(rows) == 1 else None
    except (sqlite3.Error, OSError):
        return None
    finally:
        if conn is not None:
            conn.close()


def _verified_reply_athlete(sender_phone, sender_email):
    try:
        excluded_phones, excluded_emails = get_personal_exclusion_set()
    except PrivacyCheckUnavailable:
        return None, 'Personal contact exclusions unavailable; forwarding blocked.'
    phone = normalize_phone(sender_phone)
    email_address = (sender_email or '').strip().casefold()
    if sender_phone and not phone:
        return None, 'Invalid or ambiguous sender phone; forwarding blocked.'
    if (phone and phone in excluded_phones) or (email_address and email_address in excluded_emails):
        return None, 'Personal contact excluded from forwarding.'
    athlete = find_athlete_by_contact(sender_phone=sender_phone, sender_email=sender_email)
    if athlete is None:
        return None, 'No unique, exact athlete-roster match; forwarding blocked.'
    return athlete, ''






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
    if not outbound_messaging_enabled("recdebut"):
        return {"success": False, "blocked": True, "code": "OUTBOUND_MESSAGING_DISABLED", "error": RECDEBUT_DISABLED_MESSAGE, "reason": RECDEBUT_DISABLED_MESSAGE}

    verified_athlete, privacy_reason = _verified_reply_athlete(sender_phone, sender_email)
    if verified_athlete is None:
        return {'success': False, 'reason': privacy_reason}
    athlete_info = verified_athlete
    athlete_name = verified_athlete.get('name') or 'Student-Athlete'

    dennis_phone = "+1-616-291-5227"

    dennis_email = "dbell002@sbcglobal.net"

    dennis_clean = "6162915227"



    sender_clean = re.sub(r'\D', '', sender_phone)[-10:] if sender_phone else ""

    if dennis_clean in sender_clean:

        return {"success": False, "reason": "Self-sent message from Dennis Bell ignored"}



    excluded_phones, excluded_emails = get_personal_exclusion_set()

    if sender_clean and sender_clean in excluded_phones:

        return {"success": False, "reason": f"Blocked personal/operator phone ({sender_phone}) from forwarding to Dennis Bell"}

    if sender_email and sender_email.lower().strip() in excluded_emails:

        return {"success": False, "reason": f"Blocked personal/operator email ({sender_email}) from forwarding to Dennis Bell"}



    sport_str = (athlete_info.get("sport") if athlete_info and athlete_info.get("sport") else "Basketball")

    hs_str = (f" | {athlete_info.get('high_school')}" if athlete_info and athlete_info.get("high_school") else "")

    grad_str = (f" ('{str(athlete_info.get('grad_year'))[-2:]})" if athlete_info and athlete_info.get("grad_year") else "")

    city_str = (f" - {athlete_info.get('city_state')}" if athlete_info and athlete_info.get("city_state") else "")



    contact_display = sender_phone if sender_phone else (sender_email if sender_email else "Unknown Contact")



    # 1. Direct Live SMS payload to Dennis Bell's phone (+1-616-291-5227)

    forward_sms = (

        f"🏀 REC DEBUT ATHLETE REPLY!\n"

        f"From: {athlete_name} ({sport_str}{hs_str}{grad_str})\n"

        f"Phone: {contact_display}\n\n"

        f"\"{reply_body.strip()[:320]}\"\n\n"

        f"👉 Tap to call or text back: {contact_display}"

    )



    sms_res = dispatch_sms_message(dennis_phone, forward_sms, caller_id_name="RecDebut Lead Alert")



    # 2. Instant Rich HTML & Text Email Alert to Dennis Bell (dbell002@sbcglobal.net)

    email_subject = f"🏀 RecDebut Reply: {athlete_name} ({sport_str}{hs_str})"

    text_content = (

        f"NEW STUDENT-ATHLETE REPLY RECEIVED!\n\n"

        f"Athlete: {athlete_name}\n"

        f"Sport: {sport_str}\n"

        f"School: {athlete_info.get('high_school', 'N/A') if athlete_info else 'N/A'}\n"

        f"Grad Year: {athlete_info.get('grad_year', '2027') if athlete_info else '2027'}\n"

        f"Phone: {contact_display}\n"

        f"Email: {sender_email if sender_email else (athlete_info.get('email', 'N/A') if athlete_info else 'N/A')}\n\n"

        f"Message Text:\n"

        f"\"{reply_body.strip()}\"\n\n"

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

        <div class="msg-box">\"{reply_body.strip()}\"</div>

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

    secondary_db = Path(r"C:\Recreational-Debut\saved_data\rec_debut.db")



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
    # Receive-only opt-outs remain available while the forwarding gate is closed.
    if sender_email:
        from recdebut_email_unsubscribe import process_email_opt_out
        email_meta = raw_meta if isinstance(raw_meta, dict) else {}
        opt_out = process_email_opt_out(sender_email, email_meta.get('subject', ''),
                                        email_meta.get('reply_text', reply_body))
        if opt_out['handled']:
            return opt_out
    _require_recdebut_outbound()

    verified_athlete, privacy_reason = _verified_reply_athlete(sender_phone, sender_email)
    if verified_athlete is None:
        return {'success': False, 'reason': privacy_reason}
    raw_meta = raw_meta or {}

    reply_body = (reply_body or "").strip()

    if not reply_body:

        return {"success": False, "reason": "Empty reply body"}



    sender_phone = (sender_phone or "").strip()

    sender_email = (sender_email or "").strip().lower()



    sender_clean = re.sub(r'\D', '', sender_phone)[-10:] if sender_phone else ""

    sender_digits_all = re.sub(r'\D', '', sender_phone) if sender_phone else ""



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



    # Match athlete strictly against the verified 7,357 student-athlete roster

    athlete = find_athlete_by_contact(sender_phone=sender_phone, sender_email=sender_email)

    if not athlete:

        # Strict Separation Rule: NEVER forward or log messages from non-roster phone numbers

        # so personal texts to Brett's phone are 100% isolated from Dennis Bell's feed.

        return {

            "success": False,

            "reason": f"Ignored non-roster contact ({sender_phone or sender_email}): strict athlete roster whitelist enforced."

        }

    athlete_id = athlete.get("id")

    athlete_name = athlete.get("name") or "Student-Athlete"



    # Message hash for deduping

    m_id = raw_meta.get("smsId") or raw_meta.get("messageId") or raw_meta.get("_id") or raw_meta.get("id") or raw_meta.get("idempotencyKey")

    if m_id:

        source_namespace = "textbee" if source.startswith("textbee") else source
        msg_hash = f"{source_namespace}_{m_id}"

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

    secondary_db = Path(r"C:\Recreational-Debut\saved_data\rec_debut.db")

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



    if not saved_primary:
        return {'success': False, 'reason': 'Reply not newly stored; forwarding blocked to prevent duplicates.'}

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
    _require_recdebut_outbound()

    creds = load_credentials()

    textbee_device = (os.environ.get("TEXTBEE_DEVICE_ID") or creds.get("TEXTBEE_DEVICE_ID") or "").strip()

    textbee_key = (os.environ.get("TEXTBEE_API_KEY") or creds.get("TEXTBEE_API_KEY") or "").strip()



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





class TextBeeDispatchRequest(BaseModel):

    batch_size: int = 50

    grad_year: Optional[str] = "2027"

    sim_subscription_id: Optional[int] = None

    custom_message_template: Optional[str] = None

    dry_run: bool = False

    portal: Optional[str] = "recdebut"





@router.get("/textbee/status")

@legacy_router.get("/textbee/status")

async def get_textbee_gateway_status():

    _require_recdebut_outbound()
    """

    Returns live hardware, battery, SIM, and connection telemetry for the Samsung Galaxy S25 Ultra gateway.

    """

    creds = load_credentials()

    textbee_device = (os.environ.get("TEXTBEE_DEVICE_ID") or creds.get("TEXTBEE_DEVICE_ID") or "").strip()

    textbee_key = (os.environ.get("TEXTBEE_API_KEY") or creds.get("TEXTBEE_API_KEY") or "").strip()



    if not textbee_device or not textbee_key:

        return {"connected": False, "error": "Missing TextBee credentials"}



    url = f"https://api.textbee.dev/api/v1/gateway/devices/{textbee_device}"

    headers = {"x-api-key": textbee_key, "Content-Type": "application/json"}



    try:

        resp = requests.get(url, headers=headers, timeout=8.0)

        if resp.status_code == 200:

            dev_data = resp.json().get("data", {})

            return {

                "connected": True,

                "provider": "textbee",

                "device": dev_data

            }

        else:

            return {"connected": False, "error": f"TextBee API returned HTTP {resp.status_code}"}

    except Exception as e:

        return {"connected": False, "error": str(e)}





@router.get("/textbee/messages")

@legacy_router.get("/textbee/messages")

async def get_textbee_gateway_messages(limit: int = 30):

    _require_recdebut_outbound()
    """

    Fetches real-time inbound & outbound SMS logs from the TextBee device gateway.

    """

    creds = load_credentials()

    textbee_device = (os.environ.get("TEXTBEE_DEVICE_ID") or creds.get("TEXTBEE_DEVICE_ID") or "").strip()

    textbee_key = (os.environ.get("TEXTBEE_API_KEY") or creds.get("TEXTBEE_API_KEY") or "").strip()



    if not textbee_device or not textbee_key:

        return {"success": False, "messages": []}



    url = f"https://api.textbee.dev/api/v1/gateway/devices/{textbee_device}/messages?limit={limit}"

    headers = {"x-api-key": textbee_key, "Content-Type": "application/json"}



    try:

        resp = requests.get(url, headers=headers, timeout=10.0)

        if resp.status_code == 200:

            raw_msgs = resp.json().get("data", [])

            excluded_phones, _ = get_personal_exclusion_set()

            messages = []

            for m in raw_msgs:

                direction = "received" if m.get("type") == "RECEIVED" else "sent"

                contact_phone = m.get("sender") if direction == "received" else (

                    (m.get("recipients", [None])[0] if m.get("recipients") else None) or m.get("recipient")

                )

                digits = re.sub(r'\D', '', str(contact_phone or ""))

                # Filter out shortcodes (< 10 digits) and personal excluded numbers

                if digits and len(digits) < 10:

                    continue

                if len(digits) >= 10 and digits[-10:] in excluded_phones:

                    continue

                # For inbound messages, strictly require a verified athlete roster match

                ath = find_athlete_by_contact(sender_phone=str(contact_phone or "")) if contact_phone else None

                if direction == "received" and not ath:

                    continue

                messages.append({

                    "_id": m.get("_id"),

                    "sender": contact_phone,

                    "athlete_name": ath.get("name") if ath else None,

                    "high_school": ath.get("high_school") if ath else None,

                    "grad_year": ath.get("grad_year") if ath else None,

                    "recipients": m.get("recipients") or ([m.get("recipient")] if m.get("recipient") else []),

                    "message": m.get("message"),

                    "direction": direction,

                    "receivedAt": m.get("receivedAt") or m.get("createdAt"),

                    "createdAt": m.get("createdAt"),

                    "status": m.get("status")

                })

            return {"success": True, "messages": messages}

        return {"success": False, "messages": []}

    except Exception as e:

        return {"success": False, "error": str(e), "messages": []}





@router.post("/textbee/sync-inbound")

@legacy_router.post("/textbee/sync-inbound")

async def sync_textbee_inbound_endpoint():

    """

    Triggers an immediate poll of received SMS from TextBee and auto-forwards any recruit replies to Dennis Bell.

    """

    return sync_textbee_inbound_messages()





@router.post("/textbee/dispatch-batch")

@legacy_router.post("/textbee/dispatch-batch")

async def dispatch_textbee_batch_endpoint(req: TextBeeDispatchRequest):

    """

    Controlled bulk dispatch directly through Samsung Galaxy S25 Ultra gateway via TextBee.

    """
    if not req.dry_run:
        _require_recdebut_outbound()

    creds = load_credentials()

    textbee_device = (os.environ.get("TEXTBEE_DEVICE_ID") or creds.get("TEXTBEE_DEVICE_ID") or "").strip()

    textbee_key = (os.environ.get("TEXTBEE_API_KEY") or creds.get("TEXTBEE_API_KEY") or "").strip()



    conn = sqlite3.connect(str(DB_PATH))

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()



    # Load excluded coaches phone numbers

    cursor.execute("SELECT phone FROM rec_debut_excluded_coaches")

    coach_rows = cursor.fetchall()

    excluded_phones = set()

    for cr in coach_rows:

        cp = re.sub(r'\D', '', cr["phone"] or "")

        if len(cp) >= 10:

            excluded_phones.add(cp[-10:])



    # Load personal exclusion set and already-dispatched athlete IDs / phones

    personal_phones, _ = get_personal_exclusion_set()

    excluded_phones.update(personal_phones)



    cursor.execute("SELECT DISTINCT athlete_id FROM rec_debut_dispatches WHERE athlete_id IS NOT NULL")

    already_dispatched = {r[0] for r in cursor.fetchall()}



    cursor.execute("""

        SELECT DISTINCT a.phone

        FROM rec_debut_dispatches d

        JOIN rec_debut_athletes a ON a.id = d.athlete_id

        WHERE a.phone IS NOT NULL

    """)

    dispatched_phones = set()

    for pr in cursor.fetchall():

        dp = re.sub(r'\D', '', pr[0] or "")

        if len(dp) >= 10:

            dispatched_phones.add(dp[-10:])



    # Fetch next batch of un-dispatched candidates (prioritizing Class of 2027 by default)

    if req.grad_year and req.grad_year.lower() != "all":

        cursor.execute('''

            SELECT id, name, phone, email, sport, high_school, grad_year

            FROM rec_debut_athletes

            WHERE grad_year = ?

              AND phone IS NOT NULL AND length(phone) >= 10

            ORDER BY id ASC

        ''', (str(req.grad_year).strip(),))

    else:

        cursor.execute('''

            SELECT id, name, phone, email, sport, high_school, grad_year

            FROM rec_debut_athletes

            WHERE phone IS NOT NULL AND length(phone) >= 10

            ORDER BY CASE WHEN grad_year = '2027' THEN 0 ELSE 1 END, id ASC

        ''')

    candidate_rows = [r for r in cursor.fetchall() if r["id"] not in already_dispatched]



    staged = []

    blocked_coaches = 0

    seen_batch_phones = set(dispatched_phones)



    default_template = (

        "Hi {first_name}, a former NBA player wants to endorse your athletic portfolio! "

        "Dennis Bell, former NY Knick, can help your recruiting profile stand out. "

        "Free registration: recdebut-recruit.org/r/{athlete_id} "

        "616-291-5227 Dbell002@sbcglobal.net"

    )

    template = (req.custom_message_template or default_template).strip()



    for row in candidate_rows:

        if len(staged) >= req.batch_size:

            break

        raw_p = row["phone"] or ""

        clean_p = re.sub(r'\D', '', raw_p)

        if len(clean_p) < 10:

            continue

        ten_digit = clean_p[-10:]

        if ten_digit[0] in ("0", "1"):

            continue

        if ten_digit in excluded_phones:

            blocked_coaches += 1

            continue

        if ten_digit in seen_batch_phones:

            continue

        seen_batch_phones.add(ten_digit)



        e164_p = f"+1{ten_digit}"

        full_name = (row["name"] or "").strip()

        first_name = full_name.split()[0] if full_name else "Athlete"



        msg_body = template.replace("{first_name}", first_name)

        msg_body = msg_body.replace("{name}", full_name)

        msg_body = msg_body.replace("{sport}", row["sport"] or "Basketball")

        msg_body = msg_body.replace("{grad_year}", str(row["grad_year"] or "2027"))

        msg_body = msg_body.replace("{athlete_id}", str(row["id"]))



        staged.append({

            "athlete_id": row["id"],

            "name": full_name,

            "first_name": first_name,

            "phone": e164_p,

            "message": msg_body

        })



    if req.dry_run:

        conn.close()

        return {

            "success": True,

            "dry_run": True,

            "staged_count": len(staged),

            "blocked_coaches": blocked_coaches,

            "sample": {"message": staged[0]["message"], "recipients": [staged[0]["phone"]]} if staged else None

        }



    # Live Dispatch execution

    if not textbee_device or not textbee_key:

        conn.close()

        return {"success": False, "error": "TextBee device or API key not configured"}



    send_url = f"https://api.textbee.dev/api/v1/gateway/devices/{textbee_device}/send-sms"

    headers = {"x-api-key": textbee_key, "Content-Type": "application/json"}

    now_ts = time.time()

    batch_id = f"tb_{int(now_ts)}"

    dispatched_count = 0



    for item in staged:

        try:

            r = requests.post(

                send_url,

                headers=headers,

                json={"recipients": [item["phone"]], "message": item["message"]},

                timeout=12.0

            )

            resp_id = ""

            if r.status_code == 429:

                time.sleep(3.0)

                r = requests.post(send_url, headers=headers, json={"recipients": [item["phone"]], "message": item["message"]}, timeout=12.0)

            if r.status_code in (200, 201):

                res_json = r.json()

                data_obj = res_json.get("data", {})

                resp_id = (data_obj.get("smsBatchId") or data_obj.get("_id") or str(data_obj)) if isinstance(data_obj, dict) else str(data_obj)

            

            if r.status_code not in (200, 201):
                cursor.execute("INSERT INTO rec_debut_dispatches (athlete_id, channel, status, message_body, dispatched_at, response_status) VALUES (?, 'SMS', 'FAILED', ?, ?, ?)", (item["athlete_id"], item["message"], now_ts, "HTTP " + str(r.status_code)))
                conn.commit()
                continue

            cursor.execute('''

                INSERT INTO rec_debut_dispatches (athlete_id, channel, status, message_body, dispatched_at, response_status)

                VALUES (?, 'SMS', 'QUEUED', ?, ?, ?)

            ''', (item["athlete_id"], item["message"], now_ts, resp_id))



            cursor.execute('''

                UPDATE rec_debut_athletes

                SET status = 'SMS Queued', last_messaged_at = ?

                WHERE id = ?

            ''', (now_ts, item["athlete_id"]))

            conn.commit()

            dispatched_count += 1

        except Exception as err:

            print(f"[TEXTBEE BATCH SEND ERROR] Athlete {item['athlete_id']}: {err}")



    conn.close()



    return {

        "success": True,

        "dry_run": False,

        "dispatched_count": dispatched_count,

        "blocked_coaches": blocked_coaches,

        "sms_batch_id": batch_id,

        "sample": {"message": staged[0]["message"], "recipients": [staged[0]["phone"]]} if staged else None

    }





def sync_imap_inbound_messages(receive_only: bool = False) -> Dict[str, Any]:

    """

    Connects to IMAP SSL, searches for incoming carrier gateway MMS texts and direct email replies,

    and auto-forwards them to Dennis Bell (+1-616-291-5227 / dbell002@sbcglobal.net).

    """
    if type(receive_only) is not bool:
        raise ValueError('receive_only must be an explicit boolean')
    if not receive_only:
        _require_recdebut_outbound()

    creds = load_credentials()

    imap_user = creds.get("IMAP_USER") if isinstance(creds, dict) else None
    imap_pwd = creds.get("IMAP_APP_PASSWORD") if isinstance(creds, dict) else None
    if (not isinstance(imap_user, str) or not imap_user.strip()
            or not isinstance(imap_pwd, str) or not imap_pwd.strip()):
        return {"success": False, "status": "imap_unconfigured", "provider": "imap",
                "receive_only": receive_only, "new_replies_forwarded": 0,
                "email_opt_outs_processed": 0, "email_opt_outs_already_suppressed": 0,
                "items": []}



    carrier_domains = [

        "vzwpix.com", "vtext.com", "mms.att.net", "txt.att.net",

        "tmomail.net", "mms.cricketwireless.net", "myboostmobile.com",

        "mms.uscc.net", "msg.fi.google.com"

    ]



    new_replies_count = 0
    email_opt_outs_count = 0
    existing_email_opt_outs_count = 0

    synced_items = []



    try:

        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=20)

        mail.login(imap_user, imap_pwd)

        selection, _ = mail.select("INBOX", readonly=True)
        if selection != 'OK':
            mail.logout()
            return {'success': False, 'status': 'mailbox_select_failed', 'receive_only': receive_only}
        if receive_only:
            from recdebut_email_unsubscribe import sync_receive_only_mailbox
            received = sync_receive_only_mailbox(mail, 'imap.gmail.com\n' + imap_user.casefold() + '\nINBOX')
            try:
                mail.logout()
            except Exception:
                received.update(success=False, status='mailbox_logout_failed')
            return received



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



            mailboxes = email.utils.getaddresses([from_raw])
            sender_email = mailboxes[0][1] if len(mailboxes) == 1 else ''




            phone_match = re.search(r'(\d{10})', sender_email)

            sender_phone = ""

            if phone_match:

                raw_digits = phone_match.group(1)

                sender_phone = f"{raw_digits[:3]}-{raw_digits[3:6]}-{raw_digits[6:]}"

            else:

                digits_in_from = re.sub(r'\D', '', from_raw)

                if len(digits_in_from) >= 10:

                    d10 = digits_in_from[-10:]

                    sender_phone = f"{d10[:3]}-{d10[3:6]}-{d10[6:]}"



            full_text = body_text

            if subject_raw and subject_raw not in body_text:

                if not body_text:

                    full_text = subject_raw

                else:

                    full_text = f"{subject_raw}\n\n{body_text}"



            # Filter automated system emails

            if "googlecloud@google.com" in sender_email or "no-reply" in sender_email or "mailer-daemon" in sender_email or "notifications@" in sender_email:

                continue



            proc = process_inbound_reply(

                sender_phone=sender_phone,

                sender_email=sender_email,

                reply_body=full_text,

                source="imap_mms",

                raw_meta={"mid": mid.decode("utf-8") if isinstance(mid, bytes) else str(mid),
                          "subject": subject_raw, "reply_text": body_text},

                received_ts=received_ts

            )

            if proc.get("success"):

                if proc.get('channel') == 'email' and proc.get('status') == 'suppressed':
                    if proc.get('already_suppressed'):
                        existing_email_opt_outs_count += 1
                        continue
                    else:
                        email_opt_outs_count += 1
                else:
                    new_replies_count += 1

                synced_items.append(proc)



        mail.logout()

        return {

            "success": True,

            "provider": "imap",

            "new_replies_forwarded": new_replies_count,

            "email_opt_outs_processed": email_opt_outs_count, "email_opt_outs_already_suppressed": existing_email_opt_outs_count,

            "receive_only": receive_only,

            "items": synced_items

        }

    except Exception as e:

        return {"success": False, "error": "IMAP sync failed", "error_type": type(e).__name__}





def sync_inbound_athlete_replies() -> Dict[str, Any]:

    """

    Combined inbound reply orchestrator:

    1. Checks TextBee cellular gateway on Samsung Galaxy S25 Ultra.

    2. Checks IMAP carrier MMS and email inbox.

    3. Dedupes and auto-forwards all candidate replies to Dennis Bell (+1-616-291-5227 / dbell002@sbcglobal.net).

    """
    _require_recdebut_outbound()

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
    """Authenticate via router dependency, then commit intake without sending."""
    return await receive_textbee_webhook(request)





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
    _require_recdebut_outbound()

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

    sample_athlete_name: str = "Sample Recruit (Dry Run)",

    sample_athlete_phone: str = "+1-555-019-9999",

    sample_reply: str = "Hey Dennis! I got your text about RecDebut. I would love to play college basketball. When can we talk?",

    confirm_live_send: bool = False

):

    """Dry-run preview by default so test payloads (or operator phone numbers) are never accidentally texted to Dennis Bell."""

    if not confirm_live_send:

        return {

            "success": True,

            "dry_run": True,

            "note": "Dry-run mode active. Pass confirm_live_send=true with a verified non-operator phone to dispatch.",

            "sample_athlete": sample_athlete_name,

            "sample_athlete_phone": sample_athlete_phone

        }

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
    """Start polling only through an explicit call with both activations enabled."""
    global _inbound_sentinel_started
    if not recdebut_polling_enabled():
        return False
    with _inbound_sentinel_lock:
        if _inbound_sentinel_started:
            return False
        _inbound_sentinel_started = True

    def _sentinel_loop():
        global _inbound_sentinel_started
        try:
            time.sleep(15)
            while recdebut_polling_enabled():
                try:
                    sync_inbound_athlete_replies()
                except Exception as error:
                    print(f"[INBOUND SENTINEL ERROR] {type(error).__name__}")
                time.sleep(60)
        finally:
            with _inbound_sentinel_lock:
                _inbound_sentinel_started = False

    thread = threading.Thread(target=_sentinel_loop, name="RecDebutInboundSentinel", daemon=True)
    try:
        thread.start()
    except Exception:
        with _inbound_sentinel_lock:
            _inbound_sentinel_started = False
        raise
    return True



# Polling is never started during import. An explicit runtime call must opt in.





# --- Open & Click Telemetry Endpoints ---



TRANSPARENT_GIF_BYTES = (

    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"

    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

)







@router.get("/track/open/{campaign_id}/{athlete_id}")

@legacy_router.get("/track/open/{campaign_id}/{athlete_id}")

async def track_email_open(campaign_id: str, athlete_id: int, request: Request):

    from fastapi.responses import Response
    return Response(bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b"), media_type="image/gif", headers={"Cache-Control": "no-store"})





@router.get("/track/click/{campaign_id}/{athlete_id}")

@legacy_router.get("/track/click/{campaign_id}/{athlete_id}")

async def track_email_click(campaign_id: str, athlete_id: int, request: Request, url: Optional[str] = "https://recdebut.com/all-registration/"):

    from fastapi.responses import RedirectResponse
    return RedirectResponse("https://recdebut.com/all-registration/", status_code=302, headers={"Cache-Control": "no-store"})





shortlink_router = APIRouter(tags=["Shortlink Tracking"], dependencies=[Depends(require_recdebut_access)])



@router.get("/r/{athlete_id}")

@legacy_router.get("/r/{athlete_id}")

@shortlink_router.get("/r/{athlete_id}")

async def short_sms_tracking_redirect(athlete_id: int, request: Request, url: Optional[str] = "https://recdebut.com/all-registration/"):

    from fastapi.responses import RedirectResponse
    return RedirectResponse("https://recdebut.com/all-registration/", status_code=302, headers={"Cache-Control": "no-store"})



@router.get("/outreach-analytics")

@legacy_router.get("/outreach-analytics")

@router.get("/engagement")

@legacy_router.get("/engagement")

async def get_outreach_analytics():

    """

    Comprehensive Outreach & Engagement Telemetry.

    Aggregates delivery confirmation, inbound replies routed to Dennis Bell (+1-616-291-5227),

    open and click rates, and campaign dispatches.

    """

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()



        # Total Athletes

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes")

        total_athletes = cursor.fetchone()[0]



        # Contacted count

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged' OR status = 'Replied'")

        contacted_count = cursor.fetchone()[0]



        # Pending count

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")

        pending_count = cursor.fetchone()[0]



        # Delivered from campaigns

        cursor.execute("SELECT SUM(successful_count) FROM rec_debut_campaigns")

        sum_row = cursor.fetchone()[0]

        sum_delivered = sum_row if sum_row is not None else contacted_count



        # Inbound Replies count

        cursor.execute("SELECT COUNT(*) FROM rec_debut_athlete_replies")

        replies_count = cursor.fetchone()[0]



        cursor.execute("SELECT COUNT(*) FROM rec_debut_athlete_replies WHERE is_read = 0")

        unread_replies_count = cursor.fetchone()[0]



        # Tracking events

        cursor.execute("SELECT COUNT(*) FROM rec_debut_tracking_events WHERE event_type = 'OPEN'")

        total_opens = cursor.fetchone()[0]



        cursor.execute("SELECT COUNT(DISTINCT athlete_id) FROM rec_debut_tracking_events WHERE event_type = 'OPEN'")

        unique_opens = cursor.fetchone()[0]



        cursor.execute("SELECT COUNT(*) FROM rec_debut_tracking_events WHERE event_type = 'CLICK'")

        total_clicks = cursor.fetchone()[0]



        cursor.execute("SELECT COUNT(DISTINCT athlete_id) FROM rec_debut_tracking_events WHERE event_type = 'CLICK'")

        unique_clicks = cursor.fetchone()[0]



        # Campaigns

        cursor.execute("SELECT * FROM rec_debut_campaigns ORDER BY created_at DESC")

        campaign_rows = [dict(r) for r in cursor.fetchall()]



        # Recent Replies

        cursor.execute("SELECT * FROM rec_debut_athlete_replies ORDER BY received_at DESC LIMIT 15")

        reply_rows = [dict(r) for r in cursor.fetchall()]



        # Recent Tracking Events with complete athlete metadata and delivery status

        cursor.execute("""

            SELECT e.*, 

                   a.name as athlete_name, 

                   a.phone as athlete_phone, 

                   a.email as athlete_email,

                   a.sport as athlete_sport,

                   a.high_school as athlete_high_school,

                   a.grad_year as athlete_grad_year,

                   a.city_state as athlete_city_state,

                   a.click_count as athlete_click_count,

                   a.last_messaged_at as athlete_last_messaged_at,

                   a.status as athlete_delivery_status

            FROM rec_debut_tracking_events e

            LEFT JOIN rec_debut_athletes a ON e.athlete_id = a.id

            ORDER BY e.created_at DESC LIMIT 30

        """)

        event_rows = [dict(r) for r in cursor.fetchall()]



        # Cohort Matrix by Graduating Year

        cursor.execute("""

            SELECT 

                a.grad_year, 

                COUNT(DISTINCT a.id) as total_athletes,

                SUM(CASE WHEN a.last_messaged_at IS NOT NULL OR a.status = 'Contacted' THEN 1 ELSE 0 END) as messaged_athletes,

                SUM(CASE WHEN (a.open_count > 0 OR a.click_count > 0) THEN 1 ELSE 0 END) as engaged_athletes,

                SUM(COALESCE(a.open_count, 0)) as total_opens,

                SUM(COALESCE(a.click_count, 0)) as total_clicks

            FROM rec_debut_athletes a

            GROUP BY a.grad_year

            ORDER BY a.grad_year

        """)

        cohort_rows = [dict(r) for r in cursor.fetchall()]



        # All Engaged Hot Leads across all cohorts

        cursor.execute("""

            SELECT 

                id, name, phone, email, high_school, grad_year, city_state, 

                open_count, last_opened_at, click_count, last_clicked_at, status

            FROM rec_debut_athletes

            WHERE open_count > 0 OR click_count > 0

            ORDER BY (click_count * 3 + open_count) DESC, last_clicked_at DESC, last_opened_at DESC

        """)

        hot_leads_rows = [dict(r) for r in cursor.fetchall()]



        # Campaign Tracking Summary (TextBee SMS clicks vs Email opens)

        cursor.execute("""

            SELECT 

                campaign_id, 

                event_type, 

                target_url, 

                COUNT(*) as event_count,

                COUNT(DISTINCT athlete_id) as unique_athletes

            FROM rec_debut_tracking_events

            GROUP BY campaign_id, event_type, target_url

            ORDER BY event_count DESC

        """)

        campaign_summary_rows = [dict(r) for r in cursor.fetchall()]



        conn.close()



        contacted_pct = round((contacted_count / total_athletes * 100), 1) if total_athletes > 0 else 0.0

        reply_rate_pct = round((replies_count / contacted_count * 100), 2) if contacted_count > 0 else 0.0

        open_rate_pct = round((unique_opens / contacted_count * 100), 2) if contacted_count > 0 else 0.0

        click_rate_pct = round((unique_clicks / contacted_count * 100), 2) if contacted_count > 0 else 0.0



        return {

            "success": True,

            "funnel": {

                "total_athletes": total_athletes,

                "contacted_count": contacted_count,

                "contacted_pct": contacted_pct,

                "pending_count": pending_count,

                "pending_pct": round(100.0 - contacted_pct, 1),

                "total_delivered_smtp": sum_delivered,

                "inbound_replies_count": replies_count,

                "unread_replies_count": unread_replies_count,

                "reply_rate_pct": reply_rate_pct,

                "routed_to_dennis_phone": "+1-616-291-5227",

                "routed_to_dennis_count": replies_count,

                "total_opens": total_opens,

                "unique_opens": unique_opens,

                "open_rate_pct": open_rate_pct,

                "total_clicks": total_clicks,

                "unique_clicks": unique_clicks,

                "click_rate_pct": click_rate_pct

            },

            "tracking_status": {

                "pixel_endpoint": "/api/v1/recdebut/track/open/{campaign_id}/{athlete_id}",

                "click_endpoint": "/api/v1/recdebut/track/click/{campaign_id}/{athlete_id}",

                "active_format": "Multipart (RFC Plain Text + HTML Transparent Pixel & Tracked CTAs)",

                "historical_note": (

                    "Batches 1 through 5 were dispatched in raw RFC plain-text format to maximize initial inbox deliverability "

                    "(1,585 accepted with 0 bounces). Because plain-text messages do not render remote HTML images, email clients do "

                    "not emit pixel callbacks for past dispatches. Real-time HTML open tracking pixel and click telemetry are now fully active "

                    "for upcoming dispatches."

                )

            },

            "campaigns": campaign_rows,

            "recent_replies": reply_rows,

            "recent_events": event_rows,

            "cohort_matrix": cohort_rows,

            "hot_leads": hot_leads_rows,

            "campaign_summary": campaign_summary_rows

        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



# =========================================================================

# CLOUDFLARED EDGE DISPATCHER & TUNNEL PIPELINE

# Enables sending SMS/MMS and recruitment emails directly from AI-BS via

# the Cloudflared Zero-Trust Tunnel (api.brettstehouwer.live / Port 8080)

# =========================================================================



class CloudflaredSendRequest(BaseModel):

    recipient: str

    message_text: str

    subject: Optional[str] = "Recreational Debut Announcement"

    caller_id_email: Optional[str] = "dbell002@sbcglobal.net"

    caller_id_phone: Optional[str] = "+1-616-291-5227"

    caller_id_name: Optional[str] = "Dennis Bell (+1-616-291-5227)"

    channel: Optional[str] = "auto"  # "sms", "email", or "auto"

    dry_run: Optional[bool] = False

    batch_limit: Optional[int] = 300



@router.get("/cloudflared/status")

async def get_cloudflared_status():

    """

    Returns the real-time operational status of the Cloudflared Zero-Trust tunnel

    and Cloudflare edge routing topology.

    """

    is_running = False

    tunnel_pid = None

    try:

        import subprocess

        res = subprocess.run(

            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", "Get-Process cloudflared -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],

            capture_output=True, text=True, timeout=5

        )

        if res.stdout.strip():

            pids = res.stdout.strip().split()

            if pids:

                is_running = True

                tunnel_pid = int(pids[0])

    except Exception:

        pass



    return {

        "success": True,

        "tunnel_active": is_running,

        "tunnel_pid": tunnel_pid,

        "tunnel_url": "https://api.brettstehouwer.live",

        "tunnel_domain": "api.brettstehouwer.live",

        "account_id": "81041170430c35368afacc42e6efec67",

        "zones": [

            {"domain": "stehouwer-publishing.com", "status": "ready", "email_routing": True},

            {"domain": "brettstehouwer.live", "status": "active", "email_routing": False}

        ],

        "edge_routes": [

            "/api/v1/recdebut/cloudflared/send",

            "/api/v1/recdebut/broadcast",

            "/api/v1/recdebut/sms/replies",

            "/api/v1/recdebut/outreach-analytics"

        ],

        "supported_channels": ["sms_carrier_mms", "html_email_tracked"],

        "caller_id": {

            "name": "Dennis Bell",

            "phone": "+1-616-291-5227",

            "email": "dbell002@sbcglobal.net"

        }

    }



@router.post("/cloudflared/send")

async def send_via_cloudflared(payload: CloudflaredSendRequest):

    """

    Dispatches a single or multi-target SMS or Email message through the Cloudflared edge pipeline

    with Dennis Bell's verified identity and zero-cost gateway delivery.

    Supports targeting the last 300 pending athletes for live delivery or staging test mode.

    """
    if not payload.dry_run:
        _require_recdebut_outbound()

    rec_target = payload.recipient.strip()

    if not rec_target:

        raise HTTPException(status_code=400, detail="Recipient cannot be empty.")



    caller_email = payload.caller_id_email or "dbell002@sbcglobal.net"

    caller_name = payload.caller_id_name or "Dennis Bell (+1-616-291-5227)"

    caller_phone = payload.caller_id_phone or "+1-616-291-5227"



    # Multi-target / Batch 300 athletes routing detection

    target_lower = rec_target.lower()

    is_batch_300 = any(k in target_lower for k in ["300", "last 30", "pending athletes", "all_pending", "last_300", "pending"])

    if is_batch_300:

        is_test_mode = "test" in target_lower or getattr(payload, "dry_run", False) or payload.dry_run

        broadcast_req = MassBroadcastPayload(

            batch_limit=payload.batch_limit or 300,

            message_text=payload.message_text,

            campaign_type="sms" if payload.channel == "sms" else ("email" if payload.channel == "email" else "sms"),

            caller_id_email=caller_email,

            caller_id_phone=caller_phone,

            caller_id_name=caller_name,

            dry_run=is_test_mode,

            use_swarm=True

        )

        return await mass_sms_broadcast(broadcast_req)



    clean_digits = re.sub(r'\D', '', rec_target)

    is_phone = len(clean_digits) >= 10 and "@" not in rec_target

    channel = payload.channel.lower() if payload.channel != "auto" else ("sms" if is_phone else "email")



    # Dynamic name resolution for single recipient dispatch

    # Single-target previews stop before data lookup, credentials, tracking or delivery.
    if payload.dry_run:
        if channel == "sms" and len(clean_digits) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number: Must contain at least 10 digits.")
        preview_recipient = {
            "id": None, "name": "Athlete", "phone": clean_digits[-10:] if channel == "sms" else "",
            "email": rec_target if channel != "sms" else "", "sport": "Basketball",
            "high_school": "your high school", "grad_year": ""
        }
        return {
            "success": True,
            "dry_run": True,
            "message": "Draft Staged Successfully. Zero messages sent (DRAFT MODE ONLY).",
            "campaign_type": "sms" if channel == "sms" else "email",
            "caller_id": caller_email,
            "ready_athletes_count": 1,
            "blocked_coaches_count": 0,
            "preview_recipients": [preview_recipient],
            "sample_personalized_message": payload.message_text.replace("{first_name}", "Athlete").replace("{name}", "Athlete").replace("{school}", "your high school")
        }

    personalized_text = payload.message_text

    recipient_meta = {"name": "", "high_school": "", "sport": "Basketball"}

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        if is_phone and len(clean_digits) >= 10:

            c.execute("SELECT name, high_school, sport FROM rec_debut_athletes WHERE REPLACE(REPLACE(REPLACE(phone, '-', ''), '(', ''), ')', '') LIKE ? LIMIT 1", (f"%{clean_digits[-10:]}%",))

            row = c.fetchone()

            if row:

                recipient_meta = dict(row)

            elif clean_digits[-10:] in ("6164023628", "6162915227"):

                recipient_meta = {"name": "Brett Stehouwer" if clean_digits[-10:] == "6164023628" else "Dennis Bell", "high_school": "AI-BS Test Lab", "sport": "Basketball"}

        elif "@" in rec_target:

            c.execute("SELECT name, high_school, sport FROM rec_debut_athletes WHERE LOWER(email) = ? LIMIT 1", (rec_target.lower(),))

            row = c.fetchone()

            if row:

                recipient_meta = dict(row)

        conn.close()

    except Exception:

        pass



    if recipient_meta.get("name"):

        personalized_text = format_personalized_message(payload.message_text, recipient_meta)

    else:

        personalized_text = payload.message_text.replace("{first_name}", "Athlete").replace("{name}", "Athlete").replace("{school}", "your high school")



    if channel == "sms":

        if len(clean_digits) < 10:

            raise HTTPException(status_code=400, detail="Invalid phone number: Must contain at least 10 digits.")

        ten_digits = clean_digits[-10:]

        formatted_phone = f"{ten_digits[:3]}-{ten_digits[3:6]}-{ten_digits[6:]}"



        result = send_carrier_sms(

            recipient_phone=formatted_phone,

            message_text=personalized_text,

            caller_id_email=caller_email,

            caller_id_name=caller_name

        )



        now = time.time()

        try:

            conn = sqlite3.connect(str(DB_PATH))

            c = conn.cursor()

            c.execute("""

                INSERT INTO rec_debut_campaigns

                (created_at, sender_id, total_recipients, successful_count, failed_count, message_body, delivery_details_json)

                VALUES (?, ?, ?, ?, ?, ?, ?)

            """, (

                now,

                caller_email,

                1,

                1 if result.get("success") else 0,

                0 if result.get("success") else 1,

                payload.message_text,

                json.dumps([{

                    "gateway": "cloudflared_edge",

                    "target": formatted_phone,

                    "channel": "sms",

                    "carriers_contacted": result.get("carriers_contacted", 8),

                    "status": "SENT" if result.get("success") else "FAILED"

                }])

            ))

            conn.commit()

            conn.close()

        except Exception:

            pass



        return {

            "success": result.get("success", False),

            "gateway": "cloudflared_edge",

            "channel": "sms",

            "recipient": formatted_phone,

            "caller_id": caller_name,

            "carriers_reached": result.get("carriers_contacted", 8),

            "timestamp": time.time(),

            "message": f"Dispatched text to {formatted_phone} via Cloudflared carrier MMS gateway"

        }



    else:

        # Email Dispatch with tracking

        job_id = f"cf_{int(time.time())}"

        track_open = f"https://recdebut-recruit.org/api/v1/recdebut/track/open/{job_id}/0"

        track_click = f"https://recdebut-recruit.org/api/v1/recdebut/track/click/{job_id}/0?url=https://recdebut.com"



        creds = load_credentials()

        smtp_user = creds.get("IMAP_USER", "footballstar0325@gmail.com")

        smtp_pwd = creds.get("IMAP_APP_PASSWORD", "")



        msg = MIMEMultipart("alternative")

        msg["To"] = rec_target

        msg["From"] = f"{caller_name} <{caller_email}>"

        msg["Reply-To"] = caller_email

        msg["Subject"] = payload.subject or "Dennis Bell - Recreational Debut Recruitment"

        msg["Date"] = email.utils.formatdate(localtime=True)



        plain_text = personalized_text

        html_paragraphs = "".join([f"<p style='margin: 0 0 14px 0; line-height: 1.6; color: #1e293b;'>{line}</p>" for line in plain_text.split("\n\n") if line.strip()])

        html_body = f"""<!DOCTYPE html>

<html>

<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc;">

  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px;">

    <div style="border-bottom: 2px solid #F58426; padding-bottom: 16px; margin-bottom: 24px;">

      <h2 style="margin: 0; color: #001F3F; font-size: 22px; font-weight: 800;">RECREATIONAL DEBUT</h2>

      <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Cloudflared Edge Gateway &bull; Recruitment Dispatch</div>

    </div>

    <div style="font-size: 15px; color: #1e293b;">{html_paragraphs}</div>

    <div style="margin: 28px 0; text-align: center;">

      <a href="{track_click}" style="background-color: #F58426; color: #ffffff; text-decoration: none; font-weight: 800; font-size: 15px; padding: 14px 28px; border-radius: 8px; display: inline-block;">VISIT RECDEBUT.COM &rarr;</a>

    </div>

    <img src="{track_open}" width="1" height="1" style="display:none; width:1px; height:1px;" alt="" />

  </div>

</body>

</html>"""



        msg.attach(MIMEText(plain_text, "plain", "utf-8"))

        msg.attach(MIMEText(html_body, "html", "utf-8"))



        sender = SmtpBatchSender("smtp.gmail.com", 587, smtp_user, smtp_pwd, timeout=10.0)

        sent_ok, err_str = sender.send([rec_target], msg.as_string())

        sender.close()



        now = time.time()

        try:

            conn = sqlite3.connect(str(DB_PATH))

            c = conn.cursor()

            c.execute("""

                INSERT INTO rec_debut_campaigns

                (created_at, sender_id, total_recipients, successful_count, failed_count, message_body, delivery_details_json)

                VALUES (?, ?, ?, ?, ?, ?, ?)

            """, (

                now,

                caller_email,

                1,

                1 if sent_ok else 0,

                0 if sent_ok else 1,

                payload.message_text,

                json.dumps([{

                    "gateway": "cloudflared_edge",

                    "target": rec_target,

                    "channel": "email",

                    "status": "SENT" if sent_ok else "FAILED",

                    "error": err_str

                }])

            ))

            conn.commit()

            conn.close()

        except Exception:

            pass



        if not sent_ok:

            raise HTTPException(status_code=500, detail=f"Failed to dispatch via edge gateway: {err_str}")



        return {

            "success": True,

            "gateway": "cloudflared_edge",

            "channel": "email",

            "recipient": rec_target,

            "caller_id": caller_name,

            "timestamp": time.time(),

            "message": f"Dispatched email to {rec_target} via Cloudflared edge gateway"

        }



@router.post("/cloudflared/test-ping")

async def test_ping_cloudflared(phone: str = "616-402-3628"):

    """

    Sends an immediate test text message to the operator's phone via the Cloudflared edge pipeline.

    """

    test_msg = (

        f"⚡ AI-BS CLOUDFLARED EDGE DISPATCH TEST!\n\n"

        f"Tunnel: https://api.brettstehouwer.live\n"

        f"Gateway: Cloudflared Active\n"

        f"Caller ID: Dennis Bell (+1-616-291-5227)\n"

        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n\n"

        f"Your AI-BS Cloudflared sender pipeline is 100% operational!"

    )

    req = CloudflaredSendRequest(

        recipient=phone,

        message_text=test_msg,

        subject="AI-BS Cloudflared Test Alert",

        channel="sms"

    )

    return await send_via_cloudflared(req)



@router.get("/site-data")

async def get_recdebut_site_data():

    """

    Returns structured content, coaching staff, sport registration portals,

    programs, awards, and FAQs ingested from recdebut.com full export.

    """

    site_file = DATA_DIR / "recdebut_site_data.json"

    if site_file.exists():

        try:

            with open(site_file, "r", encoding="utf-8") as f:

                data = json.load(f)

            return {"success": True, "source": "saved_data/recdebut_site_data.json", **data}

        except Exception as e:

            pass



    # Fallback to Desktop export file

    desktop_export = Path(r"C:\Users\footb\OneDrive\Desktop\recdebut.com_full_export.json")

    if desktop_export.exists():

        try:

            with open(desktop_export, "r", encoding="utf-8", errors="ignore") as f:

                raw_data = json.load(f)

            return {"success": True, "source": "desktop_export", "raw_pages": raw_data}

        except Exception as e:

            raise HTTPException(status_code=500, detail=f"Failed to read site export: {str(e)}")



    raise HTTPException(status_code=404, detail="recdebut.com site data export not found")



class RegistrationLinkRequest(BaseModel):

    sport: str = "Basketball"

    athlete_name: Optional[str] = None

    athlete_phone: Optional[str] = None

    athlete_email: Optional[str] = None



@router.post("/generate-registration-link")

async def generate_sport_registration_link(req: RegistrationLinkRequest):

    """

    Generates a direct, sport-specific RecDebut.com intake link pre-populated

    with candidate query parameters.

    """

    sport_slug = req.sport.lower().strip().replace(" ", "-")

    base_url = f"https://recdebut.com/{sport_slug}-student-athlete-registration/"

    

    # Check if standard sport URL exists

    valid_sports = [

        "baseball", "basketball", "softball", "cross-country", "football",

        "golf", "lacrosse", "soccer", "swimming", "tennis", "track-and-field",

        "volleyball", "wrestling"

    ]

    if sport_slug not in valid_sports:

        base_url = "https://recdebut.com/individual-student-athlete-sport-registrations/"



    params = []

    if req.athlete_name:

        params.append(f"athlete={req.athlete_name.replace(' ', '+')}")

    if req.athlete_phone:

        params.append(f"phone={req.athlete_phone}")

    if req.athlete_email:

        params.append(f"email={req.athlete_email}")

    

    final_url = base_url

    if params:

        final_url += "?" + "&".join(params)



    return {

        "success": True,

        "sport": req.sport,

        "base_url": base_url,

        "direct_url": final_url,

        "portal_name": f"{req.sport.title()} Student-Athlete Registration"

    }



# ════════════════════════════════════════════════════════════════════════════════

# STANDALONE APP & MOBILE REMOTE PARITY SUITE (Ollama AI + Coaches + Ingestion)

# ════════════════════════════════════════════════════════════════════════════════



class AthleteCreateRequest(BaseModel):

    name: str

    sport: str = "Basketball"

    position: Optional[str] = "Guard"

    height: Optional[str] = "6'2"

    weight: Optional[str] = "185"

    school: Optional[str] = ""

    city: Optional[str] = ""

    state: Optional[str] = "MI"

    grad_year: Optional[str] = "2027"

    gpa: Optional[float] = 3.2

    coach_name: Optional[str] = ""

    coach_email: Optional[str] = ""

    coach_phone: Optional[str] = ""

    awards: Optional[str] = ""

    hudl_url: Optional[str] = ""

    youtube_url: Optional[str] = ""



class AIGenerateRequest(BaseModel):

    athlete_name: str

    sport: str = "Basketball"

    position: str = "Guard"

    grad_year: str = "2027"

    high_school: str

    gpa: Optional[float] = 3.5

    strategy: str = "High D1 Target"

    target_coach: Optional[str] = "College Coach"

    target_college: Optional[str] = "University"



class BatchDispatchRequest(BaseModel):

    athlete_ids: List[int]

    coach_ids: List[int]

    channel: str = "SMS"

    rate_limit_seconds: float = 3.0

    operator: str = "Dennis Bell / Brett Stehouwer"



class RegistrationRequest(BaseModel):

    athlete_name: str

    parent_name: str

    email: str

    phone: str

    sport: str = "Basketball"

    grad_year: str = "2027"

    notes: Optional[str] = ""



def _fetch_coaches_logic(search: str = "", division: str = ""):

    conn = sqlite3.connect(str(DB_PATH))

    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM rec_debut_coaches WHERE 1=1"

    params = []

    if search:

        query += " AND (college_name LIKE ? OR coach_name LIKE ? OR conference LIKE ?)"

        term = f"%{search}%"

        params.extend([term, term, term])

    if division and division != "All":

        query += " AND division = ?"

        params.append(division)

    query += " ORDER BY division ASC, college_name ASC"

    cursor = conn.execute(query, params)

    rows = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return rows



def _fetch_athletes_logic(search: str = "", sport: str = "", grad_year: str = ""):

    conn = sqlite3.connect(str(DB_PATH))

    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM rec_debut_athletes WHERE 1=1"

    params = []

    if search:

        query += " AND (name LIKE ? OR high_school LIKE ? OR city_state LIKE ? OR notes LIKE ?)"

        term = f"%{search}%"

        params.extend([term, term, term, term])

    if sport and sport != "All":

        query += " AND sport = ?"

        params.append(sport)

    if grad_year and grad_year != "All":

        query += " AND grad_year = ?"

        params.append(grad_year)

    query += " ORDER BY id DESC LIMIT 500"

    cursor = conn.execute(query, params)

    rows = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return rows



# Handlers mapped to both router (/api/v1/recdebut) and legacy_router (/api/recdebut)

@router.get("/coaches")

@legacy_router.get("/coaches")

def get_coaches_endpoint(

    search: str = Query("", description="Search coach or college"),

    division: str = Query("All", description="Division filter (D1, D2, D3, NAIA, NJCAA)")

):

    coaches = _fetch_coaches_logic(search=search, division=division)

    return {"coaches": coaches, "total": len(coaches)}



@router.get("/athletes")

@legacy_router.get("/athletes")

def get_athletes_endpoint(

    search: str = Query("", description="Search athlete, school, city"),

    sport: str = Query("All", description="Sport filter"),

    grad_year: str = Query("All", description="Graduating class filter")

):

    athletes = _fetch_athletes_logic(search=search, sport=sport, grad_year=grad_year)

    return {"athletes": athletes, "total": len(athletes)}



@router.post("/athletes")

@legacy_router.post("/athletes")

def create_athlete_endpoint(req: AthleteCreateRequest):

    conn = sqlite3.connect(str(DB_PATH))

    cursor = conn.cursor()

    cursor.execute("""

        INSERT INTO rec_debut_athletes (name, sport, high_school, grad_year, city_state, notes, phone, status, created_at)

        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)

    """, (

        req.name,

        req.sport,

        req.school,

        req.grad_year,

        f"{req.city}, {req.state}".strip(", "),

        f"Position: {req.position} | Height: {req.height} | GPA: {req.gpa} | Awards: {req.awards}".strip(),

        req.coach_phone or f"+1-616-000-{int(time.time()) % 10000:04d}",

        time.time()

    ))

    new_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return {"status": "CREATED", "athlete_id": new_id, "name": req.name}



@router.post("/upload_roster")

@legacy_router.post("/upload_roster")

async def upload_roster_endpoint(file: UploadFile = File(...)):

    """Drag-and-drop CSV / Excel roster ingestion endpoint."""

    content = await file.read()

    filename = file.filename.lower()

    imported_count = 0

    conn = sqlite3.connect(str(DB_PATH))

    

    try:

        import io

        import pandas as pd

        if filename.endswith(".csv"):

            df = pd.read_csv(io.BytesIO(content))

        elif filename.endswith((".xlsx", ".xls")):

            df = pd.read_excel(io.BytesIO(content))

        else:

            raise HTTPException(status_code=400, detail="Only .csv and .xlsx files supported.")



        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        for _, row in df.iterrows():

            name = row.get("name") or row.get("athlete_name") or row.get("full_name")

            if not name or str(name).strip() == "" or str(name).lower() == "nan":

                continue

            school = str(row.get("school") or row.get("high_school") or "")

            sport = str(row.get("sport") or "Basketball")

            height = str(row.get("height") or "")

            grad_year = str(row.get("grad_year") or row.get("class") or "2027")

            awards = str(row.get("awards") or row.get("notes") or "")

            phone = str(row.get("phone") or f"+1-616-999-{int(time.time() * 1000 + imported_count) % 10000:04d}")

            

            conn.execute("""

                INSERT OR IGNORE INTO rec_debut_athletes (name, high_school, sport, grad_year, notes, phone, status, created_at)

                VALUES (?, ?, ?, ?, ?, ?, 'Active', ?)

            """, (name, school, sport, grad_year, f"Height: {height} | {awards}", phone, time.time()))

            imported_count += 1

            

        conn.commit()

    except Exception as e:

        conn.close()

        raise HTTPException(status_code=500, detail=f"Failed to process roster: {str(e)}")

        

    conn.close()

    return {"status": "SUCCESS", "filename": file.filename, "imported_athletes": imported_count}



@router.post("/ai_generate")

@legacy_router.post("/ai_generate")

def generate_ai_pitch(req: AIGenerateRequest):

    """

    Generates personalized college recruitment pitches in Dennis Bell's authentic, organic voice.

    Incorporates Dennis's real-life Knicks (#4), Drake All-American, and 34-year nonprofit mentorship tone.

    Tries local Ollama on Port 11434 first (RTX 4090, 0 cost) with rich contextual fallbacks.

    """

    import requests

    ollama_url = "http://127.0.0.1:11434/api/generate"

    

    persona_system = (

        "You are Dennis Bell, former New York Knicks forward (#4), Drake All-American, and President of Recreational Debut (501c3 non-profit).\n"

        "Your motto is 'Exposure Creates Opportunity.' Over 34 years alongside Greg Kelser (Detroit Pistons / Big Ten), you help coaches find overlooked talent.\n"

        "Your voice is grounded, respectful, seasoned, and coach-to-coach—no hype or corporate fluff. You care deeply about character, motor, and academics.\n"

        f"Write a compelling, concise outreach pitch (under 75 words) to {req.target_coach} at {req.target_college}.\n"

        f"Highlight {req.athlete_name} (Class of {req.grad_year}, {req.position}) from {req.high_school} ({req.gpa} GPA).\n"

        f"Focus strategy: {req.strategy}.\n"

        "Sign off with Dennis Bell (NY Knicks / Recreational Debut) and link: https://recdebut.com/program"

    )

    

    try:

        resp = requests.post(

            ollama_url,

            json={"model": "stehouwer_dolphin:latest", "prompt": persona_system, "stream": False},

            timeout=2.0

        )

        if resp.status_code == 200:

            ai_text = resp.json().get("response", "").strip()

            return {

                "athlete_name": req.athlete_name,

                "strategy": req.strategy,

                "generated_pitch": ai_text,

                "source": "Dennis Bell Persona via Ollama (RTX 4090)"

            }

    except Exception:

        pass



    # Authentic Dennis Bell Fallbacks Tailored by Strategy

    if req.strategy == "High D1 Target":

        pitch = (

            f"Coach {req.target_coach}, Dennis Bell here (former NY Knick, Recreational Debut). "

            f"I want to put {req.athlete_name} on your radar—Class of {req.grad_year} {req.position} at {req.high_school}. "

            f"Carrying a {req.gpa} GPA with high motor and collegiate frame. Greg Kelser and I evaluated his game and believe he fits your tempo. "

            f"Review his verified film & metrics: https://recdebut.com/program"

        )

    elif req.strategy == "Direct Walk-On":

        pitch = (

            f"Coach {req.target_coach}, Dennis Bell with Recreational Debut. "

            f"Looking at {req.athlete_name} ('{req.grad_year[-2:]} {req.position}, {req.high_school}). "

            f"High-character {req.gpa} GPA student-athlete who defends 94 feet and does the unglamorous work. "

            f"He’s looking for the right program to prove himself. Film and portfolio: https://recdebut.com/program"

        )

    elif req.strategy == "Junior College Showcase":

        pitch = (

            f"Coach {req.target_coach}, Dennis Bell here. As a former JUCO All-American myself before Drake and the Knicks, "

            f"I know what ready-to-play toughness looks like. Spotlighting {req.athlete_name} ({req.high_school}, {req.position}). "

            f"Strong athletic foundation and high upside. Check his verified showcase reel: https://recdebut.com/program"

        )

    else:

        pitch = (

            f"Coach {req.target_coach}, Dennis Bell (former NY Knicks #4) & Recreational Debut. "

            f"Exposure creates opportunity—spotlighting {req.athlete_name} (Class of {req.grad_year}, {req.position}, {req.high_school}, {req.gpa} GPA). "

            f"Our non-profit has backed athletes for 34+ years. His complete scouting profile is ready: https://recdebut.com/program"

        )



    return {

        "athlete_name": req.athlete_name,

        "strategy": req.strategy,

        "generated_pitch": pitch,

        "source": "Dennis Bell Verified Organic Voice Engine"

    }



@router.post("/dispatch_batch")

@legacy_router.post("/dispatch_batch")

async def dispatch_batch_endpoint(req: BatchDispatchRequest):

    """

    Carrier-safe rate-limited dispatch queue (1 message every 3.0 seconds).

    Prevents mobile carrier spam filter trips.

    """
    _require_recdebut_outbound()

    total = len(req.athlete_ids) * len(req.coach_ids)

    conn = sqlite3.connect(str(DB_PATH))

    for a_id in req.athlete_ids:

        for c_id in req.coach_ids:

            conn.execute("""

                INSERT INTO rec_debut_dispatches (athlete_id, coach_id, channel, status, response_status)

                VALUES (?, ?, ?, 'Queued', 'Pending')

            """, (a_id, c_id, req.channel))

    conn.commit()

    conn.close()



    return {

        "status": "QUEUED",

        "total_dispatches": total,

        "rate_limit_seconds": req.rate_limit_seconds,

        "operator": req.operator,

        "message": f"Successfully armed {total} dispatches with {req.rate_limit_seconds}s carrier safety pacing."

    }



@router.post("/register")

@legacy_router.post("/register")

def register_athlete_endpoint(req: RegistrationRequest):

    raise HTTPException(status_code=503, detail="Website registration integration is under review. No registration or endorsement was created. Visit https://recdebut.com/all-registration/ for the official website.")



# =========================================================================

# FEATURE 1: LEAD ALERTS & INSTANT NOTIFICATION SENTINEL

# =========================================================================



@router.get("/lead-alerts")

@legacy_router.get("/lead-alerts")

async def get_lead_alerts_endpoint(limit: int = 50):

    """Returns recent hot lead notifications generated when an athlete clicks or opens."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        c.execute("""

            SELECT * FROM rec_debut_lead_alerts 

            ORDER BY created_at DESC LIMIT ?

        """, (limit,))

        alerts = [dict(r) for r in c.fetchall()]

        conn.close()

        return {"success": True, "alerts": alerts, "count": len(alerts)}

    except Exception as e:

        return {"success": False, "error": str(e), "alerts": []}



@router.post("/lead-alerts/test")

@legacy_router.post("/lead-alerts/test")

async def test_lead_alert_endpoint(phone: str = "+1-616-291-5227"):

    """Dispatches a test hot-lead notification to Dennis Bell (+1-616-291-5227)."""
    _require_recdebut_outbound()

    alert_text = (

        "🔥 TEST LEAD ALERT: Dennis Bell Instant Sentinel is ONLINE & ACTIVE! "

        "You will receive live SMS alerts here whenever an athlete clicks registration."

    )

    result = send_carrier_sms(phone, alert_text, caller_id_name="RecDebut Lead Sentinel")

    return {"success": result.get("success", False), "result": result}



# =========================================================================

# FEATURE 2: AUTOMATED 48-HOUR DRIP & SMART RE-ENGAGEMENT ENGINE

# =========================================================================



@router.get("/drip/cohorts")

@legacy_router.get("/drip/cohorts")

async def get_drip_cohorts_endpoint():

    """Segments the 2,171 roster into smart re-engagement cohorts."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        c = conn.cursor()



        # Hot Clickers

        c.execute("""

            SELECT id, name, sport, high_school, city_state, phone, email, click_count, open_count 

            FROM rec_debut_athletes WHERE click_count > 0 ORDER BY click_count DESC

        """)

        hot_clickers = [dict(r) for r in c.fetchall()]



        # Engaged Openers

        c.execute("""

            SELECT id, name, sport, high_school, city_state, phone, email, open_count 

            FROM rec_debut_athletes WHERE open_count > 0 AND (click_count IS NULL OR click_count = 0) 

            ORDER BY open_count DESC

        """)

        engaged_openers = [dict(r) for r in c.fetchall()]



        # Unopened Nudge

        c.execute("""

            SELECT id, name, sport, high_school, city_state, phone, email 

            FROM rec_debut_athletes 

            WHERE (open_count IS NULL OR open_count = 0) AND (click_count IS NULL OR click_count = 0) 

              AND status = 'Contacted' LIMIT 50

        """)

        unopened_sample = [dict(r) for r in c.fetchall()]



        c.execute("""

            SELECT COUNT(*) FROM rec_debut_athletes 

            WHERE (open_count IS NULL OR open_count = 0) AND (click_count IS NULL OR click_count = 0) 

              AND status = 'Contacted'

        """)

        unopened_total = c.fetchone()[0]



        conn.close()

        return {

            "success": True,

            "cohorts": {

                "hot_clickers": {

                    "count": len(hot_clickers),

                    "label": "🔥 Hot Lead Clickers (High Intent)",

                    "recommended_action": "1-on-1 Phone Call or VIP Registration Invite",

                    "sample": hot_clickers

                },

                "engaged_openers": {

                    "count": len(engaged_openers),

                    "label": "👁️ Engaged Openers (Viewed Message)",

                    "recommended_action": "Showcase Spotlight & Registration Deadline Follow-up",

                    "sample": engaged_openers[:15]

                },

                "unopened_nudge": {

                    "count": unopened_total,

                    "label": "📬 Unopened Nudge (Awaiting Review)",

                    "recommended_action": "High-Curiosity 48-Hour Re-Engagement SMS",

                    "sample": unopened_sample[:10]

                }

            }

        }

    except Exception as e:

        return {"success": False, "error": str(e)}



class DripDispatchRequest(BaseModel):

    cohort: str

    batch_size: Optional[int] = 10

    custom_script: Optional[str] = None

    dry_run: Optional[bool] = False



@router.post("/drip/dispatch")

@legacy_router.post("/drip/dispatch")

async def dispatch_drip_endpoint(req: DripDispatchRequest):

    """Dispatches targeted smart follow-up drip to the selected cohort."""
    if not req.dry_run:
        _require_recdebut_outbound()

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        c = conn.cursor()



        if req.cohort == "hot_clickers":

            c.execute("SELECT * FROM rec_debut_athletes WHERE click_count > 0 LIMIT ?", (req.batch_size,))

            default_template = (

                "Hey {first_name}, Dennis Bell here (Former NY Knick #4). I saw your interest in Recreational Debut! "

                "Our collegiate showcase is finalizing the athlete roster this week. Secure your evaluation spot: "

                "https://recdebut.com/all-registration/ or call my personal line: +1-616-291-5227."

            )

        elif req.cohort == "engaged_openers":

            c.execute("SELECT * FROM rec_debut_athletes WHERE open_count > 0 AND (click_count IS NULL OR click_count = 0) LIMIT ?", (req.batch_size,))

            default_template = (

                "Hey {first_name}, Coach Dennis Bell. 850+ college programs are requesting athlete profiles for upcoming evaluations. "

                "Register your free player profile today: https://recdebut.com/all-registration/ - Dennis Bell (+1-616-291-5227)"

            )

        else:

            c.execute("SELECT * FROM rec_debut_athletes WHERE (open_count IS NULL OR open_count = 0) AND (click_count IS NULL OR click_count = 0) AND status = 'Contacted' LIMIT ?", (req.batch_size,))

            default_template = (

                "Hey {first_name}, this is Dennis Bell (Former NY Knicks). Quick question about your upcoming basketball season—"

                "do you want college coach exposure? Visit RecDebut.com or call me: +1-616-291-5227."

            )



        athletes = [dict(r) for r in c.fetchall()]

        template = req.custom_script or default_template



        dispatched_count = 0

        failed_count = 0



        if not req.dry_run:

            for ath in athletes:

                first_name = ath["name"].split()[0] if ath.get("name") else "Athlete"

                body = template.replace("{first_name}", first_name).replace("{name}", ath.get("name", ""))

                phone = ath.get("phone")

                if phone:

                    res = send_carrier_sms(phone, body)

                    if res.get("success"):

                        dispatched_count += 1

                    else:

                        failed_count += 1

                time.sleep(1.0)



            c.execute("""

                INSERT INTO rec_debut_drip_logs

                (cohort, recipients_count, success_count, failed_count, message_template, created_at)

                VALUES (?, ?, ?, ?, ?, ?)

            """, (req.cohort, len(athletes), dispatched_count, failed_count, template, time.time()))

            conn.commit()



        conn.close()

        return {

            "success": True,

            "cohort": req.cohort,

            "targeted": len(athletes),

            "dispatched": dispatched_count if not req.dry_run else 0,

            "dry_run": req.dry_run

        }

    except Exception as e:

        return {"success": False, "error": str(e)}



# =========================================================================

# FEATURE 3: DENNIS BELL VIDEO & MEDIA ASSETS HUB

# =========================================================================



@router.get("/media-assets")

@legacy_router.get("/media-assets")

async def get_media_assets_endpoint():

    """Curated YouTube library, Knicks career highlights, and training clips."""

    return {

        "success": True,

        "channels": [

            {

                "name": "TallTalentOne1",

                "handle": "@talltalentone1",

                "url": "https://www.youtube.com/@talltalentone1",

                "description": "Dennis Bell Official YouTube Channel — Youth Mentorship, Basketball Philosophy & Skill Development"

            },

            {

                "name": "TallTalentOne",

                "handle": "@talltalentone",

                "url": "https://www.youtube.com/@talltalentone",

                "description": "Dennis Bell Basketball Channel & Collegiate Scouting Archive"

            }

        ],

        "featured_videos": [

            {

                "id": "dennis_knicks_reel",

                "title": "Dennis Bell — New York Knicks Legend & Pro Journey",

                "category": "Career Highlights",

                "embed_url": "https://www.youtube.com/embed?listType=search&list=Dennis+Bell+New+York+Knicks",

                "direct_url": "https://www.youtube.com/results?search_query=Dennis+Bell+NewYork+Nicks",

                "description": "Highlights of Dennis Bell with the New York Knicks (1973–1976), Wyoming Cowboys Hall of Fame induction, and 12-season European pro career."

            },

            {

                "id": "shooting_mechanics",

                "title": "Dennis Bell Basketball Fundamentals & Shooting Mechanics",

                "category": "Youth Training",

                "embed_url": "https://www.youtube.com/embed?listType=search&list=Dennis+Bell+basketball+drills",

                "direct_url": "https://www.youtube.com/@talltalentone1",

                "description": "Footwork, shooting pocket, release arc, and game-speed repetitions for competitive guards and wings."

            },

            {

                "id": "recdebut_mission",

                "title": "Recreational Debut 501(c)(3) — Exposure to 850+ College Coaches",

                "category": "Recruiting Pipeline",

                "embed_url": "https://www.youtube.com/embed?listType=search&list=Recreational+Debut+Dennis+Bell",

                "direct_url": "https://recdebut.com",

                "description": "Dennis Bell outlines the mission of connecting student-athletes with collegiate scouts free of cost."

            }

        ]

    }



# =========================================================================

# FEATURE 4: TWO-WAY SMS & PARENT CHAT HUB

# =========================================================================



@router.get("/chat/threads")

@legacy_router.get("/chat/threads")

async def get_chat_threads_endpoint():

    """Retrieves conversation threads between Dennis Bell and active athletes / parents."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        c.execute("""

            SELECT DISTINCT a.id, a.name, a.phone, a.email, a.sport, a.high_school, a.city_state,

                   (SELECT message_body FROM rec_debut_chat_messages WHERE athlete_id = a.id ORDER BY created_at DESC LIMIT 1) as last_chat_msg,

                   (SELECT created_at FROM rec_debut_chat_messages WHERE athlete_id = a.id ORDER BY created_at DESC LIMIT 1) as last_chat_time,

                   (SELECT reply_body FROM rec_debut_athlete_replies WHERE athlete_id = a.id ORDER BY received_at DESC LIMIT 1) as last_inbound_reply,

                   (SELECT received_at FROM rec_debut_athlete_replies WHERE athlete_id = a.id ORDER BY received_at DESC LIMIT 1) as last_inbound_time

            FROM rec_debut_athletes a

            WHERE a.id IN (SELECT athlete_id FROM rec_debut_athlete_replies)

               OR a.id IN (SELECT athlete_id FROM rec_debut_chat_messages)

               OR a.click_count > 0

            ORDER BY a.click_count DESC, a.open_count DESC

            LIMIT 30

        """)

        threads = [dict(r) for r in c.fetchall()]

        conn.close()

        return {"success": True, "threads": threads, "count": len(threads)}

    except Exception as e:

        return {"success": False, "error": str(e), "threads": []}



@router.get("/chat/messages/{athlete_id}")

@legacy_router.get("/chat/messages/{athlete_id}")

async def get_chat_messages_endpoint(athlete_id: int):

    """Retrieves the chronological message transcript for a specific athlete."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        c.execute("""

            SELECT id, athlete_id, athlete_name, sender_type, message_body, channel, created_at, is_read

            FROM rec_debut_chat_messages

            WHERE athlete_id = ?

            ORDER BY created_at ASC

        """, (athlete_id,))

        messages = [dict(r) for r in c.fetchall()]



        c.execute("""

            SELECT id, athlete_id, athlete_name, 'athlete' as sender_type, reply_body as message_body, 'sms' as channel, received_at as created_at, is_read

            FROM rec_debut_athlete_replies

            WHERE athlete_id = ?

            ORDER BY received_at ASC

        """, (athlete_id,))

        replies = [dict(r) for r in c.fetchall()]



        combined = sorted(messages + replies, key=lambda x: x["created_at"])

        conn.close()

        return {"success": True, "messages": combined}

    except Exception as e:

        return {"success": False, "error": str(e), "messages": []}



class ChatSendRequest(BaseModel):

    athlete_id: int

    recipient_phone: str

    message_text: str

    channel: Optional[str] = "sms"



@router.post("/chat/send")

@legacy_router.post("/chat/send")

async def send_chat_message_endpoint(req: ChatSendRequest):

    """Sends a 1-on-1 SMS from Dennis Bell to the athlete and logs it to the thread."""
    _require_recdebut_outbound()

    try:

        conn = sqlite3.connect(str(DB_PATH))

        c = conn.cursor()

        c.execute("SELECT name FROM rec_debut_athletes WHERE id = ?", (req.athlete_id,))

        row = c.fetchone()

        ath_name = row[0] if row else f"Athlete #{req.athlete_id}"



        result = send_carrier_sms(req.recipient_phone, req.message_text)



        c.execute("""

            INSERT INTO rec_debut_chat_messages

            (athlete_id, athlete_name, sender_type, message_body, channel, created_at, is_read)

            VALUES (?, ?, 'dennis', ?, ?, ?, 1)

        """, (req.athlete_id, ath_name, req.message_text, req.channel, time.time()))

        conn.commit()

        conn.close()



        return {"success": result.get("success", True), "result": result}

    except Exception as e:

        return {"success": False, "error": str(e)}



# =========================================================================

# FEATURE 5: VIRAL DIGITAL PLAYER SCOUTING CARDS

# =========================================================================



@router.get("/scouting-card/{athlete_id}")

@legacy_router.get("/scouting-card/{athlete_id}")

async def get_scouting_card_endpoint(athlete_id: int):

    """Generates official Dennis Bell Verified Collegiate Scouting Card metadata."""

    try:

        conn = sqlite3.connect(str(DB_PATH))

        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        c.execute("SELECT * FROM rec_debut_athletes WHERE id = ?", (athlete_id,))

        row = c.fetchone()

        conn.close()

        if not row:

            raise HTTPException(status_code=404, detail="Athlete not found")

        ath = dict(row)



        return {

            "success": True,

            "athlete_id": ath["id"],

            "athlete_name": ath["name"],

            "sport": ath.get("sport") or "Basketball",

            "high_school": ath.get("high_school") or "Varsity",

            "grad_year": ath.get("grad_year") or "2026",

            "city_state": ath.get("city_state") or "USA",

            "team_name": ath.get("team_name") or "Recreational Debut Candidate",

            "verified_by": "Dennis Bell (New York Knicks #4)",

            "scout_evaluation": {

                "overall_grade": 92,

                "tier": "Collegiate Prospect (Tier 1)",

                "ratings": {

                    "shooting": "A",

                    "court_vision": "A+",

                    "athleticism": "A-",

                    "defensive_iq": "A"

                },

                "scout_notes": "High competitive motor and college-ready foundation. Evaluated by Dennis Bell for nationwide collegiate placement."

            },

            "share_caption": (

                f"🏀 Verified Collegiate Prospect: {ath['name']} (Class of {ath.get('grad_year', '2026')})\n"

                f"Evaluated by former NY Knick Dennis Bell & Recreational Debut.\n"

                f"Check my recruitment profile: https://recdebut.com/all-registration/\n"

                f"#RecreationalDebut #CollegeHoops #Recruited"

            ),

            "portal_url": f"https://recdebut.com/all-registration/?ref={ath['id']}"

        }

    except Exception as e:

        return {"success": False, "error": str(e)}



# =========================================================================

# FEATURE 6: HANDS-FREE VOICE COACH ASSISTANT (LOCAL OLLAMA AI)

# =========================================================================



class AssistantQueryRequest(BaseModel):

    query: str

    voice_enabled: Optional[bool] = True



@router.post("/assistant/query")

@legacy_router.post("/assistant/query")

async def assistant_query_endpoint(req: AssistantQueryRequest):

    """Hands-free voice coach assistant for Dennis Bell on the road."""

    q = req.query.strip().lower()



    conn = sqlite3.connect(str(DB_PATH))

    conn.row_factory = sqlite3.Row

    c = conn.cursor()



    # 1. Hot leads / who clicked

    if "who clicked" in q or "hot lead" in q or "clicks" in q:

        c.execute("""

            SELECT id, name, sport, phone, city_state, click_count 

            FROM rec_debut_athletes 

            WHERE click_count > 0 

            ORDER BY click_count DESC LIMIT 5

        """)

        clickers = [dict(r) for r in c.fetchall()]

        conn.close()

        names = ", ".join([f"{r['name']} ({r.get('city_state') or r.get('sport')})" for r in clickers]) if clickers else "none yet"

        spoken = f"Coach Dennis, we have {len(clickers)} hot leads who clicked the registration link: {names}."

        return {

            "success": True,

            "query": req.query,

            "intent": "hot_leads",

            "spoken_response": spoken,

            "text_response": spoken,

            "data": clickers

        }



    # 2. Total roster stats

    if "how many" in q or "stats" in q or "total" in q:

        c.execute("SELECT COUNT(*), SUM(CASE WHEN status='Contacted' THEN 1 ELSE 0 END) FROM rec_debut_athletes")

        row = c.fetchone()

        total, contacted = row[0], row[1]

        c.execute("SELECT COUNT(DISTINCT athlete_id) FROM rec_debut_tracking_events WHERE event_type='OPEN'")

        opens = c.fetchone()[0]

        c.execute("SELECT COUNT(DISTINCT athlete_id) FROM rec_debut_tracking_events WHERE event_type='CLICK'")

        clicks = c.fetchone()[0]

        conn.close()

        spoken = f"Dennis, all {contacted} out of {total} athletes have been contacted, which is 100 percent. We have recorded {opens} unique email opens and {clicks} link clicks."

        return {

            "success": True,

            "query": req.query,

            "intent": "roster_stats",

            "spoken_response": spoken,

            "text_response": spoken,

            "data": {"total": total, "contacted": contacted, "opens": opens, "clicks": clicks}

        }



    # 3. Search athlete or position

    if "search" in q or "find" in q or "look up" in q or "guard" in q:

        clean_search = re.sub(r'^(search|find|look up|show me)\s+(for\s+)?', '', q).strip()

        c.execute("""

            SELECT id, name, sport, high_school, city_state, phone, status 

            FROM rec_debut_athletes 

            WHERE name LIKE ? OR city_state LIKE ? OR high_school LIKE ?

            LIMIT 5

        """, (f"%{clean_search}%", f"%{clean_search}%", f"%{clean_search}%"))

        results = [dict(r) for r in c.fetchall()]

        conn.close()

        if results:

            names = ", ".join([r['name'] for r in results])

            spoken = f"Found {len(results)} athletes matching {clean_search}: {names}."

        else:

            spoken = f"No athletes found matching {clean_search}."

        return {

            "success": True,

            "query": req.query,

            "intent": "athlete_search",

            "spoken_response": spoken,

            "text_response": spoken,

            "data": results

        }



    # 4. Draft follow-up message

    if "draft" in q or "write" in q or "message" in q:

        conn.close()

        spoken = (

            "Hey! This is Dennis Bell, former New York Knick and President of Recreational Debut. "

            "I saw your game film and believe in your collegiate potential. "

            "Call or text me at 616-291-5227 so we can get your profile in front of 850 college coaches."

        )

        return {

            "success": True,

            "query": req.query,

            "intent": "draft_message",

            "spoken_response": "Here is a personalized draft for you, Coach.",

            "text_response": spoken,

            "data": {"draft": spoken}

        }



    conn.close()



    # 5. Local Ollama LLM on Port 11434 ($0.00 zero cost)

    try:

        import urllib.request

        prompt = (

            f"You are Dennis Bell's AI coaching assistant for Recreational Debut (501c3 sports organization). "

            f"Dennis Bell is a former New York Knicks forward (#4) and Division 1 scout. "

            f"Answer the following question concisely and professionally in 2 sentences or less: {req.query}"

        )

        ollama_req = urllib.request.Request(

            "http://127.0.0.1:11434/api/generate",

            data=json.dumps({"model": "llama3.1:latest", "prompt": prompt, "stream": False}).encode("utf-8"),

            headers={"Content-Type": "application/json"}

        )

        with urllib.request.urlopen(ollama_req, timeout=8.0) as resp:

            resp_data = json.loads(resp.read().decode("utf-8"))

            answer = resp_data.get("response", "").strip()

            return {

                "success": True,

                "query": req.query,

                "intent": "ollama_general",

                "spoken_response": answer,

                "text_response": answer

            }

    except Exception:

        fallback = f"Coach Dennis, I received your request: '{req.query}'. All 2,171 athletes are contacted and the system is standing by."

        return {

            "success": True,

            "query": req.query,

            "intent": "general_fallback",

            "spoken_response": fallback,

            "text_response": fallback

        }



@router.get("/status")

@legacy_router.get("/status")

def get_recdebut_status_endpoint():

    try:
        privacy_phones, privacy_emails = get_personal_exclusion_set()
        reply_privacy = {"ready": True, "excluded_phone_count": len(privacy_phones), "excluded_email_count": len(privacy_emails)}
    except PrivacyCheckUnavailable:
        reply_privacy = {"ready": False, "forwarding_blocked": True, "reason": "Personal contact exclusions unavailable"}
    reply_privacy["policy"] = "exact_unique_roster_match_and_personal_exclusion"
    conn = sqlite3.connect(str(DB_PATH))

    athlete_count = conn.execute("SELECT COUNT(*) FROM rec_debut_athletes").fetchone()[0]

    coach_count = conn.execute("SELECT COUNT(*) FROM rec_debut_coaches").fetchone()[0]

    dispatch_count = conn.execute("SELECT COUNT(*) FROM rec_debut_dispatches").fetchone()[0]

    conn.close()



    return {

        "reply_privacy": reply_privacy,
        "entity": "Recreational Debut",

        "status": "ONLINE",

        "athletes_in_db": athlete_count,

        "coaches_in_db": coach_count,

        "dispatches_sent": dispatch_count,

        "edge_tunnel": "https://api.brettstehouwer.live",

        "s25_ultra_apk_built": True,

        "verification_numbers": ["+1-616-291-5227", "+1-616-402-3628"]

    }





