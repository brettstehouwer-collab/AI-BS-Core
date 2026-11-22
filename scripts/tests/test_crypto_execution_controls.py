"""Explicit synthetic events in new OS-temporary stores; no provider imports/I/O."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from decimal import Decimal
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("offline_crypto_controls", ROOT / "backend/core/crypto_execution_controls.py")
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


class ExecutionControlsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="aibs_offline_controls_")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "fixture.db"
        self.policy = c.RiskLimits(max_order_quote="200", max_position_quote="600", max_gross_quote="800",
            max_daily_quote="2000", max_fee_bps="100", max_slippage_bps="100", max_drawdown_bps="5000")
        self.engine = c.OfflineExecutionCoordinator.create(self.path, account="fixture-account", quote="USD",
                                                          cash="1000", limits=self.policy)
        self.market = c.Instrument("BTC", "USD", "0.00000001", "0.01", "0.00000001", "0.01")
        self.quote("10", 1000)

    def quote(self, price, time=1000):
        self.engine.quote_market(self.market, bid=price, ask=price, observed_ms=time, now_ms=time)

    def prepare(self, name="buy-1", *, quantity="10", price="10", side="buy", stop="8", time=1000, trail="0"):
        return self.engine.prepare(name, symbol="BTC/USD", side=side, quantity=quantity,
            limit_price=price, now_ms=time, hard_stop=stop if side == "buy" else None, trailing_bps=trail)

    def submit(self, name="buy-1", **kw):
        self.prepare(name, **kw)
        self.engine.begin_submission(name, now_ms=kw.get("time", 1000))

    def fill(self, name="buy-1", *, fid="fill-1", quantity="10", cost="100", fees=(), sequence=1,
             side="buy", complete=True):
        order_time = next((row["created_ms"] for row in self.engine.snapshot()["orders"] if row["client_id"] == name), 1000)
        return c.Fill(fid, name, "ex-" + name, "BTC/USD", side, quantity, cost, fees, sequence, order_time, complete)

    def order(self, name="buy-1"):
        return next(row for row in self.engine.snapshot()["orders"] if row["client_id"] == name)

    def balance(self, asset):
        return Decimal(next((row["total"] for row in self.engine.snapshot()["balances"] if row["asset"] == asset), "0"))

    def reconcile(self, name="buy-1", state="OPEN", qty="0"):
        self.engine.reconcile(name, exchange_order_id="ex-" + name, state=state,
                              cumulative_quantity=qty, authoritative=True)

    def acquire(self, trail="0", stop="8"):
        self.submit(trail=trail, stop=stop)
        self.engine.apply_fill(self.fill())

    def test_ack_is_not_a_fill_and_partial_fills_are_replay_safe(self):
        self.submit()
        self.reconcile()
        self.assertEqual(self.balance("BTC"), 0)
        fill = self.fill(quantity="4", cost="40", fees=(("USD", "0.2"),))
        self.assertTrue(self.engine.apply_fill(fill))
        self.assertFalse(self.engine.apply_fill(replace(fill, quantity="4.0", cost="40.00")))
        self.assertEqual(self.balance("USD"), Decimal("959.8"))
        self.assertEqual(self.balance("BTC"), 4)
        self.assertEqual(self.order()["state"], "PARTIAL")
        self.assertEqual(Decimal(self.order()["reserve_amount"]), Decimal("60.6"))
        self.reconcile(state="CANCELLED", qty="4")
        self.assertEqual(self.order()["reserve_amount"], "0")
        self.assertEqual(self.engine.snapshot()["positions"][0]["basis"], "40.2")

    def test_fill_based_cost_basis_quote_fee_and_negative_realized_pnl(self):
        self.submit()
        self.engine.apply_fill(self.fill(fees=(("USD", "1"),)))
        self.assertEqual(self.balance("USD"), 899)
        self.quote("9", 1100)
        self.submit("sell-1", side="sell", quantity="4", price="9", time=1100)
        self.engine.apply_fill(self.fill("sell-1", fid="sell-fill", quantity="4", cost="36",
            fees=(("USD", "0.2"),), sequence=2, side="sell"))
        pos = self.engine.snapshot()["positions"][0]
        self.assertEqual(pos["quantity"], "6")
        self.assertEqual(pos["basis"], "60.6")
        self.assertEqual(pos["realized"], "-4.6")
        self.assertEqual(self.balance("USD"), Decimal("934.8"))

    def test_base_fees_are_inventory_deductions(self):
        self.submit()
        self.engine.apply_fill(self.fill(fees=(("BTC", "0.1"),)))
        self.assertEqual(self.balance("BTC"), Decimal("9.9"))
        self.assertEqual(self.engine.snapshot()["positions"][0]["basis"], "100")
        self.submit("sell", side="sell", quantity="1", price="10")
        self.engine.apply_fill(self.fill("sell", fid="s", quantity="1", cost="10",
            fees=(("BTC", "0.01"),), sequence=2, side="sell"))
        self.assertEqual(self.balance("BTC"), Decimal("8.89"))

    def test_unsupported_or_missing_fee_is_retained_pending_without_accounting(self):
        for kwargs in ({"fees": (("CRO", "0.1"),)}, {"complete": False}, {"fees": (("USD", "-0.01"),)}):
            with self.subTest(kwargs=kwargs):
                # Isolate both scenarios; no real monetary store touched.
                with tempfile.TemporaryDirectory() as directory:
                    engine = c.OfflineExecutionCoordinator.create(Path(directory) / "x.db", account="fixture", quote="USD", cash="1000")
                    engine.quote_market(self.market, bid="10", ask="10", observed_ms=1, now_ms=1)
                    engine.prepare("buy-1", symbol="BTC/USD", side="buy", quantity="1", limit_price="10", hard_stop="8", now_ms=1)
                    engine.begin_submission("buy-1", now_ms=1)
                    with self.assertRaises(c.Held):
                        engine.apply_fill(self.fill(quantity="1", cost="10", **kwargs))
                    snap = engine.snapshot()
                    self.assertEqual(snap["fills"][0]["state"], "PENDING")
                    self.assertTrue(snap["risk"]["halted"])
                    self.assertEqual(len(snap["positions"]), 0)
                    self.assertEqual(snap["balances"][0]["total"], "1000")

    def test_conflicting_duplicate_halts_and_preserves_original(self):
        self.submit()
        self.engine.apply_fill(self.fill())
        with self.assertRaises(c.Held):
            self.engine.apply_fill(replace(self.fill(), cost="99"))
        self.assertEqual(self.balance("USD"), 900)
        self.assertTrue(self.engine.snapshot()["risk"]["halted"])
        self.assertEqual(len(self.engine.snapshot()["fills"]), 1)

    def test_overfill_and_price_breach_do_not_mutate_balances(self):
        self.submit()
        for fill in (self.fill(quantity="11", cost="110"), self.fill(fid="breach", cost="101", sequence=1)):
            with self.subTest(fill=fill), self.assertRaises(c.Held):
                self.engine.apply_fill(fill)
        self.assertEqual(self.balance("USD"), 1000)
        self.assertEqual(self.balance("BTC"), 0)
        self.assertEqual(len(self.engine.snapshot()["fills"]), 2)

    def test_unknown_survives_restart_and_never_expires_or_resends(self):
        self.submit()
        self.engine.mark_unknown("buy-1", "HTTP_503")
        self.engine = c.OfflineExecutionCoordinator(self.path)
        self.assertEqual(self.order()["state"], "UNKNOWN")
        self.assertEqual(self.order()["reserve_amount"], "101")
        self.assertEqual(self.engine.recovery_orders()[0]["recovery_action"], "LOOKUP_ONLY_NEVER_RESEND")
        with self.assertRaises(c.ControlError):
            self.engine.begin_submission("buy-1", now_ms=1000)
        with self.assertRaises(c.ControlError):
            self.prepare("new", time=100000000)
        self.assertEqual(self.order()["reserve_amount"], "101")
        self.reconcile(state="CANCELLED")
        self.assertEqual(self.order()["reserve_amount"], "0")

    def test_crash_in_submitting_is_recovery_not_retry(self):
        self.submit()
        restarted = c.OfflineExecutionCoordinator(self.path)
        self.assertEqual(restarted.recovery_orders()[0]["state"], "SUBMITTING")
        with self.assertRaises(c.ControlError):
            restarted.begin_submission("buy-1", now_ms=1000)

    def test_terminal_quantity_mismatch_keeps_funds_and_hold(self):
        self.submit()
        with self.assertRaises(c.Held):
            self.reconcile(state="FILLED", qty="10")
        self.assertEqual(self.order()["reserve_amount"], "101")
        self.assertEqual(self.order()["state"], "UNKNOWN")
        self.engine.apply_fill(self.fill())  # Evidence accounting remains possible while held.
        self.reconcile(state="FILLED", qty="10")
        self.assertTrue(self.engine.snapshot()["risk"]["halted"])

    def test_late_fill_after_cancel_is_accounted_and_halts(self):
        self.submit()
        self.reconcile(state="CANCELLED")
        self.engine.apply_fill(self.fill(quantity="4", cost="40"))
        self.assertEqual(self.balance("BTC"), 4)
        self.assertEqual(self.order()["state"], "UNKNOWN")
        self.assertTrue(self.engine.snapshot()["risk"]["halted"])

    def test_intent_id_is_immutable_and_idempotent(self):
        before = self.prepare()
        self.assertEqual(before, self.prepare())
        with self.assertRaises(c.Held):
            self.prepare(quantity="9")
        self.assertEqual(len(self.engine.snapshot()["orders"]), 1)
        self.assertTrue(self.engine.snapshot()["risk"]["halted"])

    def test_concurrent_workers_share_exposure_reservations(self):
        def reserve(n):
            engine = c.OfflineExecutionCoordinator(self.path)
            try:
                engine.prepare("worker-" + str(n), symbol="BTC/USD", side="buy", quantity="20",
                    limit_price="10", hard_stop="8", now_ms=1000)
                return True
            except c.ControlError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            successes = list(pool.map(reserve, range(12)))
        self.assertEqual(sum(successes), 2)  # ceiling=600 includes worst-case fees
        self.assertEqual(sum(Decimal(r["reserve_amount"]) for r in self.engine.snapshot()["orders"]), 404)

    def test_concurrent_duplicate_fill_is_applied_once(self):
        self.submit()
        def apply(_):
            return c.OfflineExecutionCoordinator(self.path).apply_fill(self.fill())
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(apply, range(8))), 1)
        self.assertEqual(self.balance("BTC"), 10)

    def test_rejection_breaker_is_durable_and_duplicate_safe(self):
        for n in range(3):
            name = "reject-" + str(n)
            self.submit(name, quantity="1")
            self.reconcile(name, "REJECTED")
            self.reconcile(name, "REJECTED")
        restarted = c.OfflineExecutionCoordinator(self.path)
        self.assertEqual(restarted.snapshot()["risk"]["rejections"], 3)
        self.assertTrue(restarted.snapshot()["risk"]["halted"])
        with self.assertRaises(c.ControlError):
            self.prepare("blocked")

    def test_old_ack_does_not_reset_later_rejections(self):
        self.submit("old")
        self.reconcile("old")
        self.submit("failed", quantity="1")
        self.reconcile("failed", "REJECTED")
        self.reconcile("old")
        self.assertEqual(self.engine.snapshot()["risk"]["rejections"], 1)

    def test_sequence_gap_keeps_inbox_and_can_apply_once_after_prior_fact(self):
        self.submit()
        second = self.fill(fid="second", quantity="5", cost="50", sequence=2)
        with self.assertRaises(c.Held):
            self.engine.apply_fill(second)
        self.engine.apply_fill(self.fill(quantity="5", cost="50"))
        self.assertTrue(self.engine.apply_fill(second))
        self.assertEqual(self.balance("BTC"), 10)
        self.assertTrue(self.engine.snapshot()["risk"]["halted"])

    def test_transaction_failure_rolls_back_all_financial_fields(self):
        self.submit()
        original = self.engine._arm_stop
        with patch.object(self.engine, "_arm_stop", side_effect=c.ControlError("injected fixture fault")):
            with self.assertRaises(c.Held):
                self.engine.apply_fill(self.fill())
        self.assertEqual(self.balance("USD"), 1000)
        self.assertEqual(self.order()["filled_quantity"], "0")
        self.assertEqual(self.engine.snapshot()["positions"], [])
        self.assertEqual(self.engine.snapshot()["daily"], [])
        self.assertEqual(self.engine.snapshot()["fills"][0]["state"], "PENDING")
        self.assertTrue(self.engine.apply_fill(self.fill()))
        self.assertTrue(callable(original))

    def test_stop_watermark_is_durable_never_lowers_and_deduplicates_exit(self):
        self.acquire(trail="1000")
        self.quote("12", 1100)
        self.assertIsNone(self.engine.evaluate_stop("BTC/USD", now_ms=1100))
        self.engine = c.OfflineExecutionCoordinator(self.path)
        self.assertEqual(self.engine.snapshot()["stops"][0]["effective_stop"], "10.8")
        self.quote("10.5", 1200)
        def trigger(_):
            return c.OfflineExecutionCoordinator(self.path).evaluate_stop("BTC/USD", now_ms=1200)
        with ThreadPoolExecutor(max_workers=4) as pool:
            orders = list(pool.map(trigger, range(8)))
        self.assertEqual(len({o["client_id"] for o in orders}), 1)
        self.assertEqual(len(self.engine.snapshot()["orders"]), 2)
        self.assertEqual(self.engine.snapshot()["stops"][0]["effective_stop"], "10.8")

    def test_partial_cancelled_exit_leaves_protection_and_allows_next_generation(self):
        self.acquire()
        self.quote("7", 1100)
        exit_order = self.engine.evaluate_stop("BTC/USD", now_ms=1100)
        name = exit_order["client_id"]
        self.engine.begin_submission(name, now_ms=1100)
        self.engine.apply_fill(self.fill(name, fid="exit", quantity="4", cost="28", side="sell", sequence=2))
        self.reconcile(name, "CANCELLED", "4")
        next_exit = self.engine.evaluate_stop("BTC/USD", now_ms=1100)
        self.assertNotEqual(next_exit["client_id"], name)
        self.assertEqual(self.engine.snapshot()["stops"][0]["triggered"], 1)
        self.assertEqual(self.engine.snapshot()["positions"][0]["quantity"], "6")

    def test_every_quote_persists_peak_and_crossing_before_stop_evaluation(self):
        self.acquire(trail="1000")
        self.quote("12", 1100)
        self.engine = c.OfflineExecutionCoordinator(self.path)
        self.assertEqual(self.engine.snapshot()["stops"][0]["high_water"], "12")
        self.quote("10", 1200)
        self.quote("11", 1300)  # A rebound cannot erase the missed crossing.
        self.engine = c.OfflineExecutionCoordinator(self.path)
        stop = self.engine.snapshot()["stops"][0]
        self.assertEqual(stop["effective_stop"], "10.8")
        self.assertEqual(stop["triggered"], 1)
        self.assertEqual(len(self.engine.snapshot()["orders"]), 1)
        self.assertIsNotNone(self.engine.evaluate_stop("BTC/USD", now_ms=1300))

    def test_trailing_stop_is_anchored_to_first_fill_before_any_new_quote(self):
        self.submit(trail="1000")
        # The last quote predates execution and cannot raise its entry peak.
        self.engine.apply_fill(replace(self.fill(), occurred_ms=1050))
        stop = self.engine.snapshot()["stops"][0]
        self.assertEqual(stop["high_water"], "10")
        self.assertEqual(stop["effective_stop"], "9")
        self.quote("9", 1100)
        self.assertEqual(self.engine.snapshot()["stops"][0]["triggered"], 1)
        self.assertIsNotNone(self.engine.evaluate_stop("BTC/USD", now_ms=1100))

    def test_discretionary_sell_reservations_prevent_stop_oversell(self):
        self.acquire()
        self.prepare("manual-exit", side="sell", quantity="8", price="10")
        self.quote("7", 1100)
        exit_order = self.engine.evaluate_stop("BTC/USD", now_ms=1100)
        reserve = sum(Decimal(o["reserve_amount"]) for o in self.engine.snapshot()["orders"] if o["reserve_asset"] == "BTC")
        self.assertLessEqual(reserve, self.balance("BTC"))
        self.assertIsNotNone(exit_order)

    def test_stale_future_and_out_of_order_quotes_cannot_change_stop(self):
        self.acquire(trail="1000")
        with self.assertRaises(c.ControlError):
            self.engine.evaluate_stop("BTC/USD", now_ms=7000)
        with self.assertRaises(c.ControlError):
            self.engine.quote_market(self.market, bid="20", ask="20", observed_ms=2000, now_ms=1000)
        with self.assertRaises(c.ControlError):
            self.quote("20", 999)
        self.assertEqual(self.engine.snapshot()["stops"][0]["high_water"], "10")

    def test_slippage_stop_requirement_and_precision_are_enforced(self):
        for kwargs in ({"price": "10.11"}, {"stop": None}, {"quantity": "1.000000001"},
                       {"price": "10.001"}, {"quantity": "21"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(c.ControlError):
                self.prepare(**kwargs)
        for bad in (True, 0.1, "NaN", "Infinity", "-1", "1e1000", "1e-1000"):
            with self.subTest(bad=bad), self.assertRaises(c.ControlError):
                c.number(bad)
        self.assertEqual(c.number("0.000000000000000001"), Decimal("1e-18"))

    def test_policy_persisted_and_no_default_or_production_store(self):
        self.assertFalse(self.engine.snapshot()["live_dispatch_enabled"])
        self.assertEqual(c.OfflineExecutionCoordinator(self.path).limits, self.engine.limits)
        with self.assertRaises(c.ControlError):
            c.OfflineExecutionCoordinator.create(self.path, account="fixture", quote="USD", cash="1")
        with self.assertRaises(c.ControlError):
            c.OfflineExecutionCoordinator.create(ROOT / "trading_control_state.db", account="fixture", quote="USD", cash="1")
        with self.assertRaises(c.ControlError):
            c.OfflineExecutionCoordinator(Path(self.directory.name) / "missing.db")
        with closing(sqlite3.connect(self.path)) as db:
            columns = [row[2] for row in db.execute("PRAGMA table_info(orders)")]
        self.assertNotIn("REAL", columns)

    def test_submission_rechecks_quote_age_and_market_movement(self):
        self.prepare()
        with self.assertRaises(c.ControlError):
            self.engine.begin_submission("buy-1", now_ms=7000)
        self.quote("9", 1100)
        with self.assertRaises(c.ControlError):
            self.engine.begin_submission("buy-1", now_ms=1100)
        self.assertEqual(self.order()["state"], "INTENT")

    def test_full_close_clears_basis_exactly_with_base_fee(self):
        self.submit(quantity="10.1")
        self.engine.apply_fill(self.fill(quantity="10.1", cost="101"))
        self.submit("close", side="sell", quantity="10", price="10")
        self.engine.apply_fill(self.fill("close", fid="close-fill", quantity="10", cost="100",
            fees=(("BTC", "0.1"),), sequence=2, side="sell"))
        pos = self.engine.snapshot()["positions"][0]
        self.assertEqual((pos["quantity"], pos["basis"], pos["realized"]), ("0", "0", "-1"))
        self.assertEqual(self.engine.snapshot()["stops"][0]["status"], "CLOSED")

    def test_unmatched_fill_is_retained_and_halts_without_inventing_order(self):
        with self.assertRaises(c.Held):
            self.engine.apply_fill(self.fill("unmatched"))
        snap = self.engine.snapshot()
        self.assertEqual(len(snap["unmatched_fills"]), 1)
        self.assertEqual(snap["orders"], [])
        self.assertEqual(self.balance("USD"), 1000)
        self.assertTrue(snap["risk"]["halted"])

    def test_drawdown_stop_failure_preserves_circuit_breaker(self):
        self.acquire()
        # Explicit test fault/fixture, never mutate an actual ledger.
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE risk SET peak_equity='3000' WHERE id=1")
            db.commit()
        self.quote("7", 1100)
        self.assertIsNone(self.engine.evaluate_stop("BTC/USD", now_ms=1100))
        self.assertTrue(self.engine.snapshot()["risk"]["halted"])
        self.assertEqual(self.engine.snapshot()["stops"][0]["status"], "TRIGGERED_HELD")

    def test_old_order_poll_cannot_reset_newer_rejections(self):
        self.submit("old", quantity="1")
        self.reconcile("old")
        self.submit("failed", quantity="1")
        self.reconcile("failed", "REJECTED")
        self.engine.mark_unknown("old", "TIMEOUT")
        self.reconcile("old")
        self.assertEqual(self.engine.snapshot()["risk"]["rejections"], 1)

    def test_direct_successful_fill_resets_latest_rejection_streak(self):
        self.submit("failed", quantity="1")
        self.engine.reconcile("failed", exchange_order_id=None, state="REJECTED", cumulative_quantity="0", authoritative=True)
        self.submit()
        self.engine.apply_fill(self.fill())
        self.assertEqual(self.engine.snapshot()["risk"]["rejections"], 0)

    def test_historical_fill_time_and_known_to_unmatched_conflict_are_held(self):
        self.submit()
        with self.assertRaises(c.Held):
            self.engine.apply_fill(replace(self.fill(), occurred_ms=999))
        self.assertEqual(self.balance("USD"), 1000)
        self.assertEqual(self.engine.snapshot()["fills"][0]["state"], "PENDING")

    def test_observed_peak_updates_without_an_order(self):
        self.acquire()
        self.quote("50", 1100)
        self.assertEqual(self.engine.snapshot()["risk"]["peak_equity"], "1400")

    def test_receipt_conflict_cannot_create_second_unmatched_identity(self):
        self.submit()
        self.engine.apply_fill(self.fill())
        with self.assertRaises(c.Held):
            self.engine.apply_fill(replace(self.fill(), client_id="missing"))
        self.assertEqual(self.engine.snapshot()["unmatched_fills"], [])

    def test_submission_cannot_precede_intent_or_bypass_changed_daily_limit(self):
        self.prepare(time=2000)
        with self.assertRaises(c.ControlError):
            self.engine.begin_submission("buy-1", now_ms=1500)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT INTO daily VALUES(0,'1999')")
            db.commit()
        with self.assertRaises(c.ControlError):
            self.engine.begin_submission("buy-1", now_ms=2000)
        self.assertEqual(self.order()["state"], "INTENT")

    def test_intent_cannot_dispatch_after_its_stop_latches(self):
        self.acquire()
        self.prepare("additional-buy", quantity="1", stop="8")
        self.quote("7", 1100)
        self.engine.evaluate_stop("BTC/USD", now_ms=1100)
        # A later recovery in quote cannot clear the already latched stop.
        self.quote("10", 1200)
        with self.assertRaises(c.ControlError):
            self.engine.begin_submission("additional-buy", now_ms=1200)


if __name__ == "__main__":
    unittest.main()
