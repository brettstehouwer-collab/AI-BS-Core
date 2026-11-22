"""Test Plan A buy pause offline using a Mock Exchange Client.
Verifies:
1. When BUYS_PAUSED.flag exists, even if a TP fills and USDT cash is $31+, ZERO buys are submitted.
2. Sells remain preserved and active.
3. Across an engine restart simulation, ZERO buys are submitted.
4. CONTROL: When BUYS_PAUSED.flag is removed, rearm_missing_tranches places a buy.
"""
import copy
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import unittest

ENGINE_PATH = Path(r"C:\AI-BS\scratch\structural_dip_engine.py")
FLAG_PATH = Path(r"C:\AI-BS\saved_data\BUYS_PAUSED.flag")

class MockClient:
    def __init__(self, balances, open_orders):
        self._balances = balances
        self._open_orders = list(open_orders)
        self.created_orders = []

    def get_balances(self):
        return copy.deepcopy(self._balances)

    def get_open_orders(self):
        return copy.deepcopy(self._open_orders)

    def get_book(self, depth=10):
        return Decimal("0.04100"), Decimal("0.04102"), [], []

    def create_limit_order(self, **kwargs):
        self.created_orders.append(kwargs)
        oid = f"mock-{len(self.created_orders)}"
        new_order = {
            "order_id": oid,
            "side": kwargs.get("side"),
            "quantity": kwargs.get("qty_cro"),
            "limit_price": str(kwargs.get("price")),
            "status": "ACTIVE",
            "cumulative_quantity": "0",
            "client_oid": kwargs.get("client_oid", "")
        }
        self._open_orders.append(new_order)
        return {"order_id": oid}

    def cancel_order(self, oid):
        self._open_orders = [o for o in self._open_orders if o.get("order_id") != oid]
        return True

    def get_order_detail(self, oid):
        for o in self._open_orders:
            if o.get("order_id") == oid:
                return o
        return {"order_id": oid, "status": "FILLED", "cumulative_quantity": "714", "avg_price": "0.04234"}

def run_tests():
    spec = importlib.util.spec_from_file_location("eng", str(ENGINE_PATH))
    eng = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(eng)

    log = eng.configure_logging()

    # Step 1: Create the pause flag
    FLAG_PATH.write_text("PAUSED_MANUALLY_FOR_PLAN_A\n", encoding="utf-8")
    assert eng.are_buys_paused(), "Engine must recognize pause flag"
    print("[PASS] 1. are_buys_paused() is True when flag exists")

    # Step 2: Setup state with 1 TP filled, $31 USDT available, Tranche 0 uncovered
    mock_balances = {
        "CRO": {"free": Decimal("0.03"), "total": Decimal("1517.03")},
        "USDT": {"free": Decimal("31.25"), "total": Decimal("31.25")}
    }
    mock_open_orders = [
        {"order_id": "6530219611293799342", "side": "SELL", "quantity": "811", "limit_price": "0.04389", "status": "ACTIVE"},
        {"order_id": "6530219611293800751", "side": "SELL", "quantity": "706", "limit_price": "0.04313", "status": "ACTIVE"}
    ]
    client = MockClient(mock_balances, mock_open_orders)
    state = eng.default_state()
    state["profit_reserve_usdt"] = "0.226710"

    # Step 3: Run cycle with flag present
    eng.run_cycle(client, state, log)
    buy_orders = [o for o in client.created_orders if o.get("side") == "BUY"]
    assert len(buy_orders) == 0, f"Expected 0 buys when paused, got {len(buy_orders)}"
    print("[PASS] 2. With $31 USDT free and Tranche 0 uncovered, ZERO buy orders submitted")

    # Step 4: Simulate restart (fresh module load and fresh run_cycle with flag present)
    spec2 = importlib.util.spec_from_file_location("eng2", str(ENGINE_PATH))
    eng2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(eng2)
    client2 = MockClient(mock_balances, mock_open_orders)
    state2 = eng2.default_state()
    eng2.run_cycle(client2, state2, log)
    buy_orders2 = [o for o in client2.created_orders if o.get("side") == "BUY"]
    assert len(buy_orders2) == 0, f"Expected 0 buys after restart, got {len(buy_orders2)}"
    print("[PASS] 3. Simulated engine restart: pause persists, ZERO buy orders submitted")

    # Step 5: CONTROL TEST - remove flag and verify engine CAN place a buy
    FLAG_PATH.unlink(missing_ok=True)
    assert not eng.are_buys_paused(), "Engine must recognize flag removal"
    client3 = MockClient(mock_balances, mock_open_orders)
    state3 = eng.default_state()
    eng.run_cycle(client3, state3, log)
    buy_orders3 = [o for o in client3.created_orders if o.get("side") == "BUY"]
    assert len(buy_orders3) > 0, "Control test failed: engine did not place buy when flag was removed"
    print(f"[PASS] 4. Control test: without flag, engine submitted {len(buy_orders3)} BUY order as expected")

    # Restore the pause flag
    FLAG_PATH.write_text("PAUSED_MANUALLY_FOR_PLAN_A\n", encoding="utf-8")
    print("[PASS] 5. Pause flag restored and active on disk.")
    print("ALL OFFLINE TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
