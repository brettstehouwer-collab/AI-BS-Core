"""Offline audit regression tests: no daemon imports, real databases or exchanges."""
import ast
import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


safety = load("backend/core/crypto_execution_safety.py", "audit_safety")
ledger_io = load("backend/core/crypto_ledger_io.py", "audit_ledger_io")


class CryptoContainmentTests(unittest.TestCase):
    def test_dispatch_never_touches_exchange(self):
        class Exchange:
            def __getattribute__(self, key):
                raise AssertionError("Exchange accessed during reconciliation hold")
        for amount in (1, -1, float("nan"), float("inf")):
            with self.subTest(amount=amount), self.assertRaises(safety.CryptoDispatchBlocked):
                asyncio.run(safety.execute_trade_protocol(Exchange(), "CRO/USD", "buy", amount))

    def test_missing_or_corrupt_halt_state_cannot_activate(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "halt.json"
            with patch.object(safety, "HALT_FILE", marker):
                self.assertFalse(safety.execution_status()["dispatch_enabled"])
                marker.write_text("corrupt")
                with self.assertRaises(safety.CryptoDispatchBlocked):
                    safety.require_reconciled_execution()

    def test_operator_halt_is_durable(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "halt.json"
            with patch.object(safety, "HALT_FILE", marker):
                self.assertFalse(safety.halt_trading()["dispatch_enabled"])
                self.assertEqual(json.loads(marker.read_text(encoding="utf-8")), {"halted": True, "reason": "operator_halt"})

    def test_halt_failure_propagates(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(safety, "HALT_FILE", Path(directory) / "halt.json"), patch.object(safety.os, "replace", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    safety.halt_trading()

    def test_corrupt_or_missing_ledger_is_not_an_empty_portfolio(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "ledger.json"
            for raw in (None, b"\0" * 811, b"{}", b'{"positions":{"CRO/USD":{"amount":NaN}}}'):
                if raw is not None:
                    p.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(ledger_io.LedgerIntegrityError):
                    ledger_io.read_ledger(p)
                if raw is not None:
                    self.assertEqual(p.read_bytes(), raw)

    def test_failed_save_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "ledger.json"
            p.write_text('{"positions":{}}')
            before = p.read_bytes()
            with patch.object(ledger_io.os, "replace", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    ledger_io.write_ledger(p, {"positions": {}, "last_action": "intent"})
            self.assertEqual(p.read_bytes(), before)

    def test_valid_roundtrip_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "ledger.json"
            data = {"positions": {"CRO/USD": {"amount": 1.25, "avg_buy_price": 0.1}}}
            ledger_io.write_ledger(p, data)
            self.assertEqual(ledger_io.read_ledger(p), data)
            for bad in (-1, True, "1", float("inf"), 10 ** 1000):
                with self.subTest(bad=bad), self.assertRaises(ledger_io.LedgerIntegrityError):
                    ledger_io.write_ledger(p, {"positions": {"CRO/USD": {"amount": bad}}})

    def test_daemon_all_order_sites_use_closed_protocol(self):
        source = (ROOT / "backend/crypto_trader_bot.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        direct = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute) and n.func.attr.startswith(("create_market_", "create_limit_", "create_order"))]
        self.assertEqual(direct, [])
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "execute_trade_protocol"]
        self.assertEqual(len(calls), 8)
        posts = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == "app" and n.func.attr == "post"]
        self.assertTrue(posts)
        for call in posts:
            self.assertIn("reject_crypto_mutation", ast.unparse(call))
        self.assertIn('host="127.0.0.1"', source)
        self.assertIn('port=8007', source)

    def test_liveness_and_telemetry_make_no_exchange_calls(self):
        tree = ast.parse((ROOT / "backend/crypto_trader_bot.py").read_text(encoding="utf-8"))
        for name in ("healthz", "get_telemetry"):
            node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
            self.assertNotIn("fetch_balance", ast.unparse(node))
        health = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "healthz")
        self.assertNotIn("load_ledger", ast.unparse(health))

    def test_paper_simulation_refuses_canonical_storage(self):
        paper = load("Crypto-Swarm/drip_trader_daemon.py", "audit_paper")
        with self.assertRaises(RuntimeError):
            paper.process_active_twap_orders()
        with self.assertRaises(ValueError):
            paper.configure_paper_storage(ROOT / "Crypto-Swarm")

    def test_paper_execution_only_writes_temporary_fixture(self):
        paper = load("Crypto-Swarm/drip_trader_daemon.py", "audit_paper_fixture")
        with tempfile.TemporaryDirectory() as directory:
            paper.configure_paper_storage(directory)
            plan = paper.create_twap_order(num_slices=1)
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(paper.DB_PATH)) as conn, conn:
                conn.execute("UPDATE twap_plans SET next_slice_time=0 WHERE plan_id=?", (plan,))
            self.assertEqual(paper.process_active_twap_orders(), 1)
            self.assertEqual(paper.get_twap_status()["recent_orders"][0]["status"], "PAPER_FILLED")
            paper.DB_PATH = str(ROOT / "Crypto-Swarm/trade_queue.db")
            with self.assertRaises(RuntimeError):
                paper.init_db()

    def test_mutation_routes_reject_before_body_or_credentials(self):
        # Execute just the route function AST, without importing applications/DB modules.
        class HTTPError(Exception):
            def __init__(self, status_code, detail):
                self.status_code = status_code
                self.detail = detail
        for relative, names in (
            ("backend/commercial_gateway/crypto_control_router.py", ("force_swap", "set_parameters")),
            ("backend/routers/trading_router.py", ("execute_trade_order", "execute_kraken_order")),
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for name in names:
                node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
                node.decorator_list = []
                for arg in node.args.args:
                    arg.annotation = None
                scope = {"HTTPException": HTTPError, "execution_status": safety.execution_status}
                exec(compile(ast.Module(body=[node], type_ignores=[]), relative, "exec"), scope)
                # No request attributes, env, exchange or DB names are available.
                with self.subTest(route=name), self.assertRaises(HTTPError) as error:
                    asyncio.run(scope[name](object()))
                self.assertEqual(error.exception.status_code, 503)

    def test_alternate_sinks_are_contained_without_fabricated_fills(self):
        for relative in ("Crypto-Swarm/internal/daemons/trade_engine.go", "Crypto-Swarm/cryptoswarm-desktop/internal/daemons/trade_engine.go"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("func cryptoLiveDispatchBlocked() bool { return true }", source)
            self.assertNotIn("falling back to paper trade", source)
        source = (ROOT / "backend/core/executive_action_dispatcher.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        handler = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_exec_crypto_order")
        self.assertNotIn("INSERT", ast.unparse(handler))
        kraken = ast.parse((ROOT / "backend/core/kraken_service.py").read_text(encoding="utf-8"))
        create = next(n for n in ast.walk(kraken) if isinstance(n, ast.FunctionDef) and n.name == "create_order")
        self.assertIn("require_reconciled_execution()", ast.unparse(create))


if __name__ == "__main__":
    unittest.main()
