import unittest, runpy
class Check(unittest.TestCase):
 def test_value(self):
  self.assertEqual(runpy.run_path("src/app.py")["value"], 42)
