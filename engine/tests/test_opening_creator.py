"""Opening creator contracts; ordinary tests never launch a native/GPU process."""
import json,unittest,uuid,struct,hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication,QTreeWidgetItem,QPlainTextEdit,QComboBox
from PyQt6.QtCore import Qt
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine import content_commands as cmd
from native_studio.game_engine.content_jobs import ContentProposalJobs
from native_studio.game_engine.content_proposals import ProposalContext,encode_proposal
from native_studio.game_engine.content_ai import _schema
from native_studio.game_engine.creator_payload import Scope,_Reader,_Writer
from native_studio.game_engine.creator_commands import Status
APP=QApplication.instance()or QApplication([])
UID='5ea4d1b3-1c9c-4fd4-9c19-5d778e03bc72'
CAP='chapter-authored-inspections-v1'
KEYS=('inspection_text','inspection_source','inspection_action')
def fixture(*,modern=True,**changes):
    values=dict(cmd._fixture_fields(cmd.CreateFixture(UID,'Reading panel')))
    if modern:values.update(inspection_text='',inspection_source='',inspection_action='')
    values.update(changes)
    return cmd.TypedRow(UID,'authoring.Fixture',values['name'],tuple(sorted(values.items())))
def job_fixture(row,capabilities=()):
    scope=Scope('p','main',str(uuid.uuid4()),str(uuid.uuid4()))
    client=SimpleNamespace(state='ready',generation=1,pending_count=0,head=SimpleNamespace(scope=scope,head_revision=3),capabilities=frozenset(capabilities))
    context=(str(uuid.uuid4()),'a'*64,(row,))
    return ContentProposalJobs(client,lambda:context)
class WireAndProposalContracts(unittest.TestCase):
    def test_legacy_create_packet_matches_independent_preimage_golden(self):
        scope=Scope('p','main','023c59e9-ffca-4afd-803a-d906427bb880','')
        packet=cmd.encode_scoped_edit(scope,'f55ca18d-becf-4699-9e36-e5b7ee8ad0c6','legacy-create-fixture-golden',7,'a'*64,
            'Legacy geometry only',(cmd.CreateFixture(UID,'Plain fixture'),))
        self.assertEqual(len(packet),676)
        self.assertEqual(hashlib.sha256(packet).hexdigest(),'e2bd319e95b06a6f1373d4044112706f853c2613e3d219f8053deed39f12c88d')
    def test_twenty_fields_in_create_fixture_are_still_rejected(self):
        component=cmd._component(UID,'authoring.Fixture',fixture().fields)
        body=_Writer();body.number(1,'H');body.text('bad-create',True);body.number(0,'Q');body.text('a'*64);body.text('Wrong geometry');body.number(1,'I');body.number(1,'B');body.number(len(component),'I');body.append(component)
        packet=_Writer();packet.append(b'AIBP');packet.number(1,'H')
        for value in ('p','main',str(uuid.uuid4()),str(uuid.uuid4())):packet.text(value,True)
        packet.number(len(body.data),'I');packet.append(bytes(body.data))
        with self.assertRaises(ValueError):cmd.decode_scoped_edit(bytes(packet.data))
    def test_native_page_retains_separate17_and20_observations(self):
        for modern in (False,True):
            row=fixture(modern=modern);w=_Writer();w.text(UID);w.number(False,'B');w.number(1,'I');w.text(UID);w.text(row.type_id);w.text(row.name);w.number(len(row.fields),'I')
            for key,value in row.fields:w.text(key);cmd._value_writer(w,value)
            decoded,cursor,more=cmd.decode_page(bytes(w.data))
            self.assertEqual(decoded,(row,));self.assertEqual(len(decoded[0].fields),20 if modern else 17)
            self.assertEqual(cursor,UID);self.assertFalse(more)
    def test_create_fixture_is_still_exact17_and_roundtrips_unchanged(self):
        edit=cmd.CreateFixture(UID,'Plain fixture');fields=cmd._fixture_fields(edit)
        self.assertEqual(len(fields),17);self.assertFalse(set(KEYS)&dict(fields).keys())
        scope=Scope('p','main',str(uuid.uuid4()),'')
        packet=cmd.encode_scoped_edit(scope,str(uuid.uuid4()),'operation',0,'a'*64,'Create',(edit,))
        parsed=cmd.decode_scoped_edit(packet)
        self.assertEqual(len(parsed.edits),1)
        self.assertEqual(cmd._fixture_fields(parsed.edits[0]),fields)
        self.assertEqual(cmd.encode_scoped_edit(scope,parsed.definition_id,'operation',0,'a'*64,'Create',parsed.edits),packet)
    def test_modern20_observation_and_legacy17_are_explicitly_separate(self):
        self.assertEqual(cmd.fixture_inspection_fields(fixture()),dict.fromkeys(KEYS,''))
        self.assertEqual(cmd.fixture_inspection_fields(fixture(modern=False)),{})
        bad=fixture(extra_field='wrong')
        with self.assertRaises(ValueError):cmd.fixture_inspection_fields(bad)
    def test_partial_or_malformed_modern_observations_are_rejected(self):
        for changes in [dict(inspection_text='partial'),dict(inspection_text='x',inspection_source='s',inspection_action='complete_quest'),dict(inspection_text='x'*2049,inspection_source='s',inspection_action='read')]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):cmd.fixture_inspection_fields(fixture(**changes))
    def test_unsupported_host_does_not_offer_inspection_fields_to_ai(self):
        jobs=job_fixture(fixture());_,prompt=jobs.begin([UID])
        self.assertFalse(set(KEYS)&prompt['objects'][0]['fields'].keys())
        self.assertIn('x',prompt['objects'][0]['fields'])
    def test_supported_host_has_bounded_structured_inspection_schema(self):
        jobs=job_fixture(fixture(),[CAP]);_,prompt=jobs.begin([UID])
        context=ProposalContext.from_dict({**prompt['context'],'fields':[[UID,key,'text']for key in KEYS]})
        choices=_schema(context)['properties']['edits']['items']['oneOf']
        by_key={entry['properties']['field']['const']:entry['properties']['value']for entry in choices}
        self.assertEqual(by_key['inspection_text']['maxLength'],2048)
        self.assertEqual(by_key['inspection_source']['maxLength'],512)
        self.assertEqual(by_key['inspection_action']['enum'],['','read','seat'])
    def test_model_cannot_emit_outcome_actions_oversize_sources_or_control_text(self):
        context=ProposalContext('p','main',str(uuid.uuid4()),str(uuid.uuid4()),0,'a'*64,tuple((UID,key,'text')for key in KEYS))
        for field,value in [('inspection_action','award_quest'),('inspection_text','x'*2049),('inspection_source','é'*257),('inspection_text','bad\x01text')]:
            source=json.dumps({'version':1,'label':'Invalid','edits':[{'entity_id':UID,'field':field,'value':value}]})
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):encode_proposal(source,context,'model')
    def test_ai_partial_new_triple_rejects_and_valid_group_remains_a_native_preview(self):
        jobs=job_fixture(fixture(),[CAP]);job,_=jobs.begin([UID])
        partial=json.dumps({'version':1,'label':'Partial','edits':[{'entity_id':UID,'field':'inspection_text','value':'Reading'}]})
        with self.assertRaises(ValueError):jobs.consume(job,partial)
        source=json.dumps({'version':1,'label':'Panel','edits':[{'entity_id':UID,'field':k,'value':v}for k,v in zip(KEYS,('New fictional panel','Supplied source note','read'))]})
        parsed=cmd.decode_scoped_edit(jobs.consume(job,source))
        self.assertEqual(len(parsed.edits),3)
    def test_ai_existing_bound_text_edit_preserves_source_and_action(self):
        jobs=job_fixture(fixture(inspection_text='Old',inspection_source='Origin',inspection_action='seat'),[CAP]);job,_=jobs.begin([UID])
        source=json.dumps({'version':1,'label':'Change','edits':[{'entity_id':UID,'field':'inspection_text','value':'New authored text'}]})
        self.assertEqual(cmd.decode_scoped_edit(jobs.consume(job,source)).edits,(cmd.SetField(UID,'inspection_text','New authored text'),))
class OpeningCreatorUI(unittest.TestCase):
    def setUp(self):
        self.view=ContentView(Path('C:/unused.exe'));self.view.definition=SimpleNamespace(asset_profile='warm-beginning')
        self.view.description=SimpleNamespace(definition_id=str(uuid.uuid4()),fingerprint='a'*64)
        self.view.client._head=SimpleNamespace(scope=Scope('p','main',str(uuid.uuid4()),str(uuid.uuid4())),head_revision=3,checkpoint_id='',undo_depth=0,redo_depth=0)
        self.view.client._capabilities=frozenset([CAP]);self.addCleanup(self.cleanup)
    def cleanup(self):
        self.view.definition=None;self.view.client._head=None;self.view.busy=False;self.view.close();self.view.deleteLater();APP.processEvents()
    def select(self,row):
        self.view.rows=(row,);item=QTreeWidgetItem([row.name,row.type_id,row.uuid]);item.setData(0,Qt.ItemDataRole.UserRole,row.uuid)
        self.view.outliner.addTopLevelItem(item);self.view.outliner.setCurrentItem(item)
    def test_unbound_text_is_multiline_source_is_empty_and_actions_are_closed_choices(self):
        self.select(fixture())
        self.assertIsInstance(self.view.field_editors['inspection_text'],QPlainTextEdit)
        self.assertEqual(self.view.field_editors['inspection_source'].text(),'')
        action=self.view.field_editors['inspection_action'];self.assertIsInstance(action,QComboBox)
        self.assertEqual([action.itemData(i)for i in range(action.count())],['','read','seat'])
    def test_no_capability_displays_read_only_inspection_data(self):
        self.view.client._capabilities=frozenset();self.select(fixture())
        self.assertTrue(self.view.field_editors['inspection_source'].isReadOnly())
    def test_new_panel_is_one_create17_plus_three_setfields_with_explicit_preview(self):
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_submit_packet')as submit:
            self.view.preview_inspection_fixture('Reading panel','Authored reading','Echos Within paragraph332','read')
            call=submit.call_args;parsed=cmd.decode_scoped_edit(call.args[0])
            self.assertIsInstance(parsed.edits[0],cmd.CreateFixture);self.assertEqual(len(cmd._fixture_fields(parsed.edits[0])),17)
            self.assertEqual({e.field:e.value for e in parsed.edits[1:]},dict(zip(KEYS,('Authored reading','Echos Within paragraph332','read'))))
            self.assertFalse(call.kwargs['apply_after_preview']);self.assertTrue(call.kwargs['placement_preview'])
    def test_create_and_direct_inspection_edit_reject_missing_capability_or_legacy_profile(self):
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_submit_packet')as submit:
            self.view.client._capabilities=frozenset()
            with self.assertRaises(ValueError):self.view.preview_inspection_fixture('Panel','Text','Origin','read')
            with self.assertRaises(ValueError):self.view.submit_edits((cmd.SetField(UID,'inspection_text','Text'),),'Edit')
            submit.assert_not_called()
    def test_incomplete_manual_triple_cannot_leave_python_as_a_preview(self):
        self.select(fixture());self.view.field_editors['inspection_text'].setPlainText('Partial')
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_send')as send,self.assertRaises(ValueError):self.view.preview_selected()
        send.assert_not_called()
    def test_multibyte_limits_and_title_are_checked_before_creation(self):
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_submit_packet')as submit:
            for name,text,source,action in [('x'*257,'Text','Origin','read'),('Panel','é'*1025,'Origin','read'),('Panel','Text','é'*257,'seat'),('Panel','Text','Origin','open_door')]:
                with self.subTest(name=name),self.assertRaises(ValueError):self.view.preview_inspection_fixture(name,text,source,action)
            submit.assert_not_called()
    def test_clear_entire_triple_is_a_grouped_field_preview(self):
        self.select(fixture(inspection_text='Text',inspection_source='Origin',inspection_action='seat'))
        self.view.field_editors['inspection_text'].setPlainText('');self.view.field_editors['inspection_source'].setText('')
        self.view.field_editors['inspection_action'].setCurrentIndex(0)
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_controls'),patch.object(self.view,'_send')as send:
            self.view.preview_selected();payload=send.call_args.args[2]
            reader=_Reader(payload);reader.number('H');[reader.text()for _ in range(4)];packet=reader.read(reader.number('I'))
            parsed=cmd.decode_scoped_edit(packet);self.assertEqual(len(parsed.edits),3);self.assertTrue(all(e.value==''for e in parsed.edits))
    def test_creation_inputs_changed_while_native_preview_is_pending_release_it(self):
        original=self.view._inspection_creation_inputs()
        extra=(self.view.selected_id,self.view._editor_inputs(),UID,self.view.adopted_asset,self.view.asset_name_input.text(),original)
        self.view._tasks['preview-test']=('placement_preview',extra)
        self.view.inspection_source_input.blockSignals(True);self.view.inspection_source_input.setText('Changed while pending');self.view.inspection_source_input.blockSignals(False)
        w=_Writer()
        for _ in range(5):w.number(False,'B')
        w.number(0,'I');w.number(0,'I');w.text('No navigation change')
        reply=SimpleNamespace(status=Status.PREPARED,token=str(uuid.uuid4()),save_compatible=True,save_bytes=100,save_message='Compatible',body=bytes(w.data),scope=self.view.client.head.scope,head_revision=3)
        with patch.object(self.view,'_send')as send:
            self.view._response('preview-test',reply)
            self.assertIsNone(self.view._token);self.assertIn('changed',self.view.status.text());self.assertTrue(any(c.args[0]=='release'for c in send.call_args_list))
    def test_creation_inputs_changed_after_preview_cannot_apply_old_packet(self):
        self.view._prepared_placement_id=UID;self.view._token=str(uuid.uuid4())
        self.view._prepared_inspection_inputs=self.view._inspection_creation_inputs()
        self.view.inspection_source_input.blockSignals(True);self.view.inspection_source_input.setText('New provenance');self.view.inspection_source_input.blockSignals(False)
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_send')as send,self.assertRaisesRegex(ValueError,'changed'):
            self.view.apply_preview()
        self.assertIsNone(self.view._token);send.assert_not_called()
if __name__=='__main__':unittest.main()
