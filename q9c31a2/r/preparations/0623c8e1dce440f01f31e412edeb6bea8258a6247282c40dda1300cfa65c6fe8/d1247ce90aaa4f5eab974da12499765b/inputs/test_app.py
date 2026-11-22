import unittest
from app import value

class ValueTests(unittest.TestCase):
    def test_value(self):
        self.assertEqual(value, 42)
