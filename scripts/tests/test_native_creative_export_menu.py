"""Actual Qt export menu selection on the existing scoped writer fixture."""
from pathlib import Path
from unittest.mock import patch
import unittest
from scripts.tests import test_native_creative_scoped_view as fixture


class NativeExportMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.ScopedWriterQtTests.setUpClass()
    @classmethod
    def tearDownClass(cls):fixture.ScopedWriterQtTests.tearDownClass()
    def setUp(self):
        self.base=fixture.ScopedWriterQtTests();self.base.setUp();self.addCleanup(self.base.doCleanups)

    def test_reformatted_profile_actions_are_visible_and_reach_same_project(self):
        view=self.base._view()
        for fmt,button in (('fdx',view.btn_export_fdx),('pdf',view.btn_export_pdf)):
            action=next(a for a in button.menu().actions() if 'Reformatted' in a.text())
            self.assertTrue(action.isVisible());self.assertTrue(action.isEnabled())
            target=Path(self.base.temp.name)/('edited.'+fmt)
            with patch.object(fixture.writer.QFileDialog,'getSaveFileName',return_value=(str(target),'')):
                action.trigger()
            self.base.bus.drain()
            self.assertTrue(target.is_file())
            calls=[c for c in self.base.fixture.calls if c[1]=='/api/screenwriting/export/'+fmt]
            self.assertEqual(calls[-1][2]['layout'],'reflow')
            self.assertEqual(calls[-1][2]['project_name'],'Bound')

    def test_default_export_does_not_silently_choose_reformatted_profile(self):
        view=self.base._view();target=Path(self.base.temp.name)/'default.fdx'
        with patch.object(fixture.writer.QFileDialog,'getSaveFileName',return_value=(str(target),'')):
            view.btn_export_fdx.menu().actions()[0].trigger()
        self.base.bus.drain()
        call=next(c for c in self.base.fixture.calls if c[1]=='/api/screenwriting/export/fdx')
        self.assertNotIn('layout',call[2])

if __name__=='__main__':unittest.main()
