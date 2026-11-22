"""Curated manifest and owned asynchronous job contracts; synthetic data only."""
import hashlib,importlib.util,json,os,subprocess,sys,tempfile,time,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock,patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtWidgets import QApplication,QWidget
from PyQt6.QtCore import QTimer
from native_studio.game_engine.opening_assets import OPENING_ROLES,read_opening_assets,plain_path
from native_studio.game_engine.opening_project import OpeningProjectClient,_FEATURES
from native_studio.game_engine.content_view import ContentView
from native_studio.game_build_view import _opening_workspace_paths,_native_player_path,_asset_workspace_paths,GameBuildNativeView
APP=QApplication.instance()or QApplication([])

def write_fixture(root):
    value={'version':1,'roles':{}}
    for index,role in enumerate(OPENING_ROLES,1):
        directory=root/'packs'/role;directory.mkdir(parents=True)
        identity='00000000-0000-4000-8000-'+format(index,'012x')
        payload=('Synthetic owned '+role).encode();sha=hashlib.sha256(payload).hexdigest()
        suffix='.aibchar'if role=='adam'else'.aibmesh';name=sha+suffix
        header='AIBCAT 2\ncharacter 'if role=='adam'else'AIBCAT 1\n'
        files={name:payload,'catalog.aibcat':(header+identity+' '+sha+' '+name+'\n').encode(),
            'LICENSE.txt':b'Synthetic owned license','provenance.json':b'{"synthetic":true}\n'}
        native='AIBPACK 2\n'if role=='adam'else'AIBPACK 1\n'
        for filename,raw in sorted(files.items()):
            (directory/filename).write_bytes(raw)
            native+=filename+' '+str(len(raw))+' '+hashlib.sha256(raw).hexdigest()+'\n'
        pack=hashlib.sha256(native.encode()).hexdigest()
        value['roles'][role]={'directory':'packs/'+role,'asset_id':identity,'asset_sha256':sha,'pack_sha256':pack}
    (root/'opening-assets.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return value


STUB=r'''import json,os,shutil,sys,time
from pathlib import Path
root=Path(sys.argv[1]);behavior=sys.argv[2];mode=sys.argv[3];args=sys.argv[4:]
manifest=json.loads((root/'opening-assets.json').read_text());roles=manifest['roles']
with(root/'commands.jsonl').open('a')as f:f.write(json.dumps({'mode':mode,'args':args})+'\n')
if behavior=='blocked_adopt'and mode=='adopt':(root/'entered').write_text('yes');time.sleep(30)
if behavior=='failure'and mode=='adopt':print('Synthetic native failure',file=sys.stderr);raise SystemExit(2)
if mode=='adopt':
 source=Path(args[1]);store=Path(args[3]);entry=next(v for v in roles.values()if root/v['directory']==source)
 target=store/entry['pack_sha256']
 if not target.exists():shutil.copytree(source,target)
 result={'status':'passed',**{k:entry[k]for k in('asset_id','asset_sha256','pack_sha256')}}
 if behavior=='wrong_ref':result['pack_sha256']='f'*64
 print(json.dumps(result))
elif mode=='inspect':
 path=Path(args[1]);role=next(k for k,v in roles.items()if v['pack_sha256']==path.name);entry=roles[role]
 row={'asset_id':entry['asset_id'],'sha256':entry['asset_sha256'],'name':'Synthetic owned '+role,'triangles':1,'materials':1,
  'kind':'character'if role=='adam'else'mesh','image_count':0,'decoded_image_bytes':0,'decoded_bytes':1024}
 if role=='adam':row.update(joint_count=22,clip_count=4,vertices=3)
 print(json.dumps({'status':'passed','assets':[row]}))
elif mode=='factory':
 assert '--workshop'in args and '--audio-pack'not in args
 output=Path(args[args.index('--output')+1]);output.mkdir()
 (output/'.aibs-chapter-project.json').write_text(json.dumps({'version':3,'project':'synthetic-opening','branch':'main','asset_profile':'warm-beginning','opening_workshop':True}))
 (output/'chapter.aiba').write_bytes(b'Synthetic native journal');(output/'opening.aibd').write_bytes(b'Synthetic native content')
 deps=[{'kind':1 if role=='adam'else 0,**{k:entry[k]for k in('asset_id','asset_sha256','pack_sha256')}}for role,entry in roles.items()]
 (output/'opening-manifest.json').write_text(json.dumps({'version':1,'opening_workshop':True,'recording_bound':False,'dependencies':deps}))
 if behavior=='published_then_blocked':(root/'published').write_text('yes');time.sleep(30)
 print('Synthetic native atomic publication completed')
'''


class OpeningManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.manifest=write_fixture(self.root)
    def write(self,value):
        (self.root/'opening-assets.json').write_text(json.dumps(value),encoding='utf-8')
    def test_exact_roles_references_and_full_native_digest(self):
        fast=read_opening_assets(self.root);full=read_opening_assets(self.root,verify_pack_contents=True)
        self.assertEqual(fast,full);self.assertEqual(tuple(a.role for a in full.roles),OPENING_ROLES)
        self.assertEqual(full.role('adam').kind,'character');self.assertGreater(full.total_bytes,0)
        self.assertEqual(full.manifest_sha256,hashlib.sha256(full.manifest_bytes).hexdigest())
    def test_stdlib_parser_loads_without_qt_or_application(self):
        import native_studio.game_engine.opening_assets as module
        script="import importlib.util,sys; p=importlib.util.spec_from_file_location('pure_manifest',sys.argv[1]); m=importlib.util.module_from_spec(p); p.loader.exec_module(m); b=m.read_opening_assets(sys.argv[2],verify_pack_contents=True); assert len(b.roles)==6; assert not any(n.startswith(('PyQt','native_studio'))for n in sys.modules)"
        p=subprocess.run([sys.executable,'-I','-B','-c',script,module.__file__,str(self.root)],capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32'else 0)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_closed_shape_rejects_audio_extra_missing_wrong_boolean_versions(self):
        for change in ('extra','audio','missing','bool','version','role_extra','reference_type'):
            value=json.loads(json.dumps(self.manifest))
            if change=='extra':value['other']=True
            elif change=='audio':value['roles']['audio']=value['roles']['adam']
            elif change=='missing':del value['roles']['fault']
            elif change=='bool':value['version']=True
            elif change=='version':value['version']=2
            elif change=='role_extra':value['roles']['adam']['kind']='character'
            else:value['roles']['adam']['asset_sha256']=1
            self.write(value)
            with self.subTest(change=change),self.assertRaises(ValueError):read_opening_assets(self.root)
    def test_duplicate_keys_and_byte_bounds_reject(self):
        for raw in ('{"version":1,"version":1,"roles":{}}','x'*16385,'{"version":NaN,"roles":{}}'):
            (self.root/'opening-assets.json').write_text(raw)
            with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):read_opening_assets(self.root)
    def test_absolute_traversal_redirection_and_directory_aliases_reject(self):
        for relative in ('../escape','/absolute','C:/secret','packs\\adam','packs/../adam','packs//adam','packs/adam/'):
            value=json.loads(json.dumps(self.manifest));value['roles']['adam']['directory']=relative;self.write(value)
            with self.subTest(relative=relative),self.assertRaises(ValueError):read_opening_assets(self.root)
        self.write(self.manifest);target=self.root/'packs/adam'
        with patch.object(Path,'is_junction',lambda path:path==target),self.assertRaises(ValueError):read_opening_assets(self.root)
    def test_unexpected_file_and_audio_payload_reject(self):
        extra=self.root/'packs/capacitor/private.mp4';extra.write_bytes(b'synthetic')
        with self.assertRaises(ValueError):read_opening_assets(self.root)
        extra.unlink();asset=read_opening_assets(self.root).role('capacitor');asset.payload.rename(asset.payload.with_suffix('.aibaud'))
        with self.assertRaises(ValueError):read_opening_assets(self.root)
    def test_catalog_payload_and_pack_hash_mismatches_reject(self):
        asset=read_opening_assets(self.root).role('nook');asset.payload.write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'SHA256'):read_opening_assets(self.root,verify_pack_contents=True)
        value=json.loads(json.dumps(self.manifest));value['roles']['nook']['asset_id']='f0000000-0000-4000-8000-000000000000';self.write(value)
        with self.assertRaisesRegex(ValueError,'catalog'):read_opening_assets(self.root)
    def test_oversized_and_missing_files_reject_before_payload_read(self):
        asset=read_opening_assets(self.root).role('capacitor')
        original=Path.stat
        def stat(path,*args,**kwargs):
            result=original(path,*args,**kwargs)
            if path==asset.payload:
                values=list(result);values[6]=32*1024*1024+1;return os.stat_result(values)
            return result
        with patch.object(Path,'stat',stat),self.assertRaisesRegex(ValueError,'budget'):read_opening_assets(self.root)


class OpeningJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.resources=self.root/'opening';self.resources.mkdir();write_fixture(self.resources)
        self.tools=self.root/'tools';self.tools.mkdir()
        for name in ('aibs_warm_opening_project.exe','aibs_assetc.exe','aibs_content_host.exe'):(self.tools/name).write_bytes(b'synthetic placeholder')
        self.caps={'schema_version':1,'sdk_version':'0.15.0','features':{key:True for key in _FEATURES}}
        (self.tools/'aibs_capabilities.json').write_text(json.dumps(self.caps))
        self.script=self.root/'native_stub.py';self.script.write_text(STUB)
        self.client=OpeningProjectClient(self.tools/'aibs_warm_opening_project.exe',self.resources,self.tools/'aibs_content_host.exe')
        self.flags={'valid':True};self.client.context_valid=lambda:self.flags['valid']
        self.results=[];self.errors=[];self.closed=[]
        self.client.completed.connect(self.results.append);self.client.failed.connect(self.errors.append);self.client.closed.connect(lambda:self.closed.append(True))
        self.behavior='normal';original=self.client._launch
        def launch(exe,args,mode):original(Path(sys.executable),[str(self.script),str(self.resources),self.behavior,mode,*args],mode)
        self.client._launch=launch
        self.addCleanup(self.cleanup)
    def spin(self,predicate,seconds=12):
        deadline=time.monotonic()+seconds
        while not predicate()and time.monotonic()<deadline:APP.processEvents();time.sleep(.002)
        self.assertTrue(predicate(),str(self.errors)+' state='+self.client.state)
    def cleanup(self):
        self.client.stop();self.spin(lambda:not self.client.busy);self.assertEqual(self.client.process_id,0)
        self.client.deleteLater();APP.processEvents()
    def test_async_six_pack_adopt_inspect_then_exact_factory_arguments(self):
        heartbeats=[];timer=QTimer();timer.setInterval(5);timer.timeout.connect(lambda:heartbeats.append(1));timer.start()
        self.client.start(self.root/'NewOpening');self.assertTrue(self.client.busy);self.spin(lambda:not self.client.busy);timer.stop()
        self.assertFalse(self.errors);self.assertEqual(len(self.results),1);self.assertGreater(len(heartbeats),0)
        records=[json.loads(line)for line in(self.resources/'commands.jsonl').read_text().splitlines()]
        self.assertEqual([r['mode']for r in records],['adopt','inspect']*6+['factory'])
        args=records[-1]['args'];self.assertEqual(args[:3],['--workshop','--output',str(self.root/'NewOpening')])
        self.assertNotIn('--audio-pack',args)
        self.assertEqual({args[i]for i in range(3,len(args),2)},{'--'+r+'-pack'for r in OPENING_ROLES})
        self.assertFalse(list(self.root.glob('.aibs-opening-*')));self.assertEqual(self.client.process_id,0)
    def test_existing_output_and_unsupported_host_refuse_before_launch(self):
        output=self.root/'Existing';output.mkdir();(output/'keep').write_text('unchanged')
        with patch.object(self.client,'_launch')as launch,self.assertRaises(ValueError):self.client.start(output)
        launch.assert_not_called();self.assertEqual((output/'keep').read_text(),'unchanged')
        self.caps['sdk_version']='0.14.0';(self.tools/'aibs_capabilities.json').write_text(json.dumps(self.caps))
        with patch.object(self.client,'_launch')as launch,self.assertRaisesRegex(ValueError,'SDK0.15'):self.client.start(self.root/'New')
        launch.assert_not_called()
    def test_bad_manifest_and_wrong_native_reference_never_publish(self):
        self.behavior='wrong_ref';self.client.start(self.root/'New');self.spin(lambda:not self.client.busy)
        self.assertTrue(self.errors);self.assertFalse(self.results);self.assertFalse((self.root/'New').exists())
        self.assertFalse(list(self.root.glob('.aibs-opening-*')))
    def test_native_failure_cancels_pipeline_and_joins(self):
        self.behavior='failure';self.client.start(self.root/'New');self.spin(lambda:not self.client.busy)
        self.assertEqual(len(self.errors),1);self.assertFalse(self.results);self.assertFalse((self.root/'New').exists())
    def test_busy_and_explicit_cancel_join_without_output(self):
        self.behavior='blocked_adopt';self.client.start(self.root/'New');self.spin(lambda:(self.resources/'entered').exists())
        with self.assertRaises(ValueError):self.client.start(self.root/'Another')
        self.client.stop();self.spin(lambda:not self.client.busy)
        self.assertFalse(self.results);self.assertEqual(self.client.process_id,0);self.assertFalse((self.root/'New').exists())
    def test_stale_context_watchdog_kills_and_joins_without_opening(self):
        self.behavior='blocked_adopt';self.client.start(self.root/'New');self.spin(lambda:(self.resources/'entered').exists())
        self.flags['valid']=False;self.spin(lambda:not self.client.busy)
        self.assertFalse(self.results);self.assertFalse((self.root/'New').exists())
    def test_cancel_after_publication_preserves_output_and_never_reports_completion(self):
        self.behavior='published_then_blocked';output=self.root/'New';self.client.start(output);self.spin(lambda:(self.resources/'published').exists())
        before={p.name:p.read_bytes()for p in output.iterdir()};self.client.stop();self.spin(lambda:not self.client.busy)
        self.assertFalse(self.results);self.assertEqual({p.name:p.read_bytes()for p in output.iterdir()},before)
    def test_view_default_is_unavailable_and_open_project_is_not_discarded(self):
        view=ContentView(self.tools/'aibs_content_host.exe')
        try:
            self.assertFalse(view.opening_create_button.isEnabled());self.assertIn('not included',view.opening_status.text())
            view.definition=object()
            with patch.object(view.opening_client,'start')as start,self.assertRaises(ValueError):view.create_first_boot_opening(self.root/'New')
            start.assert_not_called()
        finally:view.definition=None;view.close();view.deleteLater();APP.processEvents()
    def test_bundle_resource_pairing_has_no_private_source_fallback(self):
        bundle=self.root/'bundle';player=bundle/'game_assets/player';opening=bundle/'game_assets/opening';player.mkdir(parents=True);opening.mkdir()
        factory=player/'aibs_warm_opening_project.exe';factory.write_bytes(b'placeholder');host=player/'aibs_content_host.exe'
        with patch('native_studio.game_build_view._bundle_root',return_value=bundle):self.assertEqual(_opening_workspace_paths(Path('C:/unused'),host),(factory,opening))
    def test_source_discovery_prefers015_runtime_and_preserves_legacy_fallback(self):
        source=self.root/'source';modern=source/'engine/install/0.15.0/runtime-release/bin';old=source/'engine/install/0.11.0/release/bin'
        opening=source/'engine/assets/cooked/warm-opening';opening.mkdir(parents=True)
        for directory in(modern,old):
            directory.mkdir(parents=True)
            for name in('aibs_motherboard.exe','aibs_assetc.exe','aibs_content_host.exe'):(directory/name).write_bytes(b'fixture')
        (modern/'aibs_warm_opening_project.exe').write_bytes(b'fixture')
        with patch('native_studio.game_build_view._bundle_root',return_value=None):
            self.assertEqual(_native_player_path(source),modern/'aibs_motherboard.exe')
            self.assertEqual(_asset_workspace_paths(source)[0],modern/'aibs_assetc.exe')
            self.assertEqual(_opening_workspace_paths(source,modern/'aibs_content_host.exe'),(modern/'aibs_warm_opening_project.exe',opening))
            dummy=SimpleNamespace(root=source,content_view=None,_content_page=QWidget(),_content_layout=Mock())
            with patch('native_studio.game_engine.content_view.ContentView',return_value=QWidget())as creator:
                GameBuildNativeView._workspace_changed(dummy,2)
                self.assertEqual(creator.call_args.args[0],modern/'aibs_content_host.exe')
                self.assertEqual(creator.call_args.kwargs['opening_assets_root'],opening)
            (modern/'aibs_motherboard.exe').unlink()
            self.assertEqual(_native_player_path(source),old/'aibs_motherboard.exe')
            self.assertEqual(_asset_workspace_paths(source)[0],old/'aibs_assetc.exe')

if __name__=='__main__':unittest.main()
