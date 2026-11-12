"""Use existing owner/source integrity fences for both native document kinds."""
import hashlib
import json
import uuid
import unittest
from fastapi import HTTPException
from scripts.tests import test_chat_pdf_workflow as pdf
from scripts.tests.test_fdx_source_documents import XML
from core import fdx_source_documents as fdx
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from security.native_creative_source import require_native_creative_source


class NativeCreativeSourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=pdf.PdfWorkflowFixture()
        self.fixture._setupAsyncioRunner()
        self.addCleanup(self.fixture._tearDownAsyncioRunner)
        self.addCleanup(self.fixture.doCleanups)
        self.fixture._callSetUp()

    def check(self,path,owner=pdf.OWNER):
        token=bind_memory_principal(owner)
        try:return require_native_creative_source(path)
        finally:reset_memory_principal(token)

    def rich(self):
        path=self.fixture.projects/'Rich native source'
        fdx.import_project(path,XML,pdf.OWNER,uuid.uuid4().hex)
        return path

    def test_rich_original_owner_and_integrity_required(self):
        path=self.rich()
        before={p.relative_to(path).as_posix():p.read_bytes()for p in path.rglob('*')if p.is_file()}
        self.assertEqual(self.check(path),{'source_kind':'rich_fdx','source_sha256':hashlib.sha256(XML).hexdigest()})
        with self.assertRaises(HTTPException)as denied:self.check(path,pdf.OTHER)
        self.assertEqual(denied.exception.status_code,403)
        self.assertEqual(before,{p.relative_to(path).as_posix():p.read_bytes()for p in path.rglob('*')if p.is_file()})
        (path/'original.fdx').write_bytes(XML+b' ')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,409)

    def test_current_rich_version_tampering_refused(self):
        path=self.rich()
        version=next((path/'fdx_versions').glob('*/document.fdx'))
        version.write_bytes(XML+b' ')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,409)

    def test_pdf_original_owner_and_integrity_retained(self):
        source=self.fixture.stage()
        self.fixture.import_source(source,name='PDF native source')
        path=self.fixture.projects/'PDF native source'
        self.assertEqual(self.check(path),{'source_kind':'pdf','source_sha256':source['source_sha256']})
        with self.assertRaises(HTTPException)as denied:self.check(path,pdf.OTHER)
        self.assertEqual(denied.exception.status_code,403)
        (path/'original.pdf').write_bytes(b'changed synthetic original')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,409)

    def test_missing_and_conflicting_fences_refused(self):
        plain=self.fixture.projects/'Plain';plain.mkdir()
        with self.assertRaises(HTTPException)as denied:self.check(plain)
        self.assertEqual(denied.exception.status_code,403)
        path=self.rich()
        from core.chat_pdf_sources import CONTRACT
        (path/'source_pdf.json').write_text(json.dumps({'contract':CONTRACT,'owner':pdf.OWNER}),encoding='utf8')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,409)

    def test_pdf_source_identity_must_match_verified_original_digest(self):
        source=self.fixture.stage()
        self.fixture.import_source(source,name='Identity conflict')
        path=self.fixture.projects/'Identity conflict';fence=path/'source_pdf.json'
        value=json.loads(fence.read_bytes());value['source_sha256']='f'*64
        fence.write_text(json.dumps(value),encoding='utf8')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,409)

    def test_working_copy_does_not_implicitly_gain_rich_source_admission(self):
        path=self.rich();fence=path/fdx.FENCE
        value=json.loads(fence.read_bytes());value['mode']='working_copy'
        fence.write_text(json.dumps(value),encoding='utf8')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,403)

    def test_malformed_rich_fence_or_version_metadata_is_a_conflict(self):
        path=self.rich();fence=path/fdx.FENCE;before=fence.read_bytes()
        fence.write_text('[]',encoding='utf8')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,409)
        fence.write_bytes(before)
        state=next((path/'fdx_versions').glob('*/state.json'))
        state.write_text('[]',encoding='utf8')
        with self.assertRaises(HTTPException)as denied:self.check(path)
        self.assertEqual(denied.exception.status_code,409)


if __name__=='__main__':unittest.main()
