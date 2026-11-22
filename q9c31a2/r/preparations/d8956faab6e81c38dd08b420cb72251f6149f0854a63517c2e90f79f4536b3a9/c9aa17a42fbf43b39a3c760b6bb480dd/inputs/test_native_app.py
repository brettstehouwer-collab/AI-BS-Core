import unittest
from native_app import value

class NativeValueTests(unittest.TestCase):
    def test_value(self):
        self.assertEqual(value, 42)
