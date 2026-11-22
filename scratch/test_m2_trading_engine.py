"""Isolated mock unit test suite for Milestone M2 (F6 & F7).

Uses tempfile.TemporaryDirectory(), ephemeral port 0, and mocked CryptoComClient.
Performs ZERO live exchange requests and ZERO writes to C:\\AI-BS\\saved_data\\.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gc
import importlib.util
import json
import logging
from pathlib import Path
import socket
import sqlite3
import ssl
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeCryptoComClient:
    """In-memory mock CryptoComClient supporting partial/full fills and TP sells."""

    def __init__(self) -> None:
        self.best_bid = Decimal("0.04386")
        self.best_ask = Decimal("0.04388")
        self.bids = [(Decimal("0.04386"), Decimal("25000")), (Decimal("0.04385"), Decimal("15000"))]
        self.asks = [(Decimal("0.04388"), Decimal("18000")), (Decimal("0.04389"), Decimal("20000"))]
        self.open_orders: list[dict] = []
        self.order_details: dict[str, dict] = {}
        self.balances: dict[str, dict[str, Decimal]] = {
            "USDT": {"total": Decimal("95.756234"), "reserved": Decimal("94.94083"), "free": Decimal("0.815404")},
            "CRO": {"total": Decimal("0.036881"), "reserved": Decimal("0"), "free": Decimal("0.036881")},
            "USD": {"total": Decimal("0.000001"), "reserved": Decimal("0"), "free": Decimal("0.000001")},
        }
        self.created_orders: list[dict] = []
        self.cancelled_orders: list[str] = []
        self._next_oid = 9000000000001

    def get_book(self, depth: int = 10):
        return self.best_bid, self.best_ask, self.bids[:depth], self.asks[:depth]

    def get_open_orders(self):
        return [dict(o) for o in self.open_orders]

    def get_order_detail(self, order_id: str):
        return dict(self.order_details[str(order_id)])

    def get_balances(self):
        return {k: dict(v) for k, v in self.balances.items()}

    def create_limit_order(self, *, side: str, qty_cro: int, price: Decimal, client_oid: str):
        oid = str(self._next_oid)
        self._next_oid += 1
        order = {
            "order_id": oid,
            "client_oid": client_oid,
            "side": side,
            "order_type": "LIMIT",
            "time_in_force": "GOOD_TILL_CANCEL",
            "exec_inst": ["POST_ONLY"],
            "quantity": str(qty_cro),
            "limit_price": f"{price:.5f}",
            "cumulative_quantity": "0",
            "cumulative_fee": "0",
            "fee_instrument_name": "CRO",
            "status": "ACTIVE",
            "create_time": 1794892000000,
        }
        self.created_orders.append(order)
        self.open_orders.append(order)
        self.order_details[oid] = dict(order)
        if side == "SELL":
            cro_b = self.balances["CRO"]
            cro_b["reserved"] += Decimal(qty_cro)
            cro_b["free"] = max(cro_b["total"] - cro_b["reserved"], Decimal("0"))
        elif side == "BUY":
            usdt_b = self.balances["USDT"]
            usdt_b["reserved"] += Decimal(qty_cro) * price
            usdt_b["free"] = max(usdt_b["total"] - usdt_b["reserved"], Decimal("0"))
        return {"order_id": oid, "client_oid": client_oid}

    def cancel_order(self, order_id: str):
        self.cancelled_orders.append(str(order_id))
        self.open_orders = [o for o in self.open_orders if str(o["order_id"]) != str(order_id)]


def _seed_three_tranches(client: FakeCryptoComClient) -> None:
    client.open_orders = [
        {
            "order_id": "6530219611092604764",
            "client_oid": "dip-1794891363-643110",
            "side": "BUY",
            "order_type": "LIMIT",
            "time_in_force": "GOOD_TILL_CANCEL",
            "exec_inst": ["POST_ONLY"],
            "quantity": "687",
            "limit_price": "0.04364",
            "cumulative_quantity": "0",
            "cumulative_fee": "0",
            "fee_instrument_name": "CRO",
            "status": "ACTIVE",
            "create_time": 1794891364170,
        },
        {
            "order_id": "6530219611092605070",
            "client_oid": "dip-1794891363-e0db4d",
            "side": "BUY",
            "order_type": "LIMIT",
            "time_in_force": "GOOD_TILL_CANCEL",
            "exec_inst": ["POST_ONLY"],
            "quantity": "811",
            "limit_price": "0.04311",
            "cumulative_quantity": "0",
            "cumulative_fee": "0",
            "fee_instrument_name": "CRO",
            "status": "ACTIVE",
            "create_time": 1794891364552,
        },
        {
            "order_id": "6530219611092605204",
            "client_oid": "dip-1794891364-8fe607",
            "side": "BUY",
            "order_type": "LIMIT",
            "time_in_force": "GOOD_TILL_CANCEL",
            "exec_inst": ["POST_ONLY"],
            "quantity": "706",
            "limit_price": "0.04249",
            "cumulative_quantity": "0",
            "cumulative_fee": "0",
            "fee_instrument_name": "CRO",
            "status": "ACTIVE",
            "create_time": 1794891364955,
        },
    ]
    for o in client.open_orders:
        client.order_details[o["order_id"]] = dict(o)


class TestStructuralDipEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self.engine = _load_module("structural_dip_engine", r"C:\AI-BS\scratch\structural_dip_engine.py")
        self.log = logging.getLogger("test_structural_dip_engine")
        self.log.handlers = []
        self.log.addHandler(logging.NullHandler())

        self.patches = [
            patch.object(self.engine, "SAVED_DATA_DIR", self.tmp_path),
            patch.object(self.engine, "STATE_FILE", self.tmp_path / "structural_dip_state.json"),
            patch.object(self.engine, "SCOUT_SIGNAL_FILE", self.tmp_path / "orderbook_scout_signals.json"),
            patch.object(self.engine, "LOG_FILE", self.tmp_path / "structural_dip_engine.log"),
            patch.object(self.engine, "LEDGER_CSV_FILE", self.tmp_path / "trade_ledger.csv"),
            patch.object(self.engine, "LEDGER_DB_FILE", self.tmp_path / "trade_ledger.db"),
            patch.object(self.engine, "TELEMETRY_PORT", 0),
            patch.object(self.engine, "_LATEST_STATE", None),
        ]
        for p in self.patches:
            p.start()
        self.engine.init_ledgers()

    def tearDown(self) -> None:
        for p in reversed(self.patches):
            p.stop()
        gc.collect()
        self.tmpdir.cleanup()

    def test_adopts_3_tranches_without_cancelling_or_placing(self) -> None:
        client = FakeCryptoComClient()
        _seed_three_tranches(client)
        state = self.engine.load_state()

        self.engine.run_cycle(client, state, self.log)

        self.assertEqual(client.cancelled_orders, [])
        self.assertEqual(client.created_orders, [])
        self.assertEqual(len(state["active_orders"]), 3)
        self.assertEqual(state["tracked_orders"]["6530219611092604764"]["target_profit_pct"], "0.015")
        self.assertEqual(state["tracked_orders"]["6530219611092605070"]["target_profit_pct"], "0.018")
        self.assertEqual(state["tracked_orders"]["6530219611092605204"]["target_profit_pct"], "0.022")
        self.assertEqual(state["portfolio_valuation"]["total_account_value_usd"], "95.76")

    def test_partial_and_full_fills_trigger_post_only_tp_sell_and_pnl(self) -> None:
        client = FakeCryptoComClient()
        _seed_three_tranches(client)
        state = self.engine.load_state()
        self.engine.run_cycle(client, state, self.log)

        # Partial fill of 300 CRO on Tranche 1 (0.04364)
        client.open_orders[0]["cumulative_quantity"] = "300"
        client.order_details["6530219611092604764"].update({
            "cumulative_quantity": "300",
            "avg_price": "0.04364",
            "status": "ACTIVE",
        })
        client.balances["CRO"]["total"] += Decimal("300")
        client.balances["CRO"]["free"] += Decimal("300")

        self.engine.run_cycle(client, state, self.log)

        self.assertEqual(client.cancelled_orders, [])
        self.assertEqual(len(client.created_orders), 1)
        tp1 = client.created_orders[0]
        self.assertEqual(tp1["side"], "SELL")
        self.assertEqual(tp1["quantity"], "300")
        self.assertEqual(tp1["exec_inst"], ["POST_ONLY"])
        self.assertEqual(tp1["time_in_force"], "GOOD_TILL_CANCEL")
        # 0.04364 * 1.015 = 0.0442946 -> ceil_price_tick = 0.04430 (> best_bid 0.04386)
        self.assertEqual(tp1["limit_price"], "0.04430")

        # Next idle tick must NOT create a duplicate SELL for the same 300 CRO
        self.engine.run_cycle(client, state, self.log)
        self.assertEqual(len(client.created_orders), 1)

        # Full fill of TP SELL 300 CRO @ 0.04430
        tp1_oid = tp1["order_id"]
        client.open_orders = [o for o in client.open_orders if o["order_id"] != tp1_oid]
        client.order_details[tp1_oid].update({
            "cumulative_quantity": "300",
            "avg_price": "0.04430",
            "cumulative_fee": "0",
            "fee_instrument_name": "CRO",
            "status": "FILLED",
        })
        client.balances["CRO"]["reserved"] -= Decimal("300")
        client.balances["CRO"]["total"] -= Decimal("300")

        self.engine.run_cycle(client, state, self.log)

        # Genuine PnL: (0.04430 - 0.04364) * 300 = 0.00066 * 300 = 0.198000 (no fake 0.25% fee)
        self.assertEqual(state["completed_cycles"], 1)
        self.assertEqual(state["daily_realized_pnl_usdt"], "0.198000")

        # Verify 12-column CSV and SQLite DB match
        with open(self.tmp_path / "trade_ledger.csv", "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        self.assertEqual(len(rows), 3)  # header + DIP_BUY + DIP_SELL
        self.assertEqual(len(rows[0]), 12)
        self.assertEqual(rows[1][2], "DIP_BUY")
        self.assertEqual(rows[2][2], "DIP_SELL")
        self.assertEqual(rows[2][7], "0.198000")

        conn = sqlite3.connect(str(self.tmp_path / "trade_ledger.db"))
        try:
            db_count = conn.execute("SELECT COUNT(*) FROM trade_fills").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(db_count, 2)

    def test_tp_sell_enforces_post_only_above_best_bid(self) -> None:
        client = FakeCryptoComClient()
        _seed_three_tranches(client)
        state = self.engine.load_state()
        self.engine.run_cycle(client, state, self.log)

        # Market rallied far above entry before TP SELL is placed: best_bid=0.04600
        client.best_bid = Decimal("0.04600")
        client.best_ask = Decimal("0.04602")
        client.bids = [(Decimal("0.04600"), Decimal("10000"))]
        client.asks = [(Decimal("0.04602"), Decimal("10000"))]
        client.open_orders = [o for o in client.open_orders if o["order_id"] != "6530219611092604764"]
        client.order_details["6530219611092604764"].update({
            "cumulative_quantity": "687",
            "avg_price": "0.04364",
            "status": "FILLED",
        })
        client.balances["CRO"]["total"] += Decimal("687")
        client.balances["CRO"]["free"] += Decimal("687")

        self.engine.run_cycle(client, state, self.log)

        self.assertEqual(len(client.created_orders), 1)
        tp = client.created_orders[0]
        self.assertEqual(tp["side"], "SELL")
        self.assertEqual(tp["limit_price"], "0.04601")  # best_bid + PRICE_TICK

    def test_new_grid_respects_safe_buy_ceiling_and_stale_fallback(self) -> None:
        client = FakeCryptoComClient()
        client.open_orders = []
        client.balances["USDT"] = {"total": Decimal("95.76"), "reserved": Decimal("0"), "free": Decimal("95.76")}
        state = self.engine.load_state()

        # Fresh scout signal capping safe_buy_ceiling at 0.04320
        (self.tmp_path / "orderbook_scout_signals.json").write_text(json.dumps({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "instrument": "CRO_USDT",
            "safe_buy_ceiling": 0.04320,
        }), encoding="utf-8")

        self.engine.run_cycle(client, state, self.log)

        self.assertEqual(len(client.created_orders), 3)
        # Tranche 1 (1.2% below 0.04387 = 0.04334) must be capped to 0.04320
        self.assertEqual(client.created_orders[0]["limit_price"], "0.04320")
        self.assertEqual(client.created_orders[1]["limit_price"], "0.04281")
        self.assertEqual(client.created_orders[2]["limit_price"], "0.04220")

        # Test stale fallback (> 15s old) -> falls back to best_bid - PRICE_TICK (0.04385)
        (self.tmp_path / "orderbook_scout_signals.json").write_text(json.dumps({
            "timestamp_utc": (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat(),
            "instrument": "CRO_USDT",
            "safe_buy_ceiling": 0.04200,
        }), encoding="utf-8")
        ceiling = self.engine.read_safe_buy_ceiling(Decimal("0.04386"), Decimal("0.04388"), self.log)
        self.assertEqual(ceiling, Decimal("0.04385"))

    def test_telemetry_http_server_schema_and_cors(self) -> None:
        client = FakeCryptoComClient()
        _seed_three_tranches(client)
        state = self.engine.load_state()
        self.engine.run_cycle(client, state, self.log)

        server = self.engine.start_telemetry_server(self.log, state)
        port = server.server_address[1]
        try:
            # OPTIONS preflight for localhost:5173
            req_opt = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/live-telemetry",
                method="OPTIONS",
                headers={"Origin": "http://localhost:5173"},
            )
            with urllib.request.urlopen(req_opt, timeout=3) as resp:
                self.assertEqual(resp.status, 204)
                self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")

            # GET /api/live-telemetry for 127.0.0.1:5173
            req_get = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/live-telemetry",
                headers={"Origin": "http://127.0.0.1:5173"},
            )
            with urllib.request.urlopen(req_get, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5173")
                payload = json.loads(resp.read().decode("utf-8"))

            self.assertEqual(payload["status"], "LIVE_ACTIVE")
            self.assertEqual(payload["buy_dip_pct"], "1.20")
            self.assertEqual(payload["take_profit_pct"], "1.50")
            self.assertEqual(payload["portfolio_valuation"]["total_account_value_usd"], "95.76")
            self.assertEqual(len(payload["active_orders"]), 3)
            self.assertEqual(payload["active_orders"][0]["price"], "0.04364")
            self.assertTrue(len(payload["last_book"]["bids"]) >= 2)
            self.assertTrue(len(payload["last_book"]["asks"]) >= 2)
            self.assertIsNotNone(payload["last_tick_utc"])
        finally:
            server.shutdown()
            server.server_close()


class TestAgent4RiskWatchdog(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self.watchdog = _load_module("agent4_risk_watchdog", r"C:\AI-BS\scratch\agent4_risk_watchdog.py")
        self.log = logging.getLogger("test_agent4_watchdog")
        self.log.handlers = []
        self.log.addHandler(logging.NullHandler())

        self.scout_path = self.tmp_path / "orderbook_scout_signals.json"
        self.scout_path.write_text(json.dumps({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "instrument": "CRO_USDT",
        }), encoding="utf-8")

        self.status_path = self.tmp_path / "agent4_watchdog_status.json"
        self.patches = [
            patch.object(self.watchdog, "SAVED_DATA_DIR", self.tmp_path),
            patch.object(self.watchdog, "OUTPUT_STATUS_PATH", self.status_path),
            patch.object(self.watchdog, "SCOUT_SIGNAL_PATH", self.scout_path),
            patch.object(self.watchdog, "LOG_FILE", self.tmp_path / "agent4_risk_watchdog.log"),
        ]
        for p in self.patches:
            p.start()

        self.ctx = {
            "last_equity_check_ts": 0.0,
            "baseline_equity_usdt": None,
            "equity_drawdown_usdt": Decimal("0"),
            "equity_snapshot": None,
        }

    def tearDown(self) -> None:
        for p in reversed(self.patches):
            p.stop()
        gc.collect()
        self.tmpdir.cleanup()

    def _fresh_telemetry(self) -> dict:
        return {
            "status": "LIVE_ACTIVE",
            "last_tick_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "daily_realized_pnl_usdt": "0.000000",
            "active_orders": [],
            "last_book": {"best_bid": "0.04386", "best_ask": "0.04388", "mid_price": "0.04387"},
        }

    def test_healthy_3_dip_tranches_zero_false_alarms(self) -> None:
        client = FakeCryptoComClient()
        _seed_three_tranches(client)

        with patch.object(self.watchdog, "check_trader_telemetry", return_value=self._fresh_telemetry()):
            res = self.watchdog.run_watchdog_cycle(client, self.ctx, self.log)

        self.assertEqual(res["watchdog_status"], "ONLINE")
        self.assertEqual(res["watchdog_health"], "HEALTHY")
        self.assertTrue(res["agent1_execution_engine_online"])
        self.assertEqual(res["active_order_count"], 3)
        self.assertEqual(res["excessive_drift_orders"], [])
        self.assertEqual(res["order_integrity_issues"], [])
        self.assertEqual(res["stale_data_alerts"], [])
        self.assertFalse(res["circuit_breaker_status"]["kill_switch_tripped"])
        self.assertEqual(client.cancelled_orders, [])
        self.assertTrue(self.status_path.exists())

    def test_healthy_tp_sell_within_band(self) -> None:
        client = FakeCryptoComClient()
        client.open_orders = [{
            "order_id": "777001",
            "side": "SELL",
            "exec_inst": ["POST_ONLY"],
            "time_in_force": "GOOD_TILL_CANCEL",
            "quantity": "687",
            "limit_price": "0.04430",
            "cumulative_fee": "0",
            "status": "ACTIVE",
        }]

        with patch.object(self.watchdog, "check_trader_telemetry", return_value=self._fresh_telemetry()):
            res = self.watchdog.run_watchdog_cycle(client, self.ctx, self.log)

        self.assertEqual(res["watchdog_health"], "HEALTHY")
        self.assertEqual(res["excessive_drift_orders"], [])
        self.assertEqual(res["order_integrity_issues"], [])

    def test_degraded_when_telemetry_offline_but_exchange_reachable(self) -> None:
        client = FakeCryptoComClient()
        _seed_three_tranches(client)

        with patch.object(self.watchdog, "check_trader_telemetry", return_value={}):
            res = self.watchdog.run_watchdog_cycle(client, self.ctx, self.log)

        self.assertEqual(res["watchdog_health"], "DEGRADED")
        self.assertFalse(res["agent1_execution_engine_online"])
        self.assertEqual(res["active_order_count"], 3)
        self.assertAlmostEqual(res["current_mid_price"], 0.04387, places=5)

    def test_critical_on_non_post_only_or_drawdown(self) -> None:
        client = FakeCryptoComClient()
        _seed_three_tranches(client)
        client.open_orders[0]["exec_inst"] = []
        client.open_orders[0]["cumulative_fee"] = "0.05"

        with patch.object(self.watchdog, "check_trader_telemetry", return_value=self._fresh_telemetry()):
            res = self.watchdog.run_watchdog_cycle(client, self.ctx, self.log)

        self.assertEqual(res["watchdog_health"], "CRITICAL")
        self.assertEqual(len(res["order_integrity_issues"]), 2)
        self.assertEqual(client.cancelled_orders, [])

        # Reset integrity, simulate $3.50 equity drawdown
        client.open_orders[0]["exec_inst"] = ["POST_ONLY"]
        client.open_orders[0]["cumulative_fee"] = "0"
        self.ctx["last_equity_check_ts"] = 0.0
        client.balances["USDT"]["total"] = Decimal("92.20")
        with patch.object(self.watchdog, "check_trader_telemetry", return_value=self._fresh_telemetry()):
            res2 = self.watchdog.run_watchdog_cycle(client, self.ctx, self.log)

        self.assertEqual(res2["watchdog_health"], "CRITICAL")
        self.assertTrue(res2["circuit_breaker_status"]["kill_switch_tripped"])
        self.assertEqual(client.cancelled_orders, [])


class TestIPv4HTTPSConnectionTimeout(unittest.TestCase):
    def setUp(self) -> None:
        self.trader = _load_module("live_cro_usdt_trader", r"C:\AI-BS\scratch\live_cro_usdt_trader.py")

    def test_ipv4_https_connection_times_out_on_stalled_socket(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        accepted_conns: list[socket.socket] = []
        stop_evt = threading.Event()

        def _stall_peer() -> None:
            srv.settimeout(2.0)
            try:
                cli, _ = srv.accept()
                accepted_conns.append(cli)
                stop_evt.wait(timeout=3.0)
            except OSError:
                pass

        t = threading.Thread(target=_stall_peer, daemon=True)
        t.start()
        ctx = ssl.create_default_context()
        conn = self.trader.IPv4HTTPSConnection("127.0.0.1", port=port, timeout=0.25, context=ctx)
        t0 = time.monotonic()
        try:
            with self.assertRaises((TimeoutError, socket.timeout)):
                conn.connect()
            elapsed = time.monotonic() - t0
            self.assertLess(elapsed, 2.0)
        finally:
            stop_evt.set()
            conn.close()
            for c in accepted_conns:
                try:
                    c.close()
                except OSError:
                    pass
            srv.close()
            t.join(timeout=1.0)

    def test_ipv4_https_connection_sets_timeout_before_connect_and_falls_back(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(2)
        port = srv.getsockname()[1]
        accepted_conns: list[socket.socket] = []

        def _accept_loop() -> None:
            srv.settimeout(2.0)
            for _ in range(2):
                try:
                    cli, _ = srv.accept()
                    accepted_conns.append(cli)
                except OSError:
                    break

        t = threading.Thread(target=_accept_loop, daemon=True)
        t.start()

        call_log: list[tuple[str, object]] = []
        real_socket_cls = socket.socket

        class _SpySocket(real_socket_cls):
            def settimeout(self, value):
                call_log.append(("settimeout", value))
                return super().settimeout(value)

            def connect(self, address):
                call_log.append(("connect", address))
                return super().connect(address)

        class _PassThroughContext:
            def wrap_socket(self, sock, server_hostname=None):
                return sock

        try:
            # 1. Explicit finite timeout enforced before connect()
            conn_explicit = self.trader.IPv4HTTPSConnection(
                "127.0.0.1", port=port, timeout=0.35, context=_PassThroughContext()
            )
            with patch.object(self.trader.socket, "socket", side_effect=lambda *a, **kw: _SpySocket(*a, **kw)):
                conn_explicit.connect()
            try:
                self.assertEqual(call_log[:2], [("settimeout", 0.35), ("connect", ("127.0.0.1", port))])
                self.assertAlmostEqual(conn_explicit.sock.gettimeout(), 0.35, places=3)
            finally:
                conn_explicit.close()

            # 2. Fallback to finite DEFAULT_CONNECT_TIMEOUT when timeout is None / default
            call_log.clear()
            conn_default = self.trader.IPv4HTTPSConnection(
                "127.0.0.1", port=port, timeout=None, context=_PassThroughContext()
            )
            with patch.object(self.trader.socket, "socket", side_effect=lambda *a, **kw: _SpySocket(*a, **kw)), \
                 patch.object(self.trader.socket, "getdefaulttimeout", return_value=None):
                conn_default.connect()
            try:
                expected_fallback = self.trader.IPv4HTTPSConnection.DEFAULT_CONNECT_TIMEOUT
                self.assertEqual(call_log[:2], [("settimeout", expected_fallback), ("connect", ("127.0.0.1", port))])
                self.assertAlmostEqual(conn_default.sock.gettimeout(), expected_fallback, places=3)
            finally:
                conn_default.close()
        finally:
            for c in accepted_conns:
                try:
                    c.close()
                except OSError:
                    pass
            srv.close()
            t.join(timeout=1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
