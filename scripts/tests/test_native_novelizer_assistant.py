"""Actual two dialog classes, offscreen Qt, mocked authenticated HTTP and queued workers."""
import ast
import hashlib
import html
import inspect
import json
import os
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import httpx
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtWidgets import QApplication,QFileDialog,QMessageBox,QWidget,QTextEdit
from native_studio.screenplay_client import ScreenplayClient

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'native_studio/screenwriting_modals.py'

def classes():
    tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    nodes=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom)) or
           isinstance(node,ast.ClassDef) and node.name in {'ScriptAssistantDialog','ScriptToBookNovelizerDialog'}]
    namespace={'__name__':'native_dialog_synthetic'}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),namespace)
    return namespace

class Bus:
    def __init__(self):self.jobs=[]
    def submit(self,fn,*args,on_result=None,on_error=None,**kwargs):
        job=dict(work=lambda:fn(*args,**kwargs),result=on_result,error=on_error);self.jobs.append(job)
        return types.SimpleNamespace(cancel_event=threading.Event())
    def drain(self):
        count=0
        while self.jobs:
            count+=1
            if count>30:raise AssertionError('Unexpected recurring native requests')
            job=self.jobs.pop(0)
            try:value=job['work']()
            except Exception as error:job['error'](str(error))
            else:job['result'](value)

class Server:
    def __init__(self):self.calls=[];self.fail=set();self.prose='Generated fixture prose.';self.saved={};self.query_status='success';self.completion_verified=True
    def receipt(self):return dict(schema='aibs.project_rag_snapshot.v2',project_name='Fixture',owner_hash='a'*64,
        project_hash=hashlib.sha256(b'Fixture').hexdigest(),snapshot_sha256='b'*64,complete=True,source_chunks=3,
        sources=[dict(type='script_scene',revision='c'*64,origin_sha256='d'*64)])
    def handle(self,request):
        body=json.loads(request.content) if request.content else {};path=request.url.path
        self.calls.append((path,body,dict(request.headers)))
        if path in self.fail:return httpx.Response(503,json={'detail':'Synthetic service unavailable'})
        if path.endswith('/stats'):return httpx.Response(200,json=dict(status='not_indexed',project_name='Fixture',total_docs=0,receipt=None))
        if path.endswith('/project-assistant/sync'):return httpx.Response(200,json=dict(status='success',project_name='Fixture',indexed_docs=3,receipt=self.receipt()))
        if path.endswith('/project-assistant/chat'):return httpx.Response(200,json=dict(status=self.query_status,response='<literal> quoted suggestion',provider='ollama',model='fixture',generation_verified=self.query_status=='success',receipt=self.receipt() if self.query_status=='success' else None,sources=[dict(label='source chunk',chunk_sha256='d'*64)] if self.query_status=='success' else []))
        if path.endswith('/ai/providers'):return httpx.Response(200,json={'active_provider':'local','providers':[{'id':'local','saved_model':'fixture'}]})
        if path.endswith('/group_chapters'):return httpx.Response(200,json={'source_project':'Fixture','source_kind':'bound_editor_text','source_revision':'c'*64,'chapters':[dict(chapter_number=i,title=f'Chapter {i}',combined_script=f'INT. FIXTURE {i} - DAY\nSynthetic scene.',scene_count=1,estimated_words=10,scenes=[{'heading':f'INT. FIXTURE {i} - DAY'}]) for i in (1,2)]})
        if '/get_drafts/' in path:return httpx.Response(200,json=dict(project_name='Fixture',chapters=list(self.saved.values())))
        if path.endswith('/convert_chapter'):return httpx.Response(200,json=dict(status='success',chapter_number=body['chapter_number'],chapter_title=body['chapter_title'],generation_verified=True,completion_verified=self.completion_verified,completion_reason='stop' if self.completion_verified else 'length',output_token_limit=2048,prose=self.prose,provider='ollama',model='fixture',word_count=len(self.prose.split()),factuality_verified=False,
            source=dict(project=body['project_name'],kind='caller_supplied_source',sha256=hashlib.sha256(body['scenes_text'].encode('utf-8')).hexdigest(),bytes=len(body['scenes_text'].encode('utf-8')),owner_scope_verified=True,canonical_revision_verified=False),context_budget=dict(basis='conservative_utf8_bytes_not_tokenizer_count',admitted_context=8192)))
        if path.endswith('/save_draft'):
            number=body['chapter_number'];revision='e'*64
            self.saved[number]=dict(chapter_number=number,chapter_title=body['chapter_title'],prose_content=body['prose_content'],revision=revision,word_count=len(body['prose_content'].split()))
            return httpx.Response(200,json=dict(status='saved',project_name='Fixture',chapter_number=number,revision=revision,request_id=body.get('request_id'),word_count=len(body['prose_content'].split())))
        if path.endswith('/export_book'):
            text='Saved fixture manuscript.'
            return httpx.Response(200,text=text,headers={'content-type':'text/markdown'})
        raise AssertionError('Unexpected native route '+path)

class NativeNovelizerAssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);cls.ns=classes()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.bus=Bus();self.server=Server();self.client=ScreenplayClient(transport=httpx.MockTransport(self.server.handle));self.dialogs=[]
        for guard in [patch('native_studio.screenplay_client.local_service_headers',return_value={'X-Admin-Key':'synthetic-only'}),
                      patch.object(QMessageBox,'information'),patch.object(QMessageBox,'warning'),patch.object(QMessageBox,'critical'),
                      patch('native_studio.screenplay_client._private_recovery_directory',side_effect=lambda path,*_:path.mkdir(parents=True,exist_ok=True))]:
            guard.start();self.addCleanup(guard.stop)
        self.addCleanup(lambda:[dialog.deleteLater() for dialog in self.dialogs])
    def assistant(self,**options):
        cls=self.ns['ScriptAssistantDialog'];kwargs=dict(project_name='Fixture')
        if 'client' in inspect.signature(cls).parameters:kwargs.update(client=self.client,bus=self.bus)
        kwargs.update(options);dialog=cls(**kwargs);dialog._client=self.client;dialog._bus=self.bus;self.dialogs.append(dialog);return dialog
    def novel(self,source='INT. FIXTURE - DAY\nOriginal source.',**options):
        cls=self.ns['ScriptToBookNovelizerDialog'];kwargs=dict(script_content=source,project_name='Fixture')
        if 'client' in inspect.signature(cls).parameters:kwargs.update(client=self.client,bus=self.bus,recovery_root=Path(self.temp.name)/'recovery')
        kwargs.update(options);dialog=cls(**kwargs);dialog._client=self.client;dialog._bus=self.bus;self.dialogs.append(dialog);return dialog

    def parent(self):
        parent=QWidget();parent._draft=types.SimpleNamespace(project='Fixture',revision='c'*64,dirty=False)
        parent.editor=QTextEdit(parent);parent.editor.setPlainText('Captured source.')
        self.addCleanup(parent.deleteLater);return parent

    def test_assistant_does_not_claim_connected_counts_without_current_receipt(self):
        dialog=self.assistant();self.bus.drain();status=dialog.lbl_vdb_status.text()
        self.assertNotIn('136',status);self.assertNotIn('4,280',status);self.assertNotIn('100%',status)
        self.assertIn('/api/screenwriting/project-assistant/stats',[c[0] for c in self.server.calls])

    def test_assistant_sync_uses_real_authenticated_route_and_exact_verified_count(self):
        dialog=self.assistant();self.bus.drain();dialog._sync_vector_db();self.bus.drain()
        self.assertIn('3',dialog.lbl_vdb_status.text());self.assertNotIn('136',dialog.lbl_vdb_status.text())
        call=next(c for c in self.server.calls if c[0].endswith('/project-assistant/sync'))
        self.assertEqual(call[1]['project_name'],'Fixture');self.assertEqual(call[2]['x-admin-key'],'synthetic-only')

    def test_assistant_model_output_is_literal_and_only_verified_suggestions_can_insert(self):
        dialog=self.assistant();self.bus.drain();seen=[];dialog.insert_requested.connect(seen.append)
        dialog.txt_input.setText('<query> voice');dialog._on_send_clicked();self.bus.drain()
        self.assertIn('<literal> quoted suggestion',dialog.chat_history.toPlainText());dialog._insert_last_response()
        self.assertEqual(seen,['<literal> quoted suggestion'])
        call=next(c for c in self.server.calls if c[0].endswith('/project-assistant/chat'))
        self.assertEqual(call[1]['model'],'fixture');self.assertEqual(call[1]['message'],'<query> voice')

    def test_assistant_failure_does_not_create_an_insertable_fallback(self):
        dialog=self.assistant();self.bus.drain();self.server.query_status='stale_index';seen=[];dialog.insert_requested.connect(seen.append)
        dialog.txt_input.setText('continuity');dialog._on_send_clicked();self.bus.drain();dialog._insert_last_response()
        self.assertEqual(seen,[]);self.assertNotIn('100% Continuity Verified',dialog.chat_history.toPlainText())

    def test_novelizer_missing_source_does_not_fabricate_highway_or_diner(self):
        self.server.fail.add('/api/novelizer/group_chapters');dialog=self.novel('');self.bus.drain()
        self.assertEqual(dialog.chapters,[]);self.assertNotIn('HIGHWAY',dialog.txt_compiled.toPlainText())

    def test_novelizer_generation_uses_backend_and_never_auto_saves(self):
        dialog=self.novel();self.bus.drain();dialog._convert_active_chapter();self.bus.drain()
        self.assertEqual(dialog.txt_prose.toPlainText(),self.server.prose)
        self.assertTrue(any(c[0].endswith('/convert_chapter') for c in self.server.calls))
        self.assertFalse(any(c[0].endswith('/save_draft') for c in self.server.calls))
        self.assertNotIn('weight of the moment',dialog.txt_prose.toPlainText())

    def test_chapter_navigation_and_late_generation_keep_newer_local_prose(self):
        dialog=self.novel();self.bus.drain();dialog._convert_active_chapter();dialog.txt_prose.setPlainText('My unsaved chapter one.')
        dialog.combo_chap_select.setCurrentIndex(1);dialog.txt_prose.setPlainText('My unsaved chapter two.');self.bus.drain()
        self.assertEqual(dialog.txt_prose.toPlainText(),'My unsaved chapter two.')
        dialog.combo_chap_select.setCurrentIndex(0);self.assertEqual(dialog.txt_prose.toPlainText(),'My unsaved chapter one.')
        self.assertEqual(dialog.chapters[0].get('candidate'),self.server.prose)

    def test_model_failure_and_enhancement_buttons_do_not_invent_memoir_evidence(self):
        dialog=self.novel();self.bus.drain();dialog.txt_prose.setPlainText('Only supported memoir facts.')
        before=dialog.txt_prose.toPlainText();self.server.fail.add('/api/novelizer/convert_chapter')
        dialog._convert_active_chapter();self.bus.drain();self.assertEqual(dialog.txt_prose.toPlainText(),before)
        dialog._inject_inner_monologue();dialog._enrich_sensory();self.assertEqual(dialog.txt_prose.toPlainText(),before)

    def test_real_save_captures_chapter_and_revision_and_preserves_edits_made_in_flight(self):
        self.server.saved[1]=dict(chapter_number=1,chapter_title='Authored title',prose_content='Earlier draft.',revision='a'*64,word_count=2)
        dialog=self.novel();self.bus.drain();dialog.txt_prose.setPlainText('Submitted prose.');dialog._save_active_chapter_draft()
        dialog.txt_prose.setPlainText('Newer prose while saving.');dialog.combo_chap_select.setCurrentIndex(1);self.bus.drain()
        call=next(c for c in self.server.calls if c[0].endswith('/save_draft'))
        self.assertEqual(call[1]['chapter_number'],1);self.assertEqual(call[1]['chapter_title'],'Authored title')
        self.assertEqual(call[1]['expected_revision'],'a'*64);self.assertRegex(call[1]['request_id'],'^[a-f0-9]{32}$')
        dialog.combo_chap_select.setCurrentIndex(0);self.assertEqual(dialog.txt_prose.toPlainText(),'Newer prose while saving.')
        self.assertEqual(dialog.chapters[0]['revision'],'e'*64);self.assertTrue(dialog.chapters[0]['dirty'])

    def test_save_failure_keeps_unsaved_text_and_never_claims_disk_save(self):
        dialog=self.novel();self.bus.drain();self.server.fail.add('/api/novelizer/save_draft')
        dialog.txt_prose.setPlainText('Retain this draft.');dialog._save_active_chapter_draft();self.bus.drain()
        self.assertEqual(dialog.txt_prose.toPlainText(),'Retain this draft.');self.assertTrue(dialog.chapters[0].get('dirty'))
        self.assertNotIn('Draft Saved',dialog.lbl_status.text())

    def test_local_html_export_escapes_literals_and_cannot_overwrite_existing_file(self):
        dialog=self.novel();self.bus.drain();dialog.txt_compiled.setPlainText('<script>literal prose</script> & text')
        target=Path(self.temp.name)/'book.html'
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(target),'HTML')):
            dialog._export_manuscript_file('html');self.bus.drain()
        raw=target.read_text(encoding='utf-8');self.assertNotIn('<script>',raw);self.assertIn('&lt;script&gt;',raw)
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(target),'HTML')):
            dialog.txt_compiled.setPlainText('A different draft');dialog._export_manuscript_file('html');self.bus.drain()
        self.assertEqual(target.read_text(encoding='utf-8'),raw)

    def test_close_retains_private_working_copy_without_writing_a_project(self):
        dialog=self.novel();self.bus.drain();dialog.txt_prose.setPlainText('A private unsaved draft.');dialog.done(0)
        records=list((Path(self.temp.name)/'recovery').glob('*.json'))
        self.assertTrue(records)
        self.assertIn('A private unsaved draft.',records[-1].read_text(encoding='utf-8'))

    def test_rich_source_uses_current_canonical_body_without_projection_or_notes(self):
        dialog=self.novel('PROJECTION HEADER\nPRIVATE NOTE',source_is_rich=True,source_revision='c'*64)
        self.bus.drain();call=next(c for c in self.server.calls if c[0].endswith('/group_chapters'))
        self.assertIsNone(call[1]['script_content']);self.assertIsNone(call[1]['script_project_name'])
        self.assertNotIn('PRIVATE NOTE',dialog.chapters[0]['source_text'])

    def test_dirty_rich_source_requires_explicit_text_working_copy(self):
        captured='Unsaved rich content and punctuation.'
        dialog=self.novel(captured,source_is_rich=True,source_dirty=True,source_revision='c'*64)
        self.bus.drain();self.assertEqual(self.server.calls,[]);self.assertEqual(dialog.script_content,captured)
        dialog.chk_working_copy.setChecked(True);self.bus.drain()
        call=next(c for c in self.server.calls if c[0].endswith('/group_chapters'))
        self.assertEqual(call[1]['script_content'],captured);self.assertEqual(call[1]['script_project_name'],'Fixture')

    def test_current_source_changes_during_sync_do_not_claim_current_index(self):
        parent=self.parent();dialog=self.assistant(parent=parent);self.bus.drain()
        dialog._sync_vector_db();parent.editor.setPlainText('Later unsaved source.');self.bus.drain()
        self.assertNotIn('Verified 3',dialog.lbl_vdb_status.text())

    def test_changed_native_project_blocks_new_generation_but_preserves_chapter(self):
        parent=self.parent();dialog=self.novel(parent=parent);self.bus.drain()
        dialog.txt_prose.setPlainText('Original project draft.');parent._draft.project='Different Project'
        dialog._convert_active_chapter();self.bus.drain()
        self.assertFalse(any(c[0].endswith('/convert_chapter') for c in self.server.calls))
        self.assertEqual(dialog.txt_prose.toPlainText(),'Original project draft.')

    def test_incomplete_generation_is_retained_without_claiming_a_complete_chapter(self):
        dialog=self.novel();self.bus.drain();self.server.completion_verified=False
        dialog._convert_active_chapter();self.bus.drain()
        self.assertEqual(dialog.txt_prose.toPlainText(),self.server.prose)
        self.assertIn('completion unverified',dialog.lbl_status.text().lower())
        self.assertIn('length',dialog.lbl_status.text().lower())
        self.assertIs(dialog.chapters[0]['generation_receipt']['completion_verified'],False)

    def test_prose_typed_before_plan_arrives_is_visible_and_explicitly_recoverable(self):
        dialog=self.novel();dialog.txt_prose.setPlainText('Typed before the plan arrived.');self.bus.drain()
        self.assertEqual(dialog.txt_prose.toPlainText(),'Typed before the plan arrived.')
        self.assertEqual(dialog._loose_prose,'Typed before the plan arrived.')
        dialog.combo_chap_select.setCurrentIndex(0);dialog._use_loose_prose()
        self.assertEqual(dialog.txt_prose.toPlainText(),'Typed before the plan arrived.')
        self.assertTrue(dialog.chapters[0]['dirty'])

    def test_closed_dialog_drops_late_generation_callback(self):
        dialog=self.novel();self.bus.drain();dialog._convert_active_chapter();dialog.done(0)
        before=dialog.txt_prose.toPlainText();self.bus.drain()
        self.assertEqual(dialog.txt_prose.toPlainText(),before)
        self.assertFalse(dialog._alive)

    def test_generation_retains_captured_source_provenance_without_claiming_canonical_revision(self):
        dialog=self.novel();self.bus.drain();dialog._convert_active_chapter();self.bus.drain()
        receipt=dialog.chapters[0]['generation_receipt']
        expected=hashlib.sha256(dialog.chapters[0]['source_text'].encode('utf-8')).hexdigest()
        self.assertEqual(receipt['source']['sha256'],expected)
        self.assertFalse(receipt['source']['canonical_revision_verified'])
        self.assertIn('canonical revision unverified',dialog.lbl_status.text().lower())

    def test_retry_after_uncertain_save_reuses_exact_request_identity_and_capture(self):
        dialog=self.novel();self.bus.drain();dialog.txt_prose.setPlainText('Retry this exact capture.')
        self.server.fail.add('/api/novelizer/save_draft');dialog._save_active_chapter_draft();self.bus.drain()
        first=next(c[1] for c in self.server.calls if c[0].endswith('/save_draft'))
        self.server.fail.clear();dialog._save_active_chapter_draft();self.bus.drain()
        calls=[c[1] for c in self.server.calls if c[0].endswith('/save_draft')]
        self.assertEqual(calls,[first,first]);self.assertFalse(dialog.chapters[0]['dirty'])

    def test_empty_source_failure_still_recovers_prose_typed_before_any_plan(self):
        self.server.fail.add('/api/novelizer/group_chapters');dialog=self.novel('');self.bus.drain()
        dialog.txt_prose.setPlainText('Keep pre-plan prose despite no source.');dialog.done(0)
        records=list((Path(self.temp.name)/'recovery').glob('*.json'))
        self.assertTrue(records)
        self.assertIn('Keep pre-plan prose despite no source.',records[-1].read_text(encoding='utf-8'))

    def test_source_edit_after_plan_blocks_stale_generation_even_with_same_project(self):
        parent=self.parent();dialog=self.novel(parent=parent,source_is_rich=True,source_revision='c'*64);self.bus.drain()
        parent.editor.setPlainText('Unsaved rich edit after planning.');parent._draft.dirty=True
        dialog._convert_active_chapter();self.bus.drain()
        self.assertFalse(any(c[0].endswith('/convert_chapter') for c in self.server.calls))
        self.assertIn('source',dialog.lbl_status.text().lower())

    def test_regroup_after_live_rich_edits_requires_explicit_current_text_working_copy(self):
        parent=self.parent();dialog=self.novel('Initial projection.',parent=parent,source_is_rich=True,source_revision='c'*64);self.bus.drain()
        dialog.txt_prose.setPlainText('Retain novel draft.');parent.editor.setPlainText('Current edited rich text.');parent._draft.dirty=True
        before=len(self.server.calls);dialog._parse_script_into_chapters();self.bus.drain();dialog._convert_active_chapter();self.bus.drain()
        self.assertEqual(len(self.server.calls),before)
        self.assertEqual(dialog.txt_prose.toPlainText(),'Retain novel draft.')
        self.assertFalse(dialog.chk_working_copy.isHidden())
        dialog.chk_working_copy.setChecked(True);self.bus.drain()
        call=[c for c in self.server.calls if c[0].endswith('/group_chapters')][-1]
        self.assertEqual(call[1]['script_content'],'Current edited rich text.')
        self.assertEqual(call[1]['script_project_name'],'Fixture')
        dialog._convert_active_chapter();self.bus.drain()
        self.assertTrue(any(c[0].endswith('/convert_chapter') for c in self.server.calls))
        self.assertEqual(dialog.txt_prose.toPlainText(),'Retain novel draft.')
        self.assertEqual(dialog.chapters[0]['candidate'],self.server.prose)

    def test_regroup_cannot_rebind_the_old_project_to_another_native_project(self):
        parent=self.parent();dialog=self.novel(parent=parent);self.bus.drain();before=len(self.server.calls)
        parent._draft.project='Different Project';parent.editor.setPlainText('Different project source.')
        dialog._parse_script_into_chapters();self.bus.drain()
        self.assertEqual(len(self.server.calls),before)
        self.assertEqual(dialog.project_name,'Fixture')
