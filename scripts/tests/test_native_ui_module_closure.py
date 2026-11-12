"""Isolated source/namespace import proof; never creates QApplication or a window."""
import sys
sys.dont_write_bytecode=True
import hashlib,importlib.util,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
CANONICAL=Path(r'C:/AI-BS')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
builder=load('staged_game_builder',ROOT/'scripts/build_native_game_release.py');builder.ROOT=CANONICAL;builder._graph.ROOT=CANONICAL
verifier=load('staged_creator_verifier',ROOT/'scripts/verify_native_creator_release.py')
UI={'ui_modernization','ui_modernization.components','ui_modernization.components.native_badge','ui_modernization.generated','ui_modernization.generated.native_palette','ui_modernization.generated.studio_overview'}
class UiClosure(unittest.TestCase):
 def test_actual_graph_declares_complete_ui_closure(self):
  modules=set(builder.native_modules());self.assertTrue(UI<=modules,sorted(UI-modules));self.assertNotIn('tools',modules);self.assertNotIn('backend',modules)
 def test_namespace_and_reviewed_source_mapping(self):
  self.assertIsNone(builder.module_source('ui_modernization.generated'))
  self.assertEqual(builder.module_source('ui_modernization.components'),'ui_modernization/components/__init__.py')
  self.assertEqual(verifier.module_relative('ui_modernization.components.native_badge'),'ui_modernization/components/native_badge.py')
  self.assertIsNone(verifier.module_relative('ui_modernization.generated'))
  for name in ['tools.tool_registry','backend.core','ui_modernization.compiler','other_package']:
   with self.assertRaises(ValueError):verifier.module_relative(name)
 def test_actual_old_studio98_plan_rejected_for_missing_ui_dependency(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as directory:
   source=Path(directory);(source/'native_studio').mkdir();(source/'native_studio/app.py').write_text('from ui_modernization.generated.studio_overview import OVERVIEW_QSS\n')
   with self.assertRaisesRegex(ValueError,'Missing declared local import: ui_modernization'):
    verifier.verify_local_import_closure(source,{'native_studio/app.py':'native_studio.app'},{'native_studio','native_studio.app'})
  # Independently exercise the retained actual failing package when available;
  # the always-run synthetic omission above keeps clean checkouts self-contained.
  base=CANONICAL/'backups/native_game98_checkpoint09'
  if (base/'plan.json').is_file():
   plan=json.loads((base/'plan.json').read_text());mapping={relative:name for name in plan['modules'] if (relative:=verifier.module_relative(name)) is not None}
   with self.assertRaisesRegex(ValueError,'Missing declared local import: ui_modernization'):
    verifier.verify_local_import_closure(base/'source',mapping,set(plan['modules']))
 def test_staging_copies_five_ui_sources_and_preserves_namespace(self):
  fixtures=load('ui_game_fixture',ROOT/'scripts/tests/test_native_game_release.py')
  case=fixtures.NativeGameReleaseTests();case.setUp();self.addCleanup(case.doCleanups)
  names=['native_studio','native_studio.app','native_studio.game_build_view','native_studio.game_build_monitor',*sorted(UI)]
  expected=set()
  for name in UI:
   relative=builder.module_source(name)
   if relative is None:continue
   expected.add(relative);target=case.root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((CANONICAL/relative).read_bytes())
  with patch.object(fixtures.builder,'native_modules',return_value=names):plan=case.stage()
  self.assertTrue(expected<={row['relative'] for row in plan['files']});self.assertEqual(plan['namespaceModules'],['ui_modernization.generated']);self.assertFalse((case.work/'source/ui_modernization/generated/__init__.py').exists())
 def test_verifier_ui_byte_equivalence_and_namespace_kind(self):
  fixtures=load('ui_verifier_fixture',ROOT/'scripts/tests/test_native_creator_verification.py')
  case=fixtures.CreatorVerificationTests();case.setUp();self.addCleanup(case.doCleanups)
  case.plan['modules']=[*case.plan['modules'],*sorted(UI)];case.plan['namespaceModules']=['ui_modernization.generated']
  for name in UI:
   relative=verifier.module_relative(name)
   if relative is None:case.codes[name]=None;continue
   data=(CANONICAL/relative).read_bytes();case.write_staged(relative,data);case.codes[name]=compile(data,relative,'exec')
  case.write_plan()
  frozen={'names':set(case.codes),'code':case.codes,'entry_code':case.codes['native_studio.app'],'namespace_packages':{'ui_modernization.generated'}}
  with patch.object(fixtures.verifier,'read_frozen_archive',return_value=frozen):
   report=fixtures.verifier.verify_release(case.work);self.assertEqual(report['status'],'passed');self.assertEqual(report['frozen_module_equivalence']['ui_modernization.generated']['status'],'NamespacePackage')
   original=case.codes['ui_modernization.generated.studio_overview'];case.codes['ui_modernization.generated.studio_overview']=compile('OVERVIEW_QSS="wrong"','stale.py','exec')
   with self.assertRaisesRegex(ValueError,'Frozen code differs'):fixtures.verifier.verify_release(case.work)
   case.codes['ui_modernization.generated.studio_overview']=original;frozen['namespace_packages']=set()
   with self.assertRaisesRegex(ValueError,'namespace package types'):fixtures.verifier.verify_release(case.work)
 def test_actual_isolated_staged_normal_import_graph(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as directory:
   stage=Path(directory);self.assertEqual(stage.resolve().parent,ROOT.resolve())
   modules=builder.native_modules()
   for module in modules:
    relative=builder.module_source(module)
    if relative is None:continue
    target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(CANONICAL/relative,target)
   mapping={relative:name for name in modules if (relative:=verifier.module_relative(name)) is not None}
   self.assertGreater(verifier.verify_local_import_closure(stage,mapping,set(modules)),0)
   script=r'''import importlib.abc,importlib.machinery,json,sys
from pathlib import Path
stage=Path(sys.argv[1]).resolve();canonical=Path(sys.argv[2]).resolve()
sys.dont_write_bytecode=True;sys.frozen=True;sys._MEIPASS=str(stage)
sys.path=[p for p in sys.path if p and not Path(p).resolve().is_relative_to(canonical)];sys.path.insert(0,str(stage))
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='backend' or fullname.startswith('backend.'):raise ImportError('Server modules prohibited by isolated cold-import proof')
  if fullname.split('.')[0] in {'native_studio','ui_modernization'}:
   spec=importlib.machinery.PathFinder.find_spec(fullname,path)
   if spec is None:raise ModuleNotFoundError('Missing staged local module: '+fullname)
   locations=list(spec.submodule_search_locations or [])
   if spec.origin not in (None,'namespace'):locations.append(spec.origin)
   if any(not Path(p).resolve().is_relative_to(stage) for p in locations):raise ImportError('Repository fallback prohibited: '+fullname)
   return spec
sys.meta_path.insert(0,Guard())
import native_studio.app
from ui_modernization.components.native_badge import badge_style
from ui_modernization.generated.studio_overview import OVERVIEW_QSS
assert badge_style(True,False) and OVERVIEW_QSS
origins={n: str(getattr(m,'__file__',None)) for n,m in sys.modules.items() if n.split('.')[0] in {'native_studio','ui_modernization'}}
print(json.dumps({'status':'passed','normal_app_imported':True,'mainwindow_created':False,'module_origins':origins,'namespace_preserved':not(stage/'ui_modernization/generated/__init__.py').exists()}))
'''
   environment=os.environ.copy()
   for key in ['PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH']:environment.pop(key,None)
   result=subprocess.run([sys.executable,'-I','-B','-c',script,str(stage),str(CANONICAL)],cwd=stage,env=environment,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
   self.assertEqual(result.returncode,0,result.stderr[-2500:]);observed=json.loads(result.stdout.splitlines()[-1]);self.assertTrue(observed['normal_app_imported']);self.assertTrue(observed['namespace_preserved']);self.assertFalse(observed['mainwindow_created'])
if __name__=='__main__':unittest.main(verbosity=2)
