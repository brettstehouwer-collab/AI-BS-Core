import unittest
from native_app import clamp

class ClampTests(unittest.TestCase):
    def test_cases(self):
        for args, expected in [((-2,0,10),0),((12,0,10),10),((5,0,10),5),((0,0,10),0),((10,0,10),10),((-5,-4,-1),-4)]:
            with self.subTest(args=args): self.assertEqual(clamp(*args),expected)
