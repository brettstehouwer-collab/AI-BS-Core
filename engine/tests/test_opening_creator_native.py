"""Opt-in actual Qt/native inspection preview/history/save/restart acceptance.

No native process is launched in ordinary unit runs. Inputs are synthetic authored
text, with no original family media, model inference or DX12/GPU process.
"""
import os,time,unittest,json,uuid,hashlib
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.content_commands import SetField
from native_studio.game_engine.opening_fields import INSPECTION_CAPABILITY,INSPECTION_FIELDS

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@unittest.skipUnless(os.environ.get('AIBS_RUN_OPENING_CREATOR_NATIVE')=='1','Parent must supply a rebuilt host and private artifact directory')
class NativeOpeningCreatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance()or QApplication([])
    def setUp(self):
        self.host=Path(os.environ['AIBS_OPENING_CREATOR_HOST']).resolve(strict=True)
        base=Path(os.environ['AIBS_OPENING_CREATOR_ARTIFACTS']).resolve(strict=True)
        self.assertTrue(self.host.is_file()and base.is_dir())
        self.root=base/('opening-creator-'+str(uuid.uuid4()));self.root.mkdir()
        self.views=[];self.proof={'status':'failed','host':str(self.host),'host_sha256':sha(self.host),
            'original_family_media_used':False,'gpu_processes_requested':False,'inference_requested':False,'checks':[]}
    def spin(self,predicate,view=None,seconds=40):
        end=time.monotonic()+seconds
        while not predicate()and time.monotonic()<end:self.app.processEvents();time.sleep(.003)
        self.assertTrue(predicate(),view.status.text()if view else 'Timed out waiting for an owned process')
    def idle(self,view):self.spin(lambda:view.loaded and not view.busy and not view.client.pending_count,view)
    def make_view(self):
        view=ContentView(self.host);self.views.append(view);return view
    def fields(self,view,identity):return dict(next(r for r in view.rows if r.uuid==identity and r.type_id=='authoring.Fixture').fields)
    def preview_ready(self,view):self.spin(lambda:not view.busy and not view.client.pending_count,view);self.assertTrue(view.apply_button.isEnabled(),view.status.text())
    def apply(self,view):view.apply_preview();self.idle(view)
    def close_owner(self,view):view.close_project(discard=True);self.spin(lambda:view.client.state=='closed'and not view.client.process_id,view)
    def tearDown(self):
        for view in self.views:
            view.asset_client.shutdown();view.play._shutdown();view.viewport._shutdown();view.client.abort('Opening creator proof cleanup')
        end=time.monotonic()+4
        while any(v.client.process_id for v in self.views)and time.monotonic()<end:self.app.processEvents();time.sleep(.003)
        ids=[{'owner':v.client.process_id,'asset':v.asset_client.process_id,'play':v.play.process_id,'viewport':v.viewport.process_id}for v in self.views]
        active=any(any(record.values())for record in ids)
        self.proof['final_process_ids']=ids;self.proof['owned_processes_joined']=not active
        if active:self.proof['status']='failed';self.proof['error']='An owned process remained active'
        self.assertEqual(sha(self.host),self.proof['host_sha256'],'Host changed during acceptance')
        for view in self.views:view.definition=None;view.close();view.deleteLater()
        self.app.processEvents();(self.root/'verification.json').write_text(json.dumps(self.proof,indent=2)+'\n')
        self.assertFalse(active)
    def test_legacy_fixture_observations_remain17_and_creation_is_gated(self):
        view=self.make_view();project=self.root/'legacy';project.mkdir()
        view.new_project(project,'Legacy inspection compatibility',asset_profile='legacy_v1');self.idle(view)
        view.add_fixture('Legacy plain fixture');self.idle(view);identity=view.selected_id
        self.assertEqual(len(self.fields(view,identity)),17)
        self.assertFalse(set(INSPECTION_FIELDS)&self.fields(view,identity).keys())
        revision=view.client.head.head_revision
        with self.assertRaises(ValueError):view.preview_inspection_fixture('Synthetic panel','Synthetic text','Synthetic origin','read')
        self.assertEqual(view.client.head.head_revision,revision)
        self.assertFalse(view.inspection_create_button.isEnabled())
        view.save_world();self.idle(view);self.close_owner(view)
        self.proof['checks'].append('Actual native legacy profile retains17 geometry fields and blocks inspection creation')
        self.proof['status']='passed'
    def test_modern_grouped_panels_history_restart_erase_and_owned_export(self):
        view=self.make_view();project=self.root/'modern';project.mkdir()
        view.new_project(project,'Synthetic inspection authoring',asset_profile='warm-beginning');self.idle(view)
        self.assertIn(INSPECTION_CAPABILITY,view.client.capabilities)
        view.add_fixture('Unbound synthetic panel');self.idle(view);identity=view.selected_id
        empty=self.fields(view,identity);self.assertEqual(len(empty),20)
        self.assertEqual({k:empty[k]for k in INSPECTION_FIELDS},dict.fromkeys(INSPECTION_FIELDS,''))
        document=project/'chapter.aiba';before=document.read_bytes()if document.exists()else None
        revision=view.client.head.head_revision;fingerprint=view.description.fingerprint
        values={'inspection_text':'Synthetic authored reading.\nNo historical claim.','inspection_source':'Synthetic fixture source note','inspection_action':'read'}
        view.field_editors['inspection_text'].setPlainText(values['inspection_text'])
        view.field_editors['inspection_source'].setText(values['inspection_source'])
        action=view.field_editors['inspection_action'];action.setCurrentIndex(action.findData('read'))
        view.preview_selected();self.preview_ready(view)
        self.assertEqual(view.client.head.head_revision,revision);self.assertEqual(view.description.fingerprint,fingerprint)
        self.assertEqual(self.fields(view,identity),empty);self.assertEqual(document.read_bytes()if document.exists()else None,before)
        self.apply(view);bound=self.fields(view,identity)
        self.assertEqual({k:bound[k]for k in INSPECTION_FIELDS},values);self.assertEqual(view.client.head.head_revision,revision+1)
        self.assertEqual(document.read_bytes()if document.exists()else None,before)
        view._travel(False);self.idle(view);self.assertEqual(self.fields(view,identity),empty)
        view._travel(True);self.idle(view);self.assertEqual(self.fields(view,identity),bound)
        self.proof['checks'].append('Real modern20 observations, complete triple Preview, explicit Apply and Undo/Redo preserve head/disk separation')
        # A real stale pending creation must release its prepared native token.
        view.name_input.setText('Synthetic second panel');view.inspection_text_input.setPlainText('Synthetic quiet-seat text')
        view.inspection_source_input.setText('Synthetic second source');view.inspection_action_combo.setCurrentIndex(view.inspection_action_combo.findData('seat'))
        unchanged=view.client.head.head_revision
        view.preview_inspection_fixture(*view._inspection_creation_inputs(),center=(-34.,.6,8.))
        view.inspection_source_input.setText('Changed while Preview was pending')
        self.spin(lambda:not view.busy and not view.client.pending_count,view)
        self.assertFalse(view.apply_button.isEnabled());self.assertEqual(view.client.head.head_revision,unchanged)
        view.preview_inspection_fixture(*view._inspection_creation_inputs(),center=(-34.,.6,8.));self.preview_ready(view)
        self.assertEqual(view.client.head.head_revision,unchanged);self.apply(view);second=view.selected_id
        second_fields=self.fields(view,second);self.assertEqual(len(second_fields),20)
        self.assertEqual(second_fields['inspection_action'],'seat');self.assertEqual(second_fields['inspection_source'],'Changed while Preview was pending')
        self.assertEqual(view.client.head.head_revision,unchanged+1,'Create plus3SetFields must be one accepted transaction')
        self.proof['checks'].append('Stale pending creation rejects; refreshed Create17 plus three SetFields publishes as one native history operation')
        # Partial group/name/action errors cannot alter the accepted state.
        with self.assertRaises(ValueError):view.submit_edits((SetField(second,'inspection_action','award_quest'),),'No outcome commands')
        with self.assertRaises(ValueError):view.submit_edits((SetField(second,'inspection_source',''),),'No partial clear')
        self.assertEqual(self.fields(view,second),second_fields)
        view.select_entity(identity)
        view.field_editors['inspection_text'].setPlainText('');view.field_editors['inspection_source'].setText('');view.field_editors['inspection_action'].setCurrentIndex(0)
        view.preview_selected();self.preview_ready(view);self.apply(view)
        self.assertTrue(all(self.fields(view,identity)[k]==''for k in INSPECTION_FIELDS))
        view._travel(False);self.idle(view);self.assertEqual(self.fields(view,identity),bound)
        # Deletion removes the triple; undo/restart restore the exact binding.
        view.delete_selected();self.idle(view);self.assertFalse(any(r.uuid==identity for r in view.rows))
        view._travel(False);self.idle(view);self.assertEqual(self.fields(view,identity),bound)
        view._travel(True);self.idle(view);self.assertFalse(any(r.uuid==identity for r in view.rows))
        view._travel(False);self.idle(view);self.assertEqual(self.fields(view,identity),bound)
        view.save_world();self.idle(view);saved=sha(document);saved_fp=view.description.fingerprint
        history=(view.client.head.undo_depth,view.client.head.redo_depth);epoch=view.client.head.scope.host_epoch
        self.proof['checks'].append('Invalid action/partial clear reject; grouped unbind, erase, Undo/Redo and explicit Save retain coherent complete triples')
        self.close_owner(view)
        reopened=self.make_view();reopened.open_project(project);self.idle(reopened)
        self.assertNotEqual(reopened.client.head.scope.host_epoch,epoch)
        self.assertEqual(self.fields(reopened,identity),bound);self.assertEqual(self.fields(reopened,second),second_fields)
        self.assertEqual(reopened.description.fingerprint,saved_fp);self.assertEqual(sha(document),saved)
        self.assertEqual((reopened.client.head.undo_depth,reopened.client.head.redo_depth),history)
        with patch.object(reopened,'_use_snapshot')as consume:
            reopened._begin_export('preview');self.spin(lambda:not reopened.busy and not reopened.client.pending_count,reopened);consume.assert_called_once()
        snapshot=reopened._content_snapshot
        self.assertTrue(snapshot.authored_inspections)
        for value in [*values.values(),second_fields['inspection_source']]:self.assertIn(value.encode('utf-8'),snapshot.payload)
        self.assertEqual(snapshot.fingerprint,saved_fp)
        self.proof['checks'].append('Distinct real native owner restart and owned v3 Preview export preserve exact source/text/action and history')
        self.proof.update(status='passed',fixture_id=identity,second_fixture_id=second,inspection_fields=values,
            saved_document_sha256=saved,fingerprint=saved_fp,export_sha256=hashlib.sha256(snapshot.payload).hexdigest(),
            history=list(history),old_owner_epoch=epoch,new_owner_epoch=reopened.client.head.scope.host_epoch)
        self.close_owner(reopened)
if __name__=='__main__':unittest.main()
