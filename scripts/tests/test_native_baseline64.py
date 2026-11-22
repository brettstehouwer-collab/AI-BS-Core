"""Actual retained LIVE admission; no application import or execution."""
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('native64_admission_builder',ROOT/'scripts/build_native_web_parity.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
class Live64AdmissionTests(unittest.TestCase):
 def test_actual_live64_bytes_are_admitted_with_complete_readback(self):
  cp=Path((ROOT/'scratch/current_native_cockpit_checkpoint.txt').read_text().strip())
  manifest=cp/'admitted_web64/hosting_artifact_manifest_final.json'
  web,proof_sha=builder.admit_web_baseline(manifest)
  self.assertEqual(web['buildId'],'web-v5-329-64-ea4a05ea2d5a');self.assertEqual(web['count'],189)
  self.assertEqual(proof_sha,'be8dccd4916c95bb8d8736630be6405ae21b80ea79be0b002419dd1f2d086e5a')
if __name__=='__main__':unittest.main()
