"""Real private recovery-file preservation after synthetic backend loss."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import httpx
from unittest.mock import patch
from native_studio.screenplay_client import DraftSession,ScreenplayClient,ScreenplayError

@unittest.skipUnless(os.name=='nt','Windows private recovery permissions')
class DisconnectRecovery(unittest.TestCase):
    @staticmethod
    def dacl_bytes(path):
        import ctypes
        from ctypes import wintypes
        api=ctypes.WinDLL('advapi32',use_last_error=True)
        api.GetFileSecurityW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
        size=wintypes.DWORD()
        api.GetFileSecurityW(str(path),4,None,0,ctypes.byref(size))
        buffer=ctypes.create_string_buffer(size.value)
        if not api.GetFileSecurityW(str(path),4,buffer,size.value,ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.raw

    def test_existing_inherited_permissions_are_not_accepted_or_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory)/'inherited-profile';profile.mkdir()
            marker=profile/'retained.txt';marker.write_bytes(b'synthetic retained bytes')
            draft=DraftSession(profile)
            draft.load(dict(project='Synthetic',revision='r',content='Fixture'))
            before=self.dacl_bytes(profile)
            with self.assertRaises(ScreenplayError):draft.preserve()
            self.assertEqual(self.dacl_bytes(profile),before)
            self.assertEqual(marker.read_bytes(),b'synthetic retained bytes')
            self.assertEqual(list(profile.iterdir()),[marker])

    def test_backend_loss_retains_complete_draft_and_previous_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            draft=DraftSession(Path(directory)/'private-profile')
            draft.load(dict(project='Synthetic',revision='original-r',content='Original fixture'))
            draft.content='Unsaved fixture — full text\nSecond line'
            first=draft.preserve();before=first.read_bytes()
            def offline(request):raise httpx.ConnectError('synthetic disconnect',request=request)
            client=ScreenplayClient(transport=httpx.MockTransport(offline))
            with patch('native_studio.screenplay_client.local_service_headers',return_value={'X-API-Key':'synthetic'}):
                with self.assertRaises(ScreenplayError):client.save(draft.project,draft.content,draft.revision)
            self.assertTrue(draft.dirty)
            self.assertEqual(first.read_bytes(),before)
            self.assertEqual(json.loads(before)['content'],draft.content)
            draft.content+='\nContinued offline'
            second=draft.preserve()
            self.assertNotEqual(first,second)
            self.assertEqual(first.read_bytes(),before)
            self.assertEqual(json.loads(second.read_bytes())['content'],draft.content)

if __name__=='__main__':unittest.main()
