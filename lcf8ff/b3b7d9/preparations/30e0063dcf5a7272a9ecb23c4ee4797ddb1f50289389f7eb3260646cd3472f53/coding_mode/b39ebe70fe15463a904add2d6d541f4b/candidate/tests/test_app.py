import unittest,time
class Check(unittest.TestCase):
 def test_slow(self):
  time.sleep(8)
