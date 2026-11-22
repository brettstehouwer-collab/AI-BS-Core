"""Read-only owned game GUI-thread metadata for an external ~1Hz observer.

No focus, input, hooks, window text, cross-thread attachment or memory reads.
A negative periodic observation cannot exclude an intervening modal loop.
"""
import ctypes
from ctypes import wintypes
import os
import time

GUI_CARETBLINKING = 0x1
GUI_INMOVESIZE = 0x2
GUI_INMENUMODE = 0x4
GUI_SYSTEMMENUMODE = 0x8
GUI_POPUPMENUMODE = 0x10
MODAL_MASK = GUI_INMOVESIZE | GUI_INMENUMODE | GUI_SYSTEMMENUMODE | GUI_POPUPMENUMODE


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('flags', wintypes.DWORD),
                ('hwndActive', wintypes.HWND), ('hwndFocus', wintypes.HWND),
                ('hwndCapture', wintypes.HWND), ('hwndMenuOwner', wintypes.HWND),
                ('hwndMoveSize', wintypes.HWND), ('hwndCaret', wintypes.HWND),
                ('rcCaret', wintypes.RECT)]


class Win32API:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('Owned GUI diagnostics require Windows')
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
        self.user32.GetGUIThreadInfo.restype = wintypes.BOOL
        self.user32.GetForegroundWindow.argtypes = []
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClassNameW.restype = ctypes.c_int

    def owner(self, hwnd):
        pid = wintypes.DWORD()
        thread = self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(thread), int(pid.value)

    def query_gui(self, thread_id, info):
        ctypes.set_last_error(0)
        ok = bool(self.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)))
        return ok, 0 if ok else ctypes.get_last_error()

    def foreground(self):
        return int(self.user32.GetForegroundWindow() or 0)

    def find_game_window(self, expected_pid):
        found = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def visit(hwnd, _):
            _, pid = self.owner(hwnd)
            if pid == expected_pid:
                name = ctypes.create_unicode_buffer(128)
                if self.user32.GetClassNameW(hwnd, name, len(name)) and name.value == 'AIBS.NativeGameWindow.1':
                    found.append(int(hwnd))
            return True
        callback = callback_type(visit)
        self.user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        self.user32.EnumWindows.restype = wintypes.BOOL
        if not self.user32.EnumWindows(callback, 0):
            return 0
        return found[0] if len(found) == 1 else 0


def sample_owned_gui(hwnd, expected_pid, api=None):
    """Caller pins the process identity; this checks HWND ownership every time."""
    result = dict(monotonic_ns=time.monotonic_ns(), success=False, modal=None,
                  flags=None, error=None, game_pid=expected_pid, gui_thread_id=None)
    if not hwnd or type(expected_pid) is not int or expected_pid <= 0:
        result['error'] = 'owned_game_window_unavailable'
        return result
    try:
        api = api or Win32API()
        thread, actual_pid = api.owner(hwnd)
        if not thread or actual_pid != expected_pid:
            result['error'] = 'owned_game_window_identity_changed'
            return result
        result['gui_thread_id'] = thread
        info = GUITHREADINFO()
        info.cbSize = ctypes.sizeof(GUITHREADINFO)
        ok, error = api.query_gui(thread, info)  # Never thread0/the observer's foreground default.
        foreground = api.foreground()
        result['foreground_is_game_window'] = foreground == hwnd
        result['foreground_pid'] = api.owner(foreground)[1] if foreground else None
        if not ok:
            result['error'] = f'GetGUIThreadInfo:{error}'
            return result
        result.update(success=True, flags=int(info.flags), modal=bool(info.flags & MODAL_MASK),
                      moving_or_sizing=bool(info.flags & GUI_INMOVESIZE),
                      menu_mode=bool(info.flags & GUI_INMENUMODE),
                      system_menu_mode=bool(info.flags & GUI_SYSTEMMENUMODE),
                      popup_menu_mode=bool(info.flags & GUI_POPUPMENUMODE))
        for label, handle in [('move_size', info.hwndMoveSize), ('menu', info.hwndMenuOwner)]:
            result[label+'_window_is_game'] = bool(handle and int(handle) == hwnd)
            result[label+'_window_owned_by_game'] = bool(handle and api.owner(handle)[1] == expected_pid)
        return result
    except Exception as error:
        result['error'] = type(error).__name__
        return result
