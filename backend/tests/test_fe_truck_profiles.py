"""Twelve bounded synthetic API checks; never open live driver or master stores."""
import concurrent.futures
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import fe_express_owned_records as records
import fe_truck_profiles as trucks
from routers.fe_driver_registration import register_driver_portal


class TruckProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'synthetic.sqlite3'
        self.app = FastAPI()
        self.app.include_router(trucks.router)
        self.app.dependency_overrides[records.database_path] = lambda: self.path
        self.client = TestClient(self.app)
        self.auth = patch.object(records, 'get_admin_principal', side_effect=lambda key, authorization: {'A': 'firebase:fixture:A', 'B': 'firebase:fixture:B'}.get(key))
        self.auth.start()
        self.url = '/api/v1/fe-express/driver-records/truck-profile'

    def tearDown(self):
        self.client.close()
        self.auth.stop()
        self.temp.cleanup()

    def post(self, owner='A', op='one', revision=0, payload=None):
        return self.client.post(self.url, headers={'X-Admin-Key': owner}, json={
            'op_id': op, 'base_revision': revision,
            'payload': payload if payload is not None else {'schema_version': 1, 'cargo_box_length_ft': 30}})

    def get(self, owner='A', suffix=''):
        return self.client.get(self.url + suffix, headers={'X-Admin-Key': owner})

    def test_01_inert_registration_and_unauthorized_no_storage(self):
        for flag in ('', 'true', '0'):
            app = FastAPI()
            with patch.dict('os.environ', {'AI_BS_ENABLE_DRIVER_PORTAL': flag}):
                self.assertFalse(register_driver_portal(app))
            with TestClient(app) as client:
                self.assertEqual(client.get(self.url).status_code, 404)
        app = FastAPI()
        with patch.dict('os.environ', {'AI_BS_ENABLE_DRIVER_PORTAL': '1'}):
            self.assertTrue(register_driver_portal(app))
        with TestClient(app) as client:
            self.assertEqual(client.get(self.url).status_code, 403)
        self.assertEqual(self.get('PIN').status_code, 403)
        self.assertFalse(self.path.exists())

    def test_02_unknown_profile_does_not_infer_overall_length(self):
        initial = self.get().json()
        self.assertIsNone(initial['profile'])
        self.assertEqual(initial['revision'], 0)
        result = self.post().json()
        self.assertEqual(result['profile']['payload'], {'schema_version': 1, 'cargo_box_length_ft': 30})
        self.assertIn('overall_length_ft', result['missing_vehicle_fields'])
        self.assertIn('vehicle_configuration', result['missing_vehicle_fields'])
        self.assertFalse(result['routing_ready'])

    def test_03_owner_isolation_and_private_headers(self):
        self.assertEqual(self.post().status_code, 200)
        response = self.get('B')
        self.assertIsNone(response.json()['profile'])
        self.assertEqual(self.get('B', '/history').json()['profiles'], [])
        self.assertEqual(response.headers['cache-control'], 'private, no-store')
        self.assertIn('Authorization', response.headers['vary'])
        self.assertEqual(self.post(owner='B').json()['revision'], 1)

    def test_04_retry_after_reopen_does_not_duplicate(self):
        first = self.post().json()
        self.client.close()
        self.client = TestClient(self.app)
        self.assertEqual(self.post().json(), first)
        self.assertEqual(len(self.get(suffix='/history').json()['profiles']), 1)

    def test_05_changed_retry_and_stale_edit_reject_without_loss(self):
        original = self.post().json()
        self.assertEqual(self.post(payload={'schema_version': 1}).status_code, 409)
        response = self.post(op='stale')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['detail']['current_revision'], 1)
        self.assertEqual(self.get().json(), original)

    def test_06_append_history_preserves_original_notes_and_pages(self):
        for revision in range(22):
            payload = {'schema_version': 1, 'measurement_notes': f'  Original {revision}\nπ  '}
            self.assertEqual(self.post(op=f'item{revision}', revision=revision, payload=payload).status_code, 200)
        page = self.get(suffix='/history').json()
        self.assertEqual(len(page['profiles']), 20)
        self.assertEqual(page['next_before_revision'], 3)
        second = self.get(suffix='/history?before_revision=3').json()
        self.assertEqual([p['revision'] for p in second['profiles']], [2, 1])
        self.assertEqual(second['profiles'][-1]['payload']['measurement_notes'], '  Original 0\nπ  ')
        self.assertIsNone(second['next_before_revision'])

    def test_07_units_numbers_and_unknown_fields_are_strict(self):
        invalid = [{'height_in': value} for value in (True, '150', 0, -1, 401, 10**500)]
        invalid += [{'overall_length_ft': 301}, {'owner': 'B'}, {'routing_ready': True}, {'schema_version': True}]
        for fields in invalid:
            with self.subTest(fields=str(fields)[:70]):
                self.assertEqual(self.post(payload={'schema_version': 1, **fields}).status_code, 422)
        self.assertFalse(self.path.exists())

    def test_08_confirmation_requires_full_actual_facts(self):
        for payload in ({'dimensions_confirmed': True}, {'weights_confirmed': True},
                        {'dimensions_confirmed': 'true'}, {'vehicle_configuration': 'box30'},
                        {'hazmat_status': 'assumed_none'}):
            self.assertEqual(self.post(payload={'schema_version': 1, **payload}).status_code, 422)
        complete = {'schema_version': 1, 'vehicle_configuration': 'tractor_trailer',
                    'height_in': 155.5, 'width_in': 100, 'overall_length_ft': 52,
                    'loaded_gross_lb': 33000, 'axles': [{'axle_id': 'steer', 'actual_weight_lb': 11000},
                    {'axle_id': 'rear', 'actual_weight_lb': 22000}], 'dimensions_confirmed': True,
                    'weights_confirmed': True, 'hazmat_status': 'none'}
        result = self.post(payload=complete).json()
        self.assertEqual(result['missing_vehicle_fields'], [])
        self.assertFalse(result['provider_qualified'])
        self.assertFalse(result['routing_ready'])

    def test_09_axle_validation(self):
        for axles in ({}, [{'axle_id': 'x'}, {'axle_id': 'x'}], [{'axle_id': '../escape'}],
                      [{'axle_id': 'x', 'actual_weight_lb': False}], [{'axle_id': 'x', 'guess': 1}],
                      [{'axle_id': f'x{i}'} for i in range(17)]):
            self.assertEqual(self.post(payload={'schema_version': 1, 'axles': axles}).status_code, 422)
        self.assertEqual(self.post(payload={'schema_version': 1, 'axles': [{'axle_id': 'unknown_weight'}]}).status_code, 200)

    def test_10_bounded_json_and_ambiguous_content_rejected(self):
        for raw in (b'{', b'[]', b'{"op_id":"x","op_id":"y"}',
                    b'{"op_id":"x","base_revision":0,"payload":{"schema_version":1,"height_in":NaN}}'):
            self.assertEqual(self.client.post(self.url, content=raw, headers={'X-Admin-Key': 'A'}).status_code, 422)
        self.assertEqual(self.client.post(self.url, content=b' ' * 32769, headers={'X-Admin-Key': 'A'}).status_code, 413)
        self.assertEqual(self.post(payload={'schema_version': 1, 'measurement_notes': 'x' * 4001}).status_code, 422)

    def test_11_concurrent_cas_has_one_winner(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            def attempt(op):
                with TestClient(self.app) as client:
                    return client.post(self.url, json={'op_id': op, 'base_revision': 0, 'payload': {'schema_version': 1}}, headers={'X-Admin-Key': 'A'}).status_code
            outcomes = list(pool.map(attempt, ['first', 'second']))
        self.assertEqual(sorted(outcomes), [200, 409])
        self.assertEqual(len(self.get(suffix='/history').json()['profiles']), 1)

    def test_12_existing_loads_originals_and_integrity_unchanged(self):
        with records.connection(self.path) as db:
            db.execute('INSERT INTO loads VALUES(?,?,?,?,?)', ('firebase:fixture:A', 'keep', 7, '{"notes":"original"}', 'original-time'))
            db.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?,?)', ('firebase:fixture:A', 'keep', 'file', 'original-hash', 3, 'application/pdf', b'raw'))
        self.assertEqual(self.post().status_code, 200)
        with records.connection(self.path) as db:
            self.assertEqual(tuple(db.execute('SELECT * FROM loads').fetchone()), ('firebase:fixture:A', 'keep', 7, '{"notes":"original"}', 'original-time'))
            self.assertEqual(db.execute('SELECT content FROM attachments').fetchone()[0], b'raw')
            self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
            self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0], 2)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')


if __name__ == '__main__':
    unittest.main()
