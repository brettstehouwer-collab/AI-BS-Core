"""Explicit real native chapter/surface acceptance; never launches a GPU."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView,ChapterProjectDefinition
from native_studio.game_engine.project_assets import ProjectAssetClient

APP=QApplication.instance() or QApplication([])
ROOT=Path(__file__).resolve().parents[2]

@contextmanager
def artifacts():
    retained=os.environ.get('AIBS_SURFACE_UI_ARTIFACTS')
    if retained:
        root=Path(retained).resolve();root.mkdir(parents=True,exist_ok=False);yield root
    else:
        with tempfile.TemporaryDirectory(prefix='aibs-surface-ui-') as directory:yield Path(directory)

@unittest.skipUnless(os.environ.get('AIBS_RUN_SURFACE_UI_NATIVE')=='1','Requires coordinated native owner/cooker slot')
class NativeSurfaceCreatorTests(unittest.TestCase):
    def test_modern_surface_preview_apply_history_save_new_owner_and_private_stage(self):
        host=Path(os.environ.get('AIBS_SURFACE_UI_HOST',str(ROOT/'engine/out/windows-msvc/Release/aibs_content_host.exe')))
        cooker=Path(os.environ.get('AIBS_SURFACE_UI_COOKER',str(host.with_name('aibs_assetc.exe'))))
        pack=Path(os.environ.get('AIBS_SURFACE_UI_PACK',str(ROOT/'engine/out/warm_beginning/surface-showcase-Release/pack')))
        self.assertTrue(host.is_file());self.assertTrue(cooker.is_file());self.assertTrue(pack.is_dir())
        with artifacts() as root:
            report={'status':'failed','gpu_requested':False,'checks':[]};views=[]
            source_client=ProjectAssetClient(cooker);receipts=[];errors=[]
            source_client.receipt.connect(lambda mode,value:receipts.append((mode,value)))
            source_client.failed.connect(errors.append)
            def check(condition,message):self.assertTrue(condition,message);report['checks'].append(message)
            def spin(predicate,view=None,seconds=35):
                end=time.monotonic()+seconds
                while not predicate() and time.monotonic()<end:APP.processEvents();time.sleep(.005)
                self.assertTrue(predicate(),view.status.text() if view is not None else str(errors))
            def idle(view):spin(lambda:view.loaded and not view.busy and not view.client.pending_count,view)
            def close_owner(view):
                view.close_project(discard=True)
                spin(lambda:view.client.state=='closed' and not view.asset_client.busy,view)
            try:
                owned=root/'owned-source';owned.mkdir()
                source_client.adopt_pack(pack,owned);spin(lambda:not source_client.busy);self.assertFalse(errors,errors)
                ref=receipts[-1][1];owned_pack=owned/ref['pack_sha256']
                project=root/'chapter-project';project.mkdir()
                view=ContentView(host,asset_cooker=cooker,sample_asset_pack=owned_pack);views.append(view)
                view.new_project(project,'Modern surface acceptance',asset_profile='warm-beginning');idle(view)
                check({'chapter-content-v3','chapter-assets-v2'}<=view.client.capabilities,'Native owner advertises the implemented v3/surface contracts')
                check(ChapterProjectDefinition.load(project).asset_profile=='warm-beginning','Explicit project profile survives metadata readback')
                settings=next(row for row in view.rows if row.type_id=='authoring.ChapterSettings')
                check(dict(settings.fields)['asset_profile']=='warm_beginning','Native authoritative chapter profile matches metadata')
                view.select_entity(settings.uuid)
                check(view.field_editors['asset_profile'].isReadOnly(),'Profile is read-only in the chapter field editor')
                job,prompt=view.proposal_jobs.begin([settings.uuid]);view.proposal_jobs.cancel(job)
                check('asset_profile' not in prompt['objects'][0]['fields'],'AI authoring cannot propose a profile change')
                view.save_world();idle(view);document=project/'chapter.aiba';initial=document.read_bytes();metadata=(project/'.aibs-chapter-project.json').read_bytes()
                view.use_sample_asset();spin(lambda:not view.asset_client.busy,view)
                check(view._inspected_asset is not None and view._inspected_asset.get('kind')=='surface','Real cooker receipt retains the surface kind and texture counts')
                dependency=view.adopted_asset;self.assertIsNotNone(dependency,view.asset_status.text())
                head=view.client.head.head_revision;fingerprint=view.description.fingerprint
                view.preview_asset_placement('Saved textured board',center=(-35.,2.,10.),scale=(1.,1.,1.))
                spin(lambda:not view.busy and not view.client.pending_count,view)
                check(view.apply_button.isEnabled() and view.client.head.head_revision==head and view.description.fingerprint==fingerprint,
                      'Surface placement Preview stays private until explicit Apply')
                check(document.read_bytes()==initial,'Private Preview does not write the saved chapter')
                view.apply_preview();idle(view);placement=next(row for row in view.rows if row.type_id=='authoring.AssetPlacement');identity=placement.uuid
                check(view.select_entity(identity),'Applied surface placement remains addressable by persistent UUID')
                view.field_editors['x'].setText('-34.25');before_transform=view.description.fingerprint
                view.preview_selected();spin(lambda:not view.busy and not view.client.pending_count,view)
                check(view.description.fingerprint==before_transform,'Typed transform Preview does not publish state')
                view.apply_preview();idle(view)
                check(dict(next(row for row in view.rows if row.uuid==identity).fields)['x']==-34.25,'Typed transform Apply updates the surface instance')
                view._travel(False);idle(view)
                check(dict(next(row for row in view.rows if row.uuid==identity).fields)['x']==-35.,'Undo restores the prior surface transform')
                view._travel(True);idle(view)
                check(dict(next(row for row in view.rows if row.uuid==identity).fields)['x']==-34.25,'Redo restores the edited surface transform')
                view.save_world();idle(view);saved=document.read_bytes();fingerprint=view.description.fingerprint
                fields=dict(next(row for row in view.rows if row.uuid==identity).fields);history=(view.client.head.undo_depth,view.client.head.redo_depth);epoch=view.client.head.scope.host_epoch
                close_owner(view)
                away=owned_pack.with_name(owned_pack.name+'.away');self.assertTrue(away.resolve().is_relative_to(root));owned_pack.rename(away)
                reopened=ContentView(host,asset_cooker=cooker);views.append(reopened);reopened.open_project(project);idle(reopened)
                check(reopened.client.head.scope.host_epoch!=epoch,'Reopen starts a genuinely new native owner')
                check(dict(next(row for row in reopened.rows if row.uuid==identity).fields)==fields,'Restart preserves placement UUID, immutable references and all transform fields')
                check(reopened.description.fingerprint==fingerprint and document.read_bytes()==saved,'Restart preserves the exact chapter fingerprint and saved bytes')
                check((reopened.client.head.undo_depth,reopened.client.head.redo_depth)==history,'Restart preserves Undo/Redo history')
                check((project/'.aibs-chapter-project.json').read_bytes()==metadata,'Restart keeps the explicit modern project metadata unchanged')
                with patch.object(reopened,'_use_snapshot') as dispatch:
                    reopened._begin_export('acceptance-export');spin(lambda:not reopened.busy and reopened._content_snapshot is not None,reopened)
                    dispatch.assert_called_once()
                snapshot=reopened._content_snapshot
                check(snapshot.asset_profile=='warm-beginning' and snapshot.asset_refs==(dependency,), 'Export pins modern profile and exact dependency closure for Preview and Play')
                destination=root/'private-packs';receipts.clear();errors.clear()
                source_client.stage_store(snapshot.asset_store,destination,snapshot.asset_refs,profile=snapshot.asset_profile)
                spin(lambda:not source_client.busy);self.assertFalse(errors,errors)
                staged=destination/dependency.pack_sha256;project_pack=project/'assets/packs'/dependency.pack_sha256
                check(sorted(p.name for p in staged.iterdir())==sorted(p.name for p in project_pack.iterdir()),'Real cooker stages the complete four-file private dependency pack')
                check(all(p.read_bytes()==(project_pack/p.name).read_bytes() for p in staged.iterdir()),'Private staged content is byte-identical without the original source pack')
                saved_metadata=json.loads(metadata);saved_metadata['asset_profile']='legacy_v1'
                mismatch=root/'mismatch';mismatch.mkdir();(mismatch/'chapter.aiba').write_bytes(saved)
                (mismatch/'.aibs-chapter-project.json').write_text(json.dumps(saved_metadata))
                invalid=ContentView(host,asset_cooker=cooker);views.append(invalid);invalid.open_project(mismatch)
                spin(lambda:not invalid.busy and not invalid.client.pending_count,invalid)
                check(not invalid.loaded and 'profile' in invalid.status.text().lower(),'Metadata cannot disguise a persisted modern document as legacy')
                check((mismatch/'chapter.aiba').read_bytes()==saved,'Rejected profile mismatch preserves saved document bytes')
                report.update(status='passed',placement_uuid=identity,asset=dependency.__dict__,fields=fields,
                    saved_fingerprint=fingerprint,saved_sha256=hashlib.sha256(saved).hexdigest(),history=list(history))
            finally:
                source_client.shutdown()
                for view in views:
                    view.asset_client.shutdown();view.play._shutdown();view.viewport._shutdown();view.client.abort('Surface acceptance cleanup')
                end=time.monotonic()+3
                while any(v.client.process_id for v in views) and time.monotonic()<end:APP.processEvents();time.sleep(.005)
                report['final_process_ids']=[{'owner':v.client.process_id,'asset_cli':v.asset_client.process_id,'viewport':v.viewport.process_id,'play':v.play.process_id} for v in views]
                for view in views:view.deleteLater()
                APP.processEvents();(root/'verification.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':unittest.main()
