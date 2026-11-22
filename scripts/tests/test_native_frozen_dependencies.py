"""Verify imports from the bundled pywin32 layout without host search paths."""
import importlib.machinery
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
from native_studio import runtime_policy as policy


class FrozenDependencyTests(unittest.TestCase):
    def test_actual_subdirectory_layout_becomes_resolvable_without_host_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'_internal';child=root/'win32';child.mkdir(parents=True)
            (child/'win32cred.py').write_text('fixture=True',encoding='utf-8')
            paths=[str(root)]
            self.assertIsNone(importlib.machinery.PathFinder.find_spec('win32cred',paths))
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS',str(root),create=True),patch.object(sys,'path',paths):
                policy.configure_frozen_dependencies()
                found=importlib.machinery.PathFinder.find_spec('win32cred',sys.path)
                self.assertIsNotNone(found)
                self.assertEqual(Path(found.origin).parent,child)
                self.assertEqual(sys.path,[str(root),str(child)])
                policy.configure_frozen_dependencies()
                self.assertEqual(len(sys.path),2)

    def test_source_execution_does_not_add_dependency_paths(self):
        with patch.object(sys,'frozen',False,create=True),patch.object(sys,'path',['fixture']):
            policy.configure_frozen_dependencies()
            self.assertEqual(sys.path,['fixture'])

    def test_redirected_frozen_dependency_is_refused_before_path_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'_internal';outside=Path(temp)/'outside';root.mkdir();outside.mkdir()
            child=root/'win32';child.mkdir()
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS',str(root),create=True),patch.object(sys,'path',[str(root)]),patch.object(Path,'is_junction',lambda p:p==child):
                with self.assertRaises(RuntimeError):policy.configure_frozen_dependencies()
                self.assertEqual(sys.path,[str(root)])


if __name__=='__main__':unittest.main()
