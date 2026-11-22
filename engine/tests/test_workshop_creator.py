"""Opening Workshop contracts; synthetic typed fixtures, offscreen Qt, no GPU."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock,patch

from PyQt6.QtWidgets import QApplication,QTreeWidgetItem,QCheckBox,QPlainTextEdit
from PyQt6.QtCore import Qt
from native_studio.game_engine import content_commands as cmd
from native_studio.game_engine import workshop_fields as wf
from native_studio.game_engine.opening_fields import fixture_inspection_fields,require_inspection_reader
from native_studio.game_engine.content_view import ContentView,ChapterProjectDefinition
from native_studio.game_engine.content_client import ContentClient
from native_studio.game_engine.creator_client import CreatorClient,ClientError,_Pending,LIMIT
from native_studio.game_engine.creator_commands import Status,prepared_handle
from native_studio.game_engine.creator_wire import Opcode,Frame
from native_studio.game_engine.creator_payload import Scope,_Writer,_Reader
from native_studio.game_engine.content_preview import ContentSnapshot,ContentExportAssembly,ContentViewportClient
from native_studio.game_engine.content_play import ContentPlayClient
from native_studio.game_engine.content_proposals import ProposalContext,encode_proposal
from native_studio.game_engine.content_jobs import ContentProposalJobs

APP=QApplication.instance()or QApplication([])
CAP=wf.WORKSHOP_CAPABILITY
IDS=tuple('00000000-0000-4000-8000-'+format(i,'012x')for i in range(1,7))
SETTINGS='10000000-0000-4000-8000-000000000001'
SCOPE=Scope('synthetic-workshop','main','20000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000001')

def fixture(identity,role=False,modern=True,**changes):
    fields=dict(cmd._fixture_fields(cmd.CreateFixture(identity,'Synthetic '+identity[-1])))
    if modern:fields.update(inspection_text='',inspection_source='',inspection_action='')
    if role:fields[wf.WORKSHOP_ROLE_FIELD]=True
    fields.update(changes)
    return cmd.TypedRow(identity,'authoring.Fixture',fields['name'],tuple(sorted(fields.items())))

def settings(binding=None,profile='warm_beginning'):
    fields={'asset_profile':profile}
    if binding is not None:fields[wf.WORKSHOP_BINDING_FIELD]=binding
    return cmd.TypedRow(SETTINGS,'authoring.ChapterSettings','Synthetic settings',tuple(sorted(fields.items())))

def rows(bound=True):
    return (settings(wf.encode_workshop_binding(IDS[:5])if bound else None),)+tuple(fixture(i,bound)for i in IDS[:5])

def anchored(values,origin=(0.,0.,0.)):
    result=[]
    for row in values:
        if row.type_id=='authoring.ChapterSettings':
            fields=dict(row.fields)
            for axis,offset,value in zip('xyz',(-32.,.2,-25.),origin):fields['jenison_return.0.'+axis]=value+offset
            row=replace(row,fields=tuple(sorted(fields.items())))
        result.append(row)
    result.append(cmd.TypedRow('40000000-0000-4000-8000-000000000001','firstboot.PowerFault','Synthetic fault',tuple(('isolation_'+axis,value+offset)for axis,value,offset in zip('xyz',origin,(-34.,.2,-7.)))))
    result.append(cmd.TypedRow('50000000-0000-4000-8000-000000000001','firstboot.NPCQuest','Synthetic lamp',tuple(('lamp_'+axis,value+offset)for axis,value,offset in zip('xyz',origin,(-27.,.2,8.)))))
    return tuple(result)

def snapshot(flag=True,**changes):
    payload=b'opaque synthetic native snapshot'
    value=ContentSnapshot(SCOPE,1,4,'',SETTINGS,7,hashlib.sha256(payload).hexdigest(),payload,frozenset(IDS[:5]),asset_profile='warm-beginning',opening_workshop_authored=flag)
    return replace(value,**changes)if changes else value

def cleanup_client(client):
    client._process=None
    if hasattr(client,'_directory')and client._directory:client._directory.cleanup();client._directory=None
    if hasattr(client,'_stager'):client._stager.shutdown()
    client.deleteLater();APP.processEvents()

class WorkshopBindings(unittest.TestCase):
    def test_factory_relative_defaults_use_return_switch_and_lamp_anchors(self):
        centers=wf.workshop_default_centers(anchored(rows(False)))
        expected=((-35.45,1.45,-28.25),(-33.4,1.3,-6.9),(-42.5,1.55,-7.),(-34.,1.3,-8.25),(-25.6,1.35,7.1))
        for actual,wanted in zip(centers,expected):
            for a,b in zip(actual,wanted):self.assertAlmostEqual(a,b,places=5)
    def test_moved_board_and_independent_switch_lamp_anchors_translate_defaults(self):
        origin=(100.,5.,-80.);centers=wf.workshop_default_centers(anchored(rows(False),origin))
        base=wf.workshop_default_centers(anchored(rows(False)))
        for before,after in zip(base,centers):
            for a,b,shift in zip(before,after,origin):self.assertAlmostEqual(b,a+shift,places=4)
    def test_missing_duplicate_nonfinite_or_wrong_typed_anchors_reject_before_request(self):
        good=anchored(rows(False))
        bad=[rows(False),good[:-1],good+(good[-1],)]
        for value in (None,True,'0',float('nan'),float('inf'),1e100):
            fields=dict(good[0].fields);fields['jenison_return.0.x']=value
            bad.append((replace(good[0],fields=tuple(fields.items())),)+good[1:])
        for values in bad:
            with self.subTest(values=values),self.assertRaises(ValueError):wf.workshop_default_centers(values)
    def test_exact_closed_action_map_roundtrip(self):
        value=wf.encode_workshop_binding(IDS[:5])
        self.assertEqual(value,'AIBWORKSHOP 1\n'+''.join(i+'\n'for i in IDS[:5]))
        self.assertLessEqual(len(value.encode()),256)
        self.assertEqual(wf.decode_workshop_binding(value),IDS[:5])
        self.assertEqual(wf.decode_workshop_binding(''),())
        self.assertEqual(wf.workshop_bindings_from_rows(rows(),'warm-beginning'),IDS[:5])
    def test_malformed_binding_is_never_silently_legacy(self):
        value=wf.encode_workshop_binding(IDS[:5])
        invalid=(None,False,1,b'',value[:-1],value+'\n',value.replace('\n','\r\n'),value.replace(' 1\n',' 2\n'),
            value.replace(IDS[0],IDS[1]),value.replace(IDS[0],IDS[0].replace('4000','5000')),
            value.replace(IDS[0],IDS[0].replace('8000','A000')),'x'*257,'\ud800')
        for bad in invalid:
            with self.subTest(bad=repr(bad)),self.assertRaises(ValueError):wf.decode_workshop_binding(bad)
    def test_observation_extension_is_only_true_workshop21(self):
        for modern,count in ((False,17),(True,20)):
            row=fixture(IDS[0],modern=modern);self.assertEqual(len(row.fields),count);fixture_inspection_fields(row)
        row=fixture(IDS[0],True);self.assertEqual(len(row.fields),21);self.assertFalse(any(fixture_inspection_fields(row).values()))
        for bad in (fixture(IDS[0],True,modern=False),fixture(IDS[0],workshop_role=False),fixture(IDS[0],workshop_role=1),
            fixture(IDS[0],True,selectable=False),fixture(IDS[0],True,extra='unknown'),
            fixture(IDS[0],True,inspection_text='x',inspection_source='Synthetic',inspection_action='read')):
            with self.subTest(bad=bad),self.assertRaises(ValueError):fixture_inspection_fields(bad)
    def test_binding_ownership_profile_role_and_panel_invariants(self):
        good=rows()
        invalid=(good[:-1],good+(fixture(IDS[5],True),),good+(good[1],),
            (replace(good[0],type_id='authoring.Definition'),)+good[1:],
            (good[0],replace(good[1],type_id='authoring.AssetPlacement'))+good[2:],
            (settings(wf.encode_workshop_binding(IDS[:5]),'legacy_v1'),)+good[1:],
            (settings(''),)+good[1:],(settings(),)+good[1:],
            (good[0],fixture(IDS[0]))+good[2:],
            (good[0],fixture(IDS[0],True,selectable=False))+good[2:],
            (good[0],fixture(IDS[0],True,inspection_text='x',inspection_source='s',inspection_action='seat'))+good[2:],
            (replace(good[0],fields=good[0].fields+((wf.WORKSHOP_BINDING_FIELD,wf.encode_workshop_binding(IDS[:5])),)),)+good[1:])
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):wf.workshop_bindings_from_rows(bad,'warm-beginning')
        with self.assertRaises(ValueError):wf.workshop_bindings_from_rows(good,'legacy_v1')
    def test_legacy_absence_and_virtual_empty_need_no_capability(self):
        self.assertFalse(wf.opening_workshop_authored_from_rows(rows(False),'warm-beginning'))
        self.assertFalse(wf.opening_workshop_authored_from_rows((settings(''),fixture(IDS[0])),'warm-beginning'))
        self.assertFalse(wf.opening_workshop_authored_from_rows((fixture(IDS[0],modern=False),),'legacy_v1'))
    def test_runtime_progress_is_never_an_editable_observation(self):
        row=cmd.TypedRow(IDS[0],'firstboot.OpeningWorkshop','Runtime',(('has_probe',True),))
        with self.assertRaisesRegex(ValueError,'runtime progress'):wf.workshop_bindings_from_rows((row,),'warm-beginning')
    def test_group_create_then_bind_uses_only_legacy17_create(self):
        edits=[]
        for identity in IDS[:5]:edits.extend((cmd.CreateFixture(identity,'Synthetic'),cmd.SetField(identity,wf.WORKSHOP_ROLE_FIELD,True)))
        edits.append(cmd.SetField(SETTINGS,wf.WORKSHOP_BINDING_FIELD,wf.encode_workshop_binding(IDS[:5])))
        wf.validate_workshop_edits((settings(),),edits,'warm-beginning')
        packet=cmd.encode_scoped_edit(SCOPE,SETTINGS,'create-workshop',0,'a'*64,'Synthetic group',edits)
        parsed=cmd.decode_scoped_edit(packet)
        self.assertEqual(len(parsed.edits),11)
        self.assertTrue(all(len(cmd._fixture_fields(e))==17 for e in parsed.edits if isinstance(e,cmd.CreateFixture)))
        self.assertTrue(wf.edits_require_workshop(edits));self.assertTrue(wf.edits_publish_workshop(edits))
    def test_group_rebind_and_remove_keep_final_state_coherent(self):
        owned=rows()+(fixture(IDS[5]),)
        replacement=(IDS[5],)+IDS[1:5]
        wf.validate_workshop_edits(owned,(cmd.SetField(IDS[0],wf.WORKSHOP_ROLE_FIELD,False),cmd.SetField(IDS[5],wf.WORKSHOP_ROLE_FIELD,True),
            cmd.SetField(SETTINGS,wf.WORKSHOP_BINDING_FIELD,wf.encode_workshop_binding(replacement))),'warm-beginning')
        clear=tuple(cmd.SetField(i,wf.WORKSHOP_ROLE_FIELD,False)for i in IDS[:5])+(cmd.SetField(SETTINGS,wf.WORKSHOP_BINDING_FIELD,''),)
        wf.validate_workshop_edits(rows(),clear,'warm-beginning')
        self.assertFalse(wf.edits_publish_workshop(clear))
    def test_dangling_geometry_deletion_role_and_inspection_changes_reject(self):
        invalid=((cmd.EraseFixture(IDS[0]),),(cmd.SetField(IDS[0],'selectable',False),),
            (cmd.SetField(IDS[0],wf.WORKSHOP_ROLE_FIELD,False),),(cmd.SetField(SETTINGS,wf.WORKSHOP_BINDING_FIELD,''),),
            (cmd.SetField(IDS[0],'inspection_text','Read'),cmd.SetField(IDS[0],'inspection_source','Synthetic'),cmd.SetField(IDS[0],'inspection_action','read')),
            (cmd.SetField(IDS[0],wf.WORKSHOP_ROLE_FIELD,1),),(cmd.SetField(IDS[0],wf.WORKSHOP_BINDING_FIELD,''),),
            (cmd.SetField(SETTINGS,wf.WORKSHOP_ROLE_FIELD,True),))
        for edits in invalid:
            with self.subTest(edits=edits),self.assertRaises(ValueError):wf.validate_workshop_edits(rows(),edits,'warm-beginning')
        wf.validate_workshop_edits(rows(),(cmd.SetField(IDS[0],'x',12.),),'warm-beginning')
    def test_ai_cannot_forge_role_or_binding_even_with_forged_context(self):
        for key,value in ((wf.WORKSHOP_ROLE_FIELD,True),(wf.WORKSHOP_BINDING_FIELD,wf.encode_workshop_binding(IDS[:5]))):
            context=ProposalContext('p','main',SCOPE.world_id,SETTINGS,0,'a'*64,((IDS[0],key,'boolean'if type(value)is bool else'text'),))
            source=json.dumps({'version':1,'label':'Forged','edits':[{'entity_id':IDS[0],'field':key,'value':value}]})
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'grouped|Workshop'):encode_proposal(source,context,'forged')
    def test_ai_job_omits_role_map_and_rejects_breaking_bound_fixtures(self):
        client=SimpleNamespace(state='ready',generation=1,pending_count=0,head=SimpleNamespace(scope=SCOPE,head_revision=0),capabilities=frozenset([CAP]))
        jobs=ContentProposalJobs(client,lambda:(SETTINGS,'a'*64,rows()))
        job,prompt=jobs.begin();keys={key for obj in prompt['objects']for key in obj['fields']}
        self.assertFalse(keys&{wf.WORKSHOP_ROLE_FIELD,wf.WORKSHOP_BINDING_FIELD})
        bad=json.dumps({'version':1,'label':'Break selectable','edits':[{'entity_id':IDS[0],'field':'selectable','value':False}]})
        with self.assertRaises(ValueError):jobs.consume(job,bad)
        self.assertEqual(jobs.pending_count,1)

class WorkshopMetadataHistory(unittest.TestCase):
    def project(self,root):
        definition=ChapterProjectDefinition.create(root,'Synthetic project',asset_profile='warm-beginning')
        (root/'chapter.aiba').write_bytes(b'synthetic old native journal')
        return definition
    def test_legacy_metadata_v1_v2_bytes_stay_unchanged(self):
        for profile,version in (('legacy_v1',1),('warm-beginning',2)):
            with self.subTest(profile=profile),tempfile.TemporaryDirectory()as directory:
                d=ChapterProjectDefinition.create(directory,'p',asset_profile=profile)
                expected={'version':version,'project':'p','branch':'main'}
                if version==2:expected['asset_profile']=profile
                self.assertEqual(d.path.read_bytes(),(json.dumps(expected,ensure_ascii=False,indent=2)+'\n').encode())
                self.assertFalse(ChapterProjectDefinition.load(directory).opening_workshop)
    def test_v3_has_exact_typed_optin_warm_shape(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);d=self.project(root);guard=wf.WorkshopSaveGuard.prepare(d)
            loaded=ChapterProjectDefinition.load(root);self.assertTrue(loaded.opening_workshop)
            data=json.loads(guard.declared);self.assertEqual(data['version'],3)
            for change in ({'opening_workshop':1},{'opening_workshop':False},{'opening_workshop':'true'},
                {'asset_profile':'legacy_v1'},{'unexpected':True},{'version':True}):
                bad={**data,**change};d.path.write_text(json.dumps(bad),encoding='utf-8')
                with self.subTest(change=change),self.assertRaises(ValueError):ChapterProjectDefinition.load(root)
    def test_metadata_declared_and_fsynced_before_save_and_can_restore_only_unchanged(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);d=self.project(root);before=d.path.read_bytes()
            with patch('native_studio.game_engine.workshop_fields.os.fsync',wraps=__import__('os').fsync)as sync:
                guard=wf.WorkshopSaveGuard.prepare(d);self.assertTrue(sync.called)
            self.assertTrue(ChapterProjectDefinition.load(root).opening_workshop)
            self.assertTrue(guard.restore_if_uncommitted());self.assertEqual(d.path.read_bytes(),before)
    def test_changed_same_size_journal_never_downgrades(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);d=self.project(root);guard=wf.WorkshopSaveGuard.prepare(d)
            old=(root/'chapter.aiba').read_bytes();(root/'chapter.aiba').write_bytes(b'X'+old[1:])
            self.assertFalse(guard.restore_if_uncommitted());self.assertTrue(ChapterProjectDefinition.load(root).opening_workshop)
    def test_missing_oversized_or_unreadable_journal_never_downgrades(self):
        for condition in ('missing_before','missing_after','oversized_before','oversized_after','unreadable_after'):
            with self.subTest(condition=condition),tempfile.TemporaryDirectory()as directory:
                root=Path(directory);d=self.project(root);journal=root/'chapter.aiba'
                if condition=='missing_before':journal.unlink()
                elif condition=='oversized_before':journal.write_bytes(b'x'*(1024*1024+1))
                guard=wf.WorkshopSaveGuard.prepare(d)
                if condition=='missing_after':journal.unlink()
                elif condition=='oversized_after':journal.write_bytes(b'x'*(1024*1024+1))
                if condition=='unreadable_after':
                    with patch('native_studio.game_engine.workshop_fields._journal_fingerprint',return_value=None):self.assertFalse(guard.restore_if_uncommitted())
                else:self.assertFalse(guard.restore_if_uncommitted())
                self.assertTrue(ChapterProjectDefinition.load(root).opening_workshop)
    def test_foreign_metadata_and_concurrent_preparation_are_not_overwritten(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);d=self.project(root);guard=wf.WorkshopSaveGuard.prepare(d)
            foreign=guard.declared+b' ';d.path.write_bytes(foreign)
            self.assertFalse(guard.restore_if_uncommitted());self.assertEqual(d.path.read_bytes(),foreign)
            with self.assertRaisesRegex(ValueError,'changed'):wf.WorkshopSaveGuard.prepare(d)
    def test_saved_history_is_monotonic_after_current_binding_removed(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);d=self.project(root);wf.WorkshopSaveGuard.prepare(d)
            saved=ChapterProjectDefinition.load(root);before=saved.path.read_bytes()
            self.assertIsNone(wf.WorkshopSaveGuard.prepare(saved));self.assertEqual(saved.path.read_bytes(),before)
            self.assertFalse(wf.opening_workshop_authored_from_rows(rows(False),'warm-beginning'))
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{}}),self.assertRaisesRegex(ValueError,'history'):wf.require_workshop_host('old.exe',saved.opening_workshop)

def hello_frame(features):
    body=_Writer();body.text(';'.join(features));body.number(LIMIT,'I');body.number(8,'I')
    w=_Writer();w.number(1,'H');w.number(Status.OK,'H');w.text('hello')
    for value in ('','','',''):w.text(value)
    w.number(0,'Q');w.text('');w.number(0,'Q');w.text('');w.text('');w.number(False,'B');w.number(0,'Q');w.text('')
    w.number(0,'I');w.number(0,'Q');w.number(0,'Q');w.number(len(body.data),'I');w.append(bytes(body.data))
    return Frame(Opcode.HELLO,1,uuid.uuid4().bytes,0,bytes(w.data),True)

class WorkshopReaderGuards(unittest.TestCase):
    def test_host_static_preflight_precedes_process_construction(self):
        client=ContentClient();client.opening_workshop=True
        try:
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{}}),patch('native_studio.game_engine.creator_client.QProcess')as process,self.assertRaisesRegex(ValueError,'Host'):client.start('old.exe','C:/unused')
            process.assert_not_called();self.assertEqual(client.state,'closed');self.assertEqual(client.generation,0)
        finally:cleanup_client(client)
    def test_hello_rechecks_capability_before_ready_open_signal(self):
        for required,offered in ((True,False),(True,True),(False,False)):
            with self.subTest(required=required,offered=offered):
                client=ContentClient();process=object();client._process=process;client._generation=1;client._accepting=True
                client.opening_workshop=required;client._pending={1:_Pending(Opcode.HELLO,b'',b'',0,time.monotonic()+2)}
                ready=Mock();client.ready.connect(ready)
                try:
                    if required and not offered:
                        with self.assertRaises(ClientError):client._accept_frame(hello_frame(['chapter-authoring-v1']),process,1)
                        ready.assert_not_called();self.assertNotEqual(client.state,'ready')
                    else:
                        client._accept_frame(hello_frame(['chapter-authoring-v1']+([CAP]if offered else[])),process,1)
                        ready.assert_called_once();self.assertEqual(client.state,'ready')
                finally:cleanup_client(client)
    def test_host_no_new_launch_flag_and_strict_boolean(self):
        client=ContentClient()
        try:
            client.asset_profile='warm-beginning';client.opening_workshop=True
            self.assertEqual(client._launch_arguments('owned'),['--workspace','owned','--asset-profile','warm-beginning'])
            with self.assertRaises(ValueError):wf.require_workshop_host('old.exe',1)
        finally:cleanup_client(client)
    def test_snapshot_and_export_pin_current_requirement(self):
        self.assertFalse(snapshot(False).opening_workshop_authored)
        for bad in (1,None,'yes'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):snapshot(bad)
        with self.assertRaises(ValueError):snapshot(True,asset_profile='legacy_v1')
        s=snapshot();desc=cmd.ContentDescription(SETTINGS,7,s.fingerprint,False,6)
        assembly=ContentExportAssembly(s.scope,1,4,'',desc,s.entity_ids,asset_profile='warm-beginning',opening_workshop_authored=True)
        chunk=cmd.ContentExportChunk(SETTINGS,s.fingerprint,7,len(s.payload),0,s.payload)
        self.assertTrue(assembly.accept(chunk,s.scope,1,4,'').opening_workshop_authored)
        for bad in (1,None,'yes'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):ContentExportAssembly(s.scope,1,4,'',desc,(),opening_workshop_authored=bad)
    def test_reader_requirement_current_only_and_unknown_metadata_fails(self):
        with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{}}):
            with self.assertRaisesRegex(ValueError,'Workshop'):require_inspection_reader('old.exe',snapshot())
            require_inspection_reader('old.exe',snapshot(False))
        with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{CAP:True}}):require_inspection_reader('new.exe',snapshot())
    def test_player_and_preview_reject_before_files_or_launch(self):
        with tempfile.TemporaryDirectory()as directory:
            exe=Path(directory)/'reader.exe';exe.write_bytes(b'synthetic')
            for kind in ('play','preview'):
                client=ContentPlayClient()if kind=='play'else ContentViewportClient()
                try:
                    with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{}}),self.assertRaisesRegex(ValueError,'Workshop'):
                        if kind=='play':client.start(exe,snapshot())
                        else:client.start_content(exe,snapshot())
                    self.assertIsNone(client._directory)
                finally:cleanup_client(client)
    def test_running_replacement_keeps_old_bytes_and_tag(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);scene=root/'scene.aibv';scene.write_bytes(b'old pinned scene')
            client=ContentViewportClient();client._directory=SimpleNamespace(cleanup=lambda:None);client._path=root;client.state='ready';client._content_executable=Path('old.exe');client._tag=('old',)
            try:
                with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{}}),self.assertRaisesRegex(ValueError,'Workshop'):client.publish(SCOPE,4,'',snapshot())
                self.assertEqual(scene.read_bytes(),b'old pinned scene');self.assertEqual(client._tag,('old',));self.assertFalse((root/'scene.tmp').exists())
            finally:cleanup_client(client)
    def test_deferred_preview_rechecks_before_replacing_accepted_scene(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);scene=root/'scene.aibv';scene.write_bytes(b'accepted scene')
            client=ContentViewportClient();s=snapshot();client._directory=SimpleNamespace(cleanup=lambda:None)
            client._path=root;client.state='ready';client._content_executable=Path('old.exe');client._stage_active=(s,None,None);client._tag=('old',)
            try:
                with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{}}),patch.object(client,'_stage_failed')as failed:client._stage_ready('stage',{})
                failed.assert_called_once();self.assertIn('Workshop',failed.call_args.args[0]);self.assertEqual(scene.read_bytes(),b'accepted scene');self.assertEqual(client._tag,('old',))
            finally:cleanup_client(client)
    def test_deferred_callbacks_recheck_workshop_before_launch_or_replace(self):
        player=ContentPlayClient();player.snapshot=snapshot();player._staged_executable=Path('old.exe');player.state='staging'
        try:
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value={'features':{}}),patch('native_studio.game_engine.content_play.QProcess')as process,patch.object(player,'_stage_failed')as failed:player._stage_ready('stage',{})
            process.assert_not_called();failed.assert_called_once();self.assertIn('Workshop',failed.call_args.args[0])
        finally:cleanup_client(player)
    def test_highlevel_player_selection_requires_new_reader_only_for_current_rows(self):
        old=Path('C:/old.exe');new=Path('C:/new.exe')
        view=SimpleNamespace(rows=rows(),definition=SimpleNamespace(asset_profile='warm-beginning'),_binary_candidates=lambda name:(old,new))
        with patch('native_studio.game_engine.content_view.read_native_player_capabilities',side_effect=lambda path:{'features':{'first_boot_content_play':True,'chapter_asset_surfaces':True,**({CAP:True}if path==new else{})}}):
            self.assertEqual(ContentView._play_binary(view),new)
            view.rows=rows(False);self.assertEqual(ContentView._play_binary(view),old)

class WorkshopPanel(unittest.TestCase):
    def setUp(self):
        self.view=ContentView(Path('C:/not-executed.exe'))
        self.view.definition=SimpleNamespace(asset_profile='warm-beginning',opening_workshop=False)
        self.view.description=SimpleNamespace(definition_id=SETTINGS,fingerprint='a'*64)
        self.view.client._head=SimpleNamespace(scope=SCOPE,head_revision=4,checkpoint_id='',undo_depth=0,redo_depth=0)
        self.view.client._capabilities=frozenset([CAP])
        self.view.rows=anchored(rows(False)+(fixture(IDS[5]),))
        self.view._refresh_workshop_selectors()
        self.addCleanup(self.cleanup)
    def cleanup(self):
        self.view.definition=None;self.view.client._head=None;self.view.busy=False
        self.view.close();self.view.deleteLater();APP.processEvents()
    def test_five_selectors_and_explicit_preview_create17_group(self):
        self.assertEqual(len(self.view.workshop_selectors),5)
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_submit_packet',return_value=7)as submit:
            self.view.preview_workshop_create();call=submit.call_args;parsed=cmd.decode_scoped_edit(call.args[0])
            self.assertFalse(call.kwargs['apply_after_preview']);self.assertEqual(len(parsed.edits),11)
            self.assertEqual(sum(isinstance(e,cmd.CreateFixture)for e in parsed.edits),5)
            created=tuple(e for e in parsed.edits if isinstance(e,cmd.CreateFixture))
            self.assertEqual(tuple(e.center for e in created),wf.workshop_default_centers(self.view.rows))
            for e in created:
                for extent in e.half_extent:self.assertAlmostEqual(extent,.16,places=6)
                self.assertAlmostEqual(e.emission,.02,places=6)
            wf.validate_workshop_edits(self.view.rows,parsed.edits,'warm-beginning')
    def test_binding_replacement_demotes_old_role_and_remove_is_grouped(self):
        self.view.rows=rows()+(fixture(IDS[5]),)
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_submit_packet',return_value=7)as submit:
            self.view.preview_workshop_bindings((IDS[5],)+IDS[1:5]);edits=cmd.decode_scoped_edit(submit.call_args.args[0]).edits
            self.assertIn(cmd.SetField(IDS[0],wf.WORKSHOP_ROLE_FIELD,False),edits)
            self.view.preview_workshop_remove();clear=cmd.decode_scoped_edit(submit.call_args.args[0]).edits
            self.assertEqual(len(clear),6);wf.validate_workshop_edits(self.view.rows,clear,'warm-beginning')
    def test_unsupported_or_legacy_host_cannot_submit_new_roles(self):
        for condition in ('unsupported','legacy'):
            self.view.client._capabilities=frozenset()if condition=='unsupported'else frozenset([CAP])
            self.view.definition.asset_profile='legacy_v1'if condition=='legacy'else'warm-beginning'
            with self.subTest(condition=condition),patch.object(self.view,'_require_editable'),patch.object(self.view,'_send')as send,self.assertRaises(ValueError):self.view.preview_workshop_create()
            send.assert_not_called()
    def test_inspector_role_is_readonly_and_bound_delete_explains_action(self):
        self.view.rows=rows();row=self.view.rows[1];item=QTreeWidgetItem([row.name,row.type_id,row.uuid]);item.setData(0,Qt.ItemDataRole.UserRole,row.uuid)
        self.view.outliner.addTopLevelItem(item);self.view.outliner.setCurrentItem(item)
        editor=self.view.field_editors[wf.WORKSHOP_ROLE_FIELD];self.assertIsInstance(editor,QCheckBox);self.assertFalse(editor.isEnabled())
        with patch.object(self.view,'_require_editable'),self.assertRaisesRegex(ValueError,'tool.*rebind'):self.view.delete_selected()
    def test_changed_selector_after_preview_cannot_apply_old_token(self):
        self.view._token=str(uuid.uuid4());self.view._prepared_workshop_inputs=self.view._workshop_inputs()
        combo=self.view.workshop_selectors[0];combo.blockSignals(True);combo.setCurrentIndex(1);combo.blockSignals(False)
        with patch.object(self.view,'_require_editable'),patch.object(self.view,'_send')as send,self.assertRaisesRegex(ValueError,'selections changed'):self.view.apply_preview()
        send.assert_not_called();self.assertIsNone(self.view._token)
    def test_changed_selector_while_preview_pending_releases_prepared_group(self):
        inputs=self.view._workshop_inputs()
        self.view._tasks[66]=('workshop_preview',(self.view.selected_id,self.view._editor_inputs(),inputs))
        combo=self.view.workshop_selectors[0];combo.blockSignals(True);combo.setCurrentIndex(1);combo.blockSignals(False)
        w=_Writer()
        for _ in range(5):w.number(False,'B')
        w.number(0,'I');w.number(0,'I');w.text('Synthetic dependencies')
        reply=SimpleNamespace(status=Status.PREPARED,token=str(uuid.uuid4()),save_compatible=True,save_bytes=100,save_message='Compatible',body=bytes(w.data),scope=SCOPE,head_revision=4)
        with patch.object(self.view,'_send')as send:self.view._response(66,reply)
        self.assertIsNone(self.view._token);self.assertIn('changed',self.view.status.text());self.assertTrue(any(c.args[0]=='release'for c in send.call_args_list))
    def test_applied_workflow_history_survives_undo_current_rows(self):
        self.view._workshop_mutation_requests.add(42);self.view._tasks[42]=('mutate',None)
        reply=SimpleNamespace(status=Status.APPLIED,token='',scope=SCOPE,head_revision=5)
        with patch.object(self.view,'_begin_refresh')as refresh:self.view._response(42,reply)
        self.assertTrue(self.view._workshop_history_seen);refresh.assert_called_once()
        self.view.rows=rows(False);self.assertFalse(wf.opening_workshop_authored_from_rows(self.view.rows,'warm-beginning'))
        self.assertTrue(self.view._workshop_history_seen)
    def test_unknown_apply_failure_retains_conservative_history(self):
        self.view._workshop_mutation_requests.add(42)
        with patch.object(ContentView.__mro__[1],'_failed'):self.view._failed(42,'bad acknowledgement')
        self.assertTrue(self.view._workshop_history_seen)
    def test_save_predeclares_metadata_before_native_request_and_retains_on_bad_ack(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);self.view.definition=ChapterProjectDefinition.create(root,'Synthetic',asset_profile='warm-beginning')
            (root/'chapter.aiba').write_bytes(b'old journal');self.view._workshop_history_seen=True
            def send(*args,**kwargs):
                self.assertTrue(ChapterProjectDefinition.load(root).opening_workshop)
                self.assertEqual(args[1],Opcode.SAVE)
                (root/'chapter.aiba').write_bytes(b'changed committed journal')
                self.view._tasks[88]=('save',None);return 88
            with patch.object(self.view,'_require_editable'),patch.object(self.view,'_send',side_effect=send):self.view.save_world()
            with patch.object(ContentView.__mro__[1],'_failed'):self.view._failed(88,'bad acknowledgement')
            self.assertTrue(ChapterProjectDefinition.load(root).opening_workshop)
    def test_explicit_reject_restores_only_proven_unchanged_journal(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);self.view.definition=ChapterProjectDefinition.create(root,'Synthetic',asset_profile='warm-beginning')
            (root/'chapter.aiba').write_bytes(b'old journal');before=self.view.definition.path.read_bytes();self.view._workshop_history_seen=True
            with patch.object(self.view,'_require_editable'),patch.object(self.view,'_send'):self.view.save_world()
            self.view._finish_workshop_save(rejected=True)
            self.assertEqual(self.view.definition.path.read_bytes(),before);self.assertFalse(self.view.definition.opening_workshop)

if __name__=='__main__':unittest.main()
