"""Native rich writer contracts, isolated source data and mocked HTTP only."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from native_studio.screenplay_client import ScreenplayClient,ScreenplayError,DraftSession

SOURCE='a'*64

def fixture(texts=None):
    texts=texts if texts is not None else [('b1','Action','He sees 🐈.'),('b2','Character','ALEX'),('b3','Dialogue','Hello.')]
    content='Title: Fixture\n\n';spans=[];blocks=[]
    for identifier,kind,text in texts:
        content+='\n\n' if kind!='Dialogue' else '\n'
        start=len(content);content+=text
        spans.append(dict(id=identifier,type=kind,start=start,end=len(content),text=text))
        blocks.append(dict(id=identifier,type=kind,text=text,runs=[dict(id=identifier+'-r0',text=text,attributes={'Style':'Bold'})],
                           notes=[dict(id=identifier+'-n0',text='Private note',attributes={})],editable=True,edit_operations=[]))
    return dict(project='Fixture',content=content,revision=SOURCE,projection_spans=spans,
                fdx_document=dict(schema='aibs_rich_fdx_v1',source_sha256=SOURCE,document_sha256=SOURCE,blocks=blocks,
                                  title_page=[dict(type='Title',text='Fixture')],preserved_sections=['HeaderAndFooter']),
                initialized=False,workflow_revision=0,active_branch='main',pending_operation=None)

def acknowledged(base,submitted,revision='b'*64):
    """Synthetic server projection of exactly the submitted literal blocks."""
    result=copy.deepcopy(base);document=copy.deepcopy(submitted);text='';spans=[];previous=0
    for original,block in zip(base['projection_spans'],document['blocks']):
        text+=base['content'][previous:original['start']];start=len(text);text+=block['text']
        spans.append(dict(id=block['id'],type=block['type'],start=start,end=len(text),text=block['text']))
        previous=original['end'];block['edit_operations']=[]
        if len(block.get('runs',[]))==1:block['runs'][0]['text']=block['text']
    text+=base['content'][previous:];document['document_sha256']=revision
    result.update(status='success',content=text,revision=revision,projection_spans=spans,fdx_document=document)
    return result

class RichNativeDraftTests(unittest.TestCase):
    def setUp(self):
        module=importlib.import_module('native_studio.rich_screenplay_draft')
        self.Draft=module.NativeRichDraft;self.Error=module.RichDraftError

    def test_single_unicode_edit_keeps_readonly_runs_and_notes(self):
        data=fixture();draft=self.Draft(data);original=copy.deepcopy(data['fdx_document'])
        draft.edit(data['content'].replace('🐈','🐕'))
        snapshot=draft.capture();block=snapshot['blocks'][0];operation=block['edit_operations'][0]
        self.assertEqual((operation['start'],operation['end'],operation['text']),(8,9,'🐕'))
        self.assertEqual(block['text'],'He sees 🐕.');self.assertEqual(operation['before_text'],'He sees 🐈.')
        self.assertEqual(block['runs'],original['blocks'][0]['runs']);self.assertEqual(block['notes'],original['blocks'][0]['notes'])
        self.assertEqual(data['fdx_document'],original)

    def test_cross_block_change_is_retained_but_not_submitted(self):
        data=fixture();draft=self.Draft(data);changed=data['content'].replace('🐈.\n\nALEX','another person')
        draft.edit(changed)
        with self.assertRaises(self.Error):draft.capture()
        self.assertEqual(draft.recovery_payload()['content'],changed)
        self.assertEqual(draft.recovery_payload()['fdx_document'],data['fdx_document'])

    def test_undo_unsupported_edit_restores_previous_safe_state(self):
        data=fixture();draft=self.Draft(data);draft.edit(data['content']+'\nNew paragraph')
        with self.assertRaises(self.Error):draft.capture()
        draft.edit(data['content']);self.assertEqual(draft.capture(),data['fdx_document'])

    def test_bad_projection_is_refused_before_loading(self):
        data=fixture();data['projection_spans'][0]['start']+=1
        with self.assertRaises(self.Error):self.Draft(data)

    def test_changed_readonly_block_is_not_editable(self):
        data=fixture();data['fdx_document']['blocks'][0]['editable']=False;draft=self.Draft(data)
        draft.edit(data['content'].replace('🐈','🐕'))
        with self.assertRaises(self.Error):draft.capture()

    def test_late_edit_is_rebased_after_ack_without_losing_it(self):
        data=fixture();draft=self.Draft(data);submitted=data['content'].replace('🐈','🐕')
        draft.edit(submitted);captured=draft.capture()
        draft.edit(submitted.replace('Hello.','Hello again.'))
        acknowledged=fixture();acknowledged['content']=submitted;acknowledged['revision']='b'*64
        acknowledged['fdx_document']['document_sha256']='b'*64
        acknowledged['fdx_document']['blocks'][0]['text']='He sees 🐕.'
        acknowledged['fdx_document']['blocks'][0]['runs'][0]['text']='He sees 🐕.'
        acknowledged['projection_spans'][0]['text']='He sees 🐕.'
        draft.acknowledge(acknowledged,captured)
        after=draft.capture()
        self.assertEqual(draft.content,submitted.replace('Hello.','Hello again.'))
        self.assertEqual(after['document_sha256'],'b'*64)
        self.assertFalse(after['blocks'][0]['edit_operations'])
        self.assertEqual(after['blocks'][2]['edit_operations'][0]['before_text'],'Hello.')

    def test_ack_with_different_structure_does_not_replace_local_draft(self):
        data=fixture();draft=self.Draft(data);draft.edit(data['content'].replace('🐈','🐕'));captured=draft.capture()
        changed=fixture();changed['fdx_document']['blocks'].pop()
        before=draft.content
        with self.assertRaises(self.Error):draft.acknowledge(changed,captured)
        self.assertEqual(draft.content,before)

    def test_combining_and_zwj_edits_use_codepoints_without_normalizing_other_text(self):
        data=fixture([('b1','Action','Cafe\u0301 👩🏽\u200d🚀 – keep “quotes”')]);draft=self.Draft(data)
        first=data['content'].replace('Cafe\u0301','Café');draft.edit(first)
        self.assertEqual(draft.capture()['blocks'][0]['edit_operations'][0]['text'],'é')
        draft.edit(first.replace('🚀','🔬'));snapshot=draft.capture();operation=snapshot['blocks'][0]['edit_operations'][-1]
        self.assertEqual(operation['start'],snapshot['blocks'][0]['edit_operations'][-1]['before_text'].index('🚀'))
        self.assertEqual(operation['end']-operation['start'],1)
        self.assertIn('👩🏽\u200d🔬 – keep “quotes”',draft.content)

    def test_full_body_text_deletion_and_reinsertion_keep_zero_span_and_metadata(self):
        data=fixture();draft=self.Draft(data);before=copy.deepcopy(data['fdx_document']['blocks'][0])
        empty=data['content'].replace('He sees 🐈.','');draft.edit(empty)
        state=draft.capture();span=draft.projection_spans[0]
        self.assertEqual(state['blocks'][0]['text'],'');self.assertEqual(span['start'],span['end'])
        self.assertEqual(state['blocks'][0]['notes'],before['notes']);self.assertEqual(state['blocks'][0]['runs'],before['runs'])
        draft.edit(empty[:span['start']]+'Reinserted body.'+empty[span['end']:])
        self.assertEqual(draft.capture()['blocks'][0]['text'],'Reinserted body.')

    def test_initial_empty_paragraph_accepts_literal_insertion(self):
        data=fixture([('b1','Action','')]);draft=self.Draft(data);draft.edit(data['content']+'🐈 literal text')
        self.assertEqual(draft.capture()['blocks'][0]['text'],'🐈 literal text')

    def test_capture_is_detached_from_external_readonly_metadata_mutations(self):
        draft=self.Draft(fixture());snapshot=draft.capture();snapshot['blocks'][0]['notes'][0]['text']='changed externally'
        snapshot['title_page'][0]['text']='changed externally'
        self.assertEqual(draft.capture()['blocks'][0]['notes'][0]['text'],'Private note')
        self.assertEqual(draft.capture()['title_page'][0]['text'],'Fixture')

    def test_title_only_edit_stays_recoverable_but_is_never_sent_as_body_edit(self):
        data=fixture();draft=self.Draft(data);changed=data['content'].replace('Title: Fixture','Title: Edited')
        draft.edit(changed)
        with self.assertRaises(self.Error):draft.capture()
        self.assertEqual(draft.recovery_payload()['content'],changed)
        self.assertEqual(draft.recovery_payload()['fdx_document'],data['fdx_document'])

    def test_invalid_top_level_snapshot_uses_the_public_rich_error(self):
        for value in ([],None,'not a document',42):
            with self.subTest(value=type(value).__name__),self.assertRaises(self.Error):self.Draft(value)

    def test_oversize_inline_edit_retains_safe_document_and_full_recovery_text(self):
        data=fixture();draft=self.Draft(data);safe=draft.capture();changed=data['content'].replace('He sees 🐈.','x'*2000)
        module=importlib.import_module('native_studio.rich_screenplay_draft')
        limit=len(json.dumps(safe,ensure_ascii=False).encode('utf-8'))+100
        with patch.object(module,'MAX_BYTES',limit):
            draft.edit(changed)
            with self.assertRaises(self.Error):draft.capture()
            recovery=draft.recovery_payload()
            self.assertEqual(recovery['content'],changed)
            self.assertEqual(recovery['fdx_document'],safe)

    def test_ack_cannot_change_readonly_title_or_notes(self):
        for kind in ('title','note'):
            with self.subTest(kind=kind):
                data=fixture();draft=self.Draft(data);draft.edit(data['content'].replace('🐈','🐕'));submitted=draft.capture()
                response=acknowledged(data,submitted)
                if kind=='title':response['fdx_document']['title_page'][0]['text']='Unrequested title'
                else:response['fdx_document']['blocks'][0]['notes'][0]['text']='Unrequested note'
                before=draft.recovery_payload()
                with self.assertRaises(self.Error):draft.acknowledge(response,submitted)
                self.assertEqual(draft.recovery_payload(),before)

    def test_malformed_submitted_ack_document_has_a_public_error_and_no_mutation(self):
        data=fixture();draft=self.Draft(data);response=acknowledged(data,draft.capture());before=draft.recovery_payload()
        with self.assertRaises(self.Error):draft.acknowledge(response,[])
        self.assertEqual(draft.recovery_payload(),before)


class RichNativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.session=DraftSession(recovery_root=Path(self.temp.name)/'recovery');self.data=fixture();self.session.load(self.data)

    def test_ack_replays_multiple_newer_edits_in_the_same_paragraph(self):
        session=self.session;session.content=self.data['content'].replace('🐈','🐕');submitted_text=session.content;submitted=session.capture_rich_snapshot()
        session.content=session.content.replace('🐕','🐈 again');session.content=session.content.replace('again','once more')
        newer=session.content;session.saved(submitted_text,acknowledged(self.data,submitted),submitted)
        self.assertEqual(session.content,newer);self.assertTrue(session.dirty);self.assertEqual(session.baseline,submitted_text)
        operations=session.capture_rich_snapshot()['blocks'][0]['edit_operations'];self.assertEqual(len(operations),2)
        self.assertEqual(operations[0]['before_text'],'He sees 🐕.')
        self.assertEqual(session.revision,'b'*64)

    def test_structural_edit_during_save_is_retained_with_acknowledged_safe_state(self):
        session=self.session;session.content=self.data['content'].replace('🐈','🐕');text=session.content;submitted=session.capture_rich_snapshot()
        session.content=text+'\nA new unsupported paragraph';unsupported=session.content
        session.saved(text,acknowledged(self.data,submitted),submitted)
        self.assertEqual(session.content,unsupported);self.assertTrue(session.dirty)
        with self.assertRaises(ScreenplayError):session.capture_rich_snapshot()
        self.assertEqual(session.rich.recovery_payload()['fdx_document']['document_sha256'],'b'*64)

    def test_missing_or_wrong_project_ack_retains_every_local_field_and_marks_uncertain(self):
        session=self.session;session.content=self.data['content'].replace('🐈','🐕');text=session.content;submitted=session.capture_rich_snapshot()
        response=acknowledged(self.data,submitted);response['project']='Different project'
        before=(session.project,session.revision,session.content,session.baseline,session.capture_rich_snapshot())
        with self.assertRaises(ScreenplayError):session.saved(text,response,submitted)
        self.assertEqual((session.project,session.revision,session.content,session.baseline,session.capture_rich_snapshot()),before)
        self.assertTrue(session.uncertain)

    def test_missing_rich_ack_and_failed_reload_keep_the_existing_session(self):
        session=self.session;session.content=self.data['content'].replace('🐈','🐕');submitted=session.capture_rich_snapshot();text=session.content
        response=acknowledged(self.data,submitted);response.pop('projection_spans')
        with self.assertRaises(ScreenplayError):session.saved(text,response,submitted)
        before=(session.project,session.revision,session.content,session.capture_rich_snapshot())
        invalid=fixture();invalid['projection_spans'][0]['start']=True
        with self.assertRaises(ScreenplayError):session.load(invalid)
        self.assertEqual((session.project,session.revision,session.content,session.capture_rich_snapshot()),before)

    def test_rich_recovery_contains_operations_and_blocked_full_draft_in_unique_files(self):
        session=self.session;session.content=self.data['content'].replace('🐈','🐕');session.content+='\nUnsaved structural addition'
        def directory(path,*_):path.mkdir(parents=True,exist_ok=True)
        with patch('native_studio.screenplay_client._private_recovery_directory',side_effect=directory):
            first=session.preserve();self.assertEqual(session.preserve(),first)
            record=json.loads(first.read_bytes());self.assertEqual(record['content'],session.content)
            self.assertEqual(record['rich_draft']['content'],session.content);self.assertTrue(record['rich_draft']['blocked_reason'])
            self.assertEqual(record['rich_draft']['fdx_document']['blocks'][0]['edit_operations'][0]['before_text'],'He sees 🐈.')
            session.content+=' more';second=session.preserve();self.assertNotEqual(first,second)
            self.assertEqual(json.loads(first.read_bytes()),record)

class NativeRawImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.headers=patch('native_studio.screenplay_client.local_service_headers',return_value={'X-Admin-Key':'synthetic-only'})
        self.headers.start();self.addCleanup(self.headers.stop)

    def test_fdx_uses_raw_source_route_and_preserves_exact_bytes(self):
        raw=b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?><FinalDraft Version="6"><Content><Paragraph Type="Action"><Text Style="Bold">A &amp; B</Text></Paragraph></Content></FinalDraft>'
        path=Path(self.temp.name)/'input.fdx';path.write_bytes(raw);seen=[]
        def handle(request):
            seen.append(request)
            return httpx.Response(200,json={'status':'success','project':'Fixture','source':{'format':'fdx','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}})
        client=ScreenplayClient(transport=httpx.MockTransport(handle));self.assertEqual(client.import_file('Fixture',path),'Fixture')
        self.assertEqual(seen[0].url.path,'/api/screenwriting/projects/import-fdx-source')
        self.assertIn(raw,seen[0].content);self.assertIn(b'name="request_id"',seen[0].content)
        self.assertEqual(path.read_bytes(),raw)

    def test_wrong_source_hash_is_not_an_import_success(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text>Hi</Text></Paragraph></Content></FinalDraft>'
        path=Path(self.temp.name)/'input.fdx';path.write_bytes(raw)
        client=ScreenplayClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'status':'success','project':'Fixture','source':{'format':'fdx','sha256':'0'*64,'bytes':len(raw)}})))
        with self.assertRaises(ScreenplayError):client.import_file('Fixture',path)

    def test_rich_save_transmits_explicit_typed_snapshot(self):
        sent=[]
        def handle(request):
            sent.append(json.loads(request.content));return httpx.Response(200,json={'status':'success','project':'Fixture','revision':'b'*64})
        data=fixture();client=ScreenplayClient(transport=httpx.MockTransport(handle))
        client.save('Fixture',data['content'],SOURCE,fdx_document=data['fdx_document'])
        self.assertEqual(sent[0]['fdx_document'],data['fdx_document'])

if __name__=='__main__':unittest.main(verbosity=2)
