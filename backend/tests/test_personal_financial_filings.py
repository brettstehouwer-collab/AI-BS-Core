from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
import zipfile

from fastapi import FastAPI
from modules import accounting_router as accounting, personal_ledger_export as ledger
from modules import personal_payment_documents as originals, personal_year_archive as years
import test_personal_payment_documents as fixture


class FinancialFilingTests(unittest.TestCase):
    verify=staticmethod(fixture.PersonalOriginalTests.verify)
    post=fixture.PersonalOriginalTests.post
    get=fixture.PersonalOriginalTests.get
    tearDown=fixture.PersonalOriginalTests.tearDown

    def setUp(self):
        fixture.PersonalOriginalTests.setUp(self)
        flag=patch.dict('os.environ',{'AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT':'1'})
        flag.start();self.addCleanup(flag.stop)
        ledger.register_personal_ledger(self.app)
        self.filing_payload=dict(document_date='2026-02-01',filing_year=2025,source='Fixture source',
                                 document_type='tax_document',notes='Original note: no inferred eligibility')
        self.filing=self.file().json()['id']
        self.docs=f'/api/personal-finance/filings/{self.filing}/originals'
        self.file_headers={**self.headers,'Idempotency-Key':'fixture-original','X-Document-Name':'annual.pdf','Content-Type':'application/pdf'}

    def file(self,payload=None,headers=None):
        return self.client.post('/api/personal-finance/filings',json=self.filing_payload if payload is None else payload,
                                headers={**self.headers,'Idempotency-Key':'fixture-filing'} if headers is None else headers)

    def upload_filing(self,raw=None,headers=None,url=None):
        return self.client.post(url or self.docs,content=self.raw if raw is None else raw,
                                headers=self.file_headers if headers is None else headers)

    def export(self,year=2025,headers=None):
        return self.client.get(f'/api/personal-finance/exports/{year}/complete.zip',headers=self.headers if headers is None else headers)

    def unpack(self,response):
        self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
        z=zipfile.ZipFile(io.BytesIO(response.content));self.assertIsNone(z.testzip())
        return z,json.loads(z.read('manifest.json'))

    def test_01_standalone_filing_needs_no_payment(self):
        headers={'Authorization':'Bearer fixture-b','Idempotency-Key':'standalone'}
        self.assertEqual(self.file(headers=headers).status_code,201)
        owner='firebase:ai-bs-dashboard:fixture-b'
        self.assertEqual(accounting.records(owner,'personal_payment'),[])
        self.assertEqual(len(accounting.records(owner,'personal_filing')),1)
        self.assertEqual(accounting.records(owner,'entry'),[])

    def test_02_auth_owner_and_family_isolation(self):
        self.upload_filing()
        for headers in ({},{'X-FE-PIN':'fixture'},{'Authorization':'Bearer invalid'}):
            self.assertEqual(self.file(headers=headers).status_code,403)
            self.assertEqual(self.client.get(self.docs,headers=headers).status_code,403)
            self.assertEqual(self.export(headers=headers).status_code,403)
        self.assertEqual(self.client.get(self.docs,headers={'Authorization':'Bearer fixture-b'}).status_code,404)
        self.assertEqual(self.client.get(f'/api/personal-finance/payments/{self.filing}/documents',headers=self.headers).status_code,404)
        self.assertEqual(self.client.get(f'/api/personal-finance/filings/{self.payment}/originals',headers=self.headers).status_code,404)

    def test_03_strict_metadata_and_no_client_identity_or_tax_inference(self):
        for changes in ({'owner':'someone'},{'id':1},{'is_tax_deductible':True},{'filing_year':'2025'},
                        {'filing_year':0},{'document_date':'2026-02-30'},{'source':' '},{'document_type':'tax_verified'}):
            self.assertEqual(self.file({**self.filing_payload,**changes}).status_code,422)

    def test_04_metadata_replay_is_append_only(self):
        self.assertEqual(self.file().json()['id'],self.filing)
        self.assertEqual(self.file({**self.filing_payload,'notes':'changed'}).status_code,409)
        result=self.client.get('/api/personal-finance/filings',headers=self.headers).json()
        self.assertEqual(result['count'],1)
        self.assertEqual(result['filings'][0]['notes'],self.filing_payload['notes'])
        self.assertIn(self.client.delete(f'/api/personal-finance/filings/{self.filing}',headers=self.headers).status_code,(404,405))
        self.assertEqual(len(accounting.records('local_admin','personal_filing')),1)

    def test_05_original_replay_unicode_and_retained_versions(self):
        headers={**self.file_headers,'X-Document-Name':'r%C3%A9sum%C3%A9.pdf','X-Document-Name-Encoding':'uri'}
        first=self.upload_filing(headers=headers)
        self.assertEqual(first.status_code,201)
        self.assertEqual(first.json(),self.upload_filing(headers=headers).json())
        self.assertEqual(first.json()['document']['filename'],'résumé.pdf')
        self.assertEqual(first.json()['document']['filing_id'],self.filing)
        self.assertNotIn('payment_id',first.json()['document'])
        self.assertEqual(self.upload_filing(raw=b'changed',headers=headers).status_code,409)
        self.assertEqual(self.upload_filing(raw=b'new',headers={**self.file_headers,'Idempotency-Key':'new'}).status_code,201)
        downloaded=self.client.get(self.docs+'/fixture-original',headers=self.headers)
        self.assertEqual(downloaded.content,self.raw)
        self.assertEqual(downloaded.headers['cache-control'],'private, no-store')

    def test_06_existing_upload_bounds_and_safe_paths_apply_to_filings(self):
        with patch.object(originals,'MAX_DOCUMENT',2):
            self.assertEqual(self.upload_filing(raw=b'123').status_code,413)
        self.assertEqual(self.upload_filing(raw=b'').status_code,422)
        self.assertEqual(self.upload_filing(headers={**self.file_headers,'X-Document-Name':'../annual.pdf'}).status_code,400)
        self.assertEqual(self.client.get(self.docs,headers=self.headers).json()['count'],0)

    def test_07_listing_uses_user_assigned_year(self):
        self.assertEqual(self.client.get('/api/personal-finance/filings?filing_year=2025',headers=self.headers).json()['count'],1)
        self.assertEqual(self.client.get('/api/personal-finance/filings?filing_year=2026',headers=self.headers).json()['count'],0)
        self.assertEqual(self.client.get('/api/personal-finance/filings?filing_year=0',headers=self.headers).status_code,422)

    def test_08_v2_includes_filing_year_and_v1_contract_stays_separate(self):
        self.upload_filing()
        package,manifest=self.unpack(self.export())
        with package:
            self.assertEqual(manifest['version'],2)
            self.assertEqual(manifest['filings'],1)
            self.assertIn('2026-02-01',package.read('filings.json').decode())
            self.assertEqual(package.read(manifest['originals'][0]['archive_path']),self.raw)
            self.assertFalse(manifest['tax_return_or_payroll_reconciliation'])
        prior=self.client.get('/api/personal-finance/exports/2025.zip',headers=self.headers)
        with zipfile.ZipFile(io.BytesIO(prior.content)) as z:
            self.assertEqual(json.loads(z.read('manifest.json'))['version'],1)
            self.assertNotIn('filings.json',z.namelist())

    def test_09_every_v2_member_hash_and_generated_original_path(self):
        self.upload_filing()
        package,manifest=self.unpack(self.export())
        with package:
            for name,pin in manifest['files'].items():
                raw=package.read(name)
                self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(pin['bytes'],pin['sha256']))
                self.assertFalse(name.startswith('/') or '..' in name.split('/'))
        self.assertEqual(self.export().content,self.export().content)

    def test_10_corrupt_original_fails_whole_v2(self):
        self.upload_filing()
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('DROP TRIGGER personal_original_no_update_v1')
            db.execute("UPDATE personal_payment_originals_v1 SET content=X'00'")
        self.assertEqual(self.export().status_code,409)

    def test_11_v2_keeps_same_snapshot_across_new_filing_original(self):
        self.upload_filing()
        original=years.records_for_year
        def concurrent(db,owner,year):
            records=original(db,owner,year)
            originals.store_document(owner,self.filing,'concurrent','later.pdf','application/pdf',b'later',kind='personal_filing')
            return records
        with patch.object(years,'records_for_year',concurrent):
            z,manifest=self.unpack(self.export());z.close()
            self.assertEqual(len(manifest['originals']),1)
        z,manifest=self.unpack(self.export());z.close()
        self.assertEqual(len(manifest['originals']),2)

    def test_12_defaults_and_backup_preserve_originals(self):
        from modules.personal_payments import register_personal_payments
        with patch.dict('os.environ',{'AI_BS_ENABLE_PERSONAL_PAYMENTS':'','AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT':''}):
            app=FastAPI()
            self.assertFalse(register_personal_payments(app));self.assertFalse(ledger.register_personal_ledger(app))
        self.upload_filing()
        backup=Path(self.tmp.name)/'backup.db'
        with closing(sqlite3.connect(self.path)) as source,closing(sqlite3.connect(backup)) as target:
            source.backup(target)
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute('PRAGMA quick_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT content FROM personal_payment_originals_v1').fetchone()[0],self.raw)
            self.assertEqual(db.execute('SELECT value FROM legacy_original').fetchone()[0],'original fixture')


if __name__=='__main__':unittest.main(verbosity=2)
