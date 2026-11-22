import hashlib,importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('resource_cache',Path(__file__).resolve().parents[1]/'tools/resource_cache.py')
cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
class CacheTests(unittest.TestCase):
 def test_verify_before_publication_and_reuse(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'download';source.write_bytes(b'original resource');sha=hashlib.sha256(source.read_bytes()).hexdigest()
   target=cache.admit(source,root,17,sha);self.assertEqual(target.read_bytes(),source.read_bytes());self.assertEqual(cache.admit(source,root,17,sha),target)
 def test_corrupt_download_cannot_publish(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'download';source.write_bytes(b'wrong')
   with self.assertRaises(ValueError):cache.admit(source,root,5,'a'*64)
   self.assertEqual(list(root.iterdir()),[source])
if __name__=='__main__':unittest.main()
