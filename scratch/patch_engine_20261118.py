from pathlib import Path

p = Path(r"C:\AI-BS\scratch\structural_dip_engine.py")
s = p.read_text(encoding="utf-8")

def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)

# 1) constants + helpers
rep('''_STATE_LOCK = threading.Lock()
_LEDGER_LOCK''', '''PROFIT_RESERVE_SHARE = Decimal("0.50")  # share of each positive realized sell PnL banked, never traded
AUTH_ALERT_AFTER_SEC = 300.0
ALERT_FILE = SAVED_DATA_DIR / "engine_alert.json"
ENV_FILE = Path(r"C:\\AI-BS\\.env")
_AUTH_FAIL_SINCE: float | None = None
_AUTH_ALERTED = False

_STATE_LOCK = threading.Lock()
_LEDGER_LOCK''')

rep('''def default_state() -> dict[str, Any]:''', '''def _reserve(state: dict[str, Any]) -> Decimal:
    return Decimal(str(state.get("profit_reserve_usdt", "0")))


def send_alert(message: str, log: logging.Logger) -> None:
    """Write engine_alert.json and post to the user's own Discord webhook (best effort)."""
    try:
        ALERT_FILE.write_text(json.dumps({"utc": _utc_now_str(), "message": message}), encoding="utf-8")
    except Exception as exc:
        log.warning("alert file write failed: %s", exc)
    try:
        import urllib.request
        url = ""
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("DISCORD_WEBHOOK_URL="):
                url = line.split("=", 1)[1].strip().strip('"')
        if url:
            req = urllib.request.Request(
                url,
                data=json.dumps({"content": "[AI-BS dip engine] " + message}).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "AI-BS-engine"},
            )
            urllib.request.urlopen(req, timeout=8).read()
    except Exception as exc:
        log.warning("discord alert failed: %s", exc)


def default_state() -> dict[str, Any]:''')

rep('''        "completed_cycles": 0,
        "open_long_entry_price": None,''', '''        "completed_cycles": 0,
        "profit_reserve_usdt": "0.000000",
        "open_long_entry_price": None,''')

# 2) profit reserve on positive sell pnl
rep('''                state["daily_realized_pnl_usdt"] = f"{daily_pnl:.6f}"
                if closed or delta_qty > 0:''', '''                state["daily_realized_pnl_usdt"] = f"{daily_pnl:.6f}"
                if net_pnl > 0:
                    banked = net_pnl * PROFIT_RESERVE_SHARE
                    state["profit_reserve_usdt"] = f"{_reserve(state) + banked:.6f}"
                    log.info("Banked %s USDT to protected reserve (total %s)", f"{banked:.6f}", state["profit_reserve_usdt"])
                if closed or delta_qty > 0:''')

# 3) full-grid deploy respects reserve
rep('''    free_usdt = balances.get("USDT", {}).get("free", Decimal("0"))
    if free_cro >= Decimal(MIN_ORDER_QTY_CRO):
        return
    if free_usdt < Decimal("30.00"):''', '''    free_usdt = balances.get("USDT", {}).get("free", Decimal("0")) - _reserve(state)
    if free_cro >= Decimal(MIN_ORDER_QTY_CRO):
        return
    if free_usdt < Decimal("30.00"):''')

# 4) re-arm function
rep('''def _update_snapshot_fields(''', '''def rearm_missing_tranches(
    client: Any,
    state: dict[str, Any],
    best_bid: Decimal,
    best_ask: Decimal,
    mid_price: Decimal,
    balances: dict[str, dict[str, Decimal]],
    log: logging.Logger,
) -> None:
    """Re-arm one uncovered tranche per cycle (no resting BUY, no open lot), keeping the profit reserve untouched."""
    covered = {int(m.get("tranche_idx", -1)) for m in state.get("tracked_orders", {}).values() if m.get("side") == "BUY"}
    covered |= {int(l.get("tranche_idx", -1)) for l in state.get("open_lots", [])}
    available = balances.get("USDT", {}).get("free", Decimal("0")) - _reserve(state)
    safe_ceiling = None
    for t in TRANCHES:
        if t["idx"] in covered:
            continue
        budget = min(t["budget_usdt"], available)
        if budget < Decimal("20.00"):
            continue
        if safe_ceiling is None:
            safe_ceiling = read_safe_buy_ceiling(best_bid, best_ask, log)
        buy_price = floor_price_tick(min(mid_price * (Decimal("1") - t["dip_pct"]), safe_ceiling))
        if buy_price >= best_ask:
            buy_price = floor_price_tick(best_ask - PRICE_TICK)
        if buy_price <= Decimal("0"):
            continue
        buy_qty = int((budget / buy_price).to_integral_value(rounding=ROUND_DOWN))
        notional = Decimal(buy_qty) * buy_price
        if buy_qty < MIN_ORDER_QTY_CRO or notional < MIN_ORDER_NOTIONAL_USDT or notional > available:
            continue
        client_oid = f"dip-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        ack = client.create_limit_order(side="BUY", qty_cro=buy_qty, price=buy_price, client_oid=client_oid)
        oid = str(ack["order_id"])
        state["tracked_orders"][oid] = {
            "side": "BUY",
            "qty_cro": buy_qty,
            "price": format_price(buy_price),
            "client_oid": client_oid,
            "placed_ts": time.time(),
            "tranche_idx": t["idx"],
            "tranche_name": t["name"],
            "target_profit_pct": str(t["target_profit_pct"]),
            "accounted_fill_qty": 0,
            "accounted_fee_usdt": "0.000000",
        }
        log.info("Re-armed %s: order_id=%s BUY %d CRO @ %s (notional=%s)", t["name"], oid, buy_qty, format_price(buy_price), f"{notional:.5f}")
        return


def _update_snapshot_fields(''')

# 5) call in run_cycle
rep('''            open_orders=open_orders,
            log=log,
        )

    final_orders''', '''            open_orders=open_orders,
            log=log,
        )
        balances = client.get_balances()
        rearm_missing_tranches(client, state, best_bid, best_ask, mid_price, balances, log)

    final_orders''')

# 6) outage alert in main loop
rep('''                run_cycle(client, state, log)
            except Exception as exc:
                log.error("Engine iteration error (retaining state, retrying next tick): %s", exc)''', '''                run_cycle(client, state, log)
                global _AUTH_FAIL_SINCE, _AUTH_ALERTED
                if _AUTH_ALERTED:
                    send_alert("Exchange API auth recovered; engine trading again.", log)
                _AUTH_FAIL_SINCE, _AUTH_ALERTED = None, False
            except Exception as exc:
                log.error("Engine iteration error (retaining state, retrying next tick): %s", exc)
                if "40101" in str(exc):
                    now_ts = time.time()
                    if _AUTH_FAIL_SINCE is None:
                        _AUTH_FAIL_SINCE = now_ts
                    elif not _AUTH_ALERTED and now_ts - _AUTH_FAIL_SINCE >= AUTH_ALERT_AFTER_SEC:
                        _AUTH_ALERTED = True
                        send_alert("Crypto.com API 40101 auth failure for 5+ min. Check IP whitelist/key. Orders are NOT being managed.", log)''')

p.write_text(s, encoding="utf-8")
print("patched")

