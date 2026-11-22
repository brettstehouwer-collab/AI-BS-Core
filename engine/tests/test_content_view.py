import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile,time,unittest,json
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication,QMessageBox,QCheckBox
from native_studio.game_engine.content_view import ContentView,ChapterProjectDefinition
from native_studio.game_engine.project_model import ProjectError
from native_studio.game_build_view import GameBuildNativeView
from native_studio.engine import EngineBus

ROOT=Path(__file__).resolve().parents[2]
EXE=ROOT/'engine/out/windows-msvc/Debug/aibs_content_host.exe'

class ChapterProjectTests(unittest.TestCase):
    def test_exclusive_metadata_and_missing_world_not_reinitialized(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);definition=ChapterProjectDefinition.create(root,'BS chapter')
            self.assertEqual(ChapterProjectDefinition.load(root),definition)
            before=definition.path.read_bytes()
            with self.assertRaises(ProjectError):ChapterProjectDefinition.create(root,'other')
            self.assertEqual(definition.path.read_bytes(),before)
            self.assertFalse((root/'chapter.aiba').exists())

class ContentViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='aibs-chapter-ui-');self.view=ContentView(EXE)
        self.status_messages=[];set_status=self.view.status.setText
        def record_status(text):
            self.status_messages.append(str(text));self.status_messages=self.status_messages[-16:];set_status(text)
        self.view.status.setText=record_status
    def spin(self,predicate,seconds=30):
        until=time.monotonic()+seconds
        while not predicate() and time.monotonic()<until:self.app.processEvents();time.sleep(.003)
        head=self.view._tag(self.view.client.head) if self.view.client.head else None
        self.assertTrue(predicate(),self.view.status.text()+f'\nrecent_status={self.status_messages}; viewport={self.view.viewport.state}; displayed={self.view.viewport.displayed_tag}; published={self.view.viewport._tag}; head={head}; stderr={self.view.viewport.stderr_tail!r}')
    def idle(self):self.spin(lambda:self.view.loaded and not self.view.busy and not self.view.client.pending_count)
    def tearDown(self):
        self.spin(lambda:not self.view.busy and not self.view.client.pending_count)
        self.view.close_project(discard=True);self.spin(lambda:self.view.client.state=='closed')
        self.view.close();self.view.deleteLater();self.app.processEvents();self.directory.cleanup()
    def test_real_typed_edit_preview_history_save_and_reopen(self):
        root=Path(self.directory.name);self.view.new_project(root,'First Boot authoring');self.idle()
        self.assertGreater(len(self.view.rows),32)
        main=next(r for r in self.view.rows if r.type_id=='firstboot.Door' and dict(r.fields)['role']=='main')
        self.assertNotIn('unlocked',dict(main.fields));self.assertNotIn('open',dict(main.fields))
        self.view.select_entity(main.uuid);self.view.field_editors['x'].setText('-32.5')
        revision=self.view.client.head.head_revision
        self.view.preview_button.click();self.spin(lambda:self.view.apply_button.isEnabled())
        self.assertEqual(self.view.client.head.head_revision,revision)
        self.assertEqual(dict(next(r for r in self.view.rows if r.uuid==main.uuid).fields)['x'],-33.)
        self.assertIn('new Play branch',self.view.preview_details.toPlainText())
        self.view.apply_button.click();self.idle();self.assertEqual(self.view.selected_id,main.uuid)
        self.assertEqual(float(self.view.field_editors['x'].text()),-32.5)
        self.view.undo_button.click();self.idle();self.assertEqual(float(self.view.field_editors['x'].text()),-33.)
        self.view.redo_button.click();self.idle();self.assertEqual(float(self.view.field_editors['x'].text()),-32.5)
        self.view.save_button.click();self.idle();self.assertTrue((root/'chapter.aiba').is_file())
        fingerprint=self.view.description.fingerprint;world=self.view.client.head.scope.world_id
        self.view.close_project();self.spin(lambda:self.view.client.state=='closed')
        self.view.open_project(root);self.idle()
        self.assertEqual(self.view.description.fingerprint,fingerprint);self.assertEqual(self.view.client.head.scope.world_id,world)
        self.assertTrue(self.view.select_entity(main.uuid));self.assertEqual(float(self.view.field_editors['x'].text()),-32.5)
    def test_fixture_boolean_edit_delete_and_close_decisions(self):
        self.view.new_project(Path(self.directory.name),'Typed fixtures');self.idle()
        main=next(r for r in self.view.rows if r.type_id=='firstboot.Door');self.view.select_entity(main.uuid)
        self.assertFalse(self.view.delete_button.isEnabled())
        self.view.add_fixture('Seat study');self.idle();identity=self.view.selected_id
        self.assertIsInstance(self.view.field_editors['selectable'],QCheckBox)
        self.view.field_editors['selectable'].setChecked(False);self.view.preview_selected()
        self.spin(lambda:self.view.apply_button.isEnabled());self.view.apply_preview();self.idle()
        self.assertFalse(dict(next(r for r in self.view.rows if r.uuid==identity).fields)['selectable'])
        self.view.delete_selected();self.idle();self.assertFalse(any(r.uuid==identity for r in self.view.rows))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel):self.assertFalse(self.view.prepare_close())
        self.assertEqual(self.view.client.state,'ready')
        closed=[]
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Save):
            self.view.prepare_close(lambda:closed.append(True));self.spin(lambda:bool(closed))
        self.assertEqual(self.view.client.process_id,0)
    def test_proposal_uses_visible_native_preview_and_stale_jobs_are_rejected(self):
        self.view.new_project(Path(self.directory.name),'Proposal review');self.idle()
        main=next(r for r in self.view.rows if r.type_id=='firstboot.Door' and dict(r.fields)['role']=='main')
        self.view.select_entity(main.uuid)
        job,context=self.view.proposal_jobs.begin([main.uuid])
        self.assertEqual(context['objects'][0]['uuid'],main.uuid)
        payload=json.dumps({'version':1,'label':'Shift main door','edits':[{'entity_id':main.uuid,'field':'x','value':-32.5}]})
        revision=self.view.client.head.head_revision
        self.view.submit_proposal(job,payload)
        self.spin(lambda:not self.view.busy and not self.view.client.pending_count)
        self.assertEqual(self.view.client.head.head_revision,revision)
        self.assertTrue(self.view.apply_button.isEnabled())
        self.assertIn('new Play branch',self.view.preview_details.toPlainText())
        stale,_=self.view.proposal_jobs.begin([main.uuid])
        self.view.apply_preview();self.idle()
        self.assertEqual(float(self.view.field_editors['x'].text()),-32.5)
        with self.assertRaisesRegex(ValueError,'stale'):self.view.submit_proposal(stale,payload)
        pending,_=self.view.proposal_jobs.begin([main.uuid])
        self.view.close_project(discard=True);self.spin(lambda:self.view.client.state=='closed')
        self.assertEqual(self.view.proposal_jobs.pending_count,0)
    def test_native_preview_and_play_pin_unsaved_content_and_join_before_cleanup(self):
        root=Path(self.directory.name);self.view.new_project(root,'Isolated Play');self.idle()
        self.view.add_fixture('Unsaved Play fixture');self.idle();fixture=self.view.selected_id
        document=root/'chapter.aiba';before=document.read_bytes() if document.exists() else None
        fingerprint=self.view.description.fingerprint;revision=self.view.client.head.head_revision
        self.view.open_viewport();self.spin(lambda:self.view.viewport.state=='ready')
        self.assertEqual(self.view.viewport.displayed_tag[2],revision)
        self.assertEqual(self.view._content_snapshot.fingerprint,fingerprint)
        self.view.start_play();self.spin(lambda:self.view.play.state=='ready')
        scratch=self.view.play.workspace_path
        self.assertNotEqual(scratch.parent,root);self.assertTrue(scratch.is_dir())
        self.assertEqual(self.view.play.snapshot.fingerprint,fingerprint)
        self.assertEqual(self.view.play.snapshot.payload,(scratch/'chapter.aibd').read_bytes())
        self.view.select_entity(fixture);self.view.field_editors['x'].setText('-34.5');self.view.preview_selected()
        self.spin(lambda:self.view.apply_button.isEnabled());self.view.apply_preview();self.idle()
        self.spin(lambda:self.view.viewport.displayed_tag and self.view.viewport.displayed_tag[2]==self.view.client.head.head_revision)
        self.assertNotEqual(self.view.description.fingerprint,fingerprint)
        self.assertEqual(self.view.play.snapshot.fingerprint,fingerprint)
        self.assertIn('authoring has changed',self.view.play_status.text())
        self.view.undo_button.click();self.idle()
        self.assertEqual(float(self.view.field_editors['x'].text()),-35.)
        self.assertEqual(self.view.play.snapshot.fingerprint,fingerprint)
        self.view.redo_button.click();self.idle()
        self.assertEqual(float(self.view.field_editors['x'].text()),-34.5)
        self.assertEqual(self.view.play.snapshot.fingerprint,fingerprint)
        self.spin(lambda:self.view.viewport.displayed_tag and self.view.viewport.displayed_tag[2]==self.view.client.head.head_revision)
        self.assertEqual(document.read_bytes() if document.exists() else None,before)
        self.view.stop_play();self.spin(lambda:self.view.play.state=='closed')
        self.assertTrue(self.view.play.last_result['graceful']);self.assertTrue(self.view.play.last_result['saved'])
        self.assertFalse(scratch.exists());self.assertEqual(self.view.play.process_id,0)
        self.assertEqual(self.view.client.head.head_revision,revision+3)
        saved_fingerprint=self.view.description.fingerprint;world=self.view.client.head.scope.world_id
        self.view.start_play();self.spin(lambda:self.view.play.state=='ready')
        scratch=self.view.play.workspace_path
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(self.view.prepare_close())
        self.assertEqual(self.view.play.state,'ready');self.assertEqual(self.view.client.state,'ready')
        closed=[]
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Save):
            self.view.prepare_close(lambda:closed.append(True))
            self.spin(lambda:bool(closed) and self.view.client.state=='closed' and self.view.viewport.state=='closed' and self.view.play.state=='closed')
        self.assertFalse(scratch.exists());self.assertEqual(self.view.play.process_id,0)
        self.assertTrue(self.view.play.last_result['saved']);self.assertTrue(document.exists())
        self.view.open_project(root);self.idle()
        self.assertEqual(self.view.description.fingerprint,saved_fingerprint)
        self.assertEqual(self.view.client.head.scope.world_id,world)
        self.assertEqual(self.view.client.head.head_revision,revision+3)
        self.assertTrue(self.view.select_entity(fixture));self.assertEqual(float(self.view.field_editors['x'].text()),-34.5)
    def test_standalone_close_waits_for_play_after_owner_dies_while_draining(self):
        self.view.new_project(Path(self.directory.name),'Unexpected owner close');self.idle()
        self.view.add_fixture('Dirty fixture');self.idle();self.view.show()
        self.view.start_play();self.spin(lambda:self.view.play.state=='ready')
        scratch=self.view.play.workspace_path
        try:
            # Delay the real native child's stop marker to deterministically put
            # owner failure between close request and child exit.
            with patch.object(self.view.play,'stop',side_effect=lambda:self.view.play._state('stopping')):
                with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Discard):
                    self.assertFalse(self.view.close())
                self.view.client.abort('Injected owner exit while Play drain is pending')
                self.spin(lambda:self.view.client.state=='closed')
                self.assertGreater(self.view.play.process_id,0)
                self.assertTrue(self.view.isVisible(),'Standalone widget accepted close while its native Play child was still running')
                self.assertTrue(scratch.exists())
        finally:
            if self.view.play.state!='closed':
                self.view.play._state('ready');self.view.play.stop()
                self.spin(lambda:self.view.play.state=='closed')
        self.spin(lambda:not self.view.isVisible())
        self.assertEqual(self.view.play.process_id,0);self.assertFalse(scratch.exists())
    def test_native_typed_preview_exports_unsaved_document_and_joins(self):
        root=Path(self.directory.name);self.view.new_project(root,'Native typed preview');self.idle()
        self.view.add_fixture('Preview fixture');self.idle()
        revision=self.view.client.head.head_revision;fingerprint=self.view.description.fingerprint
        self.view.open_viewport(probe_directory=root)
        self.spin(lambda:not self.view.busy and self.view.viewport.state=='closed' and (root/'viewport.json').exists())
        proof=json.loads((root/'viewport.json').read_text())
        self.assertGreater(proof['nonbackground_pixels'],100);self.assertEqual(proof['debug_errors'],0)
        self.assertTrue((root/'viewport.bmp').is_file())
        self.assertEqual(self.view._content_snapshot.fingerprint,fingerprint)
        self.assertEqual(self.view.client.head.head_revision,revision)
        self.assertEqual(self.view.viewport.process_id,0)
    def test_pending_export_close_cancels_launch_and_joins_owner(self):
        self.view.new_project(Path(self.directory.name),'Cancel export');self.idle()
        self.view.add_fixture('Dirty fixture');self.idle();closed=[]
        with patch.object(self.view.viewport,'start_content') as launch:
            self.view.open_viewport()
            self.assertTrue(self.view.busy)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Discard):
                self.view.prepare_close(lambda:closed.append(True));self.spin(lambda:bool(closed))
            launch.assert_not_called()
        self.assertEqual(self.view.client.state,'closed');self.assertEqual(self.view.viewport.state,'closed')
    def test_parent_close_joins_numeric_and_typed_children(self):
        root=Path(self.directory.name);numeric=root/'numeric';typed=root/'typed';numeric.mkdir();typed.mkdir()
        bus=EngineBus(max_threads=1);parent=GameBuildNativeView(bus)
        try:
            parent.show();parent.workspace_tabs.setCurrentIndex(1);parent.creator_view.new_project(numeric,'Numeric')
            self.spin(lambda:parent.creator_view.loaded and not parent.creator_view.busy)
            parent.workspace_tabs.setCurrentIndex(2);parent.content_view.new_project(typed,'Chapter')
            self.spin(lambda:parent.content_view.loaded and not parent.content_view.busy)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Discard):
                parent.close();self.spin(lambda:not parent.isVisible() and parent.creator_view.client.state=='closed' and parent.content_view.client.state=='closed')
            self.assertFalse(parent.timer.isActive())
        finally:
            for view in (parent.creator_view,parent.content_view):
                if view and view.client.state!='closed':view.close_project(discard=True);self.spin(lambda:view.client.state=='closed')
            parent.close();bus.shutdown()

if __name__=='__main__':unittest.main()
