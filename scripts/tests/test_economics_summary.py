"""Offline contract/security checks; never import the main app or financial stores."""
import json
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import economics_gateway as gateway


class EconomicsSummaryTests(unittest.TestCase):
    def setUp(self):
        self.seen_auth = []

        def principal(key='', authorization=''):
            self.seen_auth.append((key, authorization))
            if key == 'fixture-admin' or authorization == 'Bearer fixture-token':
                return 'fixture-owner'
            return None

        self.auth = patch.object(gateway, 'get_admin_principal', principal, create=True)
        self.auth.start()
        self.addCleanup(self.auth.stop)
        app = FastAPI()
        app.include_router(gateway.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def get(self, **kwargs):
        return self.client.get('/api/v1/economics/summary', **kwargs)

    def test_anonymous_invalid_and_client_id_only_cannot_read_finances(self):
        for headers in ({}, {'x-client-id': 'fixture-owner'}, {'x-admin-key': 'wrong'},
                        {'Authorization': 'Bearer wrong'}):
            response = self.get(headers=headers)
            self.assertEqual(response.status_code, 403)
            self.assertIn('no-store', response.headers['cache-control'])

    def test_authenticated_response_has_no_values_without_verified_sources(self):
        response = self.get(headers={'x-admin-key': 'fixture-admin'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['schema'], 'aibs.economics.summary.v1')
        self.assertEqual(body['status'], 'unavailable')
        self.assertEqual(body['currency'], 'USD')
        self.assertEqual(len(body['metrics']), 14)
        self.assertNotIn('data', body)  # Retired unversioned mock/float response.
        for key, metric in body['metrics'].items():
            with self.subTest(metric=key):
                self.assertIsNone(metric['value'])
                self.assertEqual(metric['status'], 'unavailable')
                self.assertEqual(metric['verification'], 'not_verified')
                self.assertIsNone(metric['source'])
                self.assertIsNone(metric['observed_at'])
                self.assertIsNone(metric['fresh_until'])
                self.assertTrue(metric['reason_code'])
                self.assertTrue(metric['reason'])
        self.assertNotIn('fixture-owner', response.text)
        self.assertNotIn('fixture-admin', response.text)
        self.assertIn('no-store', response.headers['cache-control'])

    def test_window_is_exactly_30_days_in_utc_and_not_claimed_as_source_evidence(self):
        body = self.get(headers={'Authorization': 'Bearer fixture-token'}).json()
        end = datetime.fromisoformat(body['window']['end'])
        start = datetime.fromisoformat(body['window']['start'])
        self.assertEqual(end - start, timedelta(days=30))
        self.assertEqual(end.utcoffset(), timedelta(0))
        self.assertEqual(end.isoformat(), body['timestamp'])
        self.assertEqual(body['window']['coverage'], 'unconfirmed')

    def test_existing_admin_header_alias_and_bearer_use_identity_resolver(self):
        for headers in ({'x-api-key': 'fixture-admin'}, {'Authorization': 'Bearer fixture-token'}):
            self.assertEqual(self.get(headers=headers).status_code, 200)
        self.assertIn(('fixture-admin', ''), self.seen_auth)
        self.assertIn(('', 'Bearer fixture-token'), self.seen_auth)

    def test_read_does_not_open_or_seed_any_financial_database(self):
        with patch.object(sqlite3, 'connect', side_effect=AssertionError('unexpected DB open')):
            response = self.get(headers={'x-admin-key': 'fixture-admin'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'unavailable')

    def test_unavailable_reasons_cover_revenue_costs_security_and_derived_margin(self):
        metrics = self.get(headers={'x-admin-key': 'fixture-admin'}).json()['metrics']
        self.assertEqual(metrics['revenue.total_volume_30d']['reason_code'], 'NO_RECONCILED_REVENUE_SOURCE')
        self.assertEqual(metrics['llm_costs.total_compute_30d']['reason_code'], 'NO_RECONCILED_COST_SOURCE')
        self.assertEqual(metrics['security_telemetry.rate_limit_hits']['reason_code'], 'NO_VERIFIED_TELEMETRY_SOURCE')
        self.assertEqual(metrics['margins.net_profit_30d']['reason_code'], 'DEPENDENCIES_UNAVAILABLE')
        self.assertEqual(metrics['llm_costs.local_ollama_vram_kwh']['unit'], 'kWh')

    def test_get_is_read_only_and_forged_verification_inputs_have_no_effect(self):
        response = self.get(headers={'x-admin-key': 'fixture-admin'}, params={
            'verified': 'true', 'owner': 'other-owner', 'total_volume_30d': '14500.00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(m['value'] is None for m in response.json()['metrics'].values()))
        self.assertEqual(self.client.post('/api/v1/economics/summary', json={
            'status': 'verified_live_payment', 'amount': '14500.00',
        }).status_code, 405)


if __name__ == '__main__':
    unittest.main()
