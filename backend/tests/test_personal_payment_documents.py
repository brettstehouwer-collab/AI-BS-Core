from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from modules import personal_payment_documents as documents
import test_personal_payments as payment_fixture


class PersonalOriginalTests(unittest.TestCase):
    verify = staticmethod(payment_fixture.PersonalPaymentsTests.verify)
    post = payment_fixture.PersonalPaymentsTests.post
    get = payment_fixture.PersonalPaymentsTests.get

    def setUp(self):
        payment_fixture.PersonalPaymentsTests.setUp(self)
        self.payment = self.post().json()['id']
        self.url = f'/api/personal-finance/payments/{self.payment}/documents'
        self.raw = b'%PDF-1.7\r\nOriginal\x00\xff exact bytes\r\n'
        self.upload_headers = {**self.headers, 'Idempotency-Key': 'original-one',
                               'X-Document-Name': 'receipt.pdf', 'Content-Type': 'application/pdf'}

    tearDown = payment_fixture.PersonalPaymentsTests.tearDown

    def upload(self, raw=None, headers=None, url=None):
        return self.client.post(url or self.url, content=self.raw if raw is None else raw,
                                headers=self.upload_headers if headers is None else headers)

    def listing(self, headers=None, url=None):
        return self.client.get(url or self.url, headers=self.headers if headers is None else headers)

    def download(self, document='original-one', headers=None):
        return self.client.get(self.url + '/' + document, headers=self.headers if headers is None else headers)

    def test_01_original_roundtrip_after_reopen(self):
        result = self.upload()
        self.assertEqual(result.status_code, 201)
        info = result.json()['document']
        self.assertEqual(info['size'], len(self.raw))
        self.assertEqual(info['sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.download().content, self.raw)
        self.assertEqual(self.listing().json()['documents'][0]['filename'], 'receipt.pdf')

    def test_02_auth_and_shared_pin_no_document_access(self):
        self.upload()
        for headers in ({}, {'X-FE-PIN': 'fixture'}, {'Authorization': 'Bearer invalid'}):
            self.assertEqual(self.upload(headers=headers).status_code, 403)
            self.assertEqual(self.listing(headers=headers).status_code, 403)
            self.assertEqual(self.download(headers=headers).status_code, 403)

    def test_03_verified_cross_owner_denied(self):
        self.upload()
        headers = {'Authorization': 'Bearer fixture-b'}
        self.assertEqual(self.listing(headers=headers).status_code, 404)
        self.assertEqual(self.download(headers=headers).status_code, 404)
        self.assertEqual(self.upload(headers={**self.upload_headers, 'X-Admin-Key': '', **headers}).status_code, 404)
        self.assertEqual(self.listing().json()['count'], 1)

    def test_04_idempotent_retry_and_conflict(self):
        first = self.upload().json()
        self.assertEqual(first, self.upload().json())
        self.assertEqual(self.upload(raw=b'changed').status_code, 409)
        self.assertEqual(self.upload(headers={**self.upload_headers, 'X-Document-Name': 'renamed.pdf'}).status_code, 409)
        self.assertEqual(self.listing().json()['count'], 1)
        self.assertEqual(self.download().content, self.raw)

    def test_05_new_version_keeps_both_originals(self):
        self.upload()
        headers = {**self.upload_headers, 'Idempotency-Key': 'original-two'}
        self.assertEqual(self.upload(raw=b'new original', headers=headers).status_code, 201)
        self.assertEqual(self.download().content, self.raw)
        self.assertEqual(self.download('original-two').content, b'new original')
        self.assertEqual(self.listing().json()['count'], 2)

    def test_06_no_overwrite_or_delete_even_direct_sql(self):
        self.upload()
        for sql in (f"UPDATE {documents.TABLE} SET filename='changed'", f'DELETE FROM {documents.TABLE}'):
            with closing(sqlite3.connect(self.path)) as db:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)
        self.assertEqual(self.client.delete(self.url + '/original-one', headers=self.headers).status_code, 405)
        self.assertEqual(self.download().content, self.raw)

    def test_07_limits_empty_and_actual_stream(self):
        with patch.object(documents, 'MAX_DOCUMENT', 4):
            self.assertEqual(self.upload(raw=b'12345').status_code, 413)
            self.assertEqual(self.upload(raw=b'12345', headers={**self.upload_headers, 'Content-Length': '4'}).status_code, 413)
            self.assertEqual(self.upload(raw=b'12', headers={**self.upload_headers, 'Content-Length': '4'}).status_code, 422)
        self.assertEqual(self.upload(raw=b'').status_code, 422)
        self.assertEqual(self.listing().json()['count'], 0)

    def test_08_aggregate_quotas_do_not_block_exact_retry(self):
        self.upload()
        with patch.object(documents, 'MAX_DOCUMENTS', 1):
            self.assertEqual(self.upload().status_code, 201)
            self.assertEqual(self.upload(headers={**self.upload_headers, 'Idempotency-Key': 'two'}).status_code, 413)
        with patch.object(documents, 'MAX_PAYMENT_BYTES', len(self.raw)):
            self.assertEqual(self.upload(headers={**self.upload_headers, 'Idempotency-Key': 'two'}).status_code, 413)
        self.assertEqual(self.download().content, self.raw)

    def test_09_filename_paths_and_operation_validation(self):
        for name in ('../receipt.pdf', 'C:\\receipt.pdf', 'CON', ' receipt.pdf'):
            self.assertIn(self.upload(headers={**self.upload_headers, 'X-Document-Name': name}).status_code, (400, 422))
        self.assertEqual(self.upload(headers={**self.upload_headers, 'Idempotency-Key': 'bad/key'}).status_code, 422)
        self.assertEqual(self.listing().json()['count'], 0)

    def test_10_active_content_download_is_attachment(self):
        self.upload(raw=b'<script>fixture()</script>', headers={**self.upload_headers,
                                                              'Content-Type': 'text/html', 'X-Document-Name': 'receipt.html'})
        response = self.download()
        self.assertEqual(response.headers['content-type'], 'application/octet-stream')
        self.assertTrue(response.headers['content-disposition'].startswith('attachment;'))
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(response.headers['cache-control'], 'private, no-store')
        self.assertEqual(response.headers['x-content-sha256'], hashlib.sha256(response.content).hexdigest())

    def test_11_reads_missing_payment_and_schema_are_inert(self):
        before = self.path.read_bytes()
        self.assertEqual(self.listing().json()['count'], 0)
        self.assertEqual(self.listing(url='/api/personal-finance/payments/999999/documents').status_code, 404)
        self.assertEqual(self.upload(url='/api/personal-finance/payments/999999/documents').status_code, 404)
        self.assertEqual(before, self.path.read_bytes())
        with closing(sqlite3.connect(self.path)) as db:
            self.assertFalse(db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (documents.TABLE,)).fetchone())

    def test_12_sqlite_backup_preserves_bytes_and_legacy(self):
        self.upload()
        backup = Path(self.tmp.name)/'snapshot.db'
        with closing(sqlite3.connect(self.path)) as source, closing(sqlite3.connect(backup)) as target:
            source.backup(target)
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute('PRAGMA quick_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute(f'SELECT content FROM {documents.TABLE}').fetchone()[0], self.raw)
            self.assertEqual(db.execute('SELECT value FROM legacy_original').fetchone()[0], 'original fixture')
            self.assertEqual(db.execute("SELECT count(*) FROM accounting_owned_records_v1 WHERE kind='entry'").fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
