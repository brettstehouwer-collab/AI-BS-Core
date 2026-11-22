from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from modules import accounting_router as accounting, personal_ledger_export as ledger, personal_year_archive as archive
import test_personal_payment_documents as original_fixture


class PersonalYearArchiveTests(unittest.TestCase):
    verify = staticmethod(original_fixture.PersonalOriginalTests.verify)
    post = original_fixture.PersonalOriginalTests.post
    get = original_fixture.PersonalOriginalTests.get
    upload = original_fixture.PersonalOriginalTests.upload
    tearDown = original_fixture.PersonalOriginalTests.tearDown

    def setUp(self):
        original_fixture.PersonalOriginalTests.setUp(self)
        export_flag = patch.dict('os.environ', {'AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT': '1'})
        export_flag.start()
        self.addCleanup(export_flag.stop)
        self.assertTrue(ledger.register_personal_ledger(self.app))
        self.assertEqual(self.upload().status_code, 201)

    def export(self, year=2026, headers=None):
        return self.client.get(f'/api/personal-finance/exports/{year}.zip',
                               headers=self.headers if headers is None else headers)

    def unpack(self, response):
        import zipfile
        self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else '')
        package = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertIsNone(package.testzip())
        return package, json.loads(package.read('manifest.json'))

    def test_01_disabled_default(self):
        with patch.dict('os.environ', {'AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT': ''}):
            app = FastAPI()
            self.assertFalse(ledger.register_personal_ledger(app))
            self.assertFalse(any('/exports/' in r.path for r in app.routes))

    def test_02_auth_and_owner_isolation(self):
        for headers in ({}, {'X-FE-PIN': 'fixture'}, {'Authorization': 'Bearer invalid'}):
            self.assertEqual(self.export(headers=headers).status_code, 403)
        with self.unpack(self.export(headers={'Authorization': 'Bearer fixture-b'}))[0] as package:
            self.assertEqual(json.loads(package.read('records.json')), [])
            self.assertFalse(any(n.endswith('.bin') for n in package.namelist()))

    def test_03_original_bytes_names_and_every_manifest_hash(self):
        package, manifest = self.unpack(self.export())
        with package:
            for name, pin in manifest['files'].items():
                raw = package.read(name)
                self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (pin['bytes'], pin['sha256']))
                self.assertFalse(name.startswith('/') or '..' in name.split('/'))
            original = manifest['originals'][0]
            self.assertEqual(original['filename'], 'receipt.pdf')
            self.assertEqual(package.read(original['archive_path']), self.raw)

    def test_04_selection_uses_payment_date_not_work_week(self):
        self.post({**self.payload, 'payment_date': '2025-12-31', 'week_start': '2026-01-05'},
                  {**self.headers, 'Idempotency-Key': 'other-year'})
        package, manifest = self.unpack(self.export(2025))
        with package:
            self.assertEqual(manifest['payments'], 1)
            self.assertEqual(manifest['originals'], [])
            self.assertIn('2025-12-31', package.read('records.json').decode())

    def test_05_accounting_csv_preserves_separate_income_and_formula_safety(self):
        entry = accounting.EntrySchema(date='2026-11-14', category='Fixture', description='=unsafe()',
                                       entry_type='income', amount='4.56')
        accounting.save('local_admin', 'entry', entry, 'fixture-entry')
        package, manifest = self.unpack(self.export())
        with package:
            csv = package.read('accounting-ledger.csv').decode('utf-8-sig')
            self.assertIn("'=unsafe()", csv)
            self.assertIn('4.56', csv)
            self.assertNotIn('123.45', csv)
            self.assertFalse(manifest['tax_return_or_payroll_reconciliation'])
            self.assertEqual(manifest['accounting_entries'], 1)

    def test_06_coverage_exposes_missing_originals_without_inferring_tax(self):
        saved = self.post({**self.payload, 'amount': '2.00'}, {**self.headers, 'Idempotency-Key': 'unattached'}).json()
        package, manifest = self.unpack(self.export())
        package.close()
        self.assertIn(saved['id'], manifest['payments_without_stored_originals'])
        self.assertIn('standalone tax documents', manifest['exclusions'])
        self.assertEqual(manifest['verification'], 'manual_unreconciled')

    def test_07_corrupt_original_rejects_complete_archive(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TRIGGER personal_original_no_update_v1')
            db.execute("UPDATE personal_payment_originals_v1 SET content=X'00'")
        response = self.export()
        self.assertEqual(response.status_code, 409)
        self.assertNotEqual(response.headers['content-type'], 'application/zip')

    def test_08_corrupt_owner_record_rejects_complete_archive(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE accounting_owned_records_v1 SET payload='not-json'")
        self.assertEqual(self.export().status_code, 409)

    def test_09_missing_database_and_reads_do_not_initialize_or_modify(self):
        before = self.path.read_bytes()
        self.export()
        self.assertEqual(before, self.path.read_bytes())
        missing = Path(self.tmp.name)/'absent.db'
        with patch.object(accounting, 'DB_PATH', str(missing)):
            package, manifest = self.unpack(self.export())
            package.close()
            self.assertEqual(manifest['records'], 0)
        self.assertFalse(missing.exists())

    def test_10_resource_limit_never_silently_truncates(self):
        with patch.object(archive, 'MAX_ORIGINALS', 0):
            response = self.export()
            self.assertEqual(response.status_code, 413)
        with patch.object(archive, 'MAX_SOURCE_BYTES', 1):
            self.assertEqual(self.export().status_code, 413)

    def test_11_one_snapshot_excludes_concurrent_new_original(self):
        from modules.personal_payment_documents import store_document
        original = archive.records_for_year
        def concurrent(db, owner, year):
            selected = original(db, owner, year)
            store_document(owner, self.payment, 'concurrent', 'later.pdf', 'application/pdf', b'later')
            return selected
        with patch.object(archive, 'records_for_year', concurrent):
            package, manifest = self.unpack(self.export())
            package.close()
            self.assertEqual(len(manifest['originals']), 1)
        package, manifest = self.unpack(self.export())
        package.close()
        self.assertEqual(len(manifest['originals']), 2)

    def test_12_repeatability_and_private_download_headers(self):
        first, second = self.export(), self.export()
        self.assertEqual(first.content, second.content)
        self.assertEqual(first.headers['cache-control'], 'private, no-store')
        self.assertEqual(first.headers['x-content-sha256'], hashlib.sha256(first.content).hexdigest())
        self.assertEqual(first.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(self.export(0).status_code, 422)


if __name__ == '__main__':
    unittest.main(verbosity=2)
