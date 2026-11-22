import copy,hashlib,json,struct,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PyQt6.QtCore import QProcess,Qt
from PyQt6.QtWidgets import QApplication,QTreeWidgetItem
from native_studio.game_engine.asset_view import AssetView
from native_studio.game_engine.content_view import ContentView
from native_studio.game_engine import content_commands as commands
from native_studio.game_engine.content_commands import TypedRow,ContentExportDependency
from native_studio.game_engine.content_preview import ContentSnapshot,ContentExportAssembly
from native_studio.game_engine.project_assets import AssetDependency
from native_studio.game_engine.content_proposals import ProposalContext,encode_proposal
from native_studio.game_engine.content_jobs import ContentProposalJobs
from native_studio.game_engine.creator_payload import Scope,PayloadError
from test_asset_view import FakeProcess
APP=QApplication.instance() or QApplication([])
ASSET='876721b8-1abe-492a-926f-f5b922d23be9'
MEMORY='876721b8-1abe-492a-926f-f5b922d23be8'
SHA,PACK='a'*64,'b'*64
REF=AssetDependency(ASSET,SHA,PACK)
def audio_row(**changes):
 row={'asset_id':ASSET,'name':'Full original recording','sha256':SHA,'kind':'audio','sample_rate':44100,'channels':2,'bits_per_sample':16,'frame_count':8684544,'pcm_bytes':34738176,'decoded_bytes':34740000,'caption_count':0,'caption_text_bytes':0,'caption_review':'draft'}
 row['payload_bytes']=204+len(row['name'].encode())+row['pcm_bytes'];row.update(changes);return row
def memory_row():
 return TypedRow(MEMORY,'authoring.MemoryBinding','Optional memory',tuple(sorted({'name':'Optional memory','x':-35.,'y':1.,'z':10.,'audio_asset_id':ASSET,'audio_asset_sha256':SHA,'audio_pack_sha256':PACK}.items())))
class MemoryAssetReceipts(unittest.TestCase):
 def test_audio_receipt_preserves_full_source_format_and_computed_duration(self):
  row=AssetView._rows({'assets':[audio_row()]})[0]
  self.assertEqual((row['sample_rate'],row['channels'],row['frame_count']),(44100,2,8684544))
  self.assertAlmostEqual(row['duration_seconds'],196.92843537414967)
  self.assertEqual(row['caption_review'],'draft');self.assertNotIn('triangles',row)
 def test_audio_fields_are_bounded_exact_and_cannot_masquerade_as_geometry(self):
  for key,value in [('sample_rate',7999),('sample_rate',192001),('sample_rate',True),('channels',3),('bits_per_sample',32),('frame_count',True),('pcm_bytes',34738175),('payload_bytes',48*1024*1024+1),('decoded_bytes',64*1024*1024+1),('decoded_bytes',1),('caption_count',2049),('caption_review','approved'),('caption_text_bytes',256*1024+1),('triangles',1)]:
   with self.subTest(key=key,value=value),self.assertRaises(ValueError):AssetView._rows({'assets':[audio_row(**{key:value})]})
  missing=audio_row();del missing['payload_bytes']
  with self.assertRaises(ValueError):AssetView._rows({'assets':[missing]})
  malformed=audio_row();malformed['payload_bytes']+=1
  with self.assertRaises(ValueError):AssetView._rows({'assets':[malformed]})
 def test_checked_is_an_author_declaration_and_not_linguistic_approval(self):
  row=audio_row(caption_count=2,caption_text_bytes=25,caption_review='checked');row['payload_bytes']+=40+25
  admitted=AssetView._rows({'assets':[row]})[0]
  self.assertIn('author',AssetView.audio_summary(admitted).lower())
  self.assertIn('review',AssetView.audio_summary(admitted).lower())
  self.assertFalse(AssetView._preview_supported(object(),admitted))
 def test_legacy_surface_and_character_receipts_preserve_old_bounds(self):
  legacy={'asset_id':ASSET,'name':'Part','sha256':SHA,'triangles':1,'materials':1}
  self.assertEqual(AssetView._rows({'assets':[legacy]})[0],legacy)
  for kind in ('surface','character'):
   row={**legacy,'kind':kind,'image_count':0,'decoded_image_bytes':0,'decoded_bytes':300}
   if kind=='character':row.update(joint_count=1,clip_count=4,vertices=3)
   self.assertEqual(AssetView._rows({'assets':[row]})[0]['kind'],kind)
  with self.assertRaises(ValueError):AssetView._rows({'assets':[{**legacy,'triangles':100001}]})
 def test_audio_cooking_calls_native_without_materials_or_creating_output(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   for name in ('assetc.exe','player.exe','source.wav','rights.txt'):(root/name).write_bytes(b'synthetic')
   view=AssetView(root/'assetc.exe',root/'player.exe')
   try:
    with patch.object(view,'_start_tool') as start:
     view.cook_audio_asset(root/'source.wav',root/'rights.txt',root/'new',ASSET,'Recording')
     self.assertEqual(start.call_args.args[0],['--cook-audio','--source',str((root/'source.wav').resolve()),'--asset-id',ASSET,'--name','Recording','--license',str((root/'rights.txt').resolve()),'--output',str((root/'new').resolve())])
     self.assertFalse((root/'new').exists())
   finally:view.shutdown();view.deleteLater()
 def test_actual_qt_audio_receipt_display_and_failed_replacement_retains_rows(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);pack=root/'pack';pack.mkdir()
   for name in ('assetc.exe','player.exe'):(root/name).write_bytes(b'fixture')
   FakeProcess.instances=[]
   with patch('native_studio.game_engine.asset_view.QProcess',FakeProcess):
    view=AssetView(root/'assetc.exe',root/'player.exe')
    try:
     view.inspect_pack(pack);FakeProcess.instances[-1].finish({'status':'passed','assets':[audio_row()]})
     self.assertIn('44,100',view.status.text());self.assertIn('196.93',view.status.text());self.assertIn('review',view.status.text())
     self.assertFalse(view.preview_button.isEnabled());before=view.asset_rows
     view.inspect_pack(pack);FakeProcess.instances[-1].finish({'status':'passed','assets':[audio_row(payload_bytes=1)]})
     self.assertEqual(view.asset_rows,before);self.assertEqual(view.current_root,pack.resolve());self.assertIn('failed',view.status.text().lower())
    finally:view.shutdown();view.deleteLater()
class MemoryWire(unittest.TestCase):
 def test_native_v3_create_erase_roundtrip_and_legacy_version_dispatch(self):
  scope=Scope('project','main',str(uuid.uuid4()),'');definition=str(uuid.uuid4())
  create=commands.CreateMemoryBinding(MEMORY,'Memory',ASSET,SHA,PACK,(-35.,1.,10.))
  packet=commands.encode_scoped_edit(scope,definition,'create-memory',2,SHA,'Memory',(create,))
  self.assertEqual(commands.decode_scoped_edit(packet).edits,(create,))
  erased=commands.EraseMemoryBinding(MEMORY);self.assertEqual(commands.decode_scoped_edit(commands.encode_scoped_edit(scope,definition,'erase',2,SHA,'Erase',(erased,))).edits,(erased,))
  from native_studio.game_engine.creator_payload import _Reader
  def version(data):
   r=_Reader(data);r.read(6)
   for _ in range(4):r.text(True)
   return struct.unpack('<H',r.read(r.number('I'))[:2])[0]
  self.assertEqual(version(packet),3)
  self.assertEqual(version(commands.encode_scoped_edit(scope,definition,'legacy',2,SHA,'Legacy',(commands.SetField(MEMORY,'name','Name'),))),1)
  placement=commands.CreateAssetPlacement(MEMORY,'Part',ASSET,SHA,PACK,center=(-35.,1.,10.))
  self.assertEqual(version(commands.encode_scoped_edit(scope,definition,'placement',2,SHA,'Placement',(placement,))),2)
  mixed=commands.encode_scoped_edit(scope,definition,'mixed',2,SHA,'Mixed',(placement,create))
  self.assertEqual(version(mixed),3);self.assertEqual(commands.decode_scoped_edit(mixed).edits,(placement,create))
 def test_bad_memory_creation_values_reject_before_transport(self):
  scope=Scope('project','main',str(uuid.uuid4()),'');definition=str(uuid.uuid4())
  for position in [(1.,2.),(float('nan'),1.,2.),(True,1.,2.),(1e99,1.,2.)]:
   with self.subTest(position=position),self.assertRaises((ValueError,PayloadError)):
    commands.encode_scoped_edit(scope,definition,'bad',0,SHA,'Bad',(commands.CreateMemoryBinding(MEMORY,'Memory',ASSET,SHA,PACK,position),))
 def test_ai_cannot_assign_memory_references_even_with_forged_capabilities(self):
  for key in ('audio_asset_id','audio_asset_sha256','audio_pack_sha256'):
   context=ProposalContext('project','main',str(uuid.uuid4()),str(uuid.uuid4()),0,SHA,((MEMORY,key,'text'),))
   source=json.dumps({'version':1,'label':'Spoof','edits':[{'entity_id':MEMORY,'field':key,'value':ASSET if key.endswith('_id') else SHA}]})
   with self.subTest(key=key),self.assertRaises(ValueError):encode_proposal(source,context,'ai-edit')
 def test_controller_context_excludes_memory_refs_and_retains_name_position(self):
  scope=Scope('project','main',str(uuid.uuid4()),str(uuid.uuid4()))
  client=SimpleNamespace(state='ready',head=SimpleNamespace(scope=scope,head_revision=0),pending_count=0,generation=1)
  jobs=ContentProposalJobs(client,lambda:(str(uuid.uuid4()),SHA,(memory_row(),)))
  _,prompt=jobs.begin([MEMORY]);fields=prompt['objects'][0]['fields']
  self.assertEqual(set(fields),{'name','x','y','z'})
class MemoryCreatorUI(unittest.TestCase):
 def setUp(self):
  self.view=ContentView(Path('C:/unused.exe'));self.addCleanup(self.cleanup)
  self.view.definition=SimpleNamespace(asset_profile='warm-beginning')
  self.view._inspected_asset=AssetView._rows({'assets':[audio_row()]})[0]
  self.view.adopted_asset=REF;self.view.rows=(memory_row(),);self.view.selected_id=MEMORY
  self.view.client._capabilities=('chapter-memory-audio-v1',)
 def cleanup(self):
  self.view.definition=None;self.view.close();self.view.deleteLater();APP.processEvents()
 def test_audio_is_never_placed_as_geometry_or_assigned_as_adam(self):
  with patch.object(self.view,'_require_editable'):
   with self.assertRaises(ValueError):self.view.preview_asset_placement()
   with self.assertRaises(ValueError):self.view.preview_adam_model()
 def test_memory_creation_and_assignment_are_private_grouped_previews(self):
  with patch.object(self.view,'_require_editable'),patch.object(self.view,'_encode_edits',side_effect=lambda edits,label:tuple(edits)),patch.object(self.view,'_submit_packet') as submit:
   self.view.preview_memory_station('My memory',(-35.,1.,10.));create=submit.call_args.args[0][0]
   self.assertIsInstance(create,commands.CreateMemoryBinding);self.assertEqual((create.asset_id,create.asset_sha256,create.pack_sha256),(ASSET,SHA,PACK));self.assertFalse(submit.call_args.kwargs['apply_after_preview'])
   self.view.preview_memory_audio();edits=submit.call_args.args[0]
   self.assertEqual({e.field:e.value for e in edits},{'audio_asset_id':ASSET,'audio_asset_sha256':SHA,'audio_pack_sha256':PACK});self.assertFalse(submit.call_args.kwargs['apply_after_preview'])
 def test_missing_capability_or_uninspected_reference_cannot_create(self):
  with patch.object(self.view,'_require_editable'):
   self.view.client._capabilities=()
   with self.assertRaises(ValueError):self.view.preview_memory_station()
   self.view.client._capabilities=('chapter-memory-audio-v1',);self.view._inspected_asset=None
   with self.assertRaises(ValueError):self.view.preview_memory_station()
 def test_ref_fields_are_read_only_and_manual_tampering_is_rejected(self):
  item=QTreeWidgetItem(['Memory','authoring.MemoryBinding',MEMORY]);item.setData(0,Qt.ItemDataRole.UserRole,MEMORY);self.view.outliner.addTopLevelItem(item);self.view.outliner.setCurrentItem(item)
  for key in ('audio_asset_id','audio_asset_sha256','audio_pack_sha256'):self.assertTrue(self.view.field_editors[key].isReadOnly())
  self.view.field_editors['audio_asset_id'].setText(str(uuid.uuid4()))
  with patch.object(self.view,'_require_editable'),self.assertRaises(ValueError):self.view.preview_selected()
 def test_changed_pack_since_inspection_invalidates_adopted_audio(self):
  self.view._closing_project=False;self.view.definition.directory=Path('C:/project');self.view._asset_context=(self.view.client.generation,self.view.definition.directory);self.view._adopt_expected=(ASSET,SHA)
  self.view._asset_receipt('adopt',{'asset_id':ASSET,'asset_sha256':'c'*64,'pack_sha256':PACK})
  self.assertIsNone(self.view.adopted_asset);self.assertIsNone(self.view._inspected_asset)
 def test_buttons_require_verified_audio_role_and_native_capability(self):
  with tempfile.TemporaryDirectory() as directory:
   cooker=Path(directory)/'cooker.exe';cooker.write_bytes(b'fixture');self.view.asset_cooker=cooker
   self.view.client._capabilities=frozenset(('chapter-assets-v2','chapter-memory-audio-v1','chapter-content-export-v2'))
   self.view.save_button.setEnabled(True)
   with patch('native_studio.game_engine.creator_view.CreatorView._controls'),patch.object(self.view,'_play_binary',return_value=None):
    self.view._controls();self.assertTrue(self.view.asset_memory_create_button.isEnabled());self.assertTrue(self.view.asset_memory_assign_button.isEnabled())
    self.assertFalse(self.view.asset_place_button.isEnabled());self.assertFalse(self.view.asset_adam_button.isEnabled())
    self.view._inspected_asset=None;self.view._controls();self.assertFalse(self.view.asset_memory_create_button.isEnabled());self.assertFalse(self.view.asset_place_button.isEnabled())
 def test_old_native_player_is_not_selected_for_audio_chapter(self):
  player=Path('C:/owned/player.exe');features={'first_boot_content_play':True,'chapter_asset_surfaces':True}
  with patch.object(self.view,'_binary_candidates',return_value=(player,)),patch('native_studio.game_engine.content_view.read_native_player_capabilities',return_value={'features':features}):
   self.assertIsNone(self.view._play_binary());features['chapter-memory-audio-v1']=True;self.assertEqual(self.view._play_binary(),player)
   self.view.rows=();features.pop('chapter-memory-audio-v1');self.assertEqual(self.view._play_binary(),player)
if __name__=='__main__':unittest.main()
