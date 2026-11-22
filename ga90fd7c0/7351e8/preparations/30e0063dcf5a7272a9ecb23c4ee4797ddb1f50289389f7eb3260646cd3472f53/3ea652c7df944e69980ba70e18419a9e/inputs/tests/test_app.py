import unittest
class Check(unittest.TestCase):
 def test_failure(self):
  self.fail("synthetic failure")
