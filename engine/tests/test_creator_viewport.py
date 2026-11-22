import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile,time,unittest,uuid,ctypes
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.creator_payload import Scope,Create
from native_studio.game_engine.creator_viewport import encode_snapshot,ViewportClient
from native_studio.game_engine.creator_viewport import _replace_snapshot

ROOT=Path(__file__).resolve().parents[2]
EXE=ROOT/'engine/out/windows-msvc/Debug/aibs_creator_viewport.exe'
SCOPE=Scope('BS workshop','main',str(uuid.uuid4()),str(uuid.uuid4()))
NODE=Create('relay','Relay',str(uuid.uuid4()),tuple((k,1. if k.startswith('half_') else 0.) for k in ('half_x','half_y','half_z','x','y','z')))

class ViewportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def spin(self,predicate):
        end=time.monotonic()+8
        while not predicate() and time.monotonic()<end:self.app.processEvents();time.sleep(.003)
        self.assertTrue(predicate())
    @unittest.skipUnless(os.name=='nt','Windows shared-delete publication contract')
    def test_atomic_replace_while_native_shared_read_handle_is_open(self):
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,
                                    wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
        kernel.CreateFileW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=(wintypes.HANDLE,);kernel.CloseHandle.restype=wintypes.BOOL
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'scene.aibv';temporary=root/'scene.tmp'
            target.write_bytes(b'previous snapshot');temporary.write_bytes(b'new complete snapshot')
            stamp=time.time_ns()-5_000_000_000;os.utime(temporary,ns=(stamp,stamp));expected=temporary.stat().st_mtime_ns
            handle=kernel.CreateFileW(str(target),0x80000000,1|4,None,3,0x80,None)
            self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
            try:
                _replace_snapshot(temporary,target)
                self.assertEqual(target.read_bytes(),b'new complete snapshot')
                self.assertEqual(target.stat().st_mtime_ns,expected)
                self.assertFalse(temporary.exists())
            finally:kernel.CloseHandle(handle)
    def test_snapshot_bounds_and_identity(self):
        data=encode_snapshot(str(uuid.uuid4()),SCOPE,2,'',(NODE,))
        self.assertTrue(data.startswith(b'AIBV\x01\x00'))
        with self.assertRaises(ValueError):encode_snapshot(str(uuid.uuid4()),SCOPE,2,'',(NODE,NODE))
        with self.assertRaises(ValueError):encode_snapshot(str(uuid.uuid4()),SCOPE,-1,'',(NODE,))
    def test_real_native_gpu_pick_and_process_join(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);client=ViewportClient();picked=[];client.selection.connect(lambda uid,scope:picked.append((uid,scope)))
            try:
                client.start(EXE,SCOPE,2,'',(NODE,),probe_directory=root)
                self.spin(lambda:client.state=='closed')
                self.assertEqual(picked,[(NODE.uuid,SCOPE)])
                import json
                proof=json.loads((root/'viewport.json').read_text())
                self.assertGreater(proof['nonbackground_pixels'],100)
                self.assertEqual(proof['debug_errors'],0)
                self.assertTrue((root/'viewport.bmp').is_file())
                self.assertNotEqual((root/'viewport.bmp').read_bytes(),(root/'viewport.bmp.unselected.bmp').read_bytes())
            finally:
                client.stop();self.spin(lambda:client.state=='closed')
    def test_late_pick_does_not_rebind_after_publish(self):
        client=ViewportClient();events=[];client.selection.connect(lambda uid,scope:events.append(uid))
        client._tag=(str(uuid.uuid4()),SCOPE,3,'')
        client._ids={NODE.uuid}
        old=str(uuid.uuid4())
        client._line(f'AIBV1 PICK {old} {SCOPE.world_id} 2 {NODE.uuid}'.encode())
        self.assertEqual(events,[])

if __name__=='__main__':unittest.main()
