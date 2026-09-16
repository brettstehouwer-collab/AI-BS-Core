import os
import sys
import time
import json
import sqlite3
import logging
import urllib.request
from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("SiteAnalyticsRouter")
logger.setLevel(logging.INFO)

COMMERCIAL_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_ANALYTICS_DB_PATH = os.path.join(COMMERCIAL_DIR, "site_analytics.db")


def init_site_analytics_db():
    conn = sqlite3.connect(SITE_ANALYTICS_DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_traffic_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            session_id TEXT NOT NULL,
            ip_address TEXT,
            page_path TEXT NOT NULL,
            page_title TEXT,
            referrer TEXT,
            user_agent TEXT,
            screen_res TEXT,
            event_type TEXT DEFAULT 'pageview',
            dwell_time_sec INTEGER DEFAULT 0,
            scroll_depth_pct INTEGER DEFAULT 0,
            gpu_renderer TEXT DEFAULT 'Unknown',
            cpu_cores INTEGER DEFAULT 4,
            device_memory_gb REAL DEFAULT 8,
            lcp_ms INTEGER,
            cls_score REAL,
            is_bot INTEGER DEFAULT 0,
            country TEXT DEFAULT 'United States',
            city TEXT DEFAULT 'Local/Private',
            event_data TEXT
        )
    """)
    conn.commit()

    # Safely migrate existing tables if columns are missing
    cursor.execute("PRAGMA table_info(site_traffic_events)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    new_cols = [
        ("dwell_time_sec", "INTEGER DEFAULT 0"),
        ("scroll_depth_pct", "INTEGER DEFAULT 0"),
        ("gpu_renderer", "TEXT DEFAULT 'Unknown'"),
        ("cpu_cores", "INTEGER DEFAULT 4"),
        ("device_memory_gb", "REAL DEFAULT 8"),
        ("lcp_ms", "INTEGER"),
        ("cls_score", "REAL"),
        ("is_bot", "INTEGER DEFAULT 0"),
        ("country", "TEXT DEFAULT 'United States'"),
        ("city", "TEXT DEFAULT 'Local/Private'"),
        ("network_type", "TEXT DEFAULT '4g'"),
        ("downlink_mbps", "REAL"),
        ("rtt_ms", "INTEGER"),
        ("ttfb_ms", "INTEGER"),
        ("dns_ms", "INTEGER"),
        ("dom_load_ms", "INTEGER"),
        ("page_load_ms", "INTEGER"),
        ("device_pixel_ratio", "REAL DEFAULT 1.0"),
        ("color_depth", "INTEGER DEFAULT 24"),
        ("dark_mode", "INTEGER DEFAULT 0"),
        ("timezone", "TEXT DEFAULT 'America/Detroit'"),
        ("language", "TEXT DEFAULT 'en-US'"),
        ("utm_source", "TEXT"),
        ("utm_medium", "TEXT"),
        ("utm_campaign", "TEXT"),
        ("hls_supported", "INTEGER DEFAULT 1"),
        ("viewport_res", "TEXT"),
        ("error_message", "TEXT"),
        ("cf_ray", "TEXT"),
        ("cf_country", "TEXT"),
        ("cf_proto", "TEXT"),
        ("site_id", "TEXT DEFAULT 'stehouwer_publishing'"),
        ("domain", "TEXT DEFAULT 'stehouwer-publishing.com'"),
    ]
    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            try:
                cursor.execute(
                    f"ALTER TABLE site_traffic_events ADD COLUMN {col_name} {col_def}"
                )
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add column {col_name}: {e}")

    conn.close()


init_site_analytics_db()

# Cache for IP resolution to avoid rate limits
IP_GEO_CACHE: Dict[str, Dict[str, str]] = {}


def resolve_ip_geo(ip: str) -> Dict[str, str]:
    if (
        not ip
        or ip in ["127.0.0.1", "localhost", "::1"]
        or ip.startswith("192.168.")
        or ip.startswith("10.")
    ):
        return {"country": "United States", "city": "Michigan (Local Dev)"}
    if ip in IP_GEO_CACHE:
        return IP_GEO_CACHE[ip]

    try:
        url = f"http://ip-api.com/json/{ip}?fields=country,city,status"
        req = urllib.request.Request(url, headers={"User-Agent": "AI-BS-Analytics/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                geo = {
                    "country": data.get("country", "United States"),
                    "city": data.get("city", "Unknown"),
                }
                IP_GEO_CACHE[ip] = geo
                return geo
    except Exception:
        pass

    fallback = {"country": "United States", "city": "North America"}
    IP_GEO_CACHE[ip] = fallback
    return fallback


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from datetime import datetime

# --- Multi-Channel Notifier Credentials & State ---
_ALERT_COOLDOWN_MAP: Dict[str, float] = {}

def _load_notifier_credentials() -> Dict[str, str]:
    creds = {
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/1526362047917588510/CDD0CK6ck5jcQF8YmzZyz17JKi-d5XfbGmmb4PmTF0cvADJapSfBikHFzIYQST-FKYej",
        "OPERATOR_EMAIL": "footballstar0325@gmail.com",
        "IMAP_USER": "footballstar0325@gmail.com",
        "IMAP_APP_PASSWORD": "dnbmziwbtrfgfeht",
        "OPERATOR_PHONE": "1-616-402-3628",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587"
    }
    
    base_dir = os.path.abspath(os.path.join(COMMERCIAL_DIR, "..", ".."))
    backend_dir = os.path.abspath(os.path.join(COMMERCIAL_DIR, ".."))
    env_paths = [os.path.join(base_dir, ".env"), os.path.join(backend_dir, ".env")]
    
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
                            if k in creds:
                                creds[k] = v
            except Exception:
                pass
                
    for k in creds:
        if k in os.environ and os.environ[k]:
            creds[k] = os.environ[k]
            
    return creds

def _send_discord_alert_async(webhook_url: str, title: str, description: str, fields: List[Dict[str, Any]], color: int = 0x38bdf8):
    def _post():
        try:
            payload = {
                "username": "AI-BS Sentinel",
                "avatar_url": "https://ai-bs-dashboard.web.app/favicon.svg",
                "embeds": [{
                    "title": title,
                    "description": description,
                    "color": color,
                    "fields": fields,
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "AI-BS Sovereign Presence & Security Sentinel • Kent County, MI"}
                }]
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "AI-BS-Dashboard-Notifier/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                pass
            logger.info("Dispatched Discord Webhook alert for AI-BS Dashboard session.")
        except Exception as ex:
            logger.warning(f"Discord webhook dispatch failed: {ex}")

    threading.Thread(target=_post, daemon=True).start()

def _send_email_and_sms_async(subject: str, body_text: str, is_login: bool = False):
    def _send():
        try:
            creds = _load_notifier_credentials()
            smtp_user = creds.get("OPERATOR_EMAIL") or creds.get("IMAP_USER") or "footballstar0325@gmail.com"
            smtp_pwd = creds.get("IMAP_APP_PASSWORD") or "dnbmziwbtrfgfeht"
            smtp_host = creds.get("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(creds.get("SMTP_PORT", 587))

            if not smtp_user or not smtp_pwd:
                return

            phone_raw = creds.get("OPERATOR_PHONE", "1-616-402-3628")
            phone_digits = "".join(filter(str.isdigit, phone_raw))
            sms_gateways = []
            if len(phone_digits) >= 10:
                ten = phone_digits[-10:]
                sms_gateways = [
                    f"{ten}@vtext.com",                 # Verizon SMS
                    f"{ten}@vzwpix.com",                # Verizon MMS
                    f"{ten}@txt.att.net",               # AT&T SMS
                    f"{ten}@mms.att.net",               # AT&T MMS
                    f"{ten}@tmomail.net",               # T-Mobile SMS/MMS
                    f"{ten}@messaging.sprintpcs.com",   # Sprint SMS
                    f"{ten}@pm.sprint.com",             # Sprint MMS
                    f"{ten}@msg.fi.google.com",         # Google Fi
                    f"{ten}@cricketwireless.net",       # Cricket Wireless
                    f"{ten}@mailmymobile.net",          # Consumer Cellular
                    f"{ten}@sms.myboostmobile.com",     # Boost Mobile
                    f"{ten}@myuscellular.com",          # US Cellular
                ]

            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15.0)
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pwd)

            # Send email to operator
            email_msg = MIMEText(body_text, "plain", "utf-8")
            email_msg["Subject"] = subject
            email_msg["From"] = f"AI-BS Sentinel <{smtp_user}>"
            email_msg["To"] = smtp_user
            try:
                server.sendmail(smtp_user, [smtp_user], email_msg.as_string())
            except Exception as e_err:
                logger.warning(f"Operator email dispatch notice: {e_err}")

            # Send individually to each carrier gateway to avoid carrier multi-recipient spam filtering
            for gw in sms_gateways:
                try:
                    sms_msg = MIMEText(body_text, "plain", "utf-8")
                    sms_msg["Subject"] = subject
                    sms_msg["From"] = f"AI-BS Sentinel <{smtp_user}>"
                    sms_msg["To"] = gw
                    server.sendmail(smtp_user, [gw], sms_msg.as_string())
                except Exception as sms_err:
                    logger.debug(f"SMS gateway {gw} notice: {sms_err}")

            server.quit()
            logger.info(f"Dispatched SMS & Email notifications to {recipients}")
        except Exception as ex:
            logger.warning(f"Email/SMS dispatch failed: {ex}")

    threading.Thread(target=_send, daemon=True).start()

def trigger_dashboard_notification(event_type: str, user_email: str, ip: str, geo: Dict[str, str], metadata: Optional[Dict[str, Any]] = None):
    now = time.time()
    is_login = (event_type in ["user_login", "login", "auth_login", "dashboard_login"])
    
    clean_email = (user_email or "").strip()
    cooldown_key = f"{clean_email}:{ip}:{ 'login' if is_login else 'visitor' }"
    cooldown_period = 45 if is_login else 300  # 45s cooldown for logins, 5 min for visitor pageviews
    
    last_time = _ALERT_COOLDOWN_MAP.get(cooldown_key, 0)
    if now - last_time < cooldown_period:
        return
    _ALERT_COOLDOWN_MAP[cooldown_key] = now

    time_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p EDT")
    city = geo.get("city", "Michigan (Local)")
    country = geo.get("country", "United States")
    loc_str = f"{city}, {country}"

    if is_login:
        title = "🚨 [LOGIN] User Logged In to AI-BS Dashboard"
        sms_text = f"🚨 AI-BS DASHBOARD LOGIN!\nUser: {clean_email or 'Authorized User'}\nTime: {time_str}\nLoc: {loc_str}\nIP: {ip}\nURL: https://ai-bs-dashboard.web.app/"
        desc = f"**User Authenticated:** `{clean_email or 'Authorized User'}`\n**Site:** `https://ai-bs-dashboard.web.app/`"
        color = 0x10b981  # Emerald Green
    else:
        title = "👁️ [ACTIVE VISITOR] User Active on AI-BS Dashboard"
        sms_text = f"👁️ AI-BS Dashboard Visitor Active\nUser: {clean_email or 'Guest / Visitor'}\nTime: {time_str}\nLoc: {loc_str}\nIP: {ip}\nURL: https://ai-bs-dashboard.web.app/"
        desc = f"**Active Visitor Detected on AI-BS Dashboard**\n**Site:** `https://ai-bs-dashboard.web.app/`"
        color = 0x38bdf8  # Sky Blue

    fields = [
        {"name": "👤 User / Signatory", "value": clean_email or "Anonymous / Guest", "inline": True},
        {"name": "🌍 Location", "value": loc_str, "inline": True},
        {"name": "🌐 IP Address", "value": f"`{ip}`", "inline": True},
        {"name": "🕒 Timestamp", "value": time_str, "inline": True},
        {"name": "🔗 Origin URL", "value": "https://ai-bs-dashboard.web.app/", "inline": True},
    ]
    if metadata and metadata.get("gpu_renderer"):
        fields.append({"name": "💻 Client Hardware / GPU", "value": str(metadata.get("gpu_renderer"))[:80], "inline": False})
    if metadata and metadata.get("page_path"):
        fields.append({"name": "📄 Page / Tab", "value": str(metadata.get("page_path")), "inline": True})

    # 1. Discord Webhook
    creds = _load_notifier_credentials()
    webhook = creds.get("DISCORD_WEBHOOK_URL")
    if webhook and webhook.startswith("http"):
        _send_discord_alert_async(webhook, title, desc, fields, color)

    # 2. Email & SMS
    _send_email_and_sms_async(title, sms_text, is_login)

    # 3. Host speech announcement if local
    try:
        from bullshit_senses import speak_direct
        speech_text = f"Dashboard alert: {clean_email or 'User'} active on AI-BS"
        threading.Thread(target=speak_direct, args=(speech_text,), daemon=True).start()
    except Exception:
        pass


site_analytics_router = APIRouter(
    prefix="/api/analytics", tags=["Site Analytics Telemetry"]
)


class TrafficBeaconPayload(BaseModel):
    session_id: str
    page_path: str
    page_title: Optional[str] = "Stehouwer Publishing"
    site_id: Optional[str] = "stehouwer_publishing"
    domain: Optional[str] = None
    referrer: Optional[str] = "Direct"
    screen_res: Optional[str] = "Unknown"
    viewport_res: Optional[str] = None
    event_type: Optional[str] = "pageview"
    dwell_time_sec: Optional[int] = 0
    scroll_depth_pct: Optional[int] = 0
    gpu_renderer: Optional[str] = "Unknown"
    cpu_cores: Optional[int] = 4
    device_memory_gb: Optional[float] = 8.0
    device_pixel_ratio: Optional[float] = 1.0
    color_depth: Optional[int] = 24
    dark_mode: Optional[bool] = False
    timezone: Optional[str] = "America/Detroit"
    language: Optional[str] = "en-US"
    network_type: Optional[str] = "4g"
    downlink_mbps: Optional[float] = None
    rtt_ms: Optional[int] = None
    ttfb_ms: Optional[int] = None
    dns_ms: Optional[int] = None
    dom_load_ms: Optional[int] = None
    page_load_ms: Optional[int] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    hls_supported: Optional[bool] = True
    lcp_ms: Optional[int] = None
    cls_score: Optional[float] = None
    is_bot: Optional[bool] = False
    event_data: Optional[Union[str, Dict[str, Any], Any]] = None
    error_message: Optional[str] = None


@site_analytics_router.post("/track")
async def track_site_beacon(payload: TrafficBeaconPayload, request: Request):
    """Receive live traffic telemetry beacon from Stehouwer-Publishing.com or TheSimpleChef (16-Layer Suite)."""
    cf_ip = request.headers.get("cf-connecting-ip")
    ip = cf_ip if cf_ip else (request.client.host if request.client else "127.0.0.1")
    cf_ray = request.headers.get("cf-ray") or "direct"
    cf_country = request.headers.get("cf-ipcountry")
    cf_proto = (
        request.headers.get("cf-visitor")
        or request.headers.get("x-forwarded-proto")
        or "https"
    )
    user_agent = request.headers.get("user-agent", "Unknown")
    now = time.time()
    geo = resolve_ip_geo(ip)
    if cf_country and geo.get("country") in ["United States", "Unknown"]:
        geo["country"] = cf_country

    # Multi-site classification
    host = (request.headers.get("host") or "").lower()
    origin = (request.headers.get("origin") or "").lower()
    site_id = (payload.site_id or "stehouwer_publishing").lower()
    domain = payload.domain or request.headers.get("host") or "stehouwer-publishing.com"

    if (
        "thesimplechef" in host
        or "thesimplechef" in origin
        or "thesimplecheff" in host
        or "thesimplecheff" in origin
        or ":8055" in host
        or site_id == "thesimplechef"
    ):
        site_id = "thesimplechef"
        if not payload.domain:
            domain = "thesimplechef.web.app"
    elif (
        "ai-bs-dashboard" in host
        or "ai-bs-dashboard" in origin
        or site_id in ["aibs_dashboard", "ai_bs_dashboard", "dashboard"]
        or "ai-bs-dashboard.web.app" in domain
    ):
        site_id = "aibs_dashboard"
        if not payload.domain:
            domain = "ai-bs-dashboard.web.app"
        # Trigger real-time dashboard notification
        trigger_dashboard_notification(
            event_type=payload.event_type or "pageview",
            user_email=str(payload.event_data) if (isinstance(payload.event_data, str) and "@" in payload.event_data) else "",
            ip=ip,
            geo=geo,
            metadata=payload.dict()
        )

    try:
        event_data_str = json.dumps(payload.event_data) if isinstance(payload.event_data, (dict, list)) else (str(payload.event_data) if payload.event_data is not None else None)
        conn = sqlite3.connect(SITE_ANALYTICS_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO site_traffic_events (
                timestamp, session_id, ip_address, page_path, page_title, referrer, user_agent, screen_res,
                event_type, dwell_time_sec, scroll_depth_pct, gpu_renderer, cpu_cores, device_memory_gb,
                lcp_ms, cls_score, is_bot, country, city, event_data,
                network_type, downlink_mbps, rtt_ms, ttfb_ms, dns_ms, dom_load_ms, page_load_ms,
                device_pixel_ratio, color_depth, dark_mode, timezone, language,
                utm_source, utm_medium, utm_campaign, hls_supported, viewport_res, error_message,
                cf_ray, cf_country, cf_proto, site_id, domain
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                now,
                payload.session_id,
                ip,
                payload.page_path,
                payload.page_title,
                payload.referrer,
                user_agent,
                payload.screen_res,
                payload.event_type,
                payload.dwell_time_sec or 0,
                payload.scroll_depth_pct or 0,
                payload.gpu_renderer or "Unknown",
                payload.cpu_cores or 4,
                payload.device_memory_gb or 8.0,
                payload.lcp_ms,
                payload.cls_score,
                1 if payload.is_bot else 0,
                geo["country"],
                geo["city"],
                event_data_str,
                payload.network_type or "4g",
                payload.downlink_mbps,
                payload.rtt_ms,
                payload.ttfb_ms,
                payload.dns_ms,
                payload.dom_load_ms,
                payload.page_load_ms,
                payload.device_pixel_ratio or 1.0,
                payload.color_depth or 24,
                1 if payload.dark_mode else 0,
                payload.timezone or "America/Detroit",
                payload.language or "en-US",
                payload.utm_source,
                payload.utm_medium,
                payload.utm_campaign,
                1 if payload.hls_supported else 0,
                payload.viewport_res,
                payload.error_message,
                cf_ray,
                geo["country"],
                cf_proto,
                site_id,
                domain,
            ),
        )
        conn.commit()
        conn.close()

        # Dual-dispatch: forward to ChromaDB vector partition for The Simple Chef
        if site_id == "thesimplechef":
            try:
                from backend.core.thesimplechef_analytics_daemon import analytics_daemon
                analytics_daemon.ingest_event({
                    "ip": ip,
                    "user_agent": user_agent,
                    "path": payload.page_path,
                    "event_type": payload.event_type or "pageview",
                    "item_name": payload.page_title or "The Simple Chef Storefront",
                    "referrer": payload.referrer or "direct",
                    "session_id": payload.session_id
                })
            except Exception as ex:
                logger.debug(f"ChromaDB chef analytics forwarding: {ex}")

        return {"status": "recorded", "timestamp": now, "geo": geo, "site_id": site_id}
    except Exception as e:
        logger.error(f"Failed to record site analytics beacon: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


class DashboardLoginPayload(BaseModel):
    email: str
    displayName: Optional[str] = "Admin / User"
    uid: Optional[str] = None
    photoURL: Optional[str] = None
    url: Optional[str] = "https://ai-bs-dashboard.web.app/"
    timestamp: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    event_type: Optional[str] = "user_login"


@site_analytics_router.post("/notify-login")
async def notify_dashboard_login(payload: DashboardLoginPayload, request: Request):
    """Instant notification endpoint when a user logs into or accesses ai-bs-dashboard.web.app."""
    cf_ip = request.headers.get("cf-connecting-ip")
    ip = cf_ip if cf_ip else (request.client.host if request.client else "127.0.0.1")
    geo = resolve_ip_geo(ip)
    now = time.time()

    # 1. Dispatch Multi-Channel Alerts (Discord, SMS, Email, TTS)
    trigger_dashboard_notification(
        event_type="user_login",
        user_email=payload.email,
        ip=ip,
        geo=geo,
        metadata={
            "displayName": payload.displayName,
            "page_path": payload.url,
            "uid": payload.uid,
            "device_info": payload.device_info or {}
        }
    )

    # 2. Record to SQLite database
    try:
        conn = sqlite3.connect(SITE_ANALYTICS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO site_traffic_events (
                timestamp, session_id, ip_address, page_path, page_title, referrer, user_agent,
                event_type, country, city, event_data, site_id, domain
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            payload.session_id or f"sid_login_{int(now)}",
            ip,
            payload.url,
            f"Dashboard Login: {payload.email}",
            "Direct / Auth",
            request.headers.get("user-agent", "Unknown"),
            "user_login",
            geo.get("country", "United States"),
            geo.get("city", "Michigan (Local)"),
            json.dumps({"email": payload.email, "displayName": payload.displayName, "uid": payload.uid}),
            "aibs_dashboard",
            "ai-bs-dashboard.web.app"
        ))
        conn.commit()
        conn.close()
    except Exception as ex:
        logger.warning(f"Failed to record login event to sqlite: {ex}")

    return {
        "status": "notified",
        "user": payload.email,
        "timestamp": now,
        "geo": geo,
        "site_id": "aibs_dashboard"
    }


@site_analytics_router.get("/traffic-summary")
@site_analytics_router.get("/live_summary")
@site_analytics_router.get("/api/analytics/live_summary")
async def get_site_traffic_summary(limit: int = 50, site_id: str = "stehouwer_publishing"):
    """Fetch live web traffic analytics summary with 16-layer deep telemetry for AI-BS Traffic Studio."""
    try:
        conn = sqlite3.connect(SITE_ANALYTICS_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()

        # Multi-site filtering logic
        has_site_filter = bool(site_id and site_id.upper() != "ALL")

        def where_sql(extra: Optional[str] = None):
            clauses = []
            params = []
            if has_site_filter:
                clauses.append("site_id = ?")
                params.append(site_id)
            if extra:
                clauses.append(f"({extra})")
            if clauses:
                return f" WHERE {' AND '.join(clauses)}", params
            return "", []

        # 1. Total Pageviews & Sessions
        w, p = where_sql()
        cursor.execute(f"SELECT COUNT(*) FROM site_traffic_events{w}", p)
        total_pageviews = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(DISTINCT session_id) FROM site_traffic_events{w}", p)
        unique_visitors = cursor.fetchone()[0]

        # 2. Dwell Time & Scroll Metrics
        w, p = where_sql("dwell_time_sec > 0")
        cursor.execute(
            f"SELECT AVG(dwell_time_sec), MAX(scroll_depth_pct) FROM site_traffic_events{w}", p
        )
        dwell_row = cursor.fetchone()
        avg_dwell_time_sec = (
            round(dwell_row[0], 1) if dwell_row and dwell_row[0] else 0.0
        )

        w, p = where_sql("scroll_depth_pct >= 75")
        cursor.execute(
            f"SELECT COUNT(*) FROM site_traffic_events{w}", p
        )
        deep_scrollers = cursor.fetchone()[0]
        scroll_completion_rate = round(
            (deep_scrollers / max(1, total_pageviews)) * 100, 1
        )

        # 3. Top Pages Breakdown
        w, p = where_sql()
        cursor.execute(
            f"SELECT page_path, COUNT(*) as hits FROM site_traffic_events{w} GROUP BY page_path ORDER BY hits DESC LIMIT 10", p
        )
        top_pages = [{"path": r[0], "hits": r[1]} for r in cursor.fetchall()]

        # 4. Top Referrers
        w, p = where_sql()
        cursor.execute(
            f"SELECT referrer, COUNT(*) as hits FROM site_traffic_events{w} GROUP BY referrer ORDER BY hits DESC LIMIT 10", p
        )
        top_referrers = [{"referrer": r[0], "hits": r[1]} for r in cursor.fetchall()]

        # 5. Geo-IP Distribution
        w, p = where_sql()
        cursor.execute(
            f"SELECT country, city, COUNT(*) as hits FROM site_traffic_events{w} GROUP BY country, city ORDER BY hits DESC LIMIT 10", p
        )
        geo_distribution = [
            {"country": r[0], "city": r[1], "hits": r[2]} for r in cursor.fetchall()
        ]

        # 6. Hardware & WebGL GPU Models
        w, p = where_sql("gpu_renderer != 'Unknown'")
        cursor.execute(
            f"SELECT gpu_renderer, COUNT(*) as count FROM site_traffic_events{w} GROUP BY gpu_renderer ORDER BY count DESC LIMIT 8", p
        )
        top_gpus = [{"gpu": r[0], "count": r[1]} for r in cursor.fetchall()]

        # 7. Web Vitals Performance
        w, p = where_sql("lcp_ms IS NOT NULL")
        cursor.execute(
            f"SELECT AVG(lcp_ms), AVG(cls_score) FROM site_traffic_events{w}", p
        )
        vitals_row = cursor.fetchone()
        avg_lcp_ms = round(vitals_row[0]) if vitals_row and vitals_row[0] else 420
        avg_cls_score = (
            round(vitals_row[1], 3) if vitals_row and vitals_row[1] else 0.012
        )

        # 8. Network & Edge Latency Metrics
        w, p = where_sql("ttfb_ms IS NOT NULL")
        cursor.execute(
            f"SELECT AVG(ttfb_ms), AVG(rtt_ms), AVG(downlink_mbps) FROM site_traffic_events{w}", p
        )
        net_row = cursor.fetchone()
        avg_ttfb_ms = round(net_row[0]) if net_row and net_row[0] is not None else 65
        avg_rtt_ms = round(net_row[1]) if net_row and net_row[1] is not None else 32
        avg_downlink = round(net_row[2], 1) if net_row and net_row[2] is not None else 18.5

        w, p = where_sql("network_type IS NOT NULL")
        cursor.execute(
            f"SELECT network_type, COUNT(*) FROM site_traffic_events{w} GROUP BY network_type ORDER BY COUNT(*) DESC LIMIT 5", p
        )
        network_breakdown = [{"type": r[0], "count": r[1]} for r in cursor.fetchall()]

        # 9. Campaign & Attribution Metrics
        w, p = where_sql("utm_source IS NOT NULL")
        cursor.execute(
            f"SELECT utm_source, COUNT(*) FROM site_traffic_events{w} GROUP BY utm_source ORDER BY COUNT(*) DESC LIMIT 5", p
        )
        top_sources = [{"source": r[0], "hits": r[1]} for r in cursor.fetchall()]

        w, p = where_sql("utm_campaign IS NOT NULL")
        cursor.execute(
            f"SELECT utm_campaign, COUNT(*) FROM site_traffic_events{w} GROUP BY utm_campaign ORDER BY COUNT(*) DESC LIMIT 5", p
        )
        top_campaigns = [{"campaign": r[0], "hits": r[1]} for r in cursor.fetchall()]

        # 10. Streaming & Media Readiness
        w, p = where_sql("hls_supported = 1")
        cursor.execute(f"SELECT COUNT(*) FROM site_traffic_events{w}", p)
        hls_count = cursor.fetchone()[0]
        hls_supported_pct = round((hls_count / max(1, total_pageviews)) * 100, 1)

        w, p = where_sql("page_path = '/live' OR event_type LIKE 'stream_%'")
        cursor.execute(f"SELECT COUNT(*) FROM site_traffic_events{w}", p)
        live_stream_hits = cursor.fetchone()[0]

        # 11. Client Diagnostics & Display
        w, p = where_sql("dark_mode = 1")
        cursor.execute(f"SELECT COUNT(*) FROM site_traffic_events{w}", p)
        dark_count = cursor.fetchone()[0]
        dark_mode_pct = round((dark_count / max(1, total_pageviews)) * 100, 1)

        w, p = where_sql("timezone IS NOT NULL")
        cursor.execute(
            f"SELECT timezone, COUNT(*) FROM site_traffic_events{w} GROUP BY timezone ORDER BY COUNT(*) DESC LIMIT 5", p
        )
        top_timezones = [{"tz": r[0], "count": r[1]} for r in cursor.fetchall()]

        # 12. Form Field Abandonment Leads
        w, p = where_sql("event_type = 'form_field_input'")
        cursor.execute(
            f"SELECT timestamp, session_id, page_path, event_data FROM site_traffic_events{w} ORDER BY id DESC LIMIT 10", p
        )
        abandoned_form_leads = []
        for r in cursor.fetchall():
            try:
                edata = json.loads(r[3]) if r[3] else {}
            except Exception:
                edata = {}
            abandoned_form_leads.append(
                {
                    "timestamp": r[0],
                    "formatted_time": time.strftime("%H:%M:%S", time.localtime(r[0])),
                    "session_id": r[1],
                    "page_path": r[2],
                    "field_name": edata.get("field_name", "input"),
                    "partial_email": edata.get("partial_value", "Entered form input"),
                }
            )

        # 13. Bot vs Human Traffic Breakdown
        w, p = where_sql()
        cursor.execute(
            f"SELECT is_bot, COUNT(*) FROM site_traffic_events{w} GROUP BY is_bot", p
        )
        bot_counts = {r[0]: r[1] for r in cursor.fetchall()}
        human_traffic_pct = round(
            (bot_counts.get(0, 0) / max(1, total_pageviews)) * 100, 1
        )

        # 14. Heatmap Coordinates
        w, p = where_sql("event_type = 'click' AND event_data IS NOT NULL")
        cursor.execute(
            f"SELECT event_data FROM site_traffic_events{w} ORDER BY id DESC LIMIT 40", p
        )
        heatmap_points = []
        for r in cursor.fetchall():
            try:
                edata = json.loads(r[0]) if r[0] else {}
                if "click_x" in edata and "click_y" in edata:
                    heatmap_points.append(
                        {
                            "x": edata["click_x"],
                            "y": edata["click_y"],
                            "tag": edata.get("tag", "BTN"),
                        }
                    )
            except Exception:
                pass

        # 15. Recent Client Errors
        w, p = where_sql("error_message IS NOT NULL OR event_type IN ('js_error', 'promise_rejection', 'stream_error')")
        cursor.execute(
            f"SELECT timestamp, session_id, page_path, event_type, error_message FROM site_traffic_events{w} ORDER BY id DESC LIMIT 10", p
        )
        recent_errors = []
        for r in cursor.fetchall():
            recent_errors.append(
                {
                    "timestamp": r[0],
                    "formatted_time": time.strftime("%H:%M:%S", time.localtime(r[0])),
                    "session_id": r[1],
                    "page_path": r[2],
                    "event_type": r[3],
                    "message": r[4] or "Client Exception",
                }
            )

        # 16. Live Event Log with Expanded Columns
        w, p = where_sql()
        cursor.execute(
            f"""
            SELECT id, timestamp, session_id, ip_address, page_path, page_title, referrer, event_type, screen_res,
                   country, city, gpu_renderer, is_bot, dwell_time_sec, scroll_depth_pct,
                   network_type, ttfb_ms, dark_mode, timezone, utm_source, hls_supported, site_id
            FROM site_traffic_events{w}
            ORDER BY id DESC LIMIT ?
        """,
            p + [limit],
        )

        events = []
        for r in cursor.fetchall():
            events.append(
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "formatted_time": time.strftime("%H:%M:%S", time.localtime(r[1])),
                    "session_id": r[2],
                    "ip_address": r[3],
                    "page_path": r[4],
                    "page_title": r[5],
                    "referrer": r[6],
                    "event_type": r[7],
                    "screen_res": r[8],
                    "country": r[9],
                    "city": r[10],
                    "gpu_renderer": r[11],
                    "is_bot": bool(r[12]),
                    "dwell_time_sec": r[13],
                    "scroll_depth_pct": r[14],
                    "network_type": r[15] or "4g",
                    "ttfb_ms": r[16],
                    "dark_mode": bool(r[17]),
                    "timezone": r[18] or "America/Detroit",
                    "utm_source": r[19],
                    "hls_supported": bool(r[20]) if r[20] is not None else True,
                    "site_id": r[21] if len(r) > 21 and r[21] else "stehouwer_publishing",
                }
            )

        # Available sites in db
        cursor.execute("SELECT DISTINCT site_id FROM site_traffic_events WHERE site_id IS NOT NULL")
        available_sites = [r[0] for r in cursor.fetchall()]
        if "stehouwer_publishing" not in available_sites:
            available_sites.insert(0, "stehouwer_publishing")
        if "thesimplechef" not in available_sites:
            available_sites.append("thesimplechef")

        conn.close()

        return {
            "status": "success",
            "site_id": site_id,
            "available_sites": available_sites,
            "total_pageviews": total_pageviews,
            "unique_visitors": unique_visitors,
            "avg_dwell_time_sec": avg_dwell_time_sec,
            "scroll_completion_rate": scroll_completion_rate,
            "human_traffic_pct": human_traffic_pct,
            "top_pages": top_pages,
            "top_referrers": top_referrers,
            "geo_distribution": geo_distribution,
            "top_gpus": top_gpus,
            "web_vitals": {"lcp_ms": avg_lcp_ms, "cls_score": avg_cls_score},
            "network_metrics": {
                "avg_ttfb_ms": avg_ttfb_ms,
                "avg_rtt_ms": avg_rtt_ms,
                "avg_downlink_mbps": avg_downlink,
                "network_breakdown": network_breakdown,
            },
            "attribution_metrics": {
                "top_sources": top_sources,
                "top_campaigns": top_campaigns,
            },
            "media_readiness": {
                "hls_supported_pct": hls_supported_pct,
                "live_stream_hits": live_stream_hits,
            },
            "client_diagnostics": {
                "dark_mode_pct": dark_mode_pct,
                "top_timezones": top_timezones,
            },
            "recent_errors": recent_errors,
            "form_abandonment_leads": abandoned_form_leads,
            "heatmap_points": heatmap_points,
            "live_events": events,
        }
    except Exception as e:
        logger.error(f"Failed to query traffic summary: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )
