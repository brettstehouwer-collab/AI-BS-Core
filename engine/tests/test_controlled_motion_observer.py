"""Owned Win32 metadata contract checks; no input or activation is performed."""
import ctypes
from ctypes import wintypes
import importlib.util
import os
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('controlled_gui_observer', Path(__file__).parents[1]/'tools/controlled_motion_observer.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class FakeAPI:
    def __init__(self, flags=0, error=0):
        self.flags, self.error = flags, error
        self.queries = []
    def owner(self, hwnd):
        return (321, 123) if hwnd in (100,101) else (555,999)
    def query_gui(self, thread, info):
        self.queries.append((thread, info.cbSize))
        info.flags = self.flags
        info.hwndMoveSize = 100
        info.hwndMenuOwner = 101
        return not self.error, self.error
    def foreground(self):
        return 100


class ObserverContracts(unittest.TestCase):
    def test_explicit_owned_thread_and_cbsize(self):
        api = FakeAPI(observer.GUI_INMOVESIZE)
        result = observer.sample_owned_gui(100,123,api)
        self.assertEqual(api.queries, [(321,ctypes.sizeof(observer.GUITHREADINFO))])
        self.assertTrue(result['success'] and result['modal'] and result['moving_or_sizing'])
        self.assertTrue(result['move_size_window_is_game'] and result['menu_window_owned_by_game'])
        self.assertEqual(result['foreground_pid'], 123)

    def test_each_modal_bit_and_caret_nonmodal(self):
        for flag in (2,4,8,16):
            with self.subTest(flag=flag):
                self.assertTrue(observer.sample_owned_gui(100,123,FakeAPI(flag))['modal'])
        for flag in (0,1):
            with self.subTest(flag=flag):
                self.assertFalse(observer.sample_owned_gui(100,123,FakeAPI(flag))['modal'])

    def test_failure_is_unknown_not_false_or_foreground_query(self):
        result = observer.sample_owned_gui(100,123,FakeAPI(error=5))
        self.assertFalse(result['success'])
        self.assertIsNone(result['modal'])
        self.assertIsNone(result['flags'])
        self.assertEqual(result['error'], 'GetGUIThreadInfo:5')
        api = FakeAPI()
        self.assertIsNone(observer.sample_owned_gui(100,999,api)['modal'])
        self.assertIsNone(observer.sample_owned_gui(0,123,api)['modal'])
        self.assertEqual(api.queries, [])

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows hidden HWND contract')
    def test_real_hidden_owned_window_metadata_never_changes_foreground(self):
        api = observer.Win32API()
        user32 = api.user32
        user32.CreateWindowExW.argtypes = [wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,
                    ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,wintypes.LPVOID]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.DestroyWindow.argtypes = [wintypes.HWND]
        user32.DestroyWindow.restype = wintypes.BOOL
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        foreground = api.foreground()
        hwnd = user32.CreateWindowExW(0,'STATIC','Owned observer metadata test',0,0,0,16,16,None,None,None,None)
        self.assertTrue(hwnd)
        try:
            self.assertFalse(user32.IsWindowVisible(hwnd))
            result = observer.sample_owned_gui(int(hwnd),os.getpid(),api)
            self.assertTrue(result['success'], result)
            self.assertEqual(result['gui_thread_id'], api.owner(hwnd)[0])
            self.assertFalse(result['modal'])
            self.assertEqual(api.foreground(),foreground)
        finally:
            user32.DestroyWindow(hwnd)


if __name__ == '__main__':
    unittest.main()
