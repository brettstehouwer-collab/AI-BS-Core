"""Owned viewport cleanup must finish with deeply nested asset filenames."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtCore import QCoreApplication,QProcess
from native_studio.game_engine.creator_viewport import new_viewport_workspace,ViewportClient


@unittest.skipUnless(os.name=='nt','Windows extended path regression')
class ViewportWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QCoreApplication.instance() or QCoreApplication([])

    def stage(self,parent):
        with patch('native_studio.game_engine.creator_viewport.tempfile.gettempdir',return_value=str(parent)):
            directory=new_viewport_workspace()
        root=Path(directory.name)
        expected=Path('\\\\?\\'+str(parent.resolve()))
        self.assertEqual(root.parent.resolve(),expected.resolve())
        self.assertTrue(root.name.startswith('aibs-viewport-'))
        self.assertFalse(root.is_symlink())
        payload=root/'assets'/'packs'/('a'*64)/('b'*64)/('c'*64+'.aibsurf')
        payload.parent.mkdir(parents=True)
        payload.write_bytes(b'owned staged texture')
        self.assertGreater(len(str(payload).removeprefix('\\\\?\\')),260)
        self.assertEqual(payload.read_bytes(),b'owned staged texture')
        return directory,root

    def test_stdlib_cleanup_removes_long_asset_tree(self):
        with tempfile.TemporaryDirectory(prefix='viewport-regression-')as parent:
            directory,root=self.stage(Path(parent))
            directory.cleanup()
            self.assertFalse(root.exists())
            self.assertFalse(Path(str(root).removeprefix('\\\\?\\')).exists())

    def test_finished_callback_removes_tree_and_emits_closed(self):
        with tempfile.TemporaryDirectory(prefix='viewport-finished-')as parent:
            directory,root=self.stage(Path(parent))
            client=ViewportClient();process=QProcess(client);events=[]
            client._process=process;client._directory=directory;client.state='running'
            client.closed.connect(lambda:events.append('closed'))
            client._finished(process)
            self.assertEqual(events,['closed'])
            self.assertEqual(client.state,'closed')
            self.assertIsNone(client._directory)
            self.assertIsNone(client._process)
            self.assertFalse(root.exists())


if __name__=='__main__':unittest.main()
