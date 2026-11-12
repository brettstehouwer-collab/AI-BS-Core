import os
import sys
from pathlib import Path
import unittest
import subprocess
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from security.native_creative_channel import CreativePipes


@unittest.skipUnless(os.name == 'nt', 'Windows inherited handles')
class PipeResourcesTests(unittest.TestCase):
    def test_real_child_explicit_handle_list_roundtrip_and_exit(self):
        import msvcrt
        import ctypes
        import time
        from ctypes import wintypes
        from native_studio.creative_wire import encode, read_message
        child_code = '''import os,sys,msvcrt,struct,json
r=msvcrt.open_osfhandle(int(sys.argv[1]),os.O_RDONLY|os.O_BINARY)
w=msvcrt.open_osfhandle(int(sys.argv[2]),os.O_WRONLY|os.O_BINARY)
def exact(n):
 b=b''
 while len(b)<n:
  p=os.read(r,n-len(b))
  if not p:raise RuntimeError('EOF')
  b+=p
 return b
n=struct.unpack('!I',exact(4))[0]
if not 1<=n<=1024:raise RuntimeError('Bound')
v=json.loads(exact(n));v['child']=True
b=json.dumps(v).encode();os.write(w,struct.pack('!I',len(b))+b)
os.close(r);os.close(w)
'''
        with CreativePipes() as pipes:
            handles = pipes.child_handles
            startup = subprocess.STARTUPINFO()
            startup.lpAttributeList = {'handle_list': list(handles)}
            process = subprocess.Popen([sys._base_executable, '-I', '-B', '-c', child_code,
                *map(str, handles)], close_fds=True, startupinfo=startup,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                pipes.child_started()
                read, write = pipes.parent_fds
                os.write(write, encode({'message': 'synthetic é'}))
                api=ctypes.WinDLL('kernel32',use_last_error=True)
                api.PeekNamedPipe.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,
                    ctypes.c_void_p,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
                deadline=time.monotonic()+5
                def bounded_read(length):
                    while time.monotonic()<deadline:
                        available=wintypes.DWORD()
                        if not api.PeekNamedPipe(msvcrt.get_osfhandle(read),None,0,None,
                                                ctypes.byref(available),None):
                            raise OSError('Pipe unavailable')
                        if available.value:return os.read(read,min(length,available.value))
                        time.sleep(.005)
                    raise TimeoutError('Child response deadline')
                self.assertEqual(read_message(bounded_read), {'message':'synthetic é','child':True})
                self.assertEqual(process.wait(timeout=5),0)
            finally:
                if process.poll() is None:
                    process.kill();process.wait(timeout=5)

    def test_only_child_ends_inheritable_and_two_directions_work(self):
        import msvcrt
        with CreativePipes() as pipes:
            read, write = pipes.parent_fds
            self.assertFalse(os.get_handle_inheritable(msvcrt.get_osfhandle(read)))
            self.assertFalse(os.get_handle_inheritable(msvcrt.get_osfhandle(write)))
            self.assertTrue(all(os.get_handle_inheritable(h) for h in pipes.child_handles))
            os.write(write, b'out')
            self.assertEqual(os.read(pipes._child_read, 3), b'out')
            os.write(pipes._child_write, b'in')
            self.assertEqual(os.read(read, 2), b'in')

    def test_launch_transition_closes_child_aliases_and_cleanup_is_idempotent(self):
        pipes = CreativePipes()
        pipes.child_started(); pipes.child_started()
        with self.assertRaises(OSError): _ = pipes.child_handles
        self.assertEqual(len(pipes._fds), 2)
        pipes.close(); pipes.close()
        self.assertEqual(pipes._fds, set())
        with self.assertRaises(OSError): _ = pipes.parent_fds
