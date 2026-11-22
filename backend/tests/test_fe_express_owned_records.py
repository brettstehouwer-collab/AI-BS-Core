"""Bounded source-foundation checks; no application registration or live stores."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import fe_express_owned_records as records


class OwnedRecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'records.sqlite3'
        self.app = FastAPI()
        self.app.include_router(records.router)
        self.app.dependency_overrides[records.database_path] = lambda: self.path
        self.client = TestClient(self.app)
        self.auth = patch.object(records, 'get_admin_principal', side_effect=lambda key, authorization: {'A': 'firebase:test:A', 'B': 'firebase:test:B'}.get(key))
        self.auth.start()
        self.prefix = '/api/v1/fe-express/driver-records'

    def tearDown(self):
        self.auth.stop()
        self.client.close()
        self.temp.cleanup()

    def save(self, owner='A', **changes):
        data = dict(op_id='op1', load_id='load1', base_revision=0,
                    payload={'load_ref': '  original  ', 'pickup_arrival': '2026-11-14T10:01:02-05:00', 'expenses': '$12 original note'})
        data.update(changes)
        return self.client.post(self.prefix + '/sync', json=data, headers={'X-Admin-Key': owner})

    def test_lazy_store_and_pin_refusal(self):
        self.assertFalse(self.path.exists())
        self.assertEqual(self.client.get(self.prefix + '/identity', headers={'X-Admin-Key': 'A'}).json(), {'owner': 'firebase:test:A', 'scope': 'driver_work'})
        response = self.client.get(self.prefix + '/loads', headers={'X-FE-Session': 'pin-session'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.path.exists())

    def test_exact_retry_and_durable_revision(self):
        first = self.save()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.save().json(), first.json())
        with TestClient(self.app) as restarted:
            rows = restarted.get(self.prefix + '/loads', headers={'X-Admin-Key': 'A'}).json()['loads']
        self.assertEqual(rows[0]['revision'], 1)
        self.assertEqual(rows[0]['payload']['load_ref'], '  original  ')
        self.assertEqual(self.save(op_id='op2', base_revision=1).json()['revision'], 2)

    def test_operation_and_revision_conflicts_are_atomic(self):
        self.save()
        self.assertEqual(self.save(payload={'notes': 'different'}).status_code, 409)
        self.assertEqual(self.save(op_id='op2').status_code, 409)
        self.assertEqual(self.save(op_id='op2', base_revision=1).json()['revision'], 2)

    def test_owners_do_not_share_rows_or_operations(self):
        self.save()
        self.assertEqual(self.client.get(self.prefix + '/loads', headers={'X-Admin-Key': 'B'}).json(), {'loads': []})
        self.assertEqual(self.save(owner='B', payload={'notes': 'B original'}).status_code, 200)
        self.assertEqual(self.client.get(self.prefix + '/loads', headers={'X-Admin-Key': 'A'}).json()['loads'][0]['payload']['load_ref'], '  original  ')

    def test_immutable_attachment_retry_and_owner_download(self):
        self.save()
        url = self.prefix + '/loads/load1/attachments'
        headers = {'X-Admin-Key': 'A', 'X-Operation-Id': 'file1', 'Content-Type': 'application/octet-stream', 'X-Filename': '../../ignored'}
        first = self.client.post(url, content=b'original\x00bytes', headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.client.post(url, content=b'original\x00bytes', headers=headers).json(), first.json())
        self.assertEqual(self.client.post(url, content=b'changed', headers=headers).status_code, 409)
        download = url + '/file1'
        self.assertEqual(self.client.get(download, headers={'X-Admin-Key': 'A'}).content, b'original\x00bytes')
        self.assertEqual(self.client.get(download, headers={'X-Admin-Key': 'B'}).status_code, 404)

    def test_invalid_times_fields_and_bounds_do_not_write(self):
        for timestamp in ('2026-11-14T10:01:02', '2026-02-30T10:01:02Z', '2026-11-14T10:01:02+25:00'):
            self.assertEqual(self.save(payload={'pickup_arrival': timestamp}).status_code, 422)
        self.assertEqual(self.save(payload={'owner': 'B'}).status_code, 422)
        self.assertEqual(self.save(base_revision=True).status_code, 422)
        self.assertEqual(self.client.post(self.prefix + '/sync', content=b' ' * (records.MAX_REQUEST + 1), headers={'X-Admin-Key': 'A'}).status_code, 413)
        self.assertFalse(self.path.exists())

    def test_attachment_bounds_missing_load_and_cross_kind_operation(self):
        headers = {'X-Admin-Key': 'A', 'X-Operation-Id': 'op1', 'Content-Type': 'application/octet-stream'}
        url = self.prefix + '/loads/load1/attachments'
        self.assertEqual(self.client.post(url, content=b'x', headers=headers).status_code, 404)
        self.save()
        self.assertEqual(self.client.post(url, content=b'x', headers=headers).status_code, 409)
        headers['X-Operation-Id'] = 'file1'
        with patch.object(records, 'MAX_ATTACHMENT', 2):
            self.assertEqual(self.client.post(url, content=b'abc', headers=headers).status_code, 413)
        self.assertEqual(self.client.post(url, content=b'', headers=headers).status_code, 422)


if __name__ == '__main__':
    unittest.main()
