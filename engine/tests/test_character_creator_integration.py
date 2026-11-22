"""Opt-in real Qt/native character assignment, export, restart and DX12 proof.

The fixture and pack must be synthetic derived test assets. Only copied inputs
under this run's new directory are renamed; the supplied pack is read-only.
GPU execution is opt-in so the parent can serialize this with renderer tests.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.content_preview import ContentViewportClient
from native_studio.game_engine.project_assets import ProjectAssetClient


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pack_files(root):
    root=Path(root)
    result={}
    for path in root.iterdir():
        if path.is_symlink() or getattr(path,'is_junction',lambda:False)() or not path.is_file():
            raise AssertionError('Only four plain immutable pack files are admitted')
        result[path.name]=_hash(path)
    if len(result)!=4:
        raise AssertionError('Expected the exact four-file cooked character pack')
    return result


@unittest.skipUnless(os.environ.get('AIBS_RUN_CHARACTER_UI_NATIVE')=='1',
    'Set AIBS_RUN_CHARACTER_UI_NATIVE=1 with explicit host/cooker/fixture/pack/viewport paths')
class CharacterCreatorNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_verified_model_preview_apply_restart_and_complete_dependency_transport(self):
        required={name:Path(os.environ['AIBS_CHARACTER_UI_'+name]).resolve(strict=True)
            for name in ('HOST','COOKER','FIXTURE','PACK','VIEWPORT')}
        for name,path in required.items():
            self.assertTrue(path.is_dir() if name=='PACK' else path.is_file(),name)
        source_hashes=_pack_files(required['PACK'])
        temporary=None
        if os.environ.get('AIBS_CHARACTER_UI_ARTIFACTS'):
            parent=Path(os.environ['AIBS_CHARACTER_UI_ARTIFACTS']).resolve(strict=True)
            self.assertTrue(parent.is_dir())
            root=parent/('character-creator-'+str(uuid.uuid4()))
            root.mkdir()
        else:
            temporary=tempfile.TemporaryDirectory(prefix='aibs-character-creator-')
            root=Path(temporary.name)
        views=[]
        stager=ProjectAssetClient(required['COOKER'])
        viewport=ContentViewportClient(asset_cooker=required['COOKER'])
        receipts=[];errors=[];viewport_messages=[]
        stager.receipt.connect(lambda mode,value:receipts.append((mode,value)))
        stager.failed.connect(errors.append)
        viewport.message.connect(viewport_messages.append)
        proof={'schema_version':1,'status':'failed','family_references_used':False,
            'checks':[],'input_paths':{name:str(path) for name,path in required.items()},
            'source_pack_hashes':source_hashes,'work_directory':str(root)}

        def spin(predicate,view=None,seconds=45):
            until=time.monotonic()+seconds
            while not predicate() and time.monotonic()<until:
                self.app.processEvents();time.sleep(.004)
            message=(view.status.text()+' | '+view.asset_status.text() if view is not None else
                str(errors)+' | '+str(viewport_messages)+' | '+str(viewport.stderr_tail))
            self.assertTrue(predicate(),message)

        def idle(view):
            spin(lambda:view.loaded and not view.busy and not view.client.pending_count,view)

        def binding(view,identity):
            rows=[row for row in view.rows if row.uuid==identity and row.type_id=='authoring.CompanionBinding']
            self.assertEqual(len(rows),1)
            return dict(rows[0].fields)

        def close(view):
            view.close_project(discard=True)
            spin(lambda:view.client.state=='closed' and view.viewport.state=='closed' and
                view.play.state=='closed' and not view.asset_client.busy,view)

        try:
            project=root/'project'
            result=subprocess.run([str(required['FIXTURE']),str(project)],cwd=required['FIXTURE'].parent,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
            expected=json.loads((project/'expected.json').read_text(encoding='utf-8'))
            self.assertFalse(expected['family_references_used'])
            self.assertIsNone(expected['model_reference'])
            identity=expected['companion_id']
            document=project/'chapter.aiba'
            original=document.read_bytes()
            metadata=(project/'.aibs-chapter-project.json').read_bytes()
            owned_pack=root/'owned-source-pack'
            shutil.copytree(required['PACK'],owned_pack)
            self.assertEqual(_pack_files(owned_pack),source_hashes)

            view=ContentView(required['HOST'],asset_cooker=required['COOKER']);views.append(view)
            view.open_project(project);idle(view)
            for cap in ('chapter-assets-v2','chapter-character-assets-v1','chapter-content-export-v2'):
                self.assertIn(cap,view.client.capabilities)
            self.assertFalse(binding(view,identity)['model_bound'])
            view.inspect_asset_pack(owned_pack)
            spin(lambda:not view.asset_client.busy,view)
            self.assertEqual(view._inspected_asset['kind'],'character',view.asset_status.text())
            view.adopt_asset_pack()
            spin(lambda:not view.asset_client.busy,view)
            reference=view.adopted_asset
            self.assertIsNotNone(reference,view.asset_status.text())
            self.assertTrue(view.asset_adam_button.isEnabled())
            self.assertFalse(view.asset_place_button.isEnabled())
            project_pack=project/'assets/packs'/reference.pack_sha256
            self.assertEqual(_pack_files(project_pack),source_hashes)
            fingerprint=view.description.fingerprint;revision=view.client.head.head_revision

            view.asset_adam_button.click()
            spin(lambda:not view.busy and not view.client.pending_count,view)
            self.assertTrue(view.apply_button.isEnabled(),view.status.text())
            self.assertEqual(view.description.fingerprint,fingerprint)
            self.assertEqual(view.client.head.head_revision,revision)
            self.assertFalse(binding(view,identity)['model_bound'])
            self.assertEqual(document.read_bytes(),original)
            view.apply_preview();idle(view)
            fields=binding(view,identity)
            self.assertTrue(fields['model_bound'])
            self.assertEqual(tuple(fields[key] for key in ('model_asset_id','model_asset_sha256','model_pack_sha256')),
                (reference.asset_id,reference.asset_sha256,reference.pack_sha256))
            self.assertEqual(view.selected_id,identity)
            self.assertEqual(document.read_bytes(),original,'Apply must not silently save')
            self.assertFalse(view.field_editors['model_bound'].isEnabled())
            for key in ('model_asset_id','model_asset_sha256','model_pack_sha256'):
                self.assertTrue(view.field_editors[key].isReadOnly())
            view._travel(False);idle(view)
            self.assertFalse(binding(view,identity)['model_bound'])
            view._travel(True);idle(view)
            self.assertEqual(binding(view,identity),fields)
            view.save_world();idle(view)
            saved=document.read_bytes();fingerprint=view.description.fingerprint
            history=(view.client.head.undo_depth,view.client.head.redo_depth)
            first_epoch=view.client.head.scope.host_epoch
            proof.update(companion_id=identity,model_reference=reference.__dict__,fields=fields,
                saved_sha256=_hash(document),fingerprint=fingerprint,history=list(history),
                first_owner_epoch=first_epoch)
            proof['checks'].append('Verified character inspection/adoption and grouped private native Preview preserve the old head and disk; explicit Apply, Undo, Redo and Save retain all four binding fields')
            close(view)

            away=owned_pack.with_name(owned_pack.name+'.away')
            self.assertTrue(owned_pack.resolve().is_relative_to(root.resolve()))
            self.assertTrue(away.resolve().is_relative_to(root.resolve()))
            owned_pack.rename(away)
            reopened=ContentView(required['HOST'],asset_cooker=required['COOKER']);views.append(reopened)
            reopened.open_project(project);idle(reopened)
            self.assertNotEqual(reopened.client.head.scope.host_epoch,first_epoch)
            self.assertEqual(binding(reopened,identity),fields)
            self.assertEqual(reopened.description.fingerprint,fingerprint)
            self.assertEqual(document.read_bytes(),saved)
            self.assertEqual((project/'.aibs-chapter-project.json').read_bytes(),metadata)
            self.assertEqual((reopened.client.head.undo_depth,reopened.client.head.redo_depth),history)
            self.assertEqual(_pack_files(required['PACK']),source_hashes)
            self.assertEqual(_pack_files(project_pack),source_hashes)
            reopened._travel(False);idle(reopened)
            self.assertFalse(binding(reopened,identity)['model_bound'])
            reopened._travel(True);idle(reopened)
            self.assertEqual(binding(reopened,identity),fields)
            reopened.save_world();idle(reopened)
            proof['checks'].append('A distinct native owner reopens after the copied source pack moves away, retaining exact model reference, authored fields, saved bytes, metadata and Undo/Redo history')

            with patch.object(reopened,'_use_snapshot') as use:
                reopened._begin_export('preview')
                spin(lambda:not reopened.busy and not reopened.client.pending_count,reopened)
                use.assert_called_once()
            snapshot=reopened._content_snapshot
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.export_version,2)
            self.assertEqual(snapshot.dependency_kinds,(1,))
            self.assertEqual(snapshot.asset_refs,(reference,))
            self.assertFalse(any(row.type_id=='authoring.AssetPlacement' for row in reopened.rows),
                'This proves model dependencies were exported without any placement row')
            self.assertEqual(hashlib.sha256(snapshot.payload).hexdigest(),snapshot.fingerprint)
            self.assertEqual(snapshot.fingerprint,reopened.description.fingerprint)
            self.assertEqual(snapshot.scope,reopened.client.head.scope)
            self.assertEqual(snapshot.revision,reopened.client.head.head_revision)
            private=root/'independent-private-packs'
            stager.stage_store(snapshot.asset_store,private,snapshot.asset_refs,profile=snapshot.asset_profile)
            spin(lambda:not stager.busy)
            self.assertFalse(errors,errors)
            self.assertEqual(receipts[-1][0],'stage')
            self.assertEqual(_pack_files(private/reference.pack_sha256),source_hashes)
            proof['checks'].append('Complete v2 native export carries the character dependency with no placement rows; independent private staging preserves all four immutable pack files byte for byte')
            proof.update(second_owner_epoch=reopened.client.head.scope.host_epoch,
                export_version=snapshot.export_version,dependency_kinds=list(snapshot.dependency_kinds),
                export_sha256=hashlib.sha256(snapshot.payload).hexdigest(),private_pack_hashes=_pack_files(private/reference.pack_sha256))

            captures=root/'native-viewport';captures.mkdir()
            viewport.context_valid=reopened._export_snapshot_matches
            viewport.start_content(required['VIEWPORT'],snapshot,captures,selected_id=identity)
            spin(lambda:viewport.state=='closed' and (captures/'viewport.json').is_file(),seconds=60)
            native=json.loads((captures/'viewport.json').read_text(encoding='utf-8'))
            self.assertGreater(native['nonbackground_pixels'],100)
            self.assertEqual(native['debug_errors'],0)
            self.assertEqual(native['debug_warnings'],0)
            self.assertGreater(native['character_frames'],0)
            self.assertEqual(native['character_kind'],'cooked_character')
            self.assertEqual(native['selected_uuid'],identity)
            self.assertEqual(native['world_id'],snapshot.scope.world_id)
            self.assertTrue((captures/'viewport.bmp').is_file())
            self.assertEqual(viewport.process_id,0)
            self.assertEqual(viewport.dependency_process_id,0)
            self.assertIsNone(viewport._directory)
            proof['native_viewport']=native
            proof['captures']={'native_viewport':str(captures/'viewport.bmp')}
            proof['checks'].append('Actual DX12 chapter viewport adopts the complete private character store, draws native geometry, reports zero debug errors and joins both renderer and staging processes before scratch cleanup')
            close(reopened)
            self.assertEqual(_pack_files(required['PACK']),source_hashes)
            proof['status']='passed'
        except Exception as error:
            proof['error']=str(error)
            raise
        finally:
            stager.shutdown();viewport._shutdown()
            for view in views:
                view.asset_client.shutdown();view.play._shutdown();view.viewport._shutdown()
                view.client.abort('Character creator acceptance cleanup')
            until=time.monotonic()+3
            while any(view.client.process_id for view in views) and time.monotonic()<until:
                self.app.processEvents();time.sleep(.004)
            proof['final_process_ids']=[{'owner':view.client.process_id,'asset_cli':view.asset_client.process_id,
                'viewport':view.viewport.process_id,'viewport_stager':view.viewport.dependency_process_id,
                'play':view.play.process_id,'play_stager':view.play.dependency_process_id} for view in views]
            proof['independent_process_ids']={'stager':stager.process_id,'viewport':viewport.process_id,
                'viewport_stager':viewport.dependency_process_id}
            for view in views:
                view.definition=None;view.close();view.deleteLater()
            self.app.processEvents()
            (root/'verification.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
            if temporary is not None:temporary.cleanup()


if __name__=='__main__':
    unittest.main()
