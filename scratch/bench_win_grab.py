import ctypes
from ctypes import wintypes
import time
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal

app = QApplication(sys.argv)
screen = QGuiApplication.primaryScreen()

user32 = ctypes.windll.user32
hdesk = user32.OpenInputDesktop(0, False, 0x01FF)

wins = []
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            t = buff.value
            if "Antigravity" in t or "Settings" in t:
                wins.append((hwnd, t))
    return True

user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)
if not wins:
    print("No matching windows found")
    sys.exit(0)

target_hwnd, target_title = wins[0]
print(f"Benchmarking capture of window: HWND {target_hwnd} ({target_title[:30]})")

times = []
for i in range(30):
    t0 = time.perf_counter()
    pm = screen.grabWindow(target_hwnd)
    dt = time.perf_counter() - t0
    times.append(dt)

print(f"Average capture time: {sum(times)/len(times)*1000:.2f} ms")
print(f"Max capture time: {max(times)*1000:.2f} ms")
print(f"Captured pixmap size: {pm.width()} x {pm.height()}")
