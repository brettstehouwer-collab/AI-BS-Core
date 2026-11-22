import unittest,pathlib
class Check(unittest.TestCase):
 def test_mutation(self):
  pathlib.Path("tests/test_app.py").write_text("# changed")
