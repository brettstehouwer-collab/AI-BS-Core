import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import json
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication

from native_studio.game_engine.project_model import ProjectDefinition, ProjectError, DEFAULT_FIELDS
from native_studio.game_engine.creator_view import CreatorView
from native_studio.game_engine.creator_payload import Transaction, Create, Erase
from native_studio.game_engine.creator_payload import SetField,EditRequest,encode_edit
from native_studio.game_engine.creator_wire import Opcode
from native_studio.game_build_view import GameBuildNativeView
from native_studio.engine import EngineBus
from native_studio.game_build_monitor import read_build_progress

EXE=Path(__file__).resolve().parents[1]/'install/release/bin/aibs_creator_host.exe'


class ProjectDefinitionTests(unittest.TestCase):
    def test_exclusive_metadata_roundtrip_and_no_world_write(self):
        with tempfile.TemporaryDirectory() as directory:
            definition=ProjectDefinition.create(Path(directory),'BS ✏','main')
            self.assertEqual(ProjectDefinition.load(Path(directory)),definition)
            self.assertFalse((Path(directory)/'world.aibs').exists())
            before=definition.path.read_bytes()
            with self.assertRaises(ProjectError):ProjectDefinition.create(Path(directory),'other','main')
            self.assertEqual(definition.path.read_bytes(),before)

    def test_missing_corrupt_oversized_and_duplicate_json_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ProjectError):ProjectDefinition.load(root)
            file=root/'.aibs-project.json'
            for data in (b'{',b'x'*65537,b'{"version":1,"version":1}'):
                file.write_bytes(data)
                with self.assertRaises(ProjectError):ProjectDefinition.load(root)
            file.unlink()
            (root/'world.aibs').write_bytes(b'Unrelated original')
            with self.assertRaises(ProjectError):ProjectDefinition.create(root,'p','main')
            self.assertEqual((root/'world.aibs').read_bytes(),b'Unrelated original')


class CreatorWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='aibs-editor-')
        self.view=CreatorView(EXE)

    def spin(self,predicate,seconds=6):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.002)
        self.assertTrue(predicate(),self.view.status.text())

    def idle(self):self.spin(lambda:self.view.loaded and not self.view.busy)

    def tearDown(self):
        self.view.close_project(discard=True)
        self.spin(lambda:self.view.client.state=='closed')
        self.view.close();self.view.deleteLater();self.app.processEvents();self.directory.cleanup()

    def test_real_editor_grouped_preview_history_save_and_reopen(self):
        root=Path(self.directory.name)
        self.view.new_project(root,'BS workshop');self.idle()
        self.assertEqual(self.view.outliner.topLevelItemCount(),0)
        self.view.add_node('relay','Relay');self.idle()
        entity=self.view.rows[0];self.assertEqual(self.view.selected_id,entity.uuid)
        self.assertFalse((root/'world.aibs').exists())
        revision=self.view.client.head.head_revision
        self.view.field_editors['x'].setText('7.5');self.view.field_editors['half_x'].setText('2.0')
        self.view.preview_button.click();self.spin(lambda:not self.view.busy and self.view.apply_button.isEnabled())
        self.assertEqual(self.view.client.head.head_revision,revision)
        self.assertEqual(dict(self.view.rows[0].fields)['x'],0.)
        self.assertIn('compatible',self.view.preview_details.toPlainText().lower())
        self.view.apply_button.click();self.idle()
        self.assertEqual(self.view.client.head.head_revision,revision+1)
        self.assertEqual(dict(self.view.rows[0].fields)['x'],7.5)
        self.assertEqual(dict(self.view.rows[0].fields)['half_x'],2.)
        self.view.undo_button.click();self.idle()
        self.assertEqual(dict(self.view.rows[0].fields)['x'],0.)
        self.view.redo_button.click();self.idle()
        self.assertEqual(dict(self.view.rows[0].fields)['x'],7.5)
        self.view.save_button.click();self.idle()
        self.assertTrue((root/'world.aibs').is_file());self.assertFalse(self.view.client.dirty)
        world_id=self.view.client.head.scope.world_id;node_id=self.view.rows[0].uuid
        self.view.close_project();self.spin(lambda:self.view.client.state=='closed')
        self.view.open_project(root);self.idle()
        self.assertEqual(self.view.client.head.scope.world_id,world_id)
        self.assertEqual(self.view.rows[0].uuid,node_id)
        self.assertEqual(dict(self.view.rows[0].fields)['x'],7.5)

    def test_invalid_numeric_preview_keeps_document_and_uuid_selection(self):
        self.view.new_project(Path(self.directory.name),'p');self.idle()
        self.view.add_node('cube','Cube');self.idle()
        old=self.view.rows;revision=self.view.client.head.head_revision
        for text in ('nan','inf','999999','bad'):
            self.view.field_editors['x'].setText(text);self.view.preview_button.click();self.app.processEvents()
            self.assertFalse(self.view.apply_button.isEnabled())
            self.assertEqual(self.view.rows,old)
            self.assertEqual(self.view.client.head.head_revision,revision)

    def test_alias_replacement_never_rebinds_old_uuid_selection(self):
        self.view.new_project(Path(self.directory.name),'p');self.idle()
        self.view.add_node('same','Original');self.idle()
        original=self.view.rows[0];replacement=str(uuid.uuid4())
        tx=Transaction('replace',self.view.client.head.head_revision,'SDK replacement',(
            Erase('same',original.uuid),Create('same','Replacement',replacement,original.fields)))
        self.view.submit_transaction(tx);self.idle()
        self.assertEqual(self.view.rows[0].uuid,replacement)
        self.assertIsNone(self.view.selected_id)
        self.assertFalse(self.view.select_entity(original.uuid))

    def test_close_refuses_silent_discard_and_missing_world_is_not_reinitialized(self):
        root=Path(self.directory.name);self.view.new_project(root,'p');self.idle()
        with self.assertRaises(ProjectError):self.view.close_project()
        self.assertEqual(self.view.client.state,'ready')
        self.view.save_button.click();self.idle()
        self.view.close_project();self.spin(lambda:self.view.client.state=='closed')
        (root/'world.aibs').unlink()
        with self.assertRaises(ProjectError):self.view.open_project(root)
        self.assertFalse((root/'world.aibs').exists())

    def test_existing_build_monitor_hosts_lazy_creator_tab(self):
        bus=EngineBus(max_threads=1);host=GameBuildNativeView(bus)
        try:
            self.assertIsNone(host.creator_view)
            self.assertEqual(host.workspace_tabs.tabText(0),'Build progress')
            host.workspace_tabs.setCurrentIndex(1);self.app.processEvents()
            self.assertIsInstance(host.creator_view,CreatorView)
            self.assertIsNotNone(host.details)
            self.assertTrue(host.chapter_button.text().startswith('Play First Boot'))
        finally:host.close();bus.shutdown()

    def test_monitor_displays_recorded_creator_scope_without_claiming_native_viewport(self):
        root=Path(self.directory.name);bus=EngineBus(max_threads=1);host=GameBuildNativeView(bus,root=root)
        try:
            host._render(read_build_progress(root))
            self.assertIn('CREATOR WORKSPACE VERIFICATION',host.details.toPlainText())
            report=root/'engine/out/creator_workspace_verification.json';report.parent.mkdir(parents=True)
            report.write_text(json.dumps({'schema_version':1,'status':'passed',
                'completed_at':'2026-11-01T19:00:00+00:00','checks':['Native owner numeric preview/save/reopen'],
                'origin':'Source Qt numeric workspace; native 3D viewport unfinished'}),encoding='utf-8')
            host._render(read_build_progress(root));text=host.details.toPlainText()
            self.assertIn('Native owner numeric preview/save/reopen',text)
            self.assertIn('Source Qt numeric workspace; native 3D viewport unfinished',text)
            report.write_text('{',encoding='utf-8');host._render(read_build_progress(root))
            self.assertIn('Creator workspace: unreadable',host.details.toPlainText())
            viewport=report.with_name('creator_viewport_verification.json')
            viewport.write_text(json.dumps({'schema_version':1,'status':'passed',
                'completed_at':'2026-11-01T19:00:00+00:00','checks':['Actual DX12 UUID picking'],
                'origin':'Native authoring preview; chapter Play remains unfinished'}),encoding='utf-8')
            host._render(read_build_progress(root))
            self.assertIn('NATIVE CREATOR VIEWPORT VERIFICATION',host.details.toPlainText())
            self.assertIn('Actual DX12 UUID picking',host.details.toPlainText())
        finally:host.close();bus.shutdown()

    def test_cancel_and_save_close_are_explicit_and_join_process(self):
        from PyQt6.QtWidgets import QMessageBox
        root=Path(self.directory.name);self.view.new_project(root,'p');self.idle()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(self.view.prepare_close())
        self.assertEqual(self.view.client.state,'ready')
        closed=[]
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Save):
            self.view.prepare_close(lambda:closed.append(True))
            self.spin(lambda:bool(closed))
        self.assertEqual(self.view.client.state,'closed')
        self.assertTrue((root/'world.aibs').is_file())

    def test_changing_preview_inputs_invalidates_token_and_close_can_drain_release(self):
        from PyQt6.QtWidgets import QMessageBox
        self.view.new_project(Path(self.directory.name),'p');self.idle();self.view.add_node('n','N');self.idle()
        self.view.field_editors['x'].setText('3');self.view.preview_button.click()
        self.spin(lambda:self.view.apply_button.isEnabled())
        self.view.field_editors['x'].setText('4')
        self.assertFalse(self.view.apply_button.isEnabled())
        self.assertEqual(dict(self.view.rows[0].fields)['x'],0.)
        closed=[]
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Discard):
            self.view.prepare_close(lambda:closed.append(True));self.spin(lambda:bool(closed))
        self.assertEqual(self.view.client.state,'closed')

    def test_failed_save_cancels_close_without_repeating_dialog(self):
        from PyQt6.QtWidgets import QMessageBox
        root=Path(self.directory.name);self.view.new_project(root,'p');self.idle()
        (root/'world.aibs').mkdir()  # Real storage error in this synthetic workspace.
        closed=[]
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Save) as question:
            self.view.prepare_close(lambda:closed.append(True));self.spin(lambda:not self.view.busy)
            self.assertEqual(question.call_count,1)
        self.assertEqual(closed,[])
        self.assertIsNotNone(self.view.definition)
        self.assertEqual(self.view.client.state,'ready')

    def test_sdk_edit_refreshes_inspector_without_changing_selected_uuid(self):
        self.view.new_project(Path(self.directory.name),'p');self.idle();self.view.add_node('n','N');self.idle()
        selected=self.view.selected_id;head=self.view.client.head
        tx=Transaction('sdk-update',head.head_revision,'SDK edit',(SetField('n','x',5.,selected),))
        self.view.client.request(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(head.scope,tx)),revision=tx.revision)
        self.spin(lambda:not self.view.busy and dict(self.view.rows[0].fields)['x']==5.)
        self.assertEqual(self.view.selected_id,selected)
        self.assertEqual(float(self.view.field_editors['x'].text()),5.)

    def test_parent_workspace_close_waits_for_saved_child(self):
        from PyQt6.QtWidgets import QMessageBox
        bus=EngineBus(max_threads=1);host=GameBuildNativeView(bus)
        try:
            host.resize(1200,800);host.show();host.workspace_tabs.setCurrentIndex(1)
            editor=host.creator_view
            editor.new_project(Path(self.directory.name),'Parent close')
            self.spin(lambda:editor.loaded and not editor.busy)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Save):
                host.close();self.spin(lambda:editor.client.state=='closed' and not host.isVisible())
            self.assertEqual(editor.client.process_id,0)
            self.assertTrue((Path(self.directory.name)/'world.aibs').is_file())
            self.assertFalse(host.timer.isActive())
        finally:
            if host.creator_view:
                host.creator_view.close_project(discard=True)
                self.spin(lambda:host.creator_view.client.state=='closed')
            host.close();bus.shutdown()

    def test_paged_refresh_never_publishes_a_mixed_revision(self):
        self.view.new_project(Path(self.directory.name),'p');self.idle()
        fields=tuple((key,1. if key.startswith('half_') else 0.) for key,_,_ in DEFAULT_FIELDS)
        edits=tuple(Create('node-'+str(i),'Node '+str(i),str(uuid.uuid4()),fields) for i in range(70))
        self.view.submit_transaction(Transaction('many',0,'Paged nodes',edits));self.idle()
        self.assertEqual(len(self.view.rows),70)
        prior=self.view.rows;original=self.view._request_page;injected=[]
        def request_page():
            if self.view._cursor and not injected:
                head=self.view.client.head
                tx=Transaction('during-page',head.head_revision,'SDK insertion',(Create('extra','Extra',str(uuid.uuid4()),fields),))
                injected.append(True)
                self.view.client.request(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(head.scope,tx)),revision=tx.revision)
            original()
        with patch.object(self.view,'_request_page',side_effect=request_page):
            self.view.refresh_world();self.spin(lambda:not self.view.busy)
        self.assertIs(self.view.rows,prior)
        self.assertFalse(self.view.add_button.isEnabled())
        self.view.refresh_world();self.idle()
        self.assertEqual(len(self.view.rows),71)

    def test_native_viewport_pick_selects_inspector_without_editing_world(self):
        self.view.new_project(Path(self.directory.name),'p');self.idle()
        self.view.add_node('cube','Cube');self.idle();identity=self.view.rows[0].uuid
        self.view.outliner.setCurrentItem(None)
        before=self.view.rows;revision=self.view.client.head.head_revision
        self.view.open_viewport(probe_directory=Path(self.directory.name))
        self.spin(lambda:self.view.viewport.state=='closed')
        self.assertEqual(self.view.selected_id,identity)
        self.assertIs(self.view.rows,before)
        self.assertEqual(self.view.client.head.head_revision,revision)

    def test_native_preview_updates_and_project_close_joins_both_children(self):
        self.view.new_project(Path(self.directory.name),'p');self.idle();self.view.add_node('cube','Cube');self.idle()
        self.view.open_viewport();self.spin(lambda:self.view.viewport.state=='ready')
        self.view.field_editors['x'].setText('4');self.view.preview_selected()
        self.spin(lambda:self.view.apply_button.isEnabled());self.view.apply_preview();self.idle()
        self.spin(lambda:self.view.viewport.displayed_tag==self.view.viewport._tag)
        self.assertEqual(self.view.viewport.displayed_tag[2],self.view.client.head.head_revision)
        self.view.close_project(discard=True)
        self.spin(lambda:self.view.viewport.state=='closed' and self.view.client.state=='closed')
        self.assertEqual(self.view.viewport.process_id,0)
        self.assertEqual(self.view.client.process_id,0)


if __name__=='__main__':unittest.main()
