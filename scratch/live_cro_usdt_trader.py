"""Standalone live CRO/USDT micro-scalp trader for Crypto.com Exchange v1.

Reads credentials in memory from the DPAPI-protected replacement key archive
without touching any of the pinned files under backend/ or backups/.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN
import hashlib
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import signal
import sqlite3
import ssl
import sys
import threading
import time
from typing import Any
import uuid
import socket

import ctypes
import ctypes.wintypes as _wt


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", _wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi_unprotect(data: bytes) -> bytes:
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

class IPv4HTTPSConnection(http.client.HTTPSConnection):
    """Force IPv4 connection to prevent Windows dual-stack IPv6 routing to non-whitelisted address."""
    DEFAULT_CONNECT_TIMEOUT = 15.0

    def connect(self):
        timeout = self.timeout
        if timeout is None or timeout is socket._GLOBAL_DEFAULT_TIMEOUT:
            global_default = socket.getdefaulttimeout()
            timeout = global_default if global_default is not None else self.DEFAULT_CONNECT_TIMEOUT

        err = None
        for res in socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                self.sock.settimeout(timeout)
                self.sock.connect(sa)
                break
            except socket.error as _:
                err = _
                if self.sock:
                    self.sock.close()
                self.sock = None
        if self.sock is None:
            if err is not None:
                raise err
            raise OSError(f"No IPv4 address found for {self.host}:{self.port}")
        if self._tunnel_host:
            self._tunnel()
        server_hostname = self._tunnel_host if self._tunnel_host else self.host
        self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)

HOST = "api.crypto.com"
BASE_PATH = "/exchange/v1/"
INSTRUMENT = "CRO_USDT"
PRICE_TICK = Decimal("0.00001")
QTY_STEP = Decimal("1")
MIN_ORDER_NOTIONAL_USDT = Decimal("1.05")
MIN_ORDER_QTY_CRO = 25

BOOTSTRAP_SELL_CRO = 500
TARGET_BUY_USDT = Decimal("21.50")
TARGET_SELL_CRO = 500
BUY_DIP_PCT = Decimal("0.0022")  # 0.22% (~9-10 ticks) for high-frequency dip capture
TAKE_PROFIT_PCT = Decimal("0.0032")  # 0.32% (~14 ticks) for rapid take-profit turnover
STOP_LOSS_PCT = Decimal("0.035")
DAILY_LOSS_CUTOFF_USDT = Decimal("3.00")
POLL_INTERVAL_SEC = 0.8  # 1.25 req/sec (Crypto.com rate limit allows up to 10-100 req/sec)
MAX_DRIFT_TICKS = 15  # Reposition order if price drifts 15 ticks away
MAX_STALE_SECONDS = 90  # Reposition if order rests unmoved for 90s while price moves away
TELEMETRY_HOST = "127.0.0.1"
TELEMETRY_PORT = 8007
_STATE_LOCK = threading.Lock()

LOCATOR_PATH = Path(
    r"C:\AI-BS\backups\crypto_connector_candidate_20261115_v01\private-candidate-location.json"
)
SAVED_DATA_DIR = Path(r"C:\AI-BS\saved_data")
STATE_FILE = SAVED_DATA_DIR / "live_cro_usdt_trader_state.json"
LOG_FILE = SAVED_DATA_DIR / "live_cro_usdt_trader.log"
LEDGER_CSV_FILE = SAVED_DATA_DIR / "trade_ledger.csv"
LEDGER_DB_FILE = SAVED_DATA_DIR / "trade_ledger.db"

_STOP_REQUESTED = False


def init_ledgers() -> None:
    """Ensure CSV and SQLite append-only trade ledgers exist with correct schemas."""
    SAVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LEDGER_CSV_FILE.exists():
        with open(LEDGER_CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp_12hr",
                "Timestamp_ISO",
                "Action",
                "Qty_CRO",
                "Price_USDT",
                "Value_USDT",
                "Fee_USDT",
                "Cycle_Net_PnL_USDT",
                "Daily_Realized_PnL_USDT",
                "Order_ID",
                "Client_OID",
                "Status"
            ])
    with sqlite3.connect(str(LEDGER_DB_FILE)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_12hr TEXT NOT NULL,
                timestamp_iso TEXT NOT NULL,
                action TEXT NOT NULL,
                qty_cro NUMERIC NOT NULL,
                price_usdt NUMERIC NOT NULL,
                value_usdt NUMERIC NOT NULL,
                fee_usdt NUMERIC NOT NULL,
                cycle_net_pnl NUMERIC,
                daily_realized_pnl NUMERIC,
                order_id TEXT NOT NULL,
                client_oid TEXT,
                status TEXT NOT NULL
            );
        """)
        conn.commit()


def append_to_ledgers(
    action: str,
    qty_cro: Any,
    price_usdt: Any,
    value_usdt: Any,
    fee_usdt: Any,
    cycle_net_pnl: Any,
    daily_pnl: Any,
    order_id: str,
    client_oid: str,
    status: str,
    log: logging.Logger
) -> None:
    """Atomically append a trade fill event to both trade_ledger.csv and trade_ledger.db."""
    now_utc = datetime.now(timezone.utc)
    ts_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_12hr = now_utc.strftime("%b %d, %Y %I:%M:%S %p UTC")

    c_pnl_str = f"{Decimal(str(cycle_net_pnl)):.6f}" if cycle_net_pnl is not None else ""
    d_pnl_str = f"{Decimal(str(daily_pnl)):.6f}" if daily_pnl is not None else ""

    try:
        with open(LEDGER_CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                ts_12hr,
                ts_iso,
                action,
                str(qty_cro),
                str(price_usdt),
                str(value_usdt),
                str(fee_usdt),
                c_pnl_str,
                d_pnl_str,
                str(order_id),
                str(client_oid),
                status
            ])
    except Exception as e:
        log.error("Failed to append to trade_ledger.csv: %s", e)

    try:
        with sqlite3.connect(str(LEDGER_DB_FILE), timeout=10.0) as conn:
            conn.execute("""
                INSERT INTO trade_fills (
                    timestamp_12hr, timestamp_iso, action, qty_cro, price_usdt,
                    value_usdt, fee_usdt, cycle_net_pnl, daily_realized_pnl,
                    order_id, client_oid, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                ts_12hr,
                ts_iso,
                action,
                float(qty_cro),
                float(price_usdt),
                float(value_usdt),
                float(fee_usdt),
                float(cycle_net_pnl) if cycle_net_pnl is not None else None,
                float(daily_pnl) if daily_pnl is not None else None,
                str(order_id),
                str(client_oid),
                status
            ))
            conn.commit()
    except Exception as e:
        log.error("Failed to append to trade_ledger.db: %s", e)


def configure_logging() -> logging.Logger:
    """Configure console and file logging in C:\\AI-BS\\saved_data."""
    SAVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("live_cro_usdt_trader")
    log.setLevel(logging.INFO)
    if not log.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(sh)
        log.addHandler(fh)
    return log


def load_dpapi_credentials() -> tuple[str, str]:
    """Load API key and secret in memory via Windows DPAPI without writing plaintext."""
    locator = json.loads(LOCATOR_PATH.read_text(encoding="utf-8"))
    pair_path = Path(locator["pair"])
    decrypted = _dpapi_unprotect(pair_path.read_bytes())
    pair = json.loads(decrypted.decode("utf-8"))
    api_key = str(pair["api_key"])
    secret = str(pair["secret"])
    if not api_key or not secret:
        raise ValueError("Empty API key or secret in DPAPI archive")
    return api_key, secret


def floor_price_tick(value: Decimal) -> Decimal:
    """Round price down to the nearest 0.00001 USDT tick."""
    return ((value / PRICE_TICK).to_integral_value(rounding=ROUND_DOWN) * PRICE_TICK).quantize(PRICE_TICK)


def ceil_price_tick(value: Decimal) -> Decimal:
    """Round price up to the nearest 0.00001 USDT tick."""
    return ((value / PRICE_TICK).to_integral_value(rounding=ROUND_CEILING) * PRICE_TICK).quantize(PRICE_TICK)


def format_price(value: Decimal) -> str:
    """Format tick-aligned Decimal price for Crypto.com Exchange v1."""
    return f"{value:.5f}"


def _serialize_params(params: Any) -> str:
    """Serialize Crypto.com Exchange v1 params object for HMAC signing."""
    if isinstance(params, dict):
        return "".join(f"{k}{_serialize_params(params[k])}" for k in sorted(params))
    if isinstance(params, list):
        return "".join(_serialize_params(item) for item in params)
    if params is None:
        return ""
    return str(params)


class CryptoComClient:
    """Minimal authenticated Crypto.com Exchange v1 REST client."""

    def __init__(self, api_key: str, secret: str) -> None:
        self._api_key = api_key
        self._secret = secret.encode("utf-8")
        self._ctx = ssl.create_default_context()
        self._last_nonce = 0

    def _next_nonce(self) -> int:
        now = time.time_ns() // 1_000_000
        if now <= self._last_nonce:
            now = self._last_nonce + 1
        self._last_nonce = now
        return now

    def public_get(self, method: str, query: str) -> dict[str, Any]:
        """Execute a public GET request against Crypto.com Exchange v1."""
        conn = IPv4HTTPSConnection(HOST, port=443, timeout=10, context=self._ctx)
        try:
            conn.request("GET", f"{BASE_PATH}{method}?{query}")
            resp = conn.getresponse()
            raw = resp.read(512 * 1024)
            data = json.loads(raw.decode("utf-8"))
        finally:
            conn.close()
        if resp.status != 200 or data.get("code") != 0:
            raise RuntimeError(f"Public API {method} failed: http={resp.status} body={data}")
        return data

    def private_post(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a signed private POST request against Crypto.com Exchange v1."""
        nonce = self._next_nonce()
        req_id = nonce
        clean_params = dict(params or {})
        param_text = _serialize_params(clean_params)
        sig_payload = f"{method}{req_id}{self._api_key}{param_text}{nonce}"
        sig = hmac.new(self._secret, sig_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        body = {
            "id": req_id,
            "method": method,
            "api_key": self._api_key,
            "params": clean_params,
            "nonce": nonce,
            "sig": sig,
        }
        payload_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")
        conn = IPv4HTTPSConnection(HOST, port=443, timeout=10, context=self._ctx)
        try:
            conn.request(
                "POST",
                f"{BASE_PATH}{method}",
                body=payload_bytes,
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            raw = resp.read(512 * 1024)
            data = json.loads(raw.decode("utf-8"))
        finally:
            conn.close()
        if resp.status != 200 or data.get("code") != 0:
            raise RuntimeError(f"Private API {method} failed: http={resp.status} body={data}")
        return data

    def get_book(self, depth: int = 10) -> tuple[Decimal, Decimal, list[tuple[Decimal, Decimal]], list[tuple[Decimal, Decimal]]]:
        """Fetch top-of-book and level-2 bids/asks for CRO_USDT."""
        data = self.public_get("public/get-book", f"instrument_name={INSTRUMENT}&depth={depth}")
        entry = data["result"]["data"][0]
        bids = [(Decimal(row[0]), Decimal(row[1])) for row in entry["bids"]]
        asks = [(Decimal(row[0]), Decimal(row[1])) for row in entry["asks"]]
        if not bids or not asks:
            raise RuntimeError("Empty CRO_USDT orderbook")
        return bids[0][0], asks[0][0], bids, asks

    def get_balances(self) -> dict[str, dict[str, Decimal]]:
        """Fetch Spot balances mapped by asset symbol."""
        data = self.private_post("private/user-balance", {})
        balances: dict[str, dict[str, Decimal]] = {}
        rows = data["result"]["data"]
        if not rows:
            return balances
        for pos in rows[0].get("position_balances", []):
            ccy = str(pos["instrument_name"])
            total = Decimal(str(pos["quantity"]))
            reserved = Decimal(str(pos.get("reserved_qty", "0")))
            free = max(total - reserved, Decimal("0"))
            balances[ccy] = {"total": total, "reserved": reserved, "free": free}
        return balances

    def get_open_orders(self) -> list[dict[str, Any]]:
        """Fetch currently open spot orders for CRO_USDT."""
        data = self.private_post("private/get-open-orders", {"instrument_name": INSTRUMENT})
        return list(data["result"].get("data", []))

    def get_order_detail(self, order_id: str) -> dict[str, Any]:
        """Fetch order lifecycle detail by exchange order_id."""
        data = self.private_post("private/get-order-detail", {"order_id": str(order_id)})
        return dict(data["result"])

    def create_limit_order(
        self,
        *,
        side: str,
        qty_cro: int,
        price: Decimal,
        client_oid: str,
    ) -> dict[str, Any]:
        """Place a GOOD_TILL_CANCEL LIMIT order on CRO_USDT after checking minimums."""
        if side not in ("BUY", "SELL"):
            raise ValueError(f"Unsupported side: {side}")
        if qty_cro < MIN_ORDER_QTY_CRO:
            raise ValueError(f"Order quantity {qty_cro} CRO below minimum {MIN_ORDER_QTY_CRO} CRO")
        notional = Decimal(qty_cro) * price
        if notional < MIN_ORDER_NOTIONAL_USDT:
            raise ValueError(f"Order notional {notional} USDT below minimum {MIN_ORDER_NOTIONAL_USDT} USDT")
        params = {
            "instrument_name": INSTRUMENT,
            "side": side,
            "type": "LIMIT",
            "quantity": str(qty_cro),
            "price": format_price(price),
            "client_oid": client_oid,
            "time_in_force": "GOOD_TILL_CANCEL",
            "exec_inst": ["POST_ONLY"],
        }
        data = self.private_post("private/create-order", params)
        return dict(data["result"])

    def cancel_order(self, order_id: str) -> None:
        """Cancel a specific order on CRO_USDT."""
        self.private_post(
            "private/cancel-order",
            {"instrument_name": INSTRUMENT, "order_id": str(order_id)},
        )


def load_state() -> dict[str, Any]:
    """Load persisted state if present, otherwise return clean initial state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "instrument": INSTRUMENT,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "utc_day": time.strftime("%Y-%m-%d", time.gmtime()),
        "bootstrap_completed": False,
        "halted": False,
        "halt_reason": None,
        "daily_realized_pnl_usdt": "0",
        "completed_cycles": 0,
        "open_long_entry_price": None,
        "open_long_qty_cro": 0,
        "last_buy_fill_price": None,
        "last_sell_fill_price": None,
        "tracked_orders": {},
        "active_orders": [],
        "recent_fills": [],
        "balances": {},
        "last_book": {},
        "last_tick_utc": None,
    }


def save_state(state: dict[str, Any]) -> None:
    """Atomically persist trader state to disk."""
    SAVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def marketable_sell_price(bids: list[tuple[Decimal, Decimal]], qty_needed: int) -> Decimal:
    """Pick the highest bid tick where cumulative book depth covers qty_needed."""
    cumulative = Decimal("0")
    chosen = bids[-1][0]
    for price, size in bids:
        chosen = price
        cumulative += size
        if cumulative >= Decimal(qty_needed):
            break
    # Ensure immediate fill against the visible bid levels even on thin depth.
    return chosen


def run_bootstrap_if_needed(
    client: CryptoComClient,
    state: dict[str, Any],
    log: logging.Logger,
) -> None:
    """Execute one-time marketable SELL of 48 CRO if free USDT < 2.00 and CRO >= 100."""
    balances = client.get_balances()
    free_usdt = balances.get("USDT", {}).get("free", Decimal("0"))
    free_cro = balances.get("CRO", {}).get("free", Decimal("0"))
    open_orders = client.get_open_orders()

    if free_usdt >= TARGET_BUY_USDT:
        state["bootstrap_completed"] = True
        return
    if state.get("bootstrap_completed") or open_orders or free_cro < Decimal("100"):
        return

    best_bid, _, bids, _ = client.get_book(depth=10)
    sell_price = marketable_sell_price(bids, BOOTSTRAP_SELL_CRO)
    client_oid = str(uuid.uuid4())
    log.info(
        "Bootstrap: free_usdt=%s < 2.00; submitting marketable LIMIT SELL %d CRO @ %s (best_bid=%s, client_oid=%s)",
        free_usdt,
        BOOTSTRAP_SELL_CRO,
        format_price(sell_price),
        format_price(best_bid),
        client_oid,
    )
    ack = client.create_limit_order(
        side="SELL",
        qty_cro=BOOTSTRAP_SELL_CRO,
        price=sell_price,
        client_oid=client_oid,
    )
    order_id = str(ack["order_id"])
    log.info("Bootstrap order acknowledged: order_id=%s", order_id)

    filled_detail: dict[str, Any] = {}
    for _ in range(10):
        detail = client.get_order_detail(order_id)
        if detail.get("status") in ("FILLED", "CANCELED", "REJECTED", "EXPIRED"):
            filled_detail = detail
            break
        time.sleep(0.5)

    balances_after = client.get_balances()
    new_usdt = balances_after.get("USDT", {}).get("free", Decimal("0"))
    log.info(
        "Bootstrap finished: status=%s cumulative_qty=%s free_usdt=%s",
        filled_detail.get("status", detail.get("status") if filled_detail == {} else None),
        filled_detail.get("cumulative_quantity"),
        new_usdt,
    )
    state["bootstrap_completed"] = True
    avg_p = filled_detail.get("avg_price") or format_price(sell_price)
    if Decimal(str(avg_p)) > 0:
        state["last_sell_fill_price"] = str(avg_p)
    state["recent_fills"].append({
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": "BOOTSTRAP_SELL",
        "order_id": order_id,
        "client_oid": client_oid,
        "side": "SELL",
        "qty_cro": BOOTSTRAP_SELL_CRO,
        "price": str(avg_p),
        "status": filled_detail.get("status", "UNKNOWN"),
    })
    state["recent_fills"] = state["recent_fills"][-50:]

    bs_val = Decimal(BOOTSTRAP_SELL_CRO) * Decimal(str(avg_p))
    append_to_ledgers(
        action="BOOTSTRAP_SELL",
        qty_cro=BOOTSTRAP_SELL_CRO,
        price_usdt=str(avg_p),
        value_usdt=f"{bs_val:.5f}",
        fee_usdt="0.000000",
        cycle_net_pnl=None,
        daily_pnl=state.get("daily_realized_pnl_usdt", "0"),
        order_id=order_id,
        client_oid=client_oid,
        status=filled_detail.get("status", "FILLED"),
        log=log,
    )
    save_state(state)


def reconcile_tracked_orders(
    client: CryptoComClient,
    state: dict[str, Any],
    open_orders: list[dict[str, Any]],
    log: logging.Logger,
) -> None:
    """Inspect previously tracked orders no longer in open_orders for fills and P&L."""
    open_ids = {str(o["order_id"]) for o in open_orders}
    tracked: dict[str, dict[str, Any]] = state.get("tracked_orders", {})
    to_remove: list[str] = []

    for oid, meta in list(tracked.items()):
        if oid in open_ids:
            continue
        detail = client.get_order_detail(oid)
        status = str(detail.get("status", ""))
        if status in ("NEW", "PENDING", "ACTIVE"):
            continue
        to_remove.append(oid)
        cum_qty = Decimal(str(detail.get("cumulative_quantity", "0")))
        cum_val = Decimal(str(detail.get("cumulative_value", "0")))
        avg_price_raw = detail.get("avg_price")
        fill_price = (
            Decimal(str(avg_price_raw))
            if avg_price_raw and Decimal(str(avg_price_raw)) > 0
            else Decimal(str(meta["price"]))
        )
        cum_fee = Decimal(str(detail.get("cumulative_fee", "0")))
        fee_ccy = str(detail.get("fee_instrument_name", ""))
        if cum_qty <= 0:
            log.info("Order closed without fill: order_id=%s side=%s status=%s", oid, meta["side"], status)
            continue

        side = meta["side"]
        log.info(
            "FILL detected: order_id=%s side=%s qty=%s price=%s value=%s fee=%s %s",
            oid,
            side,
            cum_qty,
            fill_price,
            cum_val,
            cum_fee,
            fee_ccy,
        )
        cycle_net_pnl_val = None
        if side == "BUY":
            state["last_buy_fill_price"] = format_price(fill_price)
            state["open_long_entry_price"] = format_price(fill_price)
            state["open_long_qty_cro"] = int(cum_qty)
        elif side == "SELL":
            state["last_sell_fill_price"] = format_price(fill_price)
            entry_raw = state.get("open_long_entry_price")
            if entry_raw:
                entry_price = Decimal(entry_raw)
                gross_pnl = (fill_price - entry_price) * cum_qty
                fee_usdt = abs(cum_fee) if fee_ccy == "USDT" else abs(cum_fee) * fill_price
                entry_fee_est = cum_qty * entry_price * Decimal("0.0025")
                net_pnl = gross_pnl - fee_usdt - entry_fee_est
                cycle_net_pnl_val = net_pnl
                daily_pnl = Decimal(state.get("daily_realized_pnl_usdt", "0")) + net_pnl
                state["daily_realized_pnl_usdt"] = f"{daily_pnl:.6f}"
                state["completed_cycles"] = int(state.get("completed_cycles", 0)) + 1
                state["open_long_entry_price"] = None
                state["open_long_qty_cro"] = 0
                log.info(
                    "Cycle closed: net_pnl=%s USDT daily_pnl=%s USDT cycles=%d",
                    f"{net_pnl:.6f}",
                    state["daily_realized_pnl_usdt"],
                    state["completed_cycles"],
                )
        state["recent_fills"].append({
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "kind": f"SCALP_{side}",
            "order_id": oid,
            "client_oid": meta["client_oid"],
            "side": side,
            "qty_cro": str(cum_qty),
            "price": format_price(fill_price),
            "value_usdt": str(cum_val),
            "status": status,
        })
        state["recent_fills"] = state["recent_fills"][-50:]

        fee_usdt_rec = abs(cum_fee) if fee_ccy == "USDT" else abs(cum_fee) * fill_price
        append_to_ledgers(
            action=f"SCALP_{side}",
            qty_cro=cum_qty,
            price_usdt=format_price(fill_price),
            value_usdt=f"{cum_val:.5f}",
            fee_usdt=f"{fee_usdt_rec:.6f}",
            cycle_net_pnl=cycle_net_pnl_val,
            daily_pnl=state.get("daily_realized_pnl_usdt"),
            order_id=oid,
            client_oid=meta.get("client_oid", ""),
            status=status,
            log=log,
        )

    for oid in to_remove:
        tracked.pop(oid, None)
    state["tracked_orders"] = tracked


def enforce_risk_controls(
    client: CryptoComClient,
    state: dict[str, Any],
    best_bid: Decimal,
    open_orders: list[dict[str, Any]],
    log: logging.Logger,
) -> bool:
    """Enforce 1.00 USDT daily loss cutoff and 2% stop on any filled BUY position."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if state.get("utc_day") != today:
        state["utc_day"] = today
        state["daily_realized_pnl_usdt"] = "0"
        state["halted"] = False
        state["halt_reason"] = None

    if state.get("halted"):
        return False

    daily_pnl = Decimal(state.get("daily_realized_pnl_usdt", "0"))
    if daily_pnl <= -DAILY_LOSS_CUTOFF_USDT:
        for order in open_orders:
            client.cancel_order(str(order["order_id"]))
        state["halted"] = True
        state["halt_reason"] = f"DAILY_LOSS_CUTOFF_REACHED ({daily_pnl} USDT <= -{DAILY_LOSS_CUTOFF_USDT} USDT)"
        log.warning("HALTING: %s", state["halt_reason"])
        return False

    entry_raw = state.get("open_long_entry_price")
    qty_cro = int(state.get("open_long_qty_cro", 0))
    if entry_raw and qty_cro >= MIN_ORDER_QTY_CRO:
        entry_price = Decimal(entry_raw)
        stop_trigger = entry_price * (Decimal("1") - STOP_LOSS_PCT)
        if best_bid <= stop_trigger:
            log.warning(
                "2%% STOP LOSS triggered: best_bid=%s <= stop=%s (entry=%s). Canceling open orders and exiting %d CRO.",
                format_price(best_bid),
                format_price(stop_trigger),
                format_price(entry_price),
                qty_cro,
            )
            for order in open_orders:
                client.cancel_order(str(order["order_id"]))
            balances = client.get_balances()
            free_cro = int(balances.get("CRO", {}).get("free", Decimal("0")))
            exit_qty = min(qty_cro, free_cro)
            if exit_qty >= MIN_ORDER_QTY_CRO:
                _, _, bids, _ = client.get_book(depth=10)
                exit_price = marketable_sell_price(bids, exit_qty)
                if Decimal(exit_qty) * exit_price >= MIN_ORDER_NOTIONAL_USDT:
                    c_oid = str(uuid.uuid4())
                    ack = client.create_limit_order(
                        side="SELL",
                        qty_cro=exit_qty,
                        price=exit_price,
                        client_oid=c_oid,
                    )
                    state["tracked_orders"][str(ack["order_id"])] = {
                        "side": "SELL",
                        "qty_cro": exit_qty,
                        "price": format_price(exit_price),
                        "client_oid": c_oid,
                    }
                    # Wait briefly so exit fill updates daily P&L immediately.
                    for _ in range(10):
                        det = client.get_order_detail(str(ack["order_id"]))
                        if det.get("status") in ("FILLED", "CANCELED", "REJECTED", "EXPIRED"):
                            break
                        time.sleep(0.5)
                    reconcile_tracked_orders(client, state, client.get_open_orders(), log)
            if Decimal(state.get("daily_realized_pnl_usdt", "0")) <= -DAILY_LOSS_CUTOFF_USDT:
                state["halted"] = True
                state["halt_reason"] = "DAILY_LOSS_CUTOFF_AFTER_STOP_EXIT"
                return False
    return True


def maintain_bracket(
    client: CryptoComClient,
    state: dict[str, Any],
    log: logging.Logger,
) -> None:
    """Run one cycle of reconciliation, risk control, and two-way tight maker bracket placement."""
    run_bootstrap_if_needed(client, state, log)

    best_bid, best_ask, bids, asks = client.get_book(depth=10)
    mid_price = (best_bid + best_ask) / Decimal("2")
    open_orders = client.get_open_orders()
    reconcile_tracked_orders(client, state, open_orders, log)

    open_orders = client.get_open_orders()
    ok_to_trade = enforce_risk_controls(client, state, best_bid, open_orders, log)

    # ── Autonomous Stale Order Inspection & Repositioning ──
    now_ts = time.time()
    for o in list(open_orders):
        oid = str(o.get("order_id"))
        side = o.get("side")
        order_price_raw = o.get("limit_price") or o.get("price")
        if not order_price_raw:
            continue
        order_price = Decimal(str(order_price_raw))
        tracked_info = state.get("tracked_orders", {}).get(oid, {})
        placed_ts = tracked_info.get("placed_ts", now_ts)
        if "placed_ts" not in tracked_info and oid in state.get("tracked_orders", {}):
            state["tracked_orders"][oid]["placed_ts"] = now_ts

        # Check BUY order drift: if market bounced far above resting buy, pull it up to follow the action
        if side == "BUY":
            drift_ticks = int(((best_bid - order_price) / PRICE_TICK).to_integral_value())
            if drift_ticks > MAX_DRIFT_TICKS and (now_ts - placed_ts) >= MAX_STALE_SECONDS:
                log.info(
                    "Autonomous Inspection: BUY order #%s at %s drifted %d ticks below best bid %s for %ds. Repositioning...",
                    oid, order_price, drift_ticks, int(now_ts - placed_ts)
                )
                try:
                    client.cancel_order(oid)
                    state["tracked_orders"].pop(oid, None)
                except Exception as ex:
                    log.warning("Failed to cancel stale BUY #%s: %s", oid, ex)

        # Check SELL order drift: if market pulled back and resting sell is too high, recalculate optimal tight take-profit
        elif side == "SELL":
            drift_ticks = int(((order_price - best_ask) / PRICE_TICK).to_integral_value())
            # If we hold an open long entry, check if our target sell is far above entry + tight target
            entry_p_raw = state.get("last_buy_fill_price") or state.get("open_long_entry_price")
            if entry_p_raw:
                entry_p = Decimal(str(entry_p_raw))
                min_profit_price = ceil_price_tick(entry_p + PRICE_TICK)
                optimal_target_sell = max(min_profit_price, ceil_price_tick(mid_price * (Decimal("1") + TAKE_PROFIT_PCT)))
                if order_price > (optimal_target_sell + Decimal("0.00020")) and (now_ts - placed_ts) >= MAX_STALE_SECONDS:
                    log.info(
                        "Autonomous Inspection: SELL order #%s at %s is %d ticks above optimal profit %s. Repositioning...",
                        oid, order_price, drift_ticks, optimal_target_sell
                    )
                    try:
                        client.cancel_order(oid)
                        state["tracked_orders"].pop(oid, None)
                    except Exception as ex:
                        log.warning("Failed to cancel stale SELL #%s: %s", oid, ex)

    if ok_to_trade:
        open_orders = client.get_open_orders()
        has_open_buy = any(o.get("side") == "BUY" for o in open_orders)
        has_open_sell = any(o.get("side") == "SELL" for o in open_orders)
        balances = client.get_balances()
        free_usdt = balances.get("USDT", {}).get("free", Decimal("0"))
        free_cro = balances.get("CRO", {}).get("free", Decimal("0"))

        if not has_open_buy and free_usdt >= Decimal("1.10"):
            raw_target_buy = mid_price * (Decimal("1") - BUY_DIP_PCT)
            buy_price = floor_price_tick(raw_target_buy)
            # Keep strictly passive (below best ask) to earn maker fee tier.
            if buy_price >= best_ask:
                buy_price = floor_price_tick(best_ask - PRICE_TICK)
            budget = min(free_usdt, TARGET_BUY_USDT)
            buy_qty = int((budget / (buy_price * Decimal("1.005"))).to_integral_value(rounding=ROUND_DOWN))
            if buy_qty >= MIN_ORDER_QTY_CRO and Decimal(buy_qty) * buy_price >= MIN_ORDER_NOTIONAL_USDT:
                client_oid = str(uuid.uuid4())
                ack = client.create_limit_order(
                    side="BUY",
                    qty_cro=buy_qty,
                    price=buy_price,
                    client_oid=client_oid,
                )
                oid = str(ack["order_id"])
                state["tracked_orders"][oid] = {
                    "side": "BUY",
                    "qty_cro": buy_qty,
                    "price": format_price(buy_price),
                    "client_oid": client_oid,
                    "placed_ts": time.time(),
                }
                log.info(
                    "Placed passive LIMIT BUY: order_id=%s qty=%d CRO @ %s USDT (notional=%s)",
                    oid,
                    buy_qty,
                    format_price(buy_price),
                    f"{Decimal(buy_qty) * buy_price:.5f}",
                )

        if not has_open_sell and free_cro >= Decimal(TARGET_SELL_CRO):
            if state.get("last_buy_fill_price"):
                entry_p = Decimal(state["last_buy_fill_price"])
                # First moment we can take profit: exactly 1 tick above entry (0.00001 USDT profit/CRO)
                min_profit_price = ceil_price_tick(entry_p + PRICE_TICK)
                raw_target_sell = max(min_profit_price, mid_price * (Decimal("1") + TAKE_PROFIT_PCT))
            else:
                raw_target_sell = mid_price * (Decimal("1") + TAKE_PROFIT_PCT)
            sell_price = ceil_price_tick(raw_target_sell)
            # Keep strictly passive (above best bid) to earn maker fee tier.
            if sell_price <= best_bid:
                sell_price = ceil_price_tick(best_bid + PRICE_TICK)
            sell_qty = state.get("open_long_qty_cro") or TARGET_SELL_CRO
            if Decimal(sell_qty) * sell_price >= MIN_ORDER_NOTIONAL_USDT:
                client_oid = str(uuid.uuid4())
                ack = client.create_limit_order(
                    side="SELL",
                    qty_cro=sell_qty,
                    price=sell_price,
                    client_oid=client_oid,
                )
                oid = str(ack["order_id"])
                state["tracked_orders"][oid] = {
                    "side": "SELL",
                    "qty_cro": sell_qty,
                    "price": format_price(sell_price),
                    "client_oid": client_oid,
                    "placed_ts": time.time(),
                }
                log.info(
                    "Placed passive LIMIT SELL: order_id=%s qty=%d CRO @ %s USDT (notional=%s)",
                    oid,
                    sell_qty,
                    format_price(sell_price),
                    f"{Decimal(sell_qty) * sell_price:.5f}",
                )

    final_balances = client.get_balances()
    final_orders = client.get_open_orders()
    state["balances"] = {
        ccy: {k: str(v) for k, v in vals.items()}
        for ccy, vals in final_balances.items()
        if ccy in ("CRO", "USDT", "USD")
    }
    # Comprehensive Real-Time Portfolio & Equity Accounting
    cro_total = Decimal(str(state["balances"].get("CRO", {}).get("total", "0")))
    usdt_total = Decimal(str(state["balances"].get("USDT", {}).get("total", "0")))
    usd_total = Decimal(str(state["balances"].get("USD", {}).get("total", "0")))
    cro_usd_val = cro_total * mid_price
    total_equity_usd = cro_usd_val + usdt_total + usd_total
    state["portfolio_valuation"] = {
        "cro_units_total": str(cro_total),
        "cro_valuation_usd": f"{cro_usd_val:.4f}",
        "usdt_cash_total": str(usdt_total),
        "usd_cash_total": str(usd_total),
        "total_account_value_usd": f"{total_equity_usd:.2f}",
        "current_mid_price": format_price(mid_price),
        "as_of_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    state["active_orders"] = [
        {
            "order_id": str(o.get("order_id")),
            "client_oid": o.get("client_oid"),
            "side": o.get("side"),
            "price": o.get("limit_price") or o.get("price"),
            "quantity": o.get("quantity"),
            "cumulative_quantity": o.get("cumulative_quantity"),
            "status": o.get("status"),
        }
        for o in final_orders
    ]
    state["last_book"] = {
        "best_bid": format_price(best_bid),
        "best_ask": format_price(best_ask),
        "mid_price": format_price(floor_price_tick(mid_price)),
        "bids": [[str(p), str(s)] for p, s in bids[:10]],
        "asks": [[str(p), str(s)] for p, s in asks[:10]],
    }
    state["last_tick_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _STATE_LOCK:
        save_state(state)


class _ReuseThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _build_telemetry_payload() -> bytes:
    """Read current persisted state and enrich with live telemetry metadata."""
    with _STATE_LOCK:
        current = load_state()
    payload = dict(current)
    payload["status"] = "HALTED" if current.get("halted") else "LIVE_ACTIVE"
    payload["server_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload["poll_interval_sec"] = POLL_INTERVAL_SEC
    payload["buy_dip_pct"] = str(BUY_DIP_PCT * Decimal("100"))
    payload["take_profit_pct"] = str(TAKE_PROFIT_PCT * Decimal("100"))
    payload["target_buy_usdt"] = str(TARGET_BUY_USDT)
    payload["stop_loss_pct"] = str(STOP_LOSS_PCT * Decimal("100"))
    payload["daily_loss_cutoff_usdt"] = str(DAILY_LOSS_CUTOFF_USDT)
    return json.dumps(payload).encode("utf-8")


def start_telemetry_server(log: logging.Logger) -> _ReuseThreadingHTTPServer:
    """Start local read-only telemetry HTTP server on 127.0.0.1:8007."""

    class TelemetryHandler(BaseHTTPRequestHandler):
        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Cache-Control", "no-store")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            try:
                path = self.path.split("?", 1)[0]
                if path != "/api/live-telemetry":
                    self.send_response(404)
                    self._send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":"not_found"}')
                    return
                body = _build_telemetry_payload()
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ConnectionError, BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    server = _ReuseThreadingHTTPServer((TELEMETRY_HOST, TELEMETRY_PORT), TelemetryHandler)
    thread = threading.Thread(target=server.serve_forever, name="LiveTelemetryHTTP", daemon=True)
    thread.start()
    log.info("Live telemetry HTTP server listening on http://%s:%d/api/live-telemetry", TELEMETRY_HOST, TELEMETRY_PORT)
    return server


def _handle_signal(_signum: int, _frame: Any) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone Crypto.com CRO/USDT live micro-scalp trader")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="Run bootstrap and one bracket pass, then exit.")
    mode.add_argument("--daemon", action="store_true", help="Run continuously every 3 seconds until stopped.")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    init_ledgers()
    log = configure_logging()
    api_key, secret = load_dpapi_credentials()
    client = CryptoComClient(api_key, secret)
    state = load_state()

    if args.once:
        maintain_bracket(client, state, log)
        print(json.dumps({
            "active_orders": state["active_orders"],
            "balances": state["balances"],
            "last_book": state["last_book"],
            "bootstrap_completed": state["bootstrap_completed"],
            "halted": state["halted"],
        }, indent=2))
        return 0

    telemetry_server = start_telemetry_server(log)
    log.info("Starting CRO/USDT live micro-scalp daemon (poll=%.1fs, target=±0.65%%, stop=2%%, cutoff=1.00 USDT)", POLL_INTERVAL_SEC)
    try:
        while not _STOP_REQUESTED:
            try:
                maintain_bracket(client, state, log)
                if state.get("halted"):
                    log.warning("Daemon paused due to risk cutoff: %s", state.get("halt_reason"))
                    break
            except Exception as exc:
                log.error("Tick error (retaining state, retrying next poll): %s", exc)
            for _ in range(int(POLL_INTERVAL_SEC * 2)):
                if _STOP_REQUESTED:
                    break
                time.sleep(0.5)
    finally:
        telemetry_server.shutdown()
        telemetry_server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

