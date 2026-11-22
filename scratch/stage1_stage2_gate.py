import hashlib
import hmac
import json
import os
import sqlite3
import sys
import time
import urllib.request
from decimal import Decimal, ROUND_UP
from pathlib import Path

# Permanent 64-bit order-ID regression fixtures (exact delta = 138; float64 collides both to 6530219611080823808)
FIXTURE_SELL_ID = "6530219611080823900"
FIXTURE_BUY_ID = "6530219611080823762"


def lossless_json_loads(raw_text: str):
    """Preserve all JSON integers as exact strings and decimals as Decimal."""
    return json.loads(raw_text, parse_int=str, parse_float=Decimal)


def flatten_params(params: dict, level: int = 0) -> str:
    """Crypto.com Exchange v1 alphabetical key-value concatenation (MAX_LEVEL = 3)."""
    if not params or level >= 3:
        return ""
    out = []
    for k in sorted(params.keys()):
        v = params[k]
        if isinstance(v, dict):
            out.append(k + flatten_params(v, level + 1))
        elif isinstance(v, list):
            items = "".join(
                flatten_params(item, level + 1) if isinstance(item, dict) else str(item)
                for item in v
            )
            out.append(k + items)
        else:
            out.append(k + str(v))
    return "".join(out)


class ReadOnlyExchangeClient:
    """Strict read-only client for Crypto.com Exchange v1 REST API."""

    ALLOWED_READ_METHODS = {
        "public/get-instruments",
        "private/get-account-settings",
        "private/get-instrument-fee-rate",
        "private/get-fee-credit-balances",
        "private/user-balance",
        "private/get-open-orders",
        "private/get-order-history",
        "private/get-trades",
    }

    def __init__(self, base_url: str, api_key: str = "", api_secret: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")

    def request(self, method: str, params: dict | None = None):
        if method not in self.ALLOWED_READ_METHODS:
            raise PermissionError(f"Blocked non-read-only method: {method}")
        params = params or {}
        if method.startswith("public/"):
            url = f"{self.base_url}/{method}"
            with urllib.request.urlopen(url, timeout=15) as resp:
                return lossless_json_loads(resp.read().decode("utf-8"))

        if not self.api_key or not self.api_secret:
            raise ValueError("Missing API credentials for private read-only query.")

        req_id = int(time.time() * 1000)
        nonce = int(time.time() * 1000)
        sig_payload = f"{method}{req_id}{self.api_key}{flatten_params(params)}{nonce}"
        sig = hmac.new(self.api_secret, sig_payload.encode("utf-8"), hashlib.sha256).hexdigest()

        body = json.dumps({
            "id": req_id,
            "method": method,
            "api_key": self.api_key,
            "params": params,
            "nonce": nonce,
            "sig": sig,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/{method}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return lossless_json_loads(resp.read().decode("utf-8"))


def init_authoritative_ledger(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite >= 3.35 in WAL mode with synchronous=FULL and TEXT IDs."""
    ver = tuple(int(x) for x in sqlite3.sqlite_version.split("."))
    if ver < (3, 35, 0):
        raise RuntimeError(f"SQLite {sqlite3.sqlite_version} < 3.35.0 required for robust WAL and modern SQL")

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reconciled_trades (
            trade_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            client_oid TEXT,
            instrument_name TEXT NOT NULL,
            side TEXT NOT NULL,
            liquidity_indicator TEXT NOT NULL,
            traded_price TEXT NOT NULL,
            traded_quantity TEXT NOT NULL,
            net_fee TEXT NOT NULL,
            fee_credits TEXT NOT NULL,
            fee_currency TEXT NOT NULL,
            create_time_ns TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS state_transitions (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            from_state TEXT NOT NULL,
            to_state TEXT NOT NULL,
            reason TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def run_stage2_self_tests(work_dir: Path) -> dict:
    """Execute deterministic Stage 2 safety invariants offline."""
    results = {}

    # 1. Verify IEEE-754 float64 collision vs. lossless string parsing
    collides_in_float = float(FIXTURE_SELL_ID) == float(FIXTURE_BUY_ID)
    raw_json = f'{{"sell_id": {FIXTURE_SELL_ID}, "buy_id": {FIXTURE_BUY_ID}}}'
    parsed = lossless_json_loads(raw_json)
    exact_diff = int(parsed["sell_id"]) - int(parsed["buy_id"])
    assert collides_in_float is True
    assert parsed["sell_id"] != parsed["buy_id"] and exact_diff == 138
    results["64bit_id_preservation"] = "PASS (delta=138 preserved as TEXT)"

    # 2. Verify SQLite WAL + synchronous=FULL + duplicate trade_id rejection
    test_db = work_dir / "stage2_gate_test.sqlite3"
    if test_db.exists():
        test_db.unlink()
    conn = init_authoritative_ledger(test_db)
    sync_mode = conn.execute("PRAGMA synchronous;").fetchone()[0]
    journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert sync_mode == 2 and journal_mode.lower() == "wal"

    sample_row = (
        "900719925474099999",
        FIXTURE_BUY_ID,
        "client-001",
        "CRO_USDT",
        "BUY",
        "MAKER",
        "0.04304",
        "497",
        "0.000000",
        "0",
        "CRO",
        "1731715200000000000",
    )
    conn.execute("INSERT INTO reconciled_trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", sample_row)
    conn.execute("INSERT OR IGNORE INTO reconciled_trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", sample_row)
    conn.commit()
    row_count = conn.execute("SELECT COUNT(*) FROM reconciled_trades;").fetchone()[0]
    stored_oid = conn.execute("SELECT order_id FROM reconciled_trades;").fetchone()[0]
    assert row_count == 1 and stored_oid == FIXTURE_BUY_ID
    results["sqlite_wal_full_and_dedup"] = f"PASS (SQLite {sqlite3.sqlite_version}, sync=FULL)"

    # 3. Verify tick-rounded fee break-even calculation using Decimal (0.00% maker fee verified)
    entry = Decimal("0.04304")
    fee_m = Decimal("0.0000")  # Verified 0% maker fee tier
    tick = Decimal("0.00001")
    be_exact = entry * (Decimal("1") + fee_m) / (Decimal("1") - fee_m)
    be_tick = (be_exact / tick).to_integral_value(rounding=ROUND_UP) * tick
    assert be_tick == Decimal("0.04304")
    results["decimal_tick_breakeven"] = f"PASS (0.04304 -> {be_tick} at 0.00% fee)"

    conn.close()
    test_db.unlink(missing_ok=True)
    return results


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    gate_report = run_stage2_self_tests(base)
    print(json.dumps({"stage2_offline_invariants": gate_report}, indent=2))
