"""AI-BS Exclusive Execution Gateway, Durable Authority Store & Failover State Machine.

Implements AI-BS-HA-OCI-001 / AI-BS-HA-OCI-001-AGENTS (Sections 5, 7, 8, 9):
  - Single SQLite WAL + BEGIN IMMEDIATE AuthorityStore and pre-dispatch Execution Journal
  - Monotonically increasing authority_epoch fencing & serialized _dispatch_lock
  - Decimal-exact TEXT accounting and idempotent fill deduplication
  - Technical passive-mode barrier (PassiveStandbyClient cannot mutate the exchange)
  - Separate Dual-Key credential resolution (Read-Only observer key vs Gateway Trade key)
  - FailoverStateMachine with non-bypassable technical gates & clock-jump detection
  - Consistent sqlite3.Connection.backup() snapshotting & passive restore verification

Portable across Windows (x64) and OCI ARM64 Linux (aarch64) using Python stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Callable, Protocol
import uuid


DECIMAL_ZERO = Decimal("0")
USDT_QUANT = Decimal("0.000001")
PRICE_QUANT = Decimal("0.00001")
DEFAULT_PROFIT_RESERVE_SHARE = Decimal("0.50")
DEFAULT_MAX_CLOCK_JUMP_SEC = 15.0

MUTATION_ACTIONS = frozenset({"CREATE", "AMEND", "CANCEL", "BULK", "REARM", "EMERGENCY"})
VALID_ROLES = frozenset({"PASSIVE", "ACTIVE", "FENCED", "SAFE_HALT", "MANUAL_REVIEW"})
UNRESOLVED_INTENT_STATUSES = ("INTENT", "SUBMITTING", "UNKNOWN")


class HAError(RuntimeError):
    """Base error for HA authority, gateway, and durability barriers."""


class StaleEpochError(HAError):
    """Raised when caller epoch is stale, revoked, fenced, or lease-expired."""


class PassiveAuthorityError(HAError):
    """Raised when a passive host or read-only client attempts any exchange mutation."""


class UnresolvedIntentError(HAError):
    """Raised when in-flight/UNKNOWN intents block new mutations until reconciled."""


class JournalDurabilityError(HAError):
    """Raised when durable SQLite journal write fails or replica is stale/corrupt."""


class ClockAnomalyError(HAError):
    """Raised when wall-clock vs monotonic-clock divergence invalidates safe lease math."""


class GateBlockedError(HAError):
    """Raised when a failover or promotion technical gate fails (even with manual approval)."""


class ExchangeRejectError(HAError):
    """Raised on deterministic non-transport exchange rejection (e.g., invalid params / POST_ONLY)."""


class ClockProtocol(Protocol):
    """Clock interface allowing deterministic monotonic + UTC wall-clock injection in tests."""

    def monotonic(self) -> float: ...
    def utc_now(self) -> datetime: ...


class SystemClock:
    """Real OS monotonic + UTC wall clock."""

    def monotonic(self) -> float:
        return time.monotonic()

    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)


class FakeClock:
    """Deterministic test clock with separate monotonic and wall-clock control (for HA-06)."""

    def __init__(self, start_mono: float = 1000.0, start_utc: datetime | None = None) -> None:
        self._mono = float(start_mono)
        self._utc = start_utc or datetime(2026, 11, 19, 18, 0, 0, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        return self._mono

    def utc_now(self) -> datetime:
        return self._utc

    def advance(self, seconds: float) -> None:
        """Advance both monotonic and wall clock uniformly."""
        self._mono += float(seconds)
        self._utc = self._utc + timedelta(seconds=float(seconds))

    def advance_monotonic_only(self, seconds: float) -> None:
        self._mono += float(seconds)

    def jump_wall(self, delta_seconds: float) -> None:
        """Inject an abrupt wall-clock forward or backward jump without matching monotonic delta."""
        self._utc = self._utc + timedelta(seconds=float(delta_seconds))


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _q6(val: Decimal) -> str:
    return f"{val.quantize(USDT_QUANT, rounding=ROUND_DOWN):.6f}"


def _d(val: Any) -> Decimal:
    return Decimal(str(val))


def _unprotect_windows_dpapi(data: bytes) -> bytes:
    """Decrypt Windows DPAPI bytes using CryptUnprotectData (Windows only)."""
    import ctypes
    import ctypes.wintypes as _wt

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", _wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    in_blob = _DATA_BLOB(len(data), buf)
    out_blob = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 1, ctypes.byref(out_blob)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def protect_windows_dpapi(plaintext: bytes) -> bytes:
    """Encrypt bytes with Windows DPAPI (CryptProtectData, CRYPTPROTECT_UI_FORBIDDEN)."""
    import ctypes
    import ctypes.wintypes as _wt

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", _wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(plaintext, len(plaintext))
    in_blob = _DATA_BLOB(len(plaintext), buf)
    out_blob = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), "AI-BS-ReadOnly-Key", None, None, None, 1, ctypes.byref(out_blob)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


DEFAULT_READONLY_DPAPI_FILE = Path(r"C:\AI-BS\backups\crypto_readonly_dpapi.json")


def _parse_env_credentials_text(text: str) -> tuple[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, v = stripped.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    key = values.get("CRYPTO_READONLY_API_KEY") or values.get("CRYPTO_API_KEY") or ""
    secret = values.get("CRYPTO_READONLY_API_SECRET") or values.get("CRYPTO_API_SECRET") or ""
    if not key or not secret:
        raise ValueError("Read-only env file missing CRYPTO_READONLY_API_KEY / CRYPTO_READONLY_API_SECRET")
    return key, secret


def load_readonly_credentials(
    cred_file: Path | str | None = None,
    *,
    allow_env: bool = True,
) -> tuple[str, str, str]:
    """Load dedicated read-only exchange API credentials without touching trade keys.

    Resolution order:
      1. Explicit `cred_file` or `AIBS_READONLY_CRED_FILE`
         - supports JSON DPAPI wrapper `{"schema": "aibs.dpapi_pair.v1", "dpapi_b64": "..."}`
         - supports DPAPI locator JSON `{"pair": "<path>"}`
         - supports Linux root-owned systemd env file (`CRYPTO_READONLY_API_KEY=...`)
      2. Process environment variables `CRYPTO_READONLY_API_KEY` + `CRYPTO_READONLY_API_SECRET`
      3. Windows default `C:\\AI-BS\\backups\\crypto_readonly_dpapi.json`

    Returns `(api_key, api_secret, source_label)` where `source_label` never contains secrets.
    """
    import base64

    candidate: Path | None = None
    if cred_file:
        candidate = Path(cred_file)
    elif os.environ.get("AIBS_READONLY_CRED_FILE"):
        candidate = Path(os.environ["AIBS_READONLY_CRED_FILE"])
    elif DEFAULT_READONLY_DPAPI_FILE.exists():
        candidate = DEFAULT_READONLY_DPAPI_FILE

    if allow_env:
        env_key = os.environ.get("CRYPTO_READONLY_API_KEY", "").strip()
        env_secret = os.environ.get("CRYPTO_READONLY_API_SECRET", "").strip()
        if env_key and env_secret:
            return env_key, env_secret, "env:CRYPTO_READONLY_API_KEY"

    if candidate is None or not candidate.exists():
        raise FileNotFoundError(
            "Dedicated read-only credential file not configured "
            f"(checked {candidate or DEFAULT_READONLY_DPAPI_FILE})"
        )

    raw_text = candidate.read_text(encoding="utf-8")
    if candidate.suffix.lower() == ".env":
        key, secret = _parse_env_credentials_text(raw_text)
        return key, secret, f"env_file:{candidate.name}"

    obj = json.loads(raw_text)
    if "dpapi_b64" in obj:
        decrypted = _unprotect_windows_dpapi(base64.b64decode(obj["dpapi_b64"]))
        pair = json.loads(decrypted.decode("utf-8"))
    elif "pair" in obj:
        pair_path = Path(obj["pair"])
        decrypted = _unprotect_windows_dpapi(pair_path.read_bytes())
        pair = json.loads(decrypted.decode("utf-8"))
    else:
        raise ValueError(f"Unsupported read-only credential format in {candidate.name}")

    role = str(pair.get("role", "READ_ONLY")).upper()
    if role not in ("READ_ONLY", "READONLY"):
        raise ValueError(f"Credential archive role mismatch: expected READ_ONLY, got {role}")
    api_key = str(pair.get("api_key", "")).strip()
    secret = str(pair.get("secret", "")).strip()
    if not api_key or not secret:
        raise ValueError("Empty API key or secret in read-only credential archive")
    return api_key, secret, f"dpapi_readonly:{candidate.name}"


@dataclass(frozen=True)
class GatewayCommand:
    """Normalized exchange mutation command submitted through ExecutionGateway."""

    owner_id: str
    epoch: int
    action: str  # CREATE | AMEND | CANCEL | BULK | REARM | EMERGENCY
    instrument: str = "CRO_USDT"
    side: str | None = None
    qty_cro: int | None = None
    price: Decimal | None = None
    order_id: str | None = None
    client_oid: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    allow_during_reconcile: bool = False

    def __post_init__(self) -> None:
        if self.action not in MUTATION_ACTIONS:
            raise ValueError(f"Invalid gateway action: {self.action!r}")


class AuthorityStore:
    """Durable SQLite WAL authority ledger, monotonic epoch store, and execution journal."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        clock: ClockProtocol | None = None,
        max_clock_jump_sec: float = DEFAULT_MAX_CLOCK_JUMP_SEC,
        read_only_uri: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.clock: ClockProtocol = clock or SystemClock()
        self.max_clock_jump_sec = float(max_clock_jump_sec)
        self.read_only_uri = bool(read_only_uri)
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._lease_service_available = True
        self._alerts: list[dict[str, Any]] = []
        if not self.read_only_uri:
            self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        try:
            if self.read_only_uri:
                uri = f"file:{self.db_path.as_posix()}?mode=ro"
                conn = sqlite3.connect(uri, uri=True, timeout=5.0, check_same_thread=False)
            else:
                if self.db_path.exists() and self.db_path.is_dir():
                    raise JournalDurabilityError(f"Journal path is a directory, not a database: {self.db_path}")
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False, isolation_level=None)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=FULL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                conn.execute("PRAGMA busy_timeout=5000;")
            conn.row_factory = sqlite3.Row
            self._conn = conn
            return conn
        except JournalDurabilityError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise JournalDurabilityError(f"Unable to open durable journal store ({self.db_path}): {exc}") from exc

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except sqlite3.Error:
                    pass
                self._conn = None

    def _begin_immediate(self) -> sqlite3.Connection:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            return conn
        except (sqlite3.Error, OSError) as exc:
            raise JournalDurabilityError(f"Durable journal write lock failed: {exc}") from exc

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._begin_immediate()
            try:
                now_utc = self.clock.utc_now()
                now_wall = now_utc.timestamp()
                now_mono = self.clock.monotonic()
                now_iso = _iso(now_utc) or ""
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS authority_state (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        owner_id TEXT,
                        epoch INTEGER NOT NULL,
                        role TEXT NOT NULL,
                        state_machine_phase TEXT NOT NULL,
                        lease_acquired_mono REAL,
                        lease_ttl_sec REAL NOT NULL DEFAULT 0.0,
                        lease_expires_mono REAL,
                        last_wall_ts REAL NOT NULL,
                        last_mono_ts REAL NOT NULL,
                        clock_anomaly INTEGER NOT NULL DEFAULT 0,
                        clock_anomaly_reason TEXT,
                        updated_utc TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS authority_transitions (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_owner TEXT,
                        to_owner TEXT,
                        from_epoch INTEGER,
                        to_epoch INTEGER NOT NULL,
                        from_phase TEXT,
                        to_phase TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        created_utc TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS execution_intents (
                        intent_id TEXT PRIMARY KEY,
                        client_oid TEXT UNIQUE,
                        epoch INTEGER NOT NULL,
                        owner_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        instrument TEXT NOT NULL,
                        side TEXT,
                        qty_text TEXT,
                        price_text TEXT,
                        params_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        exchange_order_id TEXT,
                        error_code TEXT,
                        error_detail TEXT,
                        created_utc TEXT NOT NULL,
                        updated_utc TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS queued_commands (
                        queue_id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        epoch INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        instrument TEXT NOT NULL,
                        side TEXT,
                        qty_text TEXT,
                        price_text TEXT,
                        order_id TEXT,
                        client_oid TEXT,
                        params_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        reason TEXT,
                        created_utc TEXT NOT NULL,
                        updated_utc TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS applied_fills (
                        fill_key TEXT PRIMARY KEY,
                        order_id TEXT NOT NULL,
                        client_oid TEXT,
                        side TEXT NOT NULL,
                        order_qty_text TEXT NOT NULL,
                        cum_fill_qty_text TEXT NOT NULL,
                        delta_fill_qty_text TEXT NOT NULL,
                        price_text TEXT NOT NULL,
                        fee_text TEXT NOT NULL,
                        realized_pnl_text TEXT NOT NULL,
                        reserve_delta_text TEXT NOT NULL,
                        epoch INTEGER NOT NULL,
                        applied_utc TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS journal_meta (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        journal_position INTEGER NOT NULL DEFAULT 0,
                        replication_lag_seconds REAL,
                        last_exchange_reconcile_utc TEXT,
                        last_verified_restore_utc TEXT,
                        replica_stale INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT
                    );
                    """
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO authority_state (
                        id, owner_id, epoch, role, state_machine_phase,
                        lease_acquired_mono, lease_ttl_sec, lease_expires_mono,
                        last_wall_ts, last_mono_ts, clock_anomaly, clock_anomaly_reason, updated_utc
                    ) VALUES (1, NULL, 0, 'PASSIVE', 'PASSIVE', NULL, 0.0, NULL, ?, ?, 0, NULL, ?);
                    """,
                    (now_wall, now_mono, now_iso),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO journal_meta (
                        id, journal_position, replication_lag_seconds,
                        last_exchange_reconcile_utc, last_verified_restore_utc,
                        replica_stale, last_error
                    ) VALUES (1, 0, NULL, NULL, NULL, 0, NULL);
                    """
                )
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise

    def set_lease_service_available(self, available: bool) -> None:
        with self._lock:
            self._lease_service_available = bool(available)
            if not available:
                self._record_alert("LEASE_SERVICE_UNAVAILABLE", "Authority lease service unreachable")

    def _record_alert(self, code: str, message: str) -> None:
        self._alerts.append({
            "utc": _iso(self.clock.utc_now()),
            "code": code,
            "message": message,
        })
        self._alerts = self._alerts[-25:]

    def get_alerts(self) -> list[dict[str, Any]]:
        with self._lock:
            state = self.get_state()
            alerts = list(self._alerts)
            if state.get("clock_anomaly"):
                alerts.append({
                    "utc": state.get("updated_utc"),
                    "code": "CLOCK_ANOMALY",
                    "message": state.get("clock_anomaly_reason") or "Clock jump detected",
                })
            if state.get("replica_stale"):
                alerts.append({
                    "utc": state.get("updated_utc"),
                    "code": "REPLICA_STALE",
                    "message": f"Replica stale (lag={state.get('replication_lag_seconds')}s)",
                })
            return alerts

    def _bump_journal_pos(self, conn: sqlite3.Connection, delta: int = 1) -> int:
        conn.execute(
            "UPDATE journal_meta SET journal_position = journal_position + ? WHERE id = 1;",
            (int(delta),),
        )
        row = conn.execute("SELECT journal_position FROM journal_meta WHERE id = 1;").fetchone()
        return int(row["journal_position"])

    def _check_and_update_clock_tx(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT last_wall_ts, last_mono_ts, clock_anomaly, clock_anomaly_reason FROM authority_state WHERE id = 1;"
        ).fetchone()
        now_utc = self.clock.utc_now()
        now_wall = now_utc.timestamp()
        now_mono = self.clock.monotonic()

        if int(row["clock_anomaly"]) != 0:
            raise ClockAnomalyError(str(row["clock_anomaly_reason"] or "Persisted clock anomaly unresolved"))

        last_wall = float(row["last_wall_ts"])
        last_mono = float(row["last_mono_ts"])
        wall_delta = now_wall - last_wall
        mono_delta = now_mono - last_mono

        if mono_delta < -0.5 or wall_delta < -self.max_clock_jump_sec or abs(wall_delta - mono_delta) > self.max_clock_jump_sec:
            reason = (
                f"Clock jump/skew detected: wall_delta={wall_delta:.3f}s "
                f"mono_delta={mono_delta:.3f}s threshold={self.max_clock_jump_sec:.1f}s"
            )
            conn.execute(
                "UPDATE authority_state SET clock_anomaly = 1, clock_anomaly_reason = ?, updated_utc = ? WHERE id = 1;",
                (reason, _iso(now_utc)),
            )
            self._record_alert("CLOCK_JUMP", reason)
            conn.commit()
            raise ClockAnomalyError(reason)

        conn.execute(
            "UPDATE authority_state SET last_wall_ts = ?, last_mono_ts = ? WHERE id = 1;",
            (now_wall, now_mono),
        )

    def clear_clock_anomaly(self, actor: str, reason: str) -> None:
        with self._lock:
            conn = self._begin_immediate()
            try:
                now_utc = self.clock.utc_now()
                conn.execute(
                    """
                    UPDATE authority_state
                    SET clock_anomaly = 0, clock_anomaly_reason = NULL,
                        last_wall_ts = ?, last_mono_ts = ?, updated_utc = ?
                    WHERE id = 1;
                    """,
                    (now_utc.timestamp(), self.clock.monotonic(), _iso(now_utc)),
                )
                row = conn.execute("SELECT owner_id, epoch, state_machine_phase FROM authority_state WHERE id = 1;").fetchone()
                conn.execute(
                    """
                    INSERT INTO authority_transitions (
                        from_owner, to_owner, from_epoch, to_epoch, from_phase, to_phase, reason, actor, created_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        row["owner_id"], row["owner_id"], row["epoch"], row["epoch"],
                        row["state_machine_phase"], row["state_machine_phase"],
                        f"clear_clock_anomaly: {reason}", actor, _iso(now_utc),
                    ),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            try:
                conn = self._connect()
                st = conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone()
                meta = conn.execute("SELECT * FROM journal_meta WHERE id = 1;").fetchone()
                if st is None or meta is None:
                    raise JournalDurabilityError("AuthorityStore missing singleton metadata rows")
                unresolved_cnt = int(
                    conn.execute(
                        "SELECT COUNT(*) AS c FROM execution_intents WHERE status IN ('INTENT','SUBMITTING','UNKNOWN');"
                    ).fetchone()["c"]
                )
                d = dict(st)
                d["journal_position"] = int(meta["journal_position"])
                d["replication_lag_seconds"] = meta["replication_lag_seconds"]
                d["last_exchange_reconcile_utc"] = meta["last_exchange_reconcile_utc"]
                d["last_verified_restore_utc"] = meta["last_verified_restore_utc"]
                d["replica_stale"] = bool(meta["replica_stale"])
                d["last_error"] = meta["last_error"]
                d["unresolved_intent_count"] = unresolved_cnt
                d["lease_service_available"] = self._lease_service_available
                return d
            except JournalDurabilityError:
                raise
            except (sqlite3.Error, OSError) as exc:
                raise JournalDurabilityError(f"Failed reading authority state: {exc}") from exc

    def check_integrity(self) -> tuple[bool, str]:
        with self._lock:
            try:
                conn = self._connect()
                row = conn.execute("PRAGMA integrity_check;").fetchone()
                msg = str(row[0]) if row else "unknown"
                return msg.lower() == "ok", msg
            except (sqlite3.Error, OSError) as exc:
                return False, str(exc)

    def set_replica_stale(self, stale: bool, lag_seconds: float | None = None, reason: str | None = None) -> None:
        with self._lock:
            conn = self._begin_immediate()
            try:
                conn.execute(
                    """
                    UPDATE journal_meta
                    SET replica_stale = ?, replication_lag_seconds = ?, last_error = ?
                    WHERE id = 1;
                    """,
                    (1 if stale else 0, lag_seconds, reason),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def mark_exchange_reconciled(self) -> None:
        with self._lock:
            conn = self._begin_immediate()
            try:
                now_iso = _iso(self.clock.utc_now())
                conn.execute(
                    "UPDATE journal_meta SET last_exchange_reconcile_utc = ? WHERE id = 1;",
                    (now_iso,),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def acquire_or_promote(
        self,
        new_owner: str,
        *,
        lease_ttl_sec: float = 45.0,
        actor: str = "operator",
        reason: str = "authorized_promotion",
    ) -> dict[str, Any]:
        """Atomically fence any old epoch and grant the next monotonic epoch to `new_owner`."""
        if not new_owner:
            raise ValueError("new_owner must be non-empty")
        with self._lock:
            if not self._lease_service_available:
                raise GateBlockedError("Lease service unavailable; cannot acquire or promote")
            conn = self._begin_immediate()
            try:
                self._check_and_update_clock_tx(conn)
                cur = conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone()
                old_epoch = int(cur["epoch"])
                new_epoch = old_epoch + 1
                now_utc = self.clock.utc_now()
                now_iso = _iso(now_utc) or ""
                now_mono = self.clock.monotonic()
                lease_exp = now_mono + float(lease_ttl_sec)
                conn.execute(
                    """
                    UPDATE authority_state
                    SET owner_id = ?, epoch = ?, role = 'ACTIVE', state_machine_phase = 'ACTIVE',
                        lease_acquired_mono = ?, lease_ttl_sec = ?, lease_expires_mono = ?,
                        last_wall_ts = ?, last_mono_ts = ?, updated_utc = ?
                    WHERE id = 1;
                    """,
                    (
                        new_owner, new_epoch, now_mono, float(lease_ttl_sec), lease_exp,
                        now_utc.timestamp(), now_mono, now_iso,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO authority_transitions (
                        from_owner, to_owner, from_epoch, to_epoch, from_phase, to_phase, reason, actor, created_utc
                    ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?);
                    """,
                    (cur["owner_id"], new_owner, old_epoch, new_epoch, cur["state_machine_phase"], reason, actor, now_iso),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise
            return self.get_state()

    def fence(self, *, reason: str, actor: str = "failover", target_role: str = "FENCED") -> dict[str, Any]:
        """Increment epoch and revoke current owner authority."""
        if target_role not in ("FENCED", "PASSIVE", "SAFE_HALT", "MANUAL_REVIEW"):
            raise ValueError(f"Invalid target_role for fence: {target_role}")
        with self._lock:
            conn = self._begin_immediate()
            try:
                cur = conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone()
                old_epoch = int(cur["epoch"])
                new_epoch = old_epoch + 1
                now_utc = self.clock.utc_now()
                now_iso = _iso(now_utc) or ""
                now_mono = self.clock.monotonic()
                conn.execute(
                    """
                    UPDATE authority_state
                    SET owner_id = NULL, epoch = ?, role = ?, state_machine_phase = ?,
                        lease_expires_mono = NULL, last_wall_ts = ?, last_mono_ts = ?, updated_utc = ?
                    WHERE id = 1;
                    """,
                    (new_epoch, target_role, target_role, now_utc.timestamp(), now_mono, now_iso),
                )
                conn.execute(
                    """
                    INSERT INTO authority_transitions (
                        from_owner, to_owner, from_epoch, to_epoch, from_phase, to_phase, reason, actor, created_utc
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (cur["owner_id"], old_epoch, new_epoch, cur["state_machine_phase"], target_role, reason, actor, now_iso),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise
            return self.get_state()

    def transition_phase(self, phase: str, *, reason: str, actor: str = "failover", role: str | None = None) -> dict[str, Any]:
        with self._lock:
            conn = self._begin_immediate()
            try:
                cur = conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone()
                now_iso = _iso(self.clock.utc_now()) or ""
                new_role = role if role is not None else cur["role"]
                conn.execute(
                    "UPDATE authority_state SET state_machine_phase = ?, role = ?, updated_utc = ? WHERE id = 1;",
                    (phase, new_role, now_iso),
                )
                conn.execute(
                    """
                    INSERT INTO authority_transitions (
                        from_owner, to_owner, from_epoch, to_epoch, from_phase, to_phase, reason, actor, created_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        cur["owner_id"], cur["owner_id"], cur["epoch"], cur["epoch"],
                        cur["state_machine_phase"], phase, reason, actor, now_iso,
                    ),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise
            return self.get_state()

    def renew_lease(self, owner_id: str, epoch: int, lease_ttl_sec: float = 45.0) -> dict[str, Any]:
        with self._lock:
            if not self._lease_service_available:
                raise GateBlockedError("Lease service unavailable; cannot renew lease")
            conn = self._begin_immediate()
            try:
                self._check_and_update_clock_tx(conn)
                cur = conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone()
                if cur["role"] != "ACTIVE" or cur["owner_id"] != owner_id or int(cur["epoch"]) != int(epoch):
                    raise StaleEpochError(
                        f"Lease renewal rejected for owner={owner_id} epoch={epoch}; "
                        f"active=({cur['owner_id']}, {cur['epoch']}, {cur['role']})"
                    )
                now_mono = self.clock.monotonic()
                exp = cur["lease_expires_mono"]
                if exp is not None and now_mono > float(exp):
                    raise StaleEpochError(f"Lease already expired at mono={exp:.3f} (now={now_mono:.3f})")
                new_exp = now_mono + float(lease_ttl_sec)
                conn.execute(
                    "UPDATE authority_state SET lease_expires_mono = ?, lease_ttl_sec = ?, updated_utc = ? WHERE id = 1;",
                    (new_exp, float(lease_ttl_sec), _iso(self.clock.utc_now())),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise
            return self.get_state()

    def check_authority(self, owner_id: str, epoch: int) -> dict[str, Any]:
        """Validate active owner, exact epoch match, monotonic lease, clock health, and replica freshness."""
        with self._lock:
            if not self._lease_service_available:
                raise StaleEpochError("Authority lease service unavailable")
            conn = self._begin_immediate()
            try:
                meta = conn.execute("SELECT replica_stale FROM journal_meta WHERE id = 1;").fetchone()
                if meta is None or int(meta["replica_stale"]) != 0:
                    raise JournalDurabilityError("Replica/journal marked stale; mutations blocked")
                self._check_and_update_clock_tx(conn)
                cur = conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone()
                if cur["role"] == "PASSIVE":
                    raise PassiveAuthorityError("Authority role is PASSIVE; exchange mutations denied")
                if cur["role"] != "ACTIVE":
                    raise StaleEpochError(f"Authority role is {cur['role']} (not ACTIVE); mutation denied")
                if cur["owner_id"] != owner_id or int(cur["epoch"]) != int(epoch):
                    raise StaleEpochError(
                        f"Stale/competing authority: caller=({owner_id}, epoch={epoch}) "
                        f"current=({cur['owner_id']}, epoch={cur['epoch']})"
                    )
                exp = cur["lease_expires_mono"]
                now_mono = self.clock.monotonic()
                if exp is not None and now_mono > float(exp):
                    raise StaleEpochError(
                        f"Lease expired for owner={owner_id} epoch={epoch} (now={now_mono:.3f} > exp={exp:.3f})"
                    )
                conn.commit()
                return self.get_state()
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise

    def record_intent_pre_dispatch(self, cmd: GatewayCommand) -> str:
        """Atomically verify authority + barriers and persist SUBMITTING intent before exchange I/O."""
        with self._lock:
            if not self._lease_service_available:
                raise StaleEpochError("Authority lease service unavailable")
            conn = self._begin_immediate()
            try:
                meta = conn.execute("SELECT replica_stale FROM journal_meta WHERE id = 1;").fetchone()
                if meta is None or int(meta["replica_stale"]) != 0:
                    raise JournalDurabilityError("Replica/journal is stale; refusing unjournaled mutation")

                self._check_and_update_clock_tx(conn)
                cur = conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone()
                if cur["role"] == "PASSIVE":
                    raise PassiveAuthorityError("Cannot submit mutation while authority role is PASSIVE")
                if cur["role"] != "ACTIVE":
                    raise StaleEpochError(f"Cannot submit mutation in role={cur['role']}")
                if cur["owner_id"] != cmd.owner_id or int(cur["epoch"]) != int(cmd.epoch):
                    raise StaleEpochError(
                        f"Caller ({cmd.owner_id}, epoch={cmd.epoch}) rejected by active "
                        f"({cur['owner_id']}, epoch={cur['epoch']})"
                    )
                exp = cur["lease_expires_mono"]
                if exp is not None and self.clock.monotonic() > float(exp):
                    raise StaleEpochError(f"Lease expired for epoch={cmd.epoch}")

                if cmd.action != "EMERGENCY" and not cmd.allow_during_reconcile:
                    unresolved = conn.execute(
                        "SELECT intent_id, status FROM execution_intents WHERE status IN ('INTENT','SUBMITTING','UNKNOWN');"
                    ).fetchall()
                    if unresolved:
                        ids = [f"{r['intent_id']}:{r['status']}" for r in unresolved]
                        raise UnresolvedIntentError(
                            f"New mutation blocked until unresolved intents reconcile: {ids}"
                        )

                intent_id = f"int-{uuid.uuid4().hex[:12]}"
                c_oid = cmd.client_oid or f"{cmd.action.lower()}-{intent_id}"
                now_iso = _iso(self.clock.utc_now()) or ""
                params_payload = dict(cmd.params)
                if cmd.order_id is not None:
                    params_payload["order_id"] = str(cmd.order_id)

                conn.execute(
                    """
                    INSERT INTO execution_intents (
                        intent_id, client_oid, epoch, owner_id, action, instrument, side,
                        qty_text, price_text, params_json, status, exchange_order_id,
                        error_code, error_detail, created_utc, updated_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUBMITTING', ?, NULL, NULL, ?, ?);
                    """,
                    (
                        intent_id,
                        c_oid,
                        int(cmd.epoch),
                        cmd.owner_id,
                        cmd.action,
                        cmd.instrument,
                        cmd.side,
                        str(cmd.qty_cro) if cmd.qty_cro is not None else None,
                        f"{cmd.price}" if cmd.price is not None else None,
                        json.dumps(params_payload, sort_keys=True),
                        str(cmd.order_id) if cmd.order_id is not None else None,
                        now_iso,
                        now_iso,
                    ),
                )
                self._bump_journal_pos(conn)
                conn.commit()
                return intent_id
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise

    def update_intent_status(
        self,
        intent_id: str,
        *,
        status: str,
        exchange_order_id: str | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        if status not in ("INTENT", "SUBMITTING", "ACKED", "REJECTED", "UNKNOWN", "RECONCILED", "ABORTED"):
            raise ValueError(f"Invalid intent status: {status!r}")
        with self._lock:
            conn = self._begin_immediate()
            try:
                now_iso = _iso(self.clock.utc_now()) or ""
                conn.execute(
                    """
                    UPDATE execution_intents
                    SET status = ?,
                        exchange_order_id = COALESCE(?, exchange_order_id),
                        error_code = COALESCE(?, error_code),
                        error_detail = COALESCE(?, error_detail),
                        updated_utc = ?
                    WHERE intent_id = ?;
                    """,
                    (status, exchange_order_id, error_code, error_detail, now_iso, intent_id),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise

    def seed_intent_for_test(
        self,
        *,
        intent_id: str,
        client_oid: str,
        epoch: int,
        owner_id: str,
        action: str,
        status: str,
        side: str = "BUY",
        qty_cro: int = 100,
        price: Decimal = Decimal("0.04100"),
        exchange_order_id: str | None = None,
    ) -> None:
        """Persist a synthetic intent directly (used for crash/restart recovery drills like HA-05)."""
        with self._lock:
            conn = self._begin_immediate()
            try:
                now_iso = _iso(self.clock.utc_now()) or ""
                conn.execute(
                    """
                    INSERT OR REPLACE INTO execution_intents (
                        intent_id, client_oid, epoch, owner_id, action, instrument, side,
                        qty_text, price_text, params_json, status, exchange_order_id,
                        error_code, error_detail, created_utc, updated_utc
                    ) VALUES (?, ?, ?, ?, ?, 'CRO_USDT', ?, ?, ?, '{}', ?, ?, NULL, NULL, ?, ?);
                    """,
                    (
                        intent_id, client_oid, int(epoch), owner_id, action, side,
                        str(qty_cro), f"{price}", status, exchange_order_id, now_iso, now_iso,
                    ),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_unresolved_intents(self) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM execution_intents WHERE status IN ('INTENT','SUBMITTING','UNKNOWN') ORDER BY created_utc ASC;"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_intents(self) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute("SELECT * FROM execution_intents ORDER BY created_utc ASC;").fetchall()
            return [dict(r) for r in rows]

    def enqueue_durable_command(self, cmd: GatewayCommand) -> str:
        with self._lock:
            conn = self._begin_immediate()
            try:
                queue_id = f"q-{uuid.uuid4().hex[:12]}"
                now_iso = _iso(self.clock.utc_now()) or ""
                conn.execute(
                    """
                    INSERT INTO queued_commands (
                        queue_id, owner_id, epoch, action, instrument, side, qty_text, price_text,
                        order_id, client_oid, params_json, status, reason, created_utc, updated_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', NULL, ?, ?);
                    """,
                    (
                        queue_id, cmd.owner_id, int(cmd.epoch), cmd.action, cmd.instrument, cmd.side,
                        str(cmd.qty_cro) if cmd.qty_cro is not None else None,
                        f"{cmd.price}" if cmd.price is not None else None,
                        str(cmd.order_id) if cmd.order_id is not None else None,
                        cmd.client_oid, json.dumps(cmd.params, sort_keys=True), now_iso, now_iso,
                    ),
                )
                self._bump_journal_pos(conn)
                conn.commit()
                return queue_id
            except Exception:
                conn.rollback()
                raise

    def list_queued_commands(self, status: str = "QUEUED") -> list[dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM queued_commands WHERE status = ? ORDER BY created_utc ASC;",
                (status,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_queued_command(self, queue_id: str, status: str, reason: str | None = None) -> None:
        with self._lock:
            conn = self._begin_immediate()
            try:
                conn.execute(
                    "UPDATE queued_commands SET status = ?, reason = ?, updated_utc = ? WHERE queue_id = ?;",
                    (status, reason, _iso(self.clock.utc_now()), queue_id),
                )
                self._bump_journal_pos(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def apply_fill_idempotent(
        self,
        *,
        fill_key: str,
        order_id: str,
        client_oid: str,
        side: str,
        order_qty: Decimal | int | str,
        cum_fill_qty: Decimal | int | str,
        delta_fill_qty: Decimal | int | str,
        price: Decimal | str,
        fee_usdt: Decimal | str = DECIMAL_ZERO,
        cost_basis_price: Decimal | str | None = None,
        reserve_share: Decimal = DEFAULT_PROFIT_RESERVE_SHARE,
        epoch: int = 0,
    ) -> tuple[bool, dict[str, str]]:
        """Apply fill deduplicated by `fill_key` with strict Decimal arithmetic."""
        ord_qty_d = _d(order_qty)
        cum_qty_d = _d(cum_fill_qty)
        delta_qty_d = _d(delta_fill_qty)
        price_d = _d(price)
        fee_d = _d(fee_usdt)
        realized = DECIMAL_ZERO
        reserve_delta = DECIMAL_ZERO
        if side.upper() == "SELL" and cost_basis_price is not None and delta_qty_d > DECIMAL_ZERO:
            cost_d = _d(cost_basis_price)
            realized = (delta_qty_d * price_d) - (delta_qty_d * cost_d) - fee_d
            if realized > DECIMAL_ZERO:
                reserve_delta = (realized * reserve_share).quantize(USDT_QUANT, rounding=ROUND_DOWN)

        with self._lock:
            conn = self._begin_immediate()
            try:
                now_iso = _iso(self.clock.utc_now()) or ""
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO applied_fills (
                        fill_key, order_id, client_oid, side,
                        order_qty_text, cum_fill_qty_text, delta_fill_qty_text,
                        price_text, fee_text, realized_pnl_text, reserve_delta_text,
                        epoch, applied_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        fill_key, str(order_id), client_oid, side.upper(),
                        str(ord_qty_d), str(cum_qty_d), str(delta_qty_d),
                        str(price_d), _q6(fee_d), _q6(realized), _q6(reserve_delta),
                        int(epoch), now_iso,
                    ),
                )
                applied = cur.rowcount == 1
                if applied:
                    self._bump_journal_pos(conn)

                rows = conn.execute(
                    "SELECT delta_fill_qty_text, realized_pnl_text, reserve_delta_text FROM applied_fills WHERE order_id = ?;",
                    (str(order_id),),
                ).fetchall()
                all_rows = conn.execute(
                    "SELECT realized_pnl_text, reserve_delta_text FROM applied_fills;"
                ).fetchall()
                conn.commit()

                order_filled = sum((_d(r["delta_fill_qty_text"]) for r in rows), DECIMAL_ZERO)
                remaining_qty = max(DECIMAL_ZERO, ord_qty_d - order_filled)
                total_realized = sum((_d(r["realized_pnl_text"]) for r in all_rows), DECIMAL_ZERO)
                total_reserve = sum((_d(r["reserve_delta_text"]) for r in all_rows), DECIMAL_ZERO)

                return applied, {
                    "fill_key": fill_key,
                    "order_id": str(order_id),
                    "order_filled_qty": str(order_filled),
                    "remaining_qty": str(remaining_qty),
                    "total_realized_pnl_usdt": _q6(total_realized),
                    "profit_reserve_usdt": _q6(total_reserve),
                }
            except Exception:
                conn.rollback()
                raise

    def create_consistent_backup(self, dest_path: str | Path) -> dict[str, Any]:
        """Create a consistent SQLite snapshot using sqlite3.Connection.backup() and verify it."""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            src_conn = self._connect()
            dst_conn = sqlite3.connect(str(dest), timeout=5.0)
            try:
                src_conn.backup(dst_conn)
                # Restored standby/backup snapshots MUST start in PASSIVE mode cleanly!
                dst_conn.execute(
                    "UPDATE authority_state SET role = 'PASSIVE', state_machine_phase = 'PASSIVE', owner_id = NULL, lease_expires_mono = NULL WHERE id = 1;"
                )
                now_iso = _iso(self.clock.utc_now()) or ""
                dst_conn.execute(
                    "UPDATE journal_meta SET last_verified_restore_utc = ? WHERE id = 1;",
                    (now_iso,),
                )
                dst_conn.commit()
            finally:
                dst_conn.close()

            sha256 = hashlib.sha256(dest.read_bytes()).hexdigest()
            now_iso = _iso(self.clock.utc_now()) or ""
            conn = self._begin_immediate()
            try:
                conn.execute("UPDATE journal_meta SET last_verified_restore_utc = ? WHERE id = 1;", (now_iso,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        verification = verify_backup_passive(dest)
        verification["sha256"] = sha256
        verification["backup_path"] = str(dest)
        return verification


def verify_backup_passive(backup_path: str | Path) -> dict[str, Any]:
    """Verify SQLite backup integrity and guarantee it opens strictly PASSIVE (OPS-03)."""
    p = Path(backup_path)
    if not p.is_file():
        raise JournalDurabilityError(f"Backup file does not exist: {p}")
    conn = sqlite3.connect(str(p), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        integ = str(conn.execute("PRAGMA integrity_check;").fetchone()[0])
        if integ.lower() != "ok":
            raise JournalDurabilityError(f"Backup integrity_check failed: {integ}")
        # Enforce passive-only start on any restored copy
        conn.execute(
            "UPDATE authority_state SET role = 'PASSIVE', state_machine_phase = 'PASSIVE', owner_id = NULL, lease_expires_mono = NULL WHERE id = 1;"
        )
        conn.commit()
        st = dict(conn.execute("SELECT * FROM authority_state WHERE id = 1;").fetchone())
        fills = int(conn.execute("SELECT COUNT(*) FROM applied_fills;").fetchone()[0])
        intents = int(conn.execute("SELECT COUNT(*) FROM execution_intents;").fetchone()[0])
        return {
            "integrity": integ,
            "role": st["role"],
            "epoch": int(st["epoch"]),
            "owner_id": st["owner_id"],
            "applied_fills_count": fills,
            "execution_intents_count": intents,
            "auto_live_disabled": st["role"] == "PASSIVE" and st["owner_id"] is None,
        }
    finally:
        conn.close()


class PassiveStandbyClient:
    """Read-only exchange client for standby/watchdog hosts; technically denies all mutations (HA-08)."""

    def __init__(self, read_observer: Any) -> None:
        self._observer = read_observer
        self.denied_mutation_attempts = 0
        self.denial_log: list[dict[str, str]] = []

    def _deny(self, op: str) -> None:
        self.denied_mutation_attempts += 1
        self.denial_log.append({"utc": _iso(datetime.now(timezone.utc)) or "", "op": op})
        raise PassiveAuthorityError(
            f"Passive host/read-only client denied exchange mutation '{op}' (HA-08)"
        )

    def get_book(self, depth: int = 10) -> Any:
        return self._observer.get_book(depth=depth)

    def get_open_orders(self) -> Any:
        return self._observer.get_open_orders()

    def get_order_detail(self, order_id: str) -> Any:
        return self._observer.get_order_detail(order_id)

    def get_balances(self) -> Any:
        return self._observer.get_balances()

    # All exchange mutation methods unconditionally raise PassiveAuthorityError
    def create_limit_order(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self._deny("CREATE_LIMIT_ORDER")

    def cancel_order(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self._deny("CANCEL_ORDER")

    def amend_order(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self._deny("AMEND_ORDER")

    def bulk_order(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self._deny("BULK_ORDER")

    def rearm(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self._deny("REARM")

    def emergency_cancel_all(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        self._deny("EMERGENCY_CANCEL_ALL")


class ExecutionGateway:
    """Exclusive admission, journaling, queuing, and reconciliation boundary for exchange mutations."""

    def __init__(
        self,
        store: AuthorityStore,
        exchange_client: Any,
        *,
        risk_validator: Callable[[GatewayCommand], tuple[bool, str]] | None = None,
    ) -> None:
        self.store = store
        self._exchange = exchange_client
        self._risk_validator = risk_validator
        self._dispatch_lock = threading.RLock()
        self._pending_queue: list[tuple[str, GatewayCommand]] = []

    def submit_create_limit(
        self,
        *,
        owner_id: str,
        epoch: int,
        side: str,
        qty_cro: int,
        price: Decimal,
        client_oid: str,
        instrument: str = "CRO_USDT",
    ) -> dict[str, Any]:
        return self._execute_mutation(
            GatewayCommand(
                owner_id=owner_id,
                epoch=epoch,
                action="CREATE",
                instrument=instrument,
                side=side,
                qty_cro=int(qty_cro),
                price=Decimal(str(price)),
                client_oid=client_oid,
            )
        )

    def submit_cancel(self, *, owner_id: str, epoch: int, order_id: str, client_oid: str | None = None) -> dict[str, Any]:
        return self._execute_mutation(
            GatewayCommand(
                owner_id=owner_id,
                epoch=epoch,
                action="CANCEL",
                order_id=str(order_id),
                client_oid=client_oid,
            )
        )

    def submit_amend(
        self,
        *,
        owner_id: str,
        epoch: int,
        order_id: str,
        new_price: Decimal,
        new_qty_cro: int,
        client_oid: str | None = None,
    ) -> dict[str, Any]:
        return self._execute_mutation(
            GatewayCommand(
                owner_id=owner_id,
                epoch=epoch,
                action="AMEND",
                order_id=str(order_id),
                qty_cro=int(new_qty_cro),
                price=Decimal(str(new_price)),
                client_oid=client_oid,
            )
        )

    def submit_bulk(self, *, owner_id: str, epoch: int, orders: list[dict[str, Any]], client_oid: str | None = None) -> dict[str, Any]:
        return self._execute_mutation(
            GatewayCommand(
                owner_id=owner_id,
                epoch=epoch,
                action="BULK",
                client_oid=client_oid,
                params={"orders": list(orders)},
            )
        )

    def submit_rearm(self, *, owner_id: str, epoch: int, tranche_idx: int, side: str, qty_cro: int, price: Decimal, client_oid: str) -> dict[str, Any]:
        return self._execute_mutation(
            GatewayCommand(
                owner_id=owner_id,
                epoch=epoch,
                action="REARM",
                side=side,
                qty_cro=int(qty_cro),
                price=Decimal(str(price)),
                client_oid=client_oid,
                params={"tranche_idx": int(tranche_idx)},
            )
        )

    def submit_emergency(self, *, owner_id: str, epoch: int, operation: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._execute_mutation(
            GatewayCommand(
                owner_id=owner_id,
                epoch=epoch,
                action="EMERGENCY",
                params={"operation": operation, **(params or {})},
                allow_during_reconcile=True,
            )
        )

    def enqueue_command(self, cmd: GatewayCommand) -> str:
        """Persist and queue a command tagged with `(owner_id, epoch)` for later serialized dispatch."""
        with self._dispatch_lock:
            qid = self.store.enqueue_durable_command(cmd)
            self._pending_queue.append((qid, cmd))
            return qid

    def drain_queue(self) -> list[dict[str, Any]]:
        """Revalidate all queued commands under `_dispatch_lock` before dispatch; abort expired epochs."""
        results: list[dict[str, Any]] = []
        with self._dispatch_lock:
            # Also inspect durable DB queue for any queued commands surviving a restart (Sec 5.2)
            pending = list(self._pending_queue)
            self._pending_queue.clear()
            seen_ids = {qid for qid, _ in pending}
            for row in self.store.list_queued_commands(status="QUEUED"):
                if row["queue_id"] in seen_ids:
                    continue
                params = json.loads(row["params_json"])
                pending.append((
                    row["queue_id"],
                    GatewayCommand(
                        owner_id=row["owner_id"],
                        epoch=int(row["epoch"]),
                        action=row["action"],
                        instrument=row["instrument"],
                        side=row["side"],
                        qty_cro=int(row["qty_text"]) if row["qty_text"] is not None else None,
                        price=Decimal(row["price_text"]) if row["price_text"] is not None else None,
                        order_id=row["order_id"],
                        client_oid=row["client_oid"],
                        params=params,
                    ),
                ))

            for qid, cmd in pending:
                try:
                    self.store.check_authority(cmd.owner_id, cmd.epoch)
                except HAError as exc:
                    self.store.update_queued_command(qid, "ABORTED", reason=str(exc))
                    results.append({
                        "queue_id": qid,
                        "status": "ABORTED",
                        "reason": str(exc),
                        "error_type": type(exc).__name__,
                    })
                    continue

                try:
                    ack = self._execute_mutation(cmd)
                    self.store.update_queued_command(qid, "DISPATCHED", reason="ok")
                    results.append({"queue_id": qid, "status": "DISPATCHED", "ack": ack})
                except HAError as exc:
                    self.store.update_queued_command(qid, "ABORTED", reason=str(exc))
                    results.append({
                        "queue_id": qid,
                        "status": "ABORTED",
                        "reason": str(exc),
                        "error_type": type(exc).__name__,
                    })
        return results

    def _dispatch_to_exchange(self, cmd: GatewayCommand) -> dict[str, Any]:
        if cmd.action in ("CREATE", "REARM"):
            if cmd.side is None or cmd.qty_cro is None or cmd.price is None or cmd.client_oid is None:
                raise ValueError("CREATE/REARM requires side, qty_cro, price, client_oid")
            res = self._exchange.create_limit_order(
                side=cmd.side,
                qty_cro=cmd.qty_cro,
                price=cmd.price,
                client_oid=cmd.client_oid,
            )
            return dict(res) if isinstance(res, dict) else {"order_id": str(res)}

        if cmd.action == "CANCEL":
            if not cmd.order_id:
                raise ValueError("CANCEL requires order_id")
            res = self._exchange.cancel_order(cmd.order_id)
            return dict(res) if isinstance(res, dict) else {"order_id": cmd.order_id, "cancelled": True}

        if cmd.action == "AMEND":
            if not hasattr(self._exchange, "amend_order"):
                raise ExchangeRejectError("Exchange client does not implement amend_order")
            res = self._exchange.amend_order(
                order_id=cmd.order_id,
                qty_cro=cmd.qty_cro,
                price=cmd.price,
            )
            return dict(res) if isinstance(res, dict) else {"order_id": cmd.order_id}

        if cmd.action == "BULK":
            if not hasattr(self._exchange, "bulk_order"):
                raise ExchangeRejectError("Exchange client does not implement bulk_order")
            res = self._exchange.bulk_order(cmd.params.get("orders", []))
            return dict(res) if isinstance(res, dict) else {"results": res}

        if cmd.action == "EMERGENCY":
            if hasattr(self._exchange, "emergency_action"):
                res = self._exchange.emergency_action(cmd.params.get("operation"), cmd.params)
                return dict(res) if isinstance(res, dict) else {"status": "ok"}
            if cmd.order_id:
                self._exchange.cancel_order(cmd.order_id)
                return {"order_id": cmd.order_id, "status": "emergency_cancelled"}
            return {"status": "emergency_noop"}

        raise ValueError(f"Unsupported action: {cmd.action}")

    def _execute_mutation(self, cmd: GatewayCommand) -> dict[str, Any]:
        if isinstance(self._exchange, PassiveStandbyClient):
            raise PassiveAuthorityError("ExecutionGateway cannot wrap a PassiveStandbyClient")

        with self._dispatch_lock:
            if self._risk_validator is not None:
                ok, risk_msg = self._risk_validator(cmd)
                if not ok:
                    raise GateBlockedError(f"Risk policy rejected {cmd.action}: {risk_msg}")

            intent_id = self.store.record_intent_pre_dispatch(cmd)
            try:
                ack = self._dispatch_to_exchange(cmd)
            except ExchangeRejectError as exc:
                self.store.update_intent_status(
                    intent_id,
                    status="REJECTED",
                    error_code="EXCHANGE_REJECT",
                    error_detail=str(exc),
                )
                raise
            except (TimeoutError, ConnectionError, OSError, RuntimeError, Exception) as exc:
                # Transport failure / dropped response: mark UNKNOWN, NEVER blindly retry (HA-03).
                self.store.update_intent_status(
                    intent_id,
                    status="UNKNOWN",
                    error_code=type(exc).__name__,
                    error_detail=str(exc),
                )
                raise UnresolvedIntentError(
                    f"Uncertain outcome for intent {intent_id} ({cmd.action} {cmd.client_oid}): {exc}"
                ) from exc

            ex_oid = str(ack.get("order_id") or cmd.order_id or "") or None
            self.store.update_intent_status(
                intent_id,
                status="ACKED",
                exchange_order_id=ex_oid,
            )
            return {**ack, "intent_id": intent_id, "epoch": cmd.epoch}

    def reconcile_unresolved_intents(
        self,
        read_client: Any,
        *,
        cost_basis_lookup: Callable[[dict[str, Any]], Decimal | None] | None = None,
    ) -> dict[str, Any]:
        """Resolve INTENT / SUBMITTING / UNKNOWN intents using two-pass authoritative exchange observation."""
        unresolved = self.store.get_unresolved_intents()
        if not unresolved:
            self.store.mark_exchange_reconciled()
            return {"resolved": [], "still_unresolved": []}

        # Two consistent exchange read-backs to avoid acting on a single stale snapshot (Sec 5.3)
        open_1 = list(read_client.get_open_orders())
        bal_1 = read_client.get_balances()
        open_2 = list(read_client.get_open_orders())
        bal_2 = read_client.get_balances()
        ids_1 = sorted(str(o.get("order_id")) for o in open_1)
        ids_2 = sorted(str(o.get("order_id")) for o in open_2)
        if ids_1 != ids_2 or len(bal_1) != len(bal_2):
            raise GateBlockedError("Inconsistent two-pass exchange read-back during reconciliation")

        open_by_coid = {str(o.get("client_oid", "")): o for o in open_2 if o.get("client_oid")}
        open_by_oid = {str(o.get("order_id", "")): o for o in open_2 if o.get("order_id")}

        resolved: list[dict[str, Any]] = []
        still_unresolved: list[dict[str, Any]] = []

        for intent in unresolved:
            iid = intent["intent_id"]
            coid = str(intent.get("client_oid") or "")
            ex_oid = str(intent.get("exchange_order_id") or "")

            matched = open_by_oid.get(ex_oid) or open_by_coid.get(coid)
            detail: dict[str, Any] | None = None
            if matched is None and ex_oid:
                try:
                    detail = read_client.get_order_detail(ex_oid)
                except Exception:
                    detail = None
            elif matched is None and coid and hasattr(read_client, "get_order_by_client_oid"):
                try:
                    detail = read_client.get_order_by_client_oid(coid)
                except Exception:
                    detail = None

            obs = matched or detail
            if obs is None:
                # Could not verify whether order reached exchange
                still_unresolved.append({"intent_id": iid, "reason": "not_found_and_not_proven_absent"})
                continue

            obs_oid = str(obs.get("order_id") or ex_oid or "")
            ord_qty = Decimal(str(obs.get("quantity") or intent.get("qty_text") or "0"))
            cum_qty = Decimal(str(obs.get("cumulative_quantity") or "0"))
            fill_price = Decimal(str(obs.get("avg_price") or obs.get("limit_price") or obs.get("price") or intent.get("price_text") or "0"))
            fee_usdt = abs(Decimal(str(obs.get("cumulative_fee") or "0")))

            if cum_qty > DECIMAL_ZERO:
                basis = cost_basis_lookup(intent) if cost_basis_lookup else None
                fill_key = f"{obs_oid}:{cum_qty}"
                self.store.apply_fill_idempotent(
                    fill_key=fill_key,
                    order_id=obs_oid,
                    client_oid=coid,
                    side=str(obs.get("side") or intent.get("side") or "BUY"),
                    order_qty=ord_qty,
                    cum_fill_qty=cum_qty,
                    delta_fill_qty=cum_qty,
                    price=fill_price,
                    fee_usdt=fee_usdt,
                    cost_basis_price=basis,
                    epoch=int(intent["epoch"]),
                )

            self.store.update_intent_status(
                iid,
                status="RECONCILED",
                exchange_order_id=obs_oid or None,
                error_detail=f"Reconciled status={obs.get('status')} cum_qty={cum_qty}",
            )
            resolved.append({"intent_id": iid, "exchange_order_id": obs_oid, "cum_qty": str(cum_qty)})

        if not still_unresolved:
            self.store.mark_exchange_reconciled()
        return {"resolved": resolved, "still_unresolved": still_unresolved}


class GatewayExchangeClient:
    """Adapter exposing CryptoComClient interface while forcing every mutation through ExecutionGateway."""

    def __init__(
        self,
        *,
        read_client: Any,
        gateway: ExecutionGateway,
        owner_id: str,
        epoch: int,
    ) -> None:
        self._read = read_client
        self._gateway = gateway
        self.owner_id = owner_id
        self.epoch = int(epoch)

    def get_book(self, depth: int = 10) -> Any:
        return self._read.get_book(depth=depth)

    def get_open_orders(self) -> Any:
        return self._read.get_open_orders()

    def get_order_detail(self, order_id: str) -> Any:
        return self._read.get_order_detail(order_id)

    def get_balances(self) -> Any:
        return self._read.get_balances()

    def create_limit_order(self, *, side: str, qty_cro: int, price: Decimal, client_oid: str) -> dict[str, Any]:
        return self._gateway.submit_create_limit(
            owner_id=self.owner_id,
            epoch=self.epoch,
            side=side,
            qty_cro=qty_cro,
            price=price,
            client_oid=client_oid,
        )

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return self._gateway.submit_cancel(owner_id=self.owner_id, epoch=self.epoch, order_id=order_id)


class FailoverStateMachine:
    """Enforces durable failover transitions and non-bypassable technical safety gates."""

    def __init__(
        self,
        store: AuthorityStore,
        gateway: ExecutionGateway,
        *,
        auto_promote_enabled: bool = False,
        max_market_data_age_sec: float = 15.0,
    ) -> None:
        self.store = store
        self.gateway = gateway
        self.auto_promote_enabled = bool(auto_promote_enabled)
        self.max_market_data_age_sec = float(max_market_data_age_sec)

    def recover_host_passive(self, host_id: str, *, actor: str = "boot_recovery") -> dict[str, Any]:
        """Force rebooted/returning host into PASSIVE role with no active live trading authority (OPS-01, HA-01)."""
        return self.store.transition_phase(
            "PASSIVE",
            role="PASSIVE",
            reason=f"Host {host_id} recovered in mandatory PASSIVE mode pending reconciliation & lease check",
            actor=actor,
        )

    def request_promotion(
        self,
        candidate_owner: str,
        *,
        manual_approval_actor: str | None,
        read_client: Any,
        risk_snapshot: dict[str, Any],
        market_data_age_sec: float,
        lease_ttl_sec: float = 45.0,
        primary_heartbeat_age_sec: float | None = None,
        primary_failure_confirmed: bool = True,
    ) -> dict[str, Any]:
        """Execute PASSIVE -> SUSPECT -> VERIFY -> FENCE -> DRAIN_AND_RECONCILE -> RISK_CHECK -> PROMOTE -> ACTIVE."""
        # Step 1: SUSPECT & VERIFY
        self.store.transition_phase(
            "SUSPECT",
            reason=f"Primary suspect (heartbeat_age={primary_heartbeat_age_sec}s)",
            actor=manual_approval_actor or "system",
        )
        if not primary_failure_confirmed:
            self.store.transition_phase("SAFE_HALT", role="SAFE_HALT", reason="Primary failure not confirmed")
            raise GateBlockedError("Primary failure not confirmed")

        self.store.transition_phase("VERIFY", reason="Independent outage verification passed")

        # Gate check: Stage 1 retains manual approval unless automatic promotion is explicitly enabled
        if not self.auto_promote_enabled and not (manual_approval_actor and manual_approval_actor.strip()):
            self.store.transition_phase(
                "MANUAL_REVIEW",
                role="MANUAL_REVIEW",
                reason="Stage 1 requires authenticated manual promotion approval",
            )
            raise GateBlockedError("Manual promotion approval required in Stage 1")

        # Gate check: Clock / Lease / Durability checks BEFORE promotion (HA-06, HA-07)
        try:
            st_now = self.store.get_state()
            if not st_now.get("lease_service_available", True):
                raise GateBlockedError("Authority lease service unavailable; self-promotion blocked (HA-06)")
            if st_now.get("replica_stale"):
                raise GateBlockedError("Replica is stale; promotion blocked (HA-07)")
            ok_int, int_msg = self.store.check_integrity()
            if not ok_int:
                raise GateBlockedError(f"Journal integrity check failed: {int_msg}")
            with self.store._lock:
                conn = self.store._begin_immediate()
                try:
                    self.store._check_and_update_clock_tx(conn)
                    conn.commit()
                finally:
                    pass
        except ClockAnomalyError as exc:
            self.store.transition_phase("SAFE_HALT", role="SAFE_HALT", reason=f"Clock anomaly: {exc}")
            raise GateBlockedError(f"Clock jump/anomaly blocks self-promotion (HA-06): {exc}") from exc
        except JournalDurabilityError as exc:
            self.store.transition_phase("SAFE_HALT", role="SAFE_HALT", reason=f"Durability check failed: {exc}")
            raise GateBlockedError(f"Journal durability error blocks promotion (HA-07): {exc}") from exc

        # Step 2: FENCE previous leader & increment epoch so stale queued/in-flight commands fail
        self.store.fence(reason=f"Fencing prior leader before promoting {candidate_owner}", actor=manual_approval_actor or "system")

        # Step 3: DRAIN_AND_RECONCILE (manual approval CANNOT bypass unresolved intents!)
        self.store.transition_phase("DRAIN_AND_RECONCILE", reason="Draining stale queue & reconciling exchange")
        self.gateway.drain_queue()
        try:
            rec = self.gateway.reconcile_unresolved_intents(read_client)
        except Exception as exc:
            self.store.transition_phase("SAFE_HALT", role="SAFE_HALT", reason=f"Exchange reconcile failed: {exc}")
            raise GateBlockedError(f"Exchange reconciliation error blocks promotion: {exc}") from exc

        if rec["still_unresolved"]:
            self.store.transition_phase(
                "SAFE_HALT",
                role="SAFE_HALT",
                reason=f"Unresolved intents block promotion: {rec['still_unresolved']}",
            )
            raise GateBlockedError(
                f"Manual approval cannot bypass unresolved intents (HA-03): {rec['still_unresolved']}"
            )

        # Step 4: RISK_CHECK
        self.store.transition_phase("RISK_CHECK", reason="Validating market freshness & watchdog policy")
        if market_data_age_sec > self.max_market_data_age_sec:
            self.store.transition_phase("SAFE_HALT", role="SAFE_HALT", reason=f"Stale market data ({market_data_age_sec}s)")
            raise GateBlockedError(f"Market data stale: {market_data_age_sec}s > {self.max_market_data_age_sec}s")
        if not risk_snapshot.get("healthy", False) or risk_snapshot.get("kill_switch_tripped", False):
            self.store.transition_phase("SAFE_HALT", role="SAFE_HALT", reason=f"Risk check failed: {risk_snapshot}")
            raise GateBlockedError(f"Risk watchdog rejected promotion: {risk_snapshot}")

        # Step 5: PROMOTE -> ACTIVE
        self.store.transition_phase("PROMOTE", reason=f"Granting exclusive authority epoch to {candidate_owner}")
        return self.store.acquire_or_promote(
            candidate_owner,
            lease_ttl_sec=lease_ttl_sec,
            actor=manual_approval_actor or "system",
            reason="controlled_failover_promotion",
        )


def build_ha_health_payload(
    *,
    host_id: str,
    build_revision: str,
    store: AuthorityStore | None = None,
    role_override: str | None = None,
    process_alive: bool = True,
    heartbeat_age_sec: float | None = 0.0,
    exchange_read_access: bool = True,
    market_data_age_sec: float | None = 0.0,
    risk_state: str = "HEALTHY",
    oci_status: dict[str, Any] | None = None,
    status_write_ok: bool = True,
    extra_alerts: list[dict[str, Any]] | None = None,
    clock: ClockProtocol | None = None,
) -> dict[str, Any]:
    """Build non-secret Section 9 health payload separating all required HA health dimensions."""
    clk = clock or SystemClock()
    now_iso = _iso(clk.utc_now())

    st: dict[str, Any] = {}
    journal_durable = False
    alerts: list[dict[str, Any]] = list(extra_alerts or [])

    if store is not None:
        try:
            st = store.get_state()
            ok_int, int_msg = store.check_integrity()
            journal_durable = ok_int and not st.get("replica_stale", False) and not st.get("clock_anomaly", False)
            if not ok_int:
                alerts.append({"utc": now_iso, "code": "JOURNAL_INTEGRITY", "message": int_msg})
            alerts.extend(store.get_alerts())
        except Exception as exc:
            journal_durable = False
            alerts.append({"utc": now_iso, "code": "JOURNAL_UNREADABLE", "message": str(exc)})
    else:
        journal_durable = status_write_ok

    if not status_write_ok:
        alerts.append({"utc": now_iso, "code": "STATUS_WRITE_FAILED", "message": "Status or alert sink write failed"})

    oci = oci_status or {}
    role = role_override or st.get("role") or "PASSIVE"
    unresolved = int(st.get("unresolved_intent_count", 0))
    lease_status = "UNAVAILABLE"
    if st.get("lease_service_available", True):
        if role == "ACTIVE" and st.get("lease_expires_mono") is not None:
            lease_status = "VALID" if clk.monotonic() <= float(st["lease_expires_mono"]) else "EXPIRED"
        else:
            lease_status = role

    market_data_fresh = market_data_age_sec is not None and market_data_age_sec <= 15.0
    application_ready = bool(
        process_alive
        and exchange_read_access
        and market_data_fresh
        and journal_durable
        and status_write_ok
        and risk_state in ("HEALTHY", "OK")
        and unresolved == 0
    )

    return {
        "checked_utc": now_iso,
        "host_id": host_id,
        "build_revision": build_revision,
        "role": role,
        "authority_epoch": int(st.get("epoch", 0)),
        "lease_status": lease_status,
        "last_exchange_reconcile_utc": st.get("last_exchange_reconcile_utc"),
        "journal_position": int(st.get("journal_position", 0)),
        "replication_lag_seconds": st.get("replication_lag_seconds"),
        "unresolved_intent_count": unresolved,
        "risk_state": risk_state,
        "provisioning_state": oci.get("controller_mode") or oci.get("mode") or "NOT_CONFIGURED",
        "active_job_id": oci.get("active_job_id"),
        "next_attempt_not_before_utc": oci.get("next_attempt_not_before_utc"),
        "last_verified_restore_utc": st.get("last_verified_restore_utc"),
        "alerts": alerts,
        "dimensions": {
            "process_alive": bool(process_alive),
            "heartbeat_age_sec": heartbeat_age_sec,
            "exchange_read_access": bool(exchange_read_access),
            "market_data_fresh": bool(market_data_fresh),
            "journal_durable": bool(journal_durable),
            "status_write_ok": bool(status_write_ok),
            "current_authority_owner": st.get("owner_id"),
            "application_ready": application_ready,
        },
    }
