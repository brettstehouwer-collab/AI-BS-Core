"""Actual Windows job lifetime with private inherited creative pipe resources."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from security.native_creative_channel import CreativePipes
from security.native_creative_lifetime import NativeCreativeLifetime


@unittest.skipUnless(os.name == 'nt', 'Windows job handles')
class CreativePipeLifetimeTests(unittest.TestCase):
    def test_acknowledged_child_survives_release_of_backend_handles(self):
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        revoked = []
        with CreativePipes() as pipes:
            life = NativeCreativeLifetime([sys._base_executable, '-I', '-B', '-c',
                'import time;time.sleep(60)'], str(Path(__file__).resolve().parents[2]),
                {'SYSTEMROOT': os.environ['SYSTEMROOT']}, candidate_sha256='a'*64,
                revoke_invocation=revoked.append, pipes=pipes)
            retained = None
            try:
                retained = api.OpenProcess(0x100001, False, life.process.pid)
                self.assertTrue(retained)
                self.assertTrue(life.invocation.alive())
                life.acknowledge_handoff(life.invocation)
                result = life.close()
                self.assertTrue(result.acknowledged)
                self.assertFalse(result.termination_requested)
                self.assertIsNone(result.job_drained)
                self.assertEqual(api.WaitForSingleObject(retained, 0), 258)
                self.assertIsNone(life.process.hp)
                self.assertIsNone(life.process.job)
                self.assertTrue(revoked)
            finally:
                # Exact retained test-child handle only; never process discovery.
                if retained:
                    if api.WaitForSingleObject(retained, 0) == 258:
                        self.assertTrue(api.TerminateProcess(retained, 99))
                    self.assertEqual(api.WaitForSingleObject(retained, 5000), 0)
                    api.CloseHandle(retained)
                life.close()
