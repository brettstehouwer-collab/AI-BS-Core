from decimal import Decimal
from pathlib import Path

file_path = Path(r"C:\AI-BS\scratch\live_cro_usdt_trader.py")
text = file_path.read_text(encoding="utf-8")

# 1. Add Stale Order Repositioning Constants
constants_target = """DAILY_LOSS_CUTOFF_USDT = Decimal("1.00")
POLL_INTERVAL_SEC = 0.8"""

constants_replacement = """DAILY_LOSS_CUTOFF_USDT = Decimal("1.00")
POLL_INTERVAL_SEC = 0.8
MAX_DRIFT_TICKS = 25  # Reposition order if it drifts more than 25 ticks (0.00025 USDT) away from best orderbook
MAX_STALE_SECONDS = 180  # Reposition if order rests unmoved for 3 minutes while price moved away"""

if constants_target not in text:
    raise ValueError("Constants target not found")
text = text.replace(constants_target, constants_replacement, 1)

# 2. Add Stale Order Inspection and Auto-Repositioning in maintain_bracket
maintain_target = """    open_orders = client.get_open_orders()
    ok_to_trade = enforce_risk_controls(client, state, best_bid, open_orders, log)

    if ok_to_trade:
        open_orders = client.get_open_orders()
        has_open_buy = any(o.get("side") == "BUY" for o in open_orders)
        has_open_sell = any(o.get("side") == "SELL" for o in open_orders)"""

maintain_replacement = """    open_orders = client.get_open_orders()
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
        has_open_sell = any(o.get("side") == "SELL" for o in open_orders)"""

if maintain_target not in text:
    raise ValueError("Maintain target not found")
text = text.replace(maintain_target, maintain_replacement, 1)

# 3. Add placed_ts when placing orders
buy_tracked_target = """                state["tracked_orders"][oid] = {
                    "side": "BUY",
                    "qty_cro": buy_qty,
                    "price": format_price(buy_price),
                    "client_oid": client_oid,
                }"""

buy_tracked_replacement = """                state["tracked_orders"][oid] = {
                    "side": "BUY",
                    "qty_cro": buy_qty,
                    "price": format_price(buy_price),
                    "client_oid": client_oid,
                    "placed_ts": time.time(),
                }"""

if buy_tracked_target not in text:
    raise ValueError("Buy tracked target not found")
text = text.replace(buy_tracked_target, buy_tracked_replacement, 1)

sell_tracked_target = """                state["tracked_orders"][oid] = {
                    "side": "SELL",
                    "qty_cro": sell_qty,
                    "price": format_price(sell_price),
                    "client_oid": client_oid,
                }"""

sell_tracked_replacement = """                state["tracked_orders"][oid] = {
                    "side": "SELL",
                    "qty_cro": sell_qty,
                    "price": format_price(sell_price),
                    "client_oid": client_oid,
                    "placed_ts": time.time(),
                }"""

if sell_tracked_target not in text:
    raise ValueError("Sell tracked target not found")
text = text.replace(sell_tracked_target, sell_tracked_replacement, 1)

# 4. Enrich state with Total Portfolio Valuation tracking
balances_target = """    final_balances = client.get_balances()
    final_orders = client.get_open_orders()
    state["balances"] = {
        ccy: {k: str(v) for k, v in vals.items()}
        for ccy, vals in final_balances.items()
        if ccy in ("CRO", "USDT", "USD")
    }"""

balances_replacement = """    final_balances = client.get_balances()
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
    }"""

if balances_target not in text:
    raise ValueError("Balances target not found")
text = text.replace(balances_target, balances_replacement, 1)

file_path.write_text(text, encoding="utf-8")
print("live_cro_usdt_trader.py upgraded successfully with Autonomous Stale Repositioning & Portfolio Accounting!")

