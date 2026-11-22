"""Real Windows ACL APIs in isolated C fixtures; never real broadcast IPC."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid


ROOT=Path(__file__).resolve().parents[2]


class BroadcastIpcAtomic207Tests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('_audit_ipc_atomic207',ROOT/'native_studio/broadcast_ipc.py')
        self.ipc=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.ipc)
        container=ROOT/'backups/native_broadcast207_work/atomic_fixtures'/uuid.uuid4().hex
        container.mkdir(parents=True)
        private=container/'AI-BS/BroadcastIPC'
        self.paths={'status':private/'broadcast_secondary_status.json',
                    'command':private/'broadcast_secondary_command.json','stop':private/'broadcast_secondary.stop'}
        self.path_patch=patch.object(self.ipc,'ipc_paths',return_value=self.paths)
        self.path_patch.start();self.addCleanup(self.path_patch.stop)
        self.ipc.write_private_json(self.paths['command'],{'fixture':'original synthetic intent','version':2})

    def assert_write_failure_preserves_previous(self,result):
        import win32file
        target=self.paths['command'];before=target.read_bytes();failure=None
        with patch.object(win32file,'WriteFile',return_value=result), \
             patch.object(self.ipc.os,'replace',wraps=self.ipc.os.replace) as replace:
            try:self.ipc.write_private_json(target,{'fixture':'replacement synthetic intent','version':2})
            except ValueError as error:failure=error
        self.assertEqual(target.read_bytes(),before,'Incomplete write destroyed the previous IPC command')
        replace.assert_not_called()
        self.assertIsNotNone(failure,'Incomplete Win32 write must refuse publication')
        self.assertEqual(str(failure),'IPC_WRITE_INCOMPLETE')
        self.assertEqual(list(target.parent.glob('.broadcast-*.tmp')),[])

    def test_short_win32_write_keeps_previous_command_and_cleans_owned_temporary(self):
        self.assert_write_failure_preserves_previous((0,1))

    def test_nonzero_win32_error_keeps_previous_command_and_cleans_owned_temporary(self):
        self.assert_write_failure_preserves_previous((5,0))


if __name__=='__main__':unittest.main()
