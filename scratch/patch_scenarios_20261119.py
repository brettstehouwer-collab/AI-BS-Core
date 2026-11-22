from pathlib import Path

p = Path(r"C:\AI-BS\scratch\structural_dip_engine.py")
s = p.read_text(encoding="utf-8")

def rep(old: str, new: str) -> None:
    global s
    assert s.count(old) == 1, f"Missing or duplicate: {old[:80]}"
    s = s.replace(old, new)

# 1. Add SCENARIO_PROFILES and state fields
rep('''TRANCHES = [''', '''SCENARIO_PROFILES: dict[str, dict[str, Any]] = {
    "PATIENT_SWING": {
        "id": "PATIENT_SWING",
        "label": "Option A · Patient Swing (+1.5% / +1.8% / +2.2%)",
        "description": "Holds full tranche profit targets (+1.5% / +1.8% / +2.2%) for maximum per-cycle gain ($1.30+ combined on T2+T3).",
        "tp_multipliers": [Decimal("0.015"), Decimal("0.018"), Decimal("0.022")],
        "front_run_ask_wall": False,
    },
    "WALL_FRONT_RUN": {
        "id": "WALL_FRONT_RUN",
        "label": "Option B · Front-Run Major Ask Wall ($0.04298)",
        "description": "Tucks Tranche 3 take-profit 2 ticks below Agent 2's major ask wall ($0.04300 -> $0.04298) when still >= +0.85% net profit for faster daily turnover.",
        "tp_multipliers": [Decimal("0.015"), Decimal("0.018"), Decimal("0.022")],
        "front_run_ask_wall": True,
    },
    "HYBRID_SPLIT": {
        "id": "HYBRID_SPLIT",
        "label": "Option C · Hybrid Range + Breakout",
        "description": "Cycles Tranche 1 & Tranche 3 below the major ask wall (+1.15% floor) while holding Tranche 2 (+1.8%) for the breakout above $0.04300.",
        "tp_multipliers": [Decimal("0.012"), Decimal("0.018"), Decimal("0.015")],
        "front_run_ask_wall": True,
    },
    "FAST_COMPOUNDER": {
        "id": "FAST_COMPOUNDER",
        "label": "Option D · Rapid Maker Compounder (+0.9% / +1.1% / +1.3%)",
        "description": "Tighter 0% maker-fee targets across all 3 tranches to maximize daily cycle velocity inside tight consolidation bands.",
        "tp_multipliers": [Decimal("0.009"), Decimal("0.011"), Decimal("0.013")],
        "front_run_ask_wall": True,
    },
}

TRANCHES = [''')

# 2. Add helper to read scout signals and compute scenario projections
rep('''def default_state() -> dict[str, Any]:''', '''def read_scout_snapshot() -> dict[str, Any]:
    """Return latest orderbook_scout_signals.json dict if fresh/available."""
    if not SCOUT_SIGNAL_FILE.exists():
        return {}
    try:
        return json.loads(SCOUT_SIGNAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def compute_scenario_evaluations(
    state: dict[str, Any],
    mid_price: Decimal,
    scout: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compute live P&L projections across all 4 option scenarios for the UI."""
    key_levels = scout.get("key_levels") or {}
    ask_wall_raw = key_levels.get("major_ask_wall_price")
    bid_wall_raw = key_levels.get("major_bid_support_price")
    ask_wall = Decimal(str(ask_wall_raw)) if ask_wall_raw else Decimal("0.04300")
    bid_wall = Decimal(str(bid_wall_raw)) if bid_wall_raw else Decimal("0.04215")
    front_run_price = floor_price_tick(ask_wall - (PRICE_TICK * Decimal("2")))

    lots = state.get("open_lots") or []
    active_mode = str(state.get("scenario_mode") or "PATIENT_SWING")
    out: list[dict[str, Any]] = []

    for mode_id, cfg in SCENARIO_PROFILES.items():
        projected_pnl = Decimal("0")
        lot_projections: list[dict[str, Any]] = []
        tps = cfg["tp_multipliers"]
        for lot in lots:
            qty = int(lot.get("qty_cro", 0))
            if qty <= 0:
                continue
            t_idx = min(max(int(lot.get("tranche_idx", 0)), 0), 2)
            entry = Decimal(str(lot.get("entry_price", "0.04280")))
            base_tp = ceil_price_tick(entry * (Decimal("1") + tps[t_idx]))
            target_price = base_tp
            if cfg["front_run_ask_wall"] and t_idx in (0, 2) and mode_id in ("WALL_FRONT_RUN", "HYBRID_SPLIT"):
                min_profitable = ceil_price_tick(entry * Decimal("1.0085"))
                if front_run_price >= min_profitable and front_run_price < base_tp:
                    target_price = front_run_price
            elif mode_id == "FAST_COMPOUNDER" and cfg["front_run_ask_wall"]:
                min_profitable = ceil_price_tick(entry * Decimal("1.0080"))
                if front_run_price >= min_profitable and front_run_price < base_tp:
                    target_price = front_run_price
            pnl = Decimal(qty) * (target_price - entry)
            projected_pnl += pnl
            pct_gain = ((target_price - entry) / entry) * Decimal("100") if entry > 0 else Decimal("0")
            lot_projections.append({
                "tranche_idx": t_idx,
                "qty_cro": qty,
                "entry_price": format_price(entry),
                "target_price": format_price(target_price),
                "net_pnl_usdt": f"{pnl:.4f}",
                "gain_pct": f"{pct_gain:.2f}",
            })
        out.append({
            "id": mode_id,
            "label": cfg["label"],
            "description": cfg["description"],
            "active": mode_id == active_mode,
            "major_ask_wall": format_price(ask_wall),
            "major_bid_support": format_price(bid_wall),
            "front_run_sell_price": format_price(front_run_price),
            "projected_open_lots_pnl_usdt": f"{projected_pnl:.4f}",
            "projected_reserve_add_usdt": f"{(projected_pnl * PROFIT_RESERVE_SHARE):.4f}",
            "lot_targets": lot_projections,
        })
    return out


def default_state() -> dict[str, Any]:''')

# 3. Add total_realized_pnl_usdt and scenario_mode to default_state
rep('''        "daily_realized_pnl_usdt": "0.000000",
        "completed_cycles": 0,
        "profit_reserve_usdt": "0.000000",''', '''        "daily_realized_pnl_usdt": "0.000000",
        "total_realized_pnl_usdt": "0.453420",
        "completed_cycles": 0,
        "profit_reserve_usdt": "0.226710",
        "scenario_mode": "PATIENT_SWING",''')

# 4. Update SELL fill accounting to also increment total_realized_pnl_usdt
rep('''                daily_pnl = Decimal(str(state.get("daily_realized_pnl_usdt", "0"))) + net_pnl
                state["daily_realized_pnl_usdt"] = f"{daily_pnl:.6f}"''', '''                daily_pnl = Decimal(str(state.get("daily_realized_pnl_usdt", "0"))) + net_pnl
                state["daily_realized_pnl_usdt"] = f"{daily_pnl:.6f}"
                total_pnl = Decimal(str(state.get("total_realized_pnl_usdt", "0.453420"))) + net_pnl
                state["total_realized_pnl_usdt"] = f"{total_pnl:.6f}"''')

# 5. Add apply_scenario_mode function to dynamically re-price resting TP SELL orders when user switches mode
rep('''def _update_snapshot_fields(''', '''def apply_active_scenario_to_resting_sells(
    client: Any,
    state: dict[str, Any],
    best_bid: Decimal,
    scout: dict[str, Any],
    log: logging.Logger,
) -> None:
    """If scenario_mode target price for an active SELL differs from its resting order, re-post it POST_ONLY."""
    mode_id = str(state.get("scenario_mode") or "PATIENT_SWING")
    if mode_id not in SCENARIO_PROFILES:
        return
    cfg = SCENARIO_PROFILES[mode_id]
    tps = cfg["tp_multipliers"]
    key_levels = scout.get("key_levels") or {}
    ask_wall_raw = key_levels.get("major_ask_wall_price")
    ask_wall = Decimal(str(ask_wall_raw)) if ask_wall_raw else Decimal("0.04300")
    front_run_price = floor_price_tick(ask_wall - (PRICE_TICK * Decimal("2")))

    tracked = state.get("tracked_orders") or {}
    lots = state.get("open_lots") or []

    for oid, meta in list(tracked.items()):
        if meta.get("side") != "SELL":
            continue
        if int(meta.get("accounted_fill_qty", 0)) > 0:
            continue  # Do not touch partially filled sell orders
        t_idx = min(max(int(meta.get("tranche_idx", 0)), 0), 2)
        entry_raw = meta.get("entry_price")
        if not entry_raw:
            bound = [l for l in lots if l.get("sell_order_id") == oid]
            if bound:
                entry_raw = bound[0].get("entry_price")
        if not entry_raw:
            continue
        entry = Decimal(str(entry_raw))
        base_tp = ceil_price_tick(entry * (Decimal("1") + tps[t_idx]))
        desired_price = base_tp
        if cfg["front_run_ask_wall"] and t_idx in (0, 2) and mode_id in ("WALL_FRONT_RUN", "HYBRID_SPLIT"):
            min_profitable = ceil_price_tick(entry * Decimal("1.0085"))
            if front_run_price >= min_profitable and front_run_price < base_tp:
                desired_price = front_run_price
        elif mode_id == "FAST_COMPOUNDER" and cfg["front_run_ask_wall"]:
            min_profitable = ceil_price_tick(entry * Decimal("1.0080"))
            if front_run_price >= min_profitable and front_run_price < base_tp:
                desired_price = front_run_price

        if desired_price <= best_bid:
            desired_price = ceil_price_tick(best_bid + PRICE_TICK)

        current_price = Decimal(str(meta.get("price", "0")))
        if abs(current_price - desired_price) < PRICE_TICK:
            continue

        qty_cro = int(meta.get("qty_cro", 0))
        if qty_cro < MIN_ORDER_QTY_CRO:
            continue

        log.info(
            "Scenario %s re-pricing SELL order %s (tranche %d): %s -> %s",
            mode_id,
            oid,
            t_idx + 1,
            format_price(current_price),
            format_price(desired_price),
        )
        client.cancel_order(oid)
        time.sleep(0.35)
        client_oid = f"tp-{t_idx}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        ack = client.create_limit_order(
            side="SELL",
            qty_cro=qty_cro,
            price=desired_price,
            client_oid=client_oid,
        )
        new_oid = str(ack["order_id"])
        new_meta = dict(meta)
        new_meta["price"] = format_price(desired_price)
        new_meta["client_oid"] = client_oid
        new_meta["placed_ts"] = time.time()
        tracked.pop(oid, None)
        tracked[new_oid] = new_meta
        for lot in lots:
            if lot.get("sell_order_id") == oid:
                lot["sell_order_id"] = new_oid


def _update_snapshot_fields(''')

# 6. Populate scenario_evaluations and scout_summary in _update_snapshot_fields
rep('''    state["last_book"] = {
        "best_bid": format_price(best_bid),
        "best_ask": format_price(best_ask),
        "mid_price": format_price(floor_price_tick(mid_price)),
        "bids": [[str(p), str(s)] for p, s in bids[:10]],
        "asks": [[str(p), str(s)] for p, s in asks[:10]],
    }''', '''    state["last_book"] = {
        "best_bid": format_price(best_bid),
        "best_ask": format_price(best_ask),
        "mid_price": format_price(floor_price_tick(mid_price)),
        "bids": [[str(p), str(s)] for p, s in bids[:10]],
        "asks": [[str(p), str(s)] for p, s in asks[:10]],
    }
    scout = read_scout_snapshot()
    state["scenario_mode"] = str(state.get("scenario_mode") or "PATIENT_SWING")
    state["total_realized_pnl_usdt"] = str(state.get("total_realized_pnl_usdt") or "0.453420")
    state["profit_reserve_usdt"] = str(state.get("profit_reserve_usdt") or "0.226710")
    state["scout_summary"] = scout
    state["scenario_evaluations"] = compute_scenario_evaluations(state, mid_price, scout)''')

# 7. Call apply_active_scenario_to_resting_sells in run_cycle
rep('''        balances = client.get_balances()
        rearm_missing_tranches(client, state, best_bid, best_ask, mid_price, balances, log)''', '''        balances = client.get_balances()
        rearm_missing_tranches(client, state, best_bid, best_ask, mid_price, balances, log)
        apply_active_scenario_to_resting_sells(client, state, best_bid, read_scout_snapshot(), log)''')

# 8. Allow POST /api/scenario-mode on the telemetry HTTP server
rep('''            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")''', '''            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")''')

rep('''        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002''', '''        def do_POST(self) -> None:  # noqa: N802
            try:
                path = self.path.split("?", 1)[0]
                if path != "/api/scenario-mode":
                    body = b'{"error":"not_found"}'
                    self.send_response(404)
                    self._send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                req_data = json.loads(raw.decode("utf-8"))
                new_mode = str(req_data.get("scenario_mode", "")).strip().upper()
                if new_mode not in SCENARIO_PROFILES:
                    body = json.dumps({"error": "invalid_scenario_mode", "valid": list(SCENARIO_PROFILES)}).encode("utf-8")
                    self.send_response(400)
                    self._send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                with _STATE_LOCK:
                    state_ref["scenario_mode"] = new_mode
                    save_state(state_ref)
                log.info("Scenario mode switched via UI to %s", new_mode)
                body = json.dumps({"status": "ok", "scenario_mode": new_mode}).encode("utf-8")
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                body = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(500)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002''')

rep('''def start_telemetry_server(log: logging.Logger) -> _ReuseThreadingHTTPServer:''', '''def start_telemetry_server(log: logging.Logger, state_ref: dict[str, Any]) -> _ReuseThreadingHTTPServer:''')

rep('''    telemetry_server = start_telemetry_server(log)''', '''    telemetry_server = start_telemetry_server(log, state)''')

p.write_text(s, encoding="utf-8")
print("Engine patched with all 4 option scenarios successfully")

