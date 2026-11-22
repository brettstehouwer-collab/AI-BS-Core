import contextlib,hashlib,importlib.util,io,json,shutil,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
W=Path(__file__).parent
E=ROOT=tool=None
def configure(package,evidence):
 global E,ROOT,tool
 E=Path(evidence).absolute()
 if any(p.is_symlink()or p.is_junction()for p in(E,*E.parents)):raise ValueError('Evidence paths must not redirect')
 E.mkdir(exist_ok=False);ROOT=E/'Relocated Review Package';shutil.copytree(package,ROOT);(E/'retained').mkdir()
 spec=importlib.util.spec_from_file_location('private_review_test_subject',W/'standalone_opening_review.py');tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
@contextlib.contextmanager
def changed(path,payload,label):
 original=path.read_bytes();(E/'retained'/(label+'.bin')).write_bytes(payload)
 try:path.write_bytes(payload);yield
 finally:path.write_bytes(original)
class PrivateReviewAdmission(unittest.TestCase):
 def test_readiness_never_starts_process_and_is_relocatable(self):
  out=io.StringIO()
  with patch('subprocess.Popen',side_effect=AssertionError('Unexpected launch'))as start,contextlib.redirect_stdout(out):self.assertEqual(tool.main([],package_root=ROOT),0)
  row=json.loads(out.getvalue());self.assertEqual(row['status'],'ready_not_run');self.assertFalse(row['window_started']);self.assertFalse(row['human_pacing_accepted']);self.assertFalse(row['likeness_approved']);self.assertTrue(Path(row['player']).is_relative_to(ROOT));start.assert_not_called()
 def test_models_bind_distinct_adam_and_same_scenery(self):
  a=tool.inspect_package(ROOT,'draft31')[2];b=tool.inspect_package(ROOT,'previous20')[2]
  ar={r.role:r.reference for r in a.roles};br={r.role:r.reference for r in b.roles}
  self.assertNotEqual(ar['adam'],br['adam']);self.assertEqual({k:v for k,v in ar.items()if k!='adam'},{k:v for k,v in br.items()if k!='adam'})
 def test_corrupt_player_rejected_before_launch(self):
  p=ROOT/'runtime/bin/aibs_motherboard.exe';data=p.read_bytes();mutated=bytes([data[0]^1])+data[1:]
  with changed(p,mutated,'corrupt-player'),self.assertRaises(ValueError),patch('subprocess.Popen',side_effect=AssertionError('Unexpected launch')):tool.inspect_package(ROOT)
 def test_corrupt_helper_rejected_before_import(self):
  p=ROOT/'opening_assets.py'
  with changed(p,p.read_bytes()+b'\nraise RuntimeError("Unexpected import")\n','corrupt-helper'),self.assertRaises(ValueError):tool.inspect_package(ROOT)
 def test_unknown_profile_rejected(self):
  with self.assertRaises(ValueError):tool.inspect_package(ROOT,'../../real-save')
 def test_missing_helper_rejected_and_retained(self):
  p=ROOT/'opening_assets.py';dest=E/'retained/missing-opening-assets.py';self.assertTrue(p.resolve().is_relative_to(E.resolve()));p.rename(dest)
  try:
   with self.assertRaises((ValueError,OSError)):tool.inspect_package(ROOT)
  finally:dest.rename(p)
 def test_duplicate_metadata_key_rejected(self):
  p=ROOT/'package.json';data=p.read_text();bad=data.replace('"schema_version": 1,','"schema_version": 1, "schema_version": 1,',1).encode()
  with changed(p,bad,'duplicate-json'),self.assertRaises(ValueError):tool.inspect_package(ROOT)
 def test_wrong_sdk_and_incomplete_inventory_rejected(self):
  p=ROOT/'package.json';original=json.loads(p.read_text())
  for case in ['wrong_sdk','missing_runtime','boolean_size']:
   d=json.loads(json.dumps(original))
   if case=='wrong_sdk':d['sdk_version']='0.17.1'
   elif case=='missing_runtime':del d['files']['runtime/bin/aibs_motherboard.exe']
   else:d['files']['runtime/bin/aibs_motherboard.exe']['bytes']=True
   with self.subTest(case=case),changed(p,json.dumps(d).encode(),case),self.assertRaises(ValueError):tool.inspect_package(ROOT)
 def test_extra_pack_file_is_rejected(self):
  p=ROOT/'profiles/draft31/packs/adam/extra.txt';p.write_text('Owned invalid fixture')
  try:
   with self.assertRaises(ValueError):tool.inspect_package(ROOT)
  finally:p.rename(E/'retained/extra-pack-file.txt')
 def test_inner_payload_identity_rejected_even_if_outer_size_hash_updated(self):
  meta=ROOT/'package.json';d=json.loads(meta.read_text());p=next((ROOT/'profiles/draft31/packs/adam').glob('*.aibchar'));data=p.read_bytes();bad=bytes([data[0]^1])+data[1:];row=d['files'][p.relative_to(ROOT).as_posix()];row['sha256']=hashlib.sha256(bad).hexdigest()
  with changed(p,bad,'corrupt-typed-payload'),changed(meta,json.dumps(d).encode(),'updated-outer-hash'),self.assertRaises(ValueError):tool.inspect_package(ROOT)
 def test_review_command_requests_real_gameplay_without_tour_or_recording(self):
  driver=tool.load_module(ROOT/'review_driver.py','_fixture_driver_');args=driver.command(ROOT/'runtime/bin/aibs_motherboard.exe',ROOT/'sessions/fake/chapter',ROOT/'sessions/fake','invocation','timeline')
  self.assertIn('--persistent-play',args);self.assertIn('--performance-gameplay',args);self.assertEqual(args[args.index('--performance-seconds')+1],'900');self.assertFalse(any(a.startswith('--record')or a.startswith('--walkthrough')for a in args))
 def test_run_requires_interactive_console_and_creates_only_package_local_attempt(self):
  with patch('subprocess.Popen',side_effect=AssertionError('Unexpected launch'))as start,patch('sys.stdin.isatty',return_value=False),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(tool.main(['--run'],package_root=ROOT),1)
  start.assert_not_called();attempts=list((ROOT/'launches/draft31').glob('*/launch.json'));self.assertEqual(len(attempts),1);self.assertEqual(json.loads(attempts[0].read_text())['status'],'failed');self.assertFalse((ROOT/'sessions').exists())
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='Verify a project-owned private review package without launching gameplay; retain all diagnostic fixtures.')
 parser.add_argument('--package',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args();configure(args.package,args.evidence)
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(PrivateReviewAdmission);result=unittest.TextTestRunner(verbosity=2).run(suite)
 row={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses)};row['passed']=result.testsRun>0 and result.wasSuccessful()and not any(row[k]for k in ['failures','errors','skipped','expected_failures','unexpected_successes']);(E/'verification.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));raise SystemExit(0 if row['passed']else 1)
