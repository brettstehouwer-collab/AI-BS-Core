"""Saved Play UI admission and close ownership, with no native/GPU launch."""
import hashlib, tempfile, unittest, uuid
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView,ChapterProjectDefinition
from native_studio.game_engine.content_preview import ContentSnapshot
from native_studio.game_engine.content_commands import ContentDescription
from native_studio.game_engine.creator_payload import Scope
from native_studio.game_engine.saved_chapter_export import SavedChapterExportResult,hash_saved_journal

APP=QApplication.instance()or QApplication([])
CAP='chapter-saved-play-v1'
def uid():return str(uuid.uuid4())

class SavedUI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'chapter.aiba').write_bytes(b'owned native test journal')
        self.view=ContentView(self.root/'host.exe');self.realclient=self.view.client
        payload=b'owned content';scope=Scope('p','main',uid(),uid());checkpoint=uid()
        self.snapshot=ContentSnapshot(scope,2,3,checkpoint,uid(),5,hashlib.sha256(payload).hexdigest(),payload,
            frozenset(),asset_store=self.root/'assets/packs',export_version=2)
        self.view.definition=ChapterProjectDefinition(self.root,'p','main')
        self.head=SimpleNamespace(scope=scope,head_revision=3,checkpoint_id=checkpoint,undo_depth=0,redo_depth=0)
        self.client=SimpleNamespace(state='ready',head=self.head,generation=2,pending_count=0,dirty=False,
            uncertain_operations=(),capabilities=frozenset({'chapter-content-export-v2'}),stop=Mock())
        self.view.client=self.client;self.view.description=ContentDescription(self.snapshot.definition_id,5,self.snapshot.fingerprint,False,0)
        self.view._snapshot_tag=self.view._tag(self.head);self.view.loaded=True;self.view.busy=False
        self.view._content_snapshot=self.snapshot;self.view._saved_play_binary=Mock(return_value=self.root/'player.exe')
    def tearDown(self):
        self.view.client=self.realclient;self.view.definition=None;self.view.loaded=False;self.view.busy=False
        self.view._closing_project=False;self.view._close_callback=None
        for client in (self.view.play,self.view.saved_play,self.view.viewport):
            client.state='closed';client._stager.shutdown()
        self.view.asset_client.shutdown();self.view.saved_export.stop();self.view.deleteLater();APP.processEvents();self.tmp.cleanup()
    def test_separate_button_and_clear_retention_label(self):
        self.view._controls();self.assertEqual(self.view.saved_play_button.text(),'Play saved chapter')
        self.assertTrue(self.view.saved_play_button.isEnabled());self.assertIn('retained',self.view.saved_play_status.text().lower())
    def test_start_never_saves_and_exports_current_snapshot_first(self):
        self.view._begin_export=Mock();self.view.save_world=Mock();self.view.start_saved_play()
        self.view._begin_export.assert_called_once_with('saved_play');self.view.save_world.assert_not_called()
    def test_dirty_owner_disabled_and_rejected_without_auto_save(self):
        self.client.dirty=True;self.view._controls();self.assertFalse(self.view.saved_play_button.isEnabled())
        with self.assertRaisesRegex(ValueError,'Save'):self.view.start_saved_play()
    def test_dirty_native_description_rejected(self):
        self.view.description=replace(self.view.description,dirty=True)
        with self.assertRaises(ValueError):self.view.start_saved_play()
    def test_empty_saved_checkpoint_rejected(self):
        self.head.checkpoint_id='';self.view._snapshot_tag=self.view._tag(self.head)
        with self.assertRaises(ValueError):self.view.start_saved_play()
    def test_uncertain_or_pending_native_operations_rejected(self):
        for key,value in [('pending_count',1),('uncertain_operations',(object(),))]:
            old=getattr(self.client,key);setattr(self.client,key,value)
            with self.subTest(key=key),self.assertRaises(ValueError):self.view.start_saved_play()
            setattr(self.client,key,old)
    def test_stale_visible_rows_rejected(self):
        self.head.head_revision=4
        with self.assertRaises(ValueError):self.view.start_saved_play()
    def test_old_host_complete_export_required_even_for_legacy_content(self):
        self.client.capabilities=frozenset()
        with self.assertRaisesRegex(ValueError,'complete'):self.view.start_saved_play()
    def test_old_player_rejected_before_any_export(self):
        self.view._saved_play_binary.return_value=None;self.view._begin_export=Mock()
        with self.assertRaisesRegex(ValueError,'saved'):self.view.start_saved_play()
        self.view._begin_export.assert_not_called()
    def test_isolated_session_conflict_preserves_existing_play(self):
        self.view.play.state='ready'
        with self.assertRaises(ValueError):self.view.start_saved_play()
        self.assertEqual(self.view.play.state,'ready')
    def test_second_owner_starts_with_original_pin_not_player(self):
        self.view.saved_export.start=Mock();self.view.saved_play.start=Mock();self.view._use_snapshot('saved_play')
        self.view.saved_export.start.assert_called_once();self.view.saved_play.start.assert_not_called()
        self.assertTrue(self.view.busy);args=self.view.saved_export.start.call_args
        self.assertEqual(args.args[1:],(self.view.definition,self.snapshot));self.assertTrue(args.kwargs['context_valid']())
    def test_verified_export_launches_only_after_reader_is_closed(self):
        self.view.saved_play.start=Mock();self.view._saved_exporting=True;self.view.busy=True
        result=SavedChapterExportResult(self.snapshot,hash_saved_journal(self.root).sha256,len(b'owned native test journal'))
        self.view._saved_export_completed(result);self.view.saved_play.start.assert_called_once()
        args=self.view.saved_play.start.call_args;self.assertEqual(args.args,(self.root/'player.exe',self.snapshot,self.root));self.assertTrue(args.kwargs['context_valid']())
        (self.root/'chapter.aiba').write_bytes(b'external replacement');self.assertFalse(args.kwargs['context_valid']())
    def test_late_completion_cannot_launch_after_close(self):
        self.view.saved_play.start=Mock();self.view._closing_project=True;self.view._saved_exporting=True
        self.view._saved_export_completed(SavedChapterExportResult(self.snapshot,'0'*64,1))
        self.view.saved_play.start.assert_not_called()
    def test_second_owner_failure_releases_ui_busy_without_starting_player(self):
        self.view._saved_exporting=True;self.view.busy=True;self.view.saved_play.start=Mock()
        self.view._saved_export_failed('Saved journal changed');self.assertFalse(self.view.busy)
        self.assertIn('changed',self.view.saved_play_status.text());self.view.saved_play.start.assert_not_called()
    def test_selection_skips_old_player_and_preserves_isolated_compatibility(self):
        old=self.root/'old.exe';new=self.root/'new.exe'
        def caps(path):return {'features':{'first_boot_content_play':True,**({CAP:True}if path==new else{})}}
        fake=SimpleNamespace(rows=(),definition=self.view.definition,_binary_candidates=lambda name:(old,new))
        with patch('native_studio.game_engine.content_view.read_native_player_capabilities',side_effect=caps):
            self.assertEqual(ContentView._saved_play_binary(fake),new)
            self.assertEqual(ContentView._play_binary(fake),old)
    def test_project_close_stops_saved_children_before_owner(self):
        self.view.saved_play.state='ready';self.view.saved_play.stop=Mock()
        self.view.close_project();self.view.saved_play.stop.assert_called_once();self.client.stop.assert_not_called()
        self.view.saved_play.state='closed';self.view._saved_play_closed();self.client.stop.assert_called_once()
    def test_stop_saved_export_cancels_reader_without_touching_authoring_save(self):
        self.view.saved_export.stop=Mock();self.view.saved_play.stop=Mock();self.view.save_world=Mock()
        self.view.stop_saved_play();self.view.saved_export.stop.assert_called_once();self.view.saved_play.stop.assert_called_once();self.view.save_world.assert_not_called()
    def test_prepare_close_waits_for_pending_second_reader_join(self):
        closed=[];self.view.saved_export.state='reading';self.view.saved_export.stop=Mock()
        self.view._saved_exporting=True;self.view.busy=True
        self.assertFalse(self.view.prepare_close(lambda:closed.append(True)))
        self.view.saved_export.stop.assert_called_once();self.assertEqual(closed,[]);self.client.stop.assert_not_called()
        self.view.saved_export.state='closed';self.view.saved_export.closed.emit()
        self.client.stop.assert_called_once();self.assertEqual(closed,[])
        self.client.state='closed';self.view._closed('Requested close');self.assertEqual(closed,[True])
    def test_owner_closes_first_view_waits_for_saved_player_actual_join(self):
        closed=[];definition=self.view.definition
        self.view._close_callback=lambda:closed.append(True);self.view._closing_project=True
        self.view.saved_play.state='stopping';self.view.saved_play.stop=Mock();self.client.state='closed'
        self.view._closed('Creator interrupted')
        self.assertEqual(closed,[]);self.assertIs(self.view.definition,definition)
        self.view.saved_play.state='closed';self.view.saved_play.closed.emit()
        self.assertEqual(closed,[True]);self.assertIsNone(self.view.definition)
    def test_busy_export_stop_cannot_launch_from_late_completed_callback(self):
        self.view._saved_exporting=True;self.view.busy=True;self.view.saved_export.stop=Mock()
        self.view.saved_play.start=Mock();self.view.stop_saved_play()
        journal=hash_saved_journal(self.root)
        self.view._saved_export_completed(SavedChapterExportResult(self.snapshot,journal.sha256,journal.bytes))
        self.view.saved_play.start.assert_not_called();self.assertFalse(self.view.busy)

if __name__=='__main__':unittest.main()
