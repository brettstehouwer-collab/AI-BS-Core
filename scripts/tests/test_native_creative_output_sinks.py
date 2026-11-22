"""Actual candidate CRT and Win32 output redirection; no GUI/server/secrets."""
import os,subprocess,sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

if __name__=='__main__' and sys.argv[-1:] == ['--sink-child']:
    import ctypes
    from ctypes import wintypes
    from native_studio.creative_session import silence_native_bootstrap_output
    print('before-sink',flush=True)
    silence_native_bootstrap_output()
    print('after-sink',flush=True);os.write(2,b'after-stderr')
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.GetStdHandle.argtypes=[wintypes.DWORD];api.GetStdHandle.restype=wintypes.HANDLE
    api.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    written=wintypes.DWORD();data=b'after-win32'
    if not api.WriteFile(api.GetStdHandle((-11)&0xffffffff),data,len(data),ctypes.byref(written),None):raise SystemExit(4)
    raise SystemExit(0)

@unittest.skipUnless(os.name=='nt','Windows output handles')
class OutputSinks(unittest.TestCase):
    def test_real_child_redirects_crt_and_win32_output(self):
        result=subprocess.run([sys.executable,'-B',__file__,'--sink-child'],capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout.strip(),b'before-sink')
        self.assertEqual(result.stderr,b'')

if __name__=='__main__':unittest.main()
