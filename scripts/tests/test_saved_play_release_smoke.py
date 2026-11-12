"""Frozen smoke admission/dispatch only; never run a native window or service."""
import ast,importlib.util,json,os
from pathlib import Path
import subprocess,sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch,Mock
from native_studio import saved_play_release_smoke as smoke
ROOT=Path(__file__).resolve().parents[2]

class SavedSmokeAdmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.report=self.root/'smoke.json';self.work=self.root/'new-work'
    def result(self):return json.loads(self.report.read_text(encoding='utf-8'))
    def test_missing_native_window_flag_rejects_before_runner_or_work_writes(self):
        with patch.object(smoke,'_run_frozen')as run:
            self.assertEqual(smoke.run_saved_play_release_smoke(self.report,self.work),2)
        run.assert_not_called();self.assertFalse(self.work.exists())
        self.assertIn('allow-native-window',self.result()['error'])
        self.assertFalse(self.result()['application_services_started'])
        self.assertEqual(self.result()['native_windows_started'],0)
    def test_source_fallback_is_forbidden_even_with_flag(self):
        with patch.object(sys,'frozen',False,create=True),patch.object(smoke,'_run_frozen')as run:
            self.assertEqual(smoke.run_saved_play_release_smoke(self.report,self.work,allow_native_window=True),2)
        run.assert_not_called();self.assertIn('frozen',self.result()['error']);self.assertFalse(self.work.exists())
    def test_native_flag_requires_typed_true(self):
        for flag in (1,'true',None):
            report=self.root/('flag-'+str(flag)+'.json')
            with self.subTest(flag=flag),patch.object(smoke,'_run_frozen')as run:
                self.assertEqual(smoke.run_saved_play_release_smoke(report,self.work,allow_native_window=flag),2)
                run.assert_not_called()
    def test_existing_report_is_preserved_byte_exact(self):
        self.report.write_bytes(b'previous immutable proof')
        with patch.object(smoke,'_run_frozen')as run:
            self.assertEqual(smoke.run_saved_play_release_smoke(self.report,self.work,allow_native_window=True),2)
        run.assert_not_called();self.assertEqual(self.report.read_bytes(),b'previous immutable proof');self.assertFalse(self.work.exists())
    def test_existing_work_is_preserved_before_runner(self):
        self.work.mkdir();(self.work/'keep.txt').write_bytes(b'original')
        with patch.object(smoke,'_bundle_inputs',return_value={}),patch.object(smoke,'_run_frozen')as run:
            self.assertEqual(smoke.run_saved_play_release_smoke(self.report,self.work,allow_native_window=True),2)
        run.assert_not_called();self.assertEqual((self.work/'keep.txt').read_bytes(),b'original')
        self.assertIn('new',self.result()['error'].lower())
    def test_work_and_report_must_be_distinct_owned_paths(self):
        with self.assertRaises(ValueError):smoke._owned_paths(self.report,self.root)
        with self.assertRaises(ValueError):smoke._owned_paths(self.work,self.work)
    def test_failure_diagnostics_cannot_write_a_non_d_report(self):
        report=ROOT/'native_studio'/'saved-smoke-forbidden-output.json'
        with patch.object(Path,'open',side_effect=AssertionError('Unexpected report write'))as opened:
            self.assertEqual(smoke.run_saved_play_release_smoke(report,self.work),2)
        opened.assert_not_called()
    def test_guarded_runner_failure_remains_explicit_failed_scope(self):
        with patch.object(smoke,'_bundle_inputs',return_value={}),patch.object(smoke,'_run_frozen',side_effect=RuntimeError('synthetic pre-runtime failure')):
            self.assertEqual(smoke.run_saved_play_release_smoke(self.report,self.work,allow_native_window=True),2)
        data=self.result();self.assertEqual(data['status'],'failed');self.assertFalse(data['route_or_action_durability_verified'])
        self.assertFalse(data['actual_model_inference']);self.assertEqual(data['native_windows_started'],0)
    def test_empty_runner_cannot_claim_three_joined_native_invocations(self):
        with patch.object(smoke,'_bundle_inputs',return_value={}),patch.object(smoke,'_run_frozen'):
            self.assertEqual(smoke.run_saved_play_release_smoke(self.report,self.work,allow_native_window=True),2)
        self.assertIn('three native',self.result()['error']);self.assertEqual(self.result()['status'],'failed')
    def fixture_bundle(self):
        bundle=self.root/'bundle';binary=bundle/'game_assets/player';binary.mkdir(parents=True)
        (bundle/'game_assets/opening').mkdir()
        (bundle/'game_release.json').write_text(json.dumps({'require_saved_play':True,'saved_chapter_play_included':True}))
        for name in smoke.TOOLS.values():(binary/name).write_bytes(b'MZ synthetic not executed')
        (binary/'aibs_capabilities.json').write_text(json.dumps({'schema_version':1,'sdk_version':'0.16.0','target':'windows-x64','features':dict.fromkeys(smoke.FEATURES,True)}))
        return bundle,binary
    def test_bundled_admission_uses_actual_bounded_opening_api_before_runner(self):
        from native_studio.game_engine import opening_assets
        bundle,binary=self.fixture_bundle();data={}
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS',str(bundle),create=True),\
                patch.object(smoke,'__file__',str(bundle/'native_studio/saved_play_release_smoke.py')),\
                patch.object(smoke,'_origin',return_value='synthetic bundled origin'),\
                patch.object(opening_assets,'read_opening_assets',autospec=True,return_value=SimpleNamespace(manifest_sha256='a'*64))as read:
            result=smoke._bundle_inputs(data)
        read.assert_called_once_with(bundle/'game_assets/opening',verify_pack_contents=True)
        self.assertEqual(result['tools']['player'],binary/'aibs_motherboard.exe')
        self.assertEqual(data['opening_manifest_sha256'],'a'*64)
    def test_bad_frozen_metadata_or_sdk_capability_rejects_before_opening_read(self):
        bundle,binary=self.fixture_bundle();cap=binary/'aibs_capabilities.json';value=json.loads(cap.read_text());value['features']['chapter-saved-play-v1']=False;cap.write_text(json.dumps(value))
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS',str(bundle),create=True),\
                patch.object(smoke,'__file__',str(bundle/'native_studio/saved_play_release_smoke.py')):
            with self.assertRaisesRegex(ValueError,'SDK0.16'):smoke._bundle_inputs({})
            (bundle/'game_release.json').write_text(json.dumps({'require_saved_play':True,'saved_chapter_play_included':1}))
            with self.assertRaisesRegex(ValueError,'metadata'):smoke._bundle_inputs({})
    def test_packaged_module_must_resolve_inside_actual_bundle(self):
        bundle=self.root/'bundle';bundle.mkdir()
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS',str(bundle),create=True):
            with self.assertRaisesRegex(ValueError,'bundle|Bundled'):smoke._bundle_inputs({})
    def test_new_entry_is_before_heavy_app_imports(self):
        tree=ast.parse((ROOT/'native_studio/app.py').read_text(encoding='utf-8'))
        source=(ROOT/'native_studio/app.py').read_text(encoding='utf-8')
        self.assertLess(source.index("'--saved-play-release-smoke'"),source.index('from PyQt6.QtCore import Qt, QTimer'))
        self.assertIn('native_studio.saved_play_release_smoke',source)
        self.assertNotIn('sys.path',Path(smoke.__file__).read_text(encoding='utf-8'))
    def test_source_dispatch_without_allow_flag_never_reaches_normal_views_or_qt(self):
        script="""import builtins,runpy,sys
original=builtins.__import__
def guard(name,*args,**kwargs):
 if name.startswith(('backend.', 'PyQt6')) or name=='native_studio.executive_cockpit_full':raise RuntimeError('Forbidden heavy startup '+name)
 return original(name,*args,**kwargs)
builtins.__import__=guard
sys.argv=[sys.argv[1],'--saved-play-release-smoke',sys.argv[2],'--saved-play-work',sys.argv[3]]
runpy.run_path(sys.argv[0],run_name='__main__')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT/'native_studio/app.py'),str(self.report),str(self.work)],
            cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=20,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(result.returncode,2,result.stderr)
        data=self.result();self.assertIn('allow-native-window',data['error']);self.assertFalse(data['application_services_started'])
    def test_new_smoke_module_is_explicit_without_application_import(self):
        spec=importlib.util.spec_from_file_location('saved_smoke_builder',ROOT/'scripts/build_native_game_release.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        with patch.object(builder._graph,'native_modules',return_value=['native_studio','native_studio.app']):
            self.assertIn('native_studio.saved_play_release_smoke',builder.native_modules())

if __name__=='__main__':unittest.main()
