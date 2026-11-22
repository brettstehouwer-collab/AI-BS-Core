"""Native client/session against real FDX ASGI handlers, isolated synthetic files."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from native_studio.screenplay_client import DraftSession,ScreenplayClient
from scripts.tests import test_fdx_source_workflow as workflow_fixture
from scripts.tests.test_fdx_source_documents import XML

class NativeRichRouteTests(unittest.TestCase):
    def exact_edit(self,session,start,end,replacement):
        before=session.content;content=before[:start]+replacement+before[end:]
        session.rich.edit_utf16(len(before[:start].encode('utf-16-le'))//2,
            len(before[start:end].encode('utf-16-le'))//2,len(replacement.encode('utf-16-le'))//2,content)
        session.content=content
    def setUp(self):
        self.fixture=workflow_fixture.FDXWorkflowTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'source.fdx';self.path.write_bytes(b'\xef\xbb\xbf'+XML)
        setting=patch('native_studio.screenplay_client.local_service_headers',return_value={'Authorization':'Bearer own'})
        setting.start();self.addCleanup(setting.stop)
        routes={'/api/screenwriting/projects/import-fdx-source':'/import','/api/screenwriting/read':'/read',
                '/api/screenwriting/write':'/write','/api/screenwriting/export/fdx':'/fdx',
                '/api/screenwriting/projects/fdx-working-copy':'/working'}
        def handler(request):
            result=self.fixture.client.request(request.method,routes[request.url.path],
                params=dict(request.url.params),content=request.content,headers=dict(request.headers))
            return httpx.Response(result.status_code,headers=dict(result.headers),content=result.content)
        self.client=ScreenplayClient(transport=httpx.MockTransport(handler))
        self.name=self.client.import_file('Native Rich Fixture',self.path)

    def test_two_saves_keep_styled_runs_notes_dual_title_original_and_later_text(self):
        session=DraftSession();initial=self.client.read(self.name);session.load(initial)
        for index in range(2):
            before=session.content;paragraph=session.rich.document['blocks'][2]['text']
            start=before.index(paragraph)+len(paragraph)
            self.exact_edit(session,start,start,f' Edit{index}.')
            snapshot=session.capture_rich_snapshot();submitted=session.content
            ack=self.client.save(self.name,submitted,session.revision,
                expected_workflow_revision=session.workflow_revision,fdx_document=snapshot)
            start=session.content.index('Edit'+str(index)+'.')+len('Edit'+str(index)+'.')
            self.exact_edit(session,start,start,' Later.')
            session.saved(submitted,ack,snapshot)
            self.assertTrue(session.dirty);self.assertIn('Later.',session.content)
            self.assertEqual(session.rich.document['title_page'],initial['fdx_document']['title_page'])
            self.assertEqual(session.rich.document['blocks'][0]['notes'],initial['fdx_document']['blocks'][0]['notes'])
        snapshot=session.capture_rich_snapshot();submitted=session.content
        session.saved(submitted,self.client.save(self.name,submitted,session.revision,
            expected_workflow_revision=session.workflow_revision,fdx_document=snapshot),snapshot)
        self.assertFalse(session.dirty)
        reopened=self.client.read(self.name)
        self.assertEqual(reopened['content'],session.content)
        output=self.client.export(self.name,'fdx',session.revision)
        self.assertIn(b'NOTE ONLY',output);self.assertIn(b'<DualDialogue>',output)
        original=self.fixture.files(self.name)['original.fdx']
        self.assertEqual(original,self.path.read_bytes())
        self.assertNotEqual(hashlib.sha256(output).hexdigest(),hashlib.sha256(original).hexdigest())

    def test_structural_text_working_copy_is_explicit_and_preserves_all_original_files(self):
        read=self.client.read(self.name);before=self.fixture.files(self.name)
        content=read['content']+'\n\nINT. NEW STRUCTURE - DAY\n\nA new paragraph.'
        name=self.client.create_rich_working_copy(self.name,'Separate Native Text',content,read['revision'])
        self.assertEqual(self.client.read(name)['content'],content)
        self.assertEqual(before,self.fixture.files(self.name))

if __name__=='__main__':unittest.main()
