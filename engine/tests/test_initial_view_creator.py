"""Initial-view reader requirements, with no native or GPU launches."""
import hashlib,json,tempfile,unittest,uuid
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine import opening_fields as fields
from native_studio.game_engine.content_commands import TypedRow,ContentDescription,ContentExportChunk
from native_studio.game_engine.content_preview import ContentSnapshot,ContentExportAssembly,ContentViewportClient
from native_studio.game_engine.content_play import ContentPlayClient
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.creator_payload import Scope
from test_opening_creator import fixture,UID,CAP
APP=QApplication.instance()or QApplication([])
VIEW_CAP='chapter-initial-view-v1'
KEY='hint.view.initial_target'
DEFINITION='1198e985-a431-422f-a2c7-25887e79c5a7'

def bound():return fixture(inspection_text='Synthetic opening panel',inspection_source='Synthetic provenance',inspection_action='read')
def settings(target=UID,*,profile='warm_beginning',include=True):
    pairs=[('asset_profile',profile)]if profile is not None else []
    if include:pairs.append((KEY,target))
    return TypedRow(DEFINITION,'authoring.ChapterSettings','Chapter settings',tuple(pairs))
def rows(target=UID):return (bound(),settings(target))
def snapshot(flag=False,*,inspections=True,profile='warm-beginning'):
    payload=b'owned native bytes';scope=Scope('p','main',str(uuid.uuid4()),'')
    return ContentSnapshot(scope,1,2,'',DEFINITION,2,hashlib.sha256(payload).hexdigest(),payload,frozenset([UID]),asset_profile=profile,authored_inspections=inspections,initial_view_authored=flag)
def caps(view=False):return {'features':{'first_boot_content_play':True,'chapter_asset_surfaces':True,CAP:True,**({VIEW_CAP:True}if view else{})}}
def tidy(client):
    client._process=None;client._stage_active=client._stage_pending=None
    if client._directory:client._directory.cleanup();client._directory=None
    client._path=None;client.state='closed';client._stager.shutdown();client.deleteLater();APP.processEvents()

class InitialViewCompatibility(unittest.TestCase):
    def test_a_player_selection_rejects013_inspection_only_reader_for_authored_view(self):
        old=Path('C:/old013.exe');new=Path('C:/new014.exe')
        view=SimpleNamespace(rows=rows(),definition=SimpleNamespace(asset_profile='warm-beginning'),_binary_candidates=lambda name:(old,new))
        with patch('native_studio.game_engine.content_view.read_native_player_capabilities',side_effect=lambda p:caps(p==new)):
            self.assertEqual(ContentView._play_binary(view),new)
            view.rows=(bound(),settings(include=False));self.assertEqual(ContentView._play_binary(view),old)
            view.rows=(bound(),settings(''));self.assertEqual(ContentView._play_binary(view),old)
    def test_same_pinned_metadata_derives_only_owned_selectable_inspection_target(self):
        self.assertTrue(fields.initial_view_authored_from_rows(rows(),'warm-beginning'))
        self.assertFalse(fields.initial_view_authored_from_rows((bound(),settings(include=False)),'warm-beginning'))
        self.assertFalse(fields.initial_view_authored_from_rows((bound(),settings('')),'warm-beginning'))
        self.assertFalse(fields.initial_view_authored_from_rows((fixture(modern=False),),'legacy_v1'))
    def test_invalid_native_metadata_is_rejected(self):
        invalid=[(bound(),settings(1)),(bound(),settings(UID.upper())),(bound(),settings('x'*4097)),(bound(),settings(str(uuid.uuid4()))),
            (bound(),settings(UID,profile='legacy_v1')),(bound(),settings(UID,profile=None)),(bound(),settings(''),settings('')),
            (bound(),replace(settings(),fields=(('asset_profile','warm_beginning'),(KEY,UID),(KEY,UID)))),
            (fixture(),settings()),(fixture(inspection_text='x',inspection_source='s',inspection_action='read',selectable=False),settings()),
            (fixture(modern=False),settings()),(bound(),replace(settings(),type_id='authoring.Definition')),
            (bound(),replace(bound(),type_id='authoring.AssetPlacement'),settings())]
        for value in invalid:
            with self.subTest(value=value),self.assertRaises(ValueError):fields.initial_view_authored_from_rows(value,'warm-beginning')
        with self.assertRaises(ValueError):fields.initial_view_authored_from_rows(rows(),'legacy_v1')
    def test_completed_page_rejects_bad_initial_metadata_before_publishing_rows(self):
        incoming=tuple(sorted((bound(),settings('not-a-uuid')),key=lambda row:row.uuid));prior=('previous visible rows',)
        view=SimpleNamespace(_tag=lambda reply:'pinned',_page_tag='pinned',_page_bytes=0,_page_rows=[],_page_uuids=set(),_cursor='',
            _validated_asset_profile=lambda values:'warm-beginning',rows=prior,_selected_after=None,selected_id=None,
            outliner=Mock(),_selection_changed=Mock(),status=SimpleNamespace(setText=Mock()),_refresh_message='Refreshed',client=SimpleNamespace(dirty=False),_controls=Mock(),document_changed=Mock(),_publish_viewport=Mock())
        reply=SimpleNamespace(body=b'synthetic',world_count=2,head_revision=2)
        with patch('native_studio.game_engine.content_view.decode_page',return_value=(incoming,incoming[-1].uuid,False)),self.assertRaises(ValueError):ContentView._receive_page(view,reply)
        self.assertIs(view.rows,prior);view._publish_viewport.assert_not_called();view.document_changed.emit.assert_not_called()
    def test_snapshot_and_export_append_strict_default_false_requirement(self):
        self.assertFalse(snapshot().initial_view_authored)
        for bad in (1,None,'yes'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):snapshot(bad)
        with self.assertRaises(ValueError):snapshot(True,profile='legacy_v1',inspections=False)
        s=snapshot(True);desc=ContentDescription(DEFINITION,2,s.fingerprint,False,2)
        a=ContentExportAssembly(s.scope,1,2,'',desc,[UID],asset_profile='warm-beginning',authored_inspections=True,initial_view_authored=True)
        chunk=ContentExportChunk(DEFINITION,s.fingerprint,2,len(s.payload),0,s.payload)
        self.assertTrue(a.accept(chunk,s.scope,1,2,'').initial_view_authored)
        for bad in (1,None,'yes'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):ContentExportAssembly(s.scope,1,2,'',desc,[UID],asset_profile='warm-beginning',initial_view_authored=bad)
        with self.assertRaises(ValueError):ContentExportAssembly(s.scope,1,2,'',desc,[UID],initial_view_authored=True)
    def test_assembly_rejects_stale_context_without_losing_owned_requirement(self):
        s=snapshot(True);desc=ContentDescription(DEFINITION,2,s.fingerprint,False,2)
        a=ContentExportAssembly(s.scope,1,2,'',desc,[UID],asset_profile='warm-beginning',authored_inspections=True,initial_view_authored=True)
        chunk=ContentExportChunk(DEFINITION,s.fingerprint,2,len(s.payload),0,s.payload)
        with self.assertRaises(ValueError):a.accept(chunk,s.scope,2,2,'')
        self.assertEqual(a.offset,0);self.assertTrue(a.initial_view_authored)
    def test_shared_reader_guard_checks_new_capability_independently(self):
        for flag in (True,False):
            s=snapshot(flag)
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps(False)):
                if flag:
                    with self.assertRaisesRegex(ValueError,'initial.view|Initial.view'):fields.require_inspection_reader(Path('old.exe'),s)
                else:fields.require_inspection_reader(Path('old.exe'),s)
        with self.assertRaises(ValueError):fields.require_inspection_reader('old.exe',SimpleNamespace(initial_view_authored='yes',authored_inspections=False))
        with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps(True)):fields.require_inspection_reader(Path('new.exe'),snapshot(True))
    def test_lowlevel_play_rejects_old_reader_before_staging_files_or_launch(self):
        with tempfile.TemporaryDirectory()as directory:
            exe=Path(directory)/'player.exe';exe.write_bytes(b'fixture');client=ContentPlayClient()
            try:
                with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps()),patch.object(client,'_launch')as launch,self.assertRaisesRegex(ValueError,'initial.view|Initial.view'):client.start(exe,snapshot(True))
                launch.assert_not_called();self.assertIsNone(client._directory)
            finally:tidy(client)
    def test_lowlevel_preview_rejects_old_reader_before_any_scene_write(self):
        client=ContentViewportClient()
        try:
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps()),patch.object(client,'_start_owned_content')as start,self.assertRaisesRegex(ValueError,'initial.view|Initial.view'):client.start_content('old.exe',snapshot(True))
            start.assert_not_called();self.assertIsNone(client._directory)
        finally:tidy(client)
    def test_running_publish_preserves_old_scene_and_direct_raw_guard(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);scene=root/'scene.aibv';scene.write_bytes(b'previous scene');client=ContentViewportClient();client._directory=SimpleNamespace(cleanup=lambda:None);client._path=root;client.state='ready';client._content_executable=Path('old.exe');s=snapshot(True)
            try:
                with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps()):
                    with self.assertRaisesRegex(ValueError,'initial.view|Initial.view'):client.publish(s.scope,s.revision,s.checkpoint_id,s)
                    with self.assertRaisesRegex(ValueError,'initial.view|Initial.view'):client._publish_raw(s)
                self.assertEqual(scene.read_bytes(),b'previous scene');self.assertFalse((root/'scene.tmp').exists())
            finally:tidy(client)
    def test_deferred_play_launch_rechecks_reader_after_staging(self):
        client=ContentPlayClient();client.snapshot=snapshot(True);client._staged_executable=Path('old.exe');client.state='staging'
        try:
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps()),patch('native_studio.game_engine.content_play.QProcess')as process,patch.object(client,'_stage_failed')as failed:client._stage_ready('stage',{'status':'passed'})
            process.assert_not_called();failed.assert_called_once();self.assertIn('initial',failed.call_args.args[0].lower())
        finally:tidy(client)
    def test_deferred_running_publish_rechecks_reader_before_replacing_scene(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);scene=root/'scene.aibv';scene.write_bytes(b'previous accepted scene');client=ContentViewportClient();s=snapshot(True)
            client._directory=SimpleNamespace(cleanup=lambda:None);client._path=root;client.state='ready';client._content_executable=Path('old013.exe');client._stage_active=(s,None,None);client._tag=('previous',s.scope,1,'')
            try:
                with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps()),patch.object(client,'_stage_failed')as failed:client._stage_ready('stage',{})
                failed.assert_called_once();self.assertIn('initial',failed.call_args.args[0].lower());self.assertEqual(scene.read_bytes(),b'previous accepted scene');self.assertEqual(client._tag,('previous',s.scope,1,''));self.assertFalse((root/'scene.tmp').exists())
            finally:tidy(client)
    def test_new_reader_play_accepts_pinned_bytes_and_plain_legacy_still_works(self):
        with tempfile.TemporaryDirectory()as directory:
            exe=Path(directory)/'player.exe';exe.write_bytes(b'fixture')
            for s,features in [(snapshot(True),caps(True)),(snapshot(False,inspections=False,profile='legacy_v1'),caps())]:
                client=ContentPlayClient()
                try:
                    with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=features),patch.object(client,'_launch')as launch:client.start(exe,s)
                    launch.assert_called_once();self.assertEqual((client._path/'chapter.aibd').read_bytes(),s.payload)
                finally:tidy(client)
    def test_deferred_preview_start_rechecks_reader_and_stale_context(self):
        client=ContentViewportClient();s=snapshot(True);client._stage_active=(s,None,(Path('old.exe'),None));client.state='staging';client._directory=SimpleNamespace(cleanup=lambda:None);client._path=Path('C:/unused');client._content_executable=Path('old.exe')
        try:
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps()),patch('native_studio.game_engine.creator_viewport.ViewportClient.start')as start,patch.object(client,'_stage_failed')as failed:client._stage_ready('stage',{})
            start.assert_not_called();failed.assert_called_once()
            client._stage_active=(s,None,(Path('new.exe'),None));client.context_valid=lambda item:False;client.state='staging'
            with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=caps(True)),patch.object(client,'_start_owned_content')as start,patch.object(client,'_stage_failed')as failed:client._stage_ready('stage',{})
            start.assert_not_called();self.assertIn('changed',failed.call_args.args[0].lower())
        finally:tidy(client)
    def test_new_reader_can_preview_and_old_reader_can_open_unbound_013_content(self):
        for flag,features in [(True,caps(True)),(False,caps())]:
            client=ContentViewportClient()
            try:
                with patch('native_studio.game_build_monitor.read_native_player_capabilities',return_value=features),patch.object(client,'_start_owned_content')as start:client.start_content('reader.exe',snapshot(flag))
                start.assert_called_once()
            finally:tidy(client)
    def test_highlevel_preview_selects_new_view_reader(self):
        with tempfile.TemporaryDirectory()as directory:
            old=Path(directory)/'old.exe';new=Path(directory)/'new.exe';old.write_bytes(b'old');new.write_bytes(b'new')
            view=SimpleNamespace(_content_snapshot=snapshot(True),viewport=SimpleNamespace(state='closed',start_content=Mock()),selected_id=None,_binary_candidates=lambda name:(old,new),_controls=lambda:None)
            with patch('native_studio.game_engine.content_view.read_native_player_capabilities',side_effect=lambda p:caps(p==new)):ContentView._use_snapshot(view,'preview')
            self.assertEqual(view.viewport.start_content.call_args.args[0],new)
    def test_same_native_head_context_includes_initial_view_flag(self):
        s=replace(snapshot(True),export_version=2);view=SimpleNamespace(definition=SimpleNamespace(asset_profile='warm-beginning'),description=ContentDescription(DEFINITION,2,s.fingerprint,False,2),client=SimpleNamespace(capabilities={'chapter-content-export-v2'},generation=1,head=SimpleNamespace(scope=s.scope,head_revision=2,checkpoint_id='')),rows=rows())
        self.assertTrue(ContentView._export_snapshot_matches(view,s));view.rows=rows('');self.assertFalse(ContentView._export_snapshot_matches(view,s))
    def test_export_pins_flag_and_requires_new_owner_capability(self):
        s=snapshot(True);view=SimpleNamespace(_require_editable=lambda:None,_closing_project=False,client=SimpleNamespace(capabilities={CAP,'chapter-content-export-v2'},generation=1,head=SimpleNamespace(scope=s.scope,head_revision=2,checkpoint_id='')),rows=rows(),definition=SimpleNamespace(asset_profile='warm-beginning',directory=Path('C:/unused')),description=ContentDescription(DEFINITION,2,s.fingerprint,False,2),_snapshot_is_current=lambda:False,_validated_asset_profile=lambda items:'warm-beginning',status=SimpleNamespace(setText=Mock()),_controls=Mock(),_request_export=Mock())
        with self.assertRaisesRegex(ValueError,'initial.view|Initial.view'):ContentView._begin_export(view,'preview')
        view.client.capabilities.add(VIEW_CAP);ContentView._begin_export(view,'preview');self.assertTrue(view._export.initial_view_authored);view._request_export.assert_called_once()
if __name__=='__main__':unittest.main()
