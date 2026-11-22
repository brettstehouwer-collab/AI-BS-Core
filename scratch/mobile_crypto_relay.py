"""Read-Only Authenticated Mobile Crypto Account Relay (Port 8017).

Aggregates live CRO_USDT market book/orders/balances/open_lots from :8007
(fallback structural_dip_state.json), Agent 4 risk watchdog telemetry,
Agent 2 scout walls, OCI standby mode, and full historical trade fills
from trade_ledger.db.

Security invariants:
  - Strictly READ-ONLY (GET requests only; HTTP 405 on POST/PUT/DELETE/PATCH).
  - Binds ONLY to 127.0.0.1:8017 (exposed externally ONLY via Cloudflare Tunnel
    HTTPS path `/mobile-crypto/.*` on ai-bs.brettstehouwer.live).
  - Requires constant-time `Authorization: Bearer <256-bit token>` on
    `/mobile-crypto/snapshot`.
  - Zero exchange trading/withdrawal credentials exist in this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import sys
import urllib.request
from typing import Any


HOST = "127.0.0.1"
PORT = 8017
SAVED_DATA_DIR = Path(r"C:\AI-BS\saved_data")
TOKEN_FILE = SAVED_DATA_DIR / "mobile_crypto_relay_token.txt"
TELEMETRY_URL = "http://127.0.0.1:8007/api/live-telemetry"
STATE_FILE = SAVED_DATA_DIR / "structural_dip_state.json"
WATCHDOG_FILE = SAVED_DATA_DIR / "agent4_watchdog_status.json"
SCOUT_FILE = SAVED_DATA_DIR / "orderbook_scout_signals.json"
ARB_FILE = SAVED_DATA_DIR / "triangular_arb_opportunities.json"
SUPERVISOR_FILE = SAVED_DATA_DIR / "master_supervisor_status.json"
OCI_STATUS_FILE = SAVED_DATA_DIR / "oci_claimer_status.json"
LEDGER_DB_FILE = SAVED_DATA_DIR / "trade_ledger.db"
LOG_FILE = SAVED_DATA_DIR / "mobile_crypto_relay.log"

_STOP_REQUESTED = False


def configure_logging() -> logging.Logger:
    SAVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("mobile_crypto_relay")
    log.setLevel(logging.INFO)
    if not log.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        log.addHandler(fh)
        log.addHandler(sh)
    return log


def ensure_bearer_token(token_file: Path = TOKEN_FILE) -> str:
    """Load or generate a 256-bit URL-safe bearer token without printing it."""
    token_file.parent.mkdir(parents=True, exist_ok=True)
    if token_file.is_file():
        existing = token_file.read_text(encoding="utf-8").strip()
        if len(existing) >= 32:
            return existing
    tok = secrets.token_urlsafe(32)
    tmp = token_file.with_suffix(".txt.tmp")
    tmp.write_text(tok, encoding="utf-8")
    os.replace(tmp, token_file)
    return tok


def _read_json_safe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _fetch_engine_telemetry() -> dict[str, Any]:
    try:
        req = urllib.request.Request(TELEMETRY_URL, headers={"User-Agent": "MobileCryptoRelay/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return _read_json_safe(STATE_FILE)


def _read_db_fills(limit: int = 25) -> list[dict[str, Any]]:
    if not LEDGER_DB_FILE.is_file():
        return []
    conn: sqlite3.Connection | None = None
    try:
        uri = f"file:{LEDGER_DB_FILE.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=3.0)
        conn.row_factory = sqlite3.Row
        cols = {row[1] for row in conn.execute("PRAGMA table_info(trade_fills);").fetchall()}
        if not cols:
            return []
        has_text = "qty_text" in cols and "price_text" in cols
        if has_text:
            sql = """
                SELECT id, timestamp_12hr, timestamp_iso, action,
                       COALESCE(qty_text, CAST(qty_cro AS TEXT)) AS qty_cro,
                       COALESCE(price_text, CAST(price_usdt AS TEXT)) AS price_usdt,
                       COALESCE(value_text, CAST(value_usdt AS TEXT)) AS value_usdt,
                       COALESCE(fee_text, CAST(fee_usdt AS TEXT)) AS fee_usdt,
                       COALESCE(cycle_net_pnl_text, CAST(cycle_net_pnl AS TEXT)) AS cycle_net_pnl,
                       order_id, client_oid, status
                FROM trade_fills
                ORDER BY id DESC
                LIMIT ?;
            """
        else:
            sql = """
                SELECT id, timestamp_12hr, timestamp_iso, action,
                       CAST(qty_cro AS TEXT) AS qty_cro,
                       CAST(price_usdt AS TEXT) AS price_usdt,
                       CAST(value_usdt AS TEXT) AS value_usdt,
                       CAST(fee_usdt AS TEXT) AS fee_usdt,
                       CAST(cycle_net_pnl AS TEXT) AS cycle_net_pnl,
                       order_id, client_oid, status
                FROM trade_fills
                ORDER BY id DESC
                LIMIT ?;
            """
        rows = conn.execute(sql, (int(limit),)).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            act = str(r["action"] or "")
            side = "SELL" if "SELL" in act.upper() else ("BUY" if "BUY" in act.upper() else act)
            out.append({
                "id": int(r["id"]),
                "timestamp_12hr": r["timestamp_12hr"],
                "timestamp_iso": r["timestamp_iso"],
                "action": act,
                "side": side,
                "qty_cro": str(r["qty_cro"] or "0"),
                "price": str(r["price_usdt"] or "0"),
                "value_usdt": str(r["value_usdt"] or "0"),
                "fee_usdt": str(r["fee_usdt"] or "0"),
                "cycle_net_pnl": str(r["cycle_net_pnl"]) if r["cycle_net_pnl"] is not None else None,
                "order_id": str(r["order_id"] or ""),
                "client_oid": str(r["client_oid"] or ""),
                "status": str(r["status"] or ""),
            })
        return out
    except Exception:
        return []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _read_db_stats() -> dict[str, Any]:
    empty = {
        "total_trades": 0,
        "buy_count": 0,
        "sell_count": 0,
        "total_volume_usdt": "0.00",
        "total_fees_usdt": "0.00",
        "ledger_net_pnl_usdt": "0.000000",
        "cumulative_pnl_series": [],
    }
    if not LEDGER_DB_FILE.is_file():
        return empty
    conn: sqlite3.Connection | None = None
    try:
        uri = f"file:{LEDGER_DB_FILE.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=3.0)
        row = conn.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN UPPER(action) LIKE '%BUY%' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN UPPER(action) LIKE '%SELL%' THEN 1 ELSE 0 END),
                   COALESCE(SUM(CAST(value_usdt AS REAL)), 0.0),
                   COALESCE(SUM(CAST(fee_usdt AS REAL)), 0.0),
                   COALESCE(SUM(COALESCE(CAST(cycle_net_pnl AS REAL), 0.0)), 0.0)
            FROM trade_fills;
            """
        ).fetchone()
        pnl_rows = conn.execute(
            """
            SELECT id, timestamp_iso, COALESCE(cycle_net_pnl_text, CAST(cycle_net_pnl AS TEXT)) AS pnl_txt
            FROM trade_fills
            WHERE cycle_net_pnl IS NOT NULL
            ORDER BY id ASC;
            """
        ).fetchall()
        series: list[dict[str, Any]] = []
        running = Decimal("0")
        for r_id, ts_iso, pnl_txt in pnl_rows:
            if pnl_txt is None:
                continue
            try:
                val = Decimal(str(pnl_txt))
            except (InvalidOperation, ValueError):
                continue
            if not series:
                series.append({"id": 0, "pnl": 0.0, "ts": str(ts_iso or "")})
            running += val
            series.append({"id": int(r_id), "pnl": round(float(running), 6), "ts": str(ts_iso or "")})
        if len(series) > 40:
            series = series[-40:]
        return {
            "total_trades": int(row[0] or 0),
            "buy_count": int(row[1] or 0),
            "sell_count": int(row[2] or 0),
            "total_volume_usdt": f"{float(row[3] or 0.0):.2f}",
            "total_fees_usdt": f"{float(row[4] or 0.0):.4f}",
            "ledger_net_pnl_usdt": f"{float(row[5] or 0.0):.6f}",
            "cumulative_pnl_series": series,
        }
    except Exception:
        return empty
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _to_decimal(val: Any) -> Decimal | None:
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def build_snapshot_payload() -> dict[str, Any]:
    """Assemble complete read-only crypto account, orders, lots, fills, agents, and risk snapshot."""
    now_iso = datetime.now(timezone.utc).isoformat()
    eng = _fetch_engine_telemetry()
    wd = _read_json_safe(WATCHDOG_FILE)
    scout = _read_json_safe(SCOUT_FILE) or (eng.get("scout_summary") or {})
    arb = _read_json_safe(ARB_FILE)
    sup = _read_json_safe(SUPERVISOR_FILE)
    oci = _read_json_safe(OCI_STATUS_FILE)

    last_book = eng.get("last_book") or {}
    val = eng.get("portfolio_valuation") or {}
    balances = eng.get("balances") or {}
    active_orders = list(eng.get("active_orders") or [])
    buy_orders = [o for o in active_orders if str(o.get("side", "")).upper() == "BUY"]
    sell_orders = [o for o in active_orders if str(o.get("side", "")).upper() == "SELL"]
    order_price_by_id = {str(o.get("order_id", "")): o.get("price") for o in active_orders if o.get("order_id")}

    mid_dec = _to_decimal(last_book.get("mid_price") or val.get("current_mid_price"))
    raw_lots = list(eng.get("open_lots") or [])
    open_lots: list[dict[str, Any]] = []
    total_cost = Decimal("0")
    total_cur_val = Decimal("0")
    for raw_lot in raw_lots:
        lot = dict(raw_lot)
        qty_d = _to_decimal(lot.get("qty_cro"))
        entry_d = _to_decimal(lot.get("entry_price"))
        sell_id = str(lot.get("sell_order_id", ""))
        tp_px_raw = order_price_by_id.get(sell_id)
        tp_d = _to_decimal(tp_px_raw)
        if qty_d is not None and entry_d is not None and entry_d > 0:
            cost_d = qty_d * entry_d
            total_cost += cost_d
            lot["cost_usdt"] = f"{cost_d:.4f}"
            if mid_dec is not None and mid_dec > 0:
                cur_d = qty_d * mid_dec
                total_cur_val += cur_d
                upnl_d = cur_d - cost_d
                upnl_pct = (upnl_d / cost_d) * Decimal("100")
                lot["current_value_usdt"] = f"{cur_d:.4f}"
                lot["unrealized_pnl_usdt"] = f"{upnl_d:+.4f}"
                lot["unrealized_pnl_pct"] = f"{upnl_pct:+.2f}"
                if tp_d is not None and tp_d > 0:
                    dist_pct = ((tp_d - mid_dec) / mid_dec) * Decimal("100")
                    lot["target_sell_price"] = str(tp_px_raw)
                    lot["pct_to_target"] = f"{dist_pct:.2f}"
            elif tp_d is not None:
                lot["target_sell_price"] = str(tp_px_raw)
        open_lots.append(lot)

    total_upnl = total_cur_val - total_cost if (total_cost > 0 and total_cur_val > 0) else Decimal("0")
    total_upnl_pct = ((total_upnl / total_cost) * Decimal("100")) if (total_cost > 0 and total_cur_val > 0) else Decimal("0")

    db_fills = _read_db_fills(50)
    db_stats = _read_db_stats()
    mem_fills = list(reversed(eng.get("recent_fills") or []))
    recent_fills = db_fills if db_fills else [
        {
            "id": f"mem-{idx}",
            "timestamp_iso": f.get("utc"),
            "action": f.get("kind") or f.get("side"),
            "side": f.get("side"),
            "qty_cro": str(f.get("qty_cro", "0")),
            "price": str(f.get("price", "0")),
            "value_usdt": str(f.get("value_usdt", "0")),
            "fee_usdt": "0",
            "cycle_net_pnl": None,
            "order_id": str(f.get("order_id", "")),
            "client_oid": str(f.get("client_oid", "")),
            "status": str(f.get("status", "")),
        }
        for idx, f in enumerate(mem_fills[:50])
    ]

    key_levels = scout.get("key_levels") or {}
    support_price = key_levels.get("major_bid_support_price") or key_levels.get("major_support_wall_price")
    ask_wall_price = key_levels.get("major_ask_wall_price")
    cb = wd.get("circuit_breaker_status") or {}
    wd_eq = wd.get("equity_snapshot") or {}

    sup_services_raw = sup.get("services") or []
    sup_services = [
        {
            "id": s.get("id"),
            "label": s.get("label"),
            "status": s.get("status"),
            "healthy": bool(s.get("healthy", False)),
            "port": s.get("port"),
            "heals_total": int(s.get("heals_total") or 0),
        }
        for s in sup_services_raw
        if isinstance(s, dict)
    ]

    return {
        "fetched_utc": now_iso,
        "read_only": True,
        "instrument": eng.get("instrument") or "CRO_USDT",
        "engine_status": eng.get("status") or ("HALTED" if eng.get("halted") else "LIVE_ACTIVE"),
        "engine_last_tick_utc": eng.get("last_tick_utc"),
        "scenario_mode": eng.get("scenario_mode") or "PATIENT_SWING",
        "halted": bool(eng.get("halted", False)),
        "halt_reason": eng.get("halt_reason"),
        "ha_role": eng.get("ha_role") or ((eng.get("ha_health") or {}).get("role")) or "PRIMARY",
        "market": {
            "best_bid": last_book.get("best_bid"),
            "best_ask": last_book.get("best_ask"),
            "mid_price": last_book.get("mid_price") or val.get("current_mid_price"),
            "bids": (last_book.get("bids") or [])[:5],
            "asks": (last_book.get("asks") or [])[:5],
            "scout_safe_buy_ceiling": scout.get("safe_buy_ceiling"),
            "scout_ask_wall": ask_wall_price,
            "scout_support_wall": support_price,
        },
        "scout": {
            "timestamp_utc": scout.get("timestamp_utc"),
            "spread_bps": scout.get("spread_bps"),
            "market_regime": scout.get("market_regime"),
            "action_bias": scout.get("action_bias"),
            "safe_buy_ceiling": scout.get("safe_buy_ceiling"),
            "major_bid_support_price": support_price,
            "major_bid_support_qty": key_levels.get("major_bid_support_qty"),
            "major_ask_wall_price": ask_wall_price,
            "major_ask_wall_qty": key_levels.get("major_ask_wall_qty"),
            "window_1_5pct": scout.get("window_1_5pct") or {},
        },
        "arb_scout": {
            "timestamp_utc": arb.get("timestamp_utc"),
            "status": arb.get("status") or "UNKNOWN",
            "account_equity_usd": arb.get("account_equity_usd"),
            "activation_threshold_usd": arb.get("activation_threshold_usd"),
            "live_trading_unlocked": bool(arb.get("live_trading_unlocked", False)),
            "best_synthetic_direction": arb.get("best_synthetic_direction"),
            "best_edge_bps": arb.get("best_edge_bps"),
            "synthetic_edges_bps": arb.get("synthetic_edges_bps") or {},
            "market_prices": arb.get("market_prices") or {},
        },
        "account": {
            "total_equity_usdt": val.get("total_account_value_usd") or wd_eq.get("total_equity_usdt"),
            "balances": balances,
            "daily_realized_pnl_usdt": str(eng.get("daily_realized_pnl_usdt") or "0.000000"),
            "total_realized_pnl_usdt": str(eng.get("total_realized_pnl_usdt") or "0.000000"),
            "profit_reserve_usdt": str(eng.get("profit_reserve_usdt") or "0.000000"),
            "completed_cycles": int(eng.get("completed_cycles") or 0),
            "open_long_qty_cro": int(eng.get("open_long_qty_cro") or 0),
            "open_long_entry_price": eng.get("open_long_entry_price"),
            "total_cost_basis_usdt": f"{total_cost:.4f}" if total_cost > 0 else "0.0000",
            "total_unrealized_pnl_usdt": f"{total_upnl:+.4f}",
            "total_unrealized_pnl_pct": f"{total_upnl_pct:+.2f}",
        },
        "active_orders": active_orders,
        "buy_orders": buy_orders,
        "sell_orders": sell_orders,
        "open_lots": open_lots,
        "recent_fills": recent_fills,
        "ledger_stats": db_stats,
        "supervisor": {
            "timestamp_utc": sup.get("timestamp_utc"),
            "services_healthy": int(sup.get("services_healthy") or 0),
            "services_total": int(sup.get("services_total") or 0),
            "safe_recovery_mode": bool(sup.get("safe_recovery_mode", False)),
            "services": sup_services,
        },
        "watchdog": {
            "watchdog_status": wd.get("watchdog_status") or "UNKNOWN",
            "watchdog_health": wd.get("watchdog_health") or "UNKNOWN",
            "timestamp_utc": wd.get("timestamp_utc"),
            "equity_drawdown_usdt": cb.get("equity_drawdown_usdt", 0.0),
            "max_allowable_drawdown_usdt": cb.get("max_allowable_drawdown_usdt", 3.0),
            "kill_switch_tripped": bool(cb.get("kill_switch_tripped", False)),
            "drift_count": len(wd.get("excessive_drift_orders") or []),
            "integrity_issue_count": len(wd.get("order_integrity_issues") or []),
            "stale_alert_count": len(wd.get("stale_data_alerts") or []),
        },
        "standby_oci": {
            "mode": oci.get("controller_mode") or "UNKNOWN",
            "active_instance_count": len(oci.get("active_instances") or []),
            "checked_utc": oci.get("checked_utc"),
        },
    }


class _ReuseHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_server(token: str, host: str = HOST, port: int = PORT) -> _ReuseHTTPServer:
    expected_auth = f"Bearer {token}"

    class RelayHandler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, obj: dict[str, Any]) -> None:
            body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            try:
                path = self.path.split("?", 1)[0]
                if path == "/mobile-crypto/health":
                    self._send_json(200, {"status": "ok", "service": "mobile_crypto_relay", "read_only": True})
                    return

                if path != "/mobile-crypto/snapshot":
                    self._send_json(404, {"error": "not_found"})
                    return

                auth = self.headers.get("Authorization", "")
                if not hmac.compare_digest(auth.encode("utf-8"), expected_auth.encode("utf-8")):
                    self._send_json(401, {"error": "unauthorized"})
                    return

                self._send_json(200, build_snapshot_payload())
            except (ConnectionError, BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def _deny_mutation(self) -> None:
            self._send_json(405, {"error": "read_only_method_not_allowed"})

        def do_POST(self) -> None:  # noqa: N802
            self._deny_mutation()

        def do_PUT(self) -> None:  # noqa: N802
            self._deny_mutation()

        def do_DELETE(self) -> None:  # noqa: N802
            self._deny_mutation()

        def do_PATCH(self) -> None:  # noqa: N802
            self._deny_mutation()

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return _ReuseHTTPServer((host, port), RelayHandler)


def _handle_signal(_signum: int, _frame: Any) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def main() -> int:
    global _STOP_REQUESTED
    _STOP_REQUESTED = False
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log = configure_logging()
    token = ensure_bearer_token()
    server = create_server(token)
    log.info("Mobile Crypto Read-Only Relay listening on http://%s:%d/mobile-crypto/snapshot", HOST, PORT)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
