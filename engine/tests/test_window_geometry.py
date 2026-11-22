"""Startup fitting must respect actual work areas without starting Studio."""
import unittest
from native_studio.window_geometry import fit_startup_geometry


class StartupGeometryTests(unittest.TestCase):
    def test_large_screen_preserves_existing_preferred_size(self):
        fitted=fit_startup_geometry((0,0,2560,1400))
        self.assertEqual((fitted.width,fitted.height),(1620,980))
        self.assertEqual((fitted.minimum_width,fitted.minimum_height),(1150,750))

    def test_small_display_does_not_force_old_minimum_offscreen(self):
        fitted=fit_startup_geometry((0,0,1280,680))
        self.assertEqual((fitted.width,fitted.height),(1264,640))
        self.assertLessEqual(fitted.minimum_height,fitted.height)
        self.assertLessEqual(fitted.y+fitted.height+40,680)

    def test_negative_secondary_screen_origin_and_reserved_taskbar(self):
        fitted=fit_startup_geometry((-1280,48,1280,672),frame=(12,36))
        self.assertGreaterEqual(fitted.x,-1280)
        self.assertGreaterEqual(fitted.y,48)
        self.assertLessEqual(fitted.x+fitted.width+12,0)
        self.assertLessEqual(fitted.y+fitted.height+36,720)

    def test_medium_display_reduces_only_required_dimension(self):
        fitted=fit_startup_geometry((10,20,1920,900))
        self.assertEqual(fitted.width,1620)
        self.assertEqual(fitted.height,860)

    def test_invalid_geometry_is_rejected(self):
        for available in ((0,0,0,720),(0,0,1280,-1),(0,0,True,720)):
            with self.subTest(available=available),self.assertRaises(ValueError):
                fit_startup_geometry(available)


if __name__=='__main__':unittest.main()
