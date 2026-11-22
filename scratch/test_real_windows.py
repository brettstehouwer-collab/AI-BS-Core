import ctypes
from ctypes import wintypes
import os

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

my_pid = os.getpid()

def get_real_windows():
    hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
    windows = []
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    
    def cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == my_pid:
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.strip()
                if title and title not in ["Program Manager", "Windows Input Experience"]:
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    if w > 100 and h > 100:
                        windows.append((hwnd, title, w, h))
        return True
    
    user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)
    return windows

wins = get_real_windows()
print(f"Discovered {len(wins)} active application windows:")
for h, t, w, h_dim in wins:
    print(f" - [{h}] {t} ({w}x{h_dim})")
