"""Native crypto presentation against isolated synthetic records; no live requests."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing
from decimal import Decimal
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication, QLabel
from native_studio import crypto_swarm_view as view


class QueuedBus:
    def __init__(self):
        self.jobs = []
        self.events = []

    def dispatch(self, fn, *args, callback=None, on_result=None, on_error=None, **kwargs):
        self.jobs.append((fn, args, kwargs, callback or on_result, on_error))

    def emit_event(self, *args):
        self.events.append(args)

    def finish(self, index, value):
        self.jobs[index][3](value)


class CryptoTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('AI_BS_TEST_ROOT'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'ledger.db'
        self.bus = QueuedBus()

    def make_ledger(self, rows=()):
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('CREATE TABLE trades(id INTEGER PRIMARY KEY,timestamp TEXT,type TEXT,coin_amount TEXT,coin_price TEXT,usd_value TEXT)')
            db.executemany('INSERT INTO trades VALUES(?,?,?,?,?,?)', rows)
            db.commit()
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def widget(self):
        # Explicit fixture paths: no operational SQLite database is opened.
        result = view.CryptoSwarmNativeView(self.bus, ledger_paths=[self.db])
        self.addCleanup(result.close)
        self.addCleanup(result.shutdown)
        return result

    def text(self, card):
        return card.findChild(QLabel, 'ValLabel').text()

    def test_initial_quotes_and_metrics_are_unavailable_and_dispatch_held(self):
        widget = self.widget()
        for card in [widget.card_btc, widget.card_eth, widget.card_sol, widget.card_kas, widget.card_clore,
                     widget.card_trade_count, widget.card_volume]:
            self.assertIn('Unavailable', self.text(card))
        self.assertIn('HELD', self.text(widget.card_scalper_state))
        self.assertFalse(widget.btn_pause.isEnabled())

    def test_programmatic_legacy_toggle_cannot_claim_or_request_live_resume(self):
        widget = self.widget()
        widget._toggle_scalper()
        widget._toggle_scalper()
        self.assertIn('HELD', self.text(widget.card_scalper_state))
        self.assertNotIn('ACTIVE', self.text(widget.card_scalper_state))
        self.assertFalse(widget.btn_pause.isEnabled())
        self.assertEqual(self.bus.events, [])

    def test_missing_ledger_remains_missing_and_unavailable(self):
        result = view.read_recorded_trades([self.db])
        self.assertEqual(result['status'], 'unavailable')
        self.assertFalse(self.db.exists())

    def test_sqlite_facts_use_decimal_and_remain_byte_identical(self):
        self.make_ledger([(1, '2026-10-30T00:00:00Z', 'BUY', '0.000000019', '10', '0.1'),
                          (2, '2026-10-31T00:00:00Z', 'SELL', '0.000000011', '20', '0.2')])
        before = self.db.read_bytes()
        result = view.read_recorded_trades([self.db])
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['displayed_usd'], Decimal('0.3'))
        self.assertEqual(result['rows'][0]['amount'], Decimal('0.000000011'))
        self.assertEqual(result['source'], 'ledger.db')
        self.assertFalse(result['execution_verified'])
        self.assertEqual(self.db.read_bytes(), before)
        with closing(sqlite3.connect(self.db.as_uri() + '?mode=ro', uri=True)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_unknown_schema_and_nonfinite_record_are_unavailable(self):
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('CREATE TABLE unrelated(value TEXT)')
            db.commit()
        self.assertEqual(view.read_recorded_trades([self.db])['status'], 'unavailable')
        self.db.unlink()
        self.make_ledger([(1, 'today', 'BUY', 'NaN', '1', '1')])
        self.assertEqual(view.read_recorded_trades([self.db])['status'], 'unavailable')

    def test_quote_validation_never_displays_nan_infinity_negative_or_missing_as_real(self):
        widget = self.widget()
        widget._apply_quotes({'bitcoin': {'usd': Decimal('123.4500')}, 'ethereum': {'usd': float('nan')},
                              'solana': {'usd': Decimal('Infinity')}, 'kaspa': {'usd': -1}})
        self.assertIn('123.45', self.text(widget.card_btc))
        for card in [widget.card_eth, widget.card_sol, widget.card_kas, widget.card_clore]:
            self.assertIn('Unavailable', self.text(card))

    def test_quote_requests_do_not_overlap_and_failures_clear_unverified_values(self):
        widget = self.widget()
        quote_jobs = len(self.bus.jobs)
        widget._fetch_market_prices()
        self.assertEqual(len(self.bus.jobs), quote_jobs)
        quote_index = next(i for i, item in enumerate(self.bus.jobs) if item[0] == view.fetch_public_quotes)
        self.bus.finish(quote_index, None)
        self.assertIn('Unavailable', self.text(widget.card_btc))
        widget._fetch_market_prices()
        self.assertEqual(len(self.bus.jobs), quote_jobs + 1)

    def test_recorded_rows_are_not_labeled_on_chain_or_24_hour_activity(self):
        self.make_ledger([(1, 'old-record', 'BUY', '1.123456789', '10', '11.23456789')])
        widget = self.widget()
        result = view.read_recorded_trades([self.db])
        widget._apply_ledger(result)
        self.assertEqual(widget.table.rowCount(), 1)
        self.assertEqual(widget.table.item(0, 3).text(), '1.123456789')
        self.assertIn('ledger.db', widget.ledger_status.text())
        labels = '\n'.join(item.text() for item in widget.findChildren(QLabel))
        self.assertNotIn('ON-CHAIN', labels)
        self.assertNotIn('24H VOLUME', labels)

    def test_unavailable_ledger_result_is_not_fabricated_zero_execution(self):
        widget = self.widget()
        widget._apply_ledger({'status': 'unavailable', 'reason': 'Missing or unsupported ledger.'})
        self.assertIn('Unavailable', self.text(widget.card_trade_count))
        self.assertIn('Unavailable', self.text(widget.card_volume))
        self.assertEqual(widget.table.rowCount(), 0)

    def test_closed_widget_ignores_inflight_callbacks(self):
        widget = self.widget()
        widget.shutdown()
        widget._apply_quotes({'bitcoin': {'usd': 1}})
        widget._apply_ledger({'status': 'unavailable', 'reason': 'Unavailable'})
        self.assertFalse(widget.timer.isActive())
        self.assertIn('Unavailable', self.text(widget.card_btc))

    def test_quote_payload_must_be_small_and_https_provider_response(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def geturl(self): return 'https://api.coingecko.com/api/v3/simple/price'
            def read(self, count): return b'x' * count
        with patch.object(view.urllib.request, 'urlopen', return_value=Response()):
            self.assertIsNone(view.fetch_public_quotes())

    def test_quote_parser_preserves_provider_decimal_and_rejects_redirected_host(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def geturl(self): return 'https://api.coingecko.com/api/v3/simple/price'
            def read(self, count): return b'{"bitcoin":{"usd":0.123456789123456789}}'
        with patch.object(view.urllib.request, 'urlopen', return_value=Response()):
            self.assertEqual(view.fetch_public_quotes()['bitcoin']['usd'], Decimal('0.123456789123456789'))
        with patch.object(Response, 'geturl', return_value='https://unrelated.example/'), \
                patch.object(view.urllib.request, 'urlopen', return_value=Response()):
            self.assertIsNone(view.fetch_public_quotes())

    def test_empty_existing_ledger_is_distinct_from_unavailable(self):
        self.make_ledger()
        data = view.read_recorded_trades([self.db])
        self.assertEqual(data['status'], 'available')
        self.assertEqual(data['rows'], [])
        self.assertEqual(data['displayed_usd'], Decimal(0))

    def test_ledger_page_and_numeric_formatting_are_bounded(self):
        for invalid in [0, 101, True, '100']:
            with self.assertRaises(ValueError):
                view.read_recorded_trades([self.db], limit=invalid)
        self.make_ledger([(1, 'today', 'BUY', '1E1000000', '1', '1')])
        self.assertEqual(view.read_recorded_trades([self.db])['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
