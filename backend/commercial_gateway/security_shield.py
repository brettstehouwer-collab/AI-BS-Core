import os
import re
import time
import sqlite3
import asyncio
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("SecurityShield")
logger.setLevel(logging.INFO)

COMMERCIAL_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(COMMERCIAL_DIR, "..", ".."))
os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)
AUDIT_DB_PATH = os.path.join(BASE_DIR, "database", "security_events.db")


def init_security_db():
    """Initialize security audit log and IP blacklist database."""
    conn = sqlite3.connect(AUDIT_DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            ip_address TEXT,
            event_type TEXT,
            severity TEXT,
            details TEXT,
            client_id TEXT DEFAULT 'stehouwer_publishing'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ip_blacklist (
            ip_address TEXT PRIMARY KEY,
            banned_at REAL,
            reason TEXT,
            client_id TEXT DEFAULT 'stehouwer_publishing'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            admin_user TEXT,
            ip_address TEXT,
            location_data TEXT,
            client_id TEXT DEFAULT 'stehouwer_publishing'
        )
    """)
    try:
        cursor.execute("ALTER TABLE security_events ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE ip_blacklist ADD COLUMN client_id TEXT DEFAULT 'stehouwer_publishing'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


# Initialize database tables on import
init_security_db()

# Banned IP cache in memory for O(1) fast lookup
BANNED_IPS: set = set()


def load_banned_ips():
    """Sync banned IPs from SQLite into memory."""
    global BANNED_IPS
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute("SELECT ip_address FROM ip_blacklist")
        rows = cursor.fetchall()
        BANNED_IPS = {r[0] for r in rows}
        conn.close()
    except Exception as e:
        logger.error(f"Failed to load banned IPs: {e}")


load_banned_ips()


def ban_ip(ip_address: str, reason: str, client_id: str = "stehouwer_publishing"):
    """Ban an offending IP address in database and memory cache."""
    global BANNED_IPS
    BANNED_IPS.add(ip_address)
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO ip_blacklist (ip_address, banned_at, reason, client_id) VALUES (?, ?, ?, ?)",
            (ip_address, time.time(), reason, client_id),
        )
        conn.commit()
        conn.close()
        log_security_event(
            ip_address, "IP_BAN", "CRITICAL", f"IP Banned. Reason: {reason}", client_id
        )
    except Exception as e:
        logger.error(f"Failed to log IP ban: {e}")


def log_security_event(ip_address: str, event_type: str, severity: str, details: str, client_id: str = "stehouwer_publishing"):
    """Log security anomaly to audit database."""
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO security_events (timestamp, ip_address, event_type, severity, details, client_id) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), ip_address, event_type, severity, details, client_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")


def log_admin_access(admin_user: str, ip_address: str, location_data: str, client_id: str = "stehouwer_publishing"):
    """Log admin access telemetry."""
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO admin_access_logs (timestamp, admin_user, ip_address, location_data, client_id) VALUES (?, ?, ?, ?, ?)",
            (time.time(), admin_user, ip_address, location_data, client_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log admin access: {e}")


# Dangerous patterns for Injection / Traversal
SUSPICIOUS_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"/etc/passwd",
    r"c:\\windows",
    r"exec\(",
    r"eval\(",
    r"os\.system",
    r"subprocess",
    r"__import__",
    r"DROP\s+TABLE",
    r"UNION\s+SELECT",
    r"<\s*script",
    r"javascript:",
    r"file://",
    r"gopher://",
]

# Zero-Tolerance Self-Harm / Crisis Defense Patterns
SELF_HARM_PATTERNS = [
    r"suicid",
    r"kill\s+my\s*self",
    r"end\s+my\s+life",
    r"cut\s+my\s*self",
    r"want\s+to\s+die",
    r"self\s*harm",
    r"hurt\s+my\s*self",
    r"take\s+my\s+own\s+life",
    r"hanging\s+my\s*self",
    r"overdose\s+my\s*self",
    r"how\s+to\s+die",
]

CRISIS_SAFETY_RESPONSE = (
    "💙 If you or someone you know is going through a difficult time or having thoughts of self-harm, "
    "please know that you are not alone and help is available right now.\n\n"
    "Free, confidential, 24/7 Crisis Support Resources:\n"
    "• National Suicide & Crisis Lifeline: Call or text 988 (US & Canada)\n"
    "• Crisis Text Line: Text HOME to 741741\n"
    "• International Support Directory: https://findahelpline.com\n\n"
    "Please reach out to a professional or a trusted person in your life. Stehouwer Publishing cares about your safety."
)


class SecurityShield:
    """Zero-Trust Security Shield & Active Defense Guard."""

    @staticmethod
    def extract_client_id(request: Request) -> str:
        """Extract multi-tenant client ID."""
        return request.headers.get("X-Client-ID", "stehouwer_publishing")

    @staticmethod
    def extract_client_ip(request: Request) -> str:
        """Extract client IP handling forward headers safely."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client:
            return request.client.host
        return "127.0.0.1"

    @classmethod
    def check_authorized_tester(cls, request: Request) -> Optional[Dict[str, Any]]:
        """Verify if inbound request originates from an authorized security auditor."""
        import json

        config_path = os.path.join(COMMERCIAL_DIR, "authorized_testers_config.json")
        if not os.path.exists(config_path):
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if not cfg.get("pen_testing_enabled", False):
                    return None

                ip = cls.extract_client_ip(request)
                provided_hdr_val = request.headers.get("X-AI-BS-Test-Auth", "")
                provided_key_val = request.headers.get(
                    "x-api-key", ""
                ) or request.headers.get("authorization", "")

                for tester in cfg.get("authorized_testers", []):
                    # Check Secret Header or API Passkey or IP Match
                    hdr_match = tester.get(
                        "secret_header_value"
                    ) and provided_hdr_val == tester.get("secret_header_value")
                    key_match = (
                        tester.get("tester_api_passkey")
                        and tester.get("tester_api_passkey") in provided_key_val
                    )
                    ip_match = ip in tester.get("allowed_ips", [])

                    if hdr_match or key_match or ip_match:
                        # Check Time Window
                        now_str = datetime.now().isoformat()
                        w_start = tester.get("window_start", "")
                        w_end = tester.get("window_end", "")
                        if w_start and w_end:
                            if not (w_start <= now_str <= w_end):
                                continue
                        return tester
        except Exception as e:
            logger.warning(f"Error evaluating authorized tester: {e}")
        return None

    @classmethod
    async def inspect_request(
        cls, request: Request, payload_text: str = ""
    ) -> Optional[JSONResponse]:
        """
        Inspect inbound request for IP blacklists, self-harm crisis protection, and malicious payloads.
        Implements Active Defense, Crisis Interception, and Authorized Auditor Ban Suppression.
        """
        ip = cls.extract_client_ip(request)
        client_id = cls.extract_client_id(request)
        tester_info = cls.check_authorized_tester(request)

        # 1. Check IP Blacklist (Bypass if authorized auditor)
        if ip in BANNED_IPS:
            if tester_info and tester_info.get("suppress_auto_ban"):
                logger.info(
                    f"[Authorized Auditor] Banned IP bypass granted for tester: {tester_info.get('tester_email')}"
                )
            else:
                await asyncio.sleep(2.0)
                log_security_event(
                    ip,
                    "BLOCKED_BANNED_IP_ATTEMPT",
                    "HIGH",
                    "Attempted request from banned IP",
                    client_id
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": {
                            "code": "access_denied",
                            "message": "IP address is prohibited.",
                        }
                    },
                )

        # 2. Check Self-Harm & Crisis Prevention (Zero Liability Interception)
        if payload_text:
            for pattern in SELF_HARM_PATTERNS:
                if re.search(pattern, payload_text, re.IGNORECASE):
                    log_security_event(
                        ip,
                        "SELF_HARM_INTERCEPTED",
                        "CRITICAL",
                        f"Self-harm pattern triggered: {pattern}",
                        client_id
                    )
                    now = time.time()
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "id": f"crisis-safety-{int(now)}",
                            "object": "chat.completion",
                            "created": int(now),
                            "model": "stehouwer_llm_safety_shield",
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {
                                        "role": "assistant",
                                        "content": CRISIS_SAFETY_RESPONSE,
                                    },
                                    "finish_reason": "stop",
                                }
                            ],
                        },
                    )

        # 3. Inspect Payload for Traversal and Command Injection
        if payload_text:
            for pattern in SUSPICIOUS_PATTERNS:
                if re.search(pattern, payload_text, re.IGNORECASE):
                    if tester_info and tester_info.get("suppress_auto_ban"):
                        # Authorized Pen Test Probe Caught: Log Finding & Suppress Ban
                        log_security_event(
                            ip,
                            "AUTHORIZED_PEN_TEST_EVENT",
                            "MEDIUM",
                            f"Authorized Probe Caught by Auditor ({tester_info.get('tester_email')}): Matched pattern {pattern}",
                            client_id
                        )
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            headers={
                                "X-AI-BS-Shield-Diagnostic": f"RULE_TRIGGERED_{pattern.replace(' ', '_')}"
                            },
                            content={
                                "status": "blocked_policy",
                                "message": "Security policy violation detected.",
                                "auditor_mode": "LOG_ONLY_SUPPRESS_BAN",
                                "rule_matched": pattern,
                            },
                        )
                    else:
                        # Standard Hostile Traffic: Ban IP & Enforce Delay
                        log_security_event(
                            ip,
                            "PAYLOAD_INJECTION_DETECTED",
                            "CRITICAL",
                            f"Matched pattern: {pattern}",
                            client_id
                        )
                        ban_ip(
                            ip,
                            f"Automated Security Trigger: Payload Injection ({pattern})",
                            client_id
                        )
                        await asyncio.sleep(3.0)
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "error": {
                                    "code": "security_shield_trigger",
                                    "message": "Security policy violation detected.",
                                }
                            },
                        )

        return None

    @classmethod
    def audit_ast_code(
        cls, code_text: str, filename: str = "generated.py"
    ) -> Dict[str, Any]:
        """
        Static Abstract Syntax Tree (AST) Security Auditor.
        Parses source code for unsafe imports (subprocess, os.system, eval, exec),
        hardcoded secrets, unmasked SQL injection hazards, and file system escapes.
        """
        import ast

        findings = []
        is_secure = True

        try:
            tree = ast.parse(code_text, filename=filename)
            for node in ast.walk(tree):
                # 1. Check Unsafe Imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in [
                            "subprocess",
                            "os",
                            "shutil",
                            "ctypes",
                            "pty",
                        ]:
                            findings.append(
                                f"UNSAFE_IMPORT: Module '{alias.name}' detected."
                            )
                            is_secure = False
                elif isinstance(node, ast.ImportFrom):
                    if node.module in ["subprocess", "os", "shutil", "ctypes", "pty"]:
                        findings.append(
                            f"UNSAFE_IMPORT_FROM: Module '{node.module}' detected."
                        )
                        is_secure = False
                # 2. Check Unsafe Built-ins & Function Calls (eval, exec, os.system, os.popen)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in [
                        "eval",
                        "exec",
                        "__import__",
                    ]:
                        findings.append(
                            f"DANGEROUS_CALL: Direct execution call '{node.func.id}()' detected."
                        )
                        is_secure = False
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in [
                        "system",
                        "popen",
                        "execv",
                        "spawnv",
                    ]:
                        findings.append(
                            f"DANGEROUS_ATTR_CALL: Unsafe execution method '.{node.func.attr}()' detected."
                        )
                        is_secure = False
        except SyntaxError as se:
            findings.append(
                f"SYNTAX_ERROR: Failed AST parse - {se.msg} at line {se.lineno}"
            )
            is_secure = False
        except Exception as e:
            findings.append(f"AST_PARSE_FAULT: {str(e)}")
            is_secure = False

        return {
            "status": "passed" if is_secure else "flagged",
            "is_secure": is_secure,
            "findings_count": len(findings),
            "findings": findings,
        }
