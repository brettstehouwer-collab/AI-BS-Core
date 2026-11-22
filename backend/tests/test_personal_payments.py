import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from modules import accounting_router as accounting, personal_payments as payments
from security import firebase_auth


class PersonalPaymentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'fixture.db'
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('CREATE TABLE legacy_original(value TEXT)')
            conn.execute("INSERT INTO legacy_original VALUES('original fixture')")
        self.patches = [patch.object(accounting, 'DB_PATH', str(self.path)),
                        patch.dict(os.environ, {'AI_BS_ENABLE_PERSONAL_PAYMENTS': '1',
                                                'AI_BS_ADMIN_KEY': 'fixture-payment-key',
                                                'AI_BS_ADMIN_EMAILS': 'fixture@example.invalid'}),
                        patch.object(firebase_auth, '_token_cache', {}),
                        patch.object(firebase_auth, '_request', object()),
                        patch.object(firebase_auth, 'id_token', SimpleNamespace(verify_firebase_token=self.verify))]
        for item in self.patches:
            item.start()
        self.app = FastAPI()
        payments.register_personal_payments(self.app)
        self.client = TestClient(self.app)
        self.headers = {'X-Admin-Key': 'fixture-payment-key', 'Idempotency-Key': 'fixture-operation'}
        self.payload = dict(payment_date='2026-11-14', week_start='2026-11-02', amount='123.45',
                            payer='Fixture payer', source='Manual transfer', notes='Original note',
                            load_references=['load-fixture'], evidence_references=['document-not-yet-uploaded'])

    @staticmethod
    def verify(token, request, audience):
        if token not in ('fixture-a', 'fixture-b'):
            raise ValueError('Invalid synthetic token')
        return {'email': 'fixture@example.invalid', 'email_verified': True, 'sub': token,
                'exp': time.time() + 60}

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def post(self, payload=None, headers=None):
        return self.client.post('/api/personal-finance/payments', json=self.payload if payload is None else payload,
                                headers=self.headers if headers is None else headers)

    def get(self, suffix='', headers=None):
        return self.client.get('/api/personal-finance/payments' + suffix,
                               headers=self.headers if headers is None else headers)

    def test_01_disabled_default_no_database_writes(self):
        before = self.path.read_bytes()
        with patch.dict(os.environ, {'AI_BS_ENABLE_PERSONAL_PAYMENTS': ''}):
            app = FastAPI()
            self.assertFalse(payments.register_personal_payments(app))
            self.assertFalse(any('personal-finance' in r.path for r in app.routes))
        self.assertEqual(before, self.path.read_bytes())

    def test_02_authentication_and_pin_denied(self):
        before = self.path.read_bytes()
        for headers in ({}, {'X-FE-PIN': 'fixture'}, {'Authorization': 'Bearer invalid'}):
            self.assertEqual(self.post(headers=headers).status_code, 403)
            self.assertEqual(self.get(headers=headers).status_code, 403)
        self.assertEqual(before, self.path.read_bytes())

    def test_03_append_exact_text_and_private_headers(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        result = self.get()
        self.assertEqual(result.headers['cache-control'], 'private, no-store')
        row = result.json()['payments'][0]
        self.assertEqual(row['amount'], '123.45')
        self.assertEqual(row['notes'], 'Original note')
        self.assertEqual(row['load_references'], ['load-fixture'])

    def test_04_required_idempotency_and_replay(self):
        self.assertEqual(self.post(headers={'X-Admin-Key': 'fixture-payment-key'}).status_code, 422)
        first = self.post().json()
        self.assertEqual(first, self.post().json())
        self.assertEqual(self.get().json()['count'], 1)
        self.assertEqual(self.post(headers={**self.headers, 'Idempotency-Key': 'bad key'}).status_code, 422)

    def test_05_changed_replay_is_conflict_preserves_original(self):
        self.post()
        response = self.post({**self.payload, 'amount': '1.00'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.get().json()['recorded_total'], '123.45')

    def test_06_money_validation_no_float_or_zero(self):
        for amount in (123.45, '1.234', '-1.00', '0.00', '01.00', 'NaN'):
            self.assertEqual(self.post({**self.payload, 'amount': amount}).status_code, 422)
        self.assertEqual(self.get().json()['count'], 0)

    def test_07_strict_schema_prevents_owner_update_and_classification(self):
        for field, value in (('owner', 'someone'), ('id', 1), ('is_tax_deductible', True), ('currency', 'EUR')):
            self.assertEqual(self.post({**self.payload, field: value}).status_code, 422)
        self.assertEqual(self.get().json()['count'], 0)

    def test_08_verified_owner_isolation(self):
        a = {'Authorization': 'Bearer fixture-a', 'Idempotency-Key': 'same-key'}
        b = {'Authorization': 'Bearer fixture-b', 'Idempotency-Key': 'same-key'}
        self.assertEqual(self.post(headers=a).status_code, 201)
        self.assertEqual(self.get(headers=b).json()['count'], 0)
        self.assertEqual(self.post({**self.payload, 'amount': '1.00'}, headers=b).status_code, 201)
        self.assertEqual(self.get(headers=a).json()['recorded_total'], '123.45')
        self.assertEqual(self.get(headers=b).json()['recorded_total'], '1.00')
        self.assertEqual(self.get().json()['count'], 0)

    def test_09_explicit_week_allocation_and_exact_total(self):
        self.post()
        self.post({**self.payload, 'amount': '0.10'}, {**self.headers, 'Idempotency-Key': 'two'})
        self.post({**self.payload, 'amount': '9.00', 'week_start': '2026-11-09'},
                  {**self.headers, 'Idempotency-Key': 'three'})
        result = self.get('?week_start=2026-11-02').json()
        self.assertEqual((result['count'], result['recorded_total'], result['week_end']), (2, '123.55', '2026-11-08'))
        self.assertEqual(self.get('?week_start=invalid').status_code, 422)

    def test_10_date_and_reference_bounds(self):
        for changes in ({'payment_date': '2026-02-30'}, {'week_start': '20261102'},
                        {'load_references': ['same', 'same']}, {'evidence_references': ['']},
                        {'load_references': ['x' * 513]}, {'load_references': [str(i) for i in range(101)]}):
            self.assertEqual(self.post({**self.payload, **changes}).status_code, 422)

    def test_11_no_income_inference_or_legacy_modification(self):
        self.post()
        result = self.get().json()
        self.assertFalse(result['accounting_income_posted'])
        self.assertFalse(result['references_verified'])
        self.assertFalse(result['original_documents_preserved'])
        self.assertIsNone(result['expected_pay'])
        self.assertEqual(accounting.records('local_admin', 'entry'), [])
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT value FROM legacy_original').fetchall(), [('original fixture',)])

    def test_12_corrupt_stored_evidence_stops_whole_response(self):
        self.post()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("UPDATE accounting_owned_records_v1 SET payload='{}'")
        response = self.get()
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('payments', response.json())


if __name__ == '__main__':
    unittest.main(verbosity=2)
