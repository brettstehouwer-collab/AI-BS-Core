import os
import sys
import win32gui
import win32process
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication

app = QApplication(sys.argv)
screen = QGuiApplication.primaryScreen()
my_pid = os.getpid()

def enum_cb(hwnd, results):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w > 200 and h > 200 and pid != my_pid:
                results.append((hwnd, title, pid, w, h))

wins = []
win32gui.EnumWindows(enum_cb, wins)
print(f"Found {len(wins)} candidate windows:")
for hwnd, title, pid, w, h in wins[:10]:
    pm = screen.grabWindow(hwnd)
    print(f"HWND: {hwnd:8d} | {w}x{h} | Grabbed: {pm.width()}x{pm.height()} | Title: {title[:40]}")
