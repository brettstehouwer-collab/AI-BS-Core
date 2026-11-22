"""Opt-in actual Qt/native memory creation, assignment, restart and role2 export.

Parent coordinates binaries and D: evidence storage; no native/GPU process is
started by ordinary unit tests. Supplied packs must be synthetic test assets.
"""
import hashlib,json,os,shutil,subprocess,time,unittest,uuid,wave
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine.content_commands import SetField
from native_studio.game_engine.project_assets import ProjectAssetClient

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def pack_hashes(root):
 paths=tuple(Path(root).iterdir())
 if len(paths)!=4 or any(p.is_symlink() or p.is_junction() or not p.is_file() for p in paths):
  raise AssertionError('Expected four plain immutable pack files')
 return {p.name:sha(p) for p in paths}

@unittest.skipUnless(os.environ.get('AIBS_RUN_MEMORY_UI_NATIVE')=='1',
 'Parent must opt in with explicit synthetic pack, native binaries and artifact root')
class NativeMemoryCreatorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_create_assign_history_save_restart_and_complete_audio_closure(self):
  self.assertEqual(os.environ.get('AIBS_MEMORY_UI_SYNTHETIC'),'1','Use only parent-reviewed synthetic input')
  required={name:Path(os.environ['AIBS_MEMORY_UI_'+name]).resolve(strict=True) for name in ('HOST','COOKER','PACK','ARTIFACTS')}
  self.assertTrue(required['HOST'].is_file() and required['COOKER'].is_file())
  self.assertTrue(required['PACK'].is_dir() and required['ARTIFACTS'].is_dir())
  root=required['ARTIFACTS']/('memory-creator-'+str(uuid.uuid4()));root.mkdir()
  source_hashes=pack_hashes(required['PACK']);owned=root/'owned-source';owned.mkdir()
  for name in source_hashes:shutil.copy2(required['PACK']/name,owned/name)
  project=root/'project';project.mkdir();views=[]
  stager=ProjectAssetClient(required['COOKER']);receipts=[];errors=[]
  stager.receipt.connect(lambda mode,value:receipts.append((mode,value)));stager.failed.connect(errors.append)
  proof={'schema_version':1,'status':'failed','input_declared_synthetic':True,'original_family_files_modified':False,
   'source_pack_hashes':source_hashes,'checks':[],'paths':{k:str(v) for k,v in required.items()},'work_directory':str(root)}
  def spin(predicate,view=None,seconds=45):
   until=time.monotonic()+seconds
   while not predicate() and time.monotonic()<until:self.app.processEvents();time.sleep(.004)
   self.assertTrue(predicate(),(view.status.text()+' | '+view.asset_status.text()) if view else str(errors))
  def idle(view):spin(lambda:view.loaded and not view.busy and not view.client.pending_count,view)
  def fields(view,identity):return dict(next(r for r in view.rows if r.uuid==identity and r.type_id=='authoring.MemoryBinding').fields)
  def close(view):view.close_project(discard=True);spin(lambda:view.client.state=='closed' and not view.client.process_id and not view.asset_client.busy,view)
  try:
   view=ContentView(required['HOST'],asset_cooker=required['COOKER']);views.append(view)
   view.new_project(project,'Memory creator proof',asset_profile='warm-beginning');idle(view)
   for cap in ('chapter-assets-v2','chapter-memory-audio-v1','chapter-content-export-v2'):self.assertIn(cap,view.client.capabilities)
   view.inspect_asset_pack(owned);spin(lambda:not view.asset_client.busy,view)
   self.assertEqual(view._inspected_asset['kind'],'audio',view.asset_status.text());initial_audio=dict(view._inspected_asset)
   self.assertFalse(view.asset_place_button.isEnabled());self.assertFalse(view.asset_adam_button.isEnabled())
   view.adopt_asset_pack();spin(lambda:not view.asset_client.busy,view);reference=view.adopted_asset;self.assertIsNotNone(reference)
   self.assertEqual(pack_hashes(project/'assets/packs'/reference.pack_sha256),source_hashes)
   document=project/'chapter.aiba';before=document.read_bytes() if document.exists() else None
   fingerprint=view.description.fingerprint;revision=view.client.head.head_revision
   view.preview_memory_station('Optional memory',(-35.,1.,10.));spin(lambda:not view.busy and not view.client.pending_count,view)
   self.assertTrue(view.apply_button.isEnabled(),view.status.text());self.assertEqual(view.description.fingerprint,fingerprint)
   self.assertEqual(view.client.head.head_revision,revision);self.assertFalse(any(r.type_id=='authoring.MemoryBinding' for r in view.rows))
   self.assertEqual(document.read_bytes() if document.exists() else None,before)
   view.apply_preview();idle(view);identity=view.selected_id;bound=fields(view,identity)
   self.assertEqual(tuple(bound[k] for k in ('audio_asset_id','audio_asset_sha256','audio_pack_sha256')),(reference.asset_id,reference.asset_sha256,reference.pack_sha256))
   self.assertEqual(document.read_bytes() if document.exists() else None,before,'Apply must not silently Save')
   for key in ('audio_asset_id','audio_asset_sha256','audio_pack_sha256'):self.assertTrue(view.field_editors[key].isReadOnly())
   proof['checks'].append('Verified audio adoption and private native station Preview preserve the previous head/disk; explicit Apply creates one exact role-bound memory')
   # A second small synthetic recording proves actual grouped assignment.
   wav_path=root/'synthetic-second.wav'
   with wave.open(str(wav_path),'wb') as wav:wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(44100);wav.writeframes(bytes(4410*4))
   rights=root/'synthetic-rights.txt';rights.write_text('Self-authored zero PCM fixture.\n',encoding='utf-8');second=root/'second-pack'
   completed=subprocess.run([str(required['COOKER']),'--cook-audio','--source',str(wav_path),'--asset-id',str(uuid.uuid4()),'--name','Synthetic second','--license',str(rights),'--output',str(second)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
   self.assertEqual(completed.returncode,0,completed.stderr.decode('utf-8','replace'))
   view.inspect_asset_pack(second);spin(lambda:not view.asset_client.busy,view);view.adopt_asset_pack();spin(lambda:not view.asset_client.busy,view);second_ref=view.adopted_asset
   view.preview_memory_audio();spin(lambda:not view.busy and not view.client.pending_count,view);self.assertEqual(fields(view,identity),bound);self.assertTrue(view.apply_button.isEnabled())
   view.apply_preview();idle(view);self.assertEqual(fields(view,identity)['audio_asset_id'],second_ref.asset_id)
   view._travel(False);idle(view);self.assertEqual(fields(view,identity),bound);view._travel(True);idle(view);self.assertEqual(fields(view,identity)['audio_asset_id'],second_ref.asset_id)
   view._travel(False);idle(view);self.assertEqual(fields(view,identity),bound)
   unchanged=view.client.head.head_revision;view.submit_edits((SetField(identity,'audio_asset_sha256','c'*64),),'Reject foreign digest')
   spin(lambda:not view.busy and not view.client.pending_count,view);self.assertEqual(view.client.head.head_revision,unchanged);self.assertEqual(fields(view,identity),bound)
   view.field_editors['x'].setText('-34.0');view.preview_selected();spin(lambda:not view.busy and not view.client.pending_count,view);view.apply_preview();idle(view)
   view.save_world();idle(view);saved=sha(document);metadata=sha(project/'.aibs-chapter-project.json');fingerprint=view.description.fingerprint
   history=(view.client.head.undo_depth,view.client.head.redo_depth);bound=fields(view,identity);epoch=view.client.head.scope.host_epoch
   proof['checks'].append('Actual grouped recording assignment, Undo/Redo, invalid-reference rollback, position editing and explicit Save retain exact memory references')
   close(view);away=root/'owned-source-away';self.assertTrue(owned.resolve().is_relative_to(root.resolve()) and away.resolve().is_relative_to(root.resolve()));owned.rename(away)
   reopened=ContentView(required['HOST'],asset_cooker=required['COOKER']);views.append(reopened);reopened.open_project(project);idle(reopened)
   self.assertNotEqual(reopened.client.head.scope.host_epoch,epoch);self.assertEqual(fields(reopened,identity),bound)
   self.assertEqual(reopened.description.fingerprint,fingerprint);self.assertEqual(sha(document),saved);self.assertEqual(sha(project/'.aibs-chapter-project.json'),metadata)
   self.assertEqual((reopened.client.head.undo_depth,reopened.client.head.redo_depth),history)
   with patch.object(reopened,'_use_snapshot') as use:reopened._begin_export('preview');spin(lambda:not reopened.busy and not reopened.client.pending_count,reopened);use.assert_called_once()
   snapshot=reopened._content_snapshot;self.assertEqual(snapshot.export_version,2);self.assertEqual(snapshot.asset_refs,(reference,));self.assertEqual(snapshot.dependency_kinds,(2,))
   self.assertFalse(any(r.type_id=='authoring.AssetPlacement' for r in reopened.rows),'Audio closure must come from native export, not placement rows')
   private=root/'independent-private-store';stager.stage_store(snapshot.asset_store,private,snapshot.asset_refs,profile=snapshot.asset_profile);spin(lambda:not stager.busy)
   self.assertFalse(errors);self.assertEqual(pack_hashes(private/reference.pack_sha256),source_hashes)
   self.assertEqual(pack_hashes(required['PACK']),source_hashes)
   proof.update(status='passed',memory_id=identity,memory_fields=bound,reference=reference.__dict__,first_owner_epoch=epoch,second_owner_epoch=reopened.client.head.scope.host_epoch,
    fingerprint=fingerprint,saved_sha256=saved,export_sha256=hashlib.sha256(snapshot.payload).hexdigest(),dependency_kinds=list(snapshot.dependency_kinds),initial_audio_metadata=initial_audio,private_pack_hashes=pack_hashes(private/reference.pack_sha256))
   proof['checks'].append('A distinct native owner restarts after copied source removal; complete role2 export and independent private staging retain all four audio pack files without placement rows')
   close(reopened)
  except Exception as error:proof['error']=str(error);raise
  finally:
   stager.shutdown()
   for view in views:
    view.asset_client.shutdown();view.play._shutdown();view.viewport._shutdown();view.client.abort('Memory creator acceptance cleanup')
   until=time.monotonic()+3
   while any(v.client.process_id for v in views) and time.monotonic()<until:self.app.processEvents();time.sleep(.004)
   proof['final_process_ids']=[{'owner':v.client.process_id,'asset':v.asset_client.process_id,'play':v.play.process_id,'viewport':v.viewport.process_id} for v in views]
   proof['stager_process_id']=stager.process_id
   active=bool(stager.process_id or any(any(record.values()) for record in proof['final_process_ids']))
   if active:proof['status']='failed';proof['error']='Owned process remained active after acceptance cleanup'
   for view in views:view.definition=None;view.close();view.deleteLater()
   self.app.processEvents();(root/'verification.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
   self.assertFalse(active,'Acceptance must join all owned native processes')
