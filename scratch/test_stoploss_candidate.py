"""Comprehensive offline edge-case tests for structural_dip_engine_stoploss_candidate.py.
Covers:
1. Outgoing payload omits POST_ONLY for protective exits, retains for ordinary TPs.
2. Intervening partial fill (357 CRO) during cancel -> exits only remaining 357 CRO.
3. Intervening full fill (714 CRO) during cancel -> exits 0 CRO (no duplicate sell).
4. Uncertain/pending cancel outcome -> defers exit, preserves original TP order.
5. Second tick & scenario repricer -> never cancels or reprices active stop-loss order.
"""
from decimal import Decimal
import importlib.util
from pathlib import Path

CANDIDATE_PATH = Path(r"C:\AI-BS\scratch\structural_dip_engine_stoploss_candidate.py")

class EdgeMockClient:
    def __init__(self, best_bid: Decimal, tp_detail_on_cancel: dict):
        self.best_bid = best_bid
        self.tp_detail_on_cancel = tp_detail_on_cancel
        self.canceled = []
        self.created = []

    def get_book(self, depth=10):
        return self.best_bid, self.best_bid + Decimal("0.00002"), [], []

    def get_open_orders(self):
        return []

    def get_balances(self):
        return {"CRO": {"free": Decimal("0"), "total": Decimal("714")}, "USDT": {"free": Decimal("1.27"), "total": Decimal("1.27")}}

    def get_order_detail(self, oid):
        if oid == "tp-0":
            if getattr(self, "_return_empty_on_second_read", False):
                if getattr(self, "_tp0_reads", 0) >= 1:
                    return {}
                self._tp0_reads = getattr(self, "_tp0_reads", 0) + 1
            return self.tp_detail_on_cancel
        return {"order_id": oid, "status": "ACTIVE", "cumulative_quantity": "0"}

    def cancel_order(self, oid):
        self.canceled.append(oid)
        return True

    def create_limit_order(self, **kwargs):
        self.created.append(kwargs)
        if getattr(self, "_drop_ack", False):
            # Exchange accepted order, but response timed out / lost before returning
            self._accepted_open_orders = [{
                "order_id": f"sl-order-{len(self.created)}",
                "side": kwargs["side"],
                "quantity": str(kwargs["qty_cro"]),
                "limit_price": str(kwargs["price"]),
                "client_oid": kwargs["client_oid"],
                "status": "ACTIVE",
                "cumulative_quantity": "0",
            }]
            raise TimeoutError("Simulated lost acknowledgment after exchange acceptance")
        return {"order_id": f"sl-order-{len(self.created)}"}

    def get_open_orders(self):
        return getattr(self, "_accepted_open_orders", [])

def run_edge_tests():
    import shutil, tempfile
    tmp_dir = Path(tempfile.mkdtemp(prefix="sl_test_"))
    spec = importlib.util.spec_from_file_location("cand", str(CANDIDATE_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Redirect ALL write targets to isolated temp directory BEFORE any logger or test runs
    mod.SAVED_DATA_DIR = tmp_dir
    mod.STATE_FILE = tmp_dir / "state.json"
    mod.LOG_FILE = tmp_dir / "engine.log"
    mod.ALERT_FILE = tmp_dir / "alert.json"
    mod.LEDGER_CSV_FILE = tmp_dir / "ledger.csv"
    mod.LEDGER_DB_FILE = tmp_dir / "ledger.db"
    for p_attr in ("STATE_FILE", "LOG_FILE", "ALERT_FILE", "LEDGER_CSV_FILE", "LEDGER_DB_FILE"):
        p_val = str(getattr(mod, p_attr)).lower()
        assert "saved_data" not in p_val, f"Safety abort: {p_attr} still points to live saved_data ({p_val})"
    log = mod.configure_logging()

    # 1. Uncertain/pending cancel outcome -> defers exit, submits 0 orders
    s1 = mod.default_state()
    s1["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 714, "entry_price": "0.04198", "sell_order_id": "tp-0"}]
    s1["tracked_orders"] = {"tp-0": {"side": "SELL", "qty_cro": 714, "price": "0.04236", "accounted_fill_qty": 0}}
    c1 = EdgeMockClient(Decimal("0.03950"), {"order_id": "tp-0", "status": "ACTIVE", "cumulative_quantity": "0"})
    ex1 = mod.enforce_per_lot_stop_loss(c1, s1, Decimal("0.03950"), log)
    assert len(ex1) == 0 and len(c1.created) == 0 and "tp-0" in s1["tracked_orders"]
    print("[PASS] 1. Uncertain cancel outcome: deferred exit, original TP preserved.")

    # 1b. Empty/unknown cancel detail -> defers exit, submits 0 orders, keeps original TP tracked
    c1b = EdgeMockClient(Decimal("0.03950"), {})
    ex1b = mod.enforce_per_lot_stop_loss(c1b, s1, Decimal("0.03950"), log)
    assert len(ex1b) == 0 and len(c1b.created) == 0 and "tp-0" in s1["tracked_orders"]
    print("[PASS] 1b. Empty/unknown cancel detail: deferred exit, 0 replacements, original TP preserved.")

    # 1c. Inconsistent FILLED with cumulative_quantity=0 -> defers exit, 0 replacements
    c1c = EdgeMockClient(Decimal("0.03950"), {"order_id": "tp-0", "status": "FILLED", "cumulative_quantity": "0"})
    ex1c = mod.enforce_per_lot_stop_loss(c1c, s1, Decimal("0.03950"), log)
    assert len(ex1c) == 0 and len(c1c.created) == 0 and "tp-0" in s1["tracked_orders"]
    print("[PASS] 1c. Inconsistent FILLED (cum=0 on 714-CRO): deferred exit, 0 replacements.")

    # 2. Intervening partial fill (357 CRO) during cancel -> books PnL once & exits remaining 357 CRO
    s2 = mod.default_state()
    s2["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 714, "entry_price": "0.04198", "sell_order_id": "tp-0"}]
    s2["tracked_orders"] = {"tp-0": {"side": "SELL", "qty_cro": 714, "price": "0.04236", "entry_price": "0.04198", "accounted_fill_qty": 0, "accounted_fee_usdt": "0.000000"}}
    c2 = EdgeMockClient(Decimal("0.03950"), {"order_id": "tp-0", "status": "CANCELED", "cumulative_quantity": "357", "avg_price": "0.04236", "cumulative_fee": "0.01", "fee_instrument_name": "USDT"})
    c2._return_empty_on_second_read = True
    ex2 = mod.enforce_per_lot_stop_loss(c2, s2, Decimal("0.03950"), log)
    assert len(ex2) == 1 and ex2[0]["qty_cro"] == 357
    assert c2.created[0]["post_only"] is False and c2.created[0]["qty_cro"] == 357
    assert Decimal(str(s2["daily_realized_pnl_usdt"])) == Decimal("0.125660")
    assert s2["recent_fills"][-1]["qty_cro"] == "357"
    # Persist to disk, reload, and re-run reconcile_orders -> PnL must NOT double-book
    import json, tempfile
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
        json.dump(s2, tf)
        tpath = tf.name
    s2_reloaded = json.loads(Path(tpath).read_text())
    mod.reconcile_orders(c2, s2_reloaded, [], log)
    assert Decimal(str(s2_reloaded["daily_realized_pnl_usdt"])) == Decimal("0.125660")
    Path(tpath).unlink(missing_ok=True)
    print("[PASS] 2. Two-read gap closed: booked PnL=$0.125660 & fee=$0.010000 once across disk reload, exited 357 CRO.")

    # 3. Intervening full fill (714 CRO) during cancel -> exits 0 CRO
    s3 = mod.default_state()
    s3["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 714, "entry_price": "0.04198", "sell_order_id": "tp-0"}]
    s3["tracked_orders"] = {"tp-0": {"side": "SELL", "qty_cro": 714, "price": "0.04236", "accounted_fill_qty": 0}}
    c3 = EdgeMockClient(Decimal("0.03950"), {"order_id": "tp-0", "status": "FILLED", "cumulative_quantity": "714"})
    ex3 = mod.enforce_per_lot_stop_loss(c3, s3, Decimal("0.03950"), log)
    assert len(ex3) == 0 and len(c3.created) == 0
    print("[PASS] 3. Intervening 714-CRO full fill: 0 additional sell orders submitted.")

    # 4. Second tick & scenario repricer -> preserves active stop-loss order without cancel/reprice
    c2.canceled.clear()
    c2.created.clear()
    ex4 = mod.enforce_per_lot_stop_loss(c2, s2, Decimal("0.03940"), log)
    mod.apply_active_scenario_to_resting_sells(c2, s2, Decimal("0.03940"), {}, log)
    assert len(ex4) == 0 and len(c2.canceled) == 0 and len(c2.created) == 0
    print("[PASS] 4. Second tick & scenario repricer: active stop-loss untouched (no self-cancel or reprice).")

    # 5. Lost acknowledgment -> restart from disk -> original sell recovered, ZERO duplicate submissions
    s5 = mod.default_state()
    s5["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 357, "entry_price": "0.04198", "sell_order_id": None}]
    c5 = EdgeMockClient(Decimal("0.03950"), {})
    c5._drop_ack = True
    try:
        mod.enforce_per_lot_stop_loss(c5, s5, Decimal("0.03950"), log)
        assert False, "Expected TimeoutError on dropped ack"
    except TimeoutError:
        pass
    assert len(c5.created) == 1 and "l0" in s5["pending_stop_intents"]
    # Simulate restart from disk
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf5:
        json.dump(s5, tf5)
        tpath5 = tf5.name
    s5_reloaded = json.loads(Path(tpath5).read_text())
    c5._drop_ack = False
    mod.enforce_per_lot_stop_loss(c5, s5_reloaded, Decimal("0.03940"), log)
    Path(tpath5).unlink(missing_ok=True)
    assert len(c5.created) == 1, f"Expected exactly 1 total submission across restart, got {len(c5.created)}"
    assert "sl-order-1" in s5_reloaded["tracked_orders"]
    assert s5_reloaded["open_lots"][0]["sell_order_id"] == "sl-order-1"
    assert s5_reloaded["tracked_orders"]["sl-order-1"]["qty_cro"] == 357
    print("[PASS] 5. Lost ack recovery: 1 submission total across disk restart, sl-order-1 (357 CRO) recovered cleanly.")

    # 6. Pre-submission disk persistence: crash mid-request WITHOUT post-timeout save -> recovers from disk
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf6:
        tpath6 = tf6.name
    s6 = mod.default_state()
    s6["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 357, "entry_price": "0.04198", "sell_order_id": None}]
    c6 = EdgeMockClient(Decimal("0.03950"), {})
    c6._drop_ack = True
    def _persist_before_submit(st):
        Path(tpath6).write_text(json.dumps(st), encoding="utf-8")
    try:
        mod.enforce_per_lot_stop_loss(c6, s6, Decimal("0.03950"), log, state_persist_fn=_persist_before_submit)
        assert False, "Expected TimeoutError on dropped ack"
    except TimeoutError:
        pass
    # Notice: NO post-timeout save! Reload only what was persisted BEFORE submission
    s6_reloaded = json.loads(Path(tpath6).read_text(encoding="utf-8"))
    c6._drop_ack = False
    mod.enforce_per_lot_stop_loss(c6, s6_reloaded, Decimal("0.03940"), log, state_persist_fn=_persist_before_submit)
    Path(tpath6).unlink(missing_ok=True)
    assert len(c6.created) == 1, f"Expected 1 submission total, got {len(c6.created)}"
    assert "sl-order-1" in s6_reloaded["tracked_orders"] and s6_reloaded["open_lots"][0]["sell_order_id"] == "sl-order-1"
    print("[PASS] 6. Pre-submission persistence: recovered sl-order-1 without any post-timeout save, 0 duplicates.")

    # 7. Mandatory persistence via run_cycle() using temporary STATE_FILE:
    # 7a. Failed write sends ZERO protective orders
    orig_state_file = mod.STATE_FILE
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf7:
        tpath7 = Path(tf7.name)
    try:
        mod.STATE_FILE = tpath7
        s7 = mod.default_state()
        s7["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 357, "entry_price": "0.04198", "sell_order_id": None}]
        c7 = EdgeMockClient(Decimal("0.03950"), {})
        def _fail_save(st, strict_io=False):
            return False
        orig_save = mod.save_state
        mod.save_state = _fail_save
        mod.run_cycle(c7, s7, log)
        mod.save_state = orig_save
        assert len(c7.created) == 0, f"Expected 0 orders on failed write, got {len(c7.created)}"
        assert "l0" not in s7.get("pending_stop_intents", {})
        print("[PASS] 7a. run_cycle() with failed save_state: sent 0 protective orders.")

        # 7b. Accepted order followed by timeout via run_cycle() -> recovered after disk restart with 1 submission total
        s7b = mod.default_state()
        s7b["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 357, "entry_price": "0.04198", "sell_order_id": None}]
        c7b = EdgeMockClient(Decimal("0.03950"), {})
        c7b._drop_ack = True
        try:
            mod.run_cycle(c7b, s7b, log)
            assert False, "Expected TimeoutError"
        except TimeoutError:
            pass
        s7b_reloaded = json.loads(tpath7.read_text(encoding="utf-8"))
        c7b._drop_ack = False
        mod.run_cycle(c7b, s7b_reloaded, log)
        assert len(c7b.created) == 1, f"Expected 1 submission total across run_cycle restart, got {len(c7b.created)}"
        assert "sl-order-1" in s7b_reloaded["tracked_orders"] and s7b_reloaded["open_lots"][0]["sell_order_id"] == "sl-order-1"
        print("[PASS] 7b. run_cycle() lost ack recovery: 1 submission total across disk restart, sl-order-1 recovered.")
    finally:
        mod.STATE_FILE = orig_state_file
        tpath7.unlink(missing_ok=True)

    # 8. Protective sell partially fills (100 of 357 CRO) BEFORE restart recovery -> books PnL once, 0 duplicates
    s8 = mod.default_state()
    s8["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 357, "entry_price": "0.04198", "sell_order_id": None}]
    c8 = EdgeMockClient(Decimal("0.03950"), {})
    c8._drop_ack = True
    try:
        mod.enforce_per_lot_stop_loss(c8, s8, Decimal("0.03950"), log)
        assert False, "Expected TimeoutError"
    except TimeoutError:
        pass
    # Simulate 100 CRO partial fill on exchange while process was down
    c8._drop_ack = False
    c8._accepted_open_orders[0]["cumulative_quantity"] = "100"
    c8._accepted_open_orders[0]["avg_price"] = "0.03950"
    c8.tp_detail_on_cancel = {"order_id": "sl-order-1", "status": "ACTIVE", "cumulative_quantity": "100", "avg_price": "0.03950", "cumulative_fee": "0.00", "fee_instrument_name": "USDT"}
    # Override get_order_detail for sl-order-1
    orig_god = c8.get_order_detail
    c8.get_order_detail = lambda oid: c8.tp_detail_on_cancel if oid == "sl-order-1" else orig_god(oid)
    s8_reloaded = json.loads(mod.STATE_FILE.read_text(encoding="utf-8"))
    mod.enforce_per_lot_stop_loss(c8, s8_reloaded, Decimal("0.03940"), log)
    assert len(c8.created) == 1
    assert s8_reloaded["tracked_orders"]["sl-order-1"]["accounted_fill_qty"] == 100
    assert Decimal(str(s8_reloaded["daily_realized_pnl_usdt"])) == Decimal("-0.248000")
    assert s8_reloaded["open_lots"][0]["qty_cro"] == 257
    pnl_s8 = s8_reloaded["daily_realized_pnl_usdt"]
    mod.reconcile_orders(c8, s8_reloaded, c8.get_open_orders(), log)
    assert s8_reloaded["daily_realized_pnl_usdt"] == pnl_s8
    print(f"[PASS] 8. Partial fill (100 CRO) before restart recovery: PnL={pnl_s8}, 257 CRO remaining, 1 submission total.")

    # 9. Full fill while down must recover even if the restart bid rebounds above the trigger.
    for case_name, restart_bid in (
        ("below trigger", Decimal("0.03940")),
        ("rebound above trigger", Decimal("0.04250")),
    ):
        s9 = mod.default_state()
        s9["open_lots"] = [{"lot_id": "l0", "tranche_idx": 0, "qty_cro": 357, "entry_price": "0.04198", "sell_order_id": None}]
        c9 = EdgeMockClient(Decimal("0.03950"), {})
        c9._drop_ack = True
        def _mock_private_post(method, params=None):
            if method == "private/create-order":
                res = c9.create_limit_order(side=params["side"], qty_cro=int(params["quantity"]), price=Decimal(params["price"]), client_oid=params["client_oid"], post_only=False)
                return {"result": res}
            if method == "private/get-order-history":
                return {"result": {"data": getattr(c9, "_closed_history", [])}}
            return {"result": {"data": []}}
        c9.private_post = _mock_private_post
        try:
            mod.enforce_per_lot_stop_loss(c9, s9, Decimal("0.03950"), log)
            assert False, "Expected TimeoutError"
        except TimeoutError:
            pass
        # Simulate order disappearing from open orders and appearing FILLED in order history
        c9._drop_ack = False
        c9._closed_history = [{
            "order_id": "sl-order-1",
            "client_oid": c9.created[0]["client_oid"],
            "status": "FILLED",
            "cumulative_quantity": "357",
            "avg_price": "0.03950",
            "cumulative_fee": "0.00",
            "fee_instrument_name": "USDT",
        }]
        c9._accepted_open_orders = []
        s9_reloaded = json.loads(mod.STATE_FILE.read_text(encoding="utf-8"))
        c9.best_bid = restart_bid
        mod.enforce_per_lot_stop_loss(c9, s9_reloaded, restart_bid, log)
        assert len(c9.created) == 1, f"Expected 1 submission total, got {len(c9.created)}"
        assert len(s9_reloaded["open_lots"]) == 0, f"Expected 0 CRO remaining, got {s9_reloaded['open_lots']}"
        assert "l0" not in s9_reloaded.get("pending_stop_intents", {})
        assert Decimal(str(s9_reloaded["daily_realized_pnl_usdt"])) == Decimal("-0.885360")
        # A subsequent cycle must neither duplicate the sell nor book the fill again.
        mod.enforce_per_lot_stop_loss(c9, s9_reloaded, restart_bid, log)
        mod.reconcile_orders(c9, s9_reloaded, c9.get_open_orders(), log)
        assert len(c9.created) == 1, f"Expected 1 submission total, got {len(c9.created)}"
        assert len(s9_reloaded["open_lots"]) == 0
        assert "l0" not in s9_reloaded.get("pending_stop_intents", {})
        assert Decimal(str(s9_reloaded["daily_realized_pnl_usdt"])) == Decimal("-0.885360")
        print(f"[PASS] 9 ({case_name}). Full fill (357 CRO) while down: recovered via order history, 0 CRO remaining, PnL=-0.885360 once.")
    run_review_regressions(mod, log)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("ALL EDGE-CASE ACCEPTANCE TESTS PASSED!")


def _fresh_lot(qty=714, entry="0.04198"):
    return {"lot_id": "l0", "tranche_idx": 0, "qty_cro": qty, "entry_price": entry, "sell_order_id": None}


def run_review_regressions(mod, log):
    """Regression cases for the 2026-11-21 review findings."""
    import time as _time
    persist_ok = lambda st: True  # noqa: E731

    # 10. Empty tracked_orders: the stop exit is recorded in state and never duplicated.
    s10 = mod.default_state()
    s10["tracked_orders"] = {}
    s10["open_lots"] = [_fresh_lot()]
    c10 = EdgeMockClient(Decimal("0.03950"), {})
    mod.enforce_per_lot_stop_loss(c10, s10, Decimal("0.03950"), log, state_persist_fn=persist_ok)
    mod.enforce_per_lot_stop_loss(c10, s10, Decimal("0.03950"), log, state_persist_fn=persist_ok)
    assert len(c10.created) == 1, f"Expected 1 stop exit, got {len(c10.created)}"
    assert s10["tracked_orders"]["sl-order-1"]["is_stop_loss"] is True
    assert s10["open_lots"][0]["sell_order_id"] == "sl-order-1"
    print("[PASS] 10. Empty tracked_orders: stop exit recorded in state, 0 duplicate sells on next cycle.")

    # 11a. Daily-loss halt still enforces protective exits, but places no buys/TPs.
    s11 = mod.default_state()
    s11["utc_day"] = mod._utc_day_str()
    s11["daily_realized_pnl_usdt"] = "-3.10"
    s11["open_lots"] = [_fresh_lot()]
    c11 = EdgeMockClient(Decimal("0.03500"), {})
    mod.run_cycle(c11, s11, log)
    assert s11["halted"] is True and "DAILY_LOSS_CUTOFF" in s11["halt_reason"]
    assert len(c11.created) == 1 and c11.created[0]["side"] == "SELL" and c11.created[0]["post_only"] is False
    print("[PASS] 11a. Daily-loss halt: protective exit still submitted (1 SELL), no buys.")

    # 11b. HA authority barrier (SAFE_HALT) still blocks every mutation, including stops.
    class _BrokenStore:
        def check_integrity(self):
            return False, "synthetic corruption"

    class _Gateway:
        store = _BrokenStore()

    s11b = mod.default_state()
    s11b["open_lots"] = [_fresh_lot()]
    c11b = EdgeMockClient(Decimal("0.03500"), {})
    mod.run_cycle(c11b, s11b, log, gateway=_Gateway(), authority_epoch=1, owner_id="test")
    assert s11b["ha_role"] == "SAFE_HALT" and len(c11b.created) == 0
    print("[PASS] 11b. HA SAFE_HALT barrier: 0 orders, stop-loss mutation blocked as before.")

    # 12. A stale stop exit stranded above a falling bid is cancel-confirmed and replaced once.
    s12 = mod.default_state()
    s12["open_lots"] = [_fresh_lot()]
    c12 = EdgeMockClient(Decimal("0.03980"), {})
    mod.enforce_per_lot_stop_loss(c12, s12, Decimal("0.03980"), log, state_persist_fn=persist_ok)
    s12["tracked_orders"]["sl-order-1"]["placed_ts"] = _time.time() - 30
    c12.get_order_detail = lambda oid: {"order_id": oid, "status": "CANCELED", "cumulative_quantity": "0"}
    c12.best_bid = Decimal("0.03400")
    mod.enforce_per_lot_stop_loss(c12, s12, Decimal("0.03400"), log, state_persist_fn=persist_ok)
    assert c12.canceled == ["sl-order-1"]
    assert len(c12.created) == 2 and c12.created[1]["price"] == Decimal("0.03400") and c12.created[1]["qty_cro"] == 714
    assert "sl-order-1" not in s12["tracked_orders"] and s12["open_lots"][0]["sell_order_id"] == "sl-order-2"
    # Marketable (bid at/above stop price) or fresh exits are left alone.
    mod.enforce_per_lot_stop_loss(c12, s12, Decimal("0.03400"), log, state_persist_fn=persist_ok)
    assert len(c12.created) == 2 and len(c12.canceled) == 1
    print("[PASS] 12. Stranded stop exit: confirmed cancel, replaced at 0.03400 once; marketable exit kept.")

    # 12b. Uncertain cancel of a stranded stop defers replacement and keeps the original tracked.
    s12b = mod.default_state()
    s12b["open_lots"] = [_fresh_lot()]
    c12b = EdgeMockClient(Decimal("0.03980"), {})
    mod.enforce_per_lot_stop_loss(c12b, s12b, Decimal("0.03980"), log, state_persist_fn=persist_ok)
    s12b["tracked_orders"]["sl-order-1"]["placed_ts"] = _time.time() - 30
    mod.enforce_per_lot_stop_loss(c12b, s12b, Decimal("0.03400"), log, state_persist_fn=persist_ok)
    assert len(c12b.created) == 1 and "sl-order-1" in s12b["tracked_orders"]
    print("[PASS] 12b. Stranded stop with non-terminal cancel: deferred, 0 replacements.")

    # 13. Submission that never reached the exchange: blocked while young or unverifiable,
    #     resubmitted exactly once after a successful history read past the resolve window.
    s13 = mod.default_state()
    s13["open_lots"] = [_fresh_lot()]
    c13 = EdgeMockClient(Decimal("0.03900"), {})
    state13 = {"history": "ok", "refuse": True}

    def _pp13(method, params=None):
        if method == "private/create-order":
            if state13["refuse"]:
                raise ConnectionError("connection refused before request was sent")
            res = c13.create_limit_order(side=params["side"], qty_cro=int(params["quantity"]),
                                         price=Decimal(params["price"]), client_oid=params["client_oid"], post_only=False)
            return {"result": res}
        if method == "private/get-order-history":
            if state13["history"] == "fail":
                raise TimeoutError("history unavailable")
            return {"result": {"data": []}}
        return {"result": {"data": []}}

    c13.private_post = _pp13
    try:
        mod.enforce_per_lot_stop_loss(c13, s13, Decimal("0.03900"), log, state_persist_fn=persist_ok)
        assert False, "Expected ConnectionError"
    except ConnectionError:
        pass
    state13["refuse"] = False
    assert "l0" in s13["pending_stop_intents"]
    mod.enforce_per_lot_stop_loss(c13, s13, Decimal("0.03800"), log, state_persist_fn=persist_ok)
    assert len(c13.created) == 0 and "l0" in s13["pending_stop_intents"], "Young intent must stay blocked"
    s13["pending_stop_intents"]["l0"]["created_ts"] = _time.time() - 120
    state13["history"] = "fail"
    mod.enforce_per_lot_stop_loss(c13, s13, Decimal("0.03800"), log, state_persist_fn=persist_ok)
    assert len(c13.created) == 0 and "l0" in s13["pending_stop_intents"], "Unverifiable intent must stay blocked"
    state13["history"] = "ok"
    old_oid = s13["pending_stop_intents"]["l0"]["client_oid"]
    mod.enforce_per_lot_stop_loss(c13, s13, Decimal("0.03800"), log, state_persist_fn=persist_ok)
    assert len(c13.created) == 1 and c13.created[0]["client_oid"] != old_oid
    assert "l0" not in s13["pending_stop_intents"] and s13["open_lots"][0]["sell_order_id"] == "sl-order-1"
    mod.enforce_per_lot_stop_loss(c13, s13, Decimal("0.03800"), log, state_persist_fn=persist_ok)
    assert len(c13.created) == 1
    print("[PASS] 13. Never-sent stop: blocked while young/unverifiable, resubmitted once after verified absence.")

if __name__ == "__main__":
    run_edge_tests()
