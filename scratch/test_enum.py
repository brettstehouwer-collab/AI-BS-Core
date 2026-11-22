import ctypes
from ctypes import wintypes
import sys

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

titles = []
def enum_windows_callback(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            titles.append((hwnd, buff.value))
    return True

proc = WNDENUMPROC(enum_windows_callback)
user32.EnumWindows(proc, 0)
print(f"Total visible windows with titles: {len(titles)}")
for h, t in titles[:15]:
    print(f"HWND {h}: {t}")
