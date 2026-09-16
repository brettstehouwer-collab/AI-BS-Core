import asyncio
import time

import ccxt
from ccxt.base.errors import NetworkError
from crypto_trader_bot import process_twap_tick

class MockExchange:
    def __init__(self):
        self.network_error_count = 0
        self.success_count = 0

    async def fetch_ticker(self, symbol):
        if self.network_error_count > 0:
            self.network_error_count -= 1
            raise NetworkError(f"Simulated network outage for {symbol} on fetch_ticker")
        return {"last": 100.0}

    def amount_to_precision(self, symbol, amount):
        return str(round(amount, 4))

    async def create_market_buy_order(self, symbol, amount):
        if self.network_error_count > 0:
            self.network_error_count -= 1
            raise NetworkError(f"Simulated network outage for {symbol} on order creation")
        self.success_count += 1
        return {"id": "mock_order_123", "status": "closed"}



async def test_twap_queue_network_outage_resilience():
    exchange = MockExchange()
    # Force 2 network errors
    exchange.network_error_count = 2

    # Initialize fake ledger
    initial_usd = 1000.0
    now = time.time()
    
    # We set last_drip_time in the past to trigger an immediate drip
    ledger = {
        "positions": {},
        "twap_orders": [
            {
                "symbol": "BTC/USD",
                "total_usd": initial_usd,
                "remaining_usd": initial_usd,
                "drip_size_usd": 100.0,
                "drip_interval_seconds": 60,
                "last_drip_time": now - 120 # Trigger immediately
            }
        ]
    }

    # First tick: should encounter fetch_ticker NetworkError
    modified, updated_ledger = await process_twap_tick(exchange, ledger)
    
    # The queue should remain intact and remaining_usd unchanged
    assert not modified # We failed before modifying remaining_usd
    assert updated_ledger["twap_orders"][0]["remaining_usd"] == 1000.0
    
    # Second tick: network is restored but we mock order creation failure manually if needed.
    # Actually, the first tick consumed one network_error_count (fetch_ticker)
    # The second tick will consume the second network_error_count (fetch_ticker again)
    modified, updated_ledger = await process_twap_tick(exchange, ledger)
    assert not modified
    assert updated_ledger["twap_orders"][0]["remaining_usd"] == 1000.0
    
    # Third tick: network is fully restored (0 errors left)
    assert exchange.network_error_count == 0
    modified, updated_ledger = await process_twap_tick(exchange, ledger)
    
    # The drip should execute successfully
    assert modified
    assert updated_ledger["twap_orders"][0]["remaining_usd"] == 900.0
    assert exchange.success_count == 1
    
    print("TWAP Queue Resilience Test Passed.")

if __name__ == "__main__":
    asyncio.run(test_twap_queue_network_outage_resilience())
