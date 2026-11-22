"""Current opening entry uses existing chapter tools without legacy launches."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PyQt6.QtCore import QCoreApplication,QEvent
from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
import native_studio.game_build_view as game

BUNDLE=Path('C:/AI-BS/native_studio/releases/v5.329.102/AI_BS_Studio/_internal')

class WarmOpeningEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.bus=EngineBus(max_threads=1)
        self.bundle=patch.object(game,'_bundle_root',return_value=BUNDLE);self.bundle.start()
        self.view=game.GameBuildNativeView(self.bus,root=Path(self.temp.name))
    def tearDown(self):
        self.view.close();self.bus.shutdown(3000);self.view.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.app.processEvents()
        self.bundle.stop();self.temp.cleanup()
    def test_current_opening_entry_opens_real_curated_chapter_workspace_without_launching_blockout(self):
        self.assertTrue(hasattr(self.view,'warm_opening_button'),'Current opening has no explicit player entry')
        self.assertTrue(self.view.warm_opening_button.isEnabled())
        self.assertIsNone(self.view.content_view)
        with patch.object(game.QProcess,'startDetached') as legacy:
            self.view.warm_opening_button.click()
            legacy.assert_not_called()
        self.assertEqual(self.view.workspace_tabs.currentIndex(),2)
        current=self.view.content_view
        self.assertIsNotNone(current)
        self.assertEqual(current.opening_create_button.text(),'Create First Boot opening')
        self.assertTrue(current.opening_create_button.isEnabled())
        self.assertEqual(current.saved_play_button.text(),'Play saved chapter')
        self.assertIsNone(current.definition)
        self.assertEqual(current.opening_client.state,'idle')
        self.assertEqual(current.client.state,'closed')
        self.assertIn('Play saved chapter',self.view.launch_status.text())
    def test_repeated_entry_preserves_existing_workspace_and_never_saves_or_replaces_a_project(self):
        self.assertTrue(hasattr(self.view,'warm_opening_button'),'Current opening entry missing')
        self.view.warm_opening_button.click();current=self.view.content_view
        current.status.setText('Existing user workspace remains here')
        with patch.object(current,'create_first_boot_opening') as create,patch.object(current,'open_project') as opened,patch.object(current,'save_world') as saved,patch.object(current,'start_saved_play') as play:
            self.view.workspace_tabs.setCurrentIndex(0);self.view.warm_opening_button.click()
            self.assertIs(self.view.content_view,current)
            self.assertEqual(current.status.text(),'Existing user workspace remains here')
            for callback in (create,opened,saved,play):callback.assert_not_called()
    def test_legacy_entry_is_explicitly_labelled_and_its_launch_contract_is_retained(self):
        self.assertIn('legacy blockout',self.view.chapter_button.text())
        with patch.object(game.QProcess,'startDetached',return_value=(True,123)) as launch:
            self.view.chapter_button.click()
            self.assertEqual(launch.call_args.args[1],['--durable-world','--chapter'])
    def test_missing_curated_resources_disables_current_entry_without_starting_anything(self):
        self.assertTrue(hasattr(self.view,'warm_opening_button'),'Current opening entry missing')
        with patch.object(game,'_opening_workspace_paths',return_value=(None,None)),patch.object(game.QProcess,'startDetached') as launch:
            self.view._update_launch_targets()
            self.assertFalse(self.view.warm_opening_button.isEnabled())
            self.view.warm_opening_button.click();launch.assert_not_called()
            self.assertIsNone(self.view.content_view)
    def test_workspace_failure_is_reported_without_crossing_a_Qt_callback_exception_boundary(self):
        self.assertTrue(hasattr(self.view,'warm_opening_button'),'Current opening entry missing')
        with patch.object(self.view,'_workspace_changed',side_effect=ValueError('synthetic unavailable workspace')):
            self.view.warm_opening_button.click()
        self.assertIn('Could not open Warm Beginning',self.view.launch_status.text())
        self.assertIsNone(self.view.content_view)

if __name__=='__main__':unittest.main(verbosity=2)
