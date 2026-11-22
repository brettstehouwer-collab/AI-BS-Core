"""Local brand campaign drafts and write-only TextBee connections. No sends."""
import asyncio
import base64
import ctypes
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request as URLRequest, urlopen
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from security.host_control_access import AdminHostControlRoute, require_host_admin, HOST_CONTROL_PRIVATE_HEADERS
from brand_campaigns.aws_readiness import read_ses_status, PROFILE as SES_PROFILE, REGION as SES_REGION
from brand_campaigns.outreach_records import read_records

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "state" / "brand_campaigns_20261114" / "owners"
BRANDS = {"productions": {"id": "productions", "name": "Stehouwer Productions", "website": "https://stehouwerproductions.com"},
          "publishing": {"id": "publishing", "name": "Stehouwer Publishing", "website": "https://stehouwer-publishing.com"}}
HOLD = "Dispatch held pending verified provider connection, delivery reconciliation and exact campaign authorization. No message sent."


def fail(code, message):
    raise HTTPException(code, message, headers=dict(HOST_CONTROL_PRIVATE_HEADERS))


def brand(value):
    if value not in BRANDS:
        fail(400, "Select an owned brand")
    return value


def owner_hash(owner):
    if not isinstance(owner, str) or not owner.startswith("firebase:ai-bs-dashboard:") or len(owner.split(":", 2)[-1]) < 1:
        fail(403, "Verified Firebase owner required")
    return hashlib.sha256(owner.encode()).hexdigest()


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def email(value):
    value = str(value or "").strip().lower()
    return value if re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value) and len(value) <= 254 else ""


def phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 10:
        return "+1" + digits
    return "+" + digits if len(digits) == 11 and digits.startswith("1") else ""


@contextmanager
def database(owner):
    directory = DATA
    directory.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(directory / (owner_hash(owner) + ".db"), timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS imports(id TEXT PRIMARY KEY,brand TEXT,source_name TEXT,source_sha256 TEXT,created_at TEXT,rows_count INTEGER,UNIQUE(brand,source_sha256));
        CREATE TABLE IF NOT EXISTS contacts(id TEXT PRIMARY KEY,brand TEXT,business TEXT,email TEXT,phone TEXT,sms_consent TEXT DEFAULT 'unknown');
        CREATE TABLE IF NOT EXISTS provenance(import_id TEXT,row_number INTEGER,contact_id TEXT,UNIQUE(import_id,row_number));
        CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,brand TEXT,channel TEXT,name TEXT,subject TEXT,body TEXT,contact_ids TEXT,revision INTEGER,created_at TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS attempts(campaign_id TEXT,revision INTEGER,contact_id TEXT,channel TEXT,status TEXT,reason TEXT,created_at TEXT,UNIQUE(campaign_id,revision,contact_id,channel));
        CREATE TABLE IF NOT EXISTS suppressions(channel TEXT,address TEXT,reason TEXT,created_at TEXT,UNIQUE(channel,address));
        CREATE TABLE IF NOT EXISTS provenance_metadata(import_id TEXT,row_number INTEGER,metadata_json TEXT,UNIQUE(import_id,row_number));
        """)
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def import_contacts(owner, payload):
    selected = brand(payload.get("brand"))
    rows = payload.get("rows")
    digest = payload.get("source_sha256", "")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000 or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
        fail(400, "Import requires 1-1000 rows and the original source SHA-256")
    source = str(payload.get("source_name", ""))[:200]
    with database(owner) as conn:
        previous = conn.execute("SELECT * FROM imports WHERE brand=? AND source_sha256=?", (selected, digest.lower())).fetchone()
        if previous:
            return {"import": dict(previous), "duplicate": True, "added": 0}
        import_id = str(uuid.uuid4())
        conn.execute("INSERT INTO imports VALUES(?,?,?,?,?,?)", (import_id, selected, source, digest.lower(), now(), len(rows)))
        added = 0
        for number, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                fail(400, "Each imported row must be an object")
            address = email(row.get("email", row.get("Email")))
            number_phone = phone(row.get("phone", row.get("Phone")))
            business = str(row.get("business", row.get("company", row.get("Business / Organization", row.get("Organization or contact", "")))))[:300]
            contact = None
            if address or number_phone:
                # An exact email wins over shared business telephone numbers.
                found = conn.execute("SELECT * FROM contacts WHERE brand=? AND email=? AND email!='' ORDER BY rowid LIMIT 1", (selected, address)).fetchone() if address else None
                if found is None and number_phone:
                    found = conn.execute("SELECT * FROM contacts WHERE brand=? AND phone=? AND phone!='' AND (email='' OR ?='' OR email=?) ORDER BY CASE WHEN email='' THEN 0 ELSE 1 END,rowid LIMIT 1", (selected, number_phone, address, address)).fetchone()
                if found:
                    contact = found["id"]
                    if address and not found["email"]:
                        conn.execute("UPDATE contacts SET email=? WHERE id=? AND email=''", (address, contact))
                    if number_phone and not found["phone"]:
                        conn.execute("UPDATE contacts SET phone=? WHERE id=? AND phone=''", (number_phone, contact))
                else:
                    contact = str(uuid.uuid4())
                    conn.execute("INSERT INTO contacts VALUES(?,?,?,?,?,?)", (contact, selected, business, address, number_phone, "unknown"))
                    added += 1
            conn.execute("INSERT INTO provenance VALUES(?,?,?)", (import_id, number, contact))
            metadata = research_metadata(row)
            if metadata:
                conn.execute("INSERT INTO provenance_metadata VALUES(?,?,?)", (import_id, number, json.dumps(metadata)))
        return {"import": dict(conn.execute("SELECT * FROM imports WHERE id=?", (import_id,)).fetchone()), "duplicate": False, "added": added}


def research_metadata(row):
    result = {}
    fields = ("source_urls", "purpose_restrictions", "submission_policies", "outreach_eligibility", "company_ids", "companymeter_rank")
    for field in fields:
        value = row.get(field)
        if value in (None, "", []):
            continue
        values = value if isinstance(value, list) else str(value).split(" | ")
        if len(values) > 100 or any(not isinstance(v, (str, int)) for v in values):
            fail(400, "Invalid research metadata")
        values = [str(v).strip() for v in values if str(v).strip()]
        if sum(len(v) for v in values) > 20000:
            fail(400, "Research metadata too large")
        if field == "source_urls":
            for source in values:
                parsed = urlsplit(source)
                if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                    fail(400, "Research source must be a public website URL")
        result[field] = list(dict.fromkeys(values))
    if result:
        result["selected"] = False
        result["review_status"] = "manual_review_required"
    return result


def contact_research(conn):
    combined = {}
    values = conn.execute("SELECT p.contact_id,p.import_id,p.row_number,m.metadata_json,i.source_name,i.source_sha256 FROM provenance p JOIN provenance_metadata m ON m.import_id=p.import_id AND m.row_number=p.row_number JOIN imports i ON i.id=p.import_id ORDER BY i.rowid,p.row_number")
    for value in values:
        if not value["contact_id"]:
            continue
        metadata = json.loads(value["metadata_json"])
        result = combined.setdefault(value["contact_id"], {"source_urls": [], "purpose_restrictions": [], "submission_policies": [], "outreach_eligibility": [], "company_ids": [], "companymeter_ranks": [], "source_records": [], "selected": False, "review_status": "manual_review_required"})
        for field in ("source_urls", "purpose_restrictions", "submission_policies", "outreach_eligibility", "company_ids", "companymeter_rank"):
            target = "companymeter_ranks" if field == "companymeter_rank" else field
            result[target] = list(dict.fromkeys(result[target] + metadata.get(field, [])))
        result["source_records"].append({"import_id": value["import_id"], "row_number": value["row_number"], "source_name": value["source_name"], "source_sha256": value["source_sha256"], "metadata": metadata})
    return combined


def campaign_values(payload):
    selected = brand(payload.get("brand"))
    channel = payload.get("channel")
    if channel not in ("email", "sms"):
        fail(400, "Select email or sms")
    ids = payload.get("contact_ids", [])
    if not isinstance(ids, list) or len(ids) > 1000 or any(not isinstance(x, str) for x in ids):
        fail(400, "Invalid contact selection")
    name, subject, body = (str(payload.get(k, "")).strip() for k in ("name", "subject", "body"))
    if not name or not body or len(name) > 200 or len(subject) > 300 or len(body) > 20000:
        fail(400, "Campaign name and bounded message body required")
    return selected, channel, name, subject, body, list(dict.fromkeys(ids))


def save_campaign(owner, payload, identifier=None):
    selected, channel, name, subject, body, ids = campaign_values(payload)
    with database(owner) as conn:
        for cid in ids:
            if not conn.execute("SELECT 1 FROM contacts WHERE id=? AND brand=?", (cid, selected)).fetchone():
                fail(400, "Contact does not belong to this brand")
        if identifier:
            old = conn.execute("SELECT * FROM campaigns WHERE id=?", (identifier,)).fetchone()
            if not old:
                fail(404, "Campaign not found")
            if type(payload.get("revision")) is not int or payload["revision"] != old["revision"]:
                fail(409, "Draft revision changed; refresh before editing")
            if selected != old["brand"]:
                fail(400, "Draft brand cannot be reassigned")
            conn.execute("UPDATE campaigns SET channel=?,name=?,subject=?,body=?,contact_ids=?,revision=revision+1,updated_at=? WHERE id=?", (channel, name, subject, body, json.dumps(ids), now(), identifier))
        else:
            identifier = str(uuid.uuid4())
            conn.execute("INSERT INTO campaigns VALUES(?,?,?,?,?,?,?,?,?,?)", (identifier, selected, channel, name, subject, body, json.dumps(ids), 1, now(), now()))
        return campaign_dict(dict(conn.execute("SELECT * FROM campaigns WHERE id=?", (identifier,)).fetchone()), conn)


def historical_suppressions(owner):
    # This private legacy dataset is read only for its explicitly bound verified owner.
    bound = os.getenv("BRAND_CAMPAIGN_HISTORY_OWNER", "") == owner
    binding = ROOT / "state" / "brand_campaigns_20261114" / "history-owner.json"
    if not bound and binding.exists():
        try:
            configured = json.loads(binding.read_text(encoding="utf-8"))
            bound = configured.get("owner_hash") == owner_hash(owner)
        except (OSError, ValueError, TypeError):
            bound = False
    if not bound:
        return None
    path = ROOT / "state" / "julie_outreach_20261114" / "suppression-list.json"
    if not path.exists():
        return None
    values = json.loads(path.read_text(encoding="utf-8-sig"))["entries"]
    return {email(row.get("recipient")) for row in values if email(row.get("recipient"))}


def prepare(owner, identifier, revision):
    legacy = historical_suppressions(owner)
    with database(owner) as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id=?", (identifier,)).fetchone()
        if not campaign:
            fail(404, "Campaign not found")
        if type(revision) is not int or revision != campaign["revision"]:
            fail(409, "Draft revision changed")
        seen_addresses = set()
        for cid in json.loads(campaign["contact_ids"]):
            contact = conn.execute("SELECT * FROM contacts WHERE id=? AND brand=?", (cid, campaign["brand"])).fetchone()
            channel = campaign["channel"]
            address = contact[channel] if channel == "email" else contact["phone"]
            reason = ""
            if not address:
                reason = "No valid channel address"
            elif address in seen_addresses:
                reason = "Duplicate recipient address in campaign"
            elif conn.execute("SELECT 1 FROM suppressions WHERE channel=? AND address=?", (channel, address)).fetchone():
                reason = "Owner suppression"
            elif channel == "email" and legacy is None:
                reason = "Historical suppression owner binding required"
            elif channel == "email" and address in legacy:
                reason = "Previously bounced address suppressed"
            elif channel == "sms" and contact["sms_consent"] != "verified":
                reason = "SMS consent unknown; no send authorized"
            if address:
                seen_addresses.add(address)
            conn.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?) ON CONFLICT(campaign_id,revision,contact_id,channel) DO UPDATE SET status=excluded.status,reason=excluded.reason WHERE attempts.status IN ('prepared','blocked')", (identifier, revision, cid, channel, "blocked" if reason else "prepared", reason, now()))
        return {"campaign": campaign_dict(dict(campaign), conn), "dispatch_authorized": False, "hold_reason": HOLD}


def campaign_dict(row, conn):
    row["contact_ids"] = json.loads(row["contact_ids"])
    counts = {name: 0 for name in ("prepared", "blocked", "provider_accepted", "delivered", "bounced", "failed", "unknown", "open_observations", "click_observations")}
    for value in conn.execute("SELECT status,COUNT(*) n FROM attempts WHERE campaign_id=? AND revision=? GROUP BY status", (row["id"], row["revision"])):
        if value["status"] in counts:
            counts[value["status"]] = value["n"]
    row["counters"] = counts
    row["utm_url"] = BRANDS[row["brand"]]["website"] + "/?utm_source=" + ("email" if row["channel"] == "email" else "textbee") + "&utm_medium=" + row["channel"] + "&utm_campaign=" + row["id"]
    return row


class Blob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def crypt(value, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required")
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    operation = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p if decrypt else ctypes.c_wchar_p,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    operation.restype = ctypes.c_int
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    description = None if decrypt else "AI-BS brand TextBee connection"
    if not operation(ctypes.byref(source), description, None, None, None, 1, ctypes.byref(target)):
        raise RuntimeError("DPAPI operation failed")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel32.LocalFree(target.data)


def connection_path(owner, selected):
    return DATA / owner_hash(owner) / "private" / (brand(selected) + "-textbee.json")


def read_connection(owner, selected):
    path = connection_path(owner, selected)
    if not path.exists():
        return None
    envelope = json.loads(path.read_text(encoding="utf-8"))
    return json.loads(crypt(base64.b64decode(envelope["protected"]), decrypt=True))


def connection_status(owner, selected):
    selected = brand(selected)
    saved = read_connection(owner, selected)
    verification = {}
    path = connection_path(owner, selected)
    if saved and path.exists():
        verification = json.loads(path.read_text(encoding="utf-8")).get("last_verification", {})
    return {"brand": selected, "configured": bool(saved and saved.get("api_key")), "device_id": saved.get("device_id", "") if saved else "",
            "verified": verification.get("verified", False), "device_online": verification.get("device_online", "unknown"),
            "online": verification.get("online"), "last_verification": verification}


def save_connection(owner, payload):
    selected = brand(payload.get("brand"))
    device = payload.get("device_id", "")
    secret = payload.get("api_key", "")
    if not isinstance(device, str) or not re.fullmatch(r"[a-fA-F0-9]{24}", device) or not isinstance(secret, str) or len(secret) > 4000:
        fail(400, "Valid TextBee device ID and bounded API key required")
    if not secret:
        previous = read_connection(owner, selected)
        secret = previous.get("api_key", "") if previous else ""
    if not secret:
        fail(400, "Enter the TextBee API key in the local connection form")
    path = connection_path(owner, selected)
    path.parent.mkdir(parents=True, exist_ok=True)
    protected = crypt(json.dumps({"api_key": secret, "device_id": device.lower()}).encode())
    temporary = path.with_suffix(".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump({"protected": base64.b64encode(protected).decode(), "protection": "Windows DPAPI current user"}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {**connection_status(owner, selected), "secret_saved": True}


def verify_connection(owner, selected):
    selected = brand(selected)
    saved = read_connection(owner, selected)
    if not saved:
        fail(409, "Configure the brand TextBee connection first")
    path = connection_path(owner, selected)
    original_ciphertext = json.loads(path.read_text(encoding="utf-8"))["protected"]
    request = URLRequest("https://api.textbee.dev/api/v1/gateway/devices", headers={"x-api-key": saved["api_key"], "Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as result:
            raw = result.read(65537)
            if len(raw) > 65536:
                raise ValueError("Oversized provider response")
            devices = json.loads(raw).get("data", [])
        if not isinstance(devices, list):
            raise ValueError("Invalid devices response")
    except Exception:
        fail(502, "TextBee device verification failed; no SMS was sent")
    device = next((row for row in devices if isinstance(row, dict) and row.get("_id") == saved["device_id"]), None)
    result = {"brand": selected, "configured": True, "api_key_verified": True, "verified": device is not None,
              "device_verified": device is not None, "online": None, "device_online": "unknown", "checked_at": now()}
    if device is None:
        result["reason"] = "Device not registered for this API key"
    else:
        enabled = device.get("enabled") if isinstance(device.get("enabled"), bool) else None
        revoked = device.get("apiKeyRevoked") if isinstance(device.get("apiKeyRevoked"), bool) else None
        heartbeat = str(device.get("lastHeartbeat", ""))[:80]
        interval = device.get("heartbeatIntervalMinutes")
        interval = interval if type(interval) in (int, float) and 0 < interval <= 1440 else None
        age = None
        try:
            parsed = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                age = datetime.now(timezone.utc).timestamp() - parsed.timestamp()
        except (ValueError, OverflowError):
            pass
        threshold = max(180, interval * 60 + 120) if interval is not None else None
        online = None
        if enabled is True and revoked is False and age is not None and age >= 0 and threshold is not None:
            online = age <= threshold
        result.update({"device_name": str(device.get("name", ""))[:120], "enabled": enabled,
                       "online": online, "device_online": online if online is not None else "unknown",
                       "last_heartbeat": heartbeat, "app_version": str(device.get("appVersionName", ""))[:40],
                       "online_basis": "recent heartbeat" if online is True else "stale heartbeat" if online is False else "insufficient heartbeat metadata"})
    # Only the sanitized verification projection is stored beside the existing ciphertext.
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if envelope.get("protected") != original_ciphertext:
        fail(409, "Connection changed during verification; verify again")
    envelope["last_verification"] = result
    temporary = path.with_suffix(".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(envelope, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return result


def ses_path(owner, selected):
    return DATA / owner_hash(owner) / "private" / (brand(selected) + "-ses.json")


def ses_status(owner, selected):
    selected = brand(selected)
    path = ses_path(owner, selected)
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    domain = BRANDS[selected]["website"].split("//")[1]
    verification = saved.get("last_verification", {})
    sender = saved.get("sender_email", "julie@" + domain)
    return {"brand": selected, "provider": "aws_ses", "configured": bool(saved),
            "profile": SES_PROFILE, "region": SES_REGION, "domain": domain,
            "sender_email": sender, "sender": sender, "reply_to": saved.get("reply_to", "brett@stehouwerproductions.com"),
            "mailbox_qualified": False, "reply_mailbox_qualified": False,
            "domain_identity_verified": verification.get("domain_identity_verified", False),
            "verified": verification.get("verified", False), "connection_verified": verification.get("verified", False),
            "last_verification": verification, "held": True, "hold_reason": HOLD,
            **{k: verification[k] for k in ("domain_verification_status", "dkim_status", "sandbox", "quota", "current_plan", "account_plan", "checked_at") if k in verification}}


def write_private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def save_ses(owner, payload):
    if not isinstance(payload, dict) or set(payload) - {"brand", "sender_email", "sender", "reply_to", "domain", "profile", "region"}:
        fail(400, "SES setup accepts sender metadata only; AWS credentials are never accepted")
    selected = brand(payload.get("brand"))
    domain = BRANDS[selected]["website"].split("//")[1]
    sender = email(payload.get("sender_email", payload.get("sender", "julie@" + domain)))
    reply = email(payload.get("reply_to", "brett@stehouwerproductions.com"))
    if not sender or sender.split("@", 1)[1] != domain or reply not in {"brett@stehouwerproductions.com", "footballstar0325@gmail.com"}:
        fail(400, "Use a sender on the selected brand domain and the approved reply address")
    if payload.get("domain", domain) != domain or payload.get("profile", SES_PROFILE) != SES_PROFILE or payload.get("region", SES_REGION) != SES_REGION:
        fail(400, "SES domain, profile and region are fixed by the owned brand setup")
    write_private_json(ses_path(owner, selected), {"brand": selected, "sender_email": sender, "reply_to": reply, "updated_at": now()})
    return ses_status(owner, selected)


def verify_ses(owner, selected):
    selected = brand(selected)
    path = ses_path(owner, selected)
    if not path.exists():
        fail(409, "Save the brand SES sender configuration first")
    original = path.read_bytes()
    saved = json.loads(original)
    domain = BRANDS[selected]["website"].split("//")[1]
    try:
        verification = read_ses_status(domain)
    except Exception:
        fail(502, "AWS SES readiness check unavailable; no email was sent")
    if path.read_bytes() != original:
        fail(409, "SES configuration changed; verify the saved configuration again")
    saved["last_verification"] = {**verification, "checked_at": now()}
    write_private_json(path, saved)
    return ses_status(owner, selected)


def providers(owner):
    values = {}
    for selected, info in BRANDS.items():
        candidate = email(os.getenv("BRAND_" + selected.upper() + "_SENDER_EMAIL", ""))
        domain = info["website"].split("//")[1]
        sender = candidate if candidate.endswith("@" + domain) else ""
        sms = connection_status(owner, selected)
        values[selected] = {"email": {**ses_status(owner, selected), "legacy_sender_configured": bool(sender)},
                            "sms": {**sms, "held": True, "hold_reason": HOLD}}
    return values


def state(owner):
    with database(owner) as conn:
        metadata = contact_research(conn)
        return {"brands": list(BRANDS.values()), "contacts": [{**dict(v), "research_metadata": metadata.get(v["id"], {}), "selected": False} for v in conn.execute("SELECT * FROM contacts ORDER BY rowid")],
                "imports": [dict(v) for v in conn.execute("SELECT * FROM imports ORDER BY created_at DESC")],
                "campaigns": [campaign_dict(dict(v), conn) for v in conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC")],
                "providers": providers(owner), "historical_suppressions_available": historical_suppressions(owner) is not None,
                "dispatch_held": True}


class OwnerRoute(AdminHostControlRoute):
    def get_route_handler(self):
        inherited = super().get_route_handler()
        async def owned(request):
            principal = await require_host_admin(request)
            owner_hash(principal)
            request.state.campaign_owner = principal
            size = 0
            body = bytearray()
            async for chunk in request.stream():
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    fail(413, "Campaign request exceeds 2 MB")
                body.extend(chunk)
            request._body = bytes(body)
            return await inherited(request)
        return owned


app = FastAPI(title="AI-BS Brand Campaign Manager", docs_url=None, redoc_url=None, openapi_url=None)
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
for value in os.getenv("BRAND_CAMPAIGN_ALLOWED_ORIGINS", "").split(","):
    if re.fullmatch(r"http://192\.168\.\d{1,3}\.\d{1,3}:5173", value.strip()):
        origins.append(value.strip())
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "OPTIONS"], allow_headers=["Authorization", "Content-Type"], allow_credentials=False)
router = APIRouter(prefix="/api/brand-campaigns", route_class=OwnerRoute)


@app.get("/health")
def health():
    return {"status": "ready", "dispatch_held": True}


@router.get("/state")
def get_state(request: Request):
    return state(request.state.campaign_owner)


@router.get("/providers")
def get_providers(request: Request):
    return providers(request.state.campaign_owner)


@router.get("/outreach-records/{selected}")
def get_outreach_records(selected: str, request: Request):
    return read_records(owner_hash(request.state.campaign_owner), brand(selected))


@router.post("/import")
async def post_import(request: Request):
    return import_contacts(request.state.campaign_owner, await request.json())


@router.post("/campaigns")
async def create(request: Request):
    return {"campaign": save_campaign(request.state.campaign_owner, await request.json())}


@router.put("/campaigns/{identifier}")
async def update(identifier: str, request: Request):
    return {"campaign": save_campaign(request.state.campaign_owner, await request.json(), identifier)}


@router.post("/campaigns/{identifier}/prepare")
async def stage(identifier: str, request: Request):
    payload = await request.json()
    return prepare(request.state.campaign_owner, identifier, payload.get("revision"))


@router.post("/campaigns/{identifier}/send")
def send_held(identifier: str, request: Request):
    fail(503, HOLD)


@router.post("/suppressions")
async def suppress(request: Request):
    payload = await request.json()
    channel = payload.get("channel")
    address = email(payload.get("address")) if channel == "email" else phone(payload.get("address")) if channel == "sms" else ""
    if not address:
        fail(400, "Valid suppression channel and address required")
    with database(request.state.campaign_owner) as conn:
        conn.execute("INSERT OR IGNORE INTO suppressions VALUES(?,?,?,?)", (channel, address, str(payload.get("reason", "owner request"))[:300], now()))
    return {"saved": True}


@router.post("/connections/textbee")
async def connect(request: Request):
    return await asyncio.to_thread(save_connection, request.state.campaign_owner, await request.json())


@router.get("/connections/textbee/{selected}")
def connection(selected: str, request: Request):
    return connection_status(request.state.campaign_owner, selected)


@router.post("/connections/textbee/{selected}/verify")
async def verify(selected: str, request: Request):
    return await asyncio.to_thread(verify_connection, request.state.campaign_owner, selected)


@router.post("/connections/ses")
async def connect_ses(request: Request):
    return await asyncio.to_thread(save_ses, request.state.campaign_owner, await request.json())


@router.get("/connections/ses/{selected}")
def get_ses(selected: str, request: Request):
    return ses_status(request.state.campaign_owner, selected)


@router.post("/connections/ses/{selected}/verify")
async def check_ses(selected: str, request: Request):
    return await asyncio.to_thread(verify_ses, request.state.campaign_owner, selected)


app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5191)
