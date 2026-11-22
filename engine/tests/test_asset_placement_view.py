"""Placement codec, immutable export references and UI admission contracts."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import tempfile
import time
from contextlib import contextmanager
from unittest.mock import patch,PropertyMock
import uuid

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtCore import QObject, pyqtSignal
from native_studio.game_engine.content_commands import (CreateAssetPlacement, EraseAssetPlacement,
    SetField, TypedRow, encode_scoped_edit, decode_scoped_edit, ContentDescription, ContentExportChunk)
from native_studio.game_engine.creator_payload import Scope
from native_studio.game_engine.content_jobs import ContentProposalJobs
from native_studio.game_engine.content_preview import ContentExportAssembly
from native_studio.game_engine.content_preview import ContentViewportClient, ContentSnapshot
from native_studio.game_engine.content_play import ContentPlayClient
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.project_assets import AssetDependency, dependencies_from_rows, ProjectAssetClient, ASSET_REFERENCE_FIELDS

APP = QApplication.instance() or QApplication([])
WORLD, DEFINITION, ENTITY, ASSET = (str(uuid.uuid4()) for _ in range(4))
SHA, PACK = 'a' * 64, 'b' * 64


def placement_row():
    return TypedRow(ENTITY, 'authoring.AssetPlacement', 'Part', tuple(sorted({
        'name': 'Part', 'asset_id': ASSET, 'asset_sha256': SHA, 'pack_sha256': PACK,
        'x': 1., 'y': 2., 'z': 3., 'scale_x': 1., 'scale_y': 1., 'scale_z': 1.,
        'rotation_x': 0., 'rotation_y': 0., 'rotation_z': 0., 'rotation_w': 1., 'selectable': True}.items())))


class PlacementContracts(unittest.TestCase):
    def test_new_codec_roundtrips_without_changing_legacy_edit_bytes(self):
        scope = Scope('project', 'main', WORLD, str(uuid.uuid4()))
        old = encode_scoped_edit(scope, DEFINITION, 'legacy', 2, SHA, 'Old', (SetField(ENTITY, 'x', 2.),))
        self.assertEqual(encode_scoped_edit(scope, DEFINITION, 'legacy', 2, SHA, 'Old', decode_scoped_edit(old).edits), old)
        edits = (CreateAssetPlacement(ENTITY, 'Part', ASSET, SHA, PACK,center=(-35.,.5,10.)), EraseAssetPlacement(ENTITY))
        encoded = encode_scoped_edit(scope, DEFINITION, 'placement', 2, SHA, 'Place', edits)
        self.assertEqual(decode_scoped_edit(encoded).edits, edits)
        self.assertNotEqual(encoded, old)

    def test_dependency_references_are_detached_from_matching_export_rows(self):
        refs = dependencies_from_rows((placement_row(),))
        self.assertEqual(refs, (AssetDependency(ASSET, SHA, PACK),))
        payload = b'native opaque content bytes'
        fingerprint = hashlib.sha256(payload).hexdigest()
        description = ContentDescription(DEFINITION, 4, fingerprint, False, 1)
        scope = Scope('project', 'main', WORLD, str(uuid.uuid4()))
        assembly = ContentExportAssembly(scope, 1, 2, '', description, (ENTITY,),
            asset_refs=refs, asset_store=Path('C:/owned/project/assets/packs'))
        snapshot = assembly.accept(ContentExportChunk(DEFINITION, fingerprint, 4, len(payload), 0, payload), scope, 1, 2, '')
        self.assertEqual(snapshot.asset_refs, refs)
        self.assertEqual(snapshot.payload, payload, 'Python must not decode or rewrite AIBD')
        self.assertEqual(snapshot.asset_store, Path('C:/owned/project/assets/packs'))

    def test_reference_fields_are_readonly_in_inspector_and_excluded_from_ai(self):
        row = placement_row()
        view = ContentView(Path('C:/missing-host.exe'))
        try:
            view.rows = (row,)
            item = QTreeWidgetItem([row.name, row.type_id, row.uuid])
            from PyQt6.QtCore import Qt
            item.setData(0, Qt.ItemDataRole.UserRole, row.uuid)
            view.outliner.addTopLevelItem(item)
            view.outliner.setCurrentItem(item)
            view._selection_changed()
            for name in ('asset_id', 'asset_sha256', 'pack_sha256'):
                self.assertTrue(view.field_editors[name].isReadOnly(), name)
            client = SimpleNamespace(state='ready', pending_count=0, generation=1,
                head=SimpleNamespace(scope=Scope('project', 'main', WORLD, str(uuid.uuid4())), head_revision=2))
            jobs = ContentProposalJobs(client, lambda: (DEFINITION, SHA, (row,)))
            _, prompt = jobs.begin([ENTITY])
            self.assertTrue({'asset_id', 'asset_sha256', 'pack_sha256'}.isdisjoint(prompt['objects'][0]['fields']))
        finally:
            view.close()
            view.deleteLater()

    def test_placement_creation_previews_without_automatic_apply(self):
        view = ContentView(Path('C:/missing-host.exe'))
        try:
            view.adopted_asset = AssetDependency(ASSET, SHA, PACK)
            view._require_editable = lambda: None
            with patch.object(type(view.client),'capabilities',new_callable=PropertyMock,return_value=frozenset(('chapter-assets-v1',))),patch.object(view, '_submit_packet', return_value=9) as submit, patch.object(view, '_encode_edits', return_value=b'native-edit'):
                self.assertEqual(view.preview_asset_placement('Part'), 9)
            self.assertFalse(submit.call_args.kwargs['apply_after_preview'])
            self.assertTrue(submit.call_args.kwargs['placement_preview'])
        finally:
            view.close()
            view.deleteLater()

    def test_native_staging_arguments_pin_all_three_reference_values(self):
        client = ProjectAssetClient(Path('C:/assetc.exe'))
        reference = AssetDependency(ASSET, SHA, PACK)
        with patch.object(client, '_start') as start:
            client.stage_store(Path('C:/owned/store'), Path('C:/private/staged'), (reference,), merge=True)
        self.assertEqual(start.call_args.args[0], ['--stage-store', str(Path('C:/owned/store').resolve()),
            '--output', str(Path('C:/private/staged').resolve()), '--ref', ASSET, SHA, PACK, '--merge'])

    def test_parent_close_waits_for_owned_asset_cli_even_without_a_document(self):
        view=ContentView(Path('C:/missing-host.exe'))
        try:
            with patch.object(type(view.asset_client),'busy',new_callable=PropertyMock,return_value=True),patch.object(view.asset_client,'stop') as stop:
                self.assertFalse(view.prepare_close(lambda:None))
                stop.assert_called_once()
        finally:view.close();view.deleteLater()

    def test_parent_close_callback_runs_after_asset_cli_joins_without_a_document(self):
        view=ContentView(Path('C:/missing-host.exe'));closed=[]
        try:
            with patch.object(type(view.asset_client),'busy',new_callable=PropertyMock,return_value=True) as busy,patch.object(view.asset_client,'stop'):
                view.prepare_close(lambda:closed.append(True));busy.return_value=False;view._asset_closed()
                self.assertEqual(closed,[True])
        finally:view.close();view.deleteLater()


class FakeStager(QObject):
    receipt=pyqtSignal(str,object)
    failed=pyqtSignal(str)
    closed=pyqtSignal()
    def __init__(self,*args):
        super().__init__();self.busy=False;self.process_id=0;self.cancelled=False
    def stage_store(self,*args,**kwargs):self.args=args;self.kwargs=kwargs;self.busy=True;self.process_id=77
    def stop(self):self.cancelled=True
    def shutdown(self):self.finish()
    def finish(self):
        self.busy=False;self.process_id=0;self.receipt.emit('stage',{'status':'passed'});self.closed.emit()


class PlacementTransportContracts(unittest.TestCase):
    def snapshot(self,root):
        payload=b'opaque native chapter'
        return ContentSnapshot(Scope('project','main',WORLD,str(uuid.uuid4())),1,2,'',DEFINITION,3,
            hashlib.sha256(payload).hexdigest(),payload,frozenset((ENTITY,)),
            (AssetDependency(ASSET,SHA,PACK),),root/'project/assets/packs')

    def test_play_never_launches_until_private_store_is_staged(self):
        with tempfile.TemporaryDirectory() as directory,patch('native_studio.game_engine.content_play.ProjectAssetClient',FakeStager):
            root=Path(directory);exe=root/'player.exe';exe.write_bytes(b'fixture')
            client=ContentPlayClient(asset_cooker=root/'assetc.exe')
            try:
                with patch.object(client,'_launch') as launch:
                    client.start(exe,self.snapshot(root));scratch=client.workspace_path
                    self.assertEqual(client.state,'staging');launch.assert_not_called()
                    self.assertEqual(client._stager.args[1],scratch/'assets/packs')
                    client._stager.finish();launch.assert_called_once_with(exe.resolve())
            finally:client._finish_stage_only()

    def test_stop_during_staging_joins_cli_before_deleting_scratch_and_ignores_late_receipt(self):
        with tempfile.TemporaryDirectory() as directory,patch('native_studio.game_engine.content_play.ProjectAssetClient',FakeStager):
            root=Path(directory);exe=root/'player.exe';exe.write_bytes(b'fixture')
            client=ContentPlayClient(asset_cooker=root/'assetc.exe')
            with patch.object(client,'_launch') as launch:
                client.start(exe,self.snapshot(root));scratch=client.workspace_path;client.stop()
                self.assertTrue(client._stager.cancelled);self.assertTrue(scratch.exists())
                client._stager.finish();launch.assert_not_called()
                self.assertEqual(client.state,'closed');self.assertFalse(scratch.exists())

    def test_viewport_stages_before_launch_and_pins_private_asset_root(self):
        with tempfile.TemporaryDirectory() as directory,patch('native_studio.game_engine.content_preview.ProjectAssetClient',FakeStager):
            root=Path(directory);client=ContentViewportClient(asset_cooker=root/'assetc.exe')
            with patch('native_studio.game_engine.creator_viewport.ViewportClient.start') as launch:
                snapshot=self.snapshot(root);client.start_content(root/'viewport.exe',snapshot)
                scratch=client._path;launch.assert_not_called()
                client._stager.finish()
                self.assertEqual(launch.call_args.kwargs['asset_root'],scratch/'assets/packs')
                self.assertIsNotNone(launch.call_args.kwargs['prepared_directory'])
            client._finish_stage_only()


@contextmanager
def _native_directory():
    retained=os.environ.get('AIBS_PLACEMENT_UI_ARTIFACTS')
    if retained:
        root=Path(retained).resolve();root.mkdir(parents=True,exist_ok=False);yield root
    else:
        with tempfile.TemporaryDirectory(prefix='aibs-placement-ui-') as directory:yield Path(directory)


@unittest.skipUnless(os.environ.get('AIBS_RUN_PLACEMENT_UI_NATIVE')=='1','Real placement UI integration requires the coordinated native process slot')
class NativePlacementViewTests(unittest.TestCase):
    def test_new_owner_reopens_saved_placement_without_original_pack_and_missing_dependency_blocks_play(self):
        root_source=Path(__file__).resolve().parents[2]
        host=Path(os.environ.get('AIBS_PLACEMENT_HOST_EXE',str(root_source/'engine/out/windows-msvc/Release/aibs_content_host.exe')))
        cooker=Path(os.environ.get('AIBS_PLACEMENT_COOKER_EXE',str(host.with_name('aibs_assetc.exe'))))
        reference=Path(os.environ.get('AIBS_PLACEMENT_REFERENCE',str(root_source/'engine/assets/cooked/motherboard-reference')))
        self.assertTrue(host.is_file());self.assertTrue(cooker.is_file())
        with _native_directory() as root:
            data={'status':'failed','gpu_requested':os.environ.get('AIBS_RUN_PLACEMENT_UI_GPU')=='1','checks':[]}
            views=[];source_client=ProjectAssetClient(cooker);source_receipts=[];source_errors=[]
            source_client.receipt.connect(lambda mode,value:source_receipts.append((mode,value)))
            source_client.failed.connect(source_errors.append)
            def spin(predicate,view=None,seconds=35):
                deadline=time.monotonic()+seconds
                while not predicate() and time.monotonic()<deadline:APP.processEvents();time.sleep(.005)
                self.assertTrue(predicate(),view.status.text() if view is not None else str(source_errors))
            def idle(view):spin(lambda:view.loaded and not view.busy and not view.client.pending_count,view)
            def close_owner(view):
                view.close_project(discard=True)
                spin(lambda:view.client.state=='closed' and view.viewport.state=='closed' and view.play.state=='closed' and not view.asset_client.busy,view)
                view.close();APP.processEvents()
            try:
                source_store=root/'owned-source-store';source_store.mkdir()
                source_client.adopt_pack(reference,source_store);spin(lambda:not source_client.busy)
                self.assertFalse(source_errors,source_errors)
                source_ref=source_receipts[-1][1]
                owned_pack=source_store/source_ref['pack_sha256']
                self.assertTrue(owned_pack.is_dir())
                project=root/'chapter-project';project.mkdir()
                view=ContentView(host,asset_cooker=cooker,sample_asset_pack=owned_pack);views.append(view)
                view.new_project(project,'Persistent asset UI acceptance');idle(view)
                self.assertIn('chapter-assets-v1',view.client.capabilities)
                view.save_world();idle(view)
                document=project/'chapter.aiba';before=document.read_bytes()
                metadata=(project/'.aibs-chapter-project.json').read_bytes()
                if data['gpu_requested']:
                    from PyQt6.QtGui import QFont
                    from native_studio.theme import STYLESHEET
                    APP.setFont(QFont('Segoe UI',10));APP.setStyleSheet(STYLESHEET)
                    view.resize(1600,1200);view.show()
                    view.open_viewport();spin(lambda:view.viewport.state=='ready',view)
                self.assertIsNotNone(view.sample_asset_button)
                view.use_sample_asset();spin(lambda:not view.asset_client.busy,view)
                self.assertIsNotNone(view._inspected_asset,view.asset_status.text())
                self.assertIsNotNone(view.adopted_asset,view.asset_status.text())
                dependency=view.adopted_asset
                old_fingerprint=view.description.fingerprint;old_revision=view.client.head.head_revision
                view.preview_asset_placement('Persistent cooling part',center=(-35.,.5,10.),scale=(.02,.02,.02))
                spin(lambda:not view.busy and not view.client.pending_count,view)
                self.assertTrue(view.apply_button.isEnabled(),view.status.text())
                self.assertEqual(view.description.fingerprint,old_fingerprint)
                self.assertEqual(view.client.head.head_revision,old_revision)
                self.assertEqual(document.read_bytes(),before)
                self.assertFalse(any(row.type_id=='authoring.AssetPlacement' for row in view.rows))
                view.apply_preview();idle(view)
                row=next(row for row in view.rows if row.type_id=='authoring.AssetPlacement');identity=row.uuid
                self.assertEqual(view.selected_id,identity)
                self.assertEqual(document.read_bytes(),before)
                if data['gpu_requested']:
                    spin(lambda:view.viewport.displayed_tag and view.viewport.displayed_tag[2]==view.client.head.head_revision,view)
                    self.assertTrue((view.viewport._path/'assets/packs'/dependency.pack_sha256).is_dir())
                    APP.processEvents();self.assertTrue(view.grab().save(str(root/'placement-applied.png')))
                    data.setdefault('captures',{})['placement_applied']=str(root/'placement-applied.png')
                view._travel(False);idle(view);self.assertFalse(any(row.uuid==identity for row in view.rows))
                if data['gpu_requested']:spin(lambda:view.viewport.displayed_tag and view.viewport.displayed_tag[2]==view.client.head.head_revision,view)
                view._travel(True);idle(view);self.assertTrue(view.select_entity(identity))
                if data['gpu_requested']:spin(lambda:view.viewport.displayed_tag and view.viewport.displayed_tag[2]==view.client.head.head_revision,view)
                for name in ('asset_id','asset_sha256','pack_sha256'):self.assertTrue(view.field_editors[name].isReadOnly())
                _,prompt=view.proposal_jobs.begin([identity])
                self.assertTrue(ASSET_REFERENCE_FIELDS.isdisjoint(prompt['objects'][0]['fields']))
                view.proposal_jobs.cancel_all()
                view.save_world();idle(view)
                saved=document.read_bytes();fingerprint=view.description.fingerprint
                fields=dict(next(row for row in view.rows if row.uuid==identity).fields)
                history=(view.client.head.undo_depth,view.client.head.redo_depth)
                old_epoch=view.client.head.scope.host_epoch
                data.update(placement_uuid=identity,asset=dependency.__dict__,fields=fields,saved_fingerprint=fingerprint,
                    saved_sha256=hashlib.sha256(saved).hexdigest(),first_owner_epoch=old_epoch,history=list(history))
                close_owner(view)
                away=owned_pack.with_name(owned_pack.name+'.away')
                self.assertTrue(owned_pack.resolve().is_relative_to(root.resolve()) and away.resolve().is_relative_to(root.resolve()))
                owned_pack.rename(away)
                reopened=ContentView(host,asset_cooker=cooker);views.append(reopened)
                reopened.open_project(project);idle(reopened)
                self.assertNotEqual(reopened.client.head.scope.host_epoch,old_epoch)
                self.assertTrue(reopened.select_entity(identity))
                self.assertEqual(dict(next(row for row in reopened.rows if row.uuid==identity).fields),fields)
                self.assertEqual(reopened.description.fingerprint,fingerprint)
                self.assertEqual(document.read_bytes(),saved)
                self.assertEqual((reopened.client.head.undo_depth,reopened.client.head.redo_depth),history)
                self.assertEqual((project/'.aibs-chapter-project.json').read_bytes(),metadata)
                data['checks'].append('Explicit Preview is private; Apply/Undo/Redo/Save and a new native owner preserve placement UUID, immutable references, TRS, fingerprint, history and saved bytes after the original owned source pack moves away')
                if data['gpu_requested']:
                    reopened.resize(1600,1200);reopened.show();APP.processEvents()
                    self.assertTrue(reopened.grab().save(str(root/'placement-reopened.png')))
                    data.setdefault('captures',{})['placement_reopened']=str(root/'placement-reopened.png')
                    reopened.open_viewport();spin(lambda:reopened.viewport.state=='ready',reopened)
                    self.assertTrue((reopened.viewport._path/'assets/packs'/dependency.pack_sha256).is_dir())
                    reopened.start_play();spin(lambda:reopened.play.state=='ready',reopened)
                    scratch=reopened.play.workspace_path
                    self.assertTrue((scratch/'assets/packs'/dependency.pack_sha256).is_dir())
                    self.assertEqual(reopened.play.snapshot.fingerprint,fingerprint)
                    reopened.stop_play();spin(lambda:reopened.play.state=='closed',reopened)
                    self.assertFalse(scratch.exists())
                    reopened.viewport.stop();spin(lambda:reopened.viewport.state=='closed',reopened)
                    data['checks'].append('Native viewport and Play stage private pinned dependency closures and join before scratch cleanup')
                project_pack=project/'assets/packs'/dependency.pack_sha256
                unavailable=project_pack.with_name(project_pack.name+'.missing')
                self.assertTrue(project_pack.resolve().is_relative_to(project.resolve()) and unavailable.resolve().is_relative_to(project.resolve()))
                project_pack.rename(unavailable)
                messages=[];reopened.play.message.connect(messages.append)
                with patch.object(reopened.play,'_launch',wraps=reopened.play._launch) as launch:
                    reopened.start_play()
                    spin(lambda:not reopened.busy and not reopened.client.pending_count and reopened.play.state=='closed' and reopened.play.dependency_process_id==0,reopened)
                    launch.assert_not_called()
                self.assertTrue(any('asset' in text.lower() and ('failed' in text.lower() or 'missing' in text.lower()) for text in messages),messages)
                self.assertEqual(document.read_bytes(),saved)
                unavailable.rename(project_pack)
                data['checks'].append('A missing project dependency reports failure before native Play launches and preserves saved authoring bytes')
                data['second_owner_epoch']=reopened.client.head.scope.host_epoch
                close_owner(reopened);data['status']='passed'
            except Exception as error:
                data['error']=str(error);raise
            finally:
                source_client.shutdown()
                for view in views:
                    view.asset_client.shutdown();view.play._shutdown();view.viewport._shutdown()
                    view.client.abort('Placement acceptance cleanup')
                    deadline=time.monotonic()+3
                    while view.client.process_id and time.monotonic()<deadline:APP.processEvents();time.sleep(.005)
                    view.deleteLater()
                APP.processEvents()
                data['final_process_ids']=[{'owner':view.client.process_id,'asset_cli':view.asset_client.process_id,
                    'viewport':view.viewport.process_id,'viewport_stager':view.viewport.dependency_process_id,
                    'play':view.play.process_id,'play_stager':view.play.dependency_process_id} for view in views]
                (root/'verification.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

class PlacementViewportRefreshContracts(unittest.TestCase):
    snapshot=PlacementTransportContracts.snapshot

    def test_stale_viewport_stage_does_not_publish_over_the_current_scene(self):
        with tempfile.TemporaryDirectory() as directory,patch('native_studio.game_engine.content_preview.ProjectAssetClient',FakeStager):
            root=Path(directory);client=ContentViewportClient(asset_cooker=root/'assetc.exe')
            client._directory=tempfile.TemporaryDirectory();client._path=Path(client._directory.name)
            client.state='ready';client._process=object();client.context_valid=lambda snapshot:False
            scene=client._path/'scene.aibv';scene.write_bytes(b'previous published frame')
            snapshot=self.snapshot(root)
            client.publish(snapshot.scope,snapshot.revision,snapshot.checkpoint_id,snapshot)
            self.assertEqual(scene.read_bytes(),b'previous published frame')
            client._stager.finish()
            self.assertEqual(scene.read_bytes(),b'previous published frame')
            self.assertEqual(client.state,'ready')
            client._process=None;client._finish_stage_only()

    def test_newer_snapshot_queued_during_initial_staging_still_launches_viewport(self):
        with tempfile.TemporaryDirectory() as directory,patch('native_studio.game_engine.content_preview.ProjectAssetClient',FakeStager):
            root=Path(directory);client=ContentViewportClient(asset_cooker=root/'assetc.exe')
            with patch('native_studio.game_engine.creator_viewport.ViewportClient.start') as launch:
                snapshot=self.snapshot(root);client.start_content(root/'viewport.exe',snapshot)
                client.publish(snapshot.scope,snapshot.revision,snapshot.checkpoint_id,snapshot,selected_id=ENTITY)
                client._stager.finish();client._stager.finish()
                launch.assert_called_once()
            client._finish_stage_only()

    def test_empty_initial_preview_with_cooker_binds_private_store_for_later_placements(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as directory,patch('native_studio.game_engine.content_preview.ProjectAssetClient',FakeStager):
            root=Path(directory);client=ContentViewportClient(asset_cooker=root/'assetc.exe')
            with patch('native_studio.game_engine.creator_viewport.ViewportClient.start') as launch:
                client.start_content(root/'viewport.exe',replace(self.snapshot(root),asset_refs=()))
                self.assertIn('asset_root',launch.call_args.kwargs)
            client._finish_stage_only()


if __name__ == '__main__':
    unittest.main()
