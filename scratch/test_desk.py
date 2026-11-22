import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

hdesk = user32.OpenInputDesktop(0, False, 0x01FF) # GENERIC_ALL
print("OpenInputDesktop:", hdesk)

titles = []
def cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            titles.append((hwnd, buff.value))
    return True

user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)
print(f"Total desktop windows: {len(titles)}")
for h, t in titles[:20]:
    print(f"HWND {h}: {t}")
