import unittest,time,subprocess,sys,pathlib
class Check(unittest.TestCase):
 def test_slow(self):
  child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])
  pathlib.Path("owned-child.pid").write_text(str(child.pid))
  time.sleep(8)
