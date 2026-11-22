import csv
import io
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from modules import personal_ledger_export as ledger


class PersonalLedgerExportTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'AI_BS_ADMIN_KEY': 'fixture-ledger-key',
                                          'AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT': '1'})
        self.env.start()
        self.rows = [{'id': 1, 'date': '2026-11-14', 'entry_type': 'income', 'amount': '123.45',
                      'currency': 'USD', 'category': 'Manual payment', 'description': 'Original, note',
                      'receipt_note': 'Original evidence reference'}]
        self.seen = []
        self.app = FastAPI()
        ledger.register_personal_ledger(self.app)
        def reader(owner, kind):
            self.seen.append((owner, kind))
            return self.rows
        self.app.dependency_overrides[ledger.ledger_reader] = lambda: reader
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def get(self, year=2026, headers=None):
        return self.client.get(f'/api/personal-finance/ledger/{year}.csv',
                               headers={'X-Admin-Key': 'fixture-ledger-key'} if headers is None else headers)

    def parsed(self, response):
        return list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))

    def test_01_default_disabled(self):
        with patch.dict(os.environ, {'AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT': '0'}):
            app = FastAPI()
            self.assertFalse(ledger.register_personal_ledger(app))
            self.assertFalse(any('personal-finance' in route.path for route in app.routes))

    def test_02_anonymous_denied(self):
        self.assertEqual(self.get(headers={}).status_code, 403)
        self.assertFalse(self.seen)

    def test_03_shared_pin_denied(self):
        self.assertEqual(self.get(headers={'X-FE-PIN': 'fixture-pin'}).status_code, 403)
        self.assertFalse(self.seen)

    def test_04_owner_comes_from_verified_boundary(self):
        self.assertEqual(self.get().status_code, 200)
        self.assertEqual(self.seen, [('local_admin', 'entry')])

    def test_05_year_filter(self):
        self.rows.append({**self.rows[0], 'id': 2, 'date': '2025-12-31'})
        self.assertEqual(len(self.parsed(self.get())), 1)

    def test_06_exact_money_and_original_text(self):
        row = self.parsed(self.get())[0]
        self.assertEqual(row['amount'], '123.45')
        self.assertEqual(row['description'], 'Original, note')

    def test_07_no_inferred_tax_classification(self):
        row = self.parsed(self.get())[0]
        self.assertEqual(row['verification'], 'manual_unreconciled')
        self.assertEqual(row['user_recorded_tax_flag'], 'false')

    def test_08_formula_cells_are_inert(self):
        self.rows[0]['description'] = '=HYPERLINK("https://invalid.test")'
        self.assertTrue(self.parsed(self.get())[0]['description'].startswith("'="))

    def test_09_invalid_money_fails_whole_export(self):
        self.rows.append({**self.rows[0], 'id': 2, 'amount': '1.234'})
        response = self.get()
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('Original evidence reference', response.text)

    def test_10_invalid_date_fails_visible(self):
        self.rows[0]['date'] = 'not-a-date'
        self.assertEqual(self.get().status_code, 409)

    def test_11_private_download_headers(self):
        response = self.get()
        self.assertEqual(response.headers['cache-control'], 'private, no-store')
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertIn('personal-ledger-2026.csv', response.headers['content-disposition'])

    def test_12_empty_and_invalid_year(self):
        self.rows.clear()
        self.assertEqual(self.parsed(self.get()), [])
        self.assertEqual(self.get(0).status_code, 422)


if __name__ == '__main__':
    unittest.main(verbosity=2)
