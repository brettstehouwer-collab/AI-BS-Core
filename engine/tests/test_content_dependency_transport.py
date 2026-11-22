"""Complete native dependency closure transport; no native/GPU process required."""
import hashlib,os,struct,unittest,uuid
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from native_studio.game_engine import content_commands as commands
from native_studio.game_engine.content_commands import ContentDescription,ContentExportChunk,export_content,decode_content_export
from native_studio.game_engine.content_preview import ContentExportAssembly
from native_studio.game_engine.creator_payload import Scope,_Writer,_Reader
from native_studio.game_engine.project_assets import AssetDependency
from native_studio.game_engine.project_model import ProjectError
from native_studio.game_engine.content_view import ContentView

class DependencyTransportTests(unittest.TestCase):
 def setUp(self):
  self.scope=Scope('source-project','main',str(uuid.uuid4()),str(uuid.uuid4()));self.definition=str(uuid.uuid4());self.checkpoint=str(uuid.uuid4());self.payload=b'Native immutable AIBD3 chapter with placements, companion and audio';self.fp=hashlib.sha256(self.payload).hexdigest();self.description=ContentDescription(self.definition,5,self.fp,False,3)
  self.refs=tuple((i,AssetDependency(str(uuid.uuid4()),str(i+3)*64,str(i+6)*64)) for i in range(3))
 def wire(self,*,version=2,offset=0,payload=None,refs=None,total=None,definition=None,fp=None,revision=5):
  payload=self.payload[offset:] if payload is None else payload;refs=self.refs if refs is None else refs
  w=_Writer();w.number(version,'H');w.text(definition or self.definition,True);w.text(fp or self.fp,True);w.number(revision,'Q');w.number(len(self.payload) if total is None else total,'I');w.number(offset,'I');w.number(len(payload),'I')
  if version==2:
   w.number(len(refs),'I')
   for kind,ref in refs:w.number(kind,'B');w.text(ref.asset_id,True);w.text(ref.asset_sha256,True);w.text(ref.pack_sha256,True)
  w.append(payload);return bytes(w.data)
 def assembly(self,**kwargs):return ContentExportAssembly(self.scope,7,11,self.checkpoint,self.description,(),**kwargs)
 def accept(self,assembly,chunk,**kwargs):return assembly.accept(chunk,kwargs.get('scope',self.scope),kwargs.get('generation',7),kwargs.get('revision',11),kwargs.get('checkpoint',self.checkpoint))
 def test_requested_mode2_preserves_old_wire_by_default(self):
  old=export_content(self.scope,0,256,self.fp);new=export_content(self.scope,0,256,self.fp,complete_dependencies=True)
  r=_Reader(old);self.assertEqual(r.number('H'),1)
  for text in (self.scope.project,self.scope.branch,self.scope.world_id,self.scope.host_epoch):self.assertEqual(r.text(True),text)
  mode=r.offset;self.assertEqual(old[mode],1);self.assertEqual(new[mode],2);self.assertEqual(new[:mode],old[:mode]);self.assertEqual(new[mode+1:],old[mode+1:])
  for bad in (1,None,'yes'):
   with self.subTest(bad=bad),self.assertRaises(ValueError):export_content(self.scope,0,256,self.fp,complete_dependencies=bad)
 def test_wire2_owns_visual_character_and_audio_and_legacy_unchanged(self):
  chunk=decode_content_export(self.wire());self.assertEqual(chunk.version,2);self.assertEqual(tuple((d.kind,d.reference) for d in chunk.dependencies),self.refs);self.assertEqual(chunk.payload,self.payload);self.assertIsInstance(chunk.dependencies,tuple)
  legacy=decode_content_export(self.wire(version=1));self.assertEqual(legacy.version,1);self.assertEqual(legacy.dependencies,());self.assertEqual(legacy.payload,self.payload)
 def test_complete_native_closure_overrides_incomplete_or_foreign_row_list(self):
  extra=AssetDependency(str(uuid.uuid4()),'a'*64,'b'*64)
  assembly=self.assembly(asset_refs=(extra,),asset_profile='warm-beginning',asset_store='C:/owned/assets',require_complete_dependencies=True)
  result=self.accept(assembly,decode_content_export(self.wire()));self.assertEqual(result.asset_refs,tuple(ref for _,ref in self.refs));self.assertEqual(result.dependency_kinds,tuple(kind for kind,_ in self.refs));self.assertEqual(result.export_version,2);self.assertEqual(result.payload,self.payload);self.assertEqual(result.asset_store,Path('C:/owned/assets'))
 def test_multiple_versions_of_one_asset_uuid_are_not_discarded(self):
  identity=self.refs[0][1].asset_id;old=AssetDependency(identity,'a'*64,'b'*64);new=AssetDependency(identity,'c'*64,'d'*64)
  result=self.accept(self.assembly(require_complete_dependencies=True),decode_content_export(self.wire(refs=((0,old),(1,new)))))
  self.assertEqual(result.asset_refs,(old,new));self.assertEqual(result.dependency_kinds,(0,1))
 def test_complete_empty_closure_remains_explicit(self):
  result=self.accept(self.assembly(require_complete_dependencies=True),decode_content_export(self.wire(refs=())))
  self.assertEqual(result.asset_refs,());self.assertEqual(result.dependency_kinds,());self.assertEqual(result.export_version,2)
 def test_legacy_only_preserves_existing_placement_references(self):
  refs=tuple(ref for _,ref in self.refs[:1]);result=self.accept(self.assembly(asset_refs=refs),decode_content_export(self.wire(version=1)));self.assertEqual(result.asset_refs,refs);self.assertEqual(result.export_version,1)
 def test_requested_complete_export_rejects_downgrade_without_advancing(self):
  assembly=self.assembly(require_complete_dependencies=True)
  with self.assertRaisesRegex(ValueError,'complete|version|upgrade'):self.accept(assembly,decode_content_export(self.wire(version=1)))
  self.assertEqual(assembly.offset,0)
 def test_every_chunk_pins_version_and_entire_closure_without_partial_append(self):
  assembly=self.assembly(require_complete_dependencies=True);first=decode_content_export(self.wire(payload=self.payload[:8]));self.assertIsNone(self.accept(assembly,first));self.assertEqual(assembly.offset,8)
  changed=list(self.refs);changed[1]=(1,AssetDependency(changed[1][1].asset_id,'a'*64,changed[1][1].pack_sha256))
  for final in (decode_content_export(self.wire(offset=8,refs=tuple(changed))),decode_content_export(self.wire(offset=8,version=1)),replace(decode_content_export(self.wire(offset=8)),version=9)):
   with self.assertRaises(ValueError):self.accept(assembly,final)
   self.assertEqual(assembly.offset,8)
  result=self.accept(assembly,decode_content_export(self.wire(offset=8)));self.assertEqual(result.payload,self.payload)
 def test_all_source_context_pins_are_required_for_dependency_chunks(self):
  for changed in ({'scope':replace(self.scope,host_epoch=str(uuid.uuid4()))},{'scope':replace(self.scope,world_id=str(uuid.uuid4()))},{'generation':8},{'revision':12},{'checkpoint':str(uuid.uuid4())}):
   with self.subTest(changed=changed):
    assembly=self.assembly(require_complete_dependencies=True)
    with self.assertRaises(ValueError):self.accept(assembly,decode_content_export(self.wire()),**changed)
    self.assertEqual(assembly.offset,0)
  for chunk in (decode_content_export(self.wire(definition=str(uuid.uuid4()))),decode_content_export(self.wire(fp='a'*64)),decode_content_export(self.wire(revision=6))):
   assembly=self.assembly(require_complete_dependencies=True)
   with self.assertRaises(ValueError):self.accept(assembly,chunk)
   self.assertEqual(assembly.offset,0)
 def test_hash_corruption_cannot_publish_trusted_references(self):
  with self.assertRaisesRegex(ValueError,'hash'):self.accept(self.assembly(require_complete_dependencies=True),decode_content_export(self.wire(payload=b'X'*len(self.payload))))
 def test_dependency_count_kinds_and_canonical_order_are_bounded(self):
  ref=self.refs[0][1]
  for refs in (((3,ref),),((True,ref),),((0,ref),(0,ref)),tuple(reversed(self.refs)),((0,ref),(1,replace(ref,asset_sha256='a'*64)))):
   # bool encodes as numeric1 and is a valid wire kind; only test the invalid
   # typed manual object for that case below, not a wire distinction it lacks.
   if refs==((True,ref),):continue
   with self.subTest(refs=refs),self.assertRaises(ValueError):decode_content_export(self.wire(refs=refs))
  many=tuple((0,AssetDependency(str(uuid.uuid4()),'a'*64,f'{i:064x}')) for i in range(33))
  with self.assertRaises(ValueError):decode_content_export(self.wire(refs=many))
  valid=decode_content_export(self.wire());invalid=replace(valid,dependencies=(commands.ContentExportDependency(True,ref),))
  with self.assertRaises(ValueError):self.accept(self.assembly(require_complete_dependencies=True),invalid)
 def test_chunk_metadata_and_payload_types_cannot_bypass_decoder_guards(self):
  valid=decode_content_export(self.wire())
  for change in ({'total':True},{'offset':False},{'payload':bytearray(self.payload)},{'dependencies':list(valid.dependencies)}):
   with self.subTest(change=change),self.assertRaises(ValueError):self.accept(self.assembly(require_complete_dependencies=True),replace(valid,**change))
 def test_truncated_and_trailing_wire_never_publish(self):
  raw=self.wire()
  for data in (raw[:1],raw[:-1],raw+b'x',raw[:12]):
   with self.subTest(size=len(data)),self.assertRaises(ValueError):decode_content_export(data)

class ContentViewDependencyPolicyTests(unittest.TestCase):
 def fixture(self,profile,capabilities):
  scope=Scope('p','main',str(uuid.uuid4()),str(uuid.uuid4()));data=b'native content';description=ContentDescription(str(uuid.uuid4()),1,hashlib.sha256(data).hexdigest(),False,1)
  fake=SimpleNamespace(_require_editable=lambda:None,_closing_project=False,_snapshot_is_current=lambda:False,client=SimpleNamespace(head=SimpleNamespace(scope=scope,head_revision=3,checkpoint_id=''),generation=4,capabilities=frozenset(capabilities)),definition=SimpleNamespace(directory=Path('C:/owned'),asset_profile=profile),description=description,rows=(),_validated_asset_profile=lambda rows:profile,busy=False,status=SimpleNamespace(setText=lambda text:None),_controls=lambda:None)
  fake.sent=[];fake._send=lambda *args:fake.sent.append(args);fake._request_export=lambda:ContentView._request_export(fake);fake._use_snapshot=lambda *args:fake.sent.append(('used',args));return fake
 def test_capable_owner_requests_full_native_closure_without_row_reconstruction(self):
  fake=self.fixture('warm-beginning',{'chapter-content-export-v2'})
  with patch('native_studio.game_engine.content_view.dependencies_from_rows',side_effect=AssertionError('Rows must not reconstruct v2closure')):ContentView._begin_export(fake,'preview')
  self.assertTrue(fake._export.require_complete_dependencies);r=_Reader(fake.sent[0][2]);r.number('H')
  for _ in range(4):r.text(True)
  self.assertEqual(r.number('B'),2)
 def test_legacy_owner_fallback_retains_mode1(self):
  fake=self.fixture('legacy_v1',set());ContentView._begin_export(fake,'preview');self.assertFalse(fake._export.require_complete_dependencies)
  r=_Reader(fake.sent[0][2]);r.number('H')
  for _ in range(4):r.text(True)
  self.assertEqual(r.number('B'),1)
 def test_modern_profile_missing_capability_refuses_even_cached_snapshot(self):
  for action in ('preview','play'):
   fake=self.fixture('warm-beginning',set());fake._snapshot_is_current=lambda:True
   with self.subTest(action=action),self.assertRaisesRegex(ProjectError,'upgrade|Upgrade|complete|dependency'):ContentView._begin_export(fake,action)
   self.assertEqual(fake.sent,[]);self.assertFalse(fake.busy)

class AdamModelAssignmentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PyQt6.QtWidgets import QApplication
  cls.app=QApplication.instance() or QApplication([])
 def fixture(self):
  from native_studio.game_engine.content_commands import TypedRow
  view=ContentView(Path('C:/missing-native-owner.exe'));view._require_editable=lambda:None
  view.definition=SimpleNamespace(asset_profile='warm-beginning',directory=Path('C:/owned'))
  view.client._capabilities=frozenset({'chapter-assets-v2','chapter-character-assets-v1','chapter-content-export-v2'})
  reference=AssetDependency(str(uuid.uuid4()),'a'*64,'b'*64);view.adopted_asset=reference
  view._inspected_asset={'asset_id':reference.asset_id,'sha256':reference.asset_sha256,'kind':'character','name':'Authored Adam','triangles':100,'materials':2}
  identity=str(uuid.uuid4());fields=(('name','Adam memory'),('model_bound',False),('model_asset_id',''),('model_asset_sha256',''),('model_pack_sha256',''))
  view.rows=(TypedRow(identity,'authoring.CompanionBinding','Adam memory',fields),)
  return view,reference,identity
 def cleanup(self,view):view.definition=None;view.close();view.deleteLater();self.app.processEvents()
 def test_assignment_is_one_four_field_native_preview_and_never_auto_apply(self):
  view,reference,identity=self.fixture()
  try:
   with patch.object(view,'_encode_edits',return_value=b'native-proposal') as encode,patch.object(view,'_submit_packet',return_value=17) as submit:
    self.assertEqual(view.preview_adam_model(),17)
   edits=encode.call_args.args[0];self.assertEqual(tuple((e.uuid,e.field,e.value) for e in edits),((identity,'model_bound',True),(identity,'model_asset_id',reference.asset_id),(identity,'model_asset_sha256',reference.asset_sha256),(identity,'model_pack_sha256',reference.pack_sha256)))
   self.assertFalse(submit.call_args.kwargs['apply_after_preview']);self.assertTrue(submit.call_args.kwargs['placement_preview']);self.assertEqual(submit.call_args.kwargs['select_after'],identity)
  finally:self.cleanup(view)
 def test_character_pack_cannot_be_placed_as_static_scenery(self):
  view,_,_=self.fixture()
  try:
   with patch.object(view,'_submit_packet') as submit,self.assertRaisesRegex(ProjectError,'character|model|Adam'):view.preview_asset_placement('Wrong static character')
   submit.assert_not_called()
  finally:self.cleanup(view)
 def test_model_assignment_requires_verified_kind_identity_profile_capability_and_one_binding(self):
  for condition in ('wrong_sha','mesh','no_inspection','no_adoption','legacy','missing_capability','no_binding','two_bindings'):
   view,reference,identity=self.fixture()
   try:
    if condition=='wrong_sha':view._inspected_asset={**view._inspected_asset,'sha256':'c'*64}
    elif condition=='mesh':view._inspected_asset={**view._inspected_asset,'kind':'mesh'}
    elif condition=='no_inspection':view._inspected_asset=None
    elif condition=='no_adoption':view.adopted_asset=None
    elif condition=='legacy':view.definition.asset_profile='legacy_v1'
    elif condition=='missing_capability':view.client._capabilities=frozenset({'chapter-assets-v2','chapter-content-export-v2'})
    elif condition=='no_binding':view.rows=()
    else:view.rows=view.rows+(replace(view.rows[0],uuid=str(uuid.uuid4())),)
    with self.subTest(condition=condition),patch.object(view,'_submit_packet') as submit,self.assertRaises(ProjectError):view.preview_adam_model()
    submit.assert_not_called()
   finally:self.cleanup(view)
 def test_model_button_and_placement_button_have_distinct_admission(self):
  import tempfile
  from native_studio.game_engine.creator_view import CreatorView
  view,_,_=self.fixture()
  try:
   with tempfile.TemporaryDirectory() as directory:
    cooker=Path(directory)/'assetc.exe';cooker.write_bytes(b'not executed');view.asset_cooker=cooker;view.save_button.setEnabled(True)
    with patch.object(CreatorView,'_controls'),patch.object(view,'_play_binary',return_value=None):
     view._controls();self.assertTrue(view.asset_adam_button.isEnabled());self.assertFalse(view.asset_place_button.isEnabled())
     view._inspected_asset={**view._inspected_asset,'kind':'surface'};view._controls();self.assertFalse(view.asset_adam_button.isEnabled());self.assertTrue(view.asset_place_button.isEnabled())
  finally:self.cleanup(view)
 def test_bound_model_identity_is_readonly_in_inspector(self):
  from PyQt6.QtCore import Qt
  from PyQt6.QtWidgets import QTreeWidgetItem
  view,_,identity=self.fixture()
  try:
   row=view.rows[0];item=QTreeWidgetItem([row.name,row.type_id,row.uuid]);item.setData(0,Qt.ItemDataRole.UserRole,identity);view.outliner.addTopLevelItem(item);view.outliner.setCurrentItem(item);view._selection_changed()
   for field in ('model_asset_id','model_asset_sha256','model_pack_sha256'):self.assertTrue(view.field_editors[field].isReadOnly(),field)
   self.assertFalse(view.field_editors['model_bound'].isEnabled())
  finally:self.cleanup(view)
 def test_ready_controls_never_reenable_verified_model_bound_checkbox(self):
  from PyQt6.QtCore import Qt
  from PyQt6.QtWidgets import QTreeWidgetItem
  view,_,identity=self.fixture()
  try:
   scope=Scope('p','main',str(uuid.uuid4()),str(uuid.uuid4()))
   view.client._state='ready';view.client._head=SimpleNamespace(scope=scope,head_revision=4,checkpoint_id='',undo_depth=1,redo_depth=0)
   view._snapshot_tag=view._tag(view.client.head);view.loaded=True;view.busy=False
   row=view.rows[0];item=QTreeWidgetItem([row.name,row.type_id,row.uuid]);item.setData(0,Qt.ItemDataRole.UserRole,identity);view.outliner.addTopLevelItem(item)
   with patch.object(view,'_play_binary',return_value=None):
    view.outliner.setCurrentItem(item);view._selection_changed()
    for busy in (False,True,False):
     view.busy=busy;view._controls()
     self.assertEqual(view.field_editors['name'].isEnabled(),not busy)
     self.assertFalse(view.field_editors['model_bound'].isEnabled())
  finally:
   view.client._state='closed';view.client._head=None;view.busy=False;self.cleanup(view)

class InitialCharacterViewportSelectionContracts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PyQt6.QtWidgets import QApplication
  cls.app=QApplication.instance() or QApplication([])
 def test_selected_companion_survives_initial_publish_with_or_without_async_staging(self):
  import tempfile
  from native_studio.game_engine.content_preview import ContentSnapshot,ContentViewportClient
  from native_studio.game_engine.creator_viewport import ViewportClient
  class Stager:
   def __init__(self):self.busy=False
   def stage_store(self,*args,**kwargs):self.busy=True
   def stop(self):self.busy=False
   def shutdown(self):self.busy=False
  scope=Scope('p','main',str(uuid.uuid4()),str(uuid.uuid4()));identity=str(uuid.uuid4());reference=AssetDependency(str(uuid.uuid4()),'a'*64,'b'*64)
  for refs in ((),(reference,)):
   client=ContentViewportClient(asset_cooker=Path('C:/not-executed.exe'));client._stager=Stager();captured=[]
   snapshot=ContentSnapshot(scope,1,2,'',str(uuid.uuid4()),3,'a'*64,b'native content',frozenset((identity,)),refs,Path('C:/owned'),'warm-beginning',2,(1,) if refs else ())
   def publish(owner,executable,scope,revision,checkpoint_id,rows,first_boot=False,probe_directory=None,**kwargs):
    owner.publish(scope,revision,checkpoint_id,rows,first_boot)
    captured.append((owner._path/'scene.aibv').read_bytes())
   try:
    with self.subTest(staged=bool(refs)),patch.object(ViewportClient,'start',publish):
     client.start_content(Path('C:/not-executed.exe'),snapshot,selected_id=identity)
     if refs:
      client._stager.busy=False;client._stage_ready('stage',{'status':'passed'})
     self.assertEqual(len(captured),1)
     reader=_Reader(captured[0]);self.assertEqual(reader.read(4),b'AIBV');reader.number('H');reader.number('B')
     for _ in range(5):reader.text()
     reader.number('Q');self.assertEqual(reader.text(),identity)
   finally:
    if client._directory is not None:client._directory.cleanup();client._directory=None
    client._path=None;client._stage_pending=client._stage_active=None;client.state='closed';client.deleteLater();self.app.processEvents()

class CompanionModelProposalContracts(unittest.TestCase):
 def fixture(self):
  from native_studio.game_engine.content_jobs import ContentProposalJobs
  scope=Scope('p','main',str(uuid.uuid4()),str(uuid.uuid4()))
  client=SimpleNamespace(state='ready',pending_count=0,generation=1,head=SimpleNamespace(scope=scope,head_revision=4))
  fields=(('name','Adam'),('spawn_x',1.),('spawn_y',2.),('spawn_z',3.),('initial_follow',True),('model_bound',False),('model_asset_id',''),('model_asset_sha256',''),('model_pack_sha256',''))
  row=SimpleNamespace(uuid=str(uuid.uuid4()),type_id='authoring.CompanionBinding',name='Adam',fields=fields)
  definition=str(uuid.uuid4());jobs=ContentProposalJobs(client,lambda:(definition,'a'*64,(row,)))
  return scope,definition,row,jobs
 def test_verified_model_reference_fields_are_not_ai_capabilities(self):
  _,_,row,jobs=self.fixture();_,prompt=jobs.begin((row.uuid,))
  self.assertEqual(set(prompt['objects'][0]['fields']),{'name','spawn_x','spawn_y','spawn_z','initial_follow'})
 def test_raw_model_reference_proposals_reject_even_with_forged_field_capabilities(self):
  import json
  from native_studio.game_engine.content_proposals import ProposalContext,encode_proposal
  scope,definition,row,_=self.fixture()
  for field,value,kind in (('model_bound',True,'boolean'),('model_asset_id',str(uuid.uuid4()),'text'),('model_asset_sha256','c'*64,'text'),('model_pack_sha256','d'*64,'text')):
   context=ProposalContext.from_dict({'project':scope.project,'branch':scope.branch,'world_id':scope.world_id,'definition_id':definition,'revision':4,'fingerprint':'a'*64,'fields':[[row.uuid,field,kind]]})
   proposal=json.dumps({'version':1,'label':'Raw model ref','edits':[{'entity_id':row.uuid,'field':field,'value':value}]})
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'immutable|verified|model'):encode_proposal(proposal,context,'test')
 def test_safe_companion_authoring_remains_available(self):
  import json
  _,_,row,jobs=self.fixture();job,_=jobs.begin((row.uuid,))
  proposal=json.dumps({'version':1,'label':'Companion positioning','edits':[{'entity_id':row.uuid,'field':'name','value':'Adam memory'},{'entity_id':row.uuid,'field':'spawn_x','value':4.5},{'entity_id':row.uuid,'field':'initial_follow','value':False}]})
  result=commands.decode_scoped_edit(jobs.consume(job,proposal))
  self.assertEqual(tuple((edit.field,edit.value) for edit in result.edits),(('name','Adam memory'),('spawn_x',4.5),('initial_follow',False)))

if __name__=='__main__':unittest.main()
