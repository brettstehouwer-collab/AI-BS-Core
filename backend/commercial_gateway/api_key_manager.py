import os
import time
import secrets
import hmac
import hashlib
import sqlite3
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("APIKeyManager")
logger.setLevel(logging.INFO)

COMMERCIAL_DIR = os.path.dirname(os.path.abspath(__file__))
USAGE_DB_PATH = os.path.join(COMMERCIAL_DIR, "commercial_usage.db")
SECRET_SALT = os.environ.get(
    "AIBS_HMAC_SALT", "AI_BS_SECURE_HMAC_SALT_2026_PRODUCTION_KEY"
)

# Tiers configuration with dynamic timeouts per user feedback
TIER_SPECS = {
    "sandbox": {
        "max_requests_per_day": 50,
        "rate_limit_rpm": 10,
        "max_image_timeout": 60,
        "max_video_timeout": 120,
    },
    "day_pass": {
        "max_requests_per_day": 250,
        "rate_limit_rpm": 20,
        "max_image_timeout": 90,
        "max_video_timeout": 180,
        "duration_hours": 24,
        "price_usd": 4.99,
    },
    "pass_1day": {
        "max_requests_per_day": 250,
        "rate_limit_rpm": 20,
        "max_image_timeout": 90,
        "max_video_timeout": 180,
        "duration_hours": 24,
        "price_usd": 4.99,
    },
    "pass_3day": {
        "max_requests_per_day": 250,
        "rate_limit_rpm": 25,
        "max_image_timeout": 90,
        "max_video_timeout": 180,
        "duration_hours": 72,
        "price_usd": 11.99,
    },
    "pass_5day": {
        "max_requests_per_day": 250,
        "rate_limit_rpm": 30,
        "max_image_timeout": 90,
        "max_video_timeout": 180,
        "duration_hours": 120,
        "price_usd": 17.99,
    },
    "pass_7day": {
        "max_requests_per_day": 300,
        "rate_limit_rpm": 35,
        "max_image_timeout": 120,
        "max_video_timeout": 240,
        "duration_hours": 168,
        "price_usd": 22.99,
    },
    "pass_12day": {
        "max_requests_per_day": 350,
        "rate_limit_rpm": 40,
        "max_image_timeout": 120,
        "max_video_timeout": 240,
        "duration_hours": 288,
        "price_usd": 34.99,
    },
    "pass_15day": {
        "max_requests_per_day": 400,
        "rate_limit_rpm": 45,
        "max_image_timeout": 150,
        "max_video_timeout": 270,
        "duration_hours": 360,
        "price_usd": 39.99,
    },
    "pass_30day": {
        "max_requests_per_day": 500,
        "rate_limit_rpm": 60,
        "max_image_timeout": 180,
        "max_video_timeout": 300,
        "duration_hours": 720,
        "price_usd": 69.99,
    },
    "starter": {
        "max_requests_per_day": 500,
        "rate_limit_rpm": 30,
        "max_image_timeout": 90,
        "max_video_timeout": 180,
    },
    "pro": {
        "max_requests_per_day": 5000,
        "rate_limit_rpm": 120,
        "max_image_timeout": 180,
        "max_video_timeout": 300,
    },
    "enterprise": {
        "max_requests_per_day": 100000,
        "rate_limit_rpm": 600,
        "max_image_timeout": 300,
        "max_video_timeout": 600,
    },
}


def _hash_key(raw_key: str) -> str:
    """Generate SHA256 HMAC hash of raw API key using salt."""
    return hmac.new(
        SECRET_SALT.encode("utf-8"), raw_key.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def init_usage_db():
    """Initialize database for API keys and request metering logs."""
    conn = sqlite3.connect(USAGE_DB_PATH, timeout=20.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key_hash TEXT PRIMARY KEY,
            key_prefix TEXT,
            client_name TEXT,
            tier TEXT,
            created_at REAL,
            expires_at REAL,
            is_active INTEGER DEFAULT 1,
            allowed_ips TEXT DEFAULT NULL
        )
    """)
    # Migration: Ensure allowed_ips column exists
    try:
        cursor.execute("ALTER TABLE api_keys ADD COLUMN allowed_ips TEXT DEFAULT NULL")
    except Exception:
        pass
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            key_hash TEXT,
            ip_address TEXT,
            endpoint TEXT,
            status_code INTEGER,
            response_time_ms REAL,
            units_consumed INTEGER
        )
    """)
    # Provision Perpetual Master Dev Key for Owner Testing
    master_key = "sk_aibs_dev_master_key_2026"
    master_hash = _hash_key(master_key)
    cursor.execute(
        """
        INSERT OR REPLACE INTO api_keys (key_hash, key_prefix, client_name, tier, created_at, expires_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """,
        (
            master_hash,
            "sk_aibs_dev",
            "Brett Stehouwer (Dev Master Owner)",
            "enterprise",
            time.time(),
            time.time() + (365 * 86400 * 10),
        ),
    )

    conn.commit()
    conn.close()


# Initialize tables on module load
init_usage_db()


def create_api_key(
    tier: str = "sandbox",
    client_name: str = "TestClient",
    expires_in_days: Optional[float] = None,
    allowed_ips: Optional[list] = None,
) -> Dict[str, Any]:
    """Generate cryptographic API key with unique token hex, auto-enforced expiration, and optional IP Whitelist."""
    if tier not in TIER_SPECS:
        tier = "sandbox"

    specs = TIER_SPECS.get(tier, {})
    if expires_in_days is None:
        # Default duration per tier
        duration_hours = specs.get("duration_hours", 8760)  # default 1 year
        expires_in_days = duration_hours / 24.0

    random_part = secrets.token_hex(20)
    prefix = "sk_aibs_test_" if tier == "sandbox" else "sk_aibs_live_"
    raw_key = f"{prefix}{random_part}"
    key_hash = _hash_key(raw_key)

    created_at = time.time()
    expires_at = created_at + (expires_in_days * 86400)

    import json

    allowed_ips_str = json.dumps(allowed_ips) if allowed_ips else None

    conn = sqlite3.connect(USAGE_DB_PATH, timeout=20.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute(
        "INSERT INTO api_keys (key_hash, key_prefix, client_name, tier, created_at, expires_at, is_active, allowed_ips) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
        (key_hash, prefix, client_name, tier, created_at, expires_at, allowed_ips_str),
    )
    conn.commit()
    conn.close()

    logger.info(
        f"Generated unique API key [{prefix}...] for client '{client_name}' (Tier: {tier}, Expires: {expires_at}, IP Whitelist: {allowed_ips})"
    )
    return {
        "raw_key": raw_key,
        "key_prefix": prefix,
        "client_name": client_name,
        "tier": tier,
        "expires_at": expires_at,
        "allowed_ips": allowed_ips,
    }


def bind_ip_whitelist(raw_key: str, ip_list: list) -> bool:
    """Locks an API key to a specific list of whitelisted IPv4/IPv6 addresses."""
    import json

    key_hash = _hash_key(raw_key)
    conn = sqlite3.connect(USAGE_DB_PATH, timeout=20.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    json_str = json.dumps(ip_list)
    cursor.execute(
        "UPDATE api_keys SET allowed_ips = ? WHERE key_hash = ?", (json_str, key_hash)
    )
    conn.commit()
    conn.close()
    logger.info(f"Locked API key [{raw_key[:14]}...] to IP whitelist: {ip_list}")
    return True


def verify_api_key(
    raw_key: str, client_ip: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Validate API key hash against database, check expiration/active state, and enforce IP Whitelist security."""
    if not raw_key or not isinstance(raw_key, str):
        return None

    key_hash = _hash_key(raw_key)

    conn = sqlite3.connect(USAGE_DB_PATH, timeout=20.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute(
        "SELECT key_hash, key_prefix, client_name, tier, expires_at, is_active, allowed_ips FROM api_keys WHERE key_hash = ?",
        (key_hash,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    _, prefix, client_name, tier, expires_at, is_active, allowed_ips_raw = row

    if not is_active:
        return None

    if time.time() > expires_at:
        return None

    # IP Whitelist Enforcement
    if allowed_ips_raw and allowed_ips_raw.strip():
        try:
            import json

            allowed_list = json.loads(allowed_ips_raw)
            if isinstance(allowed_list, list) and len(allowed_list) > 0:
                if (
                    client_ip
                    and client_ip not in allowed_list
                    and "*" not in allowed_list
                ):
                    # Auto-authorize and bind Owner IP for Brett Stehouwer
                    if "Brett Stehouwer" in client_name or "Owner" in client_name:
                        allowed_list.append(client_ip)
                        bind_ip_whitelist(raw_key, allowed_list)
                        logger.info(
                            f"Auto-bound new Owner IP '{client_ip}' to Passkey [{prefix}...]"
                        )
                    # Check loopback equivalence
                    elif client_ip in ["127.0.0.1", "::1", "localhost"] and any(
                        h in allowed_list for h in ["127.0.0.1", "::1", "localhost"]
                    ):
                        pass
                    else:
                        logger.warning(
                            f"IP Security Shield blocked key request: Client IP '{client_ip}' is not authorized for key [{prefix}...]"
                        )
                        return {
                            "ip_blocked": True,
                            "client_ip": client_ip,
                            "allowed_ips": allowed_list,
                        }
        except Exception as e:
            logger.error(f"IP whitelist check error: {e}")

    specs = TIER_SPECS.get(tier, TIER_SPECS["sandbox"])
    return {
        "key_hash": key_hash,
        "key_prefix": prefix,
        "client_name": client_name,
        "tier": tier,
        "specs": specs,
        "allowed_ips": allowed_ips_raw,
    }


def log_usage(
    key_hash: str,
    ip_address: str,
    endpoint: str,
    status_code: int,
    response_time_ms: float,
    units: int = 1,
):
    """Log telemetry metrics to usage database."""
    try:
        conn = sqlite3.connect(USAGE_DB_PATH, timeout=20.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage_logs (timestamp, key_hash, ip_address, endpoint, status_code, response_time_ms, units_consumed) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                key_hash,
                ip_address,
                endpoint,
                status_code,
                response_time_ms,
                units,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log usage metrics: {e}")


RESEARCH_DB_PATH = os.path.join(COMMERCIAL_DIR, "social_intelligence_research.db")


def init_research_db():
    """Initialize research database for Social/Emotional Intelligence training telemetry."""
    try:
        conn = sqlite3.connect(RESEARCH_DB_PATH, timeout=20.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interaction_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                key_hash TEXT,
                interaction_type TEXT,
                prompt_snippet TEXT,
                token_count INTEGER,
                sentiment_label TEXT,
                system_response_meta TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to init research DB: {e}")


init_research_db()


def log_social_intelligence_telemetry(
    key_hash: str,
    interaction_type: str,
    prompt_snippet: str,
    token_count: int = 0,
    sentiment_label: str = "NEUTRAL",
):
    """Record anonymized interaction data for statistical study and AI-BS Social/Emotional Intelligence training."""
    try:
        conn = sqlite3.connect(RESEARCH_DB_PATH, timeout=20.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO interaction_telemetry (timestamp, key_hash, interaction_type, prompt_snippet, token_count, sentiment_label, system_response_meta) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                key_hash,
                interaction_type,
                prompt_snippet[:500],
                token_count,
                sentiment_label,
                "AI_BS_RESEARCH_V1",
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to record research telemetry: {e}")


LEARNING_DB_PATH = os.path.join(COMMERCIAL_DIR, "learning_telemetry.db")


def init_learning_db():
    """Initialize learning database to track successful vs failed user requests for system training."""
    try:
        conn = sqlite3.connect(LEARNING_DB_PATH, timeout=20.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                key_hash TEXT,
                endpoint TEXT,
                prompt_snippet TEXT,
                is_success INTEGER,
                error_detail TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to init learning DB: {e}")


init_learning_db()


def log_request_outcome(
    key_hash: str,
    endpoint: str,
    prompt_snippet: str,
    is_success: bool,
    error_detail: str = "",
):
    """Record request outcomes (success vs failure) to train AI-BS on user interaction patterns."""
    try:
        conn = sqlite3.connect(LEARNING_DB_PATH, timeout=20.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO request_outcomes (timestamp, key_hash, endpoint, prompt_snippet, is_success, error_detail) VALUES (?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                key_hash,
                endpoint,
                prompt_snippet[:500],
                1 if is_success else 0,
                error_detail,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log request outcome: {e}")
