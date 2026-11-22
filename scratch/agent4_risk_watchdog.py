"""Agent 4: Risk & Drift Watchdog Daemon.

AI-BS Multi-Agent Crypto Pod - Defense Layer

Role:
- Polls :8007/api/live-telemetry and queries Crypto.com Exchange directly
  (private/get-open-orders, public/get-book) every 10s.
- Queries private/user-balance on startup and every 60s to audit live total
  account equity & drawdown.
- Validates POST_ONLY + GOOD_TILL_CANCEL + 0-fee order integrity and applies
  dip-grid-compatible drift bands without false alarms or auto-cancellations.
- Atomically writes C:\\AI-BS\\saved_data\\agent4_watchdog_status.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
import logging
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any
import urllib.request

INSTRUMENT = "CRO_USDT"
SAVED_DATA_DIR = Path(r"C:\AI-BS\saved_data")
OUTPUT_STATUS_PATH = SAVED_DATA_DIR / "agent4_watchdog_status.json"
SCOUT_SIGNAL_PATH = SAVED_DATA_DIR / "orderbook_scout_signals.json"
LOG_FILE = SAVED_DATA_DIR / "agent4_risk_watchdog.log"
TRADER_MODULE_PATH = Path(r"C:\AI-BS\scratch\live_cro_usdt_trader.py")

TELEMETRY_URL = "http://127.0.0.1:8007/api/live-telemetry"
POLL_INTERVAL_SEC = 10
EQUITY_POLL_INTERVAL_SEC = 60
MAX_TELEMETRY_AGE_SEC = 30.0
MAX_SCOUT_AGE_SEC = 15.0
MAX_BUY_DIP_DRIFT_PCT = Decimal("0.08")   # 8.0% below mid
MAX_SELL_TP_DRIFT_PCT = Decimal("0.10")   # 10.0% above mid
MAX_ALLOWABLE_DRAWDOWN_USDT = Decimal("3.00")

_STOP_REQUESTED = False
_TRADER_MOD: Any = None
_HA_MOD: Any = None


def _get_trader_mod() -> Any:
    global _TRADER_MOD
    if _TRADER_MOD is None:
        spec = importlib.util.spec_from_file_location("trader_mod", str(TRADER_MODULE_PATH))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load trader module from {TRADER_MODULE_PATH}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _TRADER_MOD = mod
    return _TRADER_MOD


def _get_ha_mod() -> Any:
    global _HA_MOD
    if _HA_MOD is None:
        if "ha_execution_gateway" in sys.modules:
            _HA_MOD = sys.modules["ha_execution_gateway"]
        else:
            ha_path = Path(__file__).resolve().parent / "ha_execution_gateway.py"
            spec = importlib.util.spec_from_file_location("ha_execution_gateway", str(ha_path))
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Unable to load ha_execution_gateway from {ha_path}")
            mod = importlib.util.module_from_spec(spec)
            sys.modules["ha_execution_gateway"] = mod
            spec.loader.exec_module(mod)
            _HA_MOD = mod
    return _HA_MOD


def configure_logging() -> logging.Logger:
    """Configure stdout and file logging for Agent 4 watchdog."""
    SAVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("agent4_risk_watchdog")
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


def load_client(*, require_dedicated_readonly: bool = False) -> Any:
    """Load dedicated Read-Only credentials (fallback to legacy if unconfigured) inside PassiveStandbyClient."""
    mod = _get_trader_mod()
    ha_mod = _get_ha_mod()
    try:
        api_key, secret, _src = ha_mod.load_readonly_credentials()
    except FileNotFoundError:
        if require_dedicated_readonly:
            raise
        api_key, secret = mod.load_dpapi_credentials()
    return ha_mod.PassiveStandbyClient(mod.CryptoComClient(api_key, secret))


def _parse_iso_utc(ts_str: Any) -> datetime | None:
    if not ts_str or not isinstance(ts_str, str):
        return None
    try:
        normalized = ts_str.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def check_trader_telemetry() -> dict[str, Any]:
    """Fetch live telemetry from Agent 1 (:8007/api/live-telemetry)."""
    try:
        req = urllib.request.Request(TELEMETRY_URL, headers={"User-Agent": "Agent4-Watchdog"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def check_scout_freshness(now_utc: datetime) -> dict[str, Any] | None:
    """Check Agent 2 orderbook_scout_signals.json freshness; return alert dict if stale."""
    if not SCOUT_SIGNAL_PATH.exists():
        return {"source": "agent2_scout", "reason": "missing"}
    try:
        data = json.loads(SCOUT_SIGNAL_PATH.read_text(encoding="utf-8"))
        ts_dt = _parse_iso_utc(data.get("timestamp_utc"))
        if ts_dt is None:
            return {"source": "agent2_scout", "reason": "invalid_timestamp"}
        age_sec = (now_utc - ts_dt).total_seconds()
        if age_sec > MAX_SCOUT_AGE_SEC:
            return {
                "source": "agent2_scout",
                "reason": "stale",
                "age_sec": round(age_sec, 2),
                "threshold_sec": MAX_SCOUT_AGE_SEC,
            }
        return None
    except Exception as exc:
        return {"source": "agent2_scout", "reason": f"read_error: {exc}"}


def run_watchdog_cycle(
    client: Any,
    watchdog_ctx: dict[str, Any],
    log: logging.Logger,
    *,
    strict_io: bool = False,
) -> dict[str, Any]:
    """Execute one risk & drift audit cycle and persist agent4_watchdog_status.json."""
    ha_mod = _get_ha_mod()
    if client is not None and not isinstance(client, ha_mod.PassiveStandbyClient):
        client = ha_mod.PassiveStandbyClient(client)
    now_utc = datetime.now(timezone.utc)
    now_ts = time.time()

    telemetry = check_trader_telemetry()
    stale_alerts: list[dict[str, Any]] = []

    last_tick_utc = telemetry.get("last_tick_utc") if telemetry else None
    telemetry_dt = _parse_iso_utc(last_tick_utc)
    telemetry_age_sec: float | None = None
    if telemetry_dt is not None:
        telemetry_age_sec = max(0.0, (now_utc - telemetry_dt).total_seconds())

    trader_status_raw = telemetry.get("status") if telemetry else None
    trader_alive = bool(
        telemetry
        and trader_status_raw == "LIVE_ACTIVE"
        and telemetry_age_sec is not None
        and telemetry_age_sec <= MAX_TELEMETRY_AGE_SEC
    )

    if not telemetry:
        stale_alerts.append({"source": "agent1_telemetry", "reason": "unreachable"})
    elif telemetry_age_sec is None or telemetry_age_sec > MAX_TELEMETRY_AGE_SEC:
        stale_alerts.append({
            "source": "agent1_telemetry",
            "reason": "stale",
            "age_sec": round(telemetry_age_sec, 2) if telemetry_age_sec is not None else None,
            "threshold_sec": MAX_TELEMETRY_AGE_SEC,
        })

    scout_alert = check_scout_freshness(now_utc)
    if scout_alert is not None:
        stale_alerts.append(scout_alert)

    if trader_alive:
        agent1_status = "ONLINE"
    elif trader_status_raw == "HALTED":
        agent1_status = "HALTED"
    else:
        agent1_status = "OFFLINE"

    exchange_reachable = False
    open_orders: list[dict[str, Any]] = []
    best_bid = Decimal("0")
    best_ask = Decimal("0")
    mid_price = Decimal("0")

    if client is not None:
        try:
            open_orders = list(client.get_open_orders())
            best_bid, best_ask, _, _ = client.get_book(depth=5)
            mid_price = (best_bid + best_ask) / Decimal("2")
            exchange_reachable = True
        except Exception as exc:
            log.error("Direct exchange query failed: %s", exc)
            exchange_reachable = False

    if not exchange_reachable and telemetry:
        open_orders = list(telemetry.get("active_orders", []))
        last_book = telemetry.get("last_book", {}) or {}
        best_bid = Decimal(str(last_book.get("best_bid", "0") or "0"))
        best_ask = Decimal(str(last_book.get("best_ask", "0") or "0"))
        mid_price = Decimal(str(last_book.get("mid_price", "0") or "0"))

    # Query private/user-balance on startup and every 60s.
    last_equity_ts = float(watchdog_ctx.get("last_equity_check_ts", 0.0))
    if client is not None and (last_equity_ts == 0.0 or (now_ts - last_equity_ts) >= EQUITY_POLL_INTERVAL_SEC):
        try:
            balances = client.get_balances()
            usdt_total = Decimal(str(balances.get("USDT", {}).get("total", "0")))
            usd_total = Decimal(str(balances.get("USD", {}).get("total", "0")))
            cro_total = Decimal(str(balances.get("CRO", {}).get("total", "0")))
            total_equity = usdt_total + usd_total + (cro_total * mid_price)

            if watchdog_ctx.get("baseline_equity_usdt") is None:
                watchdog_ctx["baseline_equity_usdt"] = total_equity

            baseline = Decimal(str(watchdog_ctx["baseline_equity_usdt"]))
            drawdown = max(Decimal("0"), baseline - total_equity)
            watchdog_ctx["last_equity_check_ts"] = now_ts
            watchdog_ctx["equity_drawdown_usdt"] = drawdown
            watchdog_ctx["equity_snapshot"] = {
                "as_of_utc": now_utc.isoformat(),
                "usdt_total": f"{usdt_total:.6f}",
                "cro_total": str(cro_total),
                "total_equity_usdt": f"{total_equity:.4f}",
                "baseline_equity_usdt": f"{baseline:.4f}",
                "equity_drawdown_usdt": f"{drawdown:.4f}",
            }
        except Exception as exc:
            log.error("Direct exchange balance audit failed: %s", exc)

    equity_drawdown_usdt = Decimal(str(watchdog_ctx.get("equity_drawdown_usdt", "0")))
    equity_snapshot = watchdog_ctx.get("equity_snapshot")

    drift_alerts: list[dict[str, Any]] = []
    integrity_issues: list[dict[str, Any]] = []
    active_orders_summary: list[dict[str, Any]] = []

    for o in open_orders:
        oid = str(o.get("order_id", ""))
        side = str(o.get("side", ""))
        order_price = Decimal(str(o.get("limit_price") or o.get("price") or "0"))
        qty_str = str(o.get("quantity", "0"))
        exec_inst = list(o.get("exec_inst") or [])
        tif = o.get("time_in_force")
        cum_fee = Decimal(str(o.get("cumulative_fee", "0") or "0"))

        if mid_price > 0 and order_price > 0:
            if side == "BUY":
                pct_below_mid = (mid_price - order_price) / mid_price
                if (best_ask > 0 and order_price >= best_ask) or pct_below_mid > MAX_BUY_DIP_DRIFT_PCT:
                    drift_alerts.append({
                        "order_id": oid,
                        "side": side,
                        "order_price": float(order_price),
                        "mid_price": float(mid_price),
                        "pct_from_mid": round(float(pct_below_mid * Decimal("100")), 3),
                        "reason": "crossing_best_ask" if (best_ask > 0 and order_price >= best_ask) else "below_8pct_dip_band",
                    })
            elif side == "SELL":
                pct_above_mid = (order_price - mid_price) / mid_price
                if (best_bid > 0 and order_price <= best_bid) or pct_above_mid > MAX_SELL_TP_DRIFT_PCT:
                    drift_alerts.append({
                        "order_id": oid,
                        "side": side,
                        "order_price": float(order_price),
                        "mid_price": float(mid_price),
                        "pct_from_mid": round(float(pct_above_mid * Decimal("100")), 3),
                        "reason": "crossing_best_bid" if (best_bid > 0 and order_price <= best_bid) else "above_10pct_tp_band",
                    })

        if exchange_reachable:
            if "POST_ONLY" not in exec_inst:
                integrity_issues.append({
                    "order_id": oid,
                    "side": side,
                    "issue": f"missing_POST_ONLY (exec_inst={exec_inst})",
                })
            if tif and tif != "GOOD_TILL_CANCEL":
                integrity_issues.append({
                    "order_id": oid,
                    "side": side,
                    "issue": f"unexpected_time_in_force ({tif})",
                })
            if cum_fee != Decimal("0"):
                integrity_issues.append({
                    "order_id": oid,
                    "side": side,
                    "issue": f"non_zero_cumulative_fee ({cum_fee})",
                })

        active_orders_summary.append({
            "order_id": oid,
            "side": side,
            "price": f"{order_price:.5f}",
            "quantity": qty_str,
            "status": str(o.get("status", "ACTIVE")),
            "post_only": "POST_ONLY" in exec_inst,
        })

    daily_pnl = Decimal(str((telemetry or {}).get("daily_realized_pnl_usdt", "0.0") or "0.0"))
    kill_switch_tripped = (
        daily_pnl <= -MAX_ALLOWABLE_DRAWDOWN_USDT
        or equity_drawdown_usdt >= MAX_ALLOWABLE_DRAWDOWN_USDT
    )

    if kill_switch_tripped or drift_alerts or integrity_issues or not exchange_reachable:
        watchdog_health = "CRITICAL"
    elif exchange_reachable and trader_alive and not stale_alerts:
        watchdog_health = "HEALTHY"
    else:
        watchdog_health = "DEGRADED"

    watchdog_state: dict[str, Any] = {
        "timestamp_utc": now_utc.isoformat(),
        "watchdog_status": "ONLINE",
        "watchdog_health": watchdog_health,
        "credential_role": "READ_ONLY_ENFORCED",
        "agent1_ha_role": (telemetry or {}).get("ha_role") or ((telemetry or {}).get("ha_health") or {}).get("role"),
        "agent1_unresolved_intent_count": ((telemetry or {}).get("ha_health") or {}).get("unresolved_intent_count", 0),
        "agent1_execution_engine_online": trader_alive,
        "agent1_status": agent1_status,
        "agent1_last_tick": last_tick_utc,
        "agent1_telemetry_age_sec": round(telemetry_age_sec, 2) if telemetry_age_sec is not None else None,
        "current_mid_price": float(mid_price),
        "active_order_count": len(open_orders),
        "excessive_drift_orders": drift_alerts,
        "order_integrity_issues": integrity_issues,
        "stale_data_alerts": stale_alerts,
        "circuit_breaker_status": {
            "daily_realized_pnl_usdt": float(daily_pnl),
            "equity_drawdown_usdt": float(equity_drawdown_usdt),
            "max_allowable_drawdown_usdt": float(MAX_ALLOWABLE_DRAWDOWN_USDT),
            "kill_switch_tripped": kill_switch_tripped,
        },
        "equity_snapshot": equity_snapshot,
        "active_orders_summary": active_orders_summary,
        "status_write_ok": True,
    }

    try:
        if OUTPUT_STATUS_PATH.exists() and OUTPUT_STATUS_PATH.is_dir():
            raise IsADirectoryError(f"OUTPUT_STATUS_PATH points to a directory: {OUTPUT_STATUS_PATH}")
        OUTPUT_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUTPUT_STATUS_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(watchdog_state, indent=2), encoding="utf-8")
        os.replace(tmp, OUTPUT_STATUS_PATH)
    except Exception as exc:
        watchdog_state["status_write_ok"] = False
        watchdog_state["watchdog_health"] = "CRITICAL"
        watchdog_state["stale_data_alerts"].append({
            "source": "watchdog_status_write",
            "reason": f"write_failed: {exc}",
        })
        log.error("WATCHDOG_STATUS_WRITE_FAILED (%s): %s", OUTPUT_STATUS_PATH, exc)
        if strict_io:
            raise
    return watchdog_state


def _handle_signal(_signum: int, _frame: Any) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def main() -> int:
    global _STOP_REQUESTED
    _STOP_REQUESTED = False
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    SAVED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = configure_logging()
    log.info("Agent 4 (Risk & Drift Watchdog) started...")

    client = None
    try:
        client = load_client()
    except Exception as exc:
        log.warning("Watchdog warning: DPAPI credentials offline (%s)", exc)

    watchdog_ctx: dict[str, Any] = {
        "last_equity_check_ts": 0.0,
        "baseline_equity_usdt": None,
        "equity_drawdown_usdt": Decimal("0"),
        "equity_snapshot": None,
    }

    while not _STOP_REQUESTED:
        try:
            run_watchdog_cycle(client, watchdog_ctx, log)
        except Exception as exc:
            log.error("Watchdog cycle error: %s", exc)
        steps = max(1, int(round(POLL_INTERVAL_SEC / 0.5)))
        for _ in range(steps):
            if _STOP_REQUESTED:
                break
            time.sleep(0.5)

    log.info("Agent 4 (Risk & Drift Watchdog) exiting cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
