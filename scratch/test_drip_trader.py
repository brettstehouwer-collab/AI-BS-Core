import unittest
from pathlib import Path
import drip_trader_daemon


class TestDripTrader(unittest.TestCase):
    def setUp(self):
        # Create a temporary dummy ledger for testing
        self.test_ledger = Path("test_ledger.json")
        drip_trader_daemon.LEDGER_FILE = self.test_ledger

    def tearDown(self):
        if self.test_ledger.exists():
            self.test_ledger.unlink()

    def test_module_imports(self):
        """Validates that all external dependencies load correctly."""
        self.assertIsNotNone(drip_trader_daemon.ccxt)
        self.assertIsNotNone(drip_trader_daemon.chromadb)

    def test_ledger_initialization(self):
        """Validates ledger I/O logic."""
        if self.test_ledger.exists():
            self.test_ledger.unlink()

        # Should initialize a blank ledger
        ledger = drip_trader_daemon.load_ledger()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger["total_usd_invested"], 0.0)
        self.assertEqual(len(ledger["trades"]), 0)

        # Save it
        drip_trader_daemon.save_ledger(ledger)
        self.assertTrue(self.test_ledger.exists())

        # Load it again
        ledger2 = drip_trader_daemon.load_ledger()
        self.assertEqual(ledger2["total_usd_invested"], 0.0)


if __name__ == "__main__":
    unittest.main()
