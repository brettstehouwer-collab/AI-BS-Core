"""Synthetic rich FDX source/version fixtures; no real projects/services."""
import hashlib,json,sys,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from core import fdx_source_documents as fdx

OWNER='firebase:fdx-fixture:owner';OTHER='firebase:fdx-fixture:other'
XML=b'''<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft Version="3" DocumentType="Script"><DocumentInfo><Unknown Flag="keep">inert</Unknown></DocumentInfo><HeaderAndFooter><Header><Paragraph><Text>HEADER</Text></Paragraph></Header></HeaderAndFooter><TitlePage><Content><Paragraph Type="Title"><Text>Literal *title* &amp; quotes</Text></Paragraph><Paragraph Type="Author"><Text>Original author</Text></Paragraph></Content></TitlePage><Content><Paragraph Type="Action" StartsNewPage="Yes"><Text Style="Bold" RevisionID="5">Bold &amp; </Text><Text Style="Italic">literal *stars*</Text><ScriptNote Color="Blue"><Paragraph><Text>NOTE ONLY</Text></Paragraph></ScriptNote></Paragraph><DualDialogue><Paragraph Type="Character"><Text>Left</Text></Paragraph><Paragraph Type="Dialogue"><Text>First voice.</Text></Paragraph><Paragraph Type="Character"><Text>Right</Text></Paragraph><Paragraph Type="Dialogue"><Text>Second voice.</Text></Paragraph></DualDialogue></Content></FinalDraft>'''

class FDXDocumentTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='fdxdoc-',dir=ROOT/'t');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.projects=self.root/'projects';self.projects.mkdir();self.project=self.projects/'New Rich Project'
    def imported(self):return fdx.import_project(self.project,XML,OWNER,uuid.uuid4().hex)
    def bytes(self):return {path.relative_to(self.project).as_posix():path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
    def edited(self,read,index=2,text='First revised voice.',token='1'*32):
        document=json.loads(json.dumps(read['fdx_document']));block=document['blocks'][index]
        old=block['text'];start=len('First ');block['text']=text
        block['edit_operations']=[{'id':token,'before_text':old,'start':start,'end':start,'text':'revised '}]
        return document
    def test_parse_keeps_notes_out_of_body_and_retains_styles_duals_title_breaks(self):
        document=fdx.parse_fdx(XML)
        self.assertEqual([block['text'] for block in document['blocks']],['Bold & literal *stars*','Left','First voice.','Right','Second voice.'])
        self.assertEqual(document['blocks'][0]['runs'][0]['attributes'],{'Style':'Bold','RevisionID':'5'})
        self.assertEqual(document['blocks'][0]['notes'][0]['text'],'NOTE ONLY')
        self.assertTrue(document['blocks'][0]['startsNewPage']);self.assertEqual(document['blocks'][1]['dualSide'],'left');self.assertEqual(document['blocks'][3]['dualSide'],'right')
        self.assertEqual(document['title_page'][1]['text'],'Original author')
        content,spans=fdx.projection_with_spans(document)
        for span in spans:self.assertEqual(content[span['start']:span['end']],span['text'])
    def test_noop_and_export_keep_exact_original_bytes_and_all_files(self):
        read=self.imported();before=self.bytes()
        result=fdx.write_project(self.project,read['content'],read['revision'],read['fdx_document'],owner=OWNER)
        self.assertTrue(result['unchanged']);self.assertEqual(result['revision'],hashlib.sha256(XML).hexdigest())
        self.assertEqual(fdx.export_project(self.project,read['revision'],OWNER),XML)
        self.assertEqual(self.bytes(),before)
    def test_body_edit_save_reopen_preserves_unmodified_xml_and_original_versions(self):
        read=self.imported();document=self.edited(read)
        result=fdx.write_project(self.project,fdx.projection(document),read['revision'],document,owner=OWNER)
        self.assertFalse(result['unchanged']);reopened=fdx.read_project(self.project,OWNER)
        self.assertEqual(reopened['fdx_document']['blocks'][2]['text'],'First revised voice.')
        self.assertEqual(reopened['fdx_document']['blocks'][0]['runs'],read['fdx_document']['blocks'][0]['runs'])
        self.assertEqual(reopened['fdx_document']['blocks'][0]['notes'],read['fdx_document']['blocks'][0]['notes'])
        exported=fdx.export_project(self.project,result['revision'],OWNER)
        self.assertIn(b'<Unknown Flag="keep">inert</Unknown>',exported);self.assertIn(b'<DualDialogue>',exported)
        self.assertEqual(fdx.export_project(self.project,result['revision'],OWNER,original=True),XML)
        self.assertEqual((self.project/'fdx_versions'/read['revision']/'document.fdx').read_bytes(),XML)
        (self.project/'screenplay.fountain').write_text('STALE EXTERNAL PROJECTION',encoding='utf8')
        snapshot=fdx.read_canonical_snapshot(self.project,OWNER)
        self.assertIn('First revised voice.',snapshot['body_text']);self.assertNotIn('NOTE ONLY',snapshot['body_text'])
        self.assertNotIn('STALE EXTERNAL',snapshot['content']);self.assertEqual(snapshot['revision'],result['revision'])
        with self.assertRaises(fdx.FDXSourceError):fdx.read_canonical_snapshot(self.project,OTHER)
    def test_owner_stale_plaintext_structural_and_conflicting_ids_do_not_overwrite(self):
        read=self.imported();before=self.bytes()
        for operation,status in [(lambda:fdx.read_project(self.project,OTHER),403),
          (lambda:fdx.write_project(self.project,'new','stale',owner=OWNER),409),
          (lambda:fdx.write_project(self.project,'new',read['revision'],owner=OWNER),428)]:
            with self.assertRaises(fdx.FDXSourceError) as error:operation()
            self.assertEqual(error.exception.status,status)
        document=read['fdx_document'];document['blocks']=document['blocks'][:-1]
        with self.assertRaises(fdx.FDXSourceError):fdx.write_project(self.project,'new',read['revision'],document,owner=OWNER)
        self.assertEqual(self.bytes(),before)
    def test_unsupported_or_unqualified_edits_and_unsafe_xml_are_explicit(self):
        read=self.imported();document=read['fdx_document'];document['blocks'][0]['text']='silent plain replacement'
        with self.assertRaises(fdx.FDXSourceError):fdx.write_project(self.project,fdx.projection(document),read['revision'],document,owner=OWNER)
        with self.assertRaises(fdx.FDXSourceError):fdx.parse_fdx(b'<!DOCTYPE FinalDraft><FinalDraft><Content/></FinalDraft>')
    def test_shared_reader_reports_unknown_body_extraction_instead_of_claiming_complete(self):
        raw=XML.replace(b'<Content><Paragraph Type="Action"',b'<Content><UnqualifiedBody><Text>unmapped authored text</Text></UnqualifiedBody><Paragraph Type="Action"')
        fdx.import_project(self.project,raw,OWNER,uuid.uuid4().hex)
        result=fdx.read_canonical_snapshot(self.project,OWNER)
        self.assertFalse(result['body_extraction_complete']);self.assertTrue(result['body_extraction_warnings'])
        self.assertIn(b'unmapped authored text',fdx.export_project(self.project,result['revision'],OWNER))
    def test_pointer_failure_retains_old_current_and_retryable_new_version(self):
        read=self.imported();document=self.edited(read)
        with patch.object(fdx.os,'replace',side_effect=PermissionError('synthetic interruption')):
            with self.assertRaises(PermissionError):fdx.write_project(self.project,fdx.projection(document),read['revision'],document,owner=OWNER)
        self.assertEqual(fdx.read_project(self.project,OWNER)['revision'],read['revision'])
        result=fdx.write_project(self.project,fdx.projection(document),read['revision'],document,owner=OWNER)
        self.assertEqual(fdx.read_project(self.project,OWNER)['revision'],result['revision'])
    def test_readonly_runs_notes_title_dual_and_unknown_metadata_changes_are_rejected(self):
        read=self.imported();before=self.bytes()
        def changed(field):
            document=json.loads(json.dumps(read['fdx_document']))
            if field=='runs':document['blocks'][0]['runs'][0]['attributes']['Style']='Underline'
            elif field=='notes':document['blocks'][0]['notes'][0]['text']='altered note'
            elif field=='title':document['title_page'][0]['text']='changed title'
            elif field=='dual':document['blocks'][1]['dualSide']='right'
            elif field=='attribute':document['blocks'][0]['attributes']['Unqualified']='new metadata'
            elif field=='unknownblock':document['blocks'][0]['UnknownNode']={'changed':True}
            else:document['preserved_sections']=[]
            return document
        for field in ('runs','notes','title','dual','unknown','attribute','unknownblock'):
            with self.subTest(field=field),self.assertRaises(fdx.FDXSourceError):
                fdx.write_project(self.project,read['content'],read['revision'],changed(field),owner=OWNER)
        self.assertEqual(self.bytes(),before)

if __name__=='__main__':unittest.main()
