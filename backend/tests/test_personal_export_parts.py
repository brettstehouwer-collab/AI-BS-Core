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
from modules import personal_export_parts as parts, personal_payment_documents as originals
import test_personal_financial_filings as fixture


class PersonalExportPartsTests(unittest.TestCase):
    verify=staticmethod(fixture.FinancialFilingTests.verify)
    post=fixture.FinancialFilingTests.post
    get=fixture.FinancialFilingTests.get
    file=fixture.FinancialFilingTests.file
    upload_filing=fixture.FinancialFilingTests.upload_filing
    tearDown=fixture.FinancialFilingTests.tearDown

    def setUp(self):
        fixture.FinancialFilingTests.setUp(self)
        limit=patch.object(parts,'PART_BYTES',1024)
        limit.start();self.addCleanup(limit.stop)
        self.assertEqual(self.upload_filing(raw=b'A'*900).status_code,201)
        self.assertEqual(self.upload_filing(raw=b'B'*900,headers={**self.file_headers,'Idempotency-Key':'second'}).status_code,201)

    def plan_response(self,year=2025,headers=None):
        return self.client.get(f'/api/personal-finance/exports/{year}/parts',headers=self.headers if headers is None else headers)

    def plan(self):
        result=self.plan_response();self.assertEqual(result.status_code,200,result.text)
        return result.json()['plan']

    def download(self,plan,index=0,headers=None):
        return self.client.get(f"/api/personal-finance/exports/{plan['year']}/parts/{plan['fingerprint']}/{index}.zip",
                               headers=self.headers if headers is None else headers)

    def test_01_disabled_default(self):
        with patch.dict('os.environ',{'AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT':''}):
            app=FastAPI();self.assertFalse(ledger.register_personal_ledger(app))
            self.assertFalse(any('/parts' in r.path for r in app.routes))

    def test_02_owner_auth_and_fingerprint_binding(self):
        plan=self.plan()
        for headers in ({},{'X-FE-PIN':'fixture'},{'Authorization':'Bearer invalid'}):
            self.assertEqual(self.plan_response(headers=headers).status_code,403)
            self.assertEqual(self.download(plan,headers=headers).status_code,403)
        other={'Authorization':'Bearer fixture-b'}
        self.assertEqual(self.plan_response(headers=other).json()['plan']['files'],[])
        self.assertEqual(self.download(plan,headers=other).status_code,409)

    def test_03_bounded_plan_never_reads_original_blobs(self):
        trace=[];original=accounting.get_db
        def read_only(write=False):
            self.assertFalse(write)
            db=original();db.set_trace_callback(trace.append);return db
        with patch.object(accounting,'get_db',read_only):plan=self.plan()
        self.assertGreaterEqual(len(plan['parts']),3)
        self.assertTrue(all(part['bytes']<=1024 for part in plan['parts']))
        self.assertFalse(any('select content' in sql.lower() or 'select *' in sql.lower() for sql in trace))

    def test_04_all_parts_reconstruct_every_file_and_exact_original(self):
        plan=self.plan();restored={};fingerprints=set()
        for part in plan['parts']:
            response=self.download(plan,part['index']);self.assertEqual(response.status_code,200)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                self.assertIsNone(archive.testzip())
                manifest=json.loads(archive.read('manifest.json'));fingerprints.add(manifest['fingerprint'])
                self.assertEqual(manifest['part_count'],len(plan['parts']))
                for file in manifest['files']:
                    raw=archive.read(file['path'])
                    self.assertNotIn(file['path'],restored)
                    self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(file['bytes'],file['sha256']))
                    restored[file['path']]=raw
        self.assertEqual(set(restored),{file['path'] for file in plan['files']})
        self.assertEqual(fingerprints,{plan['fingerprint']})
        self.assertEqual(sorted(raw for name,raw in restored.items() if name.endswith('.bin')),[b'A'*900,b'B'*900])

    def test_05_repeatability_and_other_owner_writes_do_not_invalidate(self):
        plan=self.plan();first=self.download(plan)
        self.file(headers={'Authorization':'Bearer fixture-b','Idempotency-Key':'other-owner'})
        self.assertEqual(self.plan()['fingerprint'],plan['fingerprint'])
        self.assertEqual(first.content,self.download(plan).content)

    def test_06_source_changes_stop_old_plan_before_more_parts(self):
        plan=self.plan();self.assertEqual(self.download(plan).status_code,200)
        self.file({**self.filing_payload,'notes':'new source'},headers={**self.headers,'Idempotency-Key':'new-source'})
        response=self.download(plan,1)
        self.assertEqual(response.status_code,409)
        self.assertNotEqual(response.headers['content-type'],'application/zip')
        self.assertNotEqual(self.plan()['fingerprint'],plan['fingerprint'])

    def test_07_each_part_is_one_snapshot_and_later_requests_detect_change(self):
        plan=self.plan();original=parts.collect_units
        def concurrent(db,owner,year):
            units=original(db,owner,year)
            originals.store_document(owner,self.filing,'concurrent','later.pdf','application/pdf',b'later',kind='personal_filing')
            return units
        with patch.object(parts,'collect_units',concurrent):
            self.assertEqual(self.download(plan).status_code,200)
        self.assertEqual(self.download(plan).status_code,409)

    def test_08_bad_original_metadata_never_produces_a_plan(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('DROP TRIGGER personal_original_no_update_v1')
            db.execute("UPDATE personal_payment_originals_v1 SET sha256='bad'")
        self.assertEqual(self.plan_response().status_code,409)

    def test_09_corrupt_blob_with_unchanged_metadata_rejects_whole_part(self):
        plan=self.plan()
        part=next(part for part in plan['parts'] if any(plan['files'][i]['source']['type']=='original' for i in part['files']))
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('DROP TRIGGER personal_original_no_update_v1')
            db.execute("UPDATE personal_payment_originals_v1 SET content=X'00'")
        response=self.download(plan,part['index'])
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.headers['cache-control'],'private, no-store')

    def test_10_planning_limits_and_invalid_parts_are_explicit(self):
        for name in ('MAX_FILES','MAX_PLAN_BYTES','MAX_INLINE_BYTES','MAX_RECORDS'):
            with patch.object(parts,name,0):self.assertEqual(self.plan_response().status_code,413)
        plan=self.plan();self.assertEqual(self.download(plan,len(plan['parts'])).status_code,404)
        self.assertEqual(self.plan_response(year=0).status_code,422)

    def test_11_reads_and_empty_year_never_initialize_storage(self):
        before=self.path.read_bytes();self.plan();self.assertEqual(before,self.path.read_bytes())
        missing=Path(self.tmp.name)/'missing.db'
        with patch.object(accounting,'DB_PATH',str(missing)):
            plan=self.plan();self.assertEqual(plan['files'],[])
            self.assertEqual(len(plan['parts']),1)
            self.assertEqual(self.download(plan).status_code,200)
        self.assertFalse(missing.exists())

    def test_12_record_source_and_per_entry_csv_remain_exact_and_unclassified(self):
        # Larger fixture part target accommodates CSV + full source JSON atomically.
        with patch.object(parts,'PART_BYTES',8192):
            entry=accounting.EntrySchema(date='2025-11-14',category='Fixture',description='=manual()',entry_type='income',amount='4.56')
            accounting.save('local_admin','entry',entry,'fixture-entry')
            plan=self.plan();files={}
            for part in plan['parts']:
                with zipfile.ZipFile(io.BytesIO(self.download(plan,part['index']).content)) as archive:
                    for name in archive.namelist():
                        if name!='manifest.json':files[name]=archive.read(name)
            self.assertTrue(any(b"'=manual()" in raw for name,raw in files.items() if name.endswith('.csv')))
            sources=[json.loads(raw) for name,raw in files.items() if name.startswith('records/')]
            source=next(row for row in sources if row['kind']=='entry')
            self.assertEqual(json.loads(source['payload'])['amount'],'4.56')
            self.assertFalse(plan['tax_return_or_payroll_reconciliation'])
            self.assertEqual(self.plan_response().headers['cache-control'],'private, no-store')


if __name__=='__main__':unittest.main(verbosity=2)
