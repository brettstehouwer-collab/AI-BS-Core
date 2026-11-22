import ctypes
from ctypes import wintypes
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication

app = QApplication(sys.argv)
screen = QGuiApplication.primaryScreen()

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
hdesk = user32.OpenInputDesktop(0, False, 0x01FF)

wins = []
def cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            t = buff.value
            if t not in ["Program Manager", "Windows Input Experience"]:
                wins.append((hwnd, t))
    return True

user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)

for h, t in wins[:5]:
    pm = screen.grabWindow(h)
    print(f"HWND {h} ({t[:30]}): Size = {pm.width()} x {pm.height()}")
    if not pm.isNull():
        pm.save(f"C:/AI-BS/scratch/win_grab_{h}.png")
        print(f"  -> Successfully saved window capture!")
